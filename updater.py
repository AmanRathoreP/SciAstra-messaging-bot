import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

def col_to_num(col_str: str) -> int:
    """
    Convert a column string (e.g., 'B', 'AA', 'aaa', 'acdd') to its corresponding numerical index.

    Args:
        col_str (str): The column letters.

    Returns:
        int: The corresponding column number (1-indexed).

    Raises:
        ValueError: If col_str contains non-alphabet characters.
    
    Examples:
        col_to_num("AAA")   -> 703
        col_to_num("acdd")  -> 19712
    """
    # Clean up the input: remove surrounding whitespace and convert to uppercase.
    col_str = col_str.strip().upper()

    # Validate that the string contains only letters.
    if not col_str.isalpha():
        raise ValueError("Invalid column string. It must contain only alphabetic characters.")

    num = 0
    # Process each character from left to right.
    for char in col_str:
        num = num * 26 + (ord(char) - ord('A') + 1)
    return num

def num_to_col(n: int) -> str:
    """
    Convert a positive integer (1-indexed) to its corresponding column letter.
    
    Args:
        n (int): The column number (1-indexed).
        
    Returns:
        str: The corresponding column letter(s).
        
    Examples:
        num_to_col(1)   -> "A"
        num_to_col(26)  -> "Z"
        num_to_col(27)  -> "AA"
    """
    if n < 1:
        raise ValueError("n must be a positive integer.")
    
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

def create_table(workbook, subject_name, start_row, start_col, channel_info=None, values=None, force_clear=False):
    """
    Creates a table in the given Google Sheet starting at the specified row and column.
    
    Parameters:
        channel_info (list of list): Data for the first row (e.g., channel info). Example:
        [["this is a testing channel", "-545454545"]]
        values (list of list): The table data rows to be placed starting two rows after start_row.
    """
    
    if subject_name in map(lambda x: x.title, workbook.worksheets()):
        sheet = workbook.worksheet(subject_name)
    else:
        sheet = workbook.add_worksheet(subject_name, rows=25, cols=500)
        sheet.clear()
    
    if force_clear:
        sheet.clear()

    sheet = workbook.worksheet(subject_name)

    start_col_idx = col_to_num(start_col)
    
    sheet.merge_cells(f"{start_col}{start_row}:{num_to_col(col_to_num(start_col)+1)}{start_row+1}", "MERGE_ALL")
    sheet.merge_cells(f"{num_to_col(col_to_num(start_col)+2)}{start_row}:{num_to_col(col_to_num(start_col)+3)}{start_row+1}", "MERGE_ALL")
    sheet.update(f"{start_col}{start_row}:{num_to_col(col_to_num(start_col)+1)}{start_row+1}", [[channel_info[0][0]]])
    sheet.update(f"{num_to_col(col_to_num(start_col)+2)}{start_row}:{num_to_col(col_to_num(start_col)+3)}{start_row+1}", [[channel_info[0][1]]])
    sheet.format(f"{start_col}{start_row}:{num_to_col(col_to_num(start_col)+3)}{start_row+1}", {"textFormat": {"bold": True, "fontSize": 13},  "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
    
    num_cols = 4
    header_row = start_row + 2
    start_cell = rowcol_to_a1(header_row, start_col_idx)
    end_cell = rowcol_to_a1(header_row, start_col_idx + num_cols - 1)
    cell_range = f"{start_cell}:{end_cell}"
    sheet.update(cell_range, [["From", "To", "mentor id", "mentor name"]])
    sheet.format(cell_range, {"textFormat": {"bold": True}})
    
    if values:
        num_cols = len(values[0])
        data_start_row = start_row + 3
        data_end_row = data_start_row + len(values) - 1
        start_cell = rowcol_to_a1(data_start_row, start_col_idx)
        end_cell = rowcol_to_a1(data_end_row, start_col_idx + num_cols - 1)
        cell_range = f"{start_cell}:{end_cell}"
        sheet.update(cell_range, values)

if __name__ == "__main__":
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("api_key.json", scopes=scopes)
    client = gspread.authorize(creds)
    
    from config import google_sheet_id as sheet_id
    workbook = client.open_by_key(sheet_id)
    
    channel_info = [["this is a testing channel","-545454545"]]
    values = [
        ["19:57", "23:02", "aman0864", "aman 4"]
    ]
    
    create_table(workbook, "test_api", start_row=3, start_col='I', channel_info=channel_info, values=values)
