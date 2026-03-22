"""
ROIN WORLD FZE — Director Features Handler
============================================
Section 2:
  2A. Daily Morning Brief (/dailybrief command)
  2B. Batch Approvals (Quick Batch)
  2C. Company Dashboard (real data)
  2D. Monthly PDF Report — see report_handler.py
  2E. Director Alerts
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler
from config import get_sheet, CURRENT_ATTENDANCE_TAB

def _bm():  return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bov(): return InlineKeyboardButton("↩️ Overview",   callback_data="menu_overview")

CHAINS = {"MGR_HR_DIR": ["manager","hr","director"], "MGR_HR": ["manager","hr"]}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_emp_info(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            return r[0].strip(), r[3].strip() if len(r) > 3 else "Employee"
    return None, None


def _get_today_attendance():
    """Returns dict: present/absent/leave/sick counts from current attendance tab."""
    try:
        ws  = get_sheet(CURRENT_ATTENDANCE_TAB)
        all_vals = ws.get_all_values()
        if len(all_vals) < 7:
            return {}
        today_col = 6 + (datetime.now().day - 1)  # col F = day 1
        counts = {"P":0,"A":0,"V":0,"S":0,"U":0,"B":0,"OFF":0,"H":0}
        for r in all_vals[6:]:  # row 7 onward
            if today_col < len(r):
                v = str(r[today_col]).strip().upper()
                if v in counts: counts[v] += 1
        return counts
    except Exception:
        return {}


def _get_pending_director_count():
    """Count requests waiting for Director approval."""
    try:
        rows = get_sheet("Leave_Log").get_all_values()
        count = 0
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 15 and r[15].strip() == "Pending":
                if len(r) > 13 and r[13].strip() == "Pending":
                    count += 1
        return count
    except Exception:
        return 0


def _get_pending_director_list():
    """Return list of rows where Director approval is pending."""
    try:
        rows = get_sheet("Leave_Log").get_all_values()
        pending = []
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 15 and r[15].strip() == "Pending":
                if len(r) > 13 and r[13].strip() == "Pending":
                    pending.append(r)
        return pending
    except Exception:
        return []


def _contracts_expiring(days=30):
    try:
        today = datetime.now().date()
        rows  = get_sheet("Employee_DB").get_all_records()
        count = 0
        for r in rows:
            exp = str(r.get("Contract_Expiry_Date","")).strip()
            if exp:
                try:
                    ed = datetime.strptime(exp, "%d/%m/%Y").date()
                    d  = (ed - today).days
                    if 0 <= d <= days: count += 1
                except Exception:
                    pass
        return count
    except Exception:
        return 0


def _expired_docs():
    try:
        today = datetime.now().date()
        rows  = get_sheet("Employee_Documents").get_all_records()
        count = 0
        for r in rows:
            exp = str(r.get("Expiry_Date","")).strip()
            if exp:
                try:
                    ed = datetime.strptime(exp, "%d/%m/%Y").date()
                    if ed < today: count += 1
                except Exception:
                    pass
        return count
    except Exception:
        return 0


def _ot_hours_this_month():
    try:
        rows  = get_sheet("Leave_Log").get_all_values()
        now   = datetime.now()
        total = 0.0
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) < 7: continue
            if r[2].strip() not in ("Overtime_Planned","Overtime_Emergency"): continue
            if len(r) > 15 and r[15].strip() == "Rejected": continue
            try:
                rd = datetime.strptime(r[3].strip(), "%d/%m/%Y").date()
                if rd.year == now.year and rd.month == now.month:
                    total += float(r[6]) if r[6] else 0
            except Exception:
                pass
        return total
    except Exception:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  2A. DAILY MORNING BRIEF
# ══════════════════════════════════════════════════════════════════════════════
async def daily_brief_cmd(update, context):
    """Handler for /dailybrief command."""
    tid  = str(update.effective_user.id)
    ec, role = _get_emp_info(tid)
    if role not in ("HR_Manager","Director"):
        await update.message.reply_text("❌ This command is for HR Manager and Director only.")
        return
    await update.message.reply_text("⏳ Generating daily brief...")
    await _send_brief(update.message.reply_text)


async def director_brief_cmd_handler(update, context):
    """Callback for menu_director_brief button."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating morning brief...")
    att    = _get_today_attendance()
    total  = sum(att.values()) or 1
    present= att.get("P",0)
    absent = att.get("A",0)
    leave  = att.get("V",0) + att.get("S",0) + att.get("U",0) + att.get("B",0)
    rate   = round(present / total * 100, 1) if total else 0
    rate_icon = "🟢" if rate >= 95 else "🟡" if rate >= 90 else "🔴"
    pending   = _get_pending_director_count()
    exp_30    = _contracts_expiring(30)
    exp_docs  = _expired_docs()
    ot_hrs    = _ot_hours_this_month()
    now       = datetime.now()
    msg = (f"☀️ Director Morning Brief\n{now.strftime('%A, %d %B %Y')}\n{'─'*32}\n"
           f"👥 Workforce Today:\n"
           f"   {rate_icon} Present:  {present}\n"
           f"   🔴 Absent:   {absent}\n"
           f"   🏖️ On Leave: {leave}\n"
           f"   Att. Rate:  {rate}%\n"
           f"{'─'*32}\n"
           f"📋 Pending MY Decisions: {pending}\n"
           f"📄 Contracts expiring 30d: {exp_30}\n"
           f"🗂️ Expired documents: {exp_docs}\n"
           f"⏰ OT this month: {ot_hrs:.1f} hrs")
    kb = [[InlineKeyboardButton("📋 Quick Batch", callback_data="menu_batch_approvals")],
          [_bov(), _bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def _send_brief(send_fn):
    att    = _get_today_attendance()
    total  = sum(att.values()) or 1
    present= att.get("P",0)
    absent = att.get("A",0)
    leave  = att.get("V",0) + att.get("S",0) + att.get("U",0) + att.get("B",0)
    rate   = round(present / total * 100, 1) if total else 0
    rate_icon = "🟢" if rate >= 95 else "🟡" if rate >= 90 else "🔴"
    pending   = _get_pending_director_count()
    exp_30    = _contracts_expiring(30)
    exp_docs  = _expired_docs()
    ot_hrs    = _ot_hours_this_month()
    now       = datetime.now()
    msg = (f"☀️ Director Morning Brief\n{now.strftime('%A, %d %B %Y')}\n{'─'*32}\n"
           f"👥 Workforce Today:\n"
           f"   {rate_icon} Present:  {present}\n"
           f"   🔴 Absent:   {absent}\n"
           f"   🏖️ On Leave: {leave}\n"
           f"   Att. Rate:  {rate}%\n"
           f"{'─'*32}\n"
           f"📋 Pending MY Decisions: {pending}\n"
           f"📄 Contracts expiring 30d: {exp_30}\n"
           f"🗂️ Expired documents: {exp_docs}\n"
           f"⏰ OT this month: {ot_hrs:.1f} hrs")
    await send_fn(msg)


# ══════════════════════════════════════════════════════════════════════════════
#  2B. BATCH APPROVALS
# ══════════════════════════════════════════════════════════════════════════════
async def batch_approvals_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading pending decisions...")
    try:
        pending = _get_pending_director_list()
        emps    = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not pending:
        await q.edit_message_text("✅ No items pending your decision.",
                                  reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]])); return
    emp_map = {str(e.get("Emp_Code","")).strip(): e.get("Full_Name","") for e in emps}
    TYPE_EMOJI = {
        "Paid":"🏖","Sick":"🤒","Emergency":"🚨","Unpaid":"📋",
        "Business_Trip":"🚗","Overtime_Planned":"⏰","Overtime_Emergency":"🚨",
        "Missing_Punch":"🖐","Early_Departure":"🚪",
    }
    lines = [f"📋 Quick Batch — {len(pending)} pending decisions\n{'─'*28}"]
    kb    = []
    for r in pending[:20]:
        rid  = r[0]; ec = r[1]; lt = r[2]
        name = emp_map.get(str(ec).strip(), ec)
        em   = TYPE_EMOJI.get(lt,"📋")
        if lt in ("Overtime_Planned","Overtime_Emergency","Early_Departure","Missing_Punch"):
            info = f"{r[3]}"
        else:
            info = f"{r[3]} to {r[4]} ({r[5]}d)"
        lines.append(f"{em} {rid} | {name} | {lt} | {info}")
        kb.append([
            InlineKeyboardButton(f"✅ {rid}", callback_data=f"batch_approve_{rid}"),
            InlineKeyboardButton(f"❌ {rid}", callback_data=f"batch_reject_{rid}"),
        ])
    if len(pending) > 20:
        lines.append(f"... +{len(pending)-20} more")
    kb.append([InlineKeyboardButton("✅ Approve All Shown", callback_data="batch_approve_all")])
    kb.append([_bov(), _bm()])
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def batch_approve_cb(update, context):
    q = update.callback_query; await q.answer()
    rid = q.data.replace("batch_approve_","")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        ws   = get_sheet("Leave_Log")
        rows = ws.get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == rid:
                ws.update_cell(i+1, 14, "Approved")  # Director_Status col 14
                ws.update_cell(i+1, 15, now)           # Director_Date col 15
                ws.update_cell(i+1, 16, "Approved")   # Final_Status col 16
                # Notify employee
                try:
                    ec = r[1]
                    for j, ur in enumerate(get_sheet("User_Registry").get_all_values()):
                        if j == 0: continue
                        if ur[0].strip() == ec.strip() and ur[1].strip():
                            await context.bot.send_message(
                                chat_id=ur[1].strip(),
                                text=f"🎉 Your request {rid} has been fully approved! ({now})")
                            break
                except Exception:
                    pass
                break
        await q.answer(f"✅ {rid} approved", show_alert=False)
        # Refresh batch view
        await batch_approvals_handler(update, context)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


