import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
import cv2
import tempfile
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

# === Liste des hash interdits (images et vidéos) ===
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
    123456789  # 👈 Remplace ceci par TON ID TELEGRAM
}

# === Fonctions utilitaires ===
def calculer_hash_image(img: Image.Image) -> str:
    return str(imagehash.average_hash(img))

def verifier_image(photo, context):
    file = context.bot.get_file(photo.file_id)
    response = requests.get(file.file_path)
    img = Image.open(BytesIO(response.content))
    return calculer_hash_image(img)

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

# === Commande /start ===
def start(update, context):
    message = update.message
    chat_type = message.chat.type
    user_id = message.from_user.id
    user = message.from_user

    if chat_type == "private":
        if user_id in TEST_AUTORISÉS:
            message.reply_text("👋 Mode test activé.\nEnvoie-moi une image ou vidéo pour vérification.")
        else:
            message.reply_text("⛔ Tu n’es pas autorisé à tester ce bot.")
    else:
        # En groupe
        if user_id not in TEST_AUTORISÉS:
            context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
            context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user_id)
            context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 @{user.username or user.first_name} a été banni (commande /start non autorisée)."
            )
        else:
            message.reply_text("🛡️ Je suis actif pour modérer ce groupe.")

# === Traitement image ou vidéo ===
def traiter_media(update, context):
    message = update.message
    user = message.from_user
    chat_type = message.chat.type

    # Sécurité : limiter l'accès au test
    if chat_type == "private" and user.id not in TEST_AUTORISÉS:
        message.reply_text("⛔ Tu n’es pas autorisé à tester ce bot.")
        return

    # Détection du type de média
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
            message.reply_text(f"🚫 Ce média est INTERDIT. (hash : {hash_calcule})")
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

# === Lancement du bot ===
def main():
    TOKEN = os.getenv("BOT_TOKEN")  # 🔐 Ton token doit être défini dans les variables d’environnement
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo | Filters.video, traiter_media))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
