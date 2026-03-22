"""
ROIN WORLD FZE — Safety & Occupational Health Handler
======================================================
Section 4 — New role: Safety_Manager

4B. Periodic Maintenance Log
4C. Incident Reports
4D. Safety Lectures for ALL employees
4E. Training Courses
4F. Safety Dashboard

Sheet tabs:
  Safety_Maintenance_Log: Log_ID, Date, Location, Equipment, Type,
    Description, Issue_Found, Solution, Responsible_Employee,
    Completion_Date, Time_To_Resolve, Cost, Photo_Before, Photo_After,
    Status, Priority
  Safety_Incident_Log: Incident_ID, Date, Time, Location, Type,
    Description, Employees_Involved, Witnesses, Immediate_Action,
    Root_Cause, Corrective_Action, Preventive_Action,
    Investigation_Date, Investigator, Photos, Report_PDF_Link,
    Status, Severity
  Safety_Lectures: Lecture_ID, Date, Title, Topic_Category, Instructor,
    Duration_Hours, Target_Department, Attendees_JSON, Total_Attended,
    Total_Expected, Attendance_Rate, Certificate_Photo,
    Materials_Link, Next_Due_Date
  Training_Log: Course_ID, Title, Provider, Date_Start, Date_End,
    Duration_Hours, Instructor, Cost, Attendees_JSON,
    Certificate_Required, Certificates_Uploaded, Status
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm():  return InlineKeyboardButton("↩️ Main Menu",   callback_data="back_to_menu")
def _bsf(): return InlineKeyboardButton("↩️ Safety Menu", callback_data="menu_safety")

# ── States ────────────────────────────────────────────────────────────────────
# Maintenance
MAINT_LOC    = 1400; MAINT_EQUIP  = 1401; MAINT_TYPE   = 1402
MAINT_DESC   = 1403; MAINT_PRI    = 1404; MAINT_CONFIRM= 1405
# Incident
INC_DATE     = 1420; INC_TIME     = 1421; INC_LOC      = 1422
INC_TYPE     = 1423; INC_DESC     = 1424; INC_SEVERITY = 1425
INC_ACTION   = 1426; INC_CONFIRM  = 1427
# Lecture
LECT_TITLE   = 1440; LECT_CAT     = 1441; LECT_DATE    = 1442
LECT_DEPT    = 1443; LECT_INSTR   = 1444; LECT_HOURS   = 1445
LECT_CONFIRM = 1446
# Training
TRAIN_TITLE  = 1460; TRAIN_PROV   = 1461; TRAIN_DATE   = 1462
TRAIN_HOURS  = 1463; TRAIN_CONFIRM= 1464

MAINT_TYPES   = ["Routine_Inspection","Repair","Emergency_Fix","Replacement"]
PRIORITIES    = ["Low","Medium","High","Critical"]
INC_TYPES     = ["Injury","Near_Miss","Fire","Spill","Equipment_Failure","Other"]
SEVERITIES    = ["Minor","Moderate","Major","Critical"]
LECT_CATS     = ["Fire_Safety","First_Aid","PPE","Food_Safety","Chemical_Handling","General"]
LOCATIONS     = ["Kitchen","Warehouse","Office","Site","Other"]

PRIO_ICON = {"Low":"🟢","Medium":"🟡","High":"🟠","Critical":"🔴"}
SEV_ICON  = {"Minor":"🟡","Moderate":"🟠","Major":"🔴","Critical":"💀"}
STATUS_ICON = {"Open":"📂","In_Progress":"⚙️","Resolved":"✅","Closed":"🔒","Escalated":"⚠️"}


def _get_emp_code(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _gen_id(tab, col, prefix):
    ids = get_sheet(tab).col_values(col)
    yr  = datetime.now().strftime("%Y")
    px  = f"{prefix}-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _ensure_tab(tab, headers):
    """Create tab with headers if it doesn't exist."""
    try:
        get_sheet(tab)
    except Exception:
        try:
            from config import WORKBOOK
            ws = WORKBOOK.add_worksheet(title=tab, rows=1000, cols=len(headers))
            ws.append_row(headers)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  SAFETY MENU
