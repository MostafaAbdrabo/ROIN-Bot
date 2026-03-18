"""
ROIN WORLD FZE — Telegram HR Bot
=================================
Full login flow + role-based inline menus.

  /start → employee code → password → inline menu based on job title

Your User_Registry Bot_Role column contains job titles like "Director",
"HR manager", etc. This bot maps each title to the correct menu.
"""

# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------

import asyncio
import bcrypt
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import (
    BOT_TOKEN,
    get_sheet,
    TAB_USER_REGISTRY,
    TAB_EMPLOYEE_DB,
    MAX_FAILED_ATTEMPTS,
)

# ---------------------------------------------------------------------------
# CONVERSATION STATES
# ---------------------------------------------------------------------------

WAITING_FOR_EMP_CODE = 0
WAITING_FOR_PASSWORD = 1


# ---------------------------------------------------------------------------
# MENU DEFINITIONS — mapped to job titles in your User_Registry
# ---------------------------------------------------------------------------

# Each menu is a list of (button_label, callback_data) pairs.
# callback_data is what the bot receives when the button is tapped.

MENU_EMPLOYEE = [
    [("My Leave Balance", "menu_leave_balance"), ("Request Leave", "menu_request_leave")],
    [("My Attendance", "menu_my_attendance"), ("My Profile", "menu_my_profile")],
    [("Help", "menu_help")],
]

MENU_DEPT_MANAGER = [
    [("My Leave Balance", "menu_leave_balance"), ("Request Leave", "menu_request_leave")],
    [("Pending Approvals", "menu_pending_approvals"), ("My Team Attendance", "menu_team_attendance")],
    [("Assign Tasks", "menu_assign_tasks"), ("My Profile", "menu_my_profile")],
    [("Help", "menu_help")],
]

MENU_HR = [
    [("All Leave Requests", "menu_all_leave"), ("Employee Lookup", "menu_emp_lookup")],
    [("Attendance Overview", "menu_attendance_overview"), ("Pending Approvals", "menu_pending_approvals")],
    [("Generate Letters", "menu_gen_letters"), ("Announcements", "menu_announcements")],
    [("Admin Functions", "menu_admin"), ("My Profile", "menu_my_profile")],
    [("Help", "menu_help")],
]

MENU_DIRECTOR = [
    [("Pending Decisions", "menu_pending_decisions"), ("Company Overview", "menu_company_overview")],
    [("Employee Lookup", "menu_emp_lookup"), ("Reports", "menu_reports")],
    [("Help", "menu_help")],
]

