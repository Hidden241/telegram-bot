import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
import cv2
import tempfile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# === Hashs de médias interdits ===
HASH_INTERDITS = {
    "8f0f0f070705071c",
    "007d070303bfffff",
    "3c7ee7cfefc40000",
    "00007f7f031fffff",
    "0406357ffffb3300",
    "829193c7f67e0ef7",
    "ffff8f0f0f070200",
    "f1fe4c721e7ce0d8",
    "00803c3e2e2c2030"
}

# === Utilisateurs autorisés à tester le bot en privé ===
TEST_AUTORISÉS = {
    7274386267,
    5296696302
}

# === Outils de hash ===
def calculer_hash_image(img: Image.Image) -> str:
    return str(imagehash.average_hash(img))

def verifier_image(photo, context):
    file = context.bot.get_file(photo.file_id)
    response = requests.get(file.file_path)
    img = Image.open(BytesIO(response.content))
    return calculer_hash_image(img)

def verifier_video(video, context):
    file = context.bot.get_file(video.file_id)
    response = requests.get(file.file_path)
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(response.content)
        path = tmp.name

    cap = cv2.VideoCapture(path)
    success, frame = cap.read()
    cap.release()
    os.remove(path)

    if success:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as img_tmp:
            cv2.imwrite(img_tmp.name, frame)
            img = Image.open(img_tmp.name)
            os.remove(img_tmp.name)
            return calculer_hash_image(img)
    return None

# === Démarrage ===
def start(update, context):
    chat_type = update.message.chat.type
    if chat_type == "private":
        if update.message.from_user.id in TEST_AUTORISÉS:
            update.message.reply_text("👋 Mode test activé. Envoie une image ou une vidéo.")
        else:
            update.message.reply_text("⛔ Tu n’es pas autorisé à utiliser ce bot.")
    else:
        update.message.reply_text("🛡️ Bot actif pour modération automatique du groupe.")

# === Traitement global de tous les médias (photos/vidéos) ===
def traiter_media(update, context):
    message = update.message
    user = message.from_user
    chat_type = message.chat.type

    # Refuser accès privé non autorisé
    if chat_type == "private" and user.id not in TEST_AUTORISÉS:
        message.reply_text("⛔ Tu n’es pas autorisé à utiliser ce bot.")
        return

    # Stocker tous les hash à tester
    hashs_detectés = []

    # 1. Traiter chaque photo individuellement
    if message.photo:
        for photo in message.photo:
            hash_img = verifier_image(photo, context)
            hashs_detectés.append(hash_img)

    # 2. Traiter la vidéo (1 par message possible)
    if message.video:
        hash_vid = verifier_video(message.video, context)
        if hash_vid:
            hashs_detectés.append(hash_vid)

    if not hashs_detectés:
        return

    # === Comportement privé : test ===
    if chat_type == "private":
        for h in hashs_detectés:
            if h in HASH_INTERDITS:
                message.reply_text(f"🚫 Média interdit (hash : {h})")
            else:
                message.reply_text(f"✅ Média autorisé (hash : {h})")

    # === Comportement groupe : modération ===
    else:
        if any(h in HASH_INTERDITS for h in hashs_detectés):
            context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
            context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user.id)
            context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 @{user.username or user.first_name} a été banni (média interdit détecté)."
            )

# === Lancement principal ===
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
