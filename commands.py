import json
import logging
import helpers
import updater
import gspread
from google.oauth2.service_account import Credentials

def load_channels_data():
    try:
        with open(helpers.get_latest_file(), "r") as f:
            data = json.load(f)
            if "channels" not in data:
                data["channels"] = []
    except Exception:
        data = {"channels": []}
    return data

def save_channels_data(data):
    with open(helpers.get_latest_file(), "w") as f:
        json.dump(data, f, indent=4)

# Existing command: /updateChannels
def handle_update_channels(args: list, chat_id) -> str:
    """
    Handles the /updateChannels command given a list of arguments.
    Expected args format:
        [ChannelName, Subject, JSON_string]
    where JSON_string is a JSON array of timing objects, for example:
        [{"time": "11 AM - 2 PM", "name": "Het", "user_id": "@iamhet7"}, ...]
    Returns a response string.
    """
    if len(args) != 3:
        return ("Invalid number of arguments for /updateChannels. Please use:\n"
                "/updateChannels $$$ChannelName$$$ $$$Subject$$$ $$$[{{\"time\":\"...\",\"name\":\"...\",\"user_id\":\"...\"}}, ...]$$$")
    
    channel_name = args[0].strip()
    subject = args[1].strip()
    timings_str = args[2].strip()

    try:
        timings = json.loads(timings_str)
        if not isinstance(timings, list):
            return "Error: Timings must be provided as a JSON array."
        for item in timings:
            if not all(key in item for key in ("time", "name", "user_id")):
                return "Error: Each timing must contain 'time', 'name', and 'user_id' keys."
    except Exception as e:
        return f"Error parsing timings JSON: {str(e)}"
    
    channel_dict = {
        "id": chat_id,
        "name": channel_name,
        "subject": subject,
        "timings": timings
    }
    
    data = load_channels_data()
    channel_found = False
    for idx, channel in enumerate(data["channels"]):
        if str(channel.get("id")) == str(chat_id):
            # Update the existing channel.
            data["channels"][idx] = channel_dict
            channel_found = True
            break

    if not channel_found:
        data["channels"].append(channel_dict)
    
    try:
        save_channels_data(data)
        status_msg = "Channel updated successfully." if channel_found else "Channel added successfully."
        timings_msg = "New Doubt Timings:\n"
        for timing in timings:
            timings_msg += f" - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
        
        return f"{status_msg}\nChannel Name: {channel_name}\nSubject: {subject}\n{timings_msg}"
    except Exception as e:
        logging.error("Failed to update channels: %s", e)
        return f"Failed to update channels: {str(e)}"

# New command: /getGroupsList
def handle_get_groups_list() -> str:
    data = load_channels_data()
    if not data["channels"]:
        return "No groups found."
    response = "Groups List:\n"
    for group in data["channels"]:
        response += f" - ID: {group.get('id')}, Name: {group.get('name')}, Subject: {group.get('subject')}\n"
    return response

# New command: /replaceGroupTimings GROUP_ID {new timings in JSON format}
def handle_replace_group_timings(args: list) -> str:
    if len(args) != 2:
        return "Usage: /replaceGroupTimings GROUP_ID TIMINGS"
    group_id = args[0].strip()
    timings_str = args[1].strip()
    try:
        new_timings = json.loads(timings_str)
        if not isinstance(new_timings, list):
            return "Error: Timings must be a JSON array."
        for timing in new_timings:
            if not all(key in timing for key in ("time", "name", "user_id")):
                return "Error: Each timing must contain 'time', 'name', and 'user_id' keys."
    except Exception as e:
        return f"Error parsing timings JSON: {str(e)}"
    
    data = load_channels_data()
    found = False
    for group in data["channels"]:
        if str(group.get("id")) == group_id:
            group["timings"] = new_timings
            found = True
            break
    if not found:
        return f"Group with ID {group_id} not found."
    
    try:
        save_channels_data(data)
        return f"Timings for group {group_id} replaced successfully."
    except Exception as e:
        return f"Failed to replace timings: {str(e)}"