# Map your actual job titles (from User_Registry Bot_Role column) → menus
TITLE_TO_MENU = {
    "Director":                 MENU_DIRECTOR,
    "Director of the branch":   MENU_DIRECTOR,
    "Catering Director":        MENU_DEPT_MANAGER,
    "HR manager":               MENU_HR,
    "Leading Engineer of PTD":  MENU_HR,
    "IT manager":               MENU_DEPT_MANAGER,
    "Translator":               MENU_EMPLOYEE,
    "Accountant":               MENU_EMPLOYEE,
    "Deputy Chief Accountant":  MENU_EMPLOYEE,
    "Secretary":                MENU_EMPLOYEE,
}


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def log(msg):
    """Print a timestamped message to terminal."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def build_inline_menu(role):
    """
    Convert a menu definition into an InlineKeyboardMarkup.
    Falls back to MENU_EMPLOYEE if the role/title isn't mapped.
    """
    menu_def = TITLE_TO_MENU.get(role, MENU_EMPLOYEE)
    keyboard = []
    for row in menu_def:
        keyboard.append([
            InlineKeyboardButton(text=label, callback_data=data)
            for label, data in row
        ])
    return InlineKeyboardMarkup(keyboard)


def find_user_in_registry(emp_code):
    """
    Look up an employee code in the User_Registry tab.
    Returns (row_number, row_data) if found, or (None, None) if not.

    User_Registry columns:
      A=Emp_Code, B=Telegram_ID, C=Password_Hash, D=Bot_Role,
      E=Registration_Date, F=Status, G=Failed_Attempts, H=Last_Access
    """
    ws = get_sheet(TAB_USER_REGISTRY)
    all_rows = ws.get_all_values()

    for idx, row in enumerate(all_rows):
        if idx == 0:
            continue
        if row[0].strip() == emp_code.strip():
            return idx + 1, row

    return None, None


def find_employee_name(emp_code):
    """
    Look up employee name and department from Employee_DB.
    Returns (full_name, department) or ("Unknown", "Unknown").
    """
    ws = get_sheet(TAB_EMPLOYEE_DB)
    all_rows = ws.get_all_values()

    for idx, row in enumerate(all_rows):
        if idx == 0:
            continue
        if row[0].strip() == emp_code.strip():
            full_name = row[1] if len(row) > 1 else "Unknown"
            department = row[6] if len(row) > 6 else "Unknown"
            return full_name, department

    return "Unknown", "Unknown"


# ---------------------------------------------------------------------------
# LOGIN HANDLERS
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start — Entry point.
    If Telegram ID already linked → welcome back + menu.
    If not → ask for employee code.
    """
    telegram_id = str(update.effective_user.id)
    log(f"/start from {update.effective_user.first_name} (ID: {telegram_id})")

    ws = get_sheet(TAB_USER_REGISTRY)
    all_rows = ws.get_all_values()

    for idx, row in enumerate(all_rows):
        if idx == 0:
            continue
        if row[1].strip() == telegram_id:
            emp_code = row[0]
            role = row[3]
            status = row[5] if len(row) > 5 else "Active"

            if status == "Terminated":
                await update.message.reply_text(
                    "Your account has been deactivated. Contact HR."
                )
                log(f"BLOCKED: {emp_code} — terminated")
                return ConversationHandler.END

            if status == "Locked":
                await update.message.reply_text(
                    "Your account is locked. Contact HR to unlock."
                )
                log(f"BLOCKED: {emp_code} — locked")
                return ConversationHandler.END

            full_name, department = find_employee_name(emp_code)

            # Update Last_Access
            row_num = idx + 1
            ws.update_cell(row_num, 8, datetime.now().strftime("%d/%m/%Y %H:%M"))

            await update.message.reply_text(
                f"Welcome back, {full_name}!\n"
                f"Department: {department}\n"
                f"Role: {role}",
                reply_markup=ReplyKeyboardRemove(),
            )
            await update.message.reply_text(
                "Choose an option:",
                reply_markup=build_inline_menu(role),
            )
            log(f"Welcome back: {emp_code} ({full_name}) — {role}")
            return ConversationHandler.END

    # Not found — new user
    await update.message.reply_text(
        "Welcome to ROIN WORLD FZE HR System.\n"
        "Please enter your employee code to begin:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOR_EMP_CODE


async def receive_emp_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed their employee code."""
    emp_code = update.message.text.strip()
    telegram_id = str(update.effective_user.id)
    log(f"Employee code entered: {emp_code} (by Telegram ID: {telegram_id})")

    row_num, row_data = find_user_in_registry(emp_code)

    if row_num is None:
        await update.message.reply_text(
            "Employee code not found. Contact HR.\n"
            "To try again, send /start"
        )
        log(f"REJECTED: {emp_code} — not found")
        return ConversationHandler.END

    status = row_data[5] if len(row_data) > 5 else "Active"

    if status == "Terminated":
        await update.message.reply_text("This account has been deactivated. Contact HR.")
        log(f"REJECTED: {emp_code} — terminated")
        return ConversationHandler.END

    if status == "Locked":
        await update.message.reply_text(
            "This account is locked due to too many failed attempts.\n"
            "Contact HR to unlock."
        )
        log(f"REJECTED: {emp_code} — locked")
        return ConversationHandler.END

    existing_telegram_id = row_data[1].strip() if len(row_data) > 1 else ""
    if existing_telegram_id and existing_telegram_id != telegram_id:
        await update.message.reply_text(
            "This employee code is already linked to another Telegram account.\n"
            "Contact HR if this is an error."
        )
        log(f"REJECTED: {emp_code} — linked to different ID")
        return ConversationHandler.END

    context.user_data["emp_code"] = emp_code
    context.user_data["registry_row"] = row_num

    await update.message.reply_text("Please enter your password:")
    return WAITING_FOR_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed their password. Verify with bcrypt."""
    password = update.message.text.strip()
    emp_code = context.user_data.get("emp_code", "")
    row_num = context.user_data.get("registry_row", 0)
    telegram_id = str(update.effective_user.id)

    # Delete password message for security
    try:
        await update.message.delete()
    except Exception:
        pass

    ws = get_sheet(TAB_USER_REGISTRY)
    row_data = ws.row_values(row_num)

    stored_hash = row_data[2] if len(row_data) > 2 else ""

    if not stored_hash:
        await update.effective_chat.send_message(
            "No password set for your account. Contact HR."
        )
        log(f"FAIL: {emp_code} — no hash")
        return ConversationHandler.END

    try:
        password_matches = bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8")
        )
    except Exception as e:
        log(f"BCRYPT ERROR for {emp_code}: {e}")
        await update.effective_chat.send_message("Authentication error. Contact HR.")
        return ConversationHandler.END

    if not password_matches:
        failed = int(row_data[6]) if len(row_data) > 6 and row_data[6].isdigit() else 0
        failed += 1
        ws.update_cell(row_num, 7, str(failed))

        log(f"WRONG PASSWORD: {emp_code} — attempt {failed}/{MAX_FAILED_ATTEMPTS}")

        if failed >= MAX_FAILED_ATTEMPTS:
            ws.update_cell(row_num, 6, "Locked")
            await update.effective_chat.send_message(
                "Account locked after 3 failed attempts.\nContact HR to unlock."
            )
            log(f"LOCKED: {emp_code}")
            return ConversationHandler.END

        remaining = MAX_FAILED_ATTEMPTS - failed
        await update.effective_chat.send_message(
            f"Incorrect password. {remaining} attempt(s) remaining.\n"
            "Please enter your password:"
        )
        return WAITING_FOR_PASSWORD

    # --- PASSWORD CORRECT ---
    full_name, department = find_employee_name(emp_code)
    role = row_data[3] if len(row_data) > 3 else ""

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws.update_cell(row_num, 2, telegram_id)
    ws.update_cell(row_num, 5, now)
    ws.update_cell(row_num, 6, "Active")
    ws.update_cell(row_num, 7, "0")
    ws.update_cell(row_num, 8, now)

    log(f"LOGIN SUCCESS: {emp_code} ({full_name}) — ID {telegram_id}")

    await update.effective_chat.send_message(
        f"Login successful!\n\n"
        f"Welcome, {full_name}\n"
        f"Department: {department}\n"
        f"Role: {role}",
    )
    await update.effective_chat.send_message(
        "Choose an option:",
        reply_markup=build_inline_menu(role),
    )
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/cancel — Exit login flow."""
    await update.message.reply_text(
        "Login cancelled. Send /start to try again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    log(f"/cancel from {update.effective_user.first_name}")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# MENU BUTTON HANDLER
# ---------------------------------------------------------------------------

async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles all inline menu button taps.
    For now, just confirms which button was pressed.
    We will add real functionality in later steps.
    """
    query = update.callback_query
    await query.answer()  # Remove the "loading" spinner on the button

    # Map callback_data to a friendly name
    button_labels = {
        "menu_leave_balance":       "My Leave Balance",
        "menu_request_leave":       "Request Leave",
        "menu_my_attendance":       "My Attendance",
        "menu_my_profile":          "My Profile",
        "menu_help":                "Help",
        "menu_pending_approvals":   "Pending Approvals",
        "menu_team_attendance":     "My Team Attendance",
        "menu_assign_tasks":        "Assign Tasks",
        "menu_all_leave":           "All Leave Requests",
        "menu_emp_lookup":          "Employee Lookup",
        "menu_attendance_overview": "Attendance Overview",
        "menu_gen_letters":         "Generate Letters",
        "menu_announcements":       "Announcements",
        "menu_admin":               "Admin Functions",
        "menu_pending_decisions":   "Pending Decisions",
        "menu_company_overview":    "Company Overview",
        "menu_reports":             "Reports",
    }

    data = query.data
    label = button_labels.get(data, data)

    await query.edit_message_text(
        f"You selected: {label}\n\n"
        f"This feature is coming soon.\n"
        f"Send /start to go back to the menu."
    )
    log(f"Menu tap: {label} (by {query.from_user.first_name})")


# ---------------------------------------------------------------------------
# ERROR HANDLER
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Catches unexpected errors so the bot doesn't crash."""
    log(f"ERROR: {context.error}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

async def main():
    print("=" * 50)
    print("ROIN WORLD FZE — HR Bot Starting...")
    print("=" * 50)

    app = Application.builder().token(BOT_TOKEN).build()

    # Login conversation flow
    login_flow = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WAITING_FOR_EMP_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_emp_code)
            ],
            WAITING_FOR_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    app.add_handler(login_flow)

    # Handle all inline menu button taps
    app.add_handler(CallbackQueryHandler(menu_button_handler))

    app.add_error_handler(error_handler)

    print("Bot is running. Press Ctrl+C to stop.")
    print("=" * 50)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
