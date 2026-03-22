"""
ROIN WORLD FZE — Manager Features Handler
==========================================
Phase 4:
  4A. My Team View — present/absent/leave today, pending approvals, contracts expiring
  4B. Smart Leave Approval Context — shown in pending_view (integrated there)
  4C. Team Attendance View — team member daily status + monthly summary
  4D. Department Drill-Down — attendance by dept, top absent, OT usage

Exposed functions used by bot.py:
  team_overview_handler, team_detail_handler
  dept_drilldown_handler, dept_dept_handler
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet, CURRENT_ATTENDANCE_TAB
from attendance_handler import (get_my_attendance_summary, get_attendance_sheet,
    DATA_START_ROW, CODE_COL, DAY_1_COL, ST_PRESENT, ST_ABSENT)

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_role_ec(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            return r[0].strip(), r[3].strip() if len(r) > 3 else "Employee"
    return None, "Employee"


def _get_team(my_code, my_role):
    """Return list of employee dicts managed by this user."""
    team = []
    for r in get_sheet("Employee_DB").get_all_records():
        ec = str(r.get("Emp_Code", "")).strip()
        if not ec: continue
        if my_role == "Supervisor" and str(r.get("Supervisor_Code", "")).strip() == str(my_code):
            team.append(r)
        elif my_role in ("Direct_Manager", "HR_Manager") and str(r.get("Manager_Code", "")).strip() == str(my_code):
            team.append(r)
        elif my_role == "HR_Staff":
            team.append(r)  # HR sees all
    return team


def _today_status_from_att(ec):
    """Return today's attendance status for an employee from the current tab."""
    try:
        ws   = get_attendance_sheet(CURRENT_ATTENDANCE_TAB)
        data = ws.get_all_values()
        today_col = DAY_1_COL - 1 + (datetime.now().day - 1)
        for i, row in enumerate(data):
            if i < DATA_START_ROW - 1: continue
            if len(row) >= CODE_COL and str(row[CODE_COL - 1]).strip() == str(ec):
                if today_col < len(row):
                    return str(row[today_col]).strip().upper() or "—"
                return "—"
    except Exception:
        pass
    return "?"


def _count_pending_for_manager(my_code, my_role):
    """Count leave requests where this manager's approval is pending."""
    try:
        rows = get_sheet("Leave_Log").get_all_values()
        if not rows: return 0
        count = 0
        for row in rows[1:]:
            if len(row) < 16: continue
            emp_ec = str(row[1]).strip()
            mgr_status = str(row[9]).strip()
            final = str(row[15]).strip()
            if final != "Pending": continue
            if mgr_status == "Pending":
                # Check if this manager manages this employee
                for r in get_sheet("Employee_DB").get_all_records():
                    if str(r.get("Emp_Code","")).strip() == emp_ec:
                        if str(r.get("Manager_Code","")).strip() == str(my_code):
                            count += 1
                        break
        return count
    except Exception:
        return 0


def _contracts_expiring(team, days=30):
    """Return list of (name, code, days_left) where contract expires within N days."""
    expiring = []
    today = datetime.now().date()
    for r in team:
        exp_str = str(r.get("Contract_Expiry_Date", "")).strip()
        if not exp_str or exp_str == "-": continue
        try:
            exp_date = datetime.strptime(exp_str, "%d/%m/%Y").date()
            left = (exp_date - today).days
            if 0 <= left <= days:
                expiring.append((r.get("Full_Name", "?"), str(r.get("Emp_Code","")), left))
        except Exception:
            pass
    return sorted(expiring, key=lambda x: x[2])


# ── 4A. My Team View ─────────────────────────────────────────────────────────

