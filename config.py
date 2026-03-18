"""
ROIN WORLD FZE — Bot Configuration
====================================
Works in TWO modes:
  LOCAL:   Reads secrets from .txt files and credentials.json
  RAILWAY: Reads secrets from environment variables

The bot auto-detects which mode to use.
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# 1. DETECT ENVIRONMENT — Railway sets RAILWAY_ENVIRONMENT automatically
# ---------------------------------------------------------------------------
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 2. READ SECRETS — from env vars (Railway) or files (local)
# ---------------------------------------------------------------------------

def _read_file(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r") as f:
        return f.read().strip()


if IS_RAILWAY:
    # On Railway: secrets come from environment variables
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    SHEET_ID = os.environ["SHEET_ID"]
    _creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
else:
    # Local: secrets come from files in the day1 folder
    BOT_TOKEN = _read_file("bot_token.txt")
    SHEET_ID = _read_file("sheet_id.txt")
    _creds_json = None  # will use file directly


# ---------------------------------------------------------------------------
# 3. GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

if IS_RAILWAY:
    _creds = Credentials.from_service_account_info(_creds_json, scopes=SCOPES)
else:
    _creds = Credentials.from_service_account_file(
        os.path.join(BASE_DIR, "credentials.json"), scopes=SCOPES
    )

GS_CLIENT = gspread.authorize(_creds)
WORKBOOK = GS_CLIENT.open_by_key(SHEET_ID)


# ---------------------------------------------------------------------------
# 4. SHEET TAB NAMES
# ---------------------------------------------------------------------------
TAB_EMPLOYEE_DB = "Employee_DB"
TAB_LEAVE_BALANCE = "Leave_Balance"
TAB_LEAVE_LOG = "Leave_Log"
TAB_USER_REGISTRY = "User_Registry"
TAB_ACCESS_LOG = "Access_Log"
TAB_ATTENDANCE = "Attendance_Sheet"


# ---------------------------------------------------------------------------
# 5. COMPANY SETTINGS
# ---------------------------------------------------------------------------
MAX_USERS = 50
MAX_FAILED_ATTEMPTS = 3
BCRYPT_SALT_ROUNDS = 12

VALID_ROLES = [
    "DIRECTOR", "HR_MANAGER", "HR_SPECIALIST", "DEPT_MANAGER",
    "SUPERVISOR", "EMPLOYEE", "WAREHOUSE", "DRIVER",
]

VALID_LEAVE_TYPES = [
    "Annual", "Sick", "Emergency", "Unpaid",
    "Early_Departure", "Overtime_Planned", "Overtime_Emergency",
]

OFFICIAL_START_TIME = "08:00"
OFFICIAL_END_TIME = "16:00"
LATENESS_GRACE_MINUTES = 15
MAX_EARLY_DEPARTURES_PER_MONTH = 2
MAX_OT_HOURS_PER_DAY = 4
MAX_OT_HOURS_PER_MONTH = 40
OT_RATE_DEFAULT = 1.5


# ---------------------------------------------------------------------------
# 6. HELPER — get any tab as a worksheet object
# ---------------------------------------------------------------------------
def get_sheet(tab_name):
    return WORKBOOK.worksheet(tab_name)
