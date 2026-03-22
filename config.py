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
TAB_MEMO_LOG = "Memo_Log"
TAB_NOTIFICATIONS = "Notifications"
TAB_HIRING_REQUESTS = "Hiring_Requests"
TAB_JOB_POSTINGS    = "Job_Postings"
TAB_CANDIDATES      = "Candidates"
TAB_ONBOARDING      = "Onboarding_Checklist"
TAB_TRANSPORT_REQUESTS = "Transport_Requests"
TAB_COMMUTE_LOG        = "Commute_Log"
TAB_VEHICLES           = "Vehicles"


# ---------------------------------------------------------------------------
# 5. COMPANY SETTINGS
# ---------------------------------------------------------------------------
MAX_USERS = 50
CURRENT_ATTENDANCE_TAB = "Copy of 3-K"   # Update this each month
MAX_FAILED_ATTEMPTS = 3
BCRYPT_SALT_ROUNDS = 12

VALID_ROLES = [
    "Bot_Manager",
    "Director",
    "HR_Manager", "HR_Staff",
    "Direct_Manager", "Supervisor", "Employee",
    "Warehouse", "Warehouse_Manager", "Warehouse_Specialist", "Store_Keeper",
    "Driver", "Transport_Manager",
    "Supply_Manager", "Supply_Specialist",
    "Safety_Manager",
    "Translation_Manager", "Translator",
    "Operations_Manager", "Operations_Specialist", "Operations_Coordinator",
    "Quality_Manager", "Quality_Specialist",
    "Housing_Manager", "Housing_Specialist",
    "Packaging_Manager", "Packaging_Specialist",
]

VALID_LEAVE_TYPES = [
    "Paid", "Sick", "Emergency", "Unpaid", "Business_Trip",
    "Early_Departure", "Overtime_Planned", "Overtime_Emergency", "Missing_Punch",
]

OFFICIAL_START_TIME = "08:00"
OFFICIAL_END_TIME = "16:00"
LATENESS_GRACE_MINUTES = 15
MAX_EARLY_DEPARTURES_PER_MONTH = 2
MAX_OT_HOURS_PER_DAY = 4
MAX_OT_HOURS_PER_MONTH = 40
OT_RATE_DEFAULT = 1.5


