"""
ROIN WORLD FZE — Reporting & Dashboards Handler
=================================================
Phase 8:
  8A. Director Daily Morning Brief (on-demand + scheduled)
  8B. Director Company Dashboard
  8C. Monthly PDF Report (auto-generated)
  8D. Director Alerts (on-demand check)
  8E. Kitchen Staffing View
  8F. Shift Coverage Alert (integrated into approval_handler)
"""

import io, os
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet, CURRENT_ATTENDANCE_TAB
from attendance_handler import get_my_attendance_summary
from fpdf import FPDF

def bm():   return InlineKeyboardButton("↩️ Main Menu",   callback_data="back_to_menu")
def bovw(): return InlineKeyboardButton("↩️ Overview",    callback_data="menu_overview")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(text):
    if not text: return ""
    text = str(text)
    for old, new in {"\u2014":"-","\u2013":"-","\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u00a0":" "}.items():
        text = text.replace(old, new)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _get_workforce_snapshot():
    """Return dict of workforce metrics from Employee_DB + current att sheet."""
    try:
        all_emp = get_sheet("Employee_DB").get_all_records()
        active   = [r for r in all_emp if str(r.get("Status","")).strip() not in ("Terminated","")]
        total    = len(active)
        present = absent = on_leave = 0
        for r in active:
            ec = str(r.get("Emp_Code","")).strip()
            try:
                s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
                if s:
                    today_day = datetime.now().day - 1
                    if today_day < len(s.get("days",[])):
                        st = s["days"][today_day][1]
                        if st == "P": present  += 1
                        elif st == "A": absent  += 1
                        elif st in ("V","S","U","B"): on_leave += 1
            except Exception: pass
        rate = round(present / (present+absent) * 100) if (present+absent) > 0 else 0
        return {"total":total,"present":present,"absent":absent,"on_leave":on_leave,"rate":rate}
    except Exception:
        return {"total":0,"present":0,"absent":0,"on_leave":0,"rate":0}


def _count_pending_dir():
    try:
        rows = get_sheet("Leave_Log").get_all_records()
        return sum(1 for r in rows if str(r.get("Director_Status","")) == "Pending"
                   and str(r.get("Final_Status","")) == "Pending")
    except Exception: return 0


def _contracts_expiring_count(days=30):
    try:
        today = datetime.now().date()
        rows  = get_sheet("Employee_DB").get_all_records()
        count = 0
        for r in rows:
            exp_str = str(r.get("Contract_Expiry_Date","")).strip()
            if not exp_str: continue
            try:
                exp = datetime.strptime(exp_str, "%d/%m/%Y").date()
                left = (exp - today).days
                if 0 <= left <= days: count += 1
            except Exception: pass
        return count
    except Exception: return 0


def _expired_docs_count():
    try:
        rows = get_sheet("Employee_Documents").get_all_records()
        today = datetime.now().date()
        count = 0
        for r in rows:
            if str(r.get("Status","")).strip().lower() == "renewed": continue
            exp_str = str(r.get("Expiry_Date","")).strip()
            if not exp_str: continue
            try:
                exp = datetime.strptime(exp_str, "%d/%m/%Y").date()
                if exp < today: count += 1
            except Exception: pass
        return count
    except Exception: return 0


def _ot_hours_this_month():
    try:
        rows = get_sheet("Leave_Log").get_all_records()
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        total = 0.0
        for r in rows:
            if str(r.get("Request_Type","")) not in ("Overtime_Planned","Overtime_Emergency"): continue
            if str(r.get("Final_Status","")) != "Approved": continue
            try:
                created = datetime.strptime(str(r.get("Created_At",""))[:10], "%d/%m/%Y")
                if created >= month_start:
                    total += float(r.get("Hours",0) or 0)
            except Exception: pass
        return round(total,1)
    except Exception: return 0


# ══════════════════════════════════════════════════════════════════
#  8A. DIRECTOR DAILY BRIEF
# ══════════════════════════════════════════════════════════════════

