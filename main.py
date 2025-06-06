import logging
import re
import datetime
import json
import helpers as h_func
from url_checker import contains_prohibited_url
from glob import glob as glob_glob
from re import split as re_split
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import commands as cmd

try:
    from config import TOKEN, PRIVILEGED_USERS
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

def load_channels():
    try:
        with open(h_func.get_latest_file(), "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading channels.json: {e}")
        return None

CHANNELS_DATA = load_channels()

# Configure logging to a file
logging.basicConfig(
    filename='logs.log',
    filemode='a',  # Append to the file
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.effective_message.text
    
    if text is None:
        #* message might be an image
        text: str = update.effective_message.caption
    
    chat = update.effective_chat
    user = update.effective_message.from_user

    chat_id = chat.id
    group_name = chat.title if hasattr(chat, "title") and chat.title else "Private Chat"

    member = await chat.get_member(user.id)
    logging.info(f"{user.username} whose id is {user.id} who is a {member.status} in chat '{group_name}' sent: {text.replace('\n', '\\n')}")

    if contains_prohibited_url(text, exempt_patterns=ALLOWED_URLS) and member.status in ['member']:
        # await update.effective_message.reply_text("Please don't share external URLs in the channel!")
        logging.info(f"deleting msg from {user.username} whose id is {user.id} who is a {member.status} whose msg was: {text.replace('\n', '\\n')}")
        await update.effective_message.delete()
        logging.info(f"msg deleted from {user.username} whose id is {user.id} who is a {member.status} whose msg was: {text.replace('\n', '\\n')}")
        return
    
    if member.status not in ['member'] and text.startswith('/'):
        msg = cmd.handle_commands(text, str(chat_id))
        if "get" not in msg:
            global CHANNELS_DATA
            CHANNELS_DATA = load_channels()
        await update.effective_message.reply_text(msg)
        return

    if "#doubt" in text:
        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).time()
        channel = h_func.get_channel_by_chat_id(chat_id, CHANNELS_DATA)
        if channel:
            active_slots = h_func.get_active_incharges(channel, current_time)
            if active_slots:
                tagged_users = " ".join([slot.get("user_id") for slot in active_slots])
                reply_text = f"{tagged_users} please check this doubt."
            else:
                next_slots = h_func.get_next_incharges(channel, current_time)
                if next_slots:
                    tagged_users = " ".join([slot.get("user_id") for slot in next_slots])
                    reply_text = f"No mentor is currently available. Mentor(s) from next slot: {tagged_users}, please be ready."
                else:
                    reply_text = "No mentor schedule available at the moment."
            await update.effective_message.reply_text(reply_text)
            logging.info(f"Replied to doubt message from {user.username} with: {reply_text}")
        else:
            logging.info(f"Channel with chat id {chat_id} not found in channels.json.")
            await update.effective_message.reply_text("Channel configuration not found.")
    
    if "#timing" in text:
        channel = h_func.get_channel_by_chat_id(chat_id, CHANNELS_DATA)
        if channel:
            timings = channel.get("timings", [])
            if timings:
                reply_text = f"Timings for {channel.get("name")}:\n"
                for slot in timings:
                    start, end = h_func.parse_time_range(slot.get('time'))
                    if start and end:
                        formatted_time = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
                    else:
                        formatted_time = f"Parsing failed: {slot.get('time')}"
                    reply_text += f"• {formatted_time}: {slot.get('name')} ({slot.get('user_id')})\n"
            else:
                reply_text = "No timings available for this channel."
        else:
            reply_text = "Channel configuration not found."
        await update.effective_message.reply_text(reply_text)
        logging.info(f"Replied with timings for chat id {chat_id}: {reply_text}")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_message))
    app.add_error_handler(error)

    logging.info("Starting bot...")
    print("Starting bot...")
    app.run_polling(poll_interval=0.05)
    print("Bot started successfully!")
    logging.info("Bot started successfully!")
