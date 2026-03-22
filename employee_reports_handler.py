"""
ROIN WORLD FZE -- Employee Self-Reports Handler
=================================================
Section 15 of FULL_SYSTEM_BUILD.md

Every employee can view:
- My Salary History (last 6 months)
- My Deductions
- My Overtime Hours
- My Leave Summary
- My Task Performance

Tab: Payroll_History (dummy data for testing)
Reads from: Leave_Log, Leave_Balance, Tasks_Log
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet


def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _br(): return InlineKeyboardButton("↩️ My Reports", callback_data="menu_my_reports")


def _get_emp_by_tid(tid):
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0: continue
            if r[1].strip() == str(tid):
                ec = r[0].strip()
                for j, e in enumerate(get_sheet("Employee_DB").get_all_values()):
                    if j == 0: continue
                    if e[0].strip() == ec:
                        return {"code": ec, "name": e[1].strip() if len(e) > 1 else ec,
                                "dept": e[6].strip() if len(e) > 6 else ""}
                return {"code": ec, "name": ec, "dept": ""}
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  MENU
# ══════════════════════════════════════════════════════════════════════════════

async def reports_menu_handler(update, context):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("💰 My Salary History", callback_data="rpt_salary")],
        [InlineKeyboardButton("📉 My Deductions",     callback_data="rpt_deductions")],
        [InlineKeyboardButton("🏖️ My Leave Summary",  callback_data="rpt_leave")],
        [InlineKeyboardButton("📋 My Task Performance",callback_data="rpt_tasks")],
        [_bm()],
    ]
    await q.edit_message_text("📊 My Reports\n\nSelect a report:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  SALARY HISTORY
# ══════════════════════════════════════════════════════════════════════════════

async def rpt_salary_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    try:
        rows = get_sheet("Payroll_History").get_all_records()
    except Exception:
        await q.edit_message_text("Payroll data not available yet.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    my = [r for r in rows if str(r.get("Emp_Code", "")).strip() == emp["code"]]
    if not my:
        await q.edit_message_text("No salary records found.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    lines = [f"💰 Salary History — {emp['name']}\n{'_' * 28}"]
    total_net = 0
    total_ded = 0
    for r in my[-6:]:
        month = r.get("Month", "")
        basic = float(r.get("Basic_Salary", 0) or 0)
        ded = float(r.get("Deductions", 0) or 0)
        bonus = float(r.get("Bonuses", 0) or 0)
        ot = float(r.get("OT_Payment", 0) or 0)
        net = float(r.get("Net_Salary", 0) or 0)
        total_net += net
        total_ded += ded
        lines.append(f"{month}: Basic {basic:,.0f} | Ded -{ded:,.0f} | "
                     f"Bon +{bonus:,.0f} | OT +{ot:,.0f} | Net: {net:,.0f}")

    avg = total_net / len(my[-6:]) if my else 0
    lines.append(f"\nAvg Net: {avg:,.0f} EGP")
    lines.append(f"Total Deductions: {total_ded:,.0f} EGP")

    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  DEDUCTIONS
# ══════════════════════════════════════════════════════════════════════════════

async def rpt_deductions_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    try:
        rows = get_sheet("Deduction_Log").get_all_records()
    except Exception:
        await q.edit_message_text("No deduction records.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    my = [r for r in rows if str(r.get("target_emp_code", "")).strip() == emp["code"]]
    if not my:
        await q.edit_message_text("No deductions found.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    lines = [f"📉 My Deductions — {emp['name']}\n{'_' * 28}"]
    total = 0
    for r in my[-10:]:
        amt = float(r.get("amount", 0) or 0)
        total += amt
        lines.append(f"{r.get('Date', '')} | {r.get('deduction_type', '')} | "
                     f"{amt:,.0f} EGP | {r.get('Final_Status', '')}")
    lines.append(f"\nTotal: {total:,.0f} EGP")

    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  LEAVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

async def rpt_leave_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    try:
        bal = get_sheet("Leave_Balance").get_all_records()
    except Exception:
        await q.edit_message_text("Leave data not available.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    my_bal = next((r for r in bal if str(r.get("Emp_Code", "")).strip() == emp["code"]), None)
    if not my_bal:
        await q.edit_message_text("No leave balance found.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    msg = (f"🏖️ Leave Summary — {emp['name']}\n{'_' * 28}\n\n"
           f"Annual:    {my_bal.get('Annual_Remaining', 0)} / {my_bal.get('Annual_Entitlement', 21)} days remaining\n"
           f"Sick:      {my_bal.get('Sick_Remaining', 0)} / {my_bal.get('Sick_Entitlement', 15)} days remaining\n"
           f"Emergency: {my_bal.get('Emergency_Remaining', 0)} / {my_bal.get('Emergency_Entitlement', 6)} days remaining\n"
           f"Unpaid:    {my_bal.get('Unpaid_Used', 0)} days used\n\n"
           f"Total balance: {my_bal.get('Total_Balance_Remaining', 0)} days")

    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  TASK PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

async def rpt_tasks_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    try:
        rows = get_sheet("Tasks_Log").get_all_values()
    except Exception:
        await q.edit_message_text("No task data available.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    my = [r for i, r in enumerate(rows) if i > 0 and len(r) > 10 and r[3].strip() == emp["code"]]
    if not my:
        await q.edit_message_text("No tasks assigned to you yet.",
                                  reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))
        return

    total = len(my)
    completed = sum(1 for r in my if r[10].strip() == "Completed")
    overdue = sum(1 for r in my if r[10].strip() == "Overdue")
    active = sum(1 for r in my if r[10].strip() in ("New", "In_Progress"))
    rate = f"{completed * 100 // total}%" if total else "0%"

    msg = (f"📋 Task Performance — {emp['name']}\n{'_' * 28}\n\n"
           f"Total assigned: {total}\n"
           f"✅ Completed:    {completed}\n"
           f"📌 Active:       {active}\n"
           f"⚠️ Overdue:      {overdue}\n"
           f"Completion rate: {rate}")

    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_br(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_reports_static_handlers():
    from telegram.ext import CallbackQueryHandler as CQH
    return [
        CQH(reports_menu_handler,    pattern="^menu_my_reports$"),
        CQH(rpt_salary_handler,      pattern="^rpt_salary$"),
        CQH(rpt_deductions_handler,  pattern="^rpt_deductions$"),
        CQH(rpt_leave_handler,       pattern="^rpt_leave$"),
        CQH(rpt_tasks_handler,       pattern="^rpt_tasks$"),
    ]
