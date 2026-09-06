"""
sheets_helper.py
Shared helper functions for connecting to and reading/writing
the Google Sheet dashboard. Other scripts import from this file.
"""

import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    """Authenticate using the service account JSON stored in the
    GOOGLE_SERVICE_ACCOUNT_JSON environment variable (set from a GitHub Secret)."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON environment variable is missing."
        )

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def open_sheet():
    """Opens the target Google Sheet using the SHEET_ID environment variable."""
    sheet_id = os.environ.get("SHEET_ID")
    if not sheet_id:
        raise RuntimeError("SHEET_ID environment variable is missing.")

    client = get_client()
    return client.open_by_key(sheet_id)


def get_worksheet(tab_name):
    """Returns a specific tab/worksheet by name, e.g. 'Today', 'Used_Stories_Log'."""
    sheet = open_sheet()
    return sheet.worksheet(tab_name)


def read_all_rows(tab_name):
    """Returns all rows from a tab as a list of dictionaries (header row used as keys)."""
    ws = get_worksheet(tab_name)
    return ws.get_all_records()


def append_row(tab_name, row_values):
    """Appends a single row (a list of values, in column order) to the given tab."""
    ws = get_worksheet(tab_name)
    ws.append_row(row_values, value_input_option="USER_ENTERED")


def overwrite_row_2(tab_name, header_row, row_values):
    """
    Clears the tab (except header) and writes a single new row as row 2.
    Used for the 'Today' tab, which always shows just the latest story.
    """
    ws = get_worksheet(tab_name)
    ws.clear()
    ws.append_row(header_row, value_input_option="USER_ENTERED")
    ws.append_row(row_values, value_input_option="USER_ENTERED")