async def batch_reject_cb(update, context):
    q = update.callback_query; await q.answer()
    rid = q.data.replace("batch_reject_","")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        ws   = get_sheet("Leave_Log")
        rows = ws.get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == rid:
                ws.update_cell(i+1, 14, "Rejected")
                ws.update_cell(i+1, 15, now)
                ws.update_cell(i+1, 16, "Rejected")
                ws.update_cell(i+1, 17, "Rejected by Director")
                try:
                    ec = r[1]
                    for j, ur in enumerate(get_sheet("User_Registry").get_all_values()):
                        if j == 0: continue
                        if ur[0].strip() == ec.strip() and ur[1].strip():
                            await context.bot.send_message(
                                chat_id=ur[1].strip(),
                                text=f"❌ Your request {rid} was rejected by Director. ({now})")
                            break
                except Exception:
                    pass
                break
        await q.answer(f"❌ {rid} rejected", show_alert=False)
        await batch_approvals_handler(update, context)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


async def batch_approve_all_cb(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Approving all pending items...")
    pending = _get_pending_director_list()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws  = get_sheet("Leave_Log")
    rows= ws.get_all_values()
    approved = 0
    try:
        for r in pending:
            rid = r[0]
            for i, row in enumerate(rows):
                if i == 0: continue
                if row[0].strip() == rid:
                    ws.update_cell(i+1, 14, "Approved")
                    ws.update_cell(i+1, 15, now)
                    ws.update_cell(i+1, 16, "Approved")
                    approved += 1
                    break
        await q.edit_message_text(
            f"✅ Batch approved {approved} requests. ({now})",
            reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  2C. COMPANY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
async def company_dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading company dashboard...")
    try:
        emps = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    total       = len(emps)
    active      = sum(1 for e in emps if str(e.get("Status","")).strip() == "Active")
    terminated  = sum(1 for e in emps if str(e.get("Status","")).strip() == "Terminated")
    on_probation= sum(1 for e in emps if str(e.get("Contract_Type","")).strip() == "Probation")
    # Department breakdown
    dept_counts = {}
    for e in emps:
        if str(e.get("Status","")).strip() != "Active": continue
        dept = str(e.get("Department","")).strip() or "Unknown"
        dept_counts[dept] = dept_counts.get(dept,0) + 1
    # Nationality breakdown (top 5)
    nat_counts = {}
    for e in emps:
        nat = str(e.get("Nationality","")).strip() or "Unknown"
        nat_counts[nat] = nat_counts.get(nat,0) + 1
    top_nat = sorted(nat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    # Contracts expiring
    exp_30 = _contracts_expiring(30)
    exp_60 = _contracts_expiring(60)
    # OT
    ot_hrs = _ot_hours_this_month()
    now    = datetime.now()
    msg    = (f"🏢 Company Dashboard\n{now.strftime('%B %Y')}\n{'─'*32}\n"
              f"👥 Workforce:\n"
              f"   Total:      {total}\n"
              f"   Active:     {active}\n"
              f"   Terminated: {terminated}\n"
              f"   Probation:  {on_probation}\n"
              f"{'─'*32}\n"
              f"🏢 By Department:\n")
    for dept, cnt in sorted(dept_counts.items(), key=lambda x: x[1], reverse=True):
        msg += f"   {dept}: {cnt}\n"
    msg += (f"{'─'*32}\n"
            f"🌍 Top Nationalities:\n")
    for nat, cnt in top_nat:
        msg += f"   {nat}: {cnt}\n"
    msg += (f"{'─'*32}\n"
            f"⚠️ Contracts expiring:\n"
            f"   30 days: {exp_30} | 60 days: {exp_60}\n"
            f"⏰ OT this month: {ot_hrs:.1f} hrs")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  2E. DIRECTOR ALERTS
# ══════════════════════════════════════════════════════════════════════════════
async def director_alerts_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Checking alerts...")
    alerts = []
    try:
        today = datetime.now().date()
        # Expired contracts
        emps = get_sheet("Employee_DB").get_all_records()
        for e in emps:
            if str(e.get("Status","")).strip() != "Active": continue
            exp = str(e.get("Contract_Expiry_Date","")).strip()
            if exp:
                try:
                    ed   = datetime.strptime(exp, "%d/%m/%Y").date()
                    days = (ed - today).days
                    if days < 0:
                        alerts.append(f"🔴 EXPIRED CONTRACT: {e.get('Full_Name','')} [{e.get('Emp_Code','')}] — expired {abs(days)}d ago")
                    elif days <= 7:
                        alerts.append(f"🟠 CONTRACT CRITICAL: {e.get('Full_Name','')} — {days}d left")
                    elif days <= 14:
                        alerts.append(f"🟡 CONTRACT URGENT: {e.get('Full_Name','')} — {days}d left")
                except Exception:
                    pass
        # Pending director decisions > 48hrs
        pending = _get_pending_director_list()
        if pending:
            alerts.append(f"📋 {len(pending)} requests waiting for YOUR decision")
        # Expired documents
        try:
            docs = get_sheet("Employee_Documents").get_all_records()
            exp_docs = [d for d in docs if _doc_expired(str(d.get("Expiry_Date","")).strip(), today)]
            if exp_docs:
                alerts.append(f"🗂️ {len(exp_docs)} expired documents require action")
        except Exception:
            pass
        # OT budget
        ot_hrs = _ot_hours_this_month()
        if ot_hrs > 35:
            alerts.append(f"⏰ OT WARNING: {ot_hrs:.1f}/40 hrs used this month")
    except Exception as e:
        alerts.append(f"Error loading data: {e}")
    if not alerts:
        msg = "✅ No active alerts. All systems normal."
    else:
        msg = f"⚠️ Director Alerts ({len(alerts)})\n{'─'*28}\n" + "\n".join(alerts)
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]]))


