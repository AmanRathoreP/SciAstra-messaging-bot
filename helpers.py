import datetime
import re
import logging
import os

def parse_time_string(time_str: str):
    """
    Tries to parse a time string using multiple formats.
    Ensures there's a space before AM/PM if missing.
    """
    # Ensure a space before AM/PM if missing (e.g., "1:26PM" -> "1:26 PM")
    time_str = re.sub(r'(\d)(AM|PM)', r'\1 \2', time_str)
    for fmt in ('%I %p', '%I:%M %p'):
        try:
            return datetime.datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    logging.error(f"Time string '{time_str}' doesn't match expected formats")
    return None

def parse_time_range(time_str: str):
    """
    Parses a time range string into two datetime.time objects.
    If the start time is missing AM/PM information, it infers it from the end time.
    """
    parts = time_str.split('-')
    if len(parts) != 2:
        return None, None
    start_str = parts[0].strip()
    end_str = parts[1].strip()

    # If start_str doesn't contain AM/PM but end_str does, append that info to start_str.
    if ('AM' not in start_str and 'PM' not in start_str) and ('AM' in end_str or 'PM' in end_str):
        if 'AM' in end_str:
            start_str = start_str + ' AM'
        elif 'PM' in end_str:
            start_str = start_str + ' PM'
    
    start_time = parse_time_string(start_str)
    end_time = parse_time_string(end_str)
    
    return start_time, end_time


def is_time_in_interval(start: datetime.time, end: datetime.time, current: datetime.time) -> bool:
    if start <= end:
        return start <= current < end
    else:
        return current >= start or current < end


def get_channel_by_chat_id(chat_id: str, channels_data):
    """
    Finds the channel in channels_data with a matching chat id.
    """
    if not channels_data or "channels" not in channels_data:
        return None
    for channel in channels_data["channels"]:
        if str(channel.get("id")) == str(chat_id):
            return channel
    return None

def get_active_incharges(channel, current_time: datetime.time):
    """
    Returns a list of all timing slots in the channel that are active at the current time.
    """
    active_slots = []
    for slot in channel.get("timings", []):
        start, end = parse_time_range(slot["time"])
        if start is None or end is None:
            continue
        if is_time_in_interval(start, end, current_time):
            active_slots.append(slot)
    return active_slots

def get_next_incharges(channel, current_time: datetime.time):
    """
    Returns a list of upcoming timing slots that share the earliest start time,
    based on the current time. If none are upcoming, returns the first slot.
    """
    upcoming_slots = []
    today = datetime.date.today()
    current_datetime = datetime.datetime.combine(today, current_time)
    for slot in channel.get("timings", []):
        start, _ = parse_time_range(slot["time"])
        if start is None:
            continue
        slot_datetime = datetime.datetime.combine(today, start)
        if slot_datetime > current_datetime:
            upcoming_slots.append((slot_datetime, slot))
    if upcoming_slots:
        upcoming_slots.sort(key=lambda x: x[0])
        earliest_start = upcoming_slots[0][0]
        # return all slots that have the earliest start time
        next_slots = [slot for dt, slot in upcoming_slots if dt == earliest_start]
        return next_slots
    # if no upcoming slot, return the first slot (as a fallback)
    if channel.get("timings", []):
        return [channel["timings"][0]]
    return []

def get_latest_file(directory_path="slots_info"):
    try:
        files = [f.replace(".json",'') for f in os.listdir(directory_path)
                if os.path.isfile(os.path.join(directory_path, f))]
        
        if not files:
            return None
        
        latest_file = max(files)
        
        return os.path.join("slots_info",latest_file+".json")
    
    except Exception as e:
        print(f"Error: {e}")
        return None

def format_time(t: datetime.time) -> str:
    """
    Formats a datetime.time object into a 12-hour time string with minutes.
    For example, if t represents 10:00 AM it returns "10:00 AM", and if t represents 13:00 it returns "1:00 PM".
    """
    # Convert 24-hr to 12-hr format: modulo 12, and use 12 in case hour is 0.
    hour = t.hour % 12
    if hour == 0:
        hour = 12
    return f"{hour}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"

def convert_group_timings_from_json_to_list(group: dict) -> list:
    """
    Converts each timing entry in the group's 'timings' list into the format:
      [start_time_str, end_time_str, user_id_without_@, name]
    
    For example, given a timing like:
        {
            "time": "10 AM - 1 PM",
            "name": "Het",
            "user_id": "@iamhet7"
        }
    The resulting list will be:
        ['10:00 AM', '1:00 PM', 'iamhet7', 'Het']
    """
    results = []
    timings = group.get("timings", [])
    for slot in timings:
        time_range_str = slot.get("time", "")
        start, end = parse_time_range(time_range_str)
        if not start or not end:
            logging.warning(f"Could not parse time range: {time_range_str}")
            continue
        start_formatted = format_time(start)
        end_formatted = format_time(end)
        # Remove the leading '@' from the user_id, if present.
        user_id = slot.get("user_id", "").lstrip("@")
        name = slot.get("name", "")
        results.append([start_formatted, end_formatted, user_id, name])
    return results

# Example usage of convert_group_timings_from_json_to_list:
if __name__ == "__main__":
    import json
    group_json = '''
    {
        "id": "-1002532167212",
        "name": "SciAstra bot test",
        "subject": "test",
        "timings": [
            {
                "time": "10 AM - 1 PM",
                "name": "Het",
                "user_id": "@iamhet7"
            },
            {
                "time": "5 PM - 7 PM",
                "name": "Aman",
                "user_id": "@aman0864"
            },
            {
                "time": "7 - 11 PM",
                "name": "Tamoghna",
                "user_id": "@Tamoghna"
            }
        ]
    }
    '''
    group = json.loads(group_json)
    print(convert_group_timings_from_json_to_list(group))


# Test time parsing
if __name__=="__main__":
    # --- Example Usage ---
    example_ranges = [
        "1:26PM - 2:30PM",      # Without space before PM
        "1:26 PM - 2:30 PM",    # With space before PM
        "10 AM - 1 PM",         # Without minutes
        "10:15 AM - 1:26 PM",   # With minutes
        "7 - 11 PM",            # Start missing AM/PM but inferred from end time
    ]

    print("Time Range Parsing Examples:")
    for example in example_ranges:
        start, end = parse_time_range(example)
        print(f"Example: '{example}'")
        print(f"  Parsed Start Time: {start}")
        print(f"  Parsed End Time:   {end}\n")
        
    
    print(get_latest_file())
