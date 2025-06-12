import os
from telegram.ext import Updater, CommandHandler

def start(update, context):
    update.message.reply_text("Bot en ligne !")

def main():
    TOKEN = os.getenv("8131425515:AAH76rY-86ooMlI-Gb895T-Zoosc0ZYk7wc")
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
