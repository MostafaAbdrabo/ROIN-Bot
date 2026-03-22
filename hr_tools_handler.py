"""
ROIN WORLD FZE — HR Tools Handler
====================================
Phase 5:
  5A. All Leave Requests — summary + view pending HR / all this month / by employee
  5B. Employee Lookup — search by code or name
  5C. Admin Functions — list users, lock, unlock, reset password
  5D. Generate Letters — Employment, Salary, Experience, Contract Renewal (placeholders)
  5E. Payroll Input — auto-calculate from attendance + leave + OT
  5F. HR Daily Dashboard — shown before menu for HR_Manager
"""

import bcrypt, secrets, string
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler, MessageHandler, filters)
from config import get_sheet, CURRENT_ATTENDANCE_TAB
from attendance_handler import get_my_attendance_summary

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bhr(): return InlineKeyboardButton("↩️ HR Tools",  callback_data="menu_hr_tools")

# ── Conversation states ────────────────────────────────────────────────────────
ADMIN_ACTION   = 500
ADMIN_CODE_IN  = 501
EMP_LOOKUP_INP = 510
PAYROLL_CONFIRM= 520


# ══════════════════════════════════════════════════════════════════
#  5A. ALL LEAVE REQUESTS
# ══════════════════════════════════════════════════════════════════

async def all_leave_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading leave summary...")
    try:
        rows = get_sheet("Leave_Log").get_all_records()
        now  = datetime.now()
        month_start = datetime(now.year, now.month, 1)

        pending_mgr = pending_hr = pending_dir = approved_month = rejected_month = 0
        for r in rows:
            final = str(r.get("Final_Status","")).strip()
            mgr_st= str(r.get("Manager_Status","")).strip()
            hr_st = str(r.get("HR_Status","")).strip()
            dir_st= str(r.get("Director_Status","")).strip()
            if final == "Pending":
                if mgr_st == "Pending": pending_mgr += 1
                elif hr_st == "Pending": pending_hr += 1
                elif dir_st == "Pending": pending_dir += 1
            # This month's closed requests
            try:
                created = datetime.strptime(str(r.get("Created_At",""))[:10], "%d/%m/%Y")
                if created >= month_start:
                    if final == "Approved": approved_month += 1
                    elif final == "Rejected": rejected_month += 1
            except Exception: pass
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return

    kb = [
        [InlineKeyboardButton(f"🔴 Pending HR ({pending_hr})",    callback_data="leave_list_hr")],
        [InlineKeyboardButton(f"🟡 Pending Mgr ({pending_mgr})",  callback_data="leave_list_mgr")],
        [InlineKeyboardButton(f"✅ Approved this month ({approved_month})", callback_data="leave_list_approved")],
        [InlineKeyboardButton(f"❌ Rejected this month ({rejected_month})", callback_data="leave_list_rejected")],
        [InlineKeyboardButton("🔍 Search by Employee",             callback_data="leave_search_emp")],
        [bhr(), bm()],
    ]
    msg = (f"📑 All Leave Requests\n{'─'*28}\n"
           f"🔴 Pending Manager: {pending_mgr}\n"
           f"🟡 Pending HR:      {pending_hr}\n"
           f"🟣 Pending Director:{pending_dir}\n"
           f"✅ Approved (month):{approved_month}\n"
           f"❌ Rejected (month):{rejected_month}")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def leave_list_handler(update, context):
    """Show list of requests by filter."""
    q = update.callback_query; await q.answer()
    mode = q.data.replace("leave_list_", "")
    await q.edit_message_text("⏳ Loading...")
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    try:
        rows = get_sheet("Leave_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return
    filtered = []
    for r in rows:
        final  = str(r.get("Final_Status","")).strip()
        mgr_st = str(r.get("Manager_Status","")).strip()
        hr_st  = str(r.get("HR_Status","")).strip()
        if mode == "hr"       and final == "Pending" and hr_st == "Pending":
            filtered.append(r)
        elif mode == "mgr"    and final == "Pending" and mgr_st == "Pending":
            filtered.append(r)
        elif mode in ("approved","rejected"):
            try:
                created = datetime.strptime(str(r.get("Created_At",""))[:10], "%d/%m/%Y")
                if created >= month_start and final == mode.capitalize():
                    filtered.append(r)
            except Exception: pass
    label = {"hr":"Pending HR","mgr":"Pending Manager","approved":"Approved","rejected":"Rejected"}.get(mode, mode)
    if not filtered:
        await q.edit_message_text(f"📑 {label}\n\nNo requests found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_all_leave"), bm()]])); return
    kb = []
    for r in filtered[:20]:
        rid  = str(r.get("Request_ID","?"))
        ec   = str(r.get("Emp_Code","?"))
        lt   = str(r.get("Request_Type","?"))
        date = str(r.get("Start_Date","?"))
        kb.append([InlineKeyboardButton(f"📋 {rid} — {ec} {lt} {date}", callback_data=f"rview_{rid}")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_all_leave"), bm()])
    await q.edit_message_text(f"📑 {label} ({len(filtered)} total):",
                               reply_markup=InlineKeyboardMarkup(kb))


async def leave_search_emp_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "🔍 Search Leave by Employee\n\nType employee code or part of name:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_all_leave"), bm()]]));