# New command: /copyGroupTimings TARGET_GROUP_ID SOURCE_GROUP_ID
def handle_copy_group_timings(args: list) -> str:
    if len(args) != 2:
        return "Usage: /copyGroupTimings TARGET_GROUP_ID SOURCE_GROUP_ID"
    target_id = args[0].strip()
    source_id = args[1].strip()
    
    data = load_channels_data()
    source_group = None
    target_group = None
    for group in data["channels"]:
        if str(group.get("id")) == source_id:
            source_group = group
        if str(group.get("id")) == target_id:
            target_group = group
    if source_group is None:
        return f"Source group with ID {source_id} not found."
    if target_group is None:
        return f"Target group with ID {target_id} not found."
    
    target_group["timings"] = source_group.get("timings", [])
    try:
        save_channels_data(data)
        return f"Timings copied from group {source_id} to group {target_id} successfully."
    except Exception as e:
        return f"Failed to copy timings: {str(e)}"

# New command: /getAllGroupsTimings
def handle_get_all_groups_timings() -> str:
    data = load_channels_data()
    if not data["channels"]:
        return "No groups found."
    response = "All Groups Timings:\n"
    for group in data["channels"]:
        response += f"Group ID: {group.get('id')}\nName: {group.get('name')}\nSubject: {group.get('subject')}\nTimings:\n"
        if "timings" in group and group["timings"]:
            for timing in group["timings"]:
                response += f"  - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
        else:
            response += "  No timings available.\n"
        response += "\n"
    return response

# New command: /getGroupTimings GROUP_ID
def handle_get_group_timings(args: list) -> str:
    if len(args) != 1:
        return "Usage: /getGroupTimings GROUP_ID"
    group_id = args[0].strip()
    data = load_channels_data()
    for group in data["channels"]:
        if str(group.get("id")) == group_id:
            response = f"Timings for Group ID {group_id}:\n"
            if "timings" in group and group["timings"]:
                for timing in group["timings"]:
                    response += f" - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
            else:
                response += "No timings available."
            return response
    return f"Group with ID {group_id} not found."

# New command: /getAllSubjectTimings SUBJECT
def handle_get_all_subject_timings(args: list) -> str:
    if len(args) != 1:
        return "Usage: /getAllSubjectTimings SUBJECT"
    subject = args[0].strip()
    data = load_channels_data()
    matching_groups = [group for group in data["channels"] if group.get("subject", "").lower() == subject.lower()]
    if not matching_groups:
        return f"No groups found for subject '{subject}'."
    response = f"Groups for subject '{subject}':\n"
    for group in matching_groups:
        response += f"Group ID: {group.get('id')}\nName: {group.get('name')}\nTimings:\n"
        if "timings" in group and group["timings"]:
            for timing in group["timings"]:
                response += f"  - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
        else:
            response += "  No timings available.\n"
        response += "\n"
    return response

# New command: /addGroupToList SUBJECT GROUP_NAME
def handle_add_group_to_list(args: list, chat_id) -> str:
    if len(args) != 2:
        return "Usage: /addGroupToList SUBJECT GROUP_NAME"
    subject = args[0].strip()
    name = args[1].strip()
    data = load_channels_data()
    group_found = False
    for group in data["channels"]:
        if str(group.get("id")) == str(chat_id):
            group["subject"] = subject
            group_found = True
            break
    if not group_found:
        # If group not found, add a new group with a default name.
        new_group = {"id": chat_id, "name": name, "subject": subject, "timings": []}
        data["channels"].append(new_group)
    try:
        save_channels_data(data)
        return (f"Group for chat ID {chat_id} updated/added with subject '{subject}'.\n"
                "Use /recreateSheets to update the Google Sheets accordingly.")
    except Exception as e:
        return f"Failed to update group: {str(e)}"

# This command reads the groups data and updates (recreates) the Google Sheet accordingly.
def handle_recreate_sheets() -> str:
    data = load_channels_data()
    if not data["channels"]:
        return "No groups available to recreate sheets."
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
    client = gspread.authorize(creds)

    from config import google_sheet_id as sheet_id
    workbook = client.open_by_key(sheet_id)
    # We use a counter per subject to calculate the starting column.
    subject_counter = {}
    for group in data["channels"]:
        subject = group.get("subject", "Unknown")
        if subject not in subject_counter:
            subject_counter[subject] = 0
        start_col = updater.num_to_col((subject_counter[subject] * 5) + 1)
        # Prepare channel info without nested double-quote issues.
        channel_info = [[group.get("name"), group.get("id")]]
        timings_list = helpers.convert_group_timings_from_json_to_list(group)
        updater.create_table(workbook, subject, start_row=1, start_col=start_col, channel_info=channel_info, values=timings_list)
        subject_counter[subject] += 1

    return "Google Sheets have been recreated with the current groups data."

