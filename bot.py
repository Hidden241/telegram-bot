import os
from telegram import ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ChatMemberHandler

# Liste des vidéos interdites (file_id à adapter)
VIDEOS_INTERDITES = {
    "ABC123==",
    "XYZ456=="
}

# Liste des mots interdits
MOTS_INTERDITS = {"mahely", "mahely."}

# Quand le bot est ajouté à un groupe
def handle_chat_member(update, context):
    chat_member = update.my_chat_member
    if chat_member.new_chat_member.status == "member":
        context.bot.send_message(
            chat_id=chat_member.chat.id,
            text="🛡️ Je commence ma mission de surveillance dans ce groupe."
        )

# Commande /start
def start(update, context):
    if update.message.chat.type == "private":
        update.message.reply_text(
            "👋 Je suis un bot de modération. "
            "Ajoute-moi dans un groupe et donne-moi les droits nécessaires pour que je puisse fonctionner."
        )
    else:
        update.message.reply_text(
            "👋 Bonjour, je suis chargé de réguler ce groupe.\n"
            "Je suis l'**anti PEDO Java**, ici pour bannir les vidéos interdites "
            "et réduire au silence ceux qui enfreignent les règles.\n"
            "Tape /aide pour en savoir plus."
        )

# Commande /aide
def aide(update, context):
    update.message.reply_text(
        "📌 Ce que je fais :\n"
        "- Je bannis les utilisateurs qui envoient certaines vidéos interdites.\n"
        "- Je réduis au silence pendant 10 minutes ceux qui utilisent certains mots.\n"
        "🛡️ Respectez les règles du groupe !"
    )

# Détection des vidéos interdites
def detect_video(update, context):
    message = update.message
    user = message.from_user
    video = message.video

    if video and video.file_id in VIDEOS_INTERDITES:
        context.bot.kick_chat_member(chat_id=message.chat_id, user_id=user.id)
        update.message.reply_text(f"🚫 @{user.username or user.first_name} a été banni (vidéo interdite).")

# Mute temporaire en cas de mot interdit
def detect_mots(update, context):
    message = update.message
    text = message.text.lower()
    user = message.from_user

    if any(mot in text for mot in MOTS_INTERDITS):
        permissions = ChatPermissions(can_send_messages=False)
        context.bot.restrict_chat_member(
            chat_id=message.chat_id,
            user_id=user.id,
            permissions=permissions,
            until_date=message.date + 600
        )
        update.message.reply_text(f"🤐 @{user.username or user.first_name} a été réduit au silence pour 10 minutes.")

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("aide", aide))
    dp.add_handler(MessageHandler(Filters.video, detect_video))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), detect_mots))
    dp.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
