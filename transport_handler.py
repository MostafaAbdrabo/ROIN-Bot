"""
ROIN WORLD FZE — Transport Handler v1
======================================
Handles:
  A. Vehicle Request (Near/Far point-to-point trip)
  B. Commute Request (daily work transport with employee list)
  C. Manager / Director approval of trip requests
  D. Transport Manager: pending trips + vehicle assignment + commute assignment
  E. Driver: view assigned trips, start / stop / end trip

Google Sheet tabs required (add to master workbook):
─────────────────────────────────────────────────────
  Transport_Requests  (36 columns — see TC class below)
  Commute_Log         (12 columns — see CC class below)
  Vehicles            (9 columns)
     Vehicle_ID | Plate | Type | Capacity | Driver_Code |
     Driver_Name | Driver_Phone | Status | Notes

Progressive PDF Drive links (Rule 5.10):
  At each approval stage → generate PDF → upload → save link → show [📄 View PDF] button.
"""

import json
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet
from drive_utils import upload_to_drive
from transport_pdf_generator import generate_transport_request_pdf, generate_commute_pdf


# ── Back-button helpers ────────────────────────────────────────────────────────
def _bm():    return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bveh():  return InlineKeyboardButton("↩️ Transport",  callback_data="menu_transport")


# ── Locations ──────────────────────────────────────────────────────────────────
# (Arabic display, English for PDF)
NEAR_LOCS = [
    ("الضبعة",              "Dabaa"),
    ("الموقع",              "Site"),
    ("كورونادو",            "Coronado"),
    ("المطبخ المصري",       "Egyptian Kitchen"),
    ("المطبخ الروسي",       "Russian Kitchen"),
    ("المطبخ الحلواني",     "Pastry Kitchen"),
    ("البيكري",             "Bakery"),
    ("فود تراك (الموقع)",   "Food Truck (Site)"),
    ("البنك",               "Bank"),
    ("سكن الضبعة",          "Dabaa Housing"),
]
FAR_LOCS = [
    ("سيدي عبدالرحمن",  "Sidi Abd El-Rahman"),
    ("العلمين",          "El Alamein"),
    ("الاسكندرية",       "Alexandria"),
    ("مطروح",            "Matruh"),
    ("القاهرة",          "Cairo"),
]
ALL_LOCS_AR  = [a for a, _ in NEAR_LOCS + FAR_LOCS]
ALL_LOCS_MAP = {a: e for a, e in NEAR_LOCS + FAR_LOCS}   # Arabic → English


# ── Column index constants (1-based for gspread update_cell) ──────────────────
class TC:   # Transport_Requests tab
    REQ_ID       = 1
    SUBMITTED    = 2
    REQ_CODE     = 3
    REQ_NAME     = 4   # VLOOKUP — write ""
    REQ_DEPT     = 5   # VLOOKUP — write ""
    TRIP_TYPE    = 6   # Near / Far
    FROM_LOC     = 7
    TO_LOC       = 8
    PURPOSE      = 9
    DATE         = 10
    DEP_TIME     = 11
    PASSENGERS   = 12
    NOTES        = 13
    MGR_STATUS   = 14  # Pending / Approved / Rejected
    MGR_DATE     = 15
    MGR_CODE     = 16
    MGR_NAME     = 17  # VLOOKUP — write ""
    DIR_STATUS   = 18  # NA / Pending / Approved / Rejected
    DIR_DATE     = 19
    DIR_CODE     = 20
    DIR_NAME     = 21  # VLOOKUP — write ""
    TRANS_STATUS = 22  # Pending / Assigned / Rejected
    TRANS_DATE   = 23
    TRANS_CODE   = 24
    VEH_PLATE    = 25
    DRIVER_CODE  = 26
    DRIVER_NAME  = 27  # VLOOKUP — write ""
    ACT_DEPART   = 28
    ACT_RETURN   = 29
    FUEL_START   = 30
    FUEL_END     = 31
    ODO_START    = 32
    ODO_END      = 33
    DELAY_REASON = 34
    FINAL_STATUS = 35
    DRIVE_LINK   = 36
    LAST_LAT     = 37
    LAST_LONG    = 38
    LAST_LOC_TIME = 39
    LOC_SHARED   = 40
    MAPS_LINK    = 41
    LAST_ALERT   = 42


class CC:   # Commute_Log tab
    COM_ID       = 1
    SUBMITTED    = 2
    REQ_CODE     = 3
    DATE         = 4
    DEP_TIME     = 5
    FROM_LOC     = 6
    TO_LOC       = 7
    EMP_CODES    = 8   # comma-separated employee codes
    EMP_COUNT    = 9
    STATUS       = 10  # Pending / Assigned / Completed
    ASSIGNMENTS  = 11  # JSON
    DRIVE_LINK   = 12


# ── Conversation states ────────────────────────────────────────────────────────
TR_TYPE    = 2000
TR_FROM    = 2001
TR_TO      = 2002
TR_TIMING  = 2003
TR_TIME    = 2004
TR_PASS    = 2005
TR_PURPOSE = 2006
TR_CONFIRM = 2007
TR_REJ     = 2008   # Manager/Director rejection reason (text input)

COM_DATE    = 2010
COM_TIME    = 2011
COM_FROM    = 2012
COM_TO      = 2013
COM_EMPS    = 2014  # Add employees by code (loop)
COM_CONFIRM = 2015

DRV_START_ODO  = 2030
DRV_START_FUEL = 2031
DRV_END_ODO    = 2032
DRV_END_FUEL   = 2033
DRV_STOP_RSN   = 2034


# ══════════════════════════════════════════════════════════════════════════════
#  SHEET HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_emp_by_tid(tid):
    """Return dict with emp_code, name, dept, role, manager_code or None."""
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if r[1].strip() == str(tid):
                ec = r[0].strip()
                role = r[3].strip() if len(r) > 3 else "Employee"
                for j, e in enumerate(get_sheet("Employee_DB").get_all_values()):
                    if j == 0:
                        continue
                    if e[0].strip() == ec:
                        return {
                            "code": ec,
                            "name": e[1].strip() if len(e) > 1 else ec,
                            "dept": e[4].strip() if len(e) > 4 else "",
                            "role": role,
                            "mgr":  e[8].strip() if len(e) > 8 else "",
                        }
                return {"code": ec, "name": ec, "dept": "", "role": role, "mgr": ""}
    except Exception:
        pass
    return None


def _get_emp_by_code(code):
    """Return dict with code, name, dept or None."""
    try:
        for i, e in enumerate(get_sheet("Employee_DB").get_all_values()):
            if i == 0:
                continue
            if e[0].strip() == str(code).strip():
                return {
                    "code": e[0].strip(),
                    "name": e[1].strip() if len(e) > 1 else code,
                    "dept": e[4].strip() if len(e) > 4 else "",
                }
    except Exception:
        pass
    return None


def _get_tid_by_code(emp_code):
    """Return Telegram ID string for an employee code, or None."""
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if r[0].strip() == str(emp_code) and r[1].strip():
                return r[1].strip()
    except Exception:
        pass
    return None


def _users_by_role(role):
    """Return list of (emp_code, tid) for users with given role."""
    out = []
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if len(r) > 3 and r[3].strip() == role and r[1].strip():
                out.append((r[0].strip(), r[1].strip()))
    except Exception:
        pass
    return out


def _gen_trip_id():
    yr = datetime.now().strftime("%Y")
    px = f"TREQ-{yr}-"
    ids = get_sheet("Transport_Requests").col_values(1)
    mx = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx + 1:04d}"


def _gen_commute_id():
    yr = datetime.now().strftime("%Y")
    px = f"COM-{yr}-"
    ids = get_sheet("Commute_Log").col_values(1)
    mx = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx + 1:04d}"


def _find_trip(req_id):
    """Return (row_num_1based, row_list) or (None, None)."""
    try:
        rows = get_sheet("Transport_Requests").get_all_values()
        for i, r in enumerate(rows):
            if i == 0:
                continue
            if r[0].strip() == str(req_id):
                return i + 1, r
    except Exception:
        pass
    return None, None


def _find_commute(com_id):
    try:
        rows = get_sheet("Commute_Log").get_all_values()
        for i, r in enumerate(rows):
            if i == 0:
                continue
            if r[0].strip() == str(com_id):
                return i + 1, r
    except Exception:
        pass
    return None, None


def _update_trip(rn, col, val):
    get_sheet("Transport_Requests").update_cell(rn, col, val)


def _update_commute(rn, col, val):
    get_sheet("Commute_Log").update_cell(rn, col, val)


def _get_vehicles(only_available=True):
    """Return list of vehicle dicts from Vehicles tab."""
    out = []
    try:
        rows = get_sheet("Vehicles").get_all_values()
        for i, r in enumerate(rows):
            if i == 0:
                continue
            if len(r) < 4:
                continue
            status = r[7].strip() if len(r) > 7 else "Available"
            if only_available and status != "Available":
                continue
            try:
                cap = int(r[3].strip())
            except Exception:
                cap = 0
            out.append({
                "id":          r[0].strip(),
                "plate":       r[1].strip(),
                "type":        r[2].strip(),
                "capacity":    cap,
                "driver_code": r[4].strip() if len(r) > 4 else "",
                "driver_name": r[5].strip() if len(r) > 5 else "",
                "driver_phone":r[6].strip() if len(r) > 6 else "",
                "status":      status,
            })
    except Exception:
        pass
    return out


def _get_emp_name(code):
    e = _get_emp_by_code(code)
    return e["name"] if e else code


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _today():
    return datetime.now().strftime("%d/%m/%Y")