async def director_brief_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating morning brief...")
    wf      = _get_workforce_snapshot()
    pending = _count_pending_dir()
    contracts = _contracts_expiring_count(30)
    docs_exp  = _expired_docs_count()
    ot_hrs    = _ot_hours_this_month()

    rate_icon = "🟢" if wf["rate"] >= 95 else "🟡" if wf["rate"] >= 90 else "🔴"
    msg = (f"📊 Director Morning Brief\n{datetime.now().strftime('%d/%m/%Y %H:%M')}\n{'─'*28}\n\n"
           f"👥 WORKFORCE TODAY\n"
           f"  Total Active:   {wf['total']}\n"
           f"  ✅ Present:     {wf['present']}\n"
           f"  ❌ Absent:      {wf['absent']}\n"
           f"  🏖️ On Leave:   {wf['on_leave']}\n"
           f"  {rate_icon} Att Rate:   {wf['rate']}%\n\n"
           f"{'─'*28}\n"
           f"🔔 Pending my decisions: {pending}\n"
           f"📄 Contracts expiring (30d): {contracts}\n"
           f"❌ Expired documents: {docs_exp}\n"
           f"⏰ OT hours this month: {ot_hrs}h\n")
    kb = [[bovw(), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════
#  8B. COMPANY DASHBOARD
# ══════════════════════════════════════════════════════════════════

async def company_dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading company dashboard...")
    try:
        all_emp = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bovw(), bm()]])); return

    total    = len(all_emp)
    active   = sum(1 for r in all_emp if str(r.get("Status","")).strip() not in ("Terminated",""))
    term     = sum(1 for r in all_emp if str(r.get("Status","")).strip() == "Terminated")

    # Dept breakdown
    dept_counts = {}
    for r in all_emp:
        if str(r.get("Status","")).strip() == "Terminated": continue
        dept = str(r.get("Department","Unknown")).strip()
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    # Nationality breakdown
    nat_counts = {}
    for r in all_emp:
        if str(r.get("Status","")).strip() == "Terminated": continue
        nat = str(r.get("Nationality","Unknown")).strip()
        nat_counts[nat] = nat_counts.get(nat, 0) + 1

    ot_hrs      = _ot_hours_this_month()
    contracts   = _contracts_expiring_count(30)
    docs_exp    = _expired_docs_count()
    pending_dir = _count_pending_dir()

    msg = (f"🏢 Company Dashboard\n{'─'*28}\n"
           f"👥 Total Staff:    {total}\n"
           f"✅ Active:         {active}\n"
           f"❌ Terminated:     {term}\n"
           f"{'─'*28}\n🏢 By Department:\n")
    for dept, cnt in sorted(dept_counts.items(), key=lambda x: -x[1])[:10]:
        msg += f"  {dept}: {cnt}\n"
    msg += f"\n{'─'*28}\n🌍 By Nationality:\n"
    for nat, cnt in sorted(nat_counts.items(), key=lambda x: -x[1])[:5]:
        msg += f"  {nat}: {cnt}\n"
    msg += (f"\n{'─'*28}\n"
            f"⏰ OT this month:    {ot_hrs}h\n"
            f"📄 Contracts exp:    {contracts}\n"
            f"❌ Expired docs:     {docs_exp}\n"
            f"🔔 Pending (mine):   {pending_dir}")
    kb = [
        [InlineKeyboardButton("📊 Morning Brief",   callback_data="menu_director_brief")],
        [InlineKeyboardButton("📈 Monthly Report",  callback_data="menu_monthly_report")],
        [InlineKeyboardButton("⚠️ Director Alerts", callback_data="menu_director_alerts")],
        [bovw(), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════
#  8C. MONTHLY PDF REPORT
# ══════════════════════════════════════════════════════════════════

def _logo_path():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_logo.png")
    return p if os.path.exists(p) else None


def _generate_monthly_report_pdf():
    """Generate monthly PDF report with 8 sections."""
    now  = datetime.now()
    logo = _logo_path()

    # Collect data
    try: all_emp = get_sheet("Employee_DB").get_all_records()
    except Exception: all_emp = []
    try: leave_rows = get_sheet("Leave_Log").get_all_records()
    except Exception: leave_rows = []

    active  = [r for r in all_emp if str(r.get("Status","")).strip() not in ("Terminated","")]
    month_start = datetime(now.year, now.month, 1)

    # Attendance stats
    present_total = absent_total = 0
    for r in active[:50]:  # limit to avoid timeout
        ec = str(r.get("Emp_Code","")).strip()
        try:
            s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
            if s: present_total += s["present"]; absent_total += s["absent"]
        except Exception: pass
    att_rate = round(present_total/(present_total+absent_total)*100) if (present_total+absent_total)>0 else 0

    # Leave by type
    leave_by_type = {}
    ot_total = 0.0
    for r in leave_rows:
        if str(r.get("Final_Status","")) != "Approved": continue
        try:
            created = datetime.strptime(str(r.get("Created_At",""))[:10], "%d/%m/%Y")
            if created < month_start: continue
        except Exception: continue
        lt = str(r.get("Request_Type",""))
        leave_by_type[lt] = leave_by_type.get(lt,0) + int(r.get("Days_Requested",0) or 0)
        if lt in ("Overtime_Planned","Overtime_Emergency"):
            ot_total += float(r.get("Hours",0) or 0)

    # Contracts
    contracts_exp = _contracts_expiring_count(30)
    docs_exp      = _expired_docs_count()

    # Build PDF
    class ReportPDF(FPDF):
        def header(self):
            if logo: self.image(logo, x=85, y=8, w=25); self.ln(28)
            else: self.ln(10)
            self.set_font("Helvetica","B",14)
            self.cell(0,6,"ROIN WORLD FZE EGYPT BRANCH",new_x="LMARGIN",new_y="NEXT",align="C")
            self.set_font("Helvetica","",9)
            self.cell(0,5,_safe(f"Monthly HR Report — {now.strftime('%B %Y')}"),
                      new_x="LMARGIN",new_y="NEXT",align="C")
            self.line(15,self.get_y()+2,195,self.get_y()+2); self.ln(4)
        def footer(self):
            self.set_y(-12); self.set_font("Helvetica","I",7)
            self.cell(0,4,_safe(f"ROIN WORLD FZE — Confidential — {now.strftime('%d/%m/%Y')}"),align="C")

    pdf = ReportPDF(); pdf.add_page()

    def section(title):
        pdf.set_fill_color(220,220,220); pdf.set_font("Helvetica","B",12)
        pdf.cell(0,8,f"  {_safe(title)}",new_x="LMARGIN",new_y="NEXT",fill=True); pdf.ln(2)

    def row_item(label, value):
        pdf.set_font("Helvetica","B",10); pdf.cell(70,7,f"  {_safe(label)}:")
        pdf.set_font("Helvetica","",10); pdf.cell(0,7,_safe(str(value)),new_x="LMARGIN",new_y="NEXT")

    # 1. Executive Summary
    section("1. EXECUTIVE SUMMARY")
    rate_color = "GOOD" if att_rate >= 95 else "NEEDS ATTENTION" if att_rate >= 90 else "CRITICAL"
    row_item("Reporting Period", now.strftime("%B %Y"))
    row_item("Attendance Rate", f"{att_rate}% — {rate_color}")
    row_item("OT Hours This Month", f"{round(ot_total,1)}h")
    row_item("Contracts Expiring Soon", contracts_exp)
    row_item("Expired Documents", docs_exp)
    pdf.ln(4)

    # 2. Headcount
    section("2. HEADCOUNT ANALYSIS")
    row_item("Total Employees", len(all_emp))
    row_item("Active", len(active))
    row_item("Terminated", len(all_emp)-len(active))
    pdf.ln(4)

    # 3. Attendance
    section("3. ATTENDANCE ANALYSIS")
    row_item("Present Days (sample)", present_total)
    row_item("Absent Days (sample)", absent_total)
    row_item("Overall Rate", f"{att_rate}%")
    pdf.ln(4)

    # 4. Leave
    section("4. LEAVE ANALYSIS")
    for lt, cnt in leave_by_type.items():
        row_item(lt.replace("_"," "), f"{cnt} days")
    pdf.ln(4)

    # 5. Contracts
    section("5. CONTRACT STATUS")
    row_item("Expiring within 30 days", contracts_exp)
    row_item("Expired Documents", docs_exp)
    pdf.ln(4)

    # 6. Performance (placeholder)
    section("6. PERFORMANCE OVERVIEW")
    pdf.set_font("Helvetica","I",10)
    pdf.cell(0,7,"  Performance evaluation data will appear here once Phase 9 evaluations are completed.",
             new_x="LMARGIN",new_y="NEXT"); pdf.ln(4)

    # 7. Document Compliance
    section("7. DOCUMENT COMPLIANCE")
    row_item("Expired Documents", docs_exp)
    row_item("Compliant (estimated)", f"{max(0,len(active)-docs_exp)}/{len(active)}")
    pdf.ln(4)

    # 8. OT & Payroll
    section("8. OVERTIME & PAYROLL SUMMARY")
    row_item("Total OT Hours", round(ot_total,1))
    row_item("OT Rate", "1.5x")
    row_item("OT Equivalent Hours", round(ot_total*1.5, 1))
    pdf.ln(4)

    return pdf.output()


async def monthly_report_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating monthly report PDF...")
    try:
        pdf_bytes = _generate_monthly_report_pdf()
        now = datetime.now()
        filename = f"ROIN-Monthly-Report-{now.strftime('%Y-%m')}.pdf"
        from drive_utils import upload_to_drive
        drive_url = upload_to_drive(pdf_bytes, filename, "reports")
        if drive_url:
            await q.edit_message_text(
                f"✅ Monthly report generated for {now.strftime('%B %Y')}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📄 View PDF", url=drive_url)],
                    [bovw(), bm()]]))
        else:
            await q.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename=filename,
                caption=f"📈 Monthly HR Report — {now.strftime('%B %Y')}")
            await q.edit_message_text(
                f"✅ Monthly report generated for {now.strftime('%B %Y')}.",
                reply_markup=InlineKeyboardMarkup([[bovw(), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bovw(), bm()]]))


