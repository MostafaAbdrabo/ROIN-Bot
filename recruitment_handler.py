"""
ROIN WORLD FZE — Recruitment System (Phase 25)
===============================================
Complete hiring pipeline: A-menu, B-hiring requests, C-job postings,
D-candidates, E-interviews, F-selection/offer, G-onboarding,
H-dashboard, K-AI features, L-referrals.
"""

import io, json
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import (get_sheet, WORKBOOK,
                    TAB_HIRING_REQUESTS, TAB_JOB_POSTINGS,
                    TAB_CANDIDATES, TAB_ONBOARDING,
                    TAB_USER_REGISTRY, TAB_EMPLOYEE_DB, TAB_LEAVE_BALANCE)
from notification_handler import create_notification
from recruitment_pdf import generate_requisition_pdf, generate_offer_pdf
from ai_writer import (improve_text, improve_job_description,
                       generate_social_posts, screen_candidate,
                       generate_interview_questions, ai_available)

# ── State constants ────────────────────────────────────────────────────────────
# Hiring Request
REC_HR_TITLE    = 4000
REC_HR_NUM      = 4001
REC_HR_PRIORITY = 4002
REC_HR_JUSTIF   = 4003
REC_HR_AI_WAIT  = 4004
REC_HR_START    = 4005
REC_HR_CONTRACT = 4006
REC_HR_SHIFT    = 4007
REC_HR_LOCATION = 4008
REC_HR_SALARY   = 4009
REC_HR_SPECIAL  = 4010
REC_HR_CONFIRM  = 4011
REC_HR_SCHED_HC = 4012
REC_HR_RNOTES   = 4013

# Job Posting
REC_JP_SELECT   = 4020
REC_JP_DESC     = 4021
REC_JP_AI_WAIT  = 4022
REC_JP_REQS     = 4023
REC_JP_BENEFITS = 4024
REC_JP_DEADLINE = 4025
REC_JP_LANGS    = 4026

# Candidate
REC_CAND_POSTING = 4030
REC_CAND_NAME    = 4031
REC_CAND_PHONE   = 4032
REC_CAND_SOURCE  = 4033
REC_CAND_EDU     = 4034
REC_CAND_EXP     = 4035
REC_CAND_NOTES   = 4036

# Interview Schedule
REC_SCHED_DATE  = 4040
REC_SCHED_TIME  = 4041
REC_SCHED_PANEL = 4042
REC_SCHED_NOTES = 4043

# Interview Feedback
REC_INT_TECH      = 4050
REC_INT_COMM      = 4051
REC_INT_EXP_RATE  = 4052
REC_INT_CULTURE   = 4053
REC_INT_RECOMMEND = 4054
REC_INT_COMMENTS  = 4055

# Offer
REC_OFFER_SALARY     = 4060
REC_OFFER_START      = 4061
REC_OFFER_CONTRACT   = 4062
REC_OFFER_DURATION   = 4063
REC_OFFER_CONDITIONS = 4064

# Referral
REC_REF_NAME     = 4070
REC_REF_PHONE    = 4071
REC_REF_POSITION = 4072
REC_REF_RELATION = 4073

HR_ROLES = ("HR_Staff", "HR_Manager", "Bot_Manager")
MGR_ROLES = ("Direct_Manager", "HR_Staff", "HR_Manager", "Director", "Bot_Manager")
DIR_ROLES = ("Director", "Bot_Manager")

WORK_LOCATIONS = ["El Dabaa", "Cairo Office", "Alexandria", "Matrouh", "Other"]
PRIORITIES     = ["Normal", "Urgent", "Critical"]
CONTRACT_TYPES = ["Fixed-term", "Permanent", "Temporary"]
SHIFTS         = ["Day", "Night", "Rotating"]
SOURCES        = ["Facebook", "Referral", "Walk-in", "Job Site", "Other"]
EDU_LEVELS     = ["Primary", "Secondary", "Diploma", "Bachelor", "Master", "PhD"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bm():
    return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")

def _back(cb):
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data=cb), _bm()]])


def _get_user(tid):
    """Return (ec, role) for telegram ID, or (None, None)."""
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            return r[0].strip(), (r[3].strip() if len(r) > 3 else "")
    return None, None


def _get_emp(ec):
    for r in get_sheet(TAB_EMPLOYEE_DB).get_all_records():
        if str(r.get("Emp_Code", "")).strip() == str(ec):
            return r
    return {}


def _get_director_record():
    director_ec = None
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if len(r) > 3 and r[3].strip() == "Director":
            director_ec = r[0].strip(); break
    if not director_ec: return {}
    return _get_emp(director_ec)


def _get_hr_manager_record():
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if len(r) > 3 and r[3].strip() == "HR_Manager":
            return _get_emp(r[0].strip())
    return {}


def _find_ecs_by_role(role):
    """Return list of emp_codes with a given role."""
    result = []
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if len(r) > 3 and r[3].strip() == role:
            result.append(r[0].strip())
    return result


def _count_dept(dept):
    n = 0
    try:
        for r in get_sheet(TAB_EMPLOYEE_DB).get_all_records():
            if str(r.get("Department", "")).strip().lower() == dept.strip().lower():
                if str(r.get("Status", "Active")).strip() not in ("Terminated", "Resigned"):
                    n += 1
    except Exception:
        pass
    return n


def _ensure_tab(tab_name, headers):
    """Get or create a worksheet with given headers."""
    try:
        ws = WORKBOOK.worksheet(tab_name)
        if not ws.row_values(1):
            ws.append_row(headers)
        return ws
    except Exception:
        ws = WORKBOOK.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws


def _get_or_create_sheets():
    _ensure_tab(TAB_HIRING_REQUESTS, [
        "HR_ID", "Date", "Manager_Code", "Manager_Name", "Department",
        "Position_Title", "Num_Positions", "Priority", "Justification",
        "Required_Start_Date", "Contract_Type", "Shift", "Work_Location",
        "Salary_Range", "Special_Requirements",
        "HR_Status", "HR_Date", "HR_Notes", "Scheduled_Headcount",
        "Director_Status", "Director_Date", "Director_Notes",
        "Final_Status", "Job_Posting_ID", "Created_At"
    ])
    _ensure_tab(TAB_JOB_POSTINGS, [
        "Posting_ID", "HR_Request_ID", "Date", "Position_Title", "Department",
        "Location", "Description_AR", "Description_EN", "Description_RU",
        "Requirements", "Benefits", "Deadline", "Status",
        "Candidates_Count", "Created_By", "Created_At"
    ])
    _ensure_tab(TAB_CANDIDATES, [
        "Candidate_ID", "Posting_ID", "Name", "Phone", "National_ID",
        "Source", "Education", "Experience_Years", "Previous_Employer",
        "Skills_Notes", "Resume_Link", "Screening_Rating", "Screening_Notes",
        "Screening_By", "Interview_Date", "Interview_Time",
        "Interview_Panel_JSON", "Interview_Feedback_JSON", "Final_Rating",
        "Status", "Rejection_Reason", "Offer_Salary", "Offer_Date",
        "Start_Date", "Emp_Code_Assigned", "Referred_By", "Created_At"
    ])
    _ensure_tab(TAB_ONBOARDING, [
        "Emp_Code", "Candidate_ID", "Item", "Status", "Date_Completed", "Notes"
    ])


def _next_id(tab_name, prefix, col=0):
    year = datetime.now().year
    full_prefix = f"{prefix}-{year}-"
    max_n = 0
    try:
        rows = get_sheet(tab_name).get_all_values()
        for r in rows[1:]:
            if len(r) > col and str(r[col]).startswith(full_prefix):
                try:
                    n = int(str(r[col]).split("-")[-1])
                    max_n = max(max_n, n)
                except ValueError:
                    pass
    except Exception:
        pass
    return f"{full_prefix}{str(max_n + 1).zfill(4)}"


def _notify_roles(roles_list, notif_type, title, message, related_id=""):
    """Send notification to all users with any of the given roles."""
    for role in roles_list:
        for ec in _find_ecs_by_role(role):
            try:
                create_notification(ec, notif_type, title, message, related_id)
            except Exception:
                pass


def _get_sig(ec):
    """Return signature bytes for an employee, or None."""
    try:
        import base64
        ws = get_sheet("Signatures")
        for r in ws.get_all_values()[1:]:
            if r[0].strip() == str(ec) and len(r) > 2 and r[2]:
                return base64.b64decode(r[2])
    except Exception:
        pass
    return None


def _get_req_row(req_id):
    """Return (row_index, row_values) for a hiring request, or (None, None)."""
    try:
        rows = get_sheet(TAB_HIRING_REQUESTS).get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == req_id:
                return i + 1, r
    except Exception:
        pass
    return None, None


def _get_cand_row(cand_id):
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == cand_id:
                return i + 1, r
    except Exception:
        pass
    return None, None


def _get_jp_row(jp_id):
    try:
        rows = get_sheet(TAB_JOB_POSTINGS).get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == jp_id:
                return i + 1, r
    except Exception:
        pass
    return None, None


# ── A: Menu ────────────────────────────────────────────────────────────────────