# ══════════════════════════════════════════════════════════════════
#  5B. EMPLOYEE LOOKUP
# ══════════════════════════════════════════════════════════════════

async def emp_lookup_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "🔍 Employee Lookup\n\nType employee code or part of name:",
        reply_markup=InlineKeyboardMarkup([[bhr(), bm()]]))
    return EMP_LOOKUP_INP


async def emp_lookup_inp(update, context):
    text = update.message.text.strip().lower()
    bk   = InlineKeyboardMarkup([[bhr(), bm()]])
    if len(text) < 2:
        await update.message.reply_text("⚠️ Enter at least 2 characters.", reply_markup=bk)
        return EMP_LOOKUP_INP
    try:
        all_emps = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", reply_markup=bk)
        return ConversationHandler.END
    matches = [r for r in all_emps
               if text in str(r.get("Emp_Code","")).lower()
               or text in str(r.get("Full_Name","")).lower()]
    if not matches:
        await update.message.reply_text("❌ No matches found. Try again:", reply_markup=bk)
        return EMP_LOOKUP_INP
    if len(matches) == 1:
        await _send_emp_profile(update.message, matches[0])
        return ConversationHandler.END
    # Multiple matches — show buttons
    kb = [[InlineKeyboardButton(f"👤 {r.get('Full_Name','?')} ({r.get('Emp_Code','?')})",
                                callback_data=f"lookup_ec_{r.get('Emp_Code','')}")] for r in matches[:10]]
    kb.append([bhr(), bm()])
    await update.message.reply_text(f"Found {len(matches)} matches. Select one:",
                                     reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


async def lookup_emp_view(update, context):
    q = update.callback_query; await q.answer()
    ec = q.data.replace("lookup_ec_", "")
    await q.edit_message_text("⏳ Loading...")
    try:
        all_emps = get_sheet("Employee_DB").get_all_records()
        emp = next((r for r in all_emps if str(r.get("Emp_Code","")).strip() == ec), None)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return
    if not emp:
        await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return
    await _send_emp_profile_inline(q, emp)


async def _send_emp_profile(msg_obj, emp):
    """Send employee profile as text message."""
    ec = str(emp.get("Emp_Code","?"))
    # Contract expiry
    exp_str = str(emp.get("Contract_Expiry_Date","")).strip()
    exp_ind = ""
    if exp_str:
        try:
            exp_date = datetime.strptime(exp_str, "%d/%m/%Y").date()
            left = (exp_date - datetime.now().date()).days
            exp_ind = f" ({'❌EXPIRED' if left<0 else '🔴'+str(left)+'d' if left<30 else '🟡'+str(left)+'d' if left<60 else '🟢'+str(left)+'d'})"
        except Exception: pass
    # Attendance rate
    att_rate = "?"
    try:
        s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
        if s: att_rate = f"{s['rate']}%"
    except Exception: pass
    text = (f"👤 {emp.get('Full_Name','-')} ({ec})\n{'─'*28}\n"
            f"🏢 Department:    {emp.get('Department','-')}\n"
            f"💼 Job Title:     {emp.get('Job_Title','-')}\n"
            f"🌍 Nationality:   {emp.get('Nationality','-')}\n"
            f"📞 Phone:         {emp.get('Phone','-')}\n"
            f"📅 Hire Date:     {emp.get('Hire_Date','-')}\n"
            f"📄 Contract:      {emp.get('Contract_Type','-')}\n"
            f"⏳ Expiry:        {exp_str}{exp_ind}\n"
            f"🏖️ Leave Bal:    {emp.get('Annual_Leave_Balance','-')}\n"
            f"📈 Att Rate:      {att_rate}\n"
            f"🔖 Status:        {emp.get('Status','-')}")
    kb = InlineKeyboardMarkup([[bhr(), bm()]])
    await msg_obj.reply_text(text, reply_markup=kb)


async def _send_emp_profile_inline(q, emp):
    """Send employee profile via edit_message_text."""
    ec = str(emp.get("Emp_Code","?"))
    exp_str = str(emp.get("Contract_Expiry_Date","")).strip()
    exp_ind = ""
    if exp_str:
        try:
            exp_date = datetime.strptime(exp_str, "%d/%m/%Y").date()
            left = (exp_date - datetime.now().date()).days
            exp_ind = f" ({'❌EXPIRED' if left<0 else '🔴'+str(left)+'d' if left<30 else '🟡'+str(left)+'d' if left<60 else '🟢'+str(left)+'d'})"
        except Exception: pass
    att_rate = "?"
    try:
        s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
        if s: att_rate = f"{s['rate']}%"
    except Exception: pass
    text = (f"👤 {emp.get('Full_Name','-')} ({ec})\n{'─'*28}\n"
            f"🏢 Department:    {emp.get('Department','-')}\n"
            f"💼 Job Title:     {emp.get('Job_Title','-')}\n"
            f"🌍 Nationality:   {emp.get('Nationality','-')}\n"
            f"📞 Phone:         {emp.get('Phone','-')}\n"
            f"📅 Hire Date:     {emp.get('Hire_Date','-')}\n"
            f"📄 Contract:      {emp.get('Contract_Type','-')}\n"
            f"⏳ Expiry:        {exp_str}{exp_ind}\n"
            f"🏖️ Leave Bal:    {emp.get('Annual_Leave_Balance','-')}\n"
            f"📈 Att Rate:      {att_rate}\n"
            f"🔖 Status:        {emp.get('Status','-')}")
    kb = InlineKeyboardMarkup([[bhr(), bm()]])
    await q.edit_message_text(text, reply_markup=kb)


def get_emp_lookup_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(emp_lookup_start, pattern="^menu_emp_lookup$")],
        states={
            EMP_LOOKUP_INP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, emp_lookup_inp),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^back_to_menu$"),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^menu_hr_tools$"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END)],
        per_message=False,
    )


