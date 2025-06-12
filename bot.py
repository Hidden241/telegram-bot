import os
import requests
from io import BytesIO
from PIL import Image
import imagehash
from telegram.ext import Updater, MessageHandler, Filters, CommandHandler
from telegram import ChatPermissions

# Hashs d'images interdites
HASH_INTERDITS = {
    "8f0f0f070705071c"
}

# Analyse une image et retourne True si interdite
def image_est_interdite(photo, context):
    file = context.bot.get_file(photo.file_id)
    response = requests.get(file.file_path)
    img = Image.open(BytesIO(response.content))
    hash_image = str(imagehash.average_hash(img))
    return hash_image in HASH_INTERDITS, hash_image

# Démarrage
def start(update, context):
    chat_type = update.message.chat.type
    if chat_type == "private":
        update.message.reply_text(
            "👋 Je suis en **mode test**.\n"
            "Envoie-moi une image ici pour que je te dise si elle est bannissable."
        )
    else:
        update.message.reply_text(
            "🛡️ Je suis actif dans ce groupe et prêt à bannir les images interdites."
        )

# Traitement des images
def traiter_image(update, context):
    message = update.message
    user = message.from_user
    photo = message.photo[-1]

    chat_type = message.chat.type
    image_interdite, hash_calcule = image_est_interdite(photo, context)

    if chat_type == "private":
        if image_interdite:
            message.reply_text(f"⚠️ Cette image est interdite ! (hash: {hash_calcule})")
        else:
            message.reply_text(f"✅ Cette image est autorisée. (hash: {hash_calcule})")
    else:
        if image_interdite:
            context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user.id)
            message.reply_text(f"🚫 @{user.username or user.first_name} a été banni (image interdite détectée).")

def main():
    TOKEN = os.getenv("TON_TOKEN_BOT")
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.photo, traiter_image))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