async def recruitment_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    rows = []
    if role in MGR_ROLES:
        rows.append([InlineKeyboardButton("📋 Hiring Requests", callback_data="rec_hiring_requests")])
    if role in HR_ROLES:
        rows.append([InlineKeyboardButton("📢 Job Postings",   callback_data="rec_job_postings")])
    if role in HR_ROLES:
        rows.append([InlineKeyboardButton("👤 Candidates",     callback_data="rec_candidates")])
    if role in HR_ROLES + ("Direct_Manager",):
        rows.append([InlineKeyboardButton("📅 Interviews",     callback_data="rec_interviews")])
    if role in HR_ROLES + ("Director",):
        rows.append([InlineKeyboardButton("✅ Selections",     callback_data="rec_selections")])
    if role in HR_ROLES + DIR_ROLES:
        rows.append([InlineKeyboardButton("📊 Dashboard",      callback_data="rec_dashboard")])
    rows.append([InlineKeyboardButton("🤝 Refer a Candidate", callback_data="rec_refer")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), _bm()])
    await q.edit_message_text("👔 Recruitment\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


async def hiring_requests_menu(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    rows = []
    if role in MGR_ROLES:
        rows.append([InlineKeyboardButton("➕ New Hiring Request", callback_data="rec_new_request")])
    rows.append([InlineKeyboardButton("📋 View Requests", callback_data="rec_view_requests")])
    if role in DIR_ROLES:
        rows.append([InlineKeyboardButton("✅ Approve Requests", callback_data="rec_approve_requests")])
    rows.append([InlineKeyboardButton("↩️ Back", callback_data="menu_recruitment"), _bm()])
    await q.edit_message_text("📋 Hiring Requests\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


async def job_postings_menu(update, context):
    q = update.callback_query; await q.answer()
    rows = [
        [InlineKeyboardButton("➕ Create Posting",  callback_data="rec_new_posting")],
        [InlineKeyboardButton("📋 Active Postings", callback_data="rec_list_postings")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_recruitment"), _bm()],
    ]
    await q.edit_message_text("📢 Job Postings\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


async def candidates_menu(update, context):
    q = update.callback_query; await q.answer()
    rows = [
        [InlineKeyboardButton("➕ Add Candidate",    callback_data="rec_add_candidate")],
        [InlineKeyboardButton("👤 View Candidates",  callback_data="rec_list_candidates")],
        [InlineKeyboardButton("⭐ Screening Queue",  callback_data="rec_screening_queue")],
        [InlineKeyboardButton("📅 Shortlisted",      callback_data="rec_shortlisted")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_recruitment"), _bm()],
    ]
    await q.edit_message_text("👤 Candidates\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


async def interviews_menu(update, context):
    q = update.callback_query; await q.answer()
    rows = [
        [InlineKeyboardButton("📅 Schedule Interview",  callback_data="rec_sched_interview")],
        [InlineKeyboardButton("📝 Give Feedback",       callback_data="rec_int_feedback_menu")],
        [InlineKeyboardButton("📋 View Scheduled",      callback_data="rec_view_interviews")],
        [InlineKeyboardButton("🤖 Interview Questions", callback_data="rec_ai_questions_menu")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_recruitment"), _bm()],
    ]
    await q.edit_message_text("📅 Interviews\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


async def selections_menu(update, context):
    q = update.callback_query; await q.answer()
    rows = [
        [InlineKeyboardButton("✅ Interviewed Candidates", callback_data="rec_selections_list")],
        [InlineKeyboardButton("📄 Pending Offers",         callback_data="rec_pending_offers")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_recruitment"), _bm()],
    ]
    await q.edit_message_text("✅ Selections & Offers\n\nSelect an option:",
                               reply_markup=InlineKeyboardMarkup(rows))


# ── B: Hiring Request Flow ─────────────────────────────────────────────────────

async def new_request_start(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=_back("menu_recruitment")); return ConversationHandler.END
    emp = _get_emp(ec)
    dept = emp.get("Department", "")
    context.user_data["rec_req"] = {"manager_ec": ec, "department": dept}
    await q.edit_message_text(
        f"📋 New Hiring Request\n\nDepartment: {dept}\n\nStep 1/10 — Enter position title:")
    return REC_HR_TITLE


async def recv_hr_title(update, context):
    title = update.message.text.strip()
    if len(title) < 3:
        await update.message.reply_text("Title too short. Please enter the position title:"); return REC_HR_TITLE
    context.user_data["rec_req"]["position_title"] = title
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(str(i), callback_data=f"rec_num_{i}") for i in range(1, 6)],
                                [InlineKeyboardButton(str(i), callback_data=f"rec_num_{i}") for i in range(6, 11)]])
    await update.message.reply_text("Step 2/10 — How many positions?", reply_markup=kb)
    return REC_HR_NUM


async def recv_hr_num(update, context):
    q = update.callback_query; await q.answer()
    num = q.data.replace("rec_num_", "")
    context.user_data["rec_req"]["num_positions"] = num
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(p, callback_data=f"rec_pri_{p}") for p in PRIORITIES]])
    await q.edit_message_text("Step 3/10 — Priority?", reply_markup=kb)
    return REC_HR_PRIORITY


async def recv_hr_priority(update, context):
    q = update.callback_query; await q.answer()
    pri = q.data.replace("rec_pri_", "")
    context.user_data["rec_req"]["priority"] = pri
    await q.edit_message_text("Step 4/10 — Justification / reason for this hire (describe the need):")
    return REC_HR_JUSTIF


async def recv_hr_justif(update, context):
    text = update.message.text.strip()
    if len(text) < 10:
        await update.message.reply_text("Please provide more detail:"); return REC_HR_JUSTIF
    context.user_data["rec_req"]["justification"] = text
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🤖 AI Improve", callback_data="rec_justif_ai"),
        InlineKeyboardButton("✅ Keep as-is",  callback_data="rec_justif_keep"),
    ]])
    await update.message.reply_text(
        f"Your justification:\n\n{text}\n\nImprove with AI?", reply_markup=kb)
    return REC_HR_AI_WAIT


async def recv_hr_ai_choice(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "rec_justif_ai":
        await q.edit_message_text("⏳ Improving with AI...")
        text = context.user_data["rec_req"]["justification"]
        improved, err = await improve_text(text, context="general", lang="EN")
        if not err:
            context.user_data["rec_req"]["justification"] = improved
        await q.edit_message_text(
            f"{'✅ AI improved' if not err else '⚠️ AI unavailable, kept original'}\n\n"
            f"Step 5/10 — Required start date (DD/MM/YYYY):")
    else:
        await q.edit_message_text("Step 5/10 — Required start date (DD/MM/YYYY):")
    return REC_HR_START


async def recv_hr_start(update, context):
    context.user_data["rec_req"]["required_start_date"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(c, callback_data=f"rec_ct_{c}") for c in CONTRACT_TYPES]])
    await update.message.reply_text("Step 6/10 — Contract type?", reply_markup=kb)
    return REC_HR_CONTRACT


async def recv_hr_contract(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_req"]["contract_type"] = q.data.replace("rec_ct_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(s, callback_data=f"rec_sh_{s}") for s in SHIFTS]])
    await q.edit_message_text("Step 7/10 — Shift?", reply_markup=kb)
    return REC_HR_SHIFT


async def recv_hr_shift(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_req"]["shift"] = q.data.replace("rec_sh_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(loc, callback_data=f"rec_loc_{i}")]
                                for i, loc in enumerate(WORK_LOCATIONS)])
    await q.edit_message_text("Step 8/10 — Work location?", reply_markup=kb)
    return REC_HR_LOCATION


async def recv_hr_location(update, context):
    q = update.callback_query; await q.answer()
    idx = int(q.data.replace("rec_loc_", ""))
    context.user_data["rec_req"]["work_location"] = WORK_LOCATIONS[idx]
    await q.edit_message_text("Step 9/10 — Salary range (e.g. 5000-7000 EGP), or type 'skip':")
    return REC_HR_SALARY


async def recv_hr_salary(update, context):
    val = update.message.text.strip()
    context.user_data["rec_req"]["salary_range"] = "" if val.lower() == "skip" else val
    await update.message.reply_text("Step 10/10 — Special requirements (or type 'skip'):")
    return REC_HR_SPECIAL


async def recv_hr_special(update, context):
    val = update.message.text.strip()
    req = context.user_data["rec_req"]
    req["special_req"] = "" if val.lower() == "skip" else val
    summary = (
        f"📋 New Hiring Request — Summary\n{'─'*30}\n"
        f"Position:   {req['position_title']}\n"
        f"Department: {req['department']}\n"
        f"Positions:  {req['num_positions']}\n"
        f"Priority:   {req['priority']}\n"
        f"Contract:   {req['contract_type']}\n"
        f"Shift:      {req['shift']}\n"
        f"Location:   {req['work_location']}\n"
        f"Start:      {req['required_start_date']}\n"
        f"Salary:     {req.get('salary_range') or '—'}\n"
        f"Justification:\n{req['justification'][:200]}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Submit", callback_data="rec_req_submit"),
        InlineKeyboardButton("❌ Cancel", callback_data="rec_req_cancel"),
    ]])
    await update.message.reply_text(summary, reply_markup=kb)
    return REC_HR_CONFIRM


async def recv_hr_confirm(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "rec_req_cancel":
        await q.edit_message_text("❌ Cancelled.", reply_markup=_back("menu_recruitment"))
        return ConversationHandler.END
    req = context.user_data["rec_req"]
    ec = req["manager_ec"]
    emp = _get_emp(ec)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    req_id = _next_id(TAB_HIRING_REQUESTS, "HR-REQ")
    dept = req["department"]
    current_hc = str(_count_dept(dept))

    _get_or_create_sheets()
    ws = get_sheet(TAB_HIRING_REQUESTS)
    ws.append_row([
        req_id, now, ec, emp.get("Full_Name", ec),
        dept, req["position_title"], req["num_positions"], req["priority"],
        req["justification"], req["required_start_date"],
        req["contract_type"], req["shift"], req["work_location"],
        req.get("salary_range", ""), req.get("special_req", ""),
        "Pending_HR", "", "", current_hc,
        "Pending", "", "",
        "Requested", "", now
    ])

    # Generate requisition PDF and attach
    try:
        dir_rec = _get_director_record()
        dir_name = dir_rec.get("Full_Name", "Director")
        mgr_sig  = _get_sig(ec)
        pdf_bytes = generate_requisition_pdf({
            "req_id": req_id, "date": now[:10].replace("/", "."),
            "position_title": req["position_title"],
            "department": dept,
            "num_positions": req["num_positions"],
            "current_headcount": current_hc,
            "scheduled_headcount": "(HR)",
            "priority": req["priority"],
            "justification": req["justification"],
            "required_start_date": req["required_start_date"],
            "contract_type": req["contract_type"],
            "shift": req["shift"],
            "work_location": req["work_location"],
            "salary_range": req.get("salary_range", ""),
            "special_req": req.get("special_req", ""),
            "manager_name": emp.get("Full_Name", ec),
            "director_name_ru": dir_name,
            "director_name_en": dir_name,
        }, sigs={"manager_sig": mgr_sig})
        from drive_utils import upload_to_drive as drive_upload
        drive_url = drive_upload(pdf_bytes, f"{req_id}-Requisition.pdf", "requisitions")
        if drive_url:
            await q.message.reply_text(
                f"📋 Personnel Requisition Form — {req_id}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View PDF", url=drive_url)]]))
        else:
            await q.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename=f"{req_id}-Requisition.pdf",
                caption=f"📋 Personnel Requisition Form — {req_id}")
    except Exception as e:
        await q.message.reply_text(f"⚠️ PDF generation error: {e}")

    # Notify HR
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "New Hiring Request", f"New request {req_id}: {req['position_title']} ({dept})", req_id)
    await q.edit_message_text(
        f"✅ Request {req_id} submitted!\nHR will review and forward to Director.",
        reply_markup=_back("menu_recruitment"))
    return ConversationHandler.END