# ══════════════════════════════════════════════════════════════════
#  5C. ADMIN FUNCTIONS
# ══════════════════════════════════════════════════════════════════

async def admin_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("👥 List Users",    callback_data="admin_list")],
        [InlineKeyboardButton("🔒 Lock User",     callback_data="admin_lock")],
        [InlineKeyboardButton("🔓 Unlock User",   callback_data="admin_unlock")],
        [InlineKeyboardButton("🔑 Reset Password",callback_data="admin_reset")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), bm()],
    ]
    await q.edit_message_text("⚙️ Admin Functions\n\nSelect action:", reply_markup=InlineKeyboardMarkup(kb))


async def admin_list_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading users...")
    try:
        rows = get_sheet("User_Registry").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return
    if not rows:
        await q.edit_message_text("No users registered.", reply_markup=InlineKeyboardMarkup([[bhr(), bm()]])); return
    lines = [f"👥 Users ({len(rows)} total)\n{'─'*28}"]
    for r in rows:
        ec   = str(r.get("Emp_Code","?"))
        role = str(r.get("Bot_Role","?"))
        st   = str(r.get("Status","?"))
        last = str(r.get("Last_Access",""))[:10]
        icon = "✅" if st == "Active" else "🔒" if st == "Locked" else "❌"
        lines.append(f"{icon} {ec} [{role}] {last}")
    msg = "\n".join(lines[:30])
    if len(rows) > 30: msg += f"\n... and {len(rows)-30} more"
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("↩️ Back", callback_data="menu_admin"), bm()]]))


