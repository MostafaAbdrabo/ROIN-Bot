"""
ROIN WORLD FZE — Bulk Employee Import Handler
===============================================
Phase 13:
  /import command for HR_Manager
  Accepts a CSV or tab-delimited text file (or inline CSV data)
  Validates each row and adds to Employee_DB + User_Registry

Expected CSV columns (header row required):
  Emp_Code, Full_Name, National_ID, DOB, Nationality, Phone,
  Department, Job_Title, Job_Grade, Hire_Date, Contract_Type,
  Contract_Start_Date, Contract_Expiry_Date, Manager_Code, Bot_Role,
  Preferred_Language, Annual_Leave_Balance, Saturday_Type, Shift_Hours

Auto-generated fields:
  Status = Active
  Bot_Password_Hash = bcrypt(Emp_Code)  (employee uses their code as initial password)
  Telegram_ID = blank (set on first login)
"""

import io
import csv
import bcrypt
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CommandHandler,
                           MessageHandler, CallbackQueryHandler, filters)
from config import get_sheet, VALID_ROLES, BCRYPT_SALT_ROUNDS

def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")

# ── States ────────────────────────────────────────────────────────────────────
IMPORT_FILE = 1300

# Required columns (case-insensitive match)
REQUIRED_COLS = {
    "emp_code", "full_name", "department", "job_title",
    "hire_date", "contract_type", "bot_role",
}

ALL_COLS = [
    "Emp_Code", "Full_Name", "National_ID", "DOB", "Nationality", "Phone",
    "Department", "Job_Title", "Job_Grade", "Hire_Date", "Contract_Type",
    "Contract_Start_Date", "Contract_Expiry_Date", "Probation_End_Date",
    "Contract_Status", "Days_Until_Expiry", "Manager_Code", "Telegram_ID",
    "Bot_Password_Hash", "Bot_Role", "Preferred_Language",
    "Annual_Leave_Balance", "Status", "Drive_Folder_Link", "Has_Expired_Docs",
    "Notes", "Saturday_Type", "Approval_Chain", "Supervisor_Code",
    "Shift_Hours", "Off_Type",
]


def _get_role(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[3].strip()
    return None


def _existing_codes():
    try:
        vals = get_sheet("Employee_DB").col_values(1)
        return {str(v).strip().lower() for v in vals[1:] if v}
    except Exception:
        return set()


def _hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_SALT_ROUNDS)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def _validate_row(row: dict, existing: set) -> list:
    """Return list of error strings; empty list = valid."""
    errors = []
    ec = str(row.get("emp_code","")).strip()
    if not ec:
        errors.append("Emp_Code is required")
    elif ec.lower() in existing:
        errors.append(f"Emp_Code {ec} already exists")
    if not str(row.get("full_name","")).strip():
        errors.append("Full_Name is required")
    role = str(row.get("bot_role","")).strip()
    if role and role not in VALID_ROLES:
        errors.append(f"Invalid Bot_Role: {role}")
    for df in ("hire_date","contract_start_date","contract_expiry_date","dob"):
        val = str(row.get(df,"")).strip()
        if val and val not in ("-",""):
            try: datetime.strptime(val, "%d/%m/%Y")
            except ValueError: errors.append(f"Invalid date format for {df}: {val}")
    return errors


def _build_emp_row(row: dict) -> list:
    """Map CSV dict to Employee_DB column order."""
    def g(k): return str(row.get(k.lower(),"")).strip()
    ec   = g("emp_code")
    role = g("bot_role") or "Employee"
    # Initial password = employee code
    pw_hash = _hash_password(ec)
    return [
        ec,                              # Emp_Code
        g("full_name"),                  # Full_Name
        g("national_id"),                # National_ID
        g("dob"),                        # DOB
        g("nationality"),                # Nationality
        g("phone"),                      # Phone
        g("department"),                 # Department
        g("job_title"),                  # Job_Title
        g("job_grade"),                  # Job_Grade
        g("hire_date"),                  # Hire_Date
        g("contract_type"),              # Contract_Type
        g("contract_start_date"),        # Contract_Start_Date
        g("contract_expiry_date"),       # Contract_Expiry_Date
        g("probation_end_date"),         # Probation_End_Date
        "Active",                        # Contract_Status
        "",                              # Days_Until_Expiry
        g("manager_code"),               # Manager_Code
        "",                              # Telegram_ID
        pw_hash,                         # Bot_Password_Hash
        role,                            # Bot_Role
        g("preferred_language") or "EN", # Preferred_Language
        g("annual_leave_balance") or "0",# Annual_Leave_Balance
        "Active",                        # Status
        "",                              # Drive_Folder_Link
        "",                              # Has_Expired_Docs
        g("notes"),                      # Notes
        g("saturday_type") or "Off",     # Saturday_Type
        "",                              # Approval_Chain
        g("supervisor_code"),            # Supervisor_Code
        g("shift_hours") or "8",         # Shift_Hours
        g("off_type") or "Friday",       # Off_Type
    ]


