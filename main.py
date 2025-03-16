import logging
from url_checker import contains_prohibited_url
from glob import glob as glob_glob
from re import split as re_split
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

try:
    from config import TOKEN
except ImportError:
    logging.error("config.py not found. Please create it with your Telegram bot token.")
    print("config.py not found. Please create it with your Telegram bot token.")
    exit(1)

def load_allowed_urls():
    all_urls = []
    for file_path in glob_glob("*_allowed_urls.txt"):
        with open(file_path, 'r') as file:
            urls = re_split(r'\n+', file.read().strip())
            all_urls.extend(urls)
    return all_urls

ALLOWED_URLS = load_allowed_urls()

# Configure logging to log error messages to a file
logging.basicConfig(
    filename='logs.log',
    filemode='a',  # Append to the file
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.effective_message.text
    chat = update.effective_chat
    user = update.effective_message.from_user
    
    member = await chat.get_member(user.id)
    logging.info(f"{user.username} whose id is {user.id} who is a {member.status} sent: {text.replace('\n', '\\n')}")
    if member.status not in ['member']:
        return

    if contains_prohibited_url(text, exempt_patterns=ALLOWED_URLS):
        # await update.effective_message.reply_text("Please don't share external URLs in the channel!")
        logging.info(f"deleting msg from {user.username} whose id is {user.id} who is a {member.status} whose msg was: {text.replace('\n', '\\n')}")
        await update.effective_message.delete()
        logging.info(f"msg deleted from {user.username} whose id is {user.id} who is a {member.status} whose msg was: {text.replace('\n', '\\n')}")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_error_handler(error)

    logging.info("Starting bot...")
    print("Starting bot...")
    app.run_polling(poll_interval=0.05)
    print("Bot started successfully!")
    logging.info("Bot started successfully!")