async def admin_action_start(update, context):
    """Start lock/unlock/reset — ask for employee code."""
    q = update.callback_query; await q.answer()
    action = q.data.replace("admin_", "")
    context.user_data["admin_action"] = action
    labels = {"lock":"Lock","unlock":"Unlock","reset":"Reset Password"}
    await q.edit_message_text(
        f"⚙️ {labels.get(action, action)} User\n\nType the employee code:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_admin"), bm()]]))
    return ADMIN_CODE_IN


async def admin_code_inp(update, context):
    ec     = update.message.text.strip()
    action = context.user_data.get("admin_action","lock")
    bk     = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_admin"), bm()]])
    try:
        ws   = get_sheet("User_Registry")
        rows = ws.get_all_values()
        hdr  = rows[0] if rows else []
        try: ec_col   = hdr.index("Emp_Code") + 1
        except: ec_col = 1
        try: st_col   = hdr.index("Status") + 1
        except: st_col = 6
        try: pw_col   = hdr.index("Password_Hash") + 1
        except: pw_col = 3
        try: fa_col   = hdr.index("Failed_Attempts") + 1
        except: fa_col = 7
        found_row = None
        for i, row in enumerate(rows):
            if i == 0: continue
            if len(row) >= ec_col and row[ec_col-1].strip() == ec:
                found_row = i + 1; break
        if not found_row:
            await update.message.reply_text(f"❌ Employee {ec} not found.", reply_markup=bk)
            return ConversationHandler.END

        if action == "lock":
            ws.update_cell(found_row, st_col, "Locked")
            reply = f"🔒 User {ec} locked."
        elif action == "unlock":
            ws.update_cell(found_row, st_col, "Active")
            ws.update_cell(found_row, fa_col, "0")
            reply = f"🔓 User {ec} unlocked."
        elif action == "reset":
            # Generate new temp password
            chars   = string.ascii_letters + string.digits
            new_pw  = "Pass@" + ec + "".join(secrets.choice(chars) for _ in range(4))
            pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
            ws.update_cell(found_row, pw_col, pw_hash)
            ws.update_cell(found_row, fa_col, "0")
            ws.update_cell(found_row, st_col, "Active")
            reply = f"🔑 Password reset for {ec}.\nNew temp password: `{new_pw}`\nShare securely."
        else:
            reply = "❌ Unknown action."

        # Log to Access_Log
        try:
            get_sheet("Access_Log").append_row(
                [datetime.now().strftime("%d/%m/%Y %H:%M"), "ADMIN", action.upper(), ec, "Success"],
                value_input_option="USER_ENTERED")
        except Exception: pass

    except Exception as e:
        reply = f"❌ {e}"
    await update.message.reply_text(reply, reply_markup=bk)
    return ConversationHandler.END


async def admin_cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_admin_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_action_start, pattern="^admin_(lock|unlock|reset)$")],
        states={
            ADMIN_CODE_IN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_code_inp),
                CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^menu_admin$"),
                CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, admin_cancel)],
        per_message=False,
    )


# ══════════════════════════════════════════════════════════════════
#  5D. GENERATE LETTERS
# ══════════════════════════════════════════════════════════════════

async def gen_letters_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("📜 Employment Confirmation", callback_data="letter_employment")],
        [InlineKeyboardButton("💰 Salary Certificate",      callback_data="letter_salary")],
        [InlineKeyboardButton("🏅 Experience Letter",       callback_data="letter_experience")],
        [InlineKeyboardButton("⚠️ Warning Letter",          callback_data="letter_warning")],
        [InlineKeyboardButton("📋 Contract Renewal",        callback_data="letter_renewal")],
        [bhr(), bm()],
    ]
    await q.edit_message_text("📝 Generate Letters\n\nSelect letter type:\n(Enter employee code after selecting)",
                               reply_markup=InlineKeyboardMarkup(kb))


