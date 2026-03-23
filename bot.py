"""
ROIN WORLD FZE — HR Bot v14.0
==============================
Roles (16): Employee, Supervisor, Direct_Manager, HR_Staff, HR_Manager, Director,
            Warehouse, Driver, Transport_Manager, Supply_Manager,
            Safety_Manager, Translation_Manager, Translator,
            Operations_Manager, Quality_Manager, Housing_Manager
All sections complete.
"""

import asyncio, bcrypt
from datetime import datetime, date as date_type
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters)
from config import BOT_TOKEN, get_sheet, TAB_USER_REGISTRY, TAB_EMPLOYEE_DB, MAX_FAILED_ATTEMPTS
from leave_request import (get_leave_conversation_handler, leave_balance_handler,
    my_requests_handler, myreq_list, team_requests_handler, teamreq_list,
    request_view_handler, pdf_download_handler, get_team_request_handler)
from approval_handler import (get_approval_handlers, pending_approvals_handler,
    pending_category_handler, pending_view_handler, back_to_menu_handler)
from jd_handler import get_jd_create_handler, get_jd_hr_handler, get_jd_manager_dir_handler
from attendance_handler import (
    attendance_menu, att_summary_placeholder,
    get_attendance_conversation_handler, get_upload_conversation_handler,
    my_attendance_handler,
    att_own_handler, att_own_year_handler, att_own_month_handler,
    att_team_handler, att_team_emp_handler, att_team_year_handler, att_team_month_handler,
    att_comp_handler, att_comp_dept_handler, att_comp_emp_handler,
    att_comp_year_handler, att_comp_month_handler)
from missing_punch import get_missing_punch_handler
from faq_handler import get_faq_handlers
from cert_handler import (cert_menu_handler, get_cert_handler, get_cert_static_handlers)
from contact_hr_handler import (get_contact_hr_handler, get_hr_chr_reply_handler,
    hr_messages_menu, hr_chr_list, hr_chr_view)
from manager_handler import get_manager_handlers
from hr_tools_handler import (get_emp_lookup_handler, get_admin_handler,
    get_hr_tools_handlers)
from doc_contract_handler import (get_doc_add_handler, get_contract_log_handler,
    get_doc_contract_static_handlers)
from announcement_handler import get_ann_create_handler, get_ann_static_handlers
from report_handler import get_report_handlers
from eval_handler import get_eval_handler, get_eval_static_handlers
from warehouse_handler import get_wh_tx_handler, get_wh_static_handlers
from vehicles_handler import get_vehicle_handlers, get_vehicle_static_handlers
from supply_handler import get_supply_handlers, get_supply_static_handlers
from bulk_import_handler import get_bulk_import_handler
from safety_handler import get_safety_handlers, get_safety_static_handlers
from translation_handler import get_translation_handlers, get_translation_static_handlers
from operations_handler import get_operations_handlers, get_operations_static_handlers
from quality_handler import get_quality_handlers, get_quality_static_handlers
from housing_handler import get_housing_handlers, get_housing_static_handlers
from director_handler import get_director_handlers
from schedule_handler import (get_schedule_handlers, get_schedule_static_handlers,
    sched_menu_handler)
from feedback_handler import (get_feedback_handler, get_fb_static_handlers,
    get_fb_mgr_handler, fb_menu_start)
from signature_handler import get_sig_setup_handler, get_sig_static_handlers
from notification_handler import get_notif_handlers, get_unread_count
from memo_handler import get_memo_handlers
from recruitment_handler import get_recruitment_handlers, get_recruitment_static_handlers
from search_handler import get_search_handler
from requests_menu import get_requests_handlers
from regen_pdfs_handler import get_regen_handler
from transport_handler import (get_transport_handlers, get_transport_static_handlers,
                               transport_menu_handler, handle_location_update, check_overdue_trips)
from generic_request_engine import build_all_request_handlers
from task_handler import get_task_handlers, get_task_static_handlers, check_overdue_tasks
from employee_reports_handler import get_reports_static_handlers
from employee_files_handler import get_emp_files_handlers, get_emp_files_static_handlers
from bulk_export_handler import get_bulk_export_handlers

W_CODE = 0; W_PASS = 1

