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
import os
import csv
import hashlib

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

def generate_query_id(user_id, date_str):
    """Generate a unique query ID based on date, time, and user ID"""
    # Create queries directory if it doesn't exist
    queries_dir = "queries"
    os.makedirs(queries_dir, exist_ok=True)
    
    # Get count of queries for today
    csv_path = os.path.join(queries_dir, f"{date_str}.csv")
    query_count = 0
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            query_count = sum(1 for _ in f) - 1  # Subtract header row
    
    # Generate hash from current timestamp, user ID and query count
    timestamp = datetime.datetime.now().timestamp()
    hash_input = f"{timestamp}-{user_id}-{query_count}"
    hash_object = hashlib.md5(hash_input.encode())
    hash_hex = hash_object.hexdigest()[:8]  # Take first 8 chars of hash
    
    # Final ID format: YYYYMMDD-COUNT-HASH
    return f"{date_str}-{query_count+1:03d}-{hash_hex}"

def log_query_to_csv(query_id, user_id, username, date_str, time_str, 
                    chat_id, chat_name, message_text):
    """Log query details to a daily CSV file in the queries folder"""
    # Create queries directory if it doesn't exist
    queries_dir = "queries"
    os.makedirs(queries_dir, exist_ok=True)
    
    csv_path = os.path.join(queries_dir, f"{date_str}.csv")
    file_exists = os.path.exists(csv_path)
    
    with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['query_id', 'date', 'time', 'user_id', 'username', 
                    'chat_id', 'chat_name', 'message']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'query_id': query_id,
            'date': date_str,
            'time': time_str,
            'user_id': user_id,
            'username': username,
            'chat_id': chat_id,
            'chat_name': chat_name,
            'message': message_text
        })
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
    
    # Handle queries with hashtags #querry, #query, or #qur
    if any(tag in text.lower() for tag in ["#querry", "#query", "#qur"]):
        # Get current date and time
        now = datetime.datetime.now()
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H:%M:%S')
        
        # Generate unique query ID
        query_id = generate_query_id(user.id, date_str)
        
        # Log to CSV
        log_query_to_csv(
            query_id, 
            user.id,
            user.username if user.username else "Unknown", 
            date_str, 
            time_str, 
            chat_id, 
            group_name, 
            text
        )
        
        # Reply to the message
        reply_text = f"Query #{query_id} raised. Our support team will reach you out soon."
        await update.effective_message.reply_text(reply_text)
        logging.info(f"Logged query #{query_id} from {user.username} in {group_name}: {text.replace('\n', '\\n')}")

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