async def team_overview_handler(update, context):
    """Show today's team snapshot: present/absent/leave, pending approvals, expiring contracts."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading team overview...")
    my_code, my_role = _get_role_ec(str(q.from_user.id))
    if my_role not in ("Supervisor", "Direct_Manager", "HR_Staff", "HR_Manager"):
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_team"), bm()]])); return
    team = _get_team(my_code, my_role)
    if not team:
        await q.edit_message_text("ℹ️ No team members found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_team"), bm()]])); return

    # Today's attendance snapshot
    status_map = {}
    for r in team:
        ec = str(r.get("Emp_Code","")).strip()
        status_map[ec] = _today_status_from_att(ec)

    present = [ec for ec, st in status_map.items() if st == ST_PRESENT]
    absent  = [ec for ec, st in status_map.items() if st == ST_ABSENT]
    on_leave= [ec for ec, st in status_map.items() if st in ("V","S","U","B")]
    off_day = [ec for ec, st in status_map.items() if st in ("OFF","H")]
    unknown = [ec for ec, st in status_map.items() if st in ("—","?","")]

    # Pending approvals count
    pending_count = _count_pending_for_manager(my_code, my_role)

    # Contracts expiring within 30 days
    expiring = _contracts_expiring(team, days=30)

    # Build name lookup
    name_of = {str(r.get("Emp_Code","")).strip(): r.get("Full_Name","?") for r in team}

    msg = (f"👥 My Team — Today ({datetime.now().strftime('%d/%m/%Y')})\n{'─'*28}\n"
           f"✅ Present:      {len(present)}\n"
           f"❌ Absent:       {len(absent)}\n"
           f"🏖️ On Leave:    {len(on_leave)}\n"
           f"📴 Off/Holiday: {len(off_day)}\n"
           f"❓ Unknown:     {len(unknown)}\n"
           f"{'─'*28}\n"
           f"🔔 My Pending Approvals: {pending_count}\n"
           f"{'─'*28}\n")

    if absent:
        absent_names = ", ".join(name_of.get(ec, ec) for ec in absent[:10])
        msg += f"❌ Absent today:\n{absent_names}\n\n"

    if expiring:
        msg += "⚠️ Contracts expiring (30 days):\n"
        for nm, ec, left in expiring[:5]:
            msg += f"  • {nm} ({ec}) — {left} days\n"

    kb = [
        [InlineKeyboardButton("👥 Team Attendance Detail", callback_data="team_att_detail")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ── 4C. Team Attendance Detail ────────────────────────────────────────────────

async def team_att_detail(update, context):
    """List team members with today's status; tap for monthly summary."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading...")
    my_code, my_role = _get_role_ec(str(q.from_user.id))
    team = _get_team(my_code, my_role)
    if not team:
        await q.edit_message_text("ℹ️ No team members.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_team"), bm()]])); return

    STATUS_ICON = {ST_PRESENT:"✅","A":"❌","V":"🏖️","S":"🤒","U":"⛔","B":"✈️",
                   "OFF":"📴","H":"🎌","—":"❓","?":"❓","":"❓"}
    kb = []
    for r in team[:20]:
        ec   = str(r.get("Emp_Code","")).strip()
        name = r.get("Full_Name", ec)
        st   = _today_status_from_att(ec)
        icon = STATUS_ICON.get(st, st)
        kb.append([InlineKeyboardButton(f"{icon} {name} ({st})", callback_data=f"team_mem_{ec}")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_team_overview"), bm()])
    await q.edit_message_text(
        f"👥 Team — {datetime.now().strftime('%d/%m/%Y')}",
        reply_markup=InlineKeyboardMarkup(kb))


async def team_member_summary(update, context):
    """Show monthly attendance summary for a specific team member."""
    q = update.callback_query; await q.answer()
    ec = q.data.replace("team_mem_", "")
    await q.edit_message_text("⏳ Loading...")
    try:
        summary = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
    except Exception:
        summary = None
    if not summary:
        await q.edit_message_text(f"No attendance data found for {ec}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="team_att_detail"), bm()]])); return
    # Get name
    name = ec
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code","")).strip() == str(ec):
                name = r.get("Full_Name", ec); break
    except Exception: pass

    now = datetime.now()
    # Compact day-by-day
    chunks = [f"{d}:{s}" for d, s in summary.get("days", [])]
    lines = []; cur = ""
    for ch in chunks:
        if len(cur) + len(ch) + 1 > 50:
            lines.append(cur.strip()); cur = ch
        else:
            cur += (" " if cur else "") + ch
    if cur: lines.append(cur.strip())
    day_block = "\n".join(lines)

    msg = (f"🕐 {name}\n{now.strftime('%B %Y')}\n{'─'*28}\n"
           f"✅ Present:      {summary['present']}\n"
           f"❌ Absent:       {summary['absent']}\n"
           f"🏖️ Leave:       {summary['leave']}\n"
           f"📴 Off:          {summary['off']}\n"
           f"🎌 Holiday:      {summary['holiday']}\n"
           f"{'─'*28}\n"
           f"📈 Rate:         {summary['rate']}%")
    if day_block:
        msg += f"\n\n📅 Day-by-Day:\n{day_block}"
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="team_att_detail"), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ── 4D. Department Drill-Down ─────────────────────────────────────────────────

async def dept_drilldown_handler(update, context):
    """Show list of departments for drill-down."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading departments...")
    try:
        depts = sorted(set(str(r.get("Department","")).strip()
                           for r in get_sheet("Employee_DB").get_all_records()
                           if str(r.get("Department","")).strip()))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), bm()]])); return
    kb = [[InlineKeyboardButton(f"🏢 {d}", callback_data=f"dept_dd_{d}")] for d in depts]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), bm()])
    await q.edit_message_text("📊 Department Attendance Drill-Down\n\nSelect department:",
                               reply_markup=InlineKeyboardMarkup(kb))


async def dept_dept_handler(update, context):
    """Show attendance stats for a department."""
    q = update.callback_query; await q.answer()
    dept = q.data.replace("dept_dd_", "")
    await q.edit_message_text(f"⏳ Loading {dept}...")
    try:
        all_emp = get_sheet("Employee_DB").get_all_records()
        dept_emps = [r for r in all_emp if str(r.get("Department","")).strip() == dept]
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_dept_drilldown"), bm()]])); return

    present = absent = leave = off = 0
    top_absent = []
    for r in dept_emps:
        ec = str(r.get("Emp_Code","")).strip()
        try:
            s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
            if s:
                present += s["present"]
                absent  += s["absent"]
                leave   += s["leave"]
                off     += s["off"]
                if s["absent"] > 0:
                    top_absent.append((r.get("Full_Name", ec), s["absent"]))
        except Exception:
            pass

    total_work = present + absent + leave
    rate = round(present / total_work * 100) if total_work > 0 else 0
    top_absent.sort(key=lambda x: x[1], reverse=True)

    msg = (f"📊 {dept}\n{'─'*28}\n"
           f"👥 Employees:  {len(dept_emps)}\n"
           f"✅ Present:    {present}\n"
           f"❌ Absent:     {absent}\n"
           f"🏖️ Leave:     {leave}\n"
           f"📴 Off:        {off}\n"
           f"📈 Rate:       {rate}%\n"
           f"{'─'*28}\n")
    if top_absent:
        msg += "Top Absentees this month:\n"
        for nm, cnt in top_absent[:5]:
            msg += f"  • {nm}: {cnt} days\n"
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_dept_drilldown"), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ── Smart Leave Approval Context ──────────────────────────────────────────────

def get_smart_leave_context(emp_ec, start_date_str, days_requested):
    """
    Return a string with context for a leave request to help manager decide.
    Called from approval_handler.py pending_view_handler.
    """
    try:
        lines = []
        all_emp = get_sheet("Employee_DB").get_all_records()
        emp = next((r for r in all_emp if str(r.get("Emp_Code","")).strip() == emp_ec), None)
        if not emp: return ""

        # Leave balance
        bal = str(emp.get("Annual_Leave_Balance","")).strip()
        if bal:
            lines.append(f"📊 Leave balance: {bal} days (uses {days_requested})")

        # Absent count this month
        try:
            s = get_my_attendance_summary(emp_ec, CURRENT_ATTENDANCE_TAB)
            if s:
                lines.append(f"📅 Absent this month: {s['absent']} day(s)")
        except Exception:
            pass

        # Same-day conflicts (same department off that day)
        try:
            dept = str(emp.get("Department","")).strip()
            dept_emps = [r for r in all_emp if str(r.get("Department","")).strip() == dept and
                         str(r.get("Emp_Code","")).strip() != emp_ec]
            leave_rows = get_sheet("Leave_Log").get_all_records()
            same_day = 0
            for row in leave_rows:
                if str(row.get("Final_Status","")) == "Approved":
                    # Check overlap with requested dates
                    try:
                        rd_start = datetime.strptime(str(row.get("Start_Date","")), "%d/%m/%Y")
                        rd_end   = datetime.strptime(str(row.get("End_Date","")), "%d/%m/%Y")
                        req_start = datetime.strptime(start_date_str, "%d/%m/%Y")
                        if rd_start <= req_start <= rd_end:
                            req_ec = str(row.get("Emp_Code","")).strip()
                            if any(str(r.get("Emp_Code","")).strip() == req_ec for r in dept_emps):
                                same_day += 1
                    except Exception:
                        pass
            if same_day > 0:
                lines.append(f"⚠️ {same_day} other(s) from {dept} off on that day")
        except Exception:
            pass

        return "\n".join(lines)
    except Exception:
        return ""


def get_manager_handlers():
    return [
        CallbackQueryHandler(team_overview_handler,   pattern="^menu_team_overview$"),
        CallbackQueryHandler(team_att_detail,         pattern="^team_att_detail$"),
        CallbackQueryHandler(team_member_summary,     pattern="^team_mem_"),
        CallbackQueryHandler(dept_drilldown_handler,  pattern="^menu_dept_drilldown$"),
        CallbackQueryHandler(dept_dept_handler,       pattern="^dept_dd_"),
    ]