MENU_EMPLOYEE = [
    [("🔔 Notifications", "menu_notifications")],
    [("📋 Requests", "menu_requests")],
    [("🕐 Attendance", "menu_my_attendance"), ("👤 My Profile", "menu_my_profile")],
    [("📜 Certificates", "menu_certificates"), ("💬 Contact HR", "menu_contact_hr")],
    [("🚗 Request Vehicle", "menu_transport"), ("🏠 My Housing", "menu_housing")],
    [("📁 My Documents", "my_documents"), ("🤝 Refer a Candidate", "rec_refer")],
    [("📬 Bot Feedback", "menu_bot_feedback"), ("❓ Help", "menu_help")],
]
MENU_SUPERVISOR = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("📋 Requests", "menu_requests")],
    [("👥 My Team", "menu_team"), ("🕐 Attendance", "menu_my_attendance")],
    [("👤 My Profile", "menu_my_profile"), ("📜 Certificates", "menu_certificates")],
    [("📅 Monthly Schedule", "menu_schedule"), ("🚗 Request Vehicle", "menu_transport")],
    [("🤝 Refer a Candidate", "rec_refer")],
    [("💬 Contact HR", "menu_contact_hr"), ("📬 Bot Feedback", "menu_bot_feedback")],
    [("❓ Help", "menu_help")],
]
MENU_DIRECT_MANAGER = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("📋 Requests", "menu_requests")],
    [("🕐 Attendance", "menu_my_attendance"), ("🔔 Pending Approvals", "menu_pending_approvals")],
    [("👥 My Team", "menu_team"), ("📄 Job Descriptions", "menu_jd")],
    [("📅 Monthly Schedule", "menu_schedule"), ("🛒 Purchase Request", "menu_supply")],
    [("📌 Assign Tasks", "menu_assign_tasks"), ("🚗 Request Vehicle", "menu_transport")],
    [("👤 My Profile", "menu_my_profile"), ("📜 Certificates", "menu_certificates")],
    [("👔 Recruitment", "menu_recruitment")],
    [("💬 Contact HR", "menu_contact_hr"), ("❓ Help", "menu_help")],
]
MENU_HR_STAFF = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("📋 Requests", "menu_requests")],
    [("🕐 Attendance", "menu_my_attendance"), ("👥 My Team", "menu_team")],
    [("📄 Job Descriptions", "menu_jd"), ("🛠️ HR Tools", "menu_hr_tools")],
    [("💬 HR Messages", "menu_hr_messages"), ("👔 Recruitment", "menu_recruitment")],
    [("📁 Employee Files", "emp_files_menu"), ("🔍 Search Documents", "menu_search")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_HR_MANAGER = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("📋 Requests", "menu_requests")],
    [("🕐 Attendance", "menu_my_attendance"), ("🔔 Pending Approvals", "menu_pending_approvals")],
    [("👥 My Team", "menu_team"), ("📄 Job Descriptions", "menu_jd")],
    [("🛠️ HR Tools", "menu_hr_tools"), ("⚙️ Admin", "menu_admin")],
    [("📅 Monthly Schedule", "menu_schedule"), ("💬 HR Messages", "menu_hr_messages")],
    [("👔 Recruitment", "menu_recruitment"), ("📬 Bot Feedback", "menu_bot_feedback")],
    [("📁 Employee Files", "emp_files_menu"), ("📚 Bulk PDF Export", "bulk_export_menu")],
    [("🔍 Search Documents", "menu_search")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_DIRECTOR = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("📋 Requests", "menu_requests"), ("🔔 Pending Approvals", "menu_pending_approvals")],
    [("📄 Job Descriptions", "menu_jd"), ("🏢 Overview", "menu_overview")],
    [("📊 Morning Brief", "menu_director_brief"), ("✅ Batch Approvals", "menu_batch_approvals")],
    [("📅 Monthly Schedule", "menu_schedule"), ("🚗 Fleet / Vehicles", "menu_vehicles")],
    [("👔 Recruitment", "menu_recruitment"), ("📬 Bot Feedback", "menu_bot_feedback")],
    [("📁 Employee Files", "emp_files_menu"), ("📚 Bulk PDF Export", "bulk_export_menu")],
    [("🔍 Search Documents", "menu_search")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_WAREHOUSE = [
    [("🔔 Notifications", "menu_notifications")],
    [("📦 Stock IN", "wh_in"), ("📤 Stock OUT", "wh_out")],
    [("🔄 Transfer", "wh_xfer"), ("🗑 Waste/Damage", "wh_waste")],
    [("📊 Inventory", "wh_inventory"), ("⚠️ Low Stock", "wh_low_stock")],
    [("🚗 Request Vehicle", "menu_transport"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_DRIVER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🚗 Vehicles & Trips", "menu_transport")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_TRANSPORT_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🚗 Vehicles & Trips", "menu_transport")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_SUPPLY_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🛒 Purchase Requests", "menu_supply"), ("📊 Supply Report", "menu_supply_report")],
    [("🏭 Supplier DB", "menu_supplier_db"), ("💰 Budget Tracker", "menu_budget_tracker")],
    [("📦 Warehouse", "menu_warehouse"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_SAFETY_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🦺 Safety Menu", "menu_safety")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_TRANSLATION_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🌐 Translation Menu", "menu_translation")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_TRANSLATOR = [
    [("🔔 Notifications", "menu_notifications")],
    [("🌐 Translation Menu", "menu_translation")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_OPERATIONS_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🍳 Operations Menu", "menu_operations")],
    [("🚗 Request Vehicle", "menu_transport"), ("📋 Requests", "menu_requests")],
    [("👤 My Profile", "menu_my_profile"), ("❓ Help", "menu_help")],
]
MENU_QUALITY_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("✅ Quality Menu", "menu_quality")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_HOUSING_MANAGER = [
    [("🔔 Notifications", "menu_notifications")],
    [("🏠 Housing Menu", "menu_housing")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]

# Specialist/Coordinator roles — same as manager but no approval authority
MENU_WAREHOUSE_MANAGER    = MENU_WAREHOUSE
MENU_WAREHOUSE_SPECIALIST = MENU_WAREHOUSE
MENU_STORE_KEEPER         = MENU_WAREHOUSE
MENU_SUPPLY_SPECIALIST    = [
    [("🔔 Notifications", "menu_notifications")],
    [("🛒 Purchase Requests", "menu_supply")],
    [("📋 Requests", "menu_requests"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help", "menu_help")],
]
MENU_OPERATIONS_SPECIALIST  = MENU_OPERATIONS_MANAGER
MENU_OPERATIONS_COORDINATOR = MENU_OPERATIONS_MANAGER
MENU_QUALITY_SPECIALIST     = MENU_QUALITY_MANAGER
MENU_HOUSING_SPECIALIST     = MENU_HOUSING_MANAGER

# Bot_Manager — superuser role with categorical sub-menus
MENU_BOT_MANAGER = [
    [("🔔 Notifications", "menu_notifications"), ("📝 Memos", "menu_memos")],
    [("🏖️ Leave & HR",        "bm_hr"),       ("🔔 Approvals",     "bm_approvals")],
    [("👥 Teams",             "bm_teams"),     ("📊 Reports",       "bm_reports")],
    [("📅 Monthly Schedule",  "bm_schedule"),  ("📦 Warehouse",     "bm_warehouse")],
    [("🚗 Transport",         "bm_transport"), ("⚠️ Safety",        "bm_safety")],
    [("🌐 Translation",       "bm_translation"),("🍽️ Operations",   "bm_operations")],
    [("🔍 Quality",           "bm_quality"),   ("🛒 Purchasing",    "bm_supply")],
    [("🏠 Housing",           "bm_housing"),   ("⚙️ System Admin",  "bm_system")],
    [("👔 Recruitment",       "bm_recruitment"),("💬 Feedback Mgmt", "bm_feedback")],
    [("🔍 Search Documents",  "menu_search")],
    [("📬 Bot Feedback",      "menu_bot_feedback"), ("👤 My Profile", "menu_my_profile")],
    [("❓ Help",              "menu_help")],
]

ROLE_TO_MENU = {
    "Bot_Manager":            MENU_BOT_MANAGER,
    "Employee":               MENU_EMPLOYEE,
    "Supervisor":             MENU_SUPERVISOR,
    "Direct_Manager":         MENU_DIRECT_MANAGER,
    "HR_Staff":               MENU_HR_STAFF,
    "HR_Manager":             MENU_HR_MANAGER,
    "Director":               MENU_DIRECTOR,
    "Warehouse":              MENU_WAREHOUSE,
    "Warehouse_Manager":      MENU_WAREHOUSE_MANAGER,
    "Warehouse_Specialist":   MENU_WAREHOUSE_SPECIALIST,
    "Store_Keeper":           MENU_STORE_KEEPER,
    "Driver":                 MENU_DRIVER,
    "Transport_Manager":      MENU_TRANSPORT_MANAGER,
    "Supply_Manager":         MENU_SUPPLY_MANAGER,
    "Supply_Specialist":      MENU_SUPPLY_SPECIALIST,
    "Safety_Manager":         MENU_SAFETY_MANAGER,
    "Translation_Manager":    MENU_TRANSLATION_MANAGER,
    "Translator":             MENU_TRANSLATOR,
    "Operations_Manager":     MENU_OPERATIONS_MANAGER,
    "Operations_Specialist":  MENU_OPERATIONS_SPECIALIST,
    "Operations_Coordinator": MENU_OPERATIONS_COORDINATOR,
    "Quality_Manager":        MENU_QUALITY_MANAGER,
    "Quality_Specialist":     MENU_QUALITY_SPECIALIST,
    "Housing_Manager":        MENU_HOUSING_MANAGER,
    "Housing_Specialist":     MENU_HOUSING_SPECIALIST,
}

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

def build_inline_menu(role, notif_count=0):
    rows = ROLE_TO_MENU.get(role, MENU_EMPLOYEE)
    kb = []
    for row in rows:
        kb_row = []
        for label, data in row:
            if data == "menu_notifications" and notif_count > 0:
                label = f"🔔 Notifications ({notif_count})"
            kb_row.append(InlineKeyboardButton(text=label, callback_data=data))
        kb.append(kb_row)
    return InlineKeyboardMarkup(kb)

def find_user(ec):
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[0].strip() == ec.strip(): return i + 1, r
    return None, None

def find_name(ec):
    for i, r in enumerate(get_sheet(TAB_EMPLOYEE_DB).get_all_values()):
        if i == 0: continue
        if r[0].strip() == ec.strip():
            return (r[1] if len(r) > 1 else "?", r[6] if len(r) > 6 else "?")
    return "?", "?"

async def start_cmd(update: Update, context):
    tid = str(update.effective_user.id); log(f"/start {update.effective_user.first_name} ({tid})")
    ws = get_sheet(TAB_USER_REGISTRY)
    for i, r in enumerate(ws.get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid:
            ec, role, st = r[0], r[3], r[5] if len(r) > 5 else "Active"
            if st == "Terminated": await update.message.reply_text("Deactivated."); return ConversationHandler.END
            if st == "Locked": await update.message.reply_text("Locked."); return ConversationHandler.END
            n, d = find_name(ec); ws.update_cell(i+1, 8, datetime.now().strftime("%d/%m/%Y %H:%M"))
            unread = 0
            try: unread = get_unread_count(ec)
            except Exception: pass
            await update.message.reply_text(f"Welcome back, {n}!\nDepartment: {d}\nRole: {role}", reply_markup=ReplyKeyboardRemove())
            if unread > 0:
                await update.message.reply_text(f"🔔 You have {unread} new notification(s)!")
            await update.message.reply_text("Choose an option:", reply_markup=build_inline_menu(role, notif_count=unread))
            return ConversationHandler.END
    await update.message.reply_text("Welcome to ROIN WORLD FZE HR System.\nEnter employee code:", reply_markup=ReplyKeyboardRemove())
    return W_CODE

async def recv_code(update, context):
    ec = update.message.text.strip(); tid = str(update.effective_user.id)
    rn, rd = find_user(ec)
    if not rn: await update.message.reply_text("Not found."); return ConversationHandler.END
    st = rd[5] if len(rd) > 5 else "Active"
    if st == "Terminated": await update.message.reply_text("Deactivated."); return ConversationHandler.END
    if st == "Locked": await update.message.reply_text("Locked."); return ConversationHandler.END
    ex = rd[1].strip() if len(rd) > 1 else ""
    if ex and ex != tid: await update.message.reply_text("Linked to another."); return ConversationHandler.END
    context.user_data["emp_code"] = ec; context.user_data["registry_row"] = rn
    await update.message.reply_text("Password:"); return W_PASS

async def recv_pass(update, context):
    pw = update.message.text.strip(); ec = context.user_data.get("emp_code","")
    rn = context.user_data.get("registry_row",0); tid = str(update.effective_user.id)
    try: await update.message.delete()
    except: pass
    ws = get_sheet(TAB_USER_REGISTRY); rd = ws.row_values(rn)
    h = rd[2] if len(rd) > 2 else ""
    if not h: await update.effective_chat.send_message("No password."); return ConversationHandler.END
    try: ok = bcrypt.checkpw(pw.encode(), h.encode())
    except: await update.effective_chat.send_message("Auth error."); return ConversationHandler.END
    if not ok:
        f = int(rd[6]) if len(rd) > 6 and rd[6].isdigit() else 0; f += 1
        ws.update_cell(rn, 7, str(f))
        if f >= MAX_FAILED_ATTEMPTS:
            ws.update_cell(rn, 6, "Locked")
            await update.effective_chat.send_message("Locked."); return ConversationHandler.END
        await update.effective_chat.send_message(f"Wrong. {MAX_FAILED_ATTEMPTS-f} left."); return W_PASS
    n, d = find_name(ec); role = rd[3] if len(rd) > 3 else ""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws.update_cell(rn,2,tid); ws.update_cell(rn,5,now); ws.update_cell(rn,6,"Active")
    ws.update_cell(rn,7,"0"); ws.update_cell(rn,8,now)
    log(f"LOGIN: {ec} ({n}) — {role}")
    await update.effective_chat.send_message(f"Login successful!\n\nWelcome, {n}\nDepartment: {d}\nRole: {role}")
    await update.effective_chat.send_message("Choose an option:", reply_markup=build_inline_menu(role))
    return ConversationHandler.END

async def cancel_cmd(update, context):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove()); return ConversationHandler.END

def _profile_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Basic Info", callback_data="profile_basic")],
        [InlineKeyboardButton("📁 My Drive Folder", callback_data="profile_drive")],
        [InlineKeyboardButton("📄 Job Description", callback_data="profile_jd")],
        [InlineKeyboardButton("📊 Performance Overview", callback_data="profile_perf")],
        [InlineKeyboardButton("📈 Employment History", callback_data="profile_history")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"),
         InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")],
    ])

def _back_profile_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back", callback_data="menu_my_profile"),
         InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")],
    ])

def _get_emp_record(tid):
    """Return (emp_code, emp_dict, all_emps) for a Telegram user ID, or (None,None,None)."""
    ec = None
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): ec = r[0].strip(); break
    if not ec: return None, None, None
    all_emps = get_sheet(TAB_EMPLOYEE_DB).get_all_records()
    emp = next((r for r in all_emps if str(r.get("Emp_Code","")).strip() == ec), None)
    return ec, emp, all_emps

def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")

async def leave_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    role = ""
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip(); break
    rows = [
        [InlineKeyboardButton("📊 My Leave Balance",   callback_data="menu_leave_balance")],
        [InlineKeyboardButton("✈️ Request Leave",      callback_data="menu_request_leave")],
        [InlineKeyboardButton("📋 My Requests",        callback_data="menu_my_requests")],
    ]
    if role in ("Supervisor", "Direct_Manager", "HR_Staff", "HR_Manager"):
        rows.append([InlineKeyboardButton("👥 Request for Employee", callback_data="menu_team_request")])
        rows.append([InlineKeyboardButton("📂 Team Requests",        callback_data="menu_team_requests")])
    if role in ("HR_Staff", "HR_Manager", "Director"):
        rows.append([InlineKeyboardButton("📑 All Leave Requests",   callback_data="menu_all_leave")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()])
    await q.edit_message_text("🏖️ Leave\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(rows))


async def team_menu_handler(update, _context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    role = ""
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip(); break
    rows = [
        [InlineKeyboardButton("📊 Team Overview",       callback_data="menu_team_overview")],
        [InlineKeyboardButton("📂 Team Leave Requests", callback_data="menu_team_requests")],
        [InlineKeyboardButton("🕐 Team Attendance",     callback_data="att_team")],
    ]
    if role in ("Direct_Manager", "HR_Staff", "HR_Manager"):
        rows.insert(0, [InlineKeyboardButton("👥 Request Leave for Employee", callback_data="menu_team_request")])
    if role in ("HR_Manager", "Director"):
        rows.append([InlineKeyboardButton("📊 Dept Drill-Down", callback_data="menu_dept_drilldown")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()])
    await q.edit_message_text("👥 My Team\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(rows))


async def jd_menu_handler(update, _context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    role = ""
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip(); break
    rows = []
    if role in ("Direct_Manager", "HR_Manager"):
        rows.append([InlineKeyboardButton("📝 Create New JD",  callback_data="menu_generate_jd")])
        rows.append([InlineKeyboardButton("📋 My JDs",         callback_data="menu_jd_my_jds")])
    if role in ("HR_Staff", "HR_Manager"):
        rows.append([InlineKeyboardButton("🔍 JD Reviews",     callback_data="menu_jd_reviews")])
    if role == "Director":
        rows.append([InlineKeyboardButton("✅ JD Approvals",   callback_data="menu_jd_approvals")])
    if not rows:
        rows.append([InlineKeyboardButton("📋 My JDs",         callback_data="menu_jd_my_jds")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()])
    await q.edit_message_text("📄 Job Descriptions\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(rows))


async def hr_tools_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    role = ""
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip(); break
    rows = [
        [InlineKeyboardButton("📑 All Leave Requests",  callback_data="menu_all_leave")],
        [InlineKeyboardButton("🔍 Employee Lookup",     callback_data="menu_emp_lookup")],
        [InlineKeyboardButton("📝 Generate Letters",    callback_data="menu_gen_letters")],
        [InlineKeyboardButton("📢 Announcements",       callback_data="menu_announcements")],
        [InlineKeyboardButton("🕐 Attendance Overview", callback_data="menu_attendance_overview")],
        [InlineKeyboardButton("💰 Payroll Input",       callback_data="menu_payroll")],
        [InlineKeyboardButton("📂 Doc & Contracts",     callback_data="menu_doc_contracts")],
    ]
    if role == "HR_Manager":
        rows.append([InlineKeyboardButton("📊 HR Dashboard",    callback_data="menu_hr_dashboard")])
        rows.append([InlineKeyboardButton("✍️ Signature Admin", callback_data="sig_admin")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()])
    await q.edit_message_text("🛠️ HR Tools\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(rows))


async def overview_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    rows = [
        [InlineKeyboardButton("🏢 Company Dashboard",  callback_data="menu_company_overview")],
        [InlineKeyboardButton("📊 Morning Brief",      callback_data="menu_director_brief")],
        [InlineKeyboardButton("📈 Monthly Report",     callback_data="menu_monthly_report")],
        [InlineKeyboardButton("⚠️ Director Alerts",   callback_data="menu_director_alerts")],
        [InlineKeyboardButton("🍳 Kitchen Staffing",   callback_data="menu_kitchen_staffing")],
        [InlineKeyboardButton("🔍 Employee Lookup",    callback_data="menu_emp_lookup")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ]
    await q.edit_message_text("🏢 Overview\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(rows))


def _contract_expiry_indicator(exp_date_str):
    """Return (display_str, indicator_str) for contract expiry."""
    if not exp_date_str or str(exp_date_str).strip() in ("-", ""):
        return "-", ""
    try:
        exp_date = datetime.strptime(str(exp_date_str).strip(), "%d/%m/%Y").date()
        today    = datetime.now().date()
        days     = (exp_date - today).days
        if days < 0:
            ind = "❌ EXPIRED"
        elif days < 30:
            ind = f"🔴 {days} days left"
        elif days < 60:
            ind = f"🟡 {days} days left"
        else:
            ind = f"🟢 {days} days left"
        return str(exp_date_str).strip(), ind
    except Exception:
        return str(exp_date_str).strip(), ""


async def my_profile_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading profile...")
    try:
        ec, emp, all_emps = _get_emp_record(str(q.from_user.id))
        if not emp:
            await q.edit_message_text("❌ Record not found.",
                reply_markup=InlineKeyboardMarkup([[_bm()]])); return
        mgr_code = str(emp.get("Manager_Code", "")).strip()
        mgr_name = "-"
        if mgr_code:
            mgr = next((r for r in all_emps if str(r.get("Emp_Code","")).strip() == mgr_code), None)
            if mgr: mgr_name = mgr.get("Full_Name", "-")
        exp_str, exp_ind = _contract_expiry_indicator(emp.get("Contract_Expiry_Date", ""))
        leave_bal = str(emp.get("Annual_Leave_Balance", "-")).strip() or "-"
        shift_hrs = str(emp.get("Shift_Hours", "-")).strip() or "-"
        drive_link = str(emp.get("Drive_Folder_Link", "")).strip()
        msg = (f"👤 My Profile\n{'─'*28}\n"
               f"👤 Name:          {emp.get('Full_Name','-')}\n"
               f"🔢 Code:          {ec}\n"
               f"🏢 Department:    {emp.get('Department','-')}\n"
               f"💼 Job Title:     {emp.get('Job_Title','-')}\n"
               f"🌍 Nationality:   {emp.get('Nationality','-')}\n"
               f"📞 Phone:         {emp.get('Phone','-')}\n"
               f"{'─'*28}\n"
               f"📄 Contract Type: {emp.get('Contract_Type','-')}\n"
               f"📅 Start Date:    {emp.get('Contract_Start_Date','-')}\n"
               f"⏳ Expiry Date:   {exp_str}\n"
               f"   Status:        {exp_ind}\n"
               f"{'─'*28}\n"
               f"👔 Manager:       {mgr_name}\n"
               f"📅 Hire Date:     {emp.get('Hire_Date','-')}\n"
               f"⏰ Shift Hours:   {shift_hrs}\n"
               f"🏖️ Leave Balance: {leave_bal} days")
        kb_rows = []
        if drive_link:
            kb_rows.append([InlineKeyboardButton("📂 Open Drive Folder", url=drive_link)])
        kb_rows.append([InlineKeyboardButton("✍️ My Signature",   callback_data="sig_view"),
                        InlineKeyboardButton("📊 Performance",     callback_data="profile_perf")])
        kb_rows.append([InlineKeyboardButton("📄 Job Description", callback_data="profile_jd"),
                        InlineKeyboardButton("📈 History",         callback_data="profile_history")])
        kb_rows.append([_bm()])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


async def profile_basic_handler(update, context):
    """Alias — redirect to my_profile_handler."""
    return await my_profile_handler(update, context)

async def profile_drive_handler(update, context):
    q = update.callback_query; await q.answer()
    try:
        ec, emp, _ = _get_emp_record(str(q.from_user.id))
        if not emp:
            await q.edit_message_text("❌ Record not found.", reply_markup=_back_profile_kb()); return
        link = str(emp.get("Drive_Folder_Link","")).strip()
        if not link:
            await q.edit_message_text(
                "📁 My Drive Folder\n\nNo Drive folder linked yet.\nContact HR to set it up.",
                reply_markup=_back_profile_kb()); return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 Open Drive Folder", url=link)],
            [InlineKeyboardButton("↩️ Back", callback_data="menu_my_profile"),
             InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")],
        ])
        await q.edit_message_text("📁 My Drive Folder\n\nTap the button below to open your folder:",
                                   reply_markup=kb)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back_profile_kb())

async def profile_jd_handler(update, context):
    q = update.callback_query; await q.answer()
    try:
        ec, emp, _ = _get_emp_record(str(q.from_user.id))
        if not ec:
            await q.edit_message_text("❌ Not registered.", reply_markup=_back_profile_kb()); return
        rows = get_sheet("JD_Drafts").get_all_records()
        mine = [r for r in rows if str(r.get("Emp_Code","")).strip() == ec
                or str(r.get("Created_By","")).strip() == ec]
        if not mine:
            await q.edit_message_text(
                "📄 Job Description\n\nNo job description found for your profile.\nContact HR to have one assigned.",
                reply_markup=_back_profile_kb()); return
        r = mine[-1]
        msg = (f"📄 Job Description\n{'─'*24}\n"
               f"Title:    {r.get('Job_Title','-')}\n"
               f"Dept:     {r.get('Department','-')}\n"
               f"Status:   {r.get('Status','-')}\n"
               f"Version:  {r.get('Version','-')}\n"
               f"Created:  {r.get('Created_At','-')}")
        kb_rows = []
        link = str(r.get("PDF_Link","")).strip()
        if link:
            kb_rows.append([InlineKeyboardButton("📄 Open JD PDF", url=link)])
        kb_rows.append([InlineKeyboardButton("↩️ Back", callback_data="menu_my_profile"),
                        InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back_profile_kb())

async def profile_perf_handler(update, context):
    q = update.callback_query; await q.answer()
    try:
        ec, emp, _ = _get_emp_record(str(q.from_user.id))
        if not ec:
            await q.edit_message_text("❌ Not registered.", reply_markup=_back_profile_kb()); return
        rows = get_sheet("Evaluations_Log").get_all_records()
        mine = [r for r in rows if str(r.get("Emp_Code","")).strip() == ec]
        if not mine:
            await q.edit_message_text(
                "📊 Performance Overview\n\nNo evaluations on record yet.",
                reply_markup=_back_profile_kb()); return
        lines = [f"📊 Performance Overview ({len(mine)} evaluation(s))\n{'─'*28}"]
        for r in mine[-5:]:
            score = str(r.get("Score",""))
            try:
                sc = float(score)
                icon = "🟢" if sc >= 80 else "🟡" if sc >= 60 else "🔴"
            except Exception:
                icon = "❓"
            lines.append(f"{icon} {r.get('Period','-')} | {r.get('Type','-')} | Score: {score}")
        await q.edit_message_text("\n".join(lines), reply_markup=_back_profile_kb())
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back_profile_kb())

async def profile_history_handler(update, context):
    q = update.callback_query; await q.answer()
    try:
        ec, emp, _ = _get_emp_record(str(q.from_user.id))
        if not ec:
            await q.edit_message_text("❌ Not registered.", reply_markup=_back_profile_kb()); return
        rows = get_sheet("Promotions_Log").get_all_records()
        mine = [r for r in rows if str(r.get("Emp_Code","")).strip() == ec]
        if not mine:
            await q.edit_message_text(
                "📈 Employment History\n\nNo promotions or role changes on record.",
                reply_markup=_back_profile_kb()); return
        lines = [f"📈 Employment History ({len(mine)} record(s))\n{'─'*28}"]
        for r in mine:
            lines.append(f"• {r.get('Date','-')} | {r.get('Change_Type','-')} | "
                         f"{r.get('Old_Title','-')} → {r.get('New_Title','-')}")
        await q.edit_message_text("\n".join(lines), reply_markup=_back_profile_kb())
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back_profile_kb())

async def warehouse_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    from warehouse_handler import wh_menu_handler
    return await wh_menu_handler(update, context)


# ── Bot_Manager sub-menu handlers ────────────────────────────────────────────

def _bm_back():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"),
        _bm()
    ]])

async def bm_hr_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏖️ Leave",           callback_data="menu_leave")],
        [InlineKeyboardButton("🛠️ HR Tools",        callback_data="menu_hr_tools")],
        [InlineKeyboardButton("⚙️ Admin",            callback_data="menu_admin")],
        [InlineKeyboardButton("💬 HR Messages",      callback_data="menu_hr_messages")],
        [InlineKeyboardButton("📢 Announcements",    callback_data="menu_announcements")],
        [InlineKeyboardButton("💰 Payroll Input",    callback_data="menu_payroll")],
        [InlineKeyboardButton("📂 Doc & Contracts",  callback_data="menu_doc_contracts")],
        [InlineKeyboardButton("📜 Certificates",     callback_data="menu_certificates")],
        [InlineKeyboardButton("📁 Employee Files",   callback_data="emp_files_menu")],
        [InlineKeyboardButton("📚 Bulk PDF Export",   callback_data="bulk_export_menu")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ])
    await q.edit_message_text("🏖️ Leave & HR\n\nSelect area:", reply_markup=kb)

async def bm_approvals_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Pending Approvals",  callback_data="menu_pending_approvals")],
        [InlineKeyboardButton("✅ Batch Approvals",    callback_data="menu_batch_approvals")],
        [InlineKeyboardButton("📊 Morning Brief",      callback_data="menu_director_brief")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ])
    await q.edit_message_text("🔔 Approvals\n\nSelect area:", reply_markup=kb)

async def bm_teams_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 My Team",           callback_data="menu_team")],
        [InlineKeyboardButton("📄 Job Descriptions",  callback_data="menu_jd")],
        [InlineKeyboardButton("📊 Performance Evals", callback_data="menu_eval")],
        [InlineKeyboardButton("🔍 Employee Lookup",   callback_data="menu_emp_lookup")],
        [InlineKeyboardButton("👔 Recruitment",        callback_data="menu_recruitment")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ])
    await q.edit_message_text("👥 Teams\n\nSelect area:", reply_markup=kb)


async def bm_recruitment_handler(update, context):
    q = update.callback_query; await q.answer()
    from recruitment_handler import recruitment_menu_handler
    return await recruitment_menu_handler(update, context)

async def bm_reports_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏢 Company Overview",  callback_data="menu_overview")],
        [InlineKeyboardButton("📊 Morning Brief",     callback_data="menu_director_brief")],
        [InlineKeyboardButton("📈 Monthly Report",    callback_data="menu_monthly_report")],
        [InlineKeyboardButton("🕐 Attendance",        callback_data="menu_attendance_overview")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ])
    await q.edit_message_text("📊 Reports & Dashboards\n\nSelect area:", reply_markup=kb)

async def bm_schedule_handler(update, context):
    q = update.callback_query; await q.answer()
    return await sched_menu_handler(update, context)

async def bm_warehouse_handler(update, context):
    q = update.callback_query; await q.answer()
    from warehouse_handler import wh_menu_handler
    return await wh_menu_handler(update, context)

async def bm_transport_handler(update, context):
    q = update.callback_query; await q.answer()
    return await transport_menu_handler(update, context)

async def bm_safety_handler(update, context):
    q = update.callback_query; await q.answer()
    from safety_handler import safety_menu_handler
    return await safety_menu_handler(update, context)

async def bm_translation_handler(update, context):
    q = update.callback_query; await q.answer()
    from translation_handler import translation_menu_handler
    return await translation_menu_handler(update, context)

async def bm_operations_handler(update, context):
    q = update.callback_query; await q.answer()
    from operations_handler import ops_menu_handler
    return await ops_menu_handler(update, context)

async def bm_quality_handler(update, context):
    q = update.callback_query; await q.answer()
    from quality_handler import qc_menu_handler
    return await qc_menu_handler(update, context)

async def bm_supply_handler(update, context):
    q = update.callback_query; await q.answer()
    from supply_handler import supply_menu_handler
    return await supply_menu_handler(update, context)

async def bm_housing_handler(update, context):
    q = update.callback_query; await q.answer()
    from housing_handler import housing_menu_handler
    return await housing_menu_handler(update, context)

async def bm_system_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Admin Functions",   callback_data="menu_admin")],
        [InlineKeyboardButton("📥 Bulk Import",       callback_data="menu_bulk_import")],
        [InlineKeyboardButton("🔍 Employee Lookup",   callback_data="menu_emp_lookup")],
        [InlineKeyboardButton("📊 HR Dashboard",      callback_data="menu_hr_dashboard")],
        [InlineKeyboardButton("✍️ Signature Admin",   callback_data="sig_admin")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()],
    ])
    await q.edit_message_text("⚙️ System Admin\n\nSelect area:", reply_markup=kb)