# ── B: Request listing & approval ─────────────────────────────────────────────

async def view_requests_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    await q.edit_message_text("⏳ Loading requests...")
    try:
        _get_or_create_sheets()
        rows = get_sheet(TAB_HIRING_REQUESTS).get_all_values()
        emp = _get_emp(ec)
        dept = emp.get("Department", "")
        items = []
        for r in rows[1:]:
            if role in HR_ROLES or role == "Director":
                items.append(r)
            elif role == "Direct_Manager" and r[4].strip() == dept:
                items.append(r)
        if not items:
            await q.edit_message_text("No hiring requests found.", reply_markup=_back("rec_hiring_requests")); return
        lines = ["📋 Hiring Requests\n"]
        for r in items[-15:]:
            status = r[22] if len(r) > 22 else "?"
            lines.append(f"• {r[0]} | {r[5]} | {r[7]} | {status}")
        kb = [[InlineKeyboardButton(f"🔍 {r[0]}", callback_data=f"rec_vreq_{r[0]}")]
              for r in items[-8:]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_hiring_requests"), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_hiring_requests"))


async def view_req_detail(update, context):
    q = update.callback_query; await q.answer()
    req_id = q.data.replace("rec_vreq_", "")
    ec, role = _get_user(str(q.from_user.id))
    row_num, r = _get_req_row(req_id)
    if not r:
        await q.edit_message_text("Not found.", reply_markup=_back("rec_view_requests")); return
    msg = (f"📋 {r[0]}\n{'─'*28}\n"
           f"Position:   {r[5]}\nDepartment: {r[4]}\n"
           f"Positions:  {r[6]}\nPriority:   {r[7]}\n"
           f"Manager:    {r[3]}\nDate:       {r[1]}\n"
           f"Contract:   {r[10]}\nShift:      {r[11]}\n"
           f"Location:   {r[12]}\n"
           f"HR Status:  {r[15] if len(r)>15 else '-'}\n"
           f"Dir Status: {r[19] if len(r)>19 else '-'}\n"
           f"Final:      {r[22] if len(r)>22 else '-'}\n\n"
           f"Justification:\n{r[8][:300]}")
    kb_rows = []
    if role in ("HR_Staff", "HR_Manager", "Bot_Manager") and (len(r) <= 15 or r[15] == "Pending_HR"):
        kb_rows.append([
            InlineKeyboardButton("✅ HR Approve", callback_data=f"rec_hrapprove_{req_id}"),
            InlineKeyboardButton("❌ HR Reject",  callback_data=f"rec_hrreject_{req_id}"),
        ])
    if role in DIR_ROLES and (len(r) <= 19 or r[19] == "Pending"):
        kb_rows.append([
            InlineKeyboardButton("✅ Director Approve", callback_data=f"rec_dirapprove_{req_id}"),
            InlineKeyboardButton("❌ Director Reject",  callback_data=f"rec_dirreject_{req_id}"),
        ])
    kb_rows.append([InlineKeyboardButton("↩️ Back", callback_data="rec_view_requests"), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))