def _doc_expired(exp_str, today):
    if not exp_str or exp_str in ("-",""):
        return False
    try:
        return datetime.strptime(exp_str, "%d/%m/%Y").date() < today
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  VEHICLE LOG (Director view)
# ══════════════════════════════════════════════════════════════════════════════
async def vehicle_log_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading vehicle log...")
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]])); return
    if not rows:
        await q.edit_message_text("🚗 No vehicle trips recorded.",
                                  reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]])); return
    lines = [f"🚗 Vehicle Trip Log ({len(rows)} total)\n{'─'*28}"]
    status_icon = {"Requested":"📩","Manager_Approved":"✅","Assigned":"🚗",
                   "Departed":"🚀","Returned":"🏁","Cancelled":"❌"}
    for r in rows[-20:]:
        st = str(r.get("Status",""))
        lines.append(f"{status_icon.get(st,'❓')} {r.get('Trip_ID','')} | "
                     f"{r.get('Date','')} | {r.get('Requesting_Emp','')} | "
                     f"{r.get('From_Location','')}→{r.get('To_Location','')} | {st}")
    if len(rows) > 20:
        lines.append(f"... +{len(rows)-20} more trips")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bov(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_director_handlers():
    return [
        CommandHandler("dailybrief",           daily_brief_cmd),
        CallbackQueryHandler(director_brief_cmd_handler, pattern="^menu_director_brief$"),
        CallbackQueryHandler(batch_approvals_handler,    pattern="^menu_batch_approvals$"),
        CallbackQueryHandler(batch_approve_cb,           pattern="^batch_approve_(?!all)"),
        CallbackQueryHandler(batch_reject_cb,            pattern="^batch_reject_"),
        CallbackQueryHandler(batch_approve_all_cb,       pattern="^batch_approve_all$"),
        CallbackQueryHandler(company_dashboard_handler,  pattern="^menu_company_overview$"),
        CallbackQueryHandler(director_alerts_handler,    pattern="^menu_director_alerts$"),
        CallbackQueryHandler(vehicle_log_handler,        pattern="^menu_vehicle_log$"),
    ]