async def letter_placeholder(update, context):
    q = update.callback_query; await q.answer()
    lt = q.data.replace("letter_","")
    labels = {
        "employment": "Employment Confirmation",
        "salary":     "Salary Certificate",
        "experience": "Experience Letter",
        "warning":    "Warning Letter",
        "renewal":    "Contract Renewal",
    }
    await q.edit_message_text(
        f"📝 {labels.get(lt, lt)}\n\n"
        f"✅ Feature ready — uses cert_handler.py PDF engine.\n"
        f"To generate: tap 📜 Certificates from employee's profile\n"
        f"or type employee code to generate for any employee.\n\n"
        f"Full per-employee generation from HR side coming in Phase 5D final.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_gen_letters"), bm()]]))


# ══════════════════════════════════════════════════════════════════
#  5E. PAYROLL INPUT
# ══════════════════════════════════════════════════════════════════

async def payroll_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("⚙️ Generate This Month",    callback_data="payroll_generate")],
        [InlineKeyboardButton("📊 View Payroll Tab",       callback_data="payroll_view")],
        [bhr(), bm()],
    ]
    await q.edit_message_text(
        "💰 Payroll Input\n\nAuto-calculated from attendance + leave + overtime:",
        reply_markup=InlineKeyboardMarkup(kb))


async def payroll_generate(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating payroll data...")
    try:
        all_emp  = get_sheet("Employee_DB").get_all_records()
        leave_rows = get_sheet("Leave_Log").get_all_records()
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)

        ws = get_sheet("Payroll_Input")
        # Check if header row exists
        existing = ws.get_all_values()
        if not existing or existing[0][0] != "Emp_Code":
            ws.append_row(["Emp_Code","Full_Name","Department","Days_Present","Days_Absent",
                           "Days_Leave_Paid","Days_Leave_Sick","Days_Leave_Unpaid",
                           "OT_Hours","OT_Rate","OT_Payment","Generated_At"],
                          value_input_option="USER_ENTERED")

        rows_to_write = []
        for emp in all_emp:
            ec   = str(emp.get("Emp_Code","")).strip()
            if not ec: continue
            # Attendance
            att = None
            try: att = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
            except Exception: pass
            p = att["present"] if att else 0
            a = att["absent"]  if att else 0

            # Leave this month by type
            paid = sick = unpaid = 0
            ot_hrs = ot_payment = 0.0
            for r in leave_rows:
                if str(r.get("Emp_Code","")).strip() != ec: continue
                if str(r.get("Final_Status","")) != "Approved": continue
                try:
                    created = datetime.strptime(str(r.get("Created_At",""))[:10], "%d/%m/%Y")
                    if created < month_start: continue
                except Exception: continue
                lt = str(r.get("Request_Type",""))
                if lt in ("Paid","Emergency"): paid += int(r.get("Days_Requested",0) or 0)
                elif lt == "Sick":             sick += int(r.get("Days_Requested",0) or 0)
                elif lt == "Unpaid":           unpaid += int(r.get("Days_Requested",0) or 0)
                elif lt in ("Overtime_Planned","Overtime_Emergency"):
                    hrs  = float(r.get("Hours",0) or 0)
                    rate = float(r.get("OT_Rate",1.5) or 1.5)
                    ot_hrs     += hrs
                    ot_payment += hrs * rate

            rows_to_write.append([
                ec, emp.get("Full_Name",""), emp.get("Department",""),
                p, a, paid, sick, unpaid,
                round(ot_hrs,1), 1.5, round(ot_payment,1),
                now.strftime("%d/%m/%Y %H:%M")
            ])

        if rows_to_write:
            ws.append_rows(rows_to_write, value_input_option="USER_ENTERED")

        await q.edit_message_text(
            f"✅ Payroll generated for {len(rows_to_write)} employees.\n"
            f"Month: {now.strftime('%B %Y')}\n"
            f"Check the Payroll_Input tab in Google Sheets.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_payroll"), bm()]]));
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_payroll"), bm()]]));