async def hr_approve_req(update, context):
    q = update.callback_query; await q.answer()
    req_id = q.data.replace("rec_hrapprove_", "")
    ec, _ = _get_user(str(q.from_user.id))
    row_num, r = _get_req_row(req_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = get_sheet(TAB_HIRING_REQUESTS)
    ws.update_cell(row_num, 16, "HR_Reviewed")
    ws.update_cell(row_num, 17, now)
    ws.update_cell(row_num, 23, "HR_Reviewed")
    _notify_roles(["Director"], "recruitment",
                  "Hiring Request Needs Approval",
                  f"HR has reviewed {req_id}: {r[5]} ({r[4]}). Your approval needed.", req_id)
    _notify_roles(["HR_Manager"], "recruitment",
                  "Request Forwarded to Director",
                  f"{req_id} forwarded to Director for final approval.", req_id)
    await q.edit_message_text(
        f"✅ {req_id} reviewed. Forwarded to Director.",
        reply_markup=_back("rec_view_requests"))


async def hr_reject_req(update, context):
    q = update.callback_query; await q.answer()
    req_id = q.data.replace("rec_hrreject_", "")
    row_num, r = _get_req_row(req_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = get_sheet(TAB_HIRING_REQUESTS)
    ws.update_cell(row_num, 16, "Rejected_HR")
    ws.update_cell(row_num, 17, now)
    ws.update_cell(row_num, 23, "Rejected")
    _notify_roles(["Direct_Manager"], "recruitment",
                  "Hiring Request Rejected by HR",
                  f"Your request {req_id} for {r[5]} was rejected at HR level.", req_id)
    await q.edit_message_text(f"❌ {req_id} rejected.", reply_markup=_back("rec_view_requests"))


async def approve_requests_handler(update, context):
    """Director sees requests pending their approval."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading...")
    try:
        rows = get_sheet(TAB_HIRING_REQUESTS).get_all_values()
        pending = [r for r in rows[1:] if len(r) > 19 and r[19] == "Pending" and (len(r) <= 15 or r[15] == "HR_Reviewed")]
        if not pending:
            await q.edit_message_text("No requests pending Director approval.",
                                       reply_markup=_back("rec_hiring_requests")); return
        kb = [[InlineKeyboardButton(f"🔍 {r[0]} — {r[5]}", callback_data=f"rec_vreq_{r[0]}")]
              for r in pending[:10]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_hiring_requests"), _bm()])
        await q.edit_message_text(
            f"✅ Pending Director Approval ({len(pending)} request(s)):",
            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_hiring_requests"))


async def dir_approve_req(update, context):
    q = update.callback_query; await q.answer()
    req_id = q.data.replace("rec_dirapprove_", "")
    ec, _ = _get_user(str(q.from_user.id))
    row_num, r = _get_req_row(req_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = get_sheet(TAB_HIRING_REQUESTS)
    ws.update_cell(row_num, 20, "Approved")
    ws.update_cell(row_num, 21, now)
    ws.update_cell(row_num, 23, "Approved")
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Hiring Request Approved",
                  f"Director approved {req_id}: {r[5]}. Create a job posting.", req_id)
    await q.edit_message_text(
        f"✅ {req_id} approved! HR can now create a job posting.",
        reply_markup=_back("rec_approve_requests"))


async def dir_reject_req(update, context):
    q = update.callback_query; await q.answer()
    req_id = q.data.replace("rec_dirreject_", "")
    row_num, r = _get_req_row(req_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = get_sheet(TAB_HIRING_REQUESTS)
    ws.update_cell(row_num, 20, "Rejected")
    ws.update_cell(row_num, 21, now)
    ws.update_cell(row_num, 23, "Rejected")
    _notify_roles(["HR_Staff", "HR_Manager", "Direct_Manager"], "recruitment",
                  "Hiring Request Rejected by Director",
                  f"Director rejected request {req_id} for {r[5]}.", req_id)
    await q.edit_message_text(f"❌ {req_id} rejected by Director.",
                               reply_markup=_back("rec_approve_requests"))


# ── C: Job Postings ────────────────────────────────────────────────────────────

async def new_posting_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading approved requests...")
    try:
        rows = get_sheet(TAB_HIRING_REQUESTS).get_all_values()
        approved = [r for r in rows[1:]
                    if len(r) > 22 and r[22] == "Approved" and (len(r) <= 23 or not r[23].strip())]
        if not approved:
            await q.edit_message_text(
                "No approved hiring requests without postings yet.\n"
                "Requests must be Director-approved before creating a posting.",
                reply_markup=_back("rec_job_postings")); return ConversationHandler.END
        context.user_data["rec_approved_reqs"] = approved
        kb = [[InlineKeyboardButton(f"{r[0]} — {r[5]} ({r[4]})", callback_data=f"rec_jp_req_{i}")]
              for i, r in enumerate(approved[:10])]
        kb.append([InlineKeyboardButton("↩️ Cancel", callback_data="rec_job_postings")])
        await q.edit_message_text("Select approved request to create posting for:",
                                   reply_markup=InlineKeyboardMarkup(kb))
        return REC_JP_SELECT
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_job_postings"))
        return ConversationHandler.END


async def recv_jp_req(update, context):
    q = update.callback_query; await q.answer()
    idx = int(q.data.replace("rec_jp_req_", ""))
    reqs = context.user_data.get("rec_approved_reqs", [])
    req_row = reqs[idx]
    context.user_data["rec_jp"] = {
        "hr_request_id": req_row[0],
        "position_title": req_row[5],
        "department": req_row[4],
        "location": req_row[12],
        "requirements": req_row[14] or "",
    }
    await q.edit_message_text(
        f"Creating posting for: {req_row[5]} ({req_row[4]})\n\n"
        f"Step 1/5 — Write the full job description:")
    return REC_JP_DESC


async def recv_jp_desc(update, context):
    text = update.message.text.strip()
    context.user_data["rec_jp"]["description_en"] = text
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🤖 AI Improve", callback_data="rec_jp_ai_improve"),
        InlineKeyboardButton("✅ Keep",        callback_data="rec_jp_ai_keep"),
    ]])
    await update.message.reply_text(f"Description received.\nImprove with AI?", reply_markup=kb)
    return REC_JP_AI_WAIT


async def recv_jp_ai(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "rec_jp_ai_improve":
        await q.edit_message_text("⏳ AI improving description...")
        text = context.user_data["rec_jp"]["description_en"]
        improved, err = await improve_job_description(text, lang="EN")
        if not err:
            context.user_data["rec_jp"]["description_en"] = improved
        await q.edit_message_text(
            f"{'✅ AI improved.' if not err else '⚠️ AI unavailable.'}\n\n"
            f"Step 2/5 — Requirements (education, experience, skills):")
    else:
        await q.edit_message_text("Step 2/5 — Requirements (education, experience, skills):")
    return REC_JP_REQS


async def recv_jp_reqs(update, context):
    context.user_data["rec_jp"]["requirements"] = update.message.text.strip()
    await update.message.reply_text("Step 3/5 — Benefits offered (or type 'skip'):")
    return REC_JP_BENEFITS


async def recv_jp_benefits(update, context):
    val = update.message.text.strip()
    context.user_data["rec_jp"]["benefits"] = "" if val.lower() == "skip" else val
    await update.message.reply_text("Step 4/5 — Application deadline (DD/MM/YYYY):")
    return REC_JP_DEADLINE


async def recv_jp_deadline(update, context):
    context.user_data["rec_jp"]["deadline"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇬🇧 English", callback_data="rec_jp_lang_EN"),
        InlineKeyboardButton("🇷🇺 Russian", callback_data="rec_jp_lang_RU"),
        InlineKeyboardButton("🇪🇬 Arabic",  callback_data="rec_jp_lang_AR"),
        InlineKeyboardButton("EN+AR",       callback_data="rec_jp_lang_EN_AR"),
    ]])
    await update.message.reply_text("Step 5/5 — Posting language(s)?", reply_markup=kb)
    return REC_JP_LANGS


async def recv_jp_langs(update, context):
    q = update.callback_query; await q.answer()
    lang = q.data.replace("rec_jp_lang_", "")
    jp = context.user_data["rec_jp"]
    ec, _ = _get_user(str(q.from_user.id))
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    jp_id = _next_id(TAB_JOB_POSTINGS, "JP")

    # If Russian or Arabic requested, generate with AI
    desc_ru, desc_ar = "", ""
    desc_en = jp.get("description_en", "")
    if "RU" in lang and ai_available():
        translated, _ = await improve_text(desc_en, context="general", lang="RU")
        desc_ru = translated
    if "AR" in lang and ai_available():
        translated, _ = await improve_text(desc_en, context="general", lang="AR")
        desc_ar = translated

    _get_or_create_sheets()
    ws = get_sheet(TAB_JOB_POSTINGS)
    ws.append_row([
        jp_id, jp.get("hr_request_id", ""), now,
        jp["position_title"], jp["department"], jp.get("location", ""),
        desc_ar, desc_en, desc_ru,
        jp.get("requirements", ""), jp.get("benefits", ""),
        jp.get("deadline", ""), "Active", "0", ec, now
    ])

    # Update hiring request with posting ID
    row_num, _ = _get_req_row(jp.get("hr_request_id", ""))
    if row_num:
        get_sheet(TAB_HIRING_REQUESTS).update_cell(row_num, 24, jp_id)
        get_sheet(TAB_HIRING_REQUESTS).update_cell(row_num, 23, "Posting_Created")

    _notify_roles(["Director", "HR_Manager", "Direct_Manager"], "recruitment",
                  "Job Posting Created",
                  f"Posting {jp_id} created for {jp['position_title']}.", jp_id)

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📱 Generate Social Media Posts", callback_data=f"rec_social_{jp_id}"),
        InlineKeyboardButton("↩️ Back", callback_data="rec_job_postings"),
    ]])
    await q.edit_message_text(
        f"✅ Job Posting {jp_id} created!\n"
        f"Position: {jp['position_title']}\nDeadline: {jp.get('deadline', '-')}",
        reply_markup=kb)
    return ConversationHandler.END


async def list_postings_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading postings...")
    try:
        rows = get_sheet(TAB_JOB_POSTINGS).get_all_values()
        active = [r for r in rows[1:] if len(r) > 12 and r[12] == "Active"]
        if not active:
            await q.edit_message_text("No active job postings.", reply_markup=_back("rec_job_postings")); return
        lines = ["📢 Active Job Postings\n"]
        for r in active[-10:]:
            lines.append(f"• {r[0]} | {r[3]} | {r[4]} | Deadline: {r[11]}")
        kb = [[InlineKeyboardButton(f"🔍 {r[0]}", callback_data=f"rec_vjp_{r[0]}")]
              for r in active[-8:]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_job_postings"), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_job_postings"))


async def view_jp_handler(update, context):
    q = update.callback_query; await q.answer()
    jp_id = q.data.replace("rec_vjp_", "")
    _, r = _get_jp_row(jp_id)
    if not r:
        await q.edit_message_text("Not found.", reply_markup=_back("rec_list_postings")); return
    msg = (f"📢 {r[0]}\n{'─'*28}\n"
           f"Position:   {r[3]}\nDepartment: {r[4]}\n"
           f"Location:   {r[5]}\nDeadline:   {r[11]}\n"
           f"Candidates: {r[13]}\nStatus:     {r[12]}\n\n"
           f"Requirements:\n{r[9][:300]}")
    kb = [
        [InlineKeyboardButton("📱 Social Media Post", callback_data=f"rec_social_{jp_id}"),
         InlineKeyboardButton("🤖 Interview Qs",      callback_data=f"rec_aiq_{jp_id}")],
        [InlineKeyboardButton("↩️ Back", callback_data="rec_list_postings"), _bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def social_media_post_handler(update, context):
    q = update.callback_query; await q.answer()
    jp_id = q.data.replace("rec_social_", "")
    await q.edit_message_text("⏳ Generating 3 social media post variations...")
    _, r = _get_jp_row(jp_id)
    if not r:
        await q.edit_message_text("Posting not found."); return
    posts, err = await generate_social_posts(
        title=r[3], dept=r[4], requirements=r[9][:500],
        benefits=r[10], phone="+20 10XXXXXXXX", lang="EN"
    )
    if err:
        await q.edit_message_text(f"⚠️ AI error: {err}\n\nPost manually.", reply_markup=_back("rec_list_postings")); return

    msg_parts = ["📱 Social Media Posts — 3 Variations\n(Copy & paste to Facebook/WhatsApp)\n"]
    for i, key in enumerate(["post_1", "post_2", "post_3"], 1):
        text = posts.get(key, "")
        if text:
            msg_parts.append(f"━━━ Variation {i} ━━━\n{text}\n")

    full = "\n".join(msg_parts)
    # Telegram max message length is 4096; split if needed
    for chunk_start in range(0, len(full), 3800):
        chunk = full[chunk_start:chunk_start + 3800]
        if chunk_start == 0:
            await q.edit_message_text(chunk)
        else:
            await q.message.reply_text(chunk)
    await q.message.reply_text("✅ Done! Copy the variation you prefer.",
                                reply_markup=_back("rec_job_postings"))


# ── D: Candidate Management ────────────────────────────────────────────────────

async def add_candidate_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading active postings...")
    try:
        rows = get_sheet(TAB_JOB_POSTINGS).get_all_values()
        active = [r for r in rows[1:] if len(r) > 12 and r[12] == "Active"]
        if not active:
            await q.edit_message_text("No active postings to add candidates for.",
                                       reply_markup=_back("rec_candidates")); return ConversationHandler.END
        context.user_data["rec_active_jps"] = active
        kb = [[InlineKeyboardButton(f"{r[0]} — {r[3]}", callback_data=f"rec_cjp_{i}")]
              for i, r in enumerate(active[:10])]
        kb.append([InlineKeyboardButton("↩️ Cancel", callback_data="rec_candidates")])
        await q.edit_message_text("Select job posting:", reply_markup=InlineKeyboardMarkup(kb))
        return REC_CAND_POSTING
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_candidates"))
        return ConversationHandler.END


async def recv_cand_posting(update, context):
    q = update.callback_query; await q.answer()
    idx = int(q.data.replace("rec_cjp_", ""))
    jp_row = context.user_data["rec_active_jps"][idx]
    context.user_data["rec_cand"] = {
        "posting_id": jp_row[0], "position_title": jp_row[3],
        "department": jp_row[4], "requirements": jp_row[9]
    }
    await q.edit_message_text(
        f"Adding candidate for: {jp_row[3]}\n\nStep 1/6 — Full name:")
    return REC_CAND_NAME


async def recv_cand_name(update, context):
    context.user_data["rec_cand"]["name"] = update.message.text.strip()
    await update.message.reply_text("Step 2/6 — Phone number:")
    return REC_CAND_PHONE


async def recv_cand_phone(update, context):
    context.user_data["rec_cand"]["phone"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(s, callback_data=f"rec_src_{s}")] for s in SOURCES])
    await update.message.reply_text("Step 3/6 — How did they apply?", reply_markup=kb)
    return REC_CAND_SOURCE


async def recv_cand_source(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_cand"]["source"] = q.data.replace("rec_src_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(e, callback_data=f"rec_edu_{e}")] for e in EDU_LEVELS])
    await q.edit_message_text("Step 4/6 — Education level?", reply_markup=kb)
    return REC_CAND_EDU


async def recv_cand_edu(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_cand"]["education"] = q.data.replace("rec_edu_", "")
    await q.edit_message_text("Step 5/6 — Years of experience (number):")
    return REC_CAND_EXP


async def recv_cand_exp(update, context):
    text = update.message.text.strip()
    context.user_data["rec_cand"]["experience"] = text
    await update.message.reply_text("Step 6/6 — Skills / notes (or type 'skip'):")
    return REC_CAND_NOTES


async def recv_cand_notes(update, context):
    val = update.message.text.strip()
    c = context.user_data["rec_cand"]
    c["notes"] = "" if val.lower() == "skip" else val
    ec, _ = _get_user(str(update.effective_user.id))
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    cand_id = _next_id(TAB_CANDIDATES, "CND")
    _get_or_create_sheets()
    ws = get_sheet(TAB_CANDIDATES)
    ws.append_row([
        cand_id, c["posting_id"], c["name"], c["phone"], "",
        c["source"], c["education"], c["experience"], "", c["notes"],
        "", "", "", "", "", "", "", "", "",
        "New", "", "", "", "", "", "", now
    ])
    # Update candidate count on posting
    row_num, r = _get_jp_row(c["posting_id"])
    if row_num:
        try:
            current = int(r[13]) if r[13].isdigit() else 0
            get_sheet(TAB_JOB_POSTINGS).update_cell(row_num, 14, str(current + 1))
        except Exception:
            pass
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "New Candidate Added",
                  f"New candidate: {c['name']} for {c['position_title']} ({cand_id})", cand_id)
    await update.message.reply_text(
        f"✅ Candidate {cand_id} added!\n{c['name']} — {c['source']}",
        reply_markup=_back("rec_candidates"))
    return ConversationHandler.END


async def list_candidates_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading candidates...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:] if r]
        if not items:
            await q.edit_message_text("No candidates yet.", reply_markup=_back("rec_candidates")); return
        lines = ["👤 All Candidates\n"]
        for r in items[-15:]:
            status = r[19] if len(r) > 19 else "?"
            lines.append(f"• {r[0]} | {r[2]} | {r[5]} | {status}")
        kb = [[InlineKeyboardButton(f"🔍 {r[0]} — {r[2]}", callback_data=f"rec_vcand_{r[0]}")]
              for r in items[-8:]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_candidates"), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_candidates"))


async def view_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_vcand_", "")
    row_num, r = _get_cand_row(cand_id)
    if not r:
        await q.edit_message_text("Not found."); return
    ec, role = _get_user(str(q.from_user.id))
    status = r[19] if len(r) > 19 else "New"
    rating = r[11] if len(r) > 11 else "-"
    msg = (f"👤 {r[0]}\n{'─'*28}\n"
           f"Name:       {r[2]}\nPhone:      {r[3]}\n"
           f"Source:     {r[5]}\nEducation:  {r[6]}\n"
           f"Experience: {r[7]} yrs\nPosting:    {r[1]}\n"
           f"Status:     {status}\nRating:     {rating}\n"
           f"Notes:\n{r[9][:200]}")
    kb_rows = []
    if role in HR_ROLES and status == "New":
        kb_rows.append([
            InlineKeyboardButton("⭐ Screen",     callback_data=f"rec_screen_{cand_id}"),
            InlineKeyboardButton("🤖 AI Screen",  callback_data=f"rec_aiscreen_{cand_id}"),
        ])
    if role in HR_ROLES and status == "Screened":
        kb_rows.append([
            InlineKeyboardButton("✅ Shortlist",  callback_data=f"rec_shortlist_{cand_id}"),
            InlineKeyboardButton("❌ Reject",     callback_data=f"rec_reject_{cand_id}"),
        ])
    if role in HR_ROLES and status == "Shortlisted":
        kb_rows.append([
            InlineKeyboardButton("📅 Schedule Interview", callback_data=f"rec_schedcand_{cand_id}"),
        ])
    if role in ("Director", "HR_Manager", "Bot_Manager") and status == "Interviewed":
        kb_rows.append([
            InlineKeyboardButton("✅ Select for Offer", callback_data=f"rec_selectcand_{cand_id}"),
            InlineKeyboardButton("❌ Reject",           callback_data=f"rec_reject_{cand_id}"),
        ])
    if role in HR_ROLES and status == "Selected":
        kb_rows.append([
            InlineKeyboardButton("📄 Create Offer", callback_data=f"rec_offer_{cand_id}"),
        ])
    if role in HR_ROLES and status == "Offer_Sent":
        kb_rows.append([
            InlineKeyboardButton("✅ Offer Accepted", callback_data=f"rec_offaccept_{cand_id}"),
            InlineKeyboardButton("❌ Offer Rejected", callback_data=f"rec_offreject_{cand_id}"),
        ])
    if role in HR_ROLES and status == "Offer_Accepted":
        kb_rows.append([
            InlineKeyboardButton("🚀 Onboard", callback_data=f"rec_onboard_{cand_id}"),
        ])
    kb_rows.append([InlineKeyboardButton("↩️ Back", callback_data="rec_list_candidates"), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))


async def screening_queue_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading screening queue...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        new_cands = [r for r in rows[1:] if len(r) > 19 and r[19] == "New"]
        if not new_cands:
            await q.edit_message_text("No candidates in screening queue.",
                                       reply_markup=_back("rec_candidates")); return
        kb = [[InlineKeyboardButton(f"⭐ {r[0]} — {r[2]}", callback_data=f"rec_screen_{r[0]}")]
              for r in new_cands[:10]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_candidates"), _bm()])
        await q.edit_message_text(
            f"⭐ Screening Queue — {len(new_cands)} candidate(s):",
            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_candidates"))


async def screen_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_screen_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"⭐{i}", callback_data=f"rec_rate_{cand_id}_{i}") for i in range(1, 6)
    ]])
    await q.edit_message_text(
        f"⭐ Screen: {r[2]}\nSource: {r[5]} | Education: {r[6]} | Exp: {r[7]} yrs\n\n"
        f"Rate this candidate:", reply_markup=kb)


async def rate_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    parts = q.data.replace("rec_rate_", "").rsplit("_", 1)
    cand_id, rating = parts[0], parts[1]
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    ec, _ = _get_user(str(q.from_user.id))
    ws = get_sheet(TAB_CANDIDATES)
    ws.update_cell(row_num, 12, rating)
    ws.update_cell(row_num, 14, ec)
    ws.update_cell(row_num, 20, "Screened")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Shortlist", callback_data=f"rec_shortlist_{cand_id}"),
        InlineKeyboardButton("❌ Reject",   callback_data=f"rec_reject_{cand_id}"),
        InlineKeyboardButton("⏸ Hold",     callback_data=f"rec_hold_{cand_id}"),
    ]])
    await q.edit_message_text(
        f"⭐ Rated {rating}/5 — {r[2]}\nDecision?", reply_markup=kb)


async def shortlist_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_shortlist_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    get_sheet(TAB_CANDIDATES).update_cell(row_num, 20, "Shortlisted")
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Candidate Shortlisted",
                  f"{r[2]} shortlisted for posting {r[1]}", cand_id)
    await q.edit_message_text(f"✅ {r[2]} shortlisted!",
                               reply_markup=_back("rec_screening_queue"))


async def reject_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_reject_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws = get_sheet(TAB_CANDIDATES)
    ws.update_cell(row_num, 20, "Rejected")
    ws.update_cell(row_num, 21, f"Rejected at {now}")
    await q.edit_message_text(f"❌ {r[2]} rejected.", reply_markup=_back("rec_candidates"))


async def hold_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_hold_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    get_sheet(TAB_CANDIDATES).update_cell(row_num, 20, "Hold")
    await q.edit_message_text(f"⏸ {r[2]} put on hold.", reply_markup=_back("rec_candidates"))


async def shortlisted_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading shortlisted candidates...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:] if len(r) > 19 and r[19] == "Shortlisted"]
        if not items:
            await q.edit_message_text("No shortlisted candidates.", reply_markup=_back("rec_candidates")); return
        kb = [[InlineKeyboardButton(f"📅 {r[0]} — {r[2]}", callback_data=f"rec_vcand_{r[0]}")]
              for r in items[:10]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_candidates"), _bm()])
        await q.edit_message_text(f"📋 Shortlisted ({len(items)}):",
                                   reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_candidates"))


async def ai_screen_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_aiscreen_", "")
    await q.edit_message_text("⏳ AI screening candidate...")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    _, jp_r = _get_jp_row(r[1])
    requirements = jp_r[9] if jp_r and len(jp_r) > 9 else "General requirements"
    candidate_profile = (
        f"Name: {r[2]}\nSource: {r[5]}\nEducation: {r[6]}\n"
        f"Experience: {r[7]} years\nPrevious employer: {r[8]}\n"
        f"Skills/Notes: {r[9]}"
    )
    result, err = await screen_candidate(candidate_profile, requirements)
    if err:
        await q.edit_message_text(f"⚠️ AI unavailable: {err}",
                                   reply_markup=_back("rec_candidates")); return
    # Save screening notes
    if row_num:
        get_sheet(TAB_CANDIDATES).update_cell(row_num, 13, f"[AI] {result[:500]}")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Shortlist", callback_data=f"rec_shortlist_{cand_id}"),
        InlineKeyboardButton("❌ Reject",   callback_data=f"rec_reject_{cand_id}"),
        InlineKeyboardButton("↩️ Back",     callback_data=f"rec_vcand_{cand_id}"),
    ]])
    await q.edit_message_text(f"🤖 AI Screening — {r[2]}\n\n{result[:800]}", reply_markup=kb)


# ── E: Interview Scheduling ────────────────────────────────────────────────────

async def sched_interview_start(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_schedcand_", "") if q.data.startswith("rec_schedcand_") else None
    if not cand_id:
        # Show list of shortlisted candidates
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:] if len(r) > 19 and r[19] == "Shortlisted"]
        if not items:
            await q.edit_message_text("No shortlisted candidates to schedule.",
                                       reply_markup=_back("rec_interviews")); return ConversationHandler.END
        kb = [[InlineKeyboardButton(f"{r[0]} — {r[2]}", callback_data=f"rec_schedcand_{r[0]}")]
              for r in items[:10]]
        kb.append([InlineKeyboardButton("↩️ Cancel", callback_data="rec_interviews")])
        await q.edit_message_text("Select candidate to schedule interview:",
                                   reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return ConversationHandler.END
    context.user_data["rec_sched"] = {"cand_id": cand_id, "cand_name": r[2]}
    await q.edit_message_text(f"📅 Schedule Interview: {r[2]}\n\nEnter interview date (DD/MM/YYYY):")
    return REC_SCHED_DATE


async def recv_sched_date(update, context):
    context.user_data["rec_sched"]["date"] = update.message.text.strip()
    await update.message.reply_text("Enter interview time (HH:MM, 24h format):")
    return REC_SCHED_TIME


async def recv_sched_time(update, context):
    context.user_data["rec_sched"]["time"] = update.message.text.strip()
    await update.message.reply_text("Enter panel members (employee codes or names, comma-separated):")
    return REC_SCHED_PANEL


async def recv_sched_panel(update, context):
    context.user_data["rec_sched"]["panel"] = update.message.text.strip()
    await update.message.reply_text("Interview notes/questions to prepare (or type 'skip'):")
    return REC_SCHED_NOTES


async def recv_sched_notes(update, context):
    val = update.message.text.strip()
    s = context.user_data["rec_sched"]
    s["notes"] = "" if val.lower() == "skip" else val
    cand_id = s["cand_id"]
    row_num, _ = _get_cand_row(cand_id)
    if row_num:
        ws = get_sheet(TAB_CANDIDATES)
        ws.update_cell(row_num, 15, s["date"])
        ws.update_cell(row_num, 16, s["time"])
        ws.update_cell(row_num, 17, s["panel"])
        ws.update_cell(row_num, 20, "Interview_Scheduled")
    _notify_roles(["HR_Manager", "Direct_Manager"], "recruitment",
                  "Interview Scheduled",
                  f"Interview for {s['cand_name']} on {s['date']} at {s['time']}. Panel: {s['panel']}", cand_id)
    await update.message.reply_text(
        f"✅ Interview scheduled!\n{s['cand_name']}\n{s['date']} at {s['time']}",
        reply_markup=_back("rec_interviews"))
    return ConversationHandler.END


async def view_interviews_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading scheduled interviews...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:] if len(r) > 19 and r[19] == "Interview_Scheduled"]
        if not items:
            await q.edit_message_text("No interviews scheduled.", reply_markup=_back("rec_interviews")); return
        lines = ["📅 Scheduled Interviews\n"]
        for r in items[-10:]:
            lines.append(f"• {r[0]} | {r[2]} | {r[14]} {r[15]}")
        kb = [[InlineKeyboardButton(f"📝 Feedback: {r[2]}", callback_data=f"rec_intfb_{r[0]}")]
              for r in items[:8]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_interviews"), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_interviews"))


# Interview Feedback

async def int_feedback_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading candidates needing feedback...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:]
                 if len(r) > 19 and r[19] in ("Interview_Scheduled", "Interviewed")]
        if not items:
            await q.edit_message_text("No candidates awaiting interview feedback.",
                                       reply_markup=_back("rec_interviews")); return
        kb = [[InlineKeyboardButton(f"📝 {r[2]}", callback_data=f"rec_intfb_{r[0]}")]
              for r in items[:10]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_interviews"), _bm()])
        await q.edit_message_text("Select candidate to give feedback:",
                                   reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_interviews"))


async def int_feedback_start(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_intfb_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return ConversationHandler.END
    context.user_data["rec_fb"] = {"cand_id": cand_id, "cand_name": r[2]}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(str(i), callback_data=f"rec_tech_{i}") for i in range(1, 6)]])
    await q.edit_message_text(
        f"📝 Interview Feedback: {r[2]}\n\nRate Technical Skills (1-5):", reply_markup=kb)
    return REC_INT_TECH


async def recv_int_tech(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_fb"]["tech"] = q.data.replace("rec_tech_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(str(i), callback_data=f"rec_comm_{i}") for i in range(1, 6)]])
    await q.edit_message_text("Rate Communication (1-5):", reply_markup=kb)
    return REC_INT_COMM


async def recv_int_comm(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_fb"]["comm"] = q.data.replace("rec_comm_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(str(i), callback_data=f"rec_expr_{i}") for i in range(1, 6)]])
    await q.edit_message_text("Rate Relevant Experience (1-5):", reply_markup=kb)
    return REC_INT_EXP_RATE


async def recv_int_exp(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_fb"]["exp"] = q.data.replace("rec_expr_", "")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(str(i), callback_data=f"rec_cult_{i}") for i in range(1, 6)]])
    await q.edit_message_text("Rate Culture Fit (1-5):", reply_markup=kb)
    return REC_INT_CULTURE


async def recv_int_culture(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_fb"]["culture"] = q.data.replace("rec_cult_", "")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Hire",       callback_data="rec_rec_hire"),
        InlineKeyboardButton("⚠️ Maybe",      callback_data="rec_rec_maybe"),
        InlineKeyboardButton("❌ Don't Hire", callback_data="rec_rec_no"),
    ]])
    await q.edit_message_text("Overall recommendation?", reply_markup=kb)
    return REC_INT_RECOMMEND


async def recv_int_recommend(update, context):
    q = update.callback_query; await q.answer()
    rec_map = {"rec_rec_hire": "Hire", "rec_rec_maybe": "Maybe", "rec_rec_no": "Don't Hire"}
    context.user_data["rec_fb"]["recommendation"] = rec_map.get(q.data, q.data)
    await q.edit_message_text("Any comments? (or type 'skip'):")
    return REC_INT_COMMENTS


async def recv_int_comments(update, context):
    val = update.message.text.strip()
    fb = context.user_data["rec_fb"]
    fb["comments"] = "" if val.lower() == "skip" else val
    ec, _ = _get_user(str(update.effective_user.id))
    cand_id = fb["cand_id"]
    row_num, r = _get_cand_row(cand_id)
    if row_num:
        # Merge with existing feedback JSON
        try:
            existing = json.loads(r[17]) if len(r) > 17 and r[17] else []
        except Exception:
            existing = []
        tech = int(fb["tech"]); comm = int(fb["comm"])
        exp = int(fb["exp"]); cult = int(fb["culture"])
        avg = round((tech + comm + exp + cult) / 4, 1)
        entry = {
            "by": ec, "tech": tech, "comm": comm, "exp": exp,
            "culture": cult, "avg": avg,
            "recommendation": fb["recommendation"],
            "comments": fb["comments"],
            "date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        existing.append(entry)
        ws = get_sheet(TAB_CANDIDATES)
        ws.update_cell(row_num, 18, json.dumps(existing))
        ws.update_cell(row_num, 19, str(avg))
        ws.update_cell(row_num, 20, "Interviewed")
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Interview Feedback Submitted",
                  f"Feedback for {fb['cand_name']}: {fb['recommendation']} (avg {avg})", cand_id)
    await update.message.reply_text(
        f"✅ Feedback submitted for {fb['cand_name']}!\n"
        f"Technical: {fb['tech']}/5 | Communication: {fb['comm']}/5\n"
        f"Experience: {fb['exp']}/5 | Culture: {fb['culture']}/5\n"
        f"Average: {avg}/5 | Recommendation: {fb['recommendation']}",
        reply_markup=_back("rec_interviews"))
    return ConversationHandler.END


async def ai_questions_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    rows = get_sheet(TAB_JOB_POSTINGS).get_all_values()
    active = [r for r in rows[1:] if len(r) > 12 and r[12] == "Active"]
    if not active:
        await q.edit_message_text("No active postings.", reply_markup=_back("rec_interviews")); return
    kb = [[InlineKeyboardButton(f"{r[0]} — {r[3]}", callback_data=f"rec_aiq_{r[0]}")]
          for r in active[:8]]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_interviews"), _bm()])
    await q.edit_message_text("Select job posting for interview questions:",
                               reply_markup=InlineKeyboardMarkup(kb))


async def ai_questions_handler(update, context):
    q = update.callback_query; await q.answer()
    jp_id = q.data.replace("rec_aiq_", "")
    await q.edit_message_text("⏳ Generating interview questions with AI...")
    _, r = _get_jp_row(jp_id)
    if not r:
        await q.edit_message_text("Not found."); return
    questions, err = await generate_interview_questions(r[3], r[9][:500])
    if err:
        await q.edit_message_text(f"⚠️ AI error: {err}", reply_markup=_back("rec_interviews")); return
    msg = f"🤖 Interview Questions — {r[3]}\n{'─'*30}\n{questions}"
    if len(msg) > 4000:
        msg = msg[:4000]
    await q.edit_message_text(msg, reply_markup=_back("rec_interviews"))


# ── F: Selection & Offer ───────────────────────────────────────────────────────

async def selections_list_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading interviewed candidates...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:] if len(r) > 19 and r[19] == "Interviewed"]
        if not items:
            await q.edit_message_text("No interviewed candidates pending selection.",
                                       reply_markup=_back("rec_selections")); return
        # Sort by final_rating descending
        def _rating(r):
            try: return float(r[18])
            except: return 0
        items.sort(key=_rating, reverse=True)
        lines = ["✅ Interviewed Candidates (ranked by score)\n"]
        for r in items[:10]:
            lines.append(f"• {r[0]} | {r[2]} | ⭐{r[18]}/5 | {r[1]}")
        kb = [[InlineKeyboardButton(f"🔍 {r[0]} — {r[2]} ⭐{r[18]}", callback_data=f"rec_vcand_{r[0]}")]
              for r in items[:8]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_selections"), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_selections"))


async def select_cand_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_selectcand_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    get_sheet(TAB_CANDIDATES).update_cell(row_num, 20, "Selected")
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Candidate Selected",
                  f"{r[2]} has been selected. Create a job offer.", cand_id)
    await q.edit_message_text(
        f"✅ {r[2]} selected!\nHR can now create a job offer.",
        reply_markup=_back("rec_selections"))


async def pending_offers_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading pending offers...")
    try:
        rows = get_sheet(TAB_CANDIDATES).get_all_values()
        items = [r for r in rows[1:]
                 if len(r) > 19 and r[19] in ("Selected", "Offer_Sent")]
        if not items:
            await q.edit_message_text("No pending offers.", reply_markup=_back("rec_selections")); return
        kb = [[InlineKeyboardButton(f"{r[19]}: {r[2]}", callback_data=f"rec_vcand_{r[0]}")]
              for r in items[:10]]
        kb.append([InlineKeyboardButton("↩️ Back", callback_data="rec_selections"), _bm()])
        await q.edit_message_text(f"📄 Pending Offers ({len(items)}):",
                                   reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=_back("rec_selections"))


async def create_offer_start(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_offer_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return ConversationHandler.END
    context.user_data["rec_offer"] = {
        "cand_id": cand_id, "cand_name": r[2], "cand_phone": r[3],
        "posting_id": r[1]
    }
    _, jp_r = _get_jp_row(r[1])
    if jp_r:
        context.user_data["rec_offer"]["position_title"] = jp_r[3]
        context.user_data["rec_offer"]["department"] = jp_r[4]
    await q.edit_message_text(
        f"📄 Create Offer: {r[2]}\n\nStep 1/5 — Offered salary (e.g. 8000 EGP):")
    return REC_OFFER_SALARY


async def recv_offer_salary(update, context):
    context.user_data["rec_offer"]["salary"] = update.message.text.strip()
    await update.message.reply_text("Step 2/5 — Start date (DD/MM/YYYY):")
    return REC_OFFER_START


async def recv_offer_start(update, context):
    context.user_data["rec_offer"]["start_date"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(c, callback_data=f"rec_oct_{c}") for c in CONTRACT_TYPES]])
    await update.message.reply_text("Step 3/5 — Contract type?", reply_markup=kb)
    return REC_OFFER_CONTRACT


async def recv_offer_contract(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["rec_offer"]["contract_type"] = q.data.replace("rec_oct_", "")
    await q.edit_message_text("Step 4/5 — Contract duration (e.g. 1 year), or type 'skip':")
    return REC_OFFER_DURATION


async def recv_offer_duration(update, context):
    val = update.message.text.strip()
    context.user_data["rec_offer"]["contract_duration"] = "" if val.lower() == "skip" else val
    await update.message.reply_text("Step 5/5 — Benefits / special conditions (or type 'skip'):")
    return REC_OFFER_CONDITIONS


async def recv_offer_conditions(update, context):
    val = update.message.text.strip()
    off = context.user_data["rec_offer"]
    off["special_conditions"] = "" if val.lower() == "skip" else val
    ec, _ = _get_user(str(update.effective_user.id))
    hr_emp = _get_emp(ec)
    dir_rec = _get_director_record()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    offer_id = _next_id(TAB_CANDIDATES, "OFF")

    # Update candidate record
    row_num, r = _get_cand_row(off["cand_id"])
    if row_num:
        ws = get_sheet(TAB_CANDIDATES)
        ws.update_cell(row_num, 20, "Offer_Sent")
        ws.update_cell(row_num, 22, off["salary"])
        ws.update_cell(row_num, 23, now)

    # Generate offer PDF
    try:
        dir_sig = _get_sig(_find_ecs_by_role("Director")[0]) if _find_ecs_by_role("Director") else None
        pdf_bytes = generate_offer_pdf({
            "offer_id": offer_id,
            "candidate_name": off["cand_name"],
            "position_title": off.get("position_title", "-"),
            "department": off.get("department", "-"),
            "salary": off["salary"],
            "start_date": off["start_date"],
            "contract_type": off["contract_type"],
            "contract_duration": off.get("contract_duration", ""),
            "special_conditions": off.get("special_conditions", ""),
            "director_name": dir_rec.get("Full_Name", "Director"),
            "hr_name": hr_emp.get("Full_Name", ec),
            "date": now[:10].replace("/", "."),
        }, sigs={"director_sig": dir_sig})
        offer_filename = f"{offer_id}-Offer-{off['cand_name'].replace(' ', '_')}.pdf"
        from drive_utils import upload_to_drive as drive_upload
        drive_url = drive_upload(pdf_bytes, offer_filename, "offers")
        if drive_url:
            await update.message.reply_text(
                f"📄 Job Offer — {off['cand_name']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View PDF", url=drive_url)]]))
        else:
            await update.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename=offer_filename,
                caption=f"📄 Job Offer — {off['cand_name']}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ PDF error: {e}")

    _notify_roles(["HR_Manager", "Director"], "recruitment",
                  "Offer Letter Created",
                  f"Offer for {off['cand_name']} — {off.get('position_title', '-')}. Salary: {off['salary']}", offer_id)
    await update.message.reply_text(
        f"✅ Offer created and PDF generated!\nCandidate: {off['cand_name']}\n"
        f"Salary: {off['salary']}\nStart: {off['start_date']}",
        reply_markup=_back("rec_selections"))
    return ConversationHandler.END


async def offer_accepted_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_offaccept_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    get_sheet(TAB_CANDIDATES).update_cell(row_num, 20, "Offer_Accepted")
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Offer Accepted!",
                  f"{r[2]} accepted the offer! Start onboarding.", cand_id)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Start Onboarding", callback_data=f"rec_onboard_{cand_id}"),
        _bm()
    ]])
    await q.edit_message_text(f"✅ {r[2]} accepted the offer! Ready to onboard.",
                               reply_markup=kb)


async def offer_rejected_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_offreject_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    get_sheet(TAB_CANDIDATES).update_cell(row_num, 20, "Withdrawn")
    await q.edit_message_text(
        f"❌ {r[2]} declined the offer. You can select the next candidate.",
        reply_markup=_back("rec_selections"))


# ── G: Onboarding ─────────────────────────────────────────────────────────────

async def onboard_handler(update, context):
    q = update.callback_query; await q.answer()
    cand_id = q.data.replace("rec_onboard_", "")
    row_num, r = _get_cand_row(cand_id)
    if not row_num:
        await q.edit_message_text("Not found."); return
    await q.edit_message_text("⏳ Creating employee record...")
    try:
        _, jp_r = _get_jp_row(r[1])
        position = jp_r[3] if jp_r and len(jp_r) > 3 else "-"
        dept     = jp_r[4] if jp_r and len(jp_r) > 4 else "-"

        # Assign next emp_code
        all_emps = get_sheet(TAB_EMPLOYEE_DB).get_all_records()
        codes = [int(str(e.get("Emp_Code", 0))) for e in all_emps
                 if str(e.get("Emp_Code", "")).isdigit()]
        new_code = str(max(codes) + 1) if codes else "1001"
        start    = r[23] if len(r) > 23 and r[23] else datetime.now().strftime("%d/%m/%Y")
        now_str  = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Add to Employee_DB
        emp_ws = get_sheet(TAB_EMPLOYEE_DB)
        emp_ws.append_row([
            new_code, r[2], dept, position, "", r[3], "", "Active",
            "", "", "", "", start, "", "", "", "", "", "", "", ""
        ])

        # Add to User_Registry (password = emp_code)
        import bcrypt
        pw_hash = bcrypt.hashpw(new_code.encode(), bcrypt.gensalt(12)).decode()
        get_sheet(TAB_USER_REGISTRY).append_row([
            new_code, "", pw_hash, "Employee", now_str, "Active", "0", now_str
        ])

        # Initialize Leave_Balance
        try:
            get_sheet(TAB_LEAVE_BALANCE).append_row([new_code, r[2], "21", "0", "21"])
        except Exception:
            pass

        # Update candidate record
        ws = get_sheet(TAB_CANDIDATES)
        ws.update_cell(row_num, 20, "Hired")
        ws.update_cell(row_num, 25, new_code)

        # Create onboarding checklist
        _get_or_create_sheets()
        ob_ws = get_sheet(TAB_ONBOARDING)
        checklist = [
            "Employee_DB record created", "User_Registry created",
            "Leave_Balance initialized", "Drive folder created",
            "Contract signed", "Documents collected (ID, photos)",
            "JD assigned", "Safety training scheduled",
            "Manager introduction done", "Equipment/uniform issued"
        ]
        for item in checklist:
            status = "Done" if item in ("Employee_DB record created",
                                        "User_Registry created",
                                        "Leave_Balance initialized") else "Pending"
            ob_ws.append_row([new_code, cand_id, item, status,
                               now_str if status == "Done" else "", ""])

        _notify_roles(["HR_Staff", "HR_Manager", "Director"], "recruitment",
                      "New Employee Onboarded",
                      f"{r[2]} onboarded! Emp_Code: {new_code}. Position: {position}", new_code)
        await q.edit_message_text(
            f"🎉 Onboarding complete!\n\n"
            f"Employee: {r[2]}\nEmp_Code: {new_code}\n"
            f"Department: {dept}\nPosition: {position}\n\n"
            f"✅ Employee_DB, User_Registry, Leave_Balance created.\n"
            f"Onboarding checklist created in Onboarding_Checklist tab.\n"
            f"Default password: {new_code}",
            reply_markup=_back("rec_selections"))
    except Exception as e:
        await q.edit_message_text(f"❌ Onboarding error: {e}",
                                   reply_markup=_back("rec_selections"))


# ── H: Dashboard ───────────────────────────────────────────────────────────────

async def dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Building dashboard...")
    try:
        req_rows  = get_sheet(TAB_HIRING_REQUESTS).get_all_values()[1:]
        jp_rows   = get_sheet(TAB_JOB_POSTINGS).get_all_values()[1:]
        cand_rows = get_sheet(TAB_CANDIDATES).get_all_values()[1:]
        now = datetime.now()

        # Requests this month
        month_str = now.strftime("%m/%Y")
        reqs_month  = [r for r in req_rows if len(r) > 1 and month_str in str(r[1])]
        approved_rq = [r for r in req_rows if len(r) > 22 and r[22] == "Approved"]
        rejected_rq = [r for r in req_rows if len(r) > 22 and r[22] == "Rejected"]

        # Postings
        active_jp = [r for r in jp_rows if len(r) > 12 and r[12] == "Active"]

        # Pipeline counts
        def _count(status):
            return len([r for r in cand_rows if len(r) > 19 and r[19] == status])

        new_c      = _count("New")
        screened   = _count("Screened")
        shortlist  = _count("Shortlisted")
        sched      = _count("Interview_Scheduled")
        interviewed = _count("Interviewed")
        selected   = _count("Selected")
        hired      = _count("Hired")
        total_c    = len(cand_rows)

        # Source breakdown
        sources = {}
        for r in cand_rows:
            src = r[5] if len(r) > 5 else "Unknown"
            sources[src] = sources.get(src, 0) + 1

        src_lines = "\n".join(f"  {k}: {v}" for k, v in sorted(sources.items(), key=lambda x: -x[1])[:5])

        # By department
        depts = {}
        for r in req_rows:
            if len(r) > 22 and r[22] not in ("Rejected", "Filled", "Cancelled"):
                d = r[4] if len(r) > 4 else "?"
                depts[d] = depts.get(d, 0) + 1
        dept_lines = "\n".join(f"  {k}: {v}" for k, v in list(depts.items())[:6])

        msg = (
            f"📊 Recruitment Dashboard\n{'═'*30}\n"
            f"📋 Requests This Month: {len(reqs_month)}\n"
            f"  ✅ Approved: {len(approved_rq)}  ❌ Rejected: {len(rejected_rq)}\n\n"
            f"📢 Active Job Postings: {len(active_jp)}\n"
            f"👤 Total Candidates: {total_c}\n\n"
            f"Pipeline:\n"
            f"  New: {new_c} → Screened: {screened} → Shortlisted: {shortlist}\n"
            f"  Interview: {sched+interviewed} → Selected: {selected} → Hired: {hired}\n\n"
            f"📍 Open Positions by Dept:\n{dept_lines if dept_lines else '  None'}\n\n"
            f"🔗 Candidate Sources:\n{src_lines if src_lines else '  No data'}"
        )
        await q.edit_message_text(msg, reply_markup=_back("menu_recruitment"))
    except Exception as e:
        await q.edit_message_text(f"❌ Dashboard error: {e}", reply_markup=_back("menu_recruitment"))


# ── L: Referral ────────────────────────────────────────────────────────────────

async def refer_start(update, context):
    q = update.callback_query; await q.answer()
    ec, _ = _get_user(str(q.from_user.id))
    context.user_data["rec_ref"] = {"referred_by": ec}
    await q.edit_message_text("🤝 Refer a Candidate\n\nStep 1/4 — Candidate's full name:")
    return REC_REF_NAME


async def recv_ref_name(update, context):
    context.user_data["rec_ref"]["name"] = update.message.text.strip()
    await update.message.reply_text("Step 2/4 — Candidate's phone number:")
    return REC_REF_PHONE


async def recv_ref_phone(update, context):
    context.user_data["rec_ref"]["phone"] = update.message.text.strip()
    await update.message.reply_text("Step 3/4 — Position they are good for:")
    return REC_REF_POSITION


async def recv_ref_position(update, context):
    context.user_data["rec_ref"]["position"] = update.message.text.strip()
    await update.message.reply_text("Step 4/4 — Your relationship with them (colleague, friend, family, etc.):")
    return REC_REF_RELATION


async def recv_ref_relation(update, context):
    val = update.message.text.strip()
    ref = context.user_data["rec_ref"]
    ref["relation"] = val
    ec, _ = _get_user(str(update.effective_user.id))
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Find matching active posting
    posting_id = ""
    try:
        jp_rows = get_sheet(TAB_JOB_POSTINGS).get_all_values()[1:]
        for r in jp_rows:
            if len(r) > 12 and r[12] == "Active":
                posting_id = r[0]; break
    except Exception:
        pass

    cand_id = _next_id(TAB_CANDIDATES, "CND")
    _get_or_create_sheets()
    get_sheet(TAB_CANDIDATES).append_row([
        cand_id, posting_id, ref["name"], ref["phone"], "",
        "Referral", "", "", "", f"Position: {ref['position']} | Relation: {ref['relation']}",
        "", "", "", "", "", "", "", "", "",
        "New", "", "", "", "", "", ref["referred_by"], now
    ])
    _notify_roles(["HR_Staff", "HR_Manager"], "recruitment",
                  "Employee Referral",
                  f"{ref['name']} referred by {ec} for {ref['position']}", cand_id)
    await update.message.reply_text(
        f"✅ Referral submitted!\n{ref['name']} — {ref['position']}\nHR will review.",
        reply_markup=_back("menu_recruitment"))
    return ConversationHandler.END


# ── Conversation Handlers ──────────────────────────────────────────────────────

def get_rec_hiring_request_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(new_request_start, pattern="^rec_new_request$")],
        states={
            REC_HR_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_hr_title)],
            REC_HR_NUM:      [CallbackQueryHandler(recv_hr_num,      pattern="^rec_num_")],
            REC_HR_PRIORITY: [CallbackQueryHandler(recv_hr_priority, pattern="^rec_pri_")],
            REC_HR_JUSTIF:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_hr_justif)],
            REC_HR_AI_WAIT:  [CallbackQueryHandler(recv_hr_ai_choice, pattern="^rec_justif_")],
            REC_HR_START:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_hr_start)],
            REC_HR_CONTRACT: [CallbackQueryHandler(recv_hr_contract, pattern="^rec_ct_")],
            REC_HR_SHIFT:    [CallbackQueryHandler(recv_hr_shift,    pattern="^rec_sh_")],
            REC_HR_LOCATION: [CallbackQueryHandler(recv_hr_location, pattern="^rec_loc_")],
            REC_HR_SALARY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_hr_salary)],
            REC_HR_SPECIAL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_hr_special)],
            REC_HR_CONFIRM:  [CallbackQueryHandler(recv_hr_confirm,  pattern="^rec_req_")],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_job_posting_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(new_posting_start, pattern="^rec_new_posting$")],
        states={
            REC_JP_SELECT:   [CallbackQueryHandler(recv_jp_req,     pattern="^rec_jp_req_")],
            REC_JP_DESC:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_jp_desc)],
            REC_JP_AI_WAIT:  [CallbackQueryHandler(recv_jp_ai,      pattern="^rec_jp_ai_")],
            REC_JP_REQS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_jp_reqs)],
            REC_JP_BENEFITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_jp_benefits)],
            REC_JP_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_jp_deadline)],
            REC_JP_LANGS:    [CallbackQueryHandler(recv_jp_langs,   pattern="^rec_jp_lang_")],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_add_candidate_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(add_candidate_start, pattern="^rec_add_candidate$")],
        states={
            REC_CAND_POSTING: [CallbackQueryHandler(recv_cand_posting, pattern="^rec_cjp_")],
            REC_CAND_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_cand_name)],
            REC_CAND_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_cand_phone)],
            REC_CAND_SOURCE:  [CallbackQueryHandler(recv_cand_source, pattern="^rec_src_")],
            REC_CAND_EDU:     [CallbackQueryHandler(recv_cand_edu,    pattern="^rec_edu_")],
            REC_CAND_EXP:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_cand_exp)],
            REC_CAND_NOTES:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_cand_notes)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_schedule_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(sched_interview_start,
                                           pattern="^rec_sched_interview$|^rec_schedcand_")],
        states={
            REC_SCHED_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_sched_date)],
            REC_SCHED_TIME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_sched_time)],
            REC_SCHED_PANEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_sched_panel)],
            REC_SCHED_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_sched_notes)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_feedback_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(int_feedback_start, pattern="^rec_intfb_")],
        states={
            REC_INT_TECH:      [CallbackQueryHandler(recv_int_tech,      pattern="^rec_tech_")],
            REC_INT_COMM:      [CallbackQueryHandler(recv_int_comm,      pattern="^rec_comm_")],
            REC_INT_EXP_RATE:  [CallbackQueryHandler(recv_int_exp,       pattern="^rec_expr_")],
            REC_INT_CULTURE:   [CallbackQueryHandler(recv_int_culture,   pattern="^rec_cult_")],
            REC_INT_RECOMMEND: [CallbackQueryHandler(recv_int_recommend, pattern="^rec_rec_")],
            REC_INT_COMMENTS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_int_comments)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_offer_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(create_offer_start, pattern="^rec_offer_")],
        states={
            REC_OFFER_SALARY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_offer_salary)],
            REC_OFFER_START:      [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_offer_start)],
            REC_OFFER_CONTRACT:   [CallbackQueryHandler(recv_offer_contract, pattern="^rec_oct_")],
            REC_OFFER_DURATION:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_offer_duration)],
            REC_OFFER_CONDITIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_offer_conditions)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


def get_rec_referral_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(refer_start, pattern="^rec_refer$")],
        states={
            REC_REF_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_ref_name)],
            REC_REF_PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_ref_phone)],
            REC_REF_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_ref_position)],
            REC_REF_RELATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_ref_relation)],
        },
        fallbacks=[CallbackQueryHandler(lambda u, c: ConversationHandler.END,
                                        pattern="^back_to_menu$")],
        per_message=False,
    )


# ── Public exports ─────────────────────────────────────────────────────────────

def get_recruitment_handlers():
    """All ConversationHandlers for the recruitment system."""
    return [
        get_rec_hiring_request_handler(),
        get_rec_job_posting_handler(),
        get_rec_add_candidate_handler(),
        get_rec_schedule_handler(),
        get_rec_feedback_handler(),
        get_rec_offer_handler(),
        get_rec_referral_handler(),
    ]


def get_recruitment_static_handlers():
    """All static CallbackQueryHandlers for the recruitment system."""
    return [
        # Menus
        CallbackQueryHandler(recruitment_menu_handler,  pattern="^menu_recruitment$"),
        CallbackQueryHandler(hiring_requests_menu,      pattern="^rec_hiring_requests$"),
        CallbackQueryHandler(job_postings_menu,         pattern="^rec_job_postings$"),
        CallbackQueryHandler(candidates_menu,           pattern="^rec_candidates$"),
        CallbackQueryHandler(interviews_menu,           pattern="^rec_interviews$"),
        CallbackQueryHandler(selections_menu,           pattern="^rec_selections$"),
        CallbackQueryHandler(dashboard_handler,         pattern="^rec_dashboard$"),
        # Hiring Requests
        CallbackQueryHandler(view_requests_handler,     pattern="^rec_view_requests$"),
        CallbackQueryHandler(approve_requests_handler,  pattern="^rec_approve_requests$"),
        CallbackQueryHandler(view_req_detail,           pattern="^rec_vreq_"),
        CallbackQueryHandler(hr_approve_req,            pattern="^rec_hrapprove_"),
        CallbackQueryHandler(hr_reject_req,             pattern="^rec_hrreject_"),
        CallbackQueryHandler(dir_approve_req,           pattern="^rec_dirapprove_"),
        CallbackQueryHandler(dir_reject_req,            pattern="^rec_dirreject_"),
        # Job Postings
        CallbackQueryHandler(list_postings_handler,     pattern="^rec_list_postings$"),
        CallbackQueryHandler(view_jp_handler,           pattern="^rec_vjp_"),
        CallbackQueryHandler(social_media_post_handler, pattern="^rec_social_"),
        # Candidates
        CallbackQueryHandler(list_candidates_handler,   pattern="^rec_list_candidates$"),
        CallbackQueryHandler(view_cand_handler,         pattern="^rec_vcand_"),
        CallbackQueryHandler(screening_queue_handler,   pattern="^rec_screening_queue$"),
        CallbackQueryHandler(shortlisted_handler,       pattern="^rec_shortlisted$"),
        CallbackQueryHandler(screen_cand_handler,       pattern="^rec_screen_"),
        CallbackQueryHandler(rate_cand_handler,         pattern="^rec_rate_"),
        CallbackQueryHandler(shortlist_cand_handler,    pattern="^rec_shortlist_"),
        CallbackQueryHandler(reject_cand_handler,       pattern="^rec_reject_"),
        CallbackQueryHandler(hold_cand_handler,         pattern="^rec_hold_"),
        CallbackQueryHandler(ai_screen_handler,         pattern="^rec_aiscreen_"),
        # Interviews
        CallbackQueryHandler(view_interviews_handler,   pattern="^rec_view_interviews$"),
        CallbackQueryHandler(int_feedback_menu_handler, pattern="^rec_int_feedback_menu$"),
        CallbackQueryHandler(ai_questions_menu_handler, pattern="^rec_ai_questions_menu$"),
        CallbackQueryHandler(ai_questions_handler,      pattern="^rec_aiq_"),
        # Selections & Offers
        CallbackQueryHandler(selections_list_handler,   pattern="^rec_selections_list$"),
        CallbackQueryHandler(pending_offers_handler,    pattern="^rec_pending_offers$"),
        CallbackQueryHandler(select_cand_handler,       pattern="^rec_selectcand_"),
        CallbackQueryHandler(offer_accepted_handler,    pattern="^rec_offaccept_"),
        CallbackQueryHandler(offer_rejected_handler,    pattern="^rec_offreject_"),
        # Onboarding
        CallbackQueryHandler(onboard_handler,           pattern="^rec_onboard_"),
    ]