def _build_registry_row(row: dict) -> list:
    """Add minimal row to User_Registry (no Telegram_ID yet)."""
    def g(k): return str(row.get(k.lower(),"")).strip()
    ec   = g("emp_code")
    role = g("bot_role") or "Employee"
    pw_hash = _hash_password(ec)
    now  = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Columns: Emp_Code, Telegram_ID, Bot_Password_Hash, Bot_Role,
    #          Last_Login, Status, Failed_Attempts, Last_Active
    return [ec, "", pw_hash, role, "", "Active", "0", now]


def _parse_csv(text: str):
    """Parse CSV text, return (header_lower_list, list_of_dicts)."""
    reader = csv.DictReader(io.StringIO(text.strip()))
    rows   = []
    for r in reader:
        rows.append({k.strip().lower(): v.strip() for k, v in r.items()})
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    return headers, rows


# ── Command and message handlers ──────────────────────────────────────────────
async def import_cmd(update, context):
    """Entry point: /import command."""
    tid  = str(update.effective_user.id)
    role = _get_role(tid)
    if role not in ("HR_Manager",):
        await update.message.reply_text("❌ Only HR_Manager can use /import.")
        return ConversationHandler.END
    await update.message.reply_text(
        "📥 Bulk Employee Import\n\n"
        "Send a CSV file or paste CSV text.\n\n"
        "Required columns:\n"
        "Emp_Code, Full_Name, Department, Job_Title, Hire_Date, Contract_Type, Bot_Role\n\n"
        "Dates must be DD/MM/YYYY.\n"
        "Initial password = Emp_Code (employees change on first login).\n\n"
        "Send /cancel to abort.",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return IMPORT_FILE


async def import_receive_file(update, context):
    """Receive a document (CSV file)."""
    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ Please send a CSV file or paste CSV text.")
        return IMPORT_FILE
    if not (doc.file_name or "").lower().endswith(".csv"):
        await update.message.reply_text("⚠️ Please send a .csv file.")
        return IMPORT_FILE
    await update.message.reply_text("⏳ Processing file...")
    tg_file = await doc.get_file()
    data = await tg_file.download_as_bytearray()
    text = data.decode("utf-8-sig", errors="replace")
    return await _process_import(update, context, text)


async def import_receive_text(update, context):
    """Receive inline CSV text."""
    text = update.message.text.strip()
    if not text or "," not in text:
        await update.message.reply_text("⚠️ Doesn't look like CSV. Include commas.")
        return IMPORT_FILE
    await update.message.reply_text("⏳ Processing...")
    return await _process_import(update, context, text)


async def _process_import(update, context, text: str):
    """Parse, validate, and import employees."""
    try:
        headers, rows = _parse_csv(text)
    except Exception as e:
        await update.message.reply_text(f"❌ CSV parse error: {e}\n\nFix and resend.")
        return IMPORT_FILE

    if not rows:
        await update.message.reply_text("❌ No data rows found.")
        return IMPORT_FILE

    # Check required columns
    missing_cols = REQUIRED_COLS - set(headers)
    if missing_cols:
        await update.message.reply_text(
            f"❌ Missing required columns: {', '.join(sorted(missing_cols))}\n\nFix header and resend."
        )
        return IMPORT_FILE

    existing = _existing_codes()

    # Validate all rows first (fail-fast)
    all_errors = []
    for i, row in enumerate(rows, start=2):  # row 1 = header
        errs = _validate_row(row, existing)
        if errs:
            for e in errs:
                all_errors.append(f"Row {i}: {e}")

    if all_errors:
        msg = f"❌ Validation failed ({len(all_errors)} errors):\n\n"
        msg += "\n".join(all_errors[:20])
        if len(all_errors) > 20:
            msg += f"\n... +{len(all_errors)-20} more"
        msg += "\n\nFix and resend."
        await update.message.reply_text(msg)
        return IMPORT_FILE

    # All valid — import
    emp_ws = get_sheet("Employee_DB")
    reg_ws = get_sheet("User_Registry")
    success = 0; failed = []

    for row in rows:
        try:
            emp_row = _build_emp_row(row)
            reg_row = _build_registry_row(row)
            emp_ws.append_row(emp_row, value_input_option="USER_ENTERED")
            reg_ws.append_row(reg_row, value_input_option="USER_ENTERED")
            existing.add(str(row.get("emp_code","")).strip().lower())
            success += 1
        except Exception as e:
            failed.append(f"{row.get('emp_code','?')}: {e}")

    msg = (f"✅ Import Complete!\n{'─'*24}\n"
           f"Imported:   {success}\n"
           f"Skipped:    {len(failed)}")
    if failed:
        msg += f"\n\nFailed rows:\n" + "\n".join(failed[:10])
        if len(failed) > 10:
            msg += f"\n... +{len(failed)-10} more"
    msg += f"\n\nInitial password for each employee = their Emp_Code."
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def import_cancel(update, context):
    await update.message.reply_text("Import cancelled.")
    return ConversationHandler.END


# ── Handler registration ──────────────────────────────────────────────────────
def get_bulk_import_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("import", import_cmd)],
        states={
            IMPORT_FILE: [
                MessageHandler(filters.Document.MimeType("text/csv"), import_receive_file),
                MessageHandler(filters.Document.FileExtension("csv"), import_receive_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, import_receive_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", import_cancel)],
        per_message=False,
    )