# ══════════════════════════════════════════════════════════════════════════════
async def safety_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("🔧 Maintenance Log",    callback_data="menu_safety_maint")],
        [InlineKeyboardButton("⚠️ Incident Reports",  callback_data="menu_safety_incidents")],
        [InlineKeyboardButton("📋 Safety Lectures",    callback_data="menu_safety_lectures")],
        [InlineKeyboardButton("🎓 Training Courses",   callback_data="menu_safety_training")],
        [InlineKeyboardButton("📊 Safety Dashboard",   callback_data="menu_safety_dashboard")],
        [_bm()],
    ]
    await q.edit_message_text("🛡️ Safety & Occupational Health\n\nSelect area:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  MAINTENANCE LOG
# ══════════════════════════════════════════════════════════════════════════════
async def maint_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("➕ New Entry",      callback_data="maint_new")],
        [InlineKeyboardButton("📂 Open Issues",    callback_data="maint_list_open")],
        [InlineKeyboardButton("✅ Resolved",        callback_data="maint_list_resolved")],
        [InlineKeyboardButton("⚠️ Overdue",         callback_data="maint_list_overdue")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_safety"), _bm()],
    ]
    await q.edit_message_text("🔧 Maintenance Log\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def maint_new_start(update, context):
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton(loc, callback_data=f"maint_loc_{loc}")] for loc in LOCATIONS]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_safety_maint"), _bm()])
    await q.edit_message_text("🔧 New Maintenance Entry\n\nSelect location:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_LOC


async def maint_loc_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["maint_loc"] = q.data.replace("maint_loc_","")
    await q.edit_message_text(f"Location: {context.user_data['maint_loc']}\n\nEnter equipment/area name:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return MAINT_EQUIP


async def maint_equip_inp(update, context):
    context.user_data["maint_equip"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(t, callback_data=f"maint_type_{t}")] for t in MAINT_TYPES]
    kb.append([_bm()])
    await update.message.reply_text("Select type:", reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_TYPE


async def maint_type_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["maint_type"] = q.data.replace("maint_type_","")
    await q.edit_message_text("Describe the issue/work needed:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return MAINT_DESC


async def maint_desc_inp(update, context):
    context.user_data["maint_desc"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(f"{PRIO_ICON.get(p,'')} {p}", callback_data=f"maint_pri_{p}")]
          for p in PRIORITIES]
    kb.append([_bm()])
    await update.message.reply_text("Select priority:", reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_PRI


async def maint_pri_cb(update, context):
    q = update.callback_query; await q.answer()
    pri = q.data.replace("maint_pri_","")
    context.user_data["maint_pri"] = pri
    loc  = context.user_data.get("maint_loc","")
    equip= context.user_data.get("maint_equip","")
    mtype= context.user_data.get("maint_type","")
    desc = context.user_data.get("maint_desc","")
    summary = (f"🔧 Maintenance Entry\n{'─'*24}\n"
               f"Location:  {loc}\nEquipment: {equip}\n"
               f"Type:      {mtype}\nPriority:  {PRIO_ICON.get(pri,'')} {pri}\n"
               f"Issue:     {desc}")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="maint_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="maint_cancel")],
          [_bm()]]
    await q.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_CONFIRM


async def maint_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "maint_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_code(str(q.from_user.id))
    try:
        lid = _gen_id("Safety_Log", 1, "MLG")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        # Safety_Log cols: Log_ID, Date, Type, Location, Equipment_or_Subject,
        #   Description, Severity, Priority, Employees_Involved, Root_Cause,
        #   Action_Taken, Solution, Responsible, Completion_Date,
        #   Time_To_Resolve, Cost, Photos, Report_PDF_Link, Status
        row = [lid, now,
               context.user_data.get("maint_type",""),
               context.user_data.get("maint_loc",""),
               context.user_data.get("maint_equip",""),
               context.user_data.get("maint_desc",""),
               "",  # Severity (N/A for maintenance)
               context.user_data.get("maint_pri","Medium"),
               ec or "",  # Employees_Involved
               "", "", "",  # Root_Cause, Action_Taken, Solution
               ec or "",   # Responsible
               "", "", "",  # Completion_Date, Time_To_Resolve, Cost
               "", "",  # Photos, Report_PDF_Link
               "Open"]
        get_sheet("Safety_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Maintenance entry saved!\nID: {lid}\nStatus: Open",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def maint_list_handler(update, context):
    q = update.callback_query; await q.answer()
    mode = q.data.replace("maint_list_","")
    await q.edit_message_text("⏳ Loading...")
    try:
        all_rows = get_sheet("Safety_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    # Filter to maintenance-type entries only
    rows = [r for r in all_rows if str(r.get("Type","")).strip() in MAINT_TYPES]
    if mode == "open":
        filtered = [r for r in rows if str(r.get("Status","")).strip() in ("Open","In_Progress","Escalated")]
        title = "📂 Open Issues"
    elif mode == "resolved":
        filtered = [r for r in rows if str(r.get("Status","")).strip() in ("Resolved","Closed")]
        title = "✅ Resolved Items"
    else:
        filtered = [r for r in rows if str(r.get("Status","")).strip() in ("Open","In_Progress")
                    and str(r.get("Priority","")).strip() == "Critical"]
        title = "⚠️ Overdue / Critical"
    if not filtered:
        await q.edit_message_text(f"{title}\n\nNo items found.",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]])); return
    lines = [f"{title} ({len(filtered)})\n{'─'*24}"]
    for r in filtered[:20]:
        pri  = str(r.get("Priority",""))
        stat = str(r.get("Status",""))
        lines.append(f"{PRIO_ICON.get(pri,'❓')} {r.get('Log_ID','')} | "
                     f"{r.get('Location','')} | {r.get('Equipment_or_Subject','')} | "
                     f"{STATUS_ICON.get(stat,'❓')} {stat}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


async def maint_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  INCIDENT REPORTS
# ══════════════════════════════════════════════════════════════════════════════
async def incident_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("⚠️ New Incident Report", callback_data="inc_new")],
        [InlineKeyboardButton("📂 Open Incidents",      callback_data="inc_list_open")],
        [InlineKeyboardButton("✅ Resolved Incidents",  callback_data="inc_list_resolved")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_safety"), _bm()],
    ]
    await q.edit_message_text("⚠️ Incident Reports\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def inc_new_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⚠️ New Incident Report\n\nEnter incident date (DD/MM/YYYY):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return INC_DATE


async def inc_date_inp(update, context):
    text = update.message.text.strip()
    try: datetime.strptime(text, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("⚠️ Use DD/MM/YYYY format:")
        return INC_DATE
    context.user_data["inc_date"] = text
    await update.message.reply_text("Enter time of incident (HH:MM):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return INC_TIME


async def inc_time_inp(update, context):
    context.user_data["inc_time"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(loc, callback_data=f"inc_loc_{loc}")] for loc in LOCATIONS]
    kb.append([_bm()])
    await update.message.reply_text("Select location:", reply_markup=InlineKeyboardMarkup(kb))
    return INC_LOC


async def inc_loc_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["inc_loc"] = q.data.replace("inc_loc_","")
    kb = [[InlineKeyboardButton(t, callback_data=f"inc_type_{t}")] for t in INC_TYPES]
    kb.append([_bm()])
    await q.edit_message_text("Select incident type:", reply_markup=InlineKeyboardMarkup(kb))
    return INC_TYPE


async def inc_type_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["inc_type"] = q.data.replace("inc_type_","")
    await q.edit_message_text("Describe what happened (include employees involved):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return INC_DESC


async def inc_desc_inp(update, context):
    context.user_data["inc_desc"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(f"{SEV_ICON.get(s,'')} {s}", callback_data=f"inc_sev_{s}")]
          for s in SEVERITIES]
    kb.append([_bm()])
    await update.message.reply_text("Select severity:", reply_markup=InlineKeyboardMarkup(kb))
    return INC_SEVERITY


async def inc_sev_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["inc_sev"] = q.data.replace("inc_sev_","")
    await q.edit_message_text("Describe immediate action taken:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return INC_ACTION


async def inc_action_inp(update, context):
    context.user_data["inc_action"] = update.message.text.strip()
    sev = context.user_data.get("inc_sev","")
    summary = (f"⚠️ Incident Report\n{'─'*24}\n"
               f"Date/Time: {context.user_data.get('inc_date','')} {context.user_data.get('inc_time','')}\n"
               f"Location:  {context.user_data.get('inc_loc','')}\n"
               f"Type:      {context.user_data.get('inc_type','')}\n"
               f"Severity:  {SEV_ICON.get(sev,'')} {sev}\n"
               f"Description:\n{context.user_data.get('inc_desc','')}\n"
               f"Immediate Action:\n{context.user_data.get('inc_action','')}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="inc_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="inc_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return INC_CONFIRM


async def inc_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "inc_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_code(str(q.from_user.id))
    sev = context.user_data.get("inc_sev","")
    try:
        iid = _gen_id("Safety_Log", 1, "INC")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        inc_datetime = (f"{context.user_data.get('inc_date','')} "
                        f"{context.user_data.get('inc_time','')}").strip()
        # Safety_Log cols: Log_ID, Date, Type, Location, Equipment_or_Subject,
        #   Description, Severity, Priority, Employees_Involved, Root_Cause,
        #   Action_Taken, Solution, Responsible, Completion_Date,
        #   Time_To_Resolve, Cost, Photos, Report_PDF_Link, Status
        row = [iid, inc_datetime,
               context.user_data.get("inc_type",""),  # Type
               context.user_data.get("inc_loc",""),   # Location
               "",                                     # Equipment_or_Subject
               context.user_data.get("inc_desc",""),  # Description
               sev,                                    # Severity
               "",                                     # Priority
               ec or "",                               # Employees_Involved
               "",                                     # Root_Cause
               context.user_data.get("inc_action",""),# Action_Taken
               "", "",                                 # Solution, Responsible
               "", "", "",                             # Completion_Date, Time_To_Resolve, Cost
               "", "",                                 # Photos, Report_PDF_Link
               "Reported"]
        get_sheet("Safety_Log").append_row(row, value_input_option="USER_ENTERED")
        msg = f"✅ Incident reported!\nID: {iid}\nSeverity: {sev}"
        # Critical/Major: notify Director
        if sev in ("Critical","Major"):
            msg += "\n\n⚠️ Director has been flagged for critical incident."
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def inc_list_handler(update, context):
    q = update.callback_query; await q.answer()
    mode = q.data.replace("inc_list_","")
    await q.edit_message_text("⏳ Loading incidents...")
    try:
        all_rows = get_sheet("Safety_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    # Filter to incident-type entries only
    rows = [r for r in all_rows if str(r.get("Type","")).strip() in INC_TYPES]
    if mode == "open":
        filtered = [r for r in rows if str(r.get("Status","")).strip() in ("Reported","Investigating")]
        title = "📂 Open Incidents"
    else:
        filtered = [r for r in rows if str(r.get("Status","")).strip() in ("Resolved","Closed")]
        title = "✅ Resolved Incidents"
    if not filtered:
        await q.edit_message_text(f"{title}\n\nNo incidents found.",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]])); return
    lines = [f"{title} ({len(filtered)})\n{'─'*24}"]
    for r in filtered[:20]:
        sev = str(r.get("Severity",""))
        lines.append(f"{SEV_ICON.get(sev,'❓')} {r.get('Log_ID','')} | "
                     f"{r.get('Date','')} | {r.get('Type','')} | {r.get('Location','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


async def inc_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  SAFETY LECTURES
# ══════════════════════════════════════════════════════════════════════════════
async def lecture_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("➕ Schedule Lecture",  callback_data="lect_new")],
        [InlineKeyboardButton("📋 All Lectures",      callback_data="lect_list")],
        [InlineKeyboardButton("⚠️ Overdue Drivers",   callback_data="lect_overdue")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_safety"), _bm()],
    ]
    await q.edit_message_text("📋 Safety Lectures\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def lect_new_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("📋 New Safety Lecture\n\nEnter lecture title:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return LECT_TITLE


async def lect_title_inp(update, context):
    context.user_data["lect_title"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(cat, callback_data=f"lect_cat_{cat}")] for cat in LECT_CATS]
    kb.append([_bm()])
    await update.message.reply_text("Select topic category:", reply_markup=InlineKeyboardMarkup(kb))
    return LECT_CAT


async def lect_cat_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["lect_cat"] = q.data.replace("lect_cat_","")
    await q.edit_message_text("Enter lecture date (DD/MM/YYYY):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return LECT_DATE


async def lect_date_inp(update, context):
    text = update.message.text.strip()
    try: datetime.strptime(text, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("⚠️ Use DD/MM/YYYY:"); return LECT_DATE
    context.user_data["lect_date"] = text
    await update.message.reply_text("Target department (or 'All'):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return LECT_DEPT


async def lect_dept_inp(update, context):
    context.user_data["lect_dept"] = update.message.text.strip()
    await update.message.reply_text("Instructor name:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return LECT_INSTR


async def lect_instr_inp(update, context):
    context.user_data["lect_instr"] = update.message.text.strip()
    await update.message.reply_text("Duration in hours (e.g. 2):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return LECT_HOURS


async def lect_hours_inp(update, context):
    text = update.message.text.strip()
    try: h = float(text); assert h > 0
    except Exception:
        await update.message.reply_text("⚠️ Enter valid hours:"); return LECT_HOURS
    context.user_data["lect_hours"] = h
    summary = (f"📋 Safety Lecture\n{'─'*24}\n"
               f"Title:    {context.user_data.get('lect_title','')}\n"
               f"Category: {context.user_data.get('lect_cat','')}\n"
               f"Date:     {context.user_data.get('lect_date','')}\n"
               f"Target:   {context.user_data.get('lect_dept','')}\n"
               f"Instructor:{context.user_data.get('lect_instr','')}\n"
               f"Duration: {h} hrs")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="lect_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="lect_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return LECT_CONFIRM


async def lect_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "lect_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        lid = _gen_id("Training_Log", 1, "LEC")
        # Training_Log cols: Record_ID, Date, Category, Title, Topic, Provider, Instructor,
        #   Duration_Hours, Target_Dept, Attendees_JSON, Total_Attended, Total_Expected,
        #   Attendance_Rate, Cost, Certificate_Link, Materials_Link, Next_Due_Date, Status
        row = [lid,
               context.user_data.get("lect_date",""),
               context.user_data.get("lect_cat",""),    # Category
               context.user_data.get("lect_title",""),  # Title
               "",                                       # Topic
               "",                                       # Provider (internal)
               context.user_data.get("lect_instr",""),  # Instructor
               context.user_data.get("lect_hours",""),  # Duration_Hours
               context.user_data.get("lect_dept",""),   # Target_Dept
               "", "", "",                               # Attendees_JSON, Total_Attended, Total_Expected
               "",                                       # Attendance_Rate (formula)
               "", "", "", "",                           # Cost, Certificate_Link, Materials_Link, Next_Due_Date
               "Scheduled"]
        get_sheet("Training_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Lecture scheduled!\nID: {lid}",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def lect_list_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading lectures...")
    try:
        all_rows = get_sheet("Training_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    rows = [r for r in all_rows if str(r.get("Category","")).strip() in LECT_CATS]
    if not rows:
        await q.edit_message_text("📋 No lectures scheduled.",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]])); return
    lines = [f"📋 All Safety Lectures ({len(rows)})\n{'─'*24}"]
    for r in rows[-15:]:
        lines.append(f"• {r.get('Record_ID','')} | {r.get('Date','')} | "
                     f"{r.get('Title','')} | {r.get('Target_Dept','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


async def lect_overdue_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Checking overdue drivers...")
    try:
        emps = get_sheet("Employee_DB").get_all_records()
        lects = get_sheet("Training_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    drivers = [e for e in emps if str(e.get("Bot_Role","")).strip() == "Driver"
               and str(e.get("Status","")).strip() == "Active"]
    # Simple check: drivers with no lecture attendance in last 30 days
    today = datetime.now().date()
    lines = [f"⚠️ Driver Safety Status ({len(drivers)} drivers)\n{'─'*24}"]
    for d in drivers[:20]:
        name = d.get("Full_Name","")
        ec   = d.get("Emp_Code","")
        lines.append(f"• {name} [{ec}] — Check lecture records")
    if not drivers:
        lines.append("No drivers found.")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


async def lect_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINING COURSES
# ══════════════════════════════════════════════════════════════════════════════
async def training_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("➕ Add Course",     callback_data="train_new")],
        [InlineKeyboardButton("📋 All Courses",    callback_data="train_list")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_safety"), _bm()],
    ]
    await q.edit_message_text("🎓 Training Courses\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def train_new_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("🎓 New Training Course\n\nEnter course title:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return TRAIN_TITLE


async def train_title_inp(update, context):
    context.user_data["train_title"] = update.message.text.strip()
    kb = [[InlineKeyboardButton("Internal", callback_data="train_prov_Internal"),
           InlineKeyboardButton("External", callback_data="train_prov_External")],
          [_bm()]]
    await update.message.reply_text("Provider:", reply_markup=InlineKeyboardMarkup(kb))
    return TRAIN_PROV


async def train_prov_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["train_prov"] = q.data.replace("train_prov_","")
    await q.edit_message_text("Enter start date (DD/MM/YYYY):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return TRAIN_DATE


async def train_date_inp(update, context):
    text = update.message.text.strip()
    try: datetime.strptime(text, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("⚠️ Use DD/MM/YYYY:"); return TRAIN_DATE
    context.user_data["train_date"] = text
    await update.message.reply_text("Total duration in hours:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return TRAIN_HOURS


async def train_hours_inp(update, context):
    text = update.message.text.strip()
    try: h = float(text)
    except Exception:
        await update.message.reply_text("⚠️ Enter valid hours:"); return TRAIN_HOURS
    context.user_data["train_hours"] = h
    summary = (f"🎓 Training Course\n{'─'*24}\n"
               f"Title:    {context.user_data.get('train_title','')}\n"
               f"Provider: {context.user_data.get('train_prov','')}\n"
               f"Date:     {context.user_data.get('train_date','')}\n"
               f"Duration: {h} hrs")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="train_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="train_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return TRAIN_CONFIRM


async def train_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "train_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        cid = _gen_id("Training_Log", 1, "TRN")
        prov = context.user_data.get("train_prov","")
        category = f"{prov}_Course" if prov in ("Internal","External") else prov
        # Training_Log cols: Record_ID, Date, Category, Title, Topic, Provider, Instructor,
        #   Duration_Hours, Target_Dept, Attendees_JSON, Total_Attended, Total_Expected,
        #   Attendance_Rate, Cost, Certificate_Link, Materials_Link, Next_Due_Date, Status
        row = [cid,
               context.user_data.get("train_date",""),  # Date
               category,                                 # Category (Internal_Course/External_Course)
               context.user_data.get("train_title",""), # Title
               "",                                       # Topic
               prov,                                     # Provider
               "",                                       # Instructor
               context.user_data.get("train_hours",""), # Duration_Hours
               "",                                       # Target_Dept
               "", "", "",                               # Attendees_JSON, Total_Attended, Total_Expected
               "",                                       # Attendance_Rate (formula)
               "", "", "", "",                           # Cost, Certificate_Link, Materials_Link, Next_Due_Date
               "Scheduled"]
        get_sheet("Training_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Course saved!\nID: {cid}",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def train_list_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading courses...")
    try:
        all_rows = get_sheet("Training_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    # Filter to non-lecture training entries only
    rows = [r for r in all_rows if str(r.get("Category","")).strip() not in LECT_CATS]
    if not rows:
        await q.edit_message_text("🎓 No courses recorded.",
                                  reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]])); return
    lines = [f"🎓 Training Courses ({len(rows)})\n{'─'*24}"]
    for r in rows[-15:]:
        st = str(r.get("Status",""))
        icon = {"Scheduled":"📅","In_Progress":"⚙️","Completed":"✅","Cancelled":"❌"}.get(st,"❓")
        lines.append(f"{icon} {r.get('Record_ID','')} | {r.get('Title','')} | {r.get('Date','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


async def train_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  SAFETY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
async def safety_dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading safety dashboard...")
    try:
        safety_log   = get_sheet("Safety_Log").get_all_records()
        training_log = get_sheet("Training_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    maint  = [r for r in safety_log if str(r.get("Type","")).strip() in MAINT_TYPES]
    incs   = [r for r in safety_log if str(r.get("Type","")).strip() in INC_TYPES]
    lects  = [r for r in training_log if str(r.get("Category","")).strip() in LECT_CATS]
    trains = [r for r in training_log if str(r.get("Category","")).strip() not in LECT_CATS]
    open_maint  = sum(1 for r in maint if str(r.get("Status","")) in ("Open","In_Progress"))
    crit_maint  = sum(1 for r in maint if str(r.get("Priority","")) == "Critical"
                       and str(r.get("Status","")) in ("Open","In_Progress"))
    open_inc    = sum(1 for r in incs if str(r.get("Status","")) in ("Reported","Investigating"))
    crit_inc    = sum(1 for r in incs if str(r.get("Severity","")) in ("Critical","Major")
                       and str(r.get("Status","")) not in ("Resolved","Closed"))
    now = datetime.now()
    lects_month = sum(1 for r in lects if _in_month(str(r.get("Date","")), now))
    incs_month  = sum(1 for r in incs if _in_month(str(r.get("Date","")), now))
    sched_train = sum(1 for r in trains if str(r.get("Status","")) == "Scheduled")
    msg = (f"📊 Safety Dashboard\n{'─'*28}\n"
           f"🔧 Maintenance:\n"
           f"   Open: {open_maint} | Critical: {crit_maint}\n"
           f"⚠️ Incidents:\n"
           f"   Open: {open_inc} | Critical/Major: {crit_inc}\n"
           f"{'─'*28}\n"
           f"This Month:\n"
           f"   Lectures conducted: {lects_month}\n"
           f"   Incidents reported: {incs_month}\n"
           f"   Training scheduled: {sched_train}")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bsf(), _bm()]]))


def _in_month(date_str, now):
    try:
        d = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return d.year == now.year and d.month == now.month
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_safety_handlers():
    maint_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(maint_new_start, pattern="^maint_new$")],
        states={
            MAINT_LOC:    [CallbackQueryHandler(maint_loc_cb, pattern="^maint_loc_")],
            MAINT_EQUIP:  [MessageHandler(filters.TEXT & ~filters.COMMAND, maint_equip_inp)],
            MAINT_TYPE:   [CallbackQueryHandler(maint_type_cb, pattern="^maint_type_")],
            MAINT_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, maint_desc_inp)],
            MAINT_PRI:    [CallbackQueryHandler(maint_pri_cb, pattern="^maint_pri_")],
            MAINT_CONFIRM:[CallbackQueryHandler(maint_confirm_cb, pattern="^maint_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, maint_cancel_handler)],
        per_message=False,
    )
    inc_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(inc_new_start, pattern="^inc_new$")],
        states={
            INC_DATE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inc_date_inp)],
            INC_TIME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inc_time_inp)],
            INC_LOC:     [CallbackQueryHandler(inc_loc_cb, pattern="^inc_loc_")],
            INC_TYPE:    [CallbackQueryHandler(inc_type_cb, pattern="^inc_type_")],
            INC_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, inc_desc_inp)],
            INC_SEVERITY:[CallbackQueryHandler(inc_sev_cb, pattern="^inc_sev_")],
            INC_ACTION:  [MessageHandler(filters.TEXT & ~filters.COMMAND, inc_action_inp)],
            INC_CONFIRM: [CallbackQueryHandler(inc_confirm_cb, pattern="^inc_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, inc_cancel_handler)],
        per_message=False,
    )
    lect_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(lect_new_start, pattern="^lect_new$")],
        states={
            LECT_TITLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, lect_title_inp)],
            LECT_CAT:    [CallbackQueryHandler(lect_cat_cb, pattern="^lect_cat_")],
            LECT_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, lect_date_inp)],
            LECT_DEPT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, lect_dept_inp)],
            LECT_INSTR:  [MessageHandler(filters.TEXT & ~filters.COMMAND, lect_instr_inp)],
            LECT_HOURS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, lect_hours_inp)],
            LECT_CONFIRM:[CallbackQueryHandler(lect_confirm_cb, pattern="^lect_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, lect_cancel_handler)],
        per_message=False,
    )
    train_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(train_new_start, pattern="^train_new$")],
        states={
            TRAIN_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_title_inp)],
            TRAIN_PROV:  [CallbackQueryHandler(train_prov_cb, pattern="^train_prov_")],
            TRAIN_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, train_date_inp)],
            TRAIN_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, train_hours_inp)],
            TRAIN_CONFIRM:[CallbackQueryHandler(train_confirm_cb, pattern="^train_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, train_cancel_handler)],
        per_message=False,
    )
    return [maint_h, inc_h, lect_h, train_h]


def get_safety_static_handlers():
    return [
        CallbackQueryHandler(safety_menu_handler,    pattern="^menu_safety$"),
        CallbackQueryHandler(maint_menu,             pattern="^menu_safety_maint$"),
        CallbackQueryHandler(maint_list_handler,     pattern="^maint_list_"),
        CallbackQueryHandler(incident_menu,          pattern="^menu_safety_incidents$"),
        CallbackQueryHandler(inc_list_handler,       pattern="^inc_list_"),
        CallbackQueryHandler(lecture_menu,           pattern="^menu_safety_lectures$"),
        CallbackQueryHandler(lect_list_handler,      pattern="^lect_list$"),
        CallbackQueryHandler(lect_overdue_handler,   pattern="^lect_overdue$"),
        CallbackQueryHandler(training_menu,          pattern="^menu_safety_training$"),
        CallbackQueryHandler(train_list_handler,     pattern="^train_list$"),
        CallbackQueryHandler(safety_dashboard_handler,pattern="^menu_safety_dashboard$"),
    ]