async def bm_feedback_handler(update, context):
    q = update.callback_query; await q.answer()
    from feedback_handler import fb_dashboard_handler
    return await fb_dashboard_handler(update, context)


async def menu_catch(update, context):
    q = update.callback_query; await q.answer()
    labels = {
        "menu_team_attendance":  "Team Attendance",
        "menu_assign_tasks":     "Assign Tasks",
        "menu_all_leave":        "All Leave Requests",
        "menu_emp_lookup":       "Employee Lookup",
        "menu_gen_letters":      "Generate Letters",
        "menu_announcements":    "Announcements",
        "menu_admin":            "Admin Functions",
        "menu_company_overview": "Company Overview",
        "menu_reports":          "Reports",
        "menu_supplier_db":      "Supplier Database",
        "menu_budget_tracker":   "Budget Tracker",
        "menu_supply_report":    "Supply Report",
        "menu_kitchen_staffing": "Kitchen Staffing",
        "menu_monthly_report":   "Monthly Report",
        "menu_dept_drilldown":   "Dept Drill-Down",
        "menu_payroll":          "Payroll Input",
        "menu_hr_dashboard":     "HR Dashboard",
        "menu_team_overview":    "Team Overview",
    }
    back_map = {
        "menu_team_attendance":  "menu_team",
        "menu_assign_tasks":     "back_to_menu",
        "menu_all_leave":        "menu_leave",
        "menu_emp_lookup":       "menu_hr_tools",
        "menu_gen_letters":      "menu_hr_tools",
        "menu_announcements":    "menu_hr_tools",
        "menu_admin":            "back_to_menu",
        "menu_company_overview": "menu_overview",
        "menu_reports":          "menu_overview",
        "menu_supplier_db":      "menu_supply",
        "menu_budget_tracker":   "menu_supply",
        "menu_supply_report":    "menu_supply",
        "menu_kitchen_staffing": "menu_overview",
        "menu_monthly_report":   "menu_overview",
        "menu_dept_drilldown":   "menu_team",
        "menu_payroll":          "menu_hr_tools",
        "menu_hr_dashboard":     "menu_hr_tools",
        "menu_team_overview":    "menu_team",
    }
    back_cb = back_map.get(q.data, "back_to_menu")
    bk = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data=back_cb),
                                 InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")]])
    await q.edit_message_text(f"{labels.get(q.data, q.data)}\n\nComing soon.", reply_markup=bk)