# ══════════════════════════════════════════════════════════════════
#  8D. DIRECTOR ALERTS
# ══════════════════════════════════════════════════════════════════

async def director_alerts_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Checking alerts...")
    alerts = []

    # Contract expired no decision
    try:
        today = datetime.now().date()
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Status","")).strip() == "Terminated": continue
            exp_str = str(r.get("Contract_Expiry_Date","")).strip()
            if not exp_str: continue
            try:
                exp = datetime.strptime(exp_str, "%d/%m/%Y").date()
                if exp < today:
                    alerts.append(f"❌ Contract EXPIRED: {r.get('Full_Name','')} ({r.get('Emp_Code','')}) since {exp_str}")
            except Exception: pass
    except Exception: pass

    # Expired documents
    try:
        today = datetime.now().date()
        for r in get_sheet("Employee_Documents").get_all_records():
            if str(r.get("Status","")).strip().lower() == "renewed": continue
            exp_str = str(r.get("Expiry_Date","")).strip()
            if not exp_str: continue
            try:
                exp = datetime.strptime(exp_str, "%d/%m/%Y").date()
                if exp < today:
                    alerts.append(f"⚠️ Doc EXPIRED: {r.get('Emp_Code','')} {r.get('Document_Type','')} since {exp_str}")
            except Exception: pass
    except Exception: pass

    # Pending director decisions
    pending_dir = _count_pending_dir()
    if pending_dir > 0:
        alerts.append(f"🔔 {pending_dir} request(s) awaiting your approval")

    if not alerts:
        msg = "✅ No critical alerts at this time."
    else:
        msg = f"⚠️ Director Alerts ({len(alerts)})\n{'─'*28}\n\n" + "\n\n".join(alerts[:15])
    kb = [[bovw(), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════
#  8E. KITCHEN STAFFING VIEW
# ══════════════════════════════════════════════════════════════════

KITCHENS = [
    "Russian Kitchen", "Egyptian Kitchen", "Pastry & Soup Kitchen",
    "Bakery & FoodTruck", "Bakery", "Office",
    "Warehouse", "Transportation", "Steward / Cleaning",
    "Packaging & Delivery", "Purchasing / Supply", "Quality Control",
    "Safety & OH", "Translation", "Operations", "Housing",
    "Finance", "HR", "Administration",
]

async def kitchen_staffing_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading kitchen staffing...")
    try:
        all_emp = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bovw(), bm()]])); return

    msg = f"🍳 Kitchen Staffing — {datetime.now().strftime('%d/%m/%Y')}\n{'─'*28}\n"
    for kitchen in KITCHENS:
        dept_emp = [r for r in all_emp
                    if str(r.get("Department","")).strip() == kitchen
                    and str(r.get("Status","")).strip() not in ("Terminated","")]
        expected = len(dept_emp)
        present = 0
        for r in dept_emp:
            ec = str(r.get("Emp_Code","")).strip()
            try:
                s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
                if s and s.get("days"):
                    today_idx = datetime.now().day - 1
                    if today_idx < len(s["days"]):
                        st = s["days"][today_idx][1]
                        if st == "P": present += 1
            except Exception: pass
        rate = round(present/expected*100) if expected > 0 else 0
        flag = "🔴" if rate < 80 else "🟡" if rate < 90 else "🟢"
        msg += (f"\n{flag} {kitchen}\n"
                f"   Present: {present}/{expected} ({rate}%)")
        if rate < 80:
            msg += f" ⚠️ UNDERSTAFFED"
    kb = [[InlineKeyboardButton("↩️ Company Dashboard", callback_data="menu_company_overview"), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


def get_report_handlers():
    return [
        CallbackQueryHandler(director_brief_handler,   pattern="^menu_director_brief$"),
        CallbackQueryHandler(company_dashboard_handler,pattern="^menu_company_overview$"),
        CallbackQueryHandler(monthly_report_handler,   pattern="^menu_monthly_report$"),
        CallbackQueryHandler(director_alerts_handler,  pattern="^menu_director_alerts$"),
        CallbackQueryHandler(kitchen_staffing_handler, pattern="^menu_kitchen_staffing$"),
    ]
