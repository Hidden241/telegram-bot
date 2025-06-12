import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
import cv2
import tempfile

from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# === Hashs interdits ===
HASH_INTERDITS = {
    "8f0f0f070705071c",  # image interdite
    "007d070303bfffff",  # vidéo interdite (hash première frame)
}

# === Fonction imagehash (image ou vidéo frame) ===
def calculer_hash_image(img: Image.Image) -> str:
    return str(imagehash.average_hash(img))

# === Traitement d'une image Telegram ===
def verifier_image(photo, context):
    file = context.bot.get_file(photo.file_id)
    response = requests.get(file.file_path)
    img = Image.open(BytesIO(response.content))
    return calculer_hash_image(img)

# === Traitement d'une vidéo Telegram (extraire frame + hasher) ===
def verifier_video(video, context):
    file = context.bot.get_file(video.file_id)
    video_url = file.file_path

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
        tmp_video.write(requests.get(video_url).content)
        tmp_video_path = tmp_video.name

    cap = cv2.VideoCapture(tmp_video_path)
    success, frame = cap.read()
    cap.release()
    os.remove(tmp_video_path)

    if success:
        frame_path = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
        cv2.imwrite(frame_path, frame)
        img = Image.open(frame_path)
        os.remove(frame_path)
        return calculer_hash_image(img)
    return None

# === START Commande ===
def start(update, context):
    chat_type = update.message.chat.type
    if chat_type == "private":
        update.message.reply_text("👋 Mode test actif.\nEnvoie-moi une image ou une vidéo.")
    else:
        update.message.reply_text("🛡️ Je suis actif pour bannir les images et vidéos interdites.")

# === Traitement général ===
def traiter_media(update, context):
    message = update.message
    user = message.from_user
    chat_type = message.chat.type

    if message.photo:
        hash_calcule = verifier_image(message.photo[-1], context)
    elif message.video:
        hash_calcule = verifier_video(message.video, context)
    else:
        return

    if hash_calcule is None:
        message.reply_text("⚠️ Impossible de lire le média.")
        return

    if chat_type == "private":
        if hash_calcule in HASH_INTERDITS:
            message.reply_text(f"🚫 Ce média est interdit. (hash : {hash_calcule})")
        else:
            message.reply_text(f"✅ Ce média est autorisé. (hash : {hash_calcule})")
    else:
        if hash_calcule in HASH_INTERDITS:
            context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
            context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user.id)
            context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 @{user.username or user.first_name} a été banni (média interdit détecté)."
            )

# === Main ===
def main():
    TOKEN = os.getenv("TON_TOKEN_BOT")
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo | Filters.video, traiter_media))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