# New command: /docs COMMAND_NAME
def handle_docs(args: list) -> str:
    if len(args) != 1:
        return "Usage: /docs COMMAND_NAME"
    command_name = args[0].strip()
    docs = {
        "/getGroupsList": "Returns a list of groups with names and subjects.",
        "/replaceGroupTimings": "Usage: /replaceGroupTimings GROUP_ID TIMINGS - Updates timings for a group.",
        "/copyGroupTimings": "Usage: /copyGroupTimings TARGET_GROUP_ID SOURCE_GROUP_ID - Copies timings from one group to another.",
        "/getAllGroupsTimings": "Returns detailed info for all groups and their timings.",
        "/getGroupTimings": "Usage: /getGroupTimings GROUP_ID - Returns the timings of a specific group.",
        "/getAllSubjectTimings": "Usage: /getAllSubjectTimings SUBJECT - Returns groups for a subject with their timings.",
        "/addGroupToList": "Usage: /addGroupToList SUBJECT GROUP_NAME - Adds/updates the current group in the local data (without Google Sheet update).",
        "/recreateSheets": "Recreates/updates the Google Sheets for all groups based on local data.",
        "/docs": "Usage: /docs COMMAND_NAME - Provides detailed documentation for a command.",
        "/help": "Shows this help message."
    }
    if command_name in docs:
        return docs[command_name]
    else:
        return f"No documentation found for command '{command_name}'."

# New command: /help
def handle_help() -> str:
    help_text = (
        "Bot Commands:\n"
        "1. /getGroupsList - Returns a list of groups with names and subjects.\n"
        "2. /replaceGroupTimings GROUP_ID TIMINGS - Updates timings for a group.\n"
        "3. /copyGroupTimings TARGET_GROUP_ID SOURCE_GROUP_ID - Copies timings from one group to another.\n"
        "4. /getAllGroupsTimings - Returns detailed info for all groups and their timings.\n"
        "5. /getGroupTimings GROUP_ID - Returns the timings of a specific group.\n"
        "6. /getAllSubjectTimings SUBJECT - Returns groups for a subject with their timings.\n"
        "7. /addGroupToList SUBJECT GROUP_NAME - Adds/updates current group with the provided subject (local data only).\n"
        "8. /recreateSheets - Recreates/updates the Google Sheets based on current groups.\n"
        "9. /docs COMMAND_NAME - Provides detailed documentation for a command.\n"
        "10. /help - Shows this help message."
    )
    return help_text

# Fallback for unknown commands
def handle_unknown_command(message: str) -> str:
    return "Unknown command. Please check your input and try again."

# Command router
def handle_commands(message: str, chat_id) -> str:
    """
    Parses the input command message, routes it to the appropriate command handler,
    and returns the response message that the bot should send.

    The $$$ delimiter is used to split the message into arguments.
    """
    try:
        if message.startswith("/updateChannels"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/updateChannels"):
                args = args[1:]
            return handle_update_channels(args, chat_id)
        
        elif message.startswith("/getGroupsList"):
            return handle_get_groups_list()
        
        elif message.startswith("/replaceGroupTimings"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/replaceGroupTimings"):
                args = args[1:]
            return handle_replace_group_timings(args)
        
        elif message.startswith("/copyGroupTimings"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/copyGroupTimings"):
                args = args[1:]
            return handle_copy_group_timings(args)
        
        elif message.startswith("/getAllGroupsTimings"):
            return handle_get_all_groups_timings()
        
        elif message.startswith("/getGroupTimings"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/getGroupTimings"):
                args = args[1:]
            return handle_get_group_timings(args)
        
        elif message.startswith("/getAllSubjectTimings"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/getAllSubjectTimings"):
                args = args[1:]
            return handle_get_all_subject_timings(args)
        
        elif message.startswith("/addGroupToList"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/addGroupToList"):
                args = args[1:]
            return handle_add_group_to_list(args, chat_id)
        
        elif message.startswith("/recreateSheets"):
            return handle_recreate_sheets()

        elif message.startswith("/docs"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]
            if args and args[0].startswith("/docs"):
                args = args[1:]
            return handle_docs(args)
        
        elif message.startswith("/help"):
            return handle_help()
        
        else:
            return handle_unknown_command(message)
    except Exception as e:
        logging.exception("Error handling command: %s", e)
        return f"An unexpected error occurred: {str(e)}"