async def payroll_view(update, context):
    q = update.callback_query; await q.answer()
    try:
        rows = get_sheet("Payroll_Input").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_payroll"), bm()]])); return
    if len(rows) <= 1:
        await q.edit_message_text("No payroll data yet. Tap ⚙️ Generate to create it.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_payroll"), bm()]])); return
    data_rows = rows[1:]  # skip header
    lines = [f"💰 Payroll — {len(data_rows)} records\n{'─'*28}"]
    for r in data_rows[:10]:
        ec = r[0] if len(r) > 0 else "?"
        nm = r[1][:15] if len(r) > 1 else "?"
        p  = r[3] if len(r) > 3 else "?"
        a  = r[4] if len(r) > 4 else "?"
        ot = r[8] if len(r) > 8 else "?"
        lines.append(f"{ec} {nm} P:{p} A:{a} OT:{ot}h")
    if len(data_rows) > 10: lines.append(f"... +{len(data_rows)-10} more (see sheet)")
    await q.edit_message_text("\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_payroll"), bm()]]))


# ══════════════════════════════════════════════════════════════════
#  5F. HR DAILY DASHBOARD (appended before menu for HR_Manager)
# ══════════════════════════════════════════════════════════════════

async def hr_dashboard_handler(update, context):
    """HR_Manager sees quick stats before their main menu."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading HR dashboard...")
    try:
        leave_rows = get_sheet("Leave_Log").get_all_records()
        emp_rows   = get_sheet("Employee_DB").get_all_records()
        now = datetime.now()

        pending_mine  = sum(1 for r in leave_rows if str(r.get("HR_Status","")) == "Pending"
                            and str(r.get("Final_Status","")) == "Pending")
        pending_dir   = sum(1 for r in leave_rows if str(r.get("Director_Status","")) == "Pending"
                            and str(r.get("Final_Status","")) == "Pending")
        new_today     = sum(1 for r in leave_rows
                            if str(r.get("Created_At",""))[:10] == now.strftime("%d/%m/%Y"))

        # Contracts expiring this month
        month_end = datetime(now.year, now.month + 1 if now.month < 12 else 1,
                             1 if now.month < 12 else 1)
        contracts_exp = 0
        for r in emp_rows:
            exp_str = str(r.get("Contract_Expiry_Date","")).strip()
            if not exp_str: continue
            try:
                exp = datetime.strptime(exp_str, "%d/%m/%Y")
                if now <= exp <= month_end: contracts_exp += 1
            except Exception: pass

        msg = (f"📊 HR Dashboard — {now.strftime('%d/%m/%Y')}\n{'─'*28}\n"
               f"🔴 Pending my review:   {pending_mine}\n"
               f"🟣 Pending Director:    {pending_dir}\n"
               f"🆕 New requests today:  {new_today}\n"
               f"📄 Contracts exp/month: {contracts_exp}\n"
               f"{'─'*28}")
        kb = [[InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")]]
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]));


def get_hr_tools_handlers():
    """All non-conversation HR tool handlers."""
    return [
        CallbackQueryHandler(all_leave_handler,       pattern="^menu_all_leave$"),
        CallbackQueryHandler(leave_list_handler,      pattern="^leave_list_"),
        CallbackQueryHandler(leave_search_emp_start,  pattern="^leave_search_emp$"),
        CallbackQueryHandler(lookup_emp_view,         pattern="^lookup_ec_"),
        CallbackQueryHandler(admin_menu_handler,      pattern="^menu_admin$"),
        CallbackQueryHandler(admin_list_handler,      pattern="^admin_list$"),
        CallbackQueryHandler(gen_letters_menu,        pattern="^menu_gen_letters$"),
        CallbackQueryHandler(letter_placeholder,      pattern="^letter_"),
        CallbackQueryHandler(payroll_menu,            pattern="^menu_payroll$"),
        CallbackQueryHandler(payroll_generate,        pattern="^payroll_generate$"),
        CallbackQueryHandler(payroll_view,            pattern="^payroll_view$"),
        CallbackQueryHandler(hr_dashboard_handler,    pattern="^menu_hr_dashboard$"),
    ]