async def err(update, context): log(f"ERROR: {context.error}")

async def main():
    print("="*50); print("ROIN WORLD FZE — HR Bot v14.0 — 16 Roles"); print("="*50)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start_cmd)],
        states={W_CODE:[MessageHandler(filters.TEXT & ~filters.COMMAND, recv_code)],
                W_PASS:[MessageHandler(filters.TEXT & ~filters.COMMAND, recv_pass)]},
        fallbacks=[CommandHandler("cancel", cancel_cmd)]))

    app.add_handler(get_leave_conversation_handler())
    app.add_handler(get_team_request_handler())
    app.add_handler(get_missing_punch_handler())
    app.add_handler(CallbackQueryHandler(leave_balance_handler, pattern="^menu_leave_balance$"))
    app.add_handler(CallbackQueryHandler(my_requests_handler, pattern="^menu_my_requests$"))
    app.add_handler(CallbackQueryHandler(myreq_list, pattern="^myreq_"))
    app.add_handler(CallbackQueryHandler(team_requests_handler, pattern="^menu_team_requests$"))
    app.add_handler(CallbackQueryHandler(teamreq_list, pattern="^teamreq_"))
    app.add_handler(CallbackQueryHandler(request_view_handler, pattern="^rview_"))
    app.add_handler(CallbackQueryHandler(pdf_download_handler, pattern="^pdf_"))

    app.add_handler(CallbackQueryHandler(pending_approvals_handler, pattern="^menu_pending_approvals$"))
    app.add_handler(CallbackQueryHandler(pending_category_handler, pattern="^pending_cat_"))
    app.add_handler(CallbackQueryHandler(pending_view_handler, pattern="^pview_"))
    for h in get_approval_handlers(): app.add_handler(h)

    app.add_handler(CallbackQueryHandler(attendance_menu, pattern="^menu_attendance_overview$"))
    app.add_handler(CallbackQueryHandler(att_summary_placeholder, pattern="^att_summary$"))
    app.add_handler(get_upload_conversation_handler())
    app.add_handler(get_attendance_conversation_handler())

    app.add_handler(CallbackQueryHandler(my_attendance_handler, pattern="^menu_my_attendance$"))
    app.add_handler(CallbackQueryHandler(att_own_handler, pattern="^att_own$"))
    app.add_handler(CallbackQueryHandler(att_own_year_handler, pattern="^att_oyr_"))
    app.add_handler(CallbackQueryHandler(att_own_month_handler, pattern="^att_omo_"))
    app.add_handler(CallbackQueryHandler(att_team_handler, pattern="^att_team$"))
    app.add_handler(CallbackQueryHandler(att_team_emp_handler, pattern="^att_te_"))
    app.add_handler(CallbackQueryHandler(att_team_year_handler, pattern="^att_tyr_"))
    app.add_handler(CallbackQueryHandler(att_team_month_handler, pattern="^att_tmo_"))
    app.add_handler(CallbackQueryHandler(att_comp_handler, pattern="^att_comp$"))
    app.add_handler(CallbackQueryHandler(att_comp_dept_handler, pattern="^att_cd_"))
    app.add_handler(CallbackQueryHandler(att_comp_emp_handler, pattern="^att_ce_"))
    app.add_handler(CallbackQueryHandler(att_comp_year_handler, pattern="^att_cyr_"))
    app.add_handler(CallbackQueryHandler(att_comp_month_handler, pattern="^att_cmo_"))
    app.add_handler(get_jd_create_handler())
    app.add_handler(get_jd_hr_handler())
    app.add_handler(get_jd_manager_dir_handler())

    # Phase 3 — FAQ, Certificates, Contact HR
    for h in get_faq_handlers(): app.add_handler(h)
    app.add_handler(get_cert_handler())
    for h in get_cert_static_handlers(): app.add_handler(h)
    app.add_handler(get_contact_hr_handler())
    app.add_handler(get_hr_chr_reply_handler())
    app.add_handler(CallbackQueryHandler(hr_messages_menu, pattern="^menu_hr_messages$"))
    app.add_handler(CallbackQueryHandler(hr_chr_list,      pattern="^hr_chr_(pending|all)$"))
    app.add_handler(CallbackQueryHandler(hr_chr_view,      pattern="^hr_chr_view_"))

    # Phase 4 — Manager Features
    for h in get_manager_handlers(): app.add_handler(h)

    # Phase 5 — HR Tools
    app.add_handler(get_emp_lookup_handler())
    app.add_handler(get_admin_handler())
    for h in get_hr_tools_handlers(): app.add_handler(h)

    # Phase 6 — Document & Contract Management
    app.add_handler(get_doc_add_handler())
    app.add_handler(get_contract_log_handler())
    for h in get_doc_contract_static_handlers(): app.add_handler(h)

    # Phase 7 — Announcements
    app.add_handler(get_ann_create_handler())
    for h in get_ann_static_handlers(): app.add_handler(h)

    # Phase 8 — Reporting & Dashboards
    for h in get_report_handlers(): app.add_handler(h)

    # Phase 9 — Performance Evaluation
    app.add_handler(get_eval_handler())
    for h in get_eval_static_handlers(): app.add_handler(h)

    # Phase 10 — Warehouse Management
    app.add_handler(get_wh_tx_handler())
    for h in get_wh_static_handlers(): app.add_handler(h)
    app.add_handler(CallbackQueryHandler(warehouse_menu_handler, pattern="^menu_warehouse$"))

    # Phase 11 — Vehicle Management
    for h in get_vehicle_handlers(): app.add_handler(h)
    for h in get_vehicle_static_handlers(): app.add_handler(h)

    # Phase 12 — Supply & Purchasing
    for h in get_supply_handlers(): app.add_handler(h)
    for h in get_supply_static_handlers(): app.add_handler(h)

    # Phase 13 — Bulk Employee Import
    app.add_handler(get_bulk_import_handler())

    # Phase 14 — Safety
    for h in get_safety_handlers(): app.add_handler(h)
    for h in get_safety_static_handlers(): app.add_handler(h)

    # Phase 15 — Translation
    for h in get_translation_handlers(): app.add_handler(h)
    for h in get_translation_static_handlers(): app.add_handler(h)

    # Phase 16 — Operations / Kitchen
    for h in get_operations_handlers(): app.add_handler(h)
    for h in get_operations_static_handlers(): app.add_handler(h)

    # Phase 17 — Quality Control
    for h in get_quality_handlers(): app.add_handler(h)
    for h in get_quality_static_handlers(): app.add_handler(h)

    # Phase 18 — Housing / Accommodation
    for h in get_housing_handlers(): app.add_handler(h)
    for h in get_housing_static_handlers(): app.add_handler(h)

    # Phase 19 — Director Features
    for h in get_director_handlers(): app.add_handler(h)

    # Phase 20 — Monthly Schedule
    for h in get_schedule_handlers(): app.add_handler(h)
    for h in get_schedule_static_handlers(): app.add_handler(h)

    # Phase 21 — Bot Feedback
    app.add_handler(get_feedback_handler())
    app.add_handler(get_fb_mgr_handler())
    for h in get_fb_static_handlers(): app.add_handler(h)
    app.add_handler(CallbackQueryHandler(fb_menu_start,        pattern="^menu_bot_feedback$"))

    # Phase 22 — Electronic Signatures
    app.add_handler(get_sig_setup_handler())
    for h in get_sig_static_handlers(): app.add_handler(h)

    # Phase 23 — Notification Center
    for h in get_notif_handlers(): app.add_handler(h)

    # Phase 24 — Memo System
    for h in get_memo_handlers(): app.add_handler(h)

    # Phase 25 — Recruitment & Hiring
    for h in get_recruitment_handlers(): app.add_handler(h)
    for h in get_recruitment_static_handlers(): app.add_handler(h)

    # Phase 26 — Universal Document Search
    app.add_handler(get_search_handler())

    # Phase 27 — Unified Requests Menu
    for h in get_requests_handlers(): app.add_handler(h)

    # Phase 28 — PDF Regeneration (backfill)
    app.add_handler(get_regen_handler())

    # Phase 29 — Transport Request System
    for h in get_transport_handlers(): app.add_handler(h)
    for h in get_transport_static_handlers(): app.add_handler(h)

    # Phase 30 — Live Location handler (group=1 to avoid ConversationHandler conflicts)
    app.add_handler(MessageHandler(filters.LOCATION, handle_location_update), group=1)

    # Phase 31 — Overdue trip checker (runs every 5 minutes)
    if app.job_queue:
        app.job_queue.run_repeating(check_overdue_trips, interval=300, first=60,
                                    name="overdue_checker")

    # Phase 32 — Generic Request Engine (21 request types from Sections 3-13)
    for h in build_all_request_handlers():
        app.add_handler(h)

    # Phase 33 — Task Management (Section 14)
    for h in get_task_handlers(): app.add_handler(h)
    for h in get_task_static_handlers(): app.add_handler(h)
    if app.job_queue:
        app.job_queue.run_repeating(check_overdue_tasks, interval=3600, first=120,
                                    name="overdue_tasks_checker")

    # Phase 34 — Employee Self-Reports (Section 15)
    for h in get_reports_static_handlers(): app.add_handler(h)

    # Phase 35 — Employee Files + Bulk PDF Export
    for h in get_emp_files_handlers(): app.add_handler(h)
    for h in get_emp_files_static_handlers(): app.add_handler(h)
    for h in get_bulk_export_handlers(): app.add_handler(h)

    # Bot_Manager sub-menu handlers
    app.add_handler(CallbackQueryHandler(bm_hr_handler,         pattern="^bm_hr$"))
    app.add_handler(CallbackQueryHandler(bm_approvals_handler,  pattern="^bm_approvals$"))
    app.add_handler(CallbackQueryHandler(bm_teams_handler,      pattern="^bm_teams$"))
    app.add_handler(CallbackQueryHandler(bm_reports_handler,    pattern="^bm_reports$"))
    app.add_handler(CallbackQueryHandler(bm_schedule_handler,   pattern="^bm_schedule$"))
    app.add_handler(CallbackQueryHandler(bm_warehouse_handler,  pattern="^bm_warehouse$"))
    app.add_handler(CallbackQueryHandler(bm_transport_handler,  pattern="^bm_transport$"))
    app.add_handler(CallbackQueryHandler(bm_safety_handler,     pattern="^bm_safety$"))
    app.add_handler(CallbackQueryHandler(bm_translation_handler,pattern="^bm_translation$"))
    app.add_handler(CallbackQueryHandler(bm_operations_handler, pattern="^bm_operations$"))
    app.add_handler(CallbackQueryHandler(bm_quality_handler,    pattern="^bm_quality$"))
    app.add_handler(CallbackQueryHandler(bm_supply_handler,     pattern="^bm_supply$"))
    app.add_handler(CallbackQueryHandler(bm_housing_handler,    pattern="^bm_housing$"))
    app.add_handler(CallbackQueryHandler(bm_system_handler,       pattern="^bm_system$"))
    app.add_handler(CallbackQueryHandler(bm_recruitment_handler,  pattern="^bm_recruitment$"))
    app.add_handler(CallbackQueryHandler(bm_feedback_handler,     pattern="^bm_feedback$"))
    app.add_handler(CallbackQueryHandler(sched_menu_handler,    pattern="^menu_schedule$"))

    app.add_handler(CallbackQueryHandler(leave_menu_handler,    pattern="^menu_leave$"))
    app.add_handler(CallbackQueryHandler(team_menu_handler,     pattern="^menu_team$"))
    app.add_handler(CallbackQueryHandler(jd_menu_handler,       pattern="^menu_jd$"))
    app.add_handler(CallbackQueryHandler(hr_tools_menu_handler, pattern="^menu_hr_tools$"))
    app.add_handler(CallbackQueryHandler(overview_menu_handler, pattern="^menu_overview$"))
    app.add_handler(CallbackQueryHandler(my_profile_handler,    pattern="^menu_my_profile$"))
    app.add_handler(CallbackQueryHandler(profile_basic_handler, pattern="^profile_basic$"))
    app.add_handler(CallbackQueryHandler(profile_drive_handler, pattern="^profile_drive$"))
    app.add_handler(CallbackQueryHandler(profile_jd_handler,    pattern="^profile_jd$"))
    app.add_handler(CallbackQueryHandler(profile_perf_handler,  pattern="^profile_perf$"))
    app.add_handler(CallbackQueryHandler(profile_history_handler, pattern="^profile_history$"))
    app.add_handler(CallbackQueryHandler(back_to_menu_handler, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(menu_catch))
    app.add_error_handler(err)

    print("Running. Ctrl+C to stop."); print("="*50)
    await app.initialize(); await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    try:
        while True: await asyncio.sleep(1)
    except KeyboardInterrupt: pass
    finally: await app.updater.stop(); await app.stop(); await app.shutdown()

if __name__ == "__main__": asyncio.run(main())