def _tomorrow():
    return (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TRANSPORT MENU
# ══════════════════════════════════════════════════════════════════════════════

async def transport_menu_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    role = emp["role"] if emp else "Employee"

    kb = [
        [InlineKeyboardButton("🚗 Request Vehicle",     callback_data="tr_request_start")],
        [InlineKeyboardButton("🚌 Commute Request",     callback_data="tr_commute_start")],
        [InlineKeyboardButton("📋 My Requests",          callback_data="tr_my_requests")],
        [InlineKeyboardButton("📂 Transport Archive",    callback_data="tr_archive")],
    ]

    if role == "Driver":
        kb.insert(2, [InlineKeyboardButton("🗺 My Trips",  callback_data="tr_driver_trips")])

    # Approval queues — Bot_Manager sees all, other roles see their own
    if role in ("Direct_Manager", "Supervisor", "HR_Manager", "Bot_Manager"):
        kb.append([InlineKeyboardButton(
            "📋 Pending: Manager Approval", callback_data="tr_mgr_pending")])

    if role in ("Director", "Bot_Manager"):
        kb.append([InlineKeyboardButton(
            "📋 Pending: Director Approval", callback_data="tr_dir_pending")])

    if role in ("Transport_Manager", "Bot_Manager"):
        kb += [
            [InlineKeyboardButton("📋 Pending: Transport Assignment", callback_data="tr_tm_pending")],
            [InlineKeyboardButton("🚌 Assign Commute Vehicles",       callback_data="tr_tm_commute_list")],
            [InlineKeyboardButton("📊 Fleet Dashboard",               callback_data="tr_fleet_dash")],
            [InlineKeyboardButton("📄 Upload Driver Permits",         callback_data="veh_upload_permit")],
        ]

    kb.append([_bm()])
    await q.edit_message_text("🚗 Transport\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  A. TRIP REQUEST FLOW
# ══════════════════════════════════════════════════════════════════════════════

async def tr_request_start(update, context):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("📍 Near Trip  (Local Sites)", callback_data="tr_type_Near")],
        [InlineKeyboardButton("🏙 Far Trip   (Remote City)", callback_data="tr_type_Far")],
        [_bveh(), _bm()],
    ]
    await q.edit_message_text(
        "🚗 Vehicle Request\n\n"
        "📍 *Near Trip* — between: Dabaa, Site, Coronado, Kitchens, Bank, Housing\n"
        "🏙 *Far Trip* — to: Alexandria, Cairo, Matruh, El Alamein, Sidi Abd El-Rahman\n\n"
        "Choose trip type:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb))
    return TR_TYPE


async def tr_type_cb(update, context):
    q = update.callback_query
    await q.answer()
    trip_type = q.data.replace("tr_type_", "")
    context.user_data["tr_type"] = trip_type
    locs = NEAR_LOCS if trip_type == "Near" else FAR_LOCS
    kb = [[InlineKeyboardButton(ar, callback_data=f"tr_from_{i}")] for i, (ar, _) in enumerate(locs)]
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📍 FROM — Select departure location:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return TR_FROM


async def tr_from_cb(update, context):
    q = update.callback_query
    await q.answer()
    trip_type = context.user_data.get("tr_type", "Near")
    locs = NEAR_LOCS if trip_type == "Near" else FAR_LOCS
    idx = int(q.data.replace("tr_from_", ""))
    ar, en = locs[idx]
    context.user_data["tr_from_ar"] = ar
    context.user_data["tr_from_en"] = en
    # Build TO list (same pool, exclude chosen)
    to_locs = [(i, a, e) for i, (a, e) in enumerate(locs) if a != ar]
    kb = [[InlineKeyboardButton(a, callback_data=f"tr_to_{i}")] for i, a, e in to_locs]
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(f"✅ From: {ar}\n\n🏁 TO — Select destination:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return TR_TO


async def tr_to_cb(update, context):
    q = update.callback_query
    await q.answer()
    trip_type = context.user_data.get("tr_type", "Near")
    locs = NEAR_LOCS if trip_type == "Near" else FAR_LOCS
    idx = int(q.data.replace("tr_to_", ""))
    ar, en = locs[idx]
    context.user_data["tr_to_ar"] = ar
    context.user_data["tr_to_en"] = en
    kb = [
        [InlineKeyboardButton("📅 Today",    callback_data="tr_timing_today")],
        [InlineKeyboardButton("📅 Tomorrow", callback_data="tr_timing_tomorrow")],
        [_bveh(), _bm()],
    ]
    await q.edit_message_text(
        f"✅ From: {context.user_data['tr_from_ar']}\n"
        f"✅ To:   {ar}\n\n"
        "🗓 When do you need the vehicle?",
        reply_markup=InlineKeyboardMarkup(kb))
    return TR_TIMING


async def tr_timing_cb(update, context):
    q = update.callback_query
    await q.answer()
    timing = q.data.replace("tr_timing_", "")
    context.user_data["tr_timing"] = timing
    if timing == "today":
        context.user_data["tr_date"] = _today()
        min_time = (datetime.now() + timedelta(minutes=15)).strftime("%H:%M")
        hint = f"⚠️ Today's requests must depart at least 15 minutes from now.\nEarliest: *{min_time}*\n\n"
    else:
        context.user_data["tr_date"] = _tomorrow()
        hint = ""
    await q.edit_message_text(
        f"{hint}⏰ Enter departure time (format: *HH:MM*):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return TR_TIME


async def tr_time_inp(update, context):
    raw = update.message.text.strip()
    try:
        t = datetime.strptime(raw, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Format: HH:MM  (e.g. 08:30)",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return TR_TIME
    if context.user_data.get("tr_timing") == "today":
        min_t = datetime.now() + timedelta(minutes=15)
        if t.hour * 60 + t.minute < min_t.hour * 60 + min_t.minute:
            await update.message.reply_text(
                f"⚠️ Too soon. Earliest departure today: *{min_t.strftime('%H:%M')}*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
            return TR_TIME
    context.user_data["tr_time"] = raw
    await update.message.reply_text(
        "👥 How many passengers? (enter a number):",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return TR_PASS


async def tr_pass_inp(update, context):
    raw = update.message.text.strip()
    if not raw.isdigit() or int(raw) < 1:
        await update.message.reply_text(
            "⚠️ Enter a valid number (1 or more):",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return TR_PASS
    context.user_data["tr_pass"] = int(raw)
    await update.message.reply_text(
        "💬 Enter the purpose / reason for this trip:",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return TR_PURPOSE


async def tr_purpose_inp(update, context):
    context.user_data["tr_purpose"] = update.message.text.strip()
    d = context.user_data
    trip_type = d.get("tr_type", "Near")
    approval_note = ("📋 Approval: Direct Manager only → Transport Manager assigns"
                     if trip_type == "Near" else
                     "📋 Approval: Direct Manager → Director → Transport Manager assigns")
    summary = (
        f"📋 *Trip Request Summary*\n"
        f"{'─' * 28}\n"
        f"🔹 Type:      {'Near (Local)' if trip_type == 'Near' else 'Far (Remote)'}\n"
        f"🔹 From:      {d.get('tr_from_ar')}\n"
        f"🔹 To:        {d.get('tr_to_ar')}\n"
        f"🔹 Date:      {d.get('tr_date')}\n"
        f"🔹 Time:      {d.get('tr_time')}\n"
        f"🔹 Passengers:{d.get('tr_pass')}\n"
        f"🔹 Purpose:   {d.get('tr_purpose')}\n\n"
        f"{approval_note}"
    )
    kb = [
        [InlineKeyboardButton("✅ Submit", callback_data="tr_confirm_yes"),
         InlineKeyboardButton("❌ Cancel", callback_data="tr_confirm_no")],
        [_bveh(), _bm()],
    ]
    await update.message.reply_text(summary, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return TR_CONFIRM


async def tr_confirm(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "tr_confirm_no":
        await q.edit_message_text("❌ Cancelled.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END

    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("❌ Not registered.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    d = context.user_data
    trip_type = d.get("tr_type", "Near")
    now_str   = _now()
    director_status = "NA" if trip_type == "Near" else "Pending"

    try:
        req_id = _gen_trip_id()
    except Exception as e:
        await q.edit_message_text(
            "❌ Setup error: The 'Transport_Requests' sheet tab is missing.\n\n"
            "Please create it in Google Sheets with the required headers, then try again.",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END

    row = [""] * TC.DRIVE_LINK
    row[TC.REQ_ID     - 1] = req_id
    row[TC.SUBMITTED  - 1] = now_str
    row[TC.REQ_CODE   - 1] = emp["code"]
    row[TC.REQ_NAME   - 1] = ""          # VLOOKUP
    row[TC.REQ_DEPT   - 1] = ""          # VLOOKUP
    row[TC.TRIP_TYPE  - 1] = trip_type
    row[TC.FROM_LOC   - 1] = d.get("tr_from_en", d.get("tr_from_ar", ""))
    row[TC.TO_LOC     - 1] = d.get("tr_to_en",   d.get("tr_to_ar",   ""))
    row[TC.PURPOSE    - 1] = d.get("tr_purpose", "")
    row[TC.DATE       - 1] = d.get("tr_date", "")
    row[TC.DEP_TIME   - 1] = d.get("tr_time", "")
    row[TC.PASSENGERS - 1] = str(d.get("tr_pass", ""))
    row[TC.NOTES      - 1] = ""
    row[TC.MGR_STATUS - 1] = "Pending"
    row[TC.DIR_STATUS - 1] = director_status
    row[TC.TRANS_STATUS-1] = "Pending"
    row[TC.FINAL_STATUS-1] = "Pending"
    try:
        get_sheet("Transport_Requests").append_row(row)
    except Exception as e:
        await q.edit_message_text(
            f"❌ Could not save request: {e}\n\n"
            "Make sure the 'Transport_Requests' tab exists in Google Sheets.",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END

    # Rule 5.10 — generate submitted PDF with employee signature
    sub_url = None
    try:
        rn, rd = _find_trip(req_id)
        if rn:
            pdf_data = _build_pdf_data(rd, emp["name"], emp["dept"])
            # Fetch employee (submitter) signature
            try:
                from signature_handler import get_sig_bytes
                sb, st = await get_sig_bytes(context.bot, emp["code"])
                pdf_data["submitter_sig_bytes"] = sb
                pdf_data["submitter_sig_text"] = st
            except Exception:
                pass
            pdf_bytes = generate_transport_request_pdf(pdf_data)
            sub_url = upload_to_drive(pdf_bytes, f"{req_id}_submitted.pdf", "transport_requests")
            if sub_url:
                _update_trip(rn, TC.DRIVE_LINK, sub_url)
    except Exception as e:
        print(f"[transport] submitted PDF error: {e}")

    kb = [[_bveh(), _bm()]]
    if sub_url:
        kb.insert(0, [InlineKeyboardButton("📄 View Submitted Request", url=sub_url)])
    await q.edit_message_text(
        f"✅ Submitted!\n🔖 ID: {req_id}\n🕐 {now_str}\n\n"
        f"Your Direct Manager will review it.",
        reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


async def tr_cancel(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Cancelled.",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
    elif update.message:
        await update.message.reply_text(
            "❌ Cancelled.",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  B. COMMUTE REQUEST FLOW
# ══════════════════════════════════════════════════════════════════════════════

async def tr_commute_start(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["com_emps"] = []
    kb = [
        [InlineKeyboardButton("📅 Today",    callback_data="com_date_today")],
        [InlineKeyboardButton("📅 Tomorrow", callback_data="com_date_tomorrow")],
        [_bveh(), _bm()],
    ]
    await q.edit_message_text(
        "🚌 Commute Request — Work Transport\n\n"
        "Fixed daily trips to/from work.\n\n"
        "📅 Which date?",
        reply_markup=InlineKeyboardMarkup(kb))
    return COM_DATE


async def com_date_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["com_date"] = _today() if "today" in q.data else _tomorrow()
    await q.edit_message_text(
        f"✅ Date: {context.user_data['com_date']}\n\n"
        "⏰ Enter departure time (HH:MM):",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return COM_TIME


async def com_time_inp(update, context):
    raw = update.message.text.strip()
    try:
        datetime.strptime(raw, "%H:%M")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Format: HH:MM",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return COM_TIME
    context.user_data["com_time"] = raw
    # FROM location
    kb = [[InlineKeyboardButton(ar, callback_data=f"com_from_{i}")]
          for i, (ar, _) in enumerate(NEAR_LOCS)]
    kb.append([_bveh(), _bm()])
    await update.message.reply_text(
        f"✅ Time: {raw}\n\n📍 FROM — Select pickup location:",
        reply_markup=InlineKeyboardMarkup(kb))
    return COM_FROM


async def com_from_cb(update, context):
    q = update.callback_query
    await q.answer()
    idx = int(q.data.replace("com_from_", ""))
    ar, en = NEAR_LOCS[idx]
    context.user_data["com_from_ar"] = ar
    context.user_data["com_from_en"] = en
    to_locs = [(i, a, e) for i, (a, e) in enumerate(NEAR_LOCS) if a != ar]
    kb = [[InlineKeyboardButton(a, callback_data=f"com_to_{i}")] for i, a, e in to_locs]
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(
        f"✅ From: {ar}\n\n🏁 TO — Select destination:",
        reply_markup=InlineKeyboardMarkup(kb))
    return COM_TO


async def com_to_cb(update, context):
    q = update.callback_query
    await q.answer()
    idx = int(q.data.replace("com_to_", ""))
    ar, en = NEAR_LOCS[idx]
    context.user_data["com_to_ar"] = ar
    context.user_data["com_to_en"] = en
    emps = context.user_data.get("com_emps", [])
    await q.edit_message_text(
        f"✅ From: {context.user_data['com_from_ar']}\n"
        f"✅ To:   {ar}\n\n"
        f"👥 Add employees by code.\n"
        f"Type one code at a time. When done, send *done*.\n\n"
        f"Added so far: {len(emps)} employee(s)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return COM_EMPS


async def com_emps_inp(update, context):
    txt = update.message.text.strip()
    emps = context.user_data.setdefault("com_emps", [])

    if txt.lower() == "done":
        if not emps:
            await update.message.reply_text(
                "⚠️ Add at least one employee first.",
                reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
            return COM_EMPS
        # Show summary + confirm
        lines = "\n".join(f"  • {e['code']} — {e['name']} ({e['dept']})" for e in emps)
        d = context.user_data
        summary = (
            f"🚌 *Commute Request Summary*\n"
            f"{'─' * 28}\n"
            f"📅 Date:  {d.get('com_date')}\n"
            f"⏰ Time:  {d.get('com_time')}\n"
            f"📍 From:  {d.get('com_from_ar')}\n"
            f"🏁 To:    {d.get('com_to_ar')}\n"
            f"👥 Employees ({len(emps)}):\n{lines}"
        )
        kb = [
            [InlineKeyboardButton("✅ Submit", callback_data="com_confirm_yes"),
             InlineKeyboardButton("❌ Cancel", callback_data="com_confirm_no")],
            [_bveh(), _bm()],
        ]
        await update.message.reply_text(summary, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(kb))
        return COM_CONFIRM

    emp = _get_emp_by_code(txt)
    if not emp:
        await update.message.reply_text(
            f"❌ Employee code *{txt}* not found. Try again:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return COM_EMPS

    if any(e["code"] == emp["code"] for e in emps):
        await update.message.reply_text(
            f"⚠️ {emp['name']} already added.",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return COM_EMPS

    emps.append(emp)
    await update.message.reply_text(
        f"✅ Added: {emp['name']} ({emp['code']}) — {emp['dept']}\n\n"
        f"Total: {len(emps)} employee(s). Add another code or send *done*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return COM_EMPS


async def com_confirm(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "com_confirm_no":
        await q.edit_message_text("❌ Cancelled.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END

    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("❌ Not registered.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    d = context.user_data
    emps = d.get("com_emps", [])
    now_str  = _now()
    com_id   = _gen_commute_id()
    codes_str = ",".join(e["code"] for e in emps)

    row = [""] * CC.DRIVE_LINK
    row[CC.COM_ID    - 1] = com_id
    row[CC.SUBMITTED - 1] = now_str
    row[CC.REQ_CODE  - 1] = emp["code"]
    row[CC.DATE      - 1] = d.get("com_date", "")
    row[CC.DEP_TIME  - 1] = d.get("com_time", "")
    row[CC.FROM_LOC  - 1] = d.get("com_from_en", d.get("com_from_ar", ""))
    row[CC.TO_LOC    - 1] = d.get("com_to_en",   d.get("com_to_ar", ""))
    row[CC.EMP_CODES - 1] = codes_str
    row[CC.EMP_COUNT - 1] = str(len(emps))
    row[CC.STATUS    - 1] = "Pending"
    get_sheet("Commute_Log").append_row(row)

    kb = [[_bveh(), _bm()]]
    await q.edit_message_text(
        f"✅ Commute Request Submitted!\n"
        f"🔖 ID: {com_id}\n"
        f"👥 {len(emps)} employee(s)\n"
        f"🕐 {now_str}\n\n"
        f"Transport Manager will assign vehicles.",
        reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  C. MY REQUESTS VIEW
# ══════════════════════════════════════════════════════════════════════════════

async def tr_my_requests(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("❌ Not registered.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    rows = get_sheet("Transport_Requests").get_all_values()
    my = [r for i, r in enumerate(rows) if i > 0 and r[TC.REQ_CODE - 1].strip() == emp["code"]]

    if not my:
        await q.edit_message_text("📋 No transport requests yet.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    kb = []
    for r in my[-20:]:
        rid    = r[TC.REQ_ID - 1]
        status = r[TC.FINAL_STATUS - 1]
        date   = r[TC.DATE - 1]
        frm    = r[TC.FROM_LOC - 1][:10]
        to     = r[TC.TO_LOC - 1][:10]
        label  = f"{rid} | {frm}→{to} | {date} | {status}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_view_{rid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📋 Your Transport Requests:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_view_request(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_view_", "")
    rn, rd = _find_trip(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    # Resolve names — fallback if VLOOKUP columns are empty
    mgr_name = rd[TC.MGR_NAME-1].strip() if len(rd) >= TC.MGR_NAME else ""
    if not mgr_name and rd[TC.MGR_CODE-1].strip():
        mgr_name = _get_emp_name(rd[TC.MGR_CODE-1].strip())
    driver_name = rd[TC.DRIVER_NAME-1].strip() if len(rd) >= TC.DRIVER_NAME else ""
    if not driver_name and rd[TC.DRIVER_CODE-1].strip():
        driver_name = _get_emp_name(rd[TC.DRIVER_CODE-1].strip())

    msg = (
        f"🚗 *{rd[TC.REQ_ID-1]}*\n"
        f"{'─'*28}\n"
        f"Type: {rd[TC.TRIP_TYPE-1]}\n"
        f"From: {rd[TC.FROM_LOC-1]}\n"
        f"To:   {rd[TC.TO_LOC-1]}\n"
        f"Date: {rd[TC.DATE-1]}  {rd[TC.DEP_TIME-1]}\n"
        f"Pax:  {rd[TC.PASSENGERS-1]}\n"
        f"Purpose: {rd[TC.PURPOSE-1]}\n\n"
        f"Manager:   {rd[TC.MGR_STATUS-1]}"
    )
    if mgr_name:
        msg += f" ({mgr_name})"
    msg += (
        f"\nDirector:  {rd[TC.DIR_STATUS-1]}\n"
        f"Transport: {rd[TC.TRANS_STATUS-1]}\n"
        f"Status:    {rd[TC.FINAL_STATUS-1]}\n"
    )
    if rd[TC.VEH_PLATE - 1]:
        msg += f"\n🚗 Vehicle: {rd[TC.VEH_PLATE-1]}  Driver: {driver_name}"

    kb = [[_bveh(), _bm()]]
    drive_link = rd[TC.DRIVE_LINK - 1] if len(rd) >= TC.DRIVE_LINK else ""
    if drive_link:
        kb.insert(0, [InlineKeyboardButton("📄 View PDF", url=drive_link)])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  C2. TRANSPORT ARCHIVE — browse all requests by status
# ══════════════════════════════════════════════════════════════════════════════

_ARCHIVE_STATUSES = [
    ("All",         "tr_arch_All"),
    ("Pending",     "tr_arch_Pending"),
    ("Assigned",    "tr_arch_Assigned"),
    ("In Progress", "tr_arch_In Progress"),
    ("Completed",   "tr_arch_Completed"),
    ("Rejected",    "tr_arch_Rejected"),
]


async def tr_archive_menu(update, context):
    q = update.callback_query
    await q.answer()
    kb = [[InlineKeyboardButton(f"{'📋' if s=='All' else '📂'} {s}", callback_data=cb)]
          for s, cb in _ARCHIVE_STATUSES]
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📂 Transport Archive\n\nFilter by status:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_archive_list(update, context):
    q = update.callback_query
    await q.answer()
    status_filter = q.data.replace("tr_arch_", "")
    emp = _get_emp_by_tid(q.from_user.id)
    role = emp["role"] if emp else "Employee"

    try:
        rows = get_sheet("Transport_Requests").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    filtered = []
    for i, r in enumerate(rows):
        if i == 0 or len(r) < TC.FINAL_STATUS:
            continue
        fs = r[TC.FINAL_STATUS - 1].strip()
        # Employees see only their own; managers/Bot_Manager see all
        if role in ("Bot_Manager", "Transport_Manager", "Director", "HR_Manager"):
            pass  # see all
        elif role in ("Direct_Manager", "Supervisor"):
            pass  # see all (team filter can be added later)
        else:
            if emp and r[TC.REQ_CODE - 1].strip() != emp["code"]:
                continue
        if status_filter != "All" and fs != status_filter:
            continue
        filtered.append(r)

    if not filtered:
        await q.edit_message_text(
            f"📂 No requests with status: {status_filter}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Archive", callback_data="tr_archive")],
                [_bveh(), _bm()]]))
        return

    kb = []
    icon = {"Pending": "⏳", "Assigned": "🔄", "In Progress": "🚗",
            "Completed": "✅", "Rejected": "❌"}
    for r in filtered[-25:]:
        rid = r[TC.REQ_ID - 1]
        fs  = r[TC.FINAL_STATUS - 1].strip()
        dt  = r[TC.DATE - 1]
        frm = r[TC.FROM_LOC - 1][:8]
        to  = r[TC.TO_LOC - 1][:8]
        ic  = icon.get(fs, "📋")
        label = f"{ic} {rid} | {frm}→{to} | {dt} | {fs}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_view_{rid}")])

    kb.append([InlineKeyboardButton("↩️ Archive", callback_data="tr_archive")])
    kb.append([_bveh(), _bm()])
    total = len(filtered)
    shown = min(total, 25)
    await q.edit_message_text(
        f"📂 Transport Archive — {status_filter} ({total} total, showing {shown})",
        reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  D. MANAGER APPROVAL (Direct Manager / Director)
# ══════════════════════════════════════════════════════════════════════════════

def _pending_for_role(role, emp_code):
    """Return list of (row_num, row) of trips waiting for this role."""
    rows = get_sheet("Transport_Requests").get_all_values()
    result = []
    for i, r in enumerate(rows):
        if i == 0:
            continue
        if len(r) < TC.FINAL_STATUS:
            continue
        if role == "manager":
            # Manager sees requests from their team where MGR_STATUS=Pending
            if r[TC.MGR_STATUS - 1].strip() == "Pending":
                result.append((i + 1, r))
        elif role == "director":
            if r[TC.DIR_STATUS - 1].strip() == "Pending":
                result.append((i + 1, r))
        elif role == "transport":
            mgr_ok  = r[TC.MGR_STATUS - 1].strip() == "Approved"
            dir_ok  = r[TC.DIR_STATUS  - 1].strip() in ("Approved", "NA")
            tms     = r[TC.TRANS_STATUS - 1].strip() == "Pending"
            if mgr_ok and dir_ok and tms:
                result.append((i + 1, r))
    return result


async def tr_mgr_pending(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    role = emp["role"] if emp else ""

    # Managers and Bot_Manager see pending manager approvals
    pending = _pending_for_role("manager", emp["code"] if emp else "")
    if not pending:
        await q.edit_message_text("✅ No pending trip requests.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    kb = []
    for rn, r in pending[-20:]:
        rid  = r[TC.REQ_ID - 1]
        date = r[TC.DATE - 1]
        frm  = r[TC.FROM_LOC - 1][:10]
        to   = r[TC.TO_LOC - 1][:10]
        tt   = r[TC.TRIP_TYPE - 1]
        label = f"{rid} | {tt} | {frm}→{to} | {date}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_mgr_view_{rid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📋 Pending Trip Requests (Manager Review):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_mgr_view(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_mgr_view_", "")
    rn, rd = _find_trip(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    msg = (
        f"🚗 *{rd[TC.REQ_ID-1]}*\n"
        f"{'─'*28}\n"
        f"👤 {_get_emp_name(rd[TC.REQ_CODE-1])} ({rd[TC.REQ_CODE-1]})\n"
        f"Type: {rd[TC.TRIP_TYPE-1]}\n"
        f"From: {rd[TC.FROM_LOC-1]}\n"
        f"To:   {rd[TC.TO_LOC-1]}\n"
        f"Date: {rd[TC.DATE-1]}  {rd[TC.DEP_TIME-1]}\n"
        f"Pax:  {rd[TC.PASSENGERS-1]}\n"
        f"Purpose: {rd[TC.PURPOSE-1]}"
    )
    drive_link = rd[TC.DRIVE_LINK - 1] if len(rd) >= TC.DRIVE_LINK else ""
    kb = []
    if drive_link:
        kb.append([InlineKeyboardButton("📄 View Current PDF", url=drive_link)])
    kb.append([
        InlineKeyboardButton("✅ Approve", callback_data=f"tr_mgr_approve_{req_id}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"tr_mgr_reject_{req_id}"),
    ])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_mgr_approve(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_mgr_approve_", "")
    emp = _get_emp_by_tid(q.from_user.id)
    rn, rd = _find_trip(req_id)
    if not rn:
        await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    now_str = _now()
    _update_trip(rn, TC.MGR_STATUS, "Approved")
    _update_trip(rn, TC.MGR_DATE,   now_str)
    _update_trip(rn, TC.MGR_CODE,   emp["code"] if emp else "")

    trip_type = rd[TC.TRIP_TYPE - 1] if len(rd) >= TC.TRIP_TYPE else "Near"
    next_role = "Director" if trip_type == "Far" else "Transport Manager"

    if trip_type == "Near":
        _update_trip(rn, TC.DIR_STATUS, "NA")

    # Rule 5.10 — generate stage PDF with electronic signatures
    stage_url = None
    try:
        _, rd_fresh = _find_trip(req_id)
        req_emp = _get_emp_by_code(rd[TC.REQ_CODE - 1])
        if rd_fresh and req_emp:
            pdf_data = _build_pdf_data(rd_fresh, req_emp["name"], req_emp["dept"])
            # Explicitly set manager data (stale-proof)
            pdf_data["manager_status"] = "Approved"
            pdf_data["manager_date"]   = now_str
            pdf_data["manager_name"]   = emp["name"] if emp else ""
            if trip_type == "Near":
                pdf_data["director_status"] = "NA"
            await _enrich_signatures(context.bot, pdf_data, rd_fresh)
            # Also fetch manager signature directly (stale-proof)
            try:
                from signature_handler import get_sig_bytes
                sb, st = await get_sig_bytes(context.bot, emp["code"] if emp else "")
                pdf_data["manager_sig_bytes"] = sb
                pdf_data["manager_sig_text"]  = st
            except Exception:
                pass
            pdf_bytes = generate_transport_request_pdf(pdf_data)
            stage_url = upload_to_drive(pdf_bytes, f"{req_id}_mgr_approved.pdf",
                                        "transport_requests")
            if stage_url:
                _update_trip(rn, TC.DRIVE_LINK, stage_url)
    except Exception as e:
        print(f"[transport] stage PDF error: {e}")

    # Notify requester
    req_ec = rd[TC.REQ_CODE - 1]
    req_tid = _get_tid_by_code(req_ec)
    if req_tid:
        try:
            notif_kb = []
            if stage_url:
                notif_kb.append([InlineKeyboardButton("📄 View Current PDF", url=stage_url)])
            await context.bot.send_message(
                chat_id=req_tid,
                text=f"✅ Your trip request {req_id} approved by Manager.\nWaiting for {next_role}.",
                reply_markup=InlineKeyboardMarkup(notif_kb) if notif_kb else None)
        except Exception:
            pass

    kb = [[_bveh(), _bm()]]
    if stage_url:
        kb.insert(0, [InlineKeyboardButton("📄 View Approved PDF", url=stage_url)])
    await q.edit_message_text(
        f"✅ {req_id} Approved ({now_str})\nForwarded to {next_role}.",
        reply_markup=InlineKeyboardMarkup(kb))


async def tr_mgr_reject_start(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_mgr_reject_", "")
    context.user_data["tr_rej_id"]   = req_id
    context.user_data["tr_rej_role"] = "manager"
    await q.edit_message_text(
        f"❌ Rejecting {req_id}.\n\nType the rejection reason:")
    return TR_REJ


async def tr_rej_reason_inp(update, context):
    reason = update.message.text.strip()
    if len(reason) < 3:
        await update.message.reply_text("⚠️ Too short. Try again:")
        return TR_REJ
    req_id = context.user_data.get("tr_rej_id", "")
    role   = context.user_data.get("tr_rej_role", "manager")
    rn, rd = _find_trip(req_id)
    now_str = _now()
    if rn:
        if role == "manager":
            _update_trip(rn, TC.MGR_STATUS, "Rejected")
            _update_trip(rn, TC.MGR_DATE,   now_str)
        elif role == "director":
            _update_trip(rn, TC.DIR_STATUS, "Rejected")
            _update_trip(rn, TC.DIR_DATE,   now_str)
        _update_trip(rn, TC.NOTES, f"Rejected: {reason}")
        _update_trip(rn, TC.FINAL_STATUS, "Rejected")
        # Notify requester
        req_tid = _get_tid_by_code(rd[TC.REQ_CODE - 1]) if rd else None
        if req_tid:
            try:
                await context.bot.send_message(
                    chat_id=req_tid,
                    text=f"❌ Trip request {req_id} was rejected.\nReason: {reason}")
            except Exception:
                pass
    await update.message.reply_text(
        f"✅ {req_id} rejected.",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return ConversationHandler.END


async def tr_dir_pending(update, context):
    q = update.callback_query
    await q.answer()
    pending = _pending_for_role("director", "")
    if not pending:
        await q.edit_message_text("✅ No far trip requests pending Director approval.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    kb = []
    for rn, r in pending[-20:]:
        rid  = r[TC.REQ_ID - 1]
        date = r[TC.DATE - 1]
        frm  = r[TC.FROM_LOC - 1][:12]
        to   = r[TC.TO_LOC - 1][:12]
        label = f"{rid} | Far | {frm}→{to} | {date}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_dir_view_{rid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📋 Far Trip Requests (Director Approval):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_dir_view(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_dir_view_", "")
    rn, rd = _find_trip(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    msg = (
        f"🏙 *Far Trip — {rd[TC.REQ_ID-1]}*\n"
        f"{'─'*28}\n"
        f"👤 {_get_emp_name(rd[TC.REQ_CODE-1])} ({rd[TC.REQ_CODE-1]})\n"
        f"From: {rd[TC.FROM_LOC-1]}\n"
        f"To:   {rd[TC.TO_LOC-1]}\n"
        f"Date: {rd[TC.DATE-1]}  {rd[TC.DEP_TIME-1]}\n"
        f"Pax:  {rd[TC.PASSENGERS-1]}\n"
        f"Purpose: {rd[TC.PURPOSE-1]}\n"
        f"Manager: {rd[TC.MGR_STATUS-1]} ({rd[TC.MGR_DATE-1]})"
    )
    drive_link = rd[TC.DRIVE_LINK - 1] if len(rd) >= TC.DRIVE_LINK else ""
    kb = []
    if drive_link:
        kb.append([InlineKeyboardButton("📄 View Current PDF", url=drive_link)])
    kb.append([
        InlineKeyboardButton("✅ Approve", callback_data=f"tr_dir_approve_{req_id}"),
        InlineKeyboardButton("❌ Reject",  callback_data=f"tr_dir_reject_{req_id}"),
    ])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_dir_approve(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_dir_approve_", "")
    emp = _get_emp_by_tid(q.from_user.id)
    rn, rd = _find_trip(req_id)
    if not rn:
        await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    now_str = _now()
    _update_trip(rn, TC.DIR_STATUS, "Approved")
    _update_trip(rn, TC.DIR_DATE,   now_str)
    _update_trip(rn, TC.DIR_CODE,   emp["code"] if emp else "")

    # Rule 5.10 — generate stage PDF with all electronic signatures so far
    stage_url = None
    try:
        _, rd_fresh = _find_trip(req_id)
        req_emp = _get_emp_by_code(rd[TC.REQ_CODE - 1])
        if rd_fresh and req_emp:
            pdf_data = _build_pdf_data(rd_fresh, req_emp["name"], req_emp["dept"])
            # Explicitly set director data (stale-proof)
            pdf_data["director_status"] = "Approved"
            pdf_data["director_date"]   = now_str
            pdf_data["director_name"]   = emp["name"] if emp else ""
            await _enrich_signatures(context.bot, pdf_data, rd_fresh)
            # Also fetch director signature directly (stale-proof)
            try:
                from signature_handler import get_sig_bytes
                sb, st = await get_sig_bytes(context.bot, emp["code"] if emp else "")
                pdf_data["director_sig_bytes"] = sb
                pdf_data["director_sig_text"]  = st
            except Exception:
                pass
            pdf_bytes = generate_transport_request_pdf(pdf_data)
            stage_url = upload_to_drive(pdf_bytes, f"{req_id}_dir_approved.pdf",
                                        "transport_requests")
            if stage_url:
                _update_trip(rn, TC.DRIVE_LINK, stage_url)
    except Exception as e:
        print(f"[transport] director PDF error: {e}")

    req_tid = _get_tid_by_code(rd[TC.REQ_CODE - 1]) if rd else None
    if req_tid:
        try:
            notif_kb = []
            if stage_url:
                notif_kb.append([InlineKeyboardButton("📄 View PDF", url=stage_url)])
            await context.bot.send_message(
                chat_id=req_tid,
                text=f"✅ Your trip {req_id} approved by Director.\nWaiting for Transport Manager.",
                reply_markup=InlineKeyboardMarkup(notif_kb) if notif_kb else None)
        except Exception:
            pass

    kb = [[_bveh(), _bm()]]
    if stage_url:
        kb.insert(0, [InlineKeyboardButton("📄 View Approved PDF", url=stage_url)])
    await q.edit_message_text(
        f"✅ {req_id} Approved by Director ({now_str})\nForwarded to Transport Manager.",
        reply_markup=InlineKeyboardMarkup(kb))


async def tr_dir_reject_start(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_dir_reject_", "")
    context.user_data["tr_rej_id"]   = req_id
    context.user_data["tr_rej_role"] = "director"
    await q.edit_message_text(f"❌ Rejecting {req_id}.\n\nType the rejection reason:")
    return TR_REJ


# ══════════════════════════════════════════════════════════════════════════════
#  E. TRANSPORT MANAGER — ASSIGN VEHICLE TO TRIP
# ══════════════════════════════════════════════════════════════════════════════

async def tr_tm_pending(update, context):
    q = update.callback_query
    await q.answer()
    pending = _pending_for_role("transport", "")
    if not pending:
        await q.edit_message_text("✅ No trips pending vehicle assignment.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    kb = []
    for rn, r in pending[-20:]:
        rid  = r[TC.REQ_ID - 1]
        date = r[TC.DATE - 1]
        frm  = r[TC.FROM_LOC - 1][:10]
        to   = r[TC.TO_LOC - 1][:10]
        pax  = r[TC.PASSENGERS - 1]
        tt   = r[TC.TRIP_TYPE - 1]
        label = f"{rid} | {tt} | {frm}→{to} | {date} | {pax}pax"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_tm_view_{rid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("📋 Trips Waiting for Vehicle Assignment:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_tm_view(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_tm_view_", "")
    rn, rd = _find_trip(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    context.user_data["tm_req_id"] = req_id
    context.user_data["tm_rn"]     = rn

    vehs = _get_vehicles(only_available=True)
    msg = (
        f"🚗 Assign Vehicle — *{req_id}*\n"
        f"{'─'*28}\n"
        f"From: {rd[TC.FROM_LOC-1]}\n"
        f"To:   {rd[TC.TO_LOC-1]}\n"
        f"Date: {rd[TC.DATE-1]}  {rd[TC.DEP_TIME-1]}\n"
        f"Pax:  {rd[TC.PASSENGERS-1]}\n\n"
        f"Select a vehicle:"
    )
    drive_link = rd[TC.DRIVE_LINK - 1] if len(rd) >= TC.DRIVE_LINK else ""
    kb = []
    if drive_link:
        kb.append([InlineKeyboardButton("📄 View Request PDF", url=drive_link)])
    for v in vehs[:12]:
        label = f"{v['plate']} | {v['type']} | Cap:{v['capacity']} | {v['driver_name']}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_tm_asgn_{v['plate']}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_tm_assign(update, context):
    q = update.callback_query
    await q.answer()
    plate  = q.data.replace("tr_tm_asgn_", "")
    req_id = context.user_data.get("tm_req_id", "")
    rn     = context.user_data.get("tm_rn")
    emp    = _get_emp_by_tid(q.from_user.id)

    vehs = _get_vehicles(only_available=False)
    veh  = next((v for v in vehs if v["plate"] == plate), None)
    if not veh or not rn:
        await q.edit_message_text("❌ Vehicle not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    now_str = _now()
    _update_trip(rn, TC.TRANS_STATUS, "Assigned")
    _update_trip(rn, TC.TRANS_DATE,   now_str)
    _update_trip(rn, TC.TRANS_CODE,   emp["code"] if emp else "")
    _update_trip(rn, TC.VEH_PLATE,    plate)
    _update_trip(rn, TC.DRIVER_CODE,  veh["driver_code"])
    _update_trip(rn, TC.DRIVER_NAME,  "")   # VLOOKUP
    _update_trip(rn, TC.FINAL_STATUS, "Assigned")

    # Rule 5.10 — final approved PDF with ALL electronic signatures
    final_url = None
    rd_fresh = None
    try:
        _, rd_fresh = _find_trip(req_id)
        req_emp = _get_emp_by_code(rd_fresh[TC.REQ_CODE - 1]) if rd_fresh else None
        if rd_fresh and req_emp:
            pdf_data = _build_pdf_data(rd_fresh, req_emp["name"], req_emp["dept"])
            # Explicitly set transport data (don't rely on stale sheet re-read)
            pdf_data["vehicle_plate"]     = plate
            pdf_data["driver_name"]       = veh["driver_name"]
            pdf_data["final_status"]      = "Assigned"
            pdf_data["transport_status"]  = "Assigned"
            pdf_data["transport_date"]    = now_str
            pdf_data["transport_name"]    = emp["name"] if emp else ""
            # Fetch all signatures (submitter + manager + director)
            await _enrich_signatures(context.bot, pdf_data, rd_fresh)
            # Also fetch transport manager signature directly (stale-proof)
            try:
                from signature_handler import get_sig_bytes
                sb, st = await get_sig_bytes(context.bot, emp["code"] if emp else "")
                pdf_data["transport_sig_bytes"] = sb
                pdf_data["transport_sig_text"]  = st
            except Exception:
                pass
            pdf_bytes = generate_transport_request_pdf(pdf_data)
            from drive_utils import upload_and_archive
            final_url = upload_and_archive(pdf_bytes, f"{req_id}_final.pdf",
                                           "transport_requests",
                                           emp_code=pdf_data.get("emp_code", ""),
                                           emp_name=pdf_data.get("emp_name", ""))
            if final_url:
                _update_trip(rn, TC.DRIVE_LINK, final_url)
    except Exception as e:
        print(f"[transport] final PDF error: {e}")

    # Notify requester
    req_tid = _get_tid_by_code(rd_fresh[TC.REQ_CODE - 1]) if rd_fresh else None
    if req_tid:
        try:
            notif_kb = []
            if final_url:
                notif_kb.append([InlineKeyboardButton("📄 View Final PDF", url=final_url)])
            await context.bot.send_message(
                chat_id=req_tid,
                text=(f"🎉 Trip {req_id} assigned!\n"
                      f"🚗 Vehicle: {plate}\n👤 Driver: {veh['driver_name']}\n"
                      f"📞 {veh['driver_phone']}"),
                reply_markup=InlineKeyboardMarkup(notif_kb) if notif_kb else None)
        except Exception:
            pass

    # Notify driver
    drv_tid = _get_tid_by_code(veh["driver_code"])
    if drv_tid and rd_fresh:
        try:
            await context.bot.send_message(
                chat_id=drv_tid,
                text=(f"🚗 New trip assigned: {req_id}\n"
                      f"📅 {rd_fresh[TC.DATE-1]}  {rd_fresh[TC.DEP_TIME-1]}\n"
                      f"From: {rd_fresh[TC.FROM_LOC-1]}\n"
                      f"To:   {rd_fresh[TC.TO_LOC-1]}\n"
                      f"Pax:  {rd_fresh[TC.PASSENGERS-1]}"))
        except Exception:
            pass

    kb = [[_bveh(), _bm()]]
    if final_url:
        kb.insert(0, [InlineKeyboardButton("📄 View Final PDF", url=final_url)])
    await q.edit_message_text(
        f"✅ {req_id} assigned to {plate} ({veh['driver_name']}).",
        reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  F. TRANSPORT MANAGER — COMMUTE VEHICLE ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════════════

async def tr_tm_commute_list(update, context):
    q = update.callback_query
    await q.answer()
    rows = get_sheet("Commute_Log").get_all_values()
    pending = [(i + 1, r) for i, r in enumerate(rows)
               if i > 0 and r[CC.STATUS - 1].strip() == "Pending"]
    if not pending:
        await q.edit_message_text("✅ No pending commute requests.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    kb = []
    for rn, r in pending[-15:]:
        cid   = r[CC.COM_ID - 1]
        date  = r[CC.DATE - 1]
        dep   = r[CC.DEP_TIME - 1]
        frm   = r[CC.FROM_LOC - 1][:10]
        to    = r[CC.TO_LOC - 1][:10]
        count = r[CC.EMP_COUNT - 1]
        label = f"{cid} | {frm}→{to} | {date} {dep} | {count}pax"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_tm_com_{cid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("🚌 Pending Commute Requests:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_tm_commute_view(update, context):
    q = update.callback_query
    await q.answer()
    com_id = q.data.replace("tr_tm_com_", "")
    rn, rd = _find_commute(com_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    codes = [c.strip() for c in rd[CC.EMP_CODES - 1].split(",") if c.strip()]
    emp_list = [(_get_emp_by_code(c) or {"code": c, "name": c, "dept": ""}) for c in codes]

    # Initialize assignment state
    context.user_data["tmc_com_id"]    = com_id
    context.user_data["tmc_rn"]        = rn
    context.user_data["tmc_unassigned"] = emp_list[:]
    context.user_data["tmc_assignments"] = []
    context.user_data["tmc_cur_veh"]   = None
    context.user_data["tmc_cur_pax"]   = []

    lines = "\n".join(f"  {i+1}. {e['name']} ({e['code']})" for i, e in enumerate(emp_list))
    msg = (
        f"🚌 *{com_id}*\n"
        f"{'─'*28}\n"
        f"📅 {rd[CC.DATE-1]}  ⏰ {rd[CC.DEP_TIME-1]}\n"
        f"📍 {rd[CC.FROM_LOC-1]} → {rd[CC.TO_LOC-1]}\n"
        f"👥 {len(emp_list)} employees:\n{lines}\n\n"
        f"Select a vehicle to start assignment:"
    )
    vehs = _get_vehicles(only_available=True)
    kb = []
    for v in vehs[:10]:
        label = f"{v['plate']} | {v['type']} | Cap:{v['capacity']} | {v['driver_name']}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tmc_veh_{v['plate']}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tmc_sel_vehicle(update, context):
    q = update.callback_query
    await q.answer()
    plate = q.data.replace("tmc_veh_", "")
    vehs  = _get_vehicles(only_available=False)
    veh   = next((v for v in vehs if v["plate"] == plate), None)
    if not veh:
        await q.answer("Vehicle not found.", show_alert=True)
        return

    context.user_data["tmc_cur_veh"] = veh
    context.user_data["tmc_cur_pax"] = []
    await _show_emp_assignment(q, context)


async def _show_emp_assignment(q, context):
    veh   = context.user_data.get("tmc_cur_veh", {})
    pax   = context.user_data.get("tmc_cur_pax", [])
    unasgn = context.user_data.get("tmc_unassigned", [])
    cap   = veh.get("capacity", 0)

    msg = (
        f"🚗 *{veh.get('plate')}* — {veh.get('type')} (Cap: {cap})\n"
        f"Driver: {veh.get('driver_name')}\n"
        f"{'─'*28}\n"
        f"Assigned ({len(pax)}/{cap}):\n"
    )
    if pax:
        msg += "\n".join(f"  ✅ {e['name']} ({e['code']})" for e in pax) + "\n"

    if len(pax) >= cap:
        msg += f"\n🚫 Vehicle full ({cap}/{cap}). Tap *Done with this vehicle* to assign another."
        kb = [
            [InlineKeyboardButton("✅ Done with this vehicle", callback_data="tmc_done_veh")],
            [_bveh(), _bm()],
        ]
    else:
        msg += f"\nSelect employees to add ({cap - len(pax)} remaining):\n"
        kb = []
        for e in unasgn[:10]:
            kb.append([InlineKeyboardButton(
                f"➕ {e['name']} ({e['code']})",
                callback_data=f"tmc_add_{e['code']}")])
        kb.append([InlineKeyboardButton("✅ Done with this vehicle", callback_data="tmc_done_veh")])
        kb.append([_bveh(), _bm()])

    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tmc_add_emp(update, context):
    q = update.callback_query
    await q.answer()
    code   = q.data.replace("tmc_add_", "")
    veh    = context.user_data.get("tmc_cur_veh", {})
    pax    = context.user_data.get("tmc_cur_pax", [])
    unasgn = context.user_data.get("tmc_unassigned", [])

    if len(pax) >= veh.get("capacity", 0):
        await q.answer("Vehicle is full!", show_alert=True)
        return

    emp = next((e for e in unasgn if e["code"] == code), None)
    if not emp:
        await q.answer("Already assigned.", show_alert=True)
        return

    pax.append(emp)
    unasgn.remove(emp)
    context.user_data["tmc_cur_pax"]    = pax
    context.user_data["tmc_unassigned"] = unasgn
    await _show_emp_assignment(q, context)


async def tmc_done_vehicle(update, context):
    q = update.callback_query
    await q.answer()
    veh  = context.user_data.get("tmc_cur_veh", {})
    pax  = context.user_data.get("tmc_cur_pax", [])
    asgn = context.user_data.get("tmc_assignments", [])
    unasgn = context.user_data.get("tmc_unassigned", [])

    if pax:
        asgn.append({
            "plate":       veh.get("plate", ""),
            "type":        veh.get("type", ""),
            "driver_code": veh.get("driver_code", ""),
            "driver_name": veh.get("driver_name", ""),
            "capacity":    veh.get("capacity", 0),
            "passengers":  pax,
        })
        context.user_data["tmc_assignments"] = asgn

    context.user_data["tmc_cur_veh"] = None
    context.user_data["tmc_cur_pax"] = []

    if not unasgn:
        # All assigned — show summary
        await tmc_show_summary(q, context)
        return

    # More employees to assign
    vehs = _get_vehicles(only_available=True)
    already_used = {a["plate"] for a in asgn}
    vehs = [v for v in vehs if v["plate"] not in already_used]

    msg = (
        f"✅ Vehicle saved. {len(unasgn)} employee(s) still unassigned.\n\n"
        f"Select another vehicle:"
    )
    kb = []
    for v in vehs[:10]:
        label = f"{v['plate']} | {v['type']} | Cap:{v['capacity']} | {v['driver_name']}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tmc_veh_{v['plate']}")])
    kb.append([InlineKeyboardButton("📋 Show Summary (assign remaining later)",
                                    callback_data="tmc_summary")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def tmc_show_summary(q, context):
    asgn   = context.user_data.get("tmc_assignments", [])
    unasgn = context.user_data.get("tmc_unassigned", [])
    com_id = context.user_data.get("tmc_com_id", "")

    msg = f"📋 *Commute Assignment Summary — {com_id}*\n{'─'*28}\n\n"
    for a in asgn:
        msg += f"🚗 *{a['plate']}* — {a['type']} | Driver: {a['driver_name']}\n"
        for e in a["passengers"]:
            msg += f"  • {e['name']} ({e['code']})\n"
        msg += "\n"
    if unasgn:
        msg += f"⚠️ Unassigned ({len(unasgn)}):\n"
        for e in unasgn:
            msg += f"  • {e['name']} ({e['code']})\n"

    kb = [
        [InlineKeyboardButton("✅ Confirm & Generate PDF", callback_data="tmc_confirm")],
        [_bveh(), _bm()],
    ]
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tmc_confirm(update, context):
    q = update.callback_query
    await q.answer()
    com_id = context.user_data.get("tmc_com_id", "")
    rn     = context.user_data.get("tmc_rn")
    asgn   = context.user_data.get("tmc_assignments", [])

    rn2, rd = _find_commute(com_id)
    rn = rn2 or rn
    now_str = _now()

    # Save assignments JSON
    asgn_json = json.dumps([{
        "plate":       a["plate"],
        "driver_code": a["driver_code"],
        "driver_name": a["driver_name"],
        "passengers":  [{"code": e["code"], "name": e["name"], "dept": e["dept"]}
                        for e in a["passengers"]],
    } for a in asgn])
    if rn:
        _update_commute(rn, CC.STATUS,      "Assigned")
        _update_commute(rn, CC.ASSIGNMENTS, asgn_json)

    # Generate commute PDF
    pdf_url = None
    try:
        req_emp = _get_emp_by_code(rd[CC.REQ_CODE - 1]) if rd else None
        pdf_data = {
            "commute_id":     com_id,
            "submitted_at":   rd[CC.SUBMITTED - 1] if rd else now_str,
            "requester_name": req_emp["name"] if req_emp else "",
            "date":           rd[CC.DATE - 1] if rd else "",
            "departure_time": rd[CC.DEP_TIME - 1] if rd else "",
            "from_location":  rd[CC.FROM_LOC - 1] if rd else "",
            "to_location":    rd[CC.TO_LOC - 1] if rd else "",
            "employee_count": rd[CC.EMP_COUNT - 1] if rd else "",
        }
        vehicle_groups = [{
            "plate":       a["plate"],
            "type":        a["type"],
            "driver_name": a["driver_name"],
            "capacity":    a["capacity"],
            "passengers":  [{"code": e["code"], "name": e["name"], "dept": e["dept"]}
                            for e in a["passengers"]],
        } for a in asgn]
        pdf_bytes = generate_commute_pdf(pdf_data, vehicle_groups)
        pdf_url = upload_to_drive(pdf_bytes, f"{com_id}_assignment.pdf", "transport_requests")
        if pdf_url and rn:
            _update_commute(rn, CC.DRIVE_LINK, pdf_url)
    except Exception as e:
        print(f"[transport] commute PDF error: {e}")

    # Notify each employee
    for a in asgn:
        for e in a["passengers"]:
            etid = _get_tid_by_code(e["code"])
            if etid:
                try:
                    notif_kb = []
                    if pdf_url:
                        notif_kb.append([InlineKeyboardButton("📄 View Assignment PDF",
                                                              url=pdf_url)])
                    d = rd if rd else {}
                    await context.bot.send_message(
                        chat_id=etid,
                        text=(f"🚌 Your commute trip for {d[CC.DATE-1] if d else 'TBD'}:\n"
                              f"🚗 Vehicle: {a['plate']} ({a['type']})\n"
                              f"👤 Driver: {a['driver_name']}\n"
                              f"📍 {d[CC.FROM_LOC-1] if d else ''} → {d[CC.TO_LOC-1] if d else ''}\n"
                              f"⏰ {d[CC.DEP_TIME-1] if d else ''}"),
                        reply_markup=InlineKeyboardMarkup(notif_kb) if notif_kb else None)
                except Exception:
                    pass

    kb = [[_bveh(), _bm()]]
    if pdf_url:
        kb.insert(0, [InlineKeyboardButton("📄 View Assignment PDF", url=pdf_url)])
    await q.edit_message_text(
        f"✅ Commute {com_id} assignment confirmed!\n{len(asgn)} vehicle(s) assigned.",
        reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  G. DRIVER — MY TRIPS + START / STOP / END
# ══════════════════════════════════════════════════════════════════════════════

async def tr_driver_trips(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("❌ Not registered.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    rows = get_sheet("Transport_Requests").get_all_values()
    my_trips = [
        (i + 1, r) for i, r in enumerate(rows)
        if i > 0 and r[TC.DRIVER_CODE - 1].strip() == emp["code"]
        and r[TC.FINAL_STATUS - 1].strip() in ("Assigned", "In Progress")
    ]

    if not my_trips:
        await q.edit_message_text("📋 No assigned trips.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    kb = []
    for rn, r in my_trips[-10:]:
        rid    = r[TC.REQ_ID - 1]
        date   = r[TC.DATE - 1]
        frm    = r[TC.FROM_LOC - 1][:10]
        to     = r[TC.TO_LOC - 1][:10]
        status = r[TC.FINAL_STATUS - 1]
        label  = f"{rid} | {frm}→{to} | {date} | {status}"
        kb.append([InlineKeyboardButton(label, callback_data=f"tr_drv_view_{rid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("🗺 My Assigned Trips:", reply_markup=InlineKeyboardMarkup(kb))


async def tr_drv_view(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_drv_view_", "")
    rn, rd = _find_trip(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    context.user_data["drv_req_id"] = req_id
    context.user_data["drv_rn"]     = rn
    status = rd[TC.FINAL_STATUS - 1]
    msg = (
        f"🚗 *{req_id}*\n"
        f"{'─'*28}\n"
        f"From: {rd[TC.FROM_LOC-1]}\n"
        f"To:   {rd[TC.TO_LOC-1]}\n"
        f"Date: {rd[TC.DATE-1]}  {rd[TC.DEP_TIME-1]}\n"
        f"Pax:  {rd[TC.PASSENGERS-1]}\n"
        f"Status: {status}"
    )
    kb = []
    drive_link = rd[TC.DRIVE_LINK - 1] if len(rd) >= TC.DRIVE_LINK else ""
    if drive_link:
        kb.append([InlineKeyboardButton("📄 View Trip PDF", url=drive_link)])
    if status == "Assigned":
        kb.append([InlineKeyboardButton("🚀 Start Trip",   callback_data=f"tr_drv_start_{req_id}")])
    elif status == "In Progress":
        kb.append([InlineKeyboardButton("⏸ Report Stop",  callback_data=f"tr_drv_stop_{req_id}")])
        kb.append([InlineKeyboardButton("🏁 End Trip",     callback_data=f"tr_drv_end_{req_id}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))


async def tr_drv_start(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_drv_start_", "")
    context.user_data["drv_req_id"] = req_id
    await q.edit_message_text(
        "🚀 Starting trip.\n\nEnter *odometer reading* (km):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return DRV_START_ODO


async def drv_start_odo(update, context):
    raw = update.message.text.strip()
    if not raw.replace(".", "").isdigit():
        await update.message.reply_text("⚠️ Enter a number:",
                                        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return DRV_START_ODO
    context.user_data["drv_odo_start"] = raw
    await update.message.reply_text(
        "⛽ Enter *fuel level* at start (e.g. 75%):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return DRV_START_FUEL


async def drv_start_fuel(update, context):
    fuel = update.message.text.strip()
    req_id = context.user_data.get("drv_req_id", "")
    rn, _  = _find_trip(req_id)
    if rn:
        _update_trip(rn, TC.ODO_START,   context.user_data.get("drv_odo_start", ""))
        _update_trip(rn, TC.FUEL_START,  fuel)
        _update_trip(rn, TC.ACT_DEPART,  _now())
        _update_trip(rn, TC.FINAL_STATUS, "In Progress")
    await update.message.reply_text(
        f"🚀 Trip *{req_id}* started!\n"
        f"Odometer: {context.user_data.get('drv_odo_start')} km\n"
        f"Fuel: {fuel}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return ConversationHandler.END


async def tr_drv_stop(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_drv_stop_", "")
    context.user_data["drv_req_id"] = req_id
    await q.edit_message_text(
        "⏸ Report a stop.\n\nType the reason (e.g. 'traffic', 'fuel stop', 'passenger pickup'):")
    return DRV_STOP_RSN


async def drv_stop_reason(update, context):
    reason = update.message.text.strip()
    req_id = context.user_data.get("drv_req_id", "")
    rn, rd = _find_trip(req_id)
    if rn:
        existing = rd[TC.DELAY_REASON - 1] if rd and len(rd) >= TC.DELAY_REASON else ""
        note = f"{existing}; STOP {_now()}: {reason}" if existing else f"STOP {_now()}: {reason}"
        _update_trip(rn, TC.DELAY_REASON, note)
    await update.message.reply_text(
        f"⏸ Stop recorded for {req_id}.\nReason: {reason}",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return ConversationHandler.END


async def tr_drv_end(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("tr_drv_end_", "")
    context.user_data["drv_req_id"] = req_id
    await q.edit_message_text(
        "🏁 Ending trip.\n\nEnter *final odometer reading* (km):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return DRV_END_ODO


async def drv_end_odo(update, context):
    raw = update.message.text.strip()
    if not raw.replace(".", "").isdigit():
        await update.message.reply_text("⚠️ Enter a number:",
                                        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return DRV_END_ODO
    context.user_data["drv_odo_end"] = raw
    await update.message.reply_text(
        "⛽ Enter *fuel level* at end:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return DRV_END_FUEL


async def drv_end_fuel(update, context):
    fuel = update.message.text.strip()
    context.user_data["drv_fuel_end"] = fuel
    await update.message.reply_text(
        "Any delay reason? (or send *none*):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return DRV_END_FUEL + 1   # DRV_DELAY = DRV_END_FUEL + 1 = 2034


async def drv_end_delay(update, context):
    reason = update.message.text.strip()
    if reason.lower() == "none":
        reason = ""
    req_id = context.user_data.get("drv_req_id", "")
    rn, _  = _find_trip(req_id)
    if rn:
        _update_trip(rn, TC.ODO_END,      context.user_data.get("drv_odo_end", ""))
        _update_trip(rn, TC.FUEL_END,     context.user_data.get("drv_fuel_end", ""))
        _update_trip(rn, TC.ACT_RETURN,   _now())
        _update_trip(rn, TC.FINAL_STATUS, "Completed")
        if reason:
            _update_trip(rn, TC.DELAY_REASON, reason)
    await update.message.reply_text(
        f"🏁 Trip *{req_id}* completed!\n"
        f"Return odometer: {context.user_data.get('drv_odo_end')} km\n"
        f"Fuel end: {context.user_data.get('drv_fuel_end')}\n"
        f"{'Reason: ' + reason if reason else ''}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER — build pdf_data dict from a Transport_Requests row
# ══════════════════════════════════════════════════════════════════════════════

def _build_pdf_data(rd, req_name="", req_dept=""):
    def _g(col): return rd[col - 1] if len(rd) >= col else ""
    # Read approver names from VLOOKUP columns, fallback to code lookup
    mgr_code = _g(TC.MGR_CODE).strip()
    dir_code = _g(TC.DIR_CODE).strip()
    trans_code = _g(TC.TRANS_CODE).strip()
    mgr_name = _g(TC.MGR_NAME).strip() or (_get_emp_name(mgr_code) if mgr_code else "")
    dir_name = _g(TC.DIR_NAME).strip() or (_get_emp_name(dir_code) if dir_code else "")
    trans_name = _get_emp_name(trans_code) if trans_code else ""
    return {
        "request_id":       _g(TC.REQ_ID),
        "submitted_at":     _g(TC.SUBMITTED),
        "requester_code":   _g(TC.REQ_CODE),
        "requester_name":   req_name or _g(TC.REQ_CODE),
        "requester_dept":   req_dept,
        "trip_type":        _g(TC.TRIP_TYPE),
        "from_location":    _g(TC.FROM_LOC),
        "to_location":      _g(TC.TO_LOC),
        "purpose":          _g(TC.PURPOSE),
        "date":             _g(TC.DATE),
        "departure_time":   _g(TC.DEP_TIME),
        "passengers":       _g(TC.PASSENGERS),
        "notes":            _g(TC.NOTES),
        "manager_status":   _g(TC.MGR_STATUS),
        "manager_date":     _g(TC.MGR_DATE),
        "manager_name":     mgr_name,
        "manager_sig_bytes": None,
        "manager_sig_text":  None,
        "director_status":  _g(TC.DIR_STATUS),
        "director_date":    _g(TC.DIR_DATE),
        "director_name":    dir_name,
        "director_sig_bytes": None,
        "director_sig_text":  None,
        "transport_status": _g(TC.TRANS_STATUS),
        "transport_date":   _g(TC.TRANS_DATE),
        "transport_name":   trans_name,
        "transport_sig_bytes": None,
        "transport_sig_text":  None,
        "vehicle_plate":    _g(TC.VEH_PLATE),
        "driver_name":      _g(TC.DRIVER_NAME),
        "final_status":     _g(TC.FINAL_STATUS),
    }


async def _enrich_signatures(bot, pdf_data, rd):
    """Fetch electronic signatures for ALL stages (progressive Rule 5.10).
    Includes submitter + all approved approvers."""
    from signature_handler import get_sig_bytes

    def _g(col): return rd[col - 1].strip() if len(rd) >= col else ""

    # Submitter (requester) signature — always present
    req_code = _g(TC.REQ_CODE)
    if req_code and not pdf_data.get("submitter_sig_bytes"):
        try:
            sb, st = await get_sig_bytes(bot, req_code)
            pdf_data["submitter_sig_bytes"] = sb
            pdf_data["submitter_sig_text"] = st
        except Exception:
            pass

    # Manager signature
    mgr_code = _g(TC.MGR_CODE)
    if mgr_code and _g(TC.MGR_STATUS) == "Approved":
        if not pdf_data.get("manager_name"):
            pdf_data["manager_name"] = _get_emp_name(mgr_code)
        try:
            sb, st = await get_sig_bytes(bot, mgr_code)
            pdf_data["manager_sig_bytes"] = sb
            pdf_data["manager_sig_text"] = st
        except Exception:
            pass

    # Director signature
    dir_code = _g(TC.DIR_CODE)
    if dir_code and _g(TC.DIR_STATUS) == "Approved":
        if not pdf_data.get("director_name"):
            pdf_data["director_name"] = _get_emp_name(dir_code)
        try:
            sb, st = await get_sig_bytes(bot, dir_code)
            pdf_data["director_sig_bytes"] = sb
            pdf_data["director_sig_text"] = st
        except Exception:
            pass

    # Transport Manager signature
    trans_code = _g(TC.TRANS_CODE)
    if trans_code and _g(TC.TRANS_STATUS) in ("Assigned",):
        if not pdf_data.get("transport_name"):
            pdf_data["transport_name"] = _get_emp_name(trans_code)
        try:
            sb, st = await get_sig_bytes(bot, trans_code)
            pdf_data["transport_sig_bytes"] = sb
            pdf_data["transport_sig_text"] = st
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  H. FLEET DASHBOARD (Transport_Manager + Bot_Manager)
# ══════════════════════════════════════════════════════════════════════════════

async def fleet_dashboard_handler(update, context):
    """Show all active trips grouped by status."""
    q = update.callback_query
    await q.answer()
    try:
        rows = get_sheet("Transport_Requests").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    active = []
    for i, r in enumerate(rows):
        if i == 0 or len(r) < TC.FINAL_STATUS:
            continue
        if r[TC.FINAL_STATUS - 1].strip() == "In Progress":
            active.append(r)

    if not active:
        vehs = _get_vehicles(only_available=True)
        await q.edit_message_text(
            f"📊 Fleet Dashboard\n{'─' * 28}\n"
            f"No active trips right now.\n"
            f"Available vehicles: {len(vehs)}",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    now = datetime.now()
    on_time = []
    overdue = []
    no_loc = []

    for r in active:
        rid = r[TC.REQ_ID - 1]
        plate = r[TC.VEH_PLATE - 1] if len(r) >= TC.VEH_PLATE else ""
        driver = r[TC.DRIVER_NAME - 1] if len(r) >= TC.DRIVER_NAME else ""
        if not driver and len(r) >= TC.DRIVER_CODE and r[TC.DRIVER_CODE - 1].strip():
            driver = _get_emp_name(r[TC.DRIVER_CODE - 1].strip())
        dest = r[TC.TO_LOC - 1] if len(r) >= TC.TO_LOC else ""
        dep_str = r[TC.ACT_DEPART - 1] if len(r) >= TC.ACT_DEPART else ""
        loc_shared = r[TC.LOC_SHARED - 1].strip() if len(r) >= TC.LOC_SHARED else ""
        maps = r[TC.MAPS_LINK - 1].strip() if len(r) >= TC.MAPS_LINK else ""
        loc_time = r[TC.LAST_LOC_TIME - 1].strip() if len(r) >= TC.LAST_LOC_TIME else ""

        # Calculate duration
        dur_str = ""
        is_overdue = False
        if dep_str:
            try:
                dep_dt = datetime.strptime(dep_str.strip(), "%d/%m/%Y %H:%M")
                mins = int((now - dep_dt).total_seconds() / 60)
                dur_str = f"{mins // 60}h{mins % 60:02d}m"
                # Check if overdue (assume 4 hours max for now)
                if mins > 240:
                    is_overdue = True
            except Exception:
                pass

        entry = {"rid": rid, "plate": plate, "driver": driver, "dest": dest,
                 "dur": dur_str, "maps": maps, "loc_time": loc_time, "overdue": is_overdue}

        if is_overdue:
            overdue.append(entry)
        elif loc_shared != "Yes":
            no_loc.append(entry)
        else:
            on_time.append(entry)

    lines = [f"📊 Fleet Dashboard ({len(active)} active)\n{'─' * 28}"]

    if overdue:
        lines.append(f"\n🔴 OVERDUE ({len(overdue)}):")
        for e in overdue:
            lines.append(f"  {e['rid']} | {e['plate']} | {e['driver']}")
            lines.append(f"  → {e['dest']} | {e['dur']} OVERDUE")

    if on_time:
        lines.append(f"\n🟢 On Track ({len(on_time)}):")
        for e in on_time:
            lines.append(f"  {e['rid']} | {e['plate']} | {e['driver']}")
            lines.append(f"  → {e['dest']} | {e['dur']}")

    if no_loc:
        lines.append(f"\n🟡 No Location ({len(no_loc)}):")
        for e in no_loc:
            lines.append(f"  {e['rid']} | {e['plate']} | {e['driver']}")
            lines.append(f"  → {e['dest']} | {e['dur']}")

    vehs = _get_vehicles(only_available=True)
    lines.append(f"\n{'─' * 28}\nAvailable vehicles: {len(vehs)}")

    kb = []
    # Add maps links for trips with location
    for e in (on_time + overdue):
        if e.get("maps"):
            kb.append([InlineKeyboardButton(
                f"📍 {e['rid']} — {e['driver']}", url=e["maps"])])
    kb.append([InlineKeyboardButton("🔄 Refresh", callback_data="tr_fleet_dash")])
    kb.append([_bveh(), _bm()])

    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  I. LIVE LOCATION HANDLER
# ══════════════════════════════════════════════════════════════════════════════

async def handle_location_update(update, context):
    """Handle live location shares from drivers. Registered with group=1."""
    msg = update.edited_message or update.message
    if not msg or not msg.location:
        return

    lat = msg.location.latitude
    lng = msg.location.longitude
    tid = str(msg.from_user.id)

    # Find driver's emp_code
    emp = _get_emp_by_tid(tid)
    if not emp:
        return  # Not registered — ignore

    ec = emp["code"]

    # Find active trip for this driver
    try:
        rows = get_sheet("Transport_Requests").get_all_values()
    except Exception:
        return

    for i, r in enumerate(rows):
        if i == 0 or len(r) < TC.FINAL_STATUS:
            continue
        if (r[TC.DRIVER_CODE - 1].strip() == ec
                and r[TC.FINAL_STATUS - 1].strip() == "In Progress"):
            rn = i + 1
            now_str = _now()
            maps_url = f"https://maps.google.com/?q={lat},{lng}"

            _update_trip(rn, TC.LAST_LAT, str(lat))
            _update_trip(rn, TC.LAST_LONG, str(lng))
            _update_trip(rn, TC.LAST_LOC_TIME, now_str)
            _update_trip(rn, TC.MAPS_LINK, maps_url)

            # Only reply on FIRST location share (LOC_SHARED not yet "Yes")
            loc_shared = r[TC.LOC_SHARED - 1].strip() if len(r) >= TC.LOC_SHARED else ""
            if loc_shared != "Yes":
                _update_trip(rn, TC.LOC_SHARED, "Yes")
                try:
                    await msg.reply_text("✅ Location received. Drive safe!")
                except Exception:
                    pass
            return  # Found the trip — done


# ══════════════════════════════════════════════════════════════════════════════
#  J. OVERDUE TRIP CHECKER (JobQueue callback)
# ══════════════════════════════════════════════════════════════════════════════

async def check_overdue_trips(context):
    """Called every 5 minutes by JobQueue. Checks for overdue/no-location trips."""
    try:
        rows = get_sheet("Transport_Requests").get_all_values()
    except Exception:
        return

    now = datetime.now()
    bot = context.bot

    for i, r in enumerate(rows):
        if i == 0 or len(r) < TC.FINAL_STATUS:
            continue
        if r[TC.FINAL_STATUS - 1].strip() != "In Progress":
            continue

        rn = i + 1
        dep_str = r[TC.ACT_DEPART - 1].strip() if len(r) >= TC.ACT_DEPART else ""
        loc_shared = r[TC.LOC_SHARED - 1].strip() if len(r) >= TC.LOC_SHARED else ""
        last_alert = r[TC.LAST_ALERT - 1].strip() if len(r) >= TC.LAST_ALERT else "none"
        driver_code = r[TC.DRIVER_CODE - 1].strip() if len(r) >= TC.DRIVER_CODE else ""
        rid = r[TC.REQ_ID - 1].strip()

        if not dep_str:
            continue

        try:
            dep_dt = datetime.strptime(dep_str, "%d/%m/%Y %H:%M")
        except Exception:
            continue

        mins_since_depart = int((now - dep_dt).total_seconds() / 60)

        # No location shared — reminders
        if loc_shared != "Yes":
            if mins_since_depart >= 5 and last_alert in ("none", ""):
                drv_tid = _get_tid_by_code(driver_code)
                if drv_tid:
                    try:
                        await bot.send_message(
                            chat_id=drv_tid,
                            text=f"📍 Please share your live location for trip {rid}.\n"
                                 f"Tap 📎 → Location → Share Live Location → 8 hours")
                    except Exception:
                        pass
                _update_trip(rn, TC.LAST_ALERT, "5min_reminder")

            elif mins_since_depart >= 15 and last_alert == "5min_reminder":
                # Alert Transport Manager
                for ec_tm, tid_tm in _users_by_role("Transport_Manager"):
                    try:
                        await bot.send_message(
                            chat_id=tid_tm,
                            text=f"⚠️ Trip {rid}: Driver {driver_code} has not shared location "
                                 f"({mins_since_depart} min since departure)")
                    except Exception:
                        pass
                _update_trip(rn, TC.LAST_ALERT, "15min_alert")

        # Overdue checks (assume 4 hours = 240 min as default max)
        if mins_since_depart > 255 and last_alert not in ("overdue_15", "overdue_30", "overdue_60"):
            # 15 min overdue — ping driver
            drv_tid = _get_tid_by_code(driver_code)
            if drv_tid:
                try:
                    await bot.send_message(
                        chat_id=drv_tid,
                        text=f"⏰ Trip {rid}: Are you delayed? "
                             f"Trip started {mins_since_depart} min ago.")
                except Exception:
                    pass
            _update_trip(rn, TC.LAST_ALERT, "overdue_15")

        elif mins_since_depart > 270 and last_alert == "overdue_15":
            # 30 min overdue — alert Transport Manager
            for ec_tm, tid_tm in _users_by_role("Transport_Manager"):
                try:
                    await bot.send_message(
                        chat_id=tid_tm,
                        text=f"🔴 OVERDUE: Trip {rid} — {mins_since_depart} min since departure. "
                             f"Driver: {driver_code}")
                except Exception:
                    pass
            _update_trip(rn, TC.LAST_ALERT, "overdue_30")

        elif mins_since_depart > 300 and last_alert == "overdue_30":
            # 60 min overdue — alert Director
            for ec_d, tid_d in _users_by_role("Director"):
                try:
                    await bot.send_message(
                        chat_id=tid_d,
                        text=f"🚨 CRITICAL: Trip {rid} — {mins_since_depart} min since departure. "
                             f"Driver: {driver_code}. Transport Manager alerted at 30min.")
                except Exception:
                    pass
            _update_trip(rn, TC.LAST_ALERT, "overdue_60")


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_transport_handlers():
    """Return list of all handlers. Add to bot.py Phase 29."""

    # Trip Request ConversationHandler
    trip_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tr_request_start, pattern="^tr_request_start$")],
        states={
            TR_TYPE:    [CallbackQueryHandler(tr_type_cb,    pattern="^tr_type_")],
            TR_FROM:    [CallbackQueryHandler(tr_from_cb,    pattern="^tr_from_")],
            TR_TO:      [CallbackQueryHandler(tr_to_cb,      pattern="^tr_to_")],
            TR_TIMING:  [CallbackQueryHandler(tr_timing_cb,  pattern="^tr_timing_")],
            TR_TIME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_time_inp)],
            TR_PASS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_pass_inp)],
            TR_PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_purpose_inp)],
            TR_CONFIRM: [CallbackQueryHandler(tr_confirm,    pattern="^tr_confirm_")],
        },
        fallbacks=[
            CallbackQueryHandler(tr_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(tr_cancel, pattern="^menu_transport$"),
        ],
        allow_reentry=True,
    )

    # Commute Request ConversationHandler
    commute_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tr_commute_start, pattern="^tr_commute_start$")],
        states={
            COM_DATE:    [CallbackQueryHandler(com_date_cb, pattern="^com_date_")],
            COM_TIME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, com_time_inp)],
            COM_FROM:    [CallbackQueryHandler(com_from_cb, pattern="^com_from_")],
            COM_TO:      [CallbackQueryHandler(com_to_cb,   pattern="^com_to_")],
            COM_EMPS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, com_emps_inp)],
            COM_CONFIRM: [CallbackQueryHandler(com_confirm, pattern="^com_confirm_")],
        },
        fallbacks=[
            CallbackQueryHandler(tr_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(tr_cancel, pattern="^menu_transport$"),
        ],
        allow_reentry=True,
    )

    # Rejection reason ConversationHandler (manager + director)
    reject_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tr_mgr_reject_start, pattern="^tr_mgr_reject_"),
            CallbackQueryHandler(tr_dir_reject_start, pattern="^tr_dir_reject_"),
        ],
        states={
            TR_REJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, tr_rej_reason_inp)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    # Driver start trip ConversationHandler
    drv_start_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tr_drv_start, pattern="^tr_drv_start_")],
        states={
            DRV_START_ODO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_start_odo)],
            DRV_START_FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_start_fuel)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    # Driver stop ConversationHandler
    drv_stop_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tr_drv_stop, pattern="^tr_drv_stop_")],
        states={
            DRV_STOP_RSN: [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_stop_reason)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    # Driver end trip ConversationHandler (DRV_END_FUEL + 1 = 2034)
    drv_end_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tr_drv_end, pattern="^tr_drv_end_")],
        states={
            DRV_END_ODO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_end_odo)],
            DRV_END_FUEL:     [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_end_fuel)],
            DRV_END_FUEL + 1: [MessageHandler(filters.TEXT & ~filters.COMMAND, drv_end_delay)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    return [
        trip_conv, commute_conv, reject_conv,
        drv_start_conv, drv_stop_conv, drv_end_conv,
    ]


def get_transport_static_handlers():
    """Return list of static CallbackQueryHandlers."""
    from telegram.ext import CallbackQueryHandler as CQH
    return [
        CQH(transport_menu_handler,  pattern="^menu_transport$"),
        CQH(tr_request_start,        pattern="^tr_request_start$"),
        CQH(tr_my_requests,          pattern="^tr_my_requests$"),
        CQH(tr_archive_menu,         pattern="^tr_archive$"),
        CQH(tr_archive_list,         pattern="^tr_arch_"),
        CQH(tr_view_request,         pattern="^tr_view_"),
        CQH(tr_mgr_pending,          pattern="^tr_mgr_pending$"),
        CQH(tr_mgr_view,             pattern="^tr_mgr_view_"),
        CQH(tr_mgr_approve,          pattern="^tr_mgr_approve_"),
        CQH(tr_dir_pending,          pattern="^tr_dir_pending$"),
        CQH(tr_dir_view,             pattern="^tr_dir_view_"),
        CQH(tr_dir_approve,          pattern="^tr_dir_approve_"),
        CQH(tr_tm_pending,           pattern="^tr_tm_pending$"),
        CQH(tr_tm_view,              pattern="^tr_tm_view_"),
        CQH(tr_tm_assign,            pattern="^tr_tm_asgn_"),
        CQH(tr_tm_commute_list,      pattern="^tr_tm_commute_list$"),
        CQH(tr_tm_commute_view,      pattern="^tr_tm_com_"),
        CQH(tmc_sel_vehicle,         pattern="^tmc_veh_"),
        CQH(tmc_add_emp,             pattern="^tmc_add_"),
        CQH(tmc_done_vehicle,        pattern="^tmc_done_veh$"),
        CQH(lambda u, c: tmc_show_summary(u.callback_query, c), pattern="^tmc_summary$"),
        CQH(tmc_confirm,             pattern="^tmc_confirm$"),
        CQH(tr_driver_trips,         pattern="^tr_driver_trips$"),
        CQH(tr_drv_view,             pattern="^tr_drv_view_"),
        CQH(fleet_dashboard_handler, pattern="^tr_fleet_dash$"),
    ]
