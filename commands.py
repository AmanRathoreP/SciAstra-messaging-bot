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
    group_to_update = None
    for group in data["channels"]:
        if str(group.get("id")) == group_id:
            group["timings"] = new_timings
            group_to_update = group
            break
    if group_to_update is None:
        return f"Group with ID {group_id} not found."
    
    try:
        save_channels_data(data)
        # --- Update Google Sheets for this group ---
        import gspread
        from google.oauth2.service_account import Credentials
        from gspread.utils import rowcol_to_a1
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
        client = gspread.authorize(creds)
        from config import google_sheet_id as sheet_id
        workbook = client.open_by_key(sheet_id)
        
        # Determine the order of this group among those with the same subject.
        subject = group_to_update.get("subject", "Unknown")
        same_subject_groups = [g for g in data["channels"] if g.get("subject", "Unknown").lower() == subject.lower()]
        index_within_subject = same_subject_groups.index(group_to_update)
        # Calculate the starting column (e.g., each group occupies 4 columns, with an extra column gap if needed)
        start_col = updater.num_to_col((index_within_subject * 5) + 1)
        channel_info = [[group_to_update.get("name"), group_to_update.get("id")]]
        
        import helpers
        timings_list = helpers.convert_group_timings_from_json_to_list(group_to_update)
        
        # Create/update the table for this group.
        updater.create_table(
            workbook, subject, start_row=1, start_col=start_col,
            channel_info=channel_info, values=timings_list, force_clear=True
        )
        
        # --- Clear any extra rows below the new data ---
        # Data rows begin at row 4 (start_row+3).
        start_data_row = 1 + 3  
        new_data_rows = len(timings_list)
        last_data_row = start_data_row + new_data_rows - 1
        sheet = workbook.worksheet(subject)
        start_col_idx = updater.col_to_num(start_col)  # convert column letter to index
        # The group table spans 4 columns (from start_col_idx to start_col_idx+3)
        total_rows = sheet.row_count
        if last_data_row < total_rows:
            clear_range = f"{rowcol_to_a1(last_data_row+1, start_col_idx)}:{rowcol_to_a1(total_rows, start_col_idx+3)}"
            sheet.batch_clear([clear_range])
        
        return f"Timings for group {group_id} replaced successfully and Google Sheet updated."
    except Exception as e:
        logging.error("Failed to update Google Sheet in replaceGroupTimings: %s", e)
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
        # --- Update Google Sheets for the target group ---
        import gspread
        from google.oauth2.service_account import Credentials
        from gspread.utils import rowcol_to_a1
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
        client = gspread.authorize(creds)
        from config import google_sheet_id as sheet_id
        workbook = client.open_by_key(sheet_id)
        
        subject = target_group.get("subject", "Unknown")
        same_subject_groups = [g for g in data["channels"] if g.get("subject", "Unknown").lower() == subject.lower()]
        index_within_subject = same_subject_groups.index(target_group)
        start_col = updater.num_to_col((index_within_subject * 5) + 1)
        channel_info = [[target_group.get("name"), target_group.get("id")]]
        
        import helpers
        timings_list = helpers.convert_group_timings_from_json_to_list(target_group)
        
        updater.create_table(
            workbook, subject, start_row=1, start_col=start_col,
            channel_info=channel_info, values=timings_list, force_clear=True
        )
        
        # --- Clear any extra rows below the newly updated data ---
        start_data_row = 1 + 3  # data rows start at row 4
        new_data_rows = len(timings_list)
        last_data_row = start_data_row + new_data_rows - 1
        sheet = workbook.worksheet(subject)
        start_col_idx = updater.col_to_num(start_col)
        total_rows = sheet.row_count
        if last_data_row < total_rows:
            clear_range = f"{rowcol_to_a1(last_data_row+1, start_col_idx)}:{rowcol_to_a1(total_rows, start_col_idx+3)}"
            sheet.batch_clear([clear_range])
        
        return f"Timings copied from group {source_id} to group {target_id} successfully, and Google Sheet updated."
    except Exception as e:
        logging.error("Failed to update Google Sheet in copyGroupTimings: %s", e)
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
    group_updated = None
    for group in data["channels"]:
        if str(group.get("id")) == str(chat_id):
            group["subject"] = subject
            group_found = True
            group_updated = group
            break
    if not group_found:
        # If group not found, add a new group with the given name.
        new_group = {"id": chat_id, "name": name, "subject": subject, "timings": []}
        data["channels"].append(new_group)
        group_updated = new_group
    try:
        save_channels_data(data)
        # --- Update Google Sheets for this group ---
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
        client = gspread.authorize(creds)
        from config import google_sheet_id as sheet_id
        workbook = client.open_by_key(sheet_id)
        
        subject = group_updated.get("subject", "Unknown")
        same_subject_groups = [g for g in data["channels"] if g.get("subject", "Unknown").lower() == subject.lower()]
        index_within_subject = same_subject_groups.index(group_updated)
        start_col = updater.num_to_col((index_within_subject * 5) + 1)
        channel_info = [[group_updated.get("name"), group_updated.get("id")]]
        timings_list = helpers.convert_group_timings_from_json_to_list(group_updated)
        updater.create_table(workbook, subject, start_row=1, start_col=start_col, channel_info=channel_info, values=timings_list)
        
        return (f"Group for chat ID {chat_id} updated/added with subject '{subject}'.\n"
                "Google Sheet updated for this group.")
    except Exception as e:
        logging.error("Failed to update google sheet in addGroupToList: %s", e)
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
        updater.create_table(workbook, subject, start_row=1, start_col=start_col, channel_info=channel_info, values=timings_list, force_clear=True)
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
        "/updateDatabase": "Updates database of bot based on the data provided in the sheets.",
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
        "9. /updateDatabase - Updates database of bot based on the data provided in the sheets.\n"
        "10. /docs COMMAND_NAME - Provides detailed documentation for a command.\n"
        "11. /help - Shows this help message."
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
        
        elif message.startswith("/updateDatabase"):
            return handle_update_database()

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

