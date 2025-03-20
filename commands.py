import json
import logging

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
    
    try:
        with open("channels_id_with_slots_info.json", "r") as f:
            data = json.load(f)
            if "channels" not in data:
                data["channels"] = []
    except Exception:
        data = {"channels": []}
    
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
        with open("channels_id_with_slots_info.json", "w") as f:
            json.dump(data, f, indent=4)
        
        status_msg = "Channel updated successfully." if channel_found else "Channel added successfully."
        timings_msg = "New Doubt Timings:\n"
        for timing in timings:
            timings_msg += f" - {timing.get('time')}: {timing.get('name')} ({timing.get('user_id')})\n"
        
        return f"{status_msg}\nChannel Name: {channel_name}\nSubject: {subject}\n{timings_msg}"
    except Exception as e:
        logging.error("Failed to update channels: %s", e)
        return f"Failed to update channels: {str(e)}"

def handle_unknown_command(message: str) -> str:
    """
    Handles commands that are not recognized.
    """
    return "Unknown command. Please check your input and try again."

def handle_commands(message: str, chat_id) -> str:
    """
    Parses the input command message, routes it to the appropriate command handler,
    and returns the response message that the bot should send.
    
    The $$$ delimiter is used only here to split the message into arguments.
    For example, the expected format for /updateChannels is:
    /updateChannels $$$ChannelName$$$ $$$Subject$$$ $$$[{"time":"11 AM - 2 PM","name":"Het","user_id":"@iamhet7"}, ...]$$$
    """
    try:
        if message.startswith("/updateChannels"):
            parts = message.split("$$$")
            args = [part.strip() for part in parts if part.strip()]

            if args and args[0].startswith("/updateChannels"):
                args = args[1:]
            return handle_update_channels(args, chat_id)
        
        else:
            return handle_unknown_command(message)
    except Exception as e:
        logging.exception("Error handling command: %s", e)
        return f"An unexpected error occurred: {str(e)}"