# ---------------------------------------------------------------------------
# 6. DRIVE FOLDER IDs — for auto-upload
# ---------------------------------------------------------------------------
DRIVE_FOLDERS = {
    # ── HR Leave ──
    "hr_leave_pending":           "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "hr_leave_approved":          "1Wr1DfpxD3vYnmr8jEamZu1Zy7MU_Cr43",
    # ── HR Memos ──
    "hr_memos_pending":           "1g8kCuwLMXdl5ZioUQSbSQzYkP235DFZL",
    "hr_memos_approved":          "15wgrvLOe1Ru60t7TKHFpQqSXCBVtuCLp",
    # ── HR Warnings ──
    "hr_warnings_pending":        "1pA_l_Nnh5lZ08g5V2y0fWVnTTETQjfx8",
    "hr_warnings_approved":       "1JN-T-S0Pc3BHfWtNULbOiJGF3kNnZIer",
    # ── HR Deductions & Bonuses ──
    "hr_deductions_pending":      "164igINEAOdJ9wDkMqeUiTQZmKwr-Phc0",
    "hr_deductions_approved":     "1eZFetwUPTLj9vU1NrKwWnqlxQAB0cy5j",
    # ── HR Salary Advance ──
    "hr_advance_pending":         "1s_haEeB7x8q-WqkAPc0ZLhdchekTwKs1",
    "hr_advance_approved":        "13hgyFGFPYl5BIs91OpTYBOknsveeXyQ7",
    # ── HR Clearance ──
    "hr_clearance_pending":       "1fKWYQdyEWnzFIS1a6baarGHmpZMB0JvG",
    "hr_clearance_approved":      "13k5QONued8IUFCQUtB_3Zm4rx-wiZxFQ",
    # ── HR Certificates ──
    "hr_certificates_pending":    "1B8BBjCrUK2SUo6jXmbjB-9Q41gY4V1tA",
    "hr_certificates_approved":   "1VjYFI10cLojVUOZR6vuxynbKz76g2JzB",
    # ── HR Evaluations ──
    "hr_evaluations_pending":     "1p0XINtKKS-Vrg4BkY8DlYJYmILrJiiBf",
    "hr_evaluations_approved":    "1tA3IWgyi-9S8e42W_CMVv4dNSdENdpUq",
    # ── Warehouse ──
    "warehouse_pending":          "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "warehouse_approved":         "1GfSUmyBHKES0O1wAve22_PBkvfYDzB-C",
    # ── Translation ──
    "translation_pending":        "1IjBVhPSfJpewzAJkNvgPA3tpCWoxvzRe",
    "translation_approved":       "1CKR3_Uo8oA0C70p7RFGloGy29iH6l5Ib",
    # ── Operations ──
    "operations_pending":         "1jXCdwUcfrLnc0nIhMpt1-o7KCYGyOITZ",
    "operations_approved":        "1Q819q6JQoT8T8aPNoYOrwhcYvoSyWTa7",
    # ── Packaging & Delivery ──
    "packaging_pending":          "1DAhAJr-m83T_eciaAHlAQlxB4VdTi0fr",
    "packaging_approved":         "1YUYfof-t_wDfhuyN3eTWjORNUD-yZKAE",
    # ── Purchasing ──
    "purchasing_pending":         "1OVKS4LC6j5x0BB8w5hYfvROs6425Q4wR",
    "purchasing_approved":        "1dfT_ltnPCsKApgu6i4-iOhcAopxByETc",
    # ── Quality Control ──
    "quality_pending":            "1FowBChZdpmIcQE9hPbLUFLHiArrnHrj2",
    "quality_approved":           "1qtbXInecUhBKu4Uyhv8HoeLFV4l3XuQV",
    # ── Housing ──
    "housing_pending":            "1LG08YDtU4MwJJSl4AbFhbV4PH6e_142j",
    "housing_approved":           "1tEbhKgmDKUGEwuQb0XtLsgEJoPsDnUVO",
    # ── Transport ──
    "transport_pending":          "1KpswSke5iljbUO-HjeZpFG8cCHWR9X5n",
    "transport_approved":         "10gMKjUWaoYfFMgGGjNFo9pLUHWYjtLTA",
    # ── Recruitment ──
    "recruitment_pending":        "1lSHMZircVL183zpvZfza2kddvB_jsplq",
    "recruitment_approved":       "1YthuuMAcEZ9FMtggszVVvliqPz2cBV-E",
    # ── Job Descriptions ──
    "jd_pending":                 "1SRScmun5KKMVzXV9RknE2BqhkWVXOrUt",
    "jd_approved":                "1c2eoj7HNnjB-YsqCZ3n4_NsY9-6TMh_v",
    # ── Legacy aliases (backward compatibility) ──
    "drafts":                     "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "approved":                   "1GfSUmyBHKES0O1wAve22_PBkvfYDzB-C",
    "in_process":                 "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "memo_drafts":                "1g8kCuwLMXdl5ZioUQSbSQzYkP235DFZL",
    "memo_approved":              "15wgrvLOe1Ru60t7TKHFpQqSXCBVtuCLp",
    "leave_approvals":            "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "leave_orders":               "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "job_descriptions":           "1SRScmun5KKMVzXV9RknE2BqhkWVXOrUt",
    "certificates":               "1B8BBjCrUK2SUo6jXmbjB-9Q41gY4V1tA",
    "evaluations":                "1p0XINtKKS-Vrg4BkY8DlYJYmILrJiiBf",
    "requisitions":               "1lSHMZircVL183zpvZfza2kddvB_jsplq",
    "safety_reports":             "1jXCdwUcfrLnc0nIhMpt1-o7KCYGyOITZ",
    "transport_requests":         "1KpswSke5iljbUO-HjeZpFG8cCHWR9X5n",
}


# ---------------------------------------------------------------------------
# 7. HELPER — get any tab as a worksheet object
# ---------------------------------------------------------------------------
def get_sheet(tab_name):
    return WORKBOOK.worksheet(tab_name)