def handle_update_database() -> str:
    """
    Reads all timings from all subject worksheets in the Google Sheets.
    Only groups that exist in the local JSON are updated;
    groups not present in JSON are ignored.
    
    For each group in the JSON, its subject is used to open the corresponding sheet,
    and the group’s block is determined by its ordering (using the same (index*5)+1 formula).
    The timings table is read from the group's block (data rows starting from row 4)
    and converted into a list of timing dictionaries.
    Finally, the JSON is updated with the new timings and the updated data is returned.
    """
    data = load_channels_data()
    
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
        client = gspread.authorize(creds)
        from config import google_sheet_id as sheet_id
        workbook = client.open_by_key(sheet_id)
    except Exception as e:
        return f"Failed to access Google Sheets: {str(e)}"
    
    updated_count = 0
    for group in data["channels"]:
        subject = group.get("subject", "Unknown")
        if subject == "Unknown":
            continue  # Skip if no proper subject.
        try:
            sheet = workbook.worksheet(subject)
        except Exception:
            continue
        
        same_subject_groups = [g for g in data["channels"] if g.get("subject", "").lower() == subject.lower()]
        try:
            index_within_subject = same_subject_groups.index(group)
        except Exception:
            continue
        
        start_col = updater.num_to_col((index_within_subject * 5) + 1)
        start_data_row = 4  
        start_col_idx = updater.col_to_num(start_col)
        end_col = updater.num_to_col(start_col_idx + 3)
        
        data_range = f"{start_col}{start_data_row}:{end_col}{sheet.row_count}"
        try:
            values = sheet.get(data_range)
        except Exception:
            values = []
        
        new_timings = []
        for row in values:
            if len(row) < 4 or row[0].strip() == "":
                continue
            from_time = row[0].strip()
            to_time = row[1].strip()
            time_range_str = f"{from_time} - {to_time}"
            mentor_id = row[2].strip()
            if mentor_id and not mentor_id.startswith("@"):
                mentor_id = "@" + mentor_id
            mentor_name = row[3].strip()
            new_timings.append({
                "time": time_range_str,
                "name": mentor_name,
                "user_id": mentor_id
            })
        group["timings"] = new_timings
        updated_count += 1
    
    try:
        save_channels_data(data)
    except Exception as e:
        return f"Failed to save updated JSON: {str(e)}"

    response = f"Database update complete. Timings updated for {updated_count} groups.\n\n"
    for group in data["channels"]:
        response += f"Group ID: {group.get('id')}, Name: {group.get('name')}, Subject: {group.get('subject')}\n"
        if group.get("timings"):
            for timing in group["timings"]:
                response += f"    - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
        else:
            response += "    No timings available.\n"
        response += "\n"
    
    return response
