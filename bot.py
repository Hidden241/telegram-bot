import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
import cv2
import tempfile
import threading
from collections import defaultdict
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler

HASH_INTERDITS = {
    "8f0f0f070705071c", "007d070303bfffff", "3c7ee7cfefc40000",
    "00007f7f031fffff", "0406357ffffb3300", "829193c7f67e0ef7",
    "ffff8f0f0f070200", "f1fe4c721e7ce0d8", "00803c3e2e2c2030",
    "ffff8f0707070300", "8290c1e3763e07f3", "0000000000ffff00", "fce0c0f0e060f0c0"
}

TEST_AUTORISÉS = {
    123456789, 5296696302  # Ajout de @op75x15
}

MODERATEUR_CHAT_ID = 5296696302

media_group_cache = defaultdict(list)
media_group_timers = {}

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
        if user_id not in TEST_AUTORISÉS:
            context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
            context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user_id)
            context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 @{user.username or user.first_name} a été banni (commande /start non autorisée)."
            )
            context.bot.send_message(
                chat_id=MODERATEUR_CHAT_ID,
                text=f"📣 J'ai supprimé @{user.username or user.first_name} pour usage non autorisé de /start dans le groupe '{message.chat.title}'."
            )
        else:
            message.reply_text("🛡️ Je suis actif pour modérer ce groupe.")

def traiter_media(update, context):
    message = update.message
    user = message.from_user
    chat_type = message.chat.type

    if chat_type == "private" and user.id not in TEST_AUTORISÉS:
        message.reply_text("⛔ Tu n’es pas autorisé à tester ce bot.")
        return

    def analyser_groupe(media_group_id):
        fichiers = media_group_cache.pop(media_group_id, [])
        suspect = False
        for msg in fichiers:
            hash_calcule = None
            if msg.video:
                hash_calcule = verifier_video(msg.video, context)
            elif msg.photo:
                hash_calcule = verifier_image(msg.photo[-1], context)

            if not hash_calcule:
                continue
            if hash_calcule in HASH_INTERDITS:
                suspect = True
                break

        if suspect:
            for msg in fichiers:
                try:
                    context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
                except:
                    pass
            context.bot.kick_chat_member(chat_id=msg.chat_id, user_id=msg.from_user.id)
            context.bot.send_message(
                chat_id=msg.chat_id,
                text=f"🚫 @{msg.from_user.username or msg.from_user.first_name} a été banni (média interdit détecté dans un groupe de fichiers)."
            )
            context.bot.send_message(
                chat_id=MODERATEUR_CHAT_ID,
                text=f"📣 J'ai supprimé @{msg.from_user.username or msg.from_user.first_name} pour envoi de médias interdits dans le groupe '{msg.chat.title}'."
            )

    if (message.video or message.photo) and message.media_group_id:
        mgid = message.media_group_id
        media_group_cache[mgid].append(message)

        if media_group_timers.get(mgid):
            media_group_timers[mgid].cancel()

        timer = threading.Timer(3.0, analyser_groupe, args=(mgid,))
        media_group_timers[mgid] = timer
        timer.start()
    elif message.video or message.photo:
        if message.video:
            hash_calcule = verifier_video(message.video, context)
        else:
            hash_calcule = verifier_image(message.photo[-1], context)

        if not hash_calcule:
            return

        if hash_calcule in HASH_INTERDITS:
            if chat_type == "private":
                message.reply_text(f"🚫 Ce média est interdit. (hash : {hash_calcule})")
            else:
                context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user.id)
                context.bot.send_message(
                    chat_id=message.chat_id,
                    text=f"🚫 @{user.username or user.first_name} a été banni (média interdit détecté)."
                )
                context.bot.send_message(
                    chat_id=MODERATEUR_CHAT_ID,
                    text=f"📣 J'ai supprimé @{user.username or user.first_name} pour envoi de média interdit dans le groupe '{message.chat.title}'."
                )
        elif chat_type == "private":
            message.reply_text(f"✅ Ce média est autorisé. (hash : {hash_calcule})")

def main():
    import logging
    logging.basicConfig(level=logging.INFO)

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("❌ BOT_TOKEN n’est pas défini dans les variables d’environnement !")

    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.video | Filters.photo, traiter_media))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
