"""
ROIN WORLD FZE — Housing / Accommodation Handler
=================================================
Section 9 — New role: Housing_Manager

9A. Apartment Registry
9B. Employee Housing Assignment
9C. Housing Request Flow
9D. Maintenance Requests (Housing)
9E. Housing Dashboard

Sheet tabs:
  Apartments_Log: Apt_ID, Building, Floor, Unit, Address,
    Type, Capacity, Current_Occupants_JSON, Occupancy_Count, Status,
    Furnished, Monthly_Rent, Lease_Start, Lease_Expiry,
    Landlord_Name, Landlord_Phone, Contract_Link, Photos_Link, Notes
  Housing_Assignments: Assignment_ID, Emp_Code, Apt_ID,
    Move_In_Date, Move_Out_Date, Status, Deposit_Paid,
    Monthly_Deduction, Notes
  Housing_Requests: Request_ID, Emp_Code, Request_Type, Preferred_Type,
    Roommate_Preference, Urgency, Reason, Housing_Manager_Status,
    Housing_Manager_Date, HR_Status, HR_Date, Assigned_Apartment, Status
  Housing_Maintenance: Ticket_ID, Date, Emp_Code, Apt_ID,
    Issue_Type, Description, Priority, Photos, Assigned_To,
    Resolution_Date, Resolution_Notes, Cost, Status
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm():  return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bhm(): return InlineKeyboardButton("↩️ Housing",    callback_data="menu_housing")

APT_TYPES   = ["Studio","1BR","2BR","3BR","Shared"]
URGENCIES   = ["Normal","Urgent","Emergency"]
MAINT_TYPES = ["Plumbing","Electrical","AC","Furniture","Other"]
PRIORITIES  = ["Low","Medium","High","Emergency"]
PRIO_ICON   = {"Low":"🟢","Medium":"🟡","High":"🟠","Emergency":"🔴"}
APT_STATUS_ICON = {"Available":"🟢","Occupied":"🔵","Maintenance":"🟡","Reserved":"⚪"}

# ── States ────────────────────────────────────────────────────────────────────
APT_BUILDING = 1800; APT_FLOOR   = 1801; APT_UNIT    = 1802
APT_TYPE     = 1803; APT_CAP     = 1804; APT_RENT    = 1805
APT_LANDLORD = 1806; APT_CONFIRM = 1807

ASSIGN_EMP   = 1810; ASSIGN_APT  = 1811; ASSIGN_DATE = 1812; ASSIGN_CONFIRM= 1813

HSG_TYPE     = 1820; HSG_PREF    = 1821; HSG_URGENCY = 1822
HSG_REASON   = 1823; HSG_CONFIRM = 1824

MAINT_APT    = 1830; MAINT_TYPE_H= 1831; MAINT_DESC_H= 1832
MAINT_PRI_H  = 1833; MAINT_CONF  = 1834


def _get_emp_code(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _gen_id(tab, col, prefix):
    try:
        ids = get_sheet(tab).col_values(col)
    except Exception:
        ids = []
    yr  = datetime.now().strftime("%Y")
    px  = f"{prefix}-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _get_available_apartments():
    try:
        rows = get_sheet("Apartments_Log").get_all_records()
        return [r for r in rows if str(r.get("Status","")).strip() == "Available"]
    except Exception:
        return []


def _get_all_apartments():
    try:
        return get_sheet("Apartments_Log").get_all_records()
    except Exception:
        return []


def _get_emp_apartment(ec):
    try:
        rows = get_sheet("Housing_Log").get_all_records()
        for r in rows:
            if (str(r.get("Type","")).strip() == "Assignment"
                    and str(r.get("Emp_Code","")).strip() == str(ec)
                    and str(r.get("Status","")).strip() == "Active"):
                return str(r.get("Apt_ID","")).strip()
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  HOUSING MENU
# ══════════════════════════════════════════════════════════════════════════════
async def housing_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    ec = _get_emp_code(str(q.from_user.id))
    role = ""
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(q.from_user.id): role = r[3].strip(); break
    if role == "Housing_Manager":
        kb = [
            [InlineKeyboardButton("🏠 Apartment Registry",  callback_data="hsg_apt_list")],
            [InlineKeyboardButton("➕ Add Apartment",        callback_data="hsg_apt_new")],
            [InlineKeyboardButton("👤 Assign Employee",      callback_data="hsg_assign_start")],
            [InlineKeyboardButton("📋 Housing Requests",     callback_data="hsg_requests_list")],
            [InlineKeyboardButton("🔧 Maintenance Tickets",  callback_data="hsg_maint_list")],
            [InlineKeyboardButton("📊 Housing Dashboard",    callback_data="hsg_dashboard")],
            [InlineKeyboardButton("💰 Rent Tracker",         callback_data="hsg_rent_tracker")],
            [_bm()],
        ]
    else:
        # Employee view
        kb = [
            [InlineKeyboardButton("🏠 My Housing",           callback_data="hsg_my_housing")],
            [InlineKeyboardButton("📋 Request Housing",      callback_data="hsg_request_new")],
            [InlineKeyboardButton("🔧 Maintenance Request",  callback_data="hsg_maint_new")],
            [_bm()],
        ]
    await q.edit_message_text("🏠 Housing / Accommodation\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  MY HOUSING (Employee)
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_my_housing(update, context):
    q = update.callback_query; await q.answer()
    ec = _get_emp_code(str(q.from_user.id))
    apt_id = _get_emp_apartment(ec or "")
    if not apt_id:
        await q.edit_message_text(
            "🏠 My Housing\n\nNo housing assigned yet.\n"
            "Contact Housing Manager or submit a housing request.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Request Housing", callback_data="hsg_request_new")],
                [_bm()]
            ])); return
    try:
        apts = get_sheet("Apartments_Log").get_all_records()
        apt  = next((a for a in apts if str(a.get("Apt_ID","")).strip() == apt_id), None)
    except Exception:
        apt = None
    if not apt:
        await q.edit_message_text(f"🏠 Assigned to: {apt_id}\nDetails not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    occ = str(apt.get("Current_Occupants_JSON","")).strip()
    msg = (f"🏠 My Housing\n{'─'*24}\n"
           f"Apartment:  {apt_id}\n"
           f"Building:   {apt.get('Building','')}\n"
           f"Unit:       Floor {apt.get('Floor','')} Unit {apt.get('Unit','')}\n"
           f"Type:       {apt.get('Type','')}\n"
           f"Capacity:   {apt.get('Capacity','')} persons\n"
           f"Address:    {apt.get('Address','')}\n"
           f"Roommates:  {occ if occ else 'N/A'}")
    kb = [[InlineKeyboardButton("🔧 Report Issue", callback_data="hsg_maint_new")], [_bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  ADD NEW APARTMENT
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_apt_new_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("🏠 Add New Apartment\n\nEnter building name:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_BUILDING


async def apt_building_inp(update, context):
    context.user_data["apt_building"] = update.message.text.strip()
    await update.message.reply_text("Enter floor number:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_FLOOR


async def apt_floor_inp(update, context):
    context.user_data["apt_floor"] = update.message.text.strip()
    await update.message.reply_text("Enter unit number:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_UNIT


async def apt_unit_inp(update, context):
    context.user_data["apt_unit"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(t, callback_data=f"apt_type_{t}")] for t in APT_TYPES]
    kb.append([_bm()])
    await update.message.reply_text("Apartment type:", reply_markup=InlineKeyboardMarkup(kb))
    return APT_TYPE


async def apt_type_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["apt_type"] = q.data.replace("apt_type_","")
    await q.edit_message_text("Capacity (max persons):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_CAP


async def apt_cap_inp(update, context):
    text = update.message.text.strip()
    try: n = int(text); assert n > 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:"); return APT_CAP
    context.user_data["apt_cap"] = n
    await update.message.reply_text("Monthly rent in AED:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_RENT


async def apt_rent_inp(update, context):
    context.user_data["apt_rent"] = update.message.text.strip()
    await update.message.reply_text("Landlord name and phone (format: Name / Phone):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return APT_LANDLORD


async def apt_landlord_inp(update, context):
    context.user_data["apt_landlord"] = update.message.text.strip()
    bld  = context.user_data.get("apt_building","")
    fl   = context.user_data.get("apt_floor","")
    unit = context.user_data.get("apt_unit","")
    atype= context.user_data.get("apt_type","")
    cap  = context.user_data.get("apt_cap","")
    rent = context.user_data.get("apt_rent","")
    ll   = context.user_data.get("apt_landlord","")
    summary = (f"🏠 New Apartment\n{'─'*24}\n"
               f"Building: {bld}\nFloor: {fl} | Unit: {unit}\n"
               f"Type: {atype} | Capacity: {cap}\n"
               f"Rent: {rent} AED/month\nLandlord: {ll}")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="apt_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="apt_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return APT_CONFIRM


async def apt_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "apt_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        aid = _gen_id("Apartments_Log", 1, "APT")
        landlord = context.user_data.get("apt_landlord","")
        ll_parts = landlord.split("/")
        ll_name  = ll_parts[0].strip() if ll_parts else landlord
        ll_phone = ll_parts[1].strip() if len(ll_parts) > 1 else ""
        row = [aid,
               context.user_data.get("apt_building",""),
               context.user_data.get("apt_floor",""),
               context.user_data.get("apt_unit",""),
               "",  # Address
               context.user_data.get("apt_type",""),
               str(context.user_data.get("apt_cap","")),
               "[]",  # Current_Occupants_JSON
               "0",   # Occupancy_Count
               "Available",
               "",    # Furnished
               context.user_data.get("apt_rent",""),
               "", "",   # Lease_Start, Lease_Expiry
               ll_name, ll_phone,
               "", "", ""]  # Contract_Link, Photos_Link, Notes
        get_sheet("Apartments_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Apartment added!\nID: {aid}",
                                  reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def apt_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  APARTMENT LIST
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_apt_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading apartments...")
    apts = _get_all_apartments()
    if not apts:
        await q.edit_message_text("🏠 No apartments registered yet.",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("➕ Add Apartment", callback_data="hsg_apt_new")],
                                      [_bhm(), _bm()]])); return
    total  = len(apts)
    avail  = sum(1 for a in apts if str(a.get("Status","")) == "Available")
    occ    = sum(1 for a in apts if str(a.get("Status","")) == "Occupied")
    maint  = sum(1 for a in apts if str(a.get("Status","")) == "Maintenance")
    lines  = [f"🏠 Apartment Registry ({total})\n"
              f"🟢 Available: {avail} | 🔵 Occupied: {occ} | 🟡 Maint: {maint}\n{'─'*28}"]
    for a in apts[:20]:
        st = str(a.get("Status",""))
        lines.append(f"{APT_STATUS_ICON.get(st,'❓')} {a.get('Apt_ID','')} | "
                     f"{a.get('Building','')} F{a.get('Floor','')}U{a.get('Unit','')} | "
                     f"{a.get('Type','')} | Cap:{a.get('Capacity','')}")
    if total > 20: lines.append(f"... +{total-20} more")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  ASSIGN EMPLOYEE TO APARTMENT
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_assign_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("👤 Assign Employee to Apartment\n\nEnter employee code:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ASSIGN_EMP


async def assign_emp_inp(update, context):
    ec = update.message.text.strip()
    context.user_data["assign_ec"] = ec
    avail = _get_available_apartments()
    if avail:
        kb = [[InlineKeyboardButton(
            f"{a.get('Apt_ID','')} — {a.get('Building','')} {a.get('Type','')} (Cap:{a.get('Capacity','')})",
            callback_data=f"assign_apt_{a.get('Apt_ID','')}")] for a in avail[:15]]
        kb.append([_bm()])
        await update.message.reply_text(f"Employee: {ec}\n\nSelect apartment:",
                                        reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("⚠️ No available apartments.",
                                        reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))
        return ConversationHandler.END
    return ASSIGN_APT


async def assign_apt_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["assign_apt_id"] = q.data.replace("assign_apt_","")
    await q.edit_message_text("Enter move-in date (DD/MM/YYYY):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ASSIGN_DATE


async def assign_date_inp(update, context):
    text = update.message.text.strip()
    try: datetime.strptime(text, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text("⚠️ Use DD/MM/YYYY:"); return ASSIGN_DATE
    context.user_data["assign_date"] = text
    ec   = context.user_data.get("assign_ec","")
    apt  = context.user_data.get("assign_apt_id","")
    summary = (f"👤 Housing Assignment\n{'─'*24}\n"
               f"Employee:   {ec}\nApartment:  {apt}\nMove-In:    {text}")
    kb = [[InlineKeyboardButton("✅ Confirm", callback_data="assign_confirm"),
           InlineKeyboardButton("❌ Cancel",  callback_data="assign_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return ASSIGN_CONFIRM


async def assign_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "assign_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec    = context.user_data.get("assign_ec","")
    apt   = context.user_data.get("assign_apt_id","")
    mdate = context.user_data.get("assign_date","")
    try:
        aid = _gen_id("Housing_Log", 1, "HSA")
        now = datetime.now().strftime("%d/%m/%Y")
        # Housing_Log cols: Record_ID, Date, Type, Emp_Code, Emp_Name(VLOOKUP),
        #   Apt_ID, Details, Priority, Status, Assigned_To,
        #   Resolution_Date, Resolution_Notes, Cost, Photos, Notes
        row = [aid, mdate, "Assignment", ec, "", apt, "", "", "Active",
               "", "", "", "", "", ""]
        get_sheet("Housing_Log").append_row(row, value_input_option="USER_ENTERED")
        # Update apartment status to Occupied
        ws   = get_sheet("Apartments_Log")
        rows = ws.get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == apt:
                ws.update_cell(i+1, 10, "Occupied")
                break
        await q.edit_message_text(
            f"✅ Employee {ec} assigned to {apt}!\nAssignment ID: {aid}",
            reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def assign_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HOUSING REQUEST (Employee)
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_request_new_start(update, context):
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton("New Housing",  callback_data="hsg_req_type_New"),
           InlineKeyboardButton("Transfer",     callback_data="hsg_req_type_Transfer")],
          [InlineKeyboardButton("Vacate",       callback_data="hsg_req_type_Vacate")],
          [_bm()]]
    await q.edit_message_text("📋 Housing Request\n\nRequest type:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return HSG_TYPE


async def hsg_req_type_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["hsg_req_type"] = q.data.replace("hsg_req_type_","")
    kb = [[InlineKeyboardButton(t, callback_data=f"hsg_pref_{t}")] for t in APT_TYPES]
    kb.append([InlineKeyboardButton("No Preference", callback_data="hsg_pref_Any")])
    kb.append([_bm()])
    await q.edit_message_text("Preferred apartment type:", reply_markup=InlineKeyboardMarkup(kb))
    return HSG_PREF


async def hsg_pref_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["hsg_pref"] = q.data.replace("hsg_pref_","")
    kb = [[InlineKeyboardButton(u, callback_data=f"hsg_urg_{u}")] for u in URGENCIES]
    kb.append([_bm()])
    await q.edit_message_text("Urgency:", reply_markup=InlineKeyboardMarkup(kb))
    return HSG_URGENCY


async def hsg_urgency_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["hsg_urgency"] = q.data.replace("hsg_urg_","")
    await q.edit_message_text("Enter reason for request:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return HSG_REASON


async def hsg_reason_inp(update, context):
    context.user_data["hsg_reason"] = update.message.text.strip()
    rtype = context.user_data.get("hsg_req_type","")
    pref  = context.user_data.get("hsg_pref","")
    urg   = context.user_data.get("hsg_urgency","")
    reason= context.user_data.get("hsg_reason","")
    summary = (f"📋 Housing Request\n{'─'*24}\n"
               f"Type:       {rtype}\nPreference: {pref}\n"
               f"Urgency:    {urg}\nReason:     {reason}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="hsg_req_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="hsg_req_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return HSG_CONFIRM


async def hsg_req_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "hsg_req_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_code(str(q.from_user.id))
    try:
        rid = _gen_id("Housing_Log", 1, "HSG")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        req_type = context.user_data.get("hsg_req_type","")
        pref     = context.user_data.get("hsg_pref","")
        reason   = context.user_data.get("hsg_reason","")
        urg      = context.user_data.get("hsg_urgency","")
        details  = f"{req_type} | Pref: {pref} | {reason}"
        # Housing_Log cols: Record_ID, Date, Type, Emp_Code, Emp_Name(VLOOKUP),
        #   Apt_ID, Details, Priority, Status, Assigned_To,
        #   Resolution_Date, Resolution_Notes, Cost, Photos, Notes
        row = [rid, now, "Request", ec or "", "", "", details, urg, "Requested",
               "", "", "", "", "", ""]
        get_sheet("Housing_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Housing request submitted!\nID: {rid}\nStatus: Pending",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def hsg_req_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HOUSING REQUESTS LIST (Manager)
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_requests_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading housing requests...")
    try:
        all_rows = get_sheet("Housing_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    rows = [r for r in all_rows if str(r.get("Type","")).strip() == "Request"]
    if not rows:
        await q.edit_message_text("📋 No housing requests.",
                                  reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]])); return
    pending = [r for r in rows if str(r.get("Status","")).strip() in ("Requested","Approved")]
    lines   = [f"📋 Housing Requests ({len(rows)} total, {len(pending)} pending)\n{'─'*24}"]
    for r in pending[:15]:
        lines.append(f"⏳ {r.get('Record_ID','')} | {r.get('Emp_Code','')} | "
                     f"{r.get('Details','')[:30]} | {r.get('Priority','')} | {r.get('Status','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HOUSING MAINTENANCE (Ticket)
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_maint_new_start(update, context):
    q = update.callback_query; await q.answer()
    ec = _get_emp_code(str(q.from_user.id))
    apt = _get_emp_apartment(ec or "")
    if not apt:
        await q.edit_message_text(
            "🔧 Maintenance Request\n\n❌ You have no assigned apartment.",
            reply_markup=InlineKeyboardMarkup([[_bm()]])); return ConversationHandler.END
    context.user_data["maint_apt_h"] = apt
    await q.edit_message_text(f"🔧 Maintenance Request\nApartment: {apt}\n\nEnter your apartment ID to confirm:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return MAINT_APT


async def hsg_maint_apt_inp(update, context):
    context.user_data["maint_apt_h"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(t, callback_data=f"hmaint_type_{t}")] for t in MAINT_TYPES]
    kb.append([_bm()])
    await update.message.reply_text("Issue type:", reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_TYPE_H


async def hsg_maint_type_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["maint_type_h"] = q.data.replace("hmaint_type_","")
    await q.edit_message_text("Describe the issue:", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return MAINT_DESC_H


async def hsg_maint_desc_inp(update, context):
    context.user_data["maint_desc_h"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(f"{PRIO_ICON.get(p,'')} {p}", callback_data=f"hmaint_pri_{p}")]
          for p in PRIORITIES]
    kb.append([_bm()])
    await update.message.reply_text("Priority:", reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_PRI_H


async def hsg_maint_pri_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["maint_pri_h"] = q.data.replace("hmaint_pri_","")
    apt  = context.user_data.get("maint_apt_h","")
    mtype= context.user_data.get("maint_type_h","")
    desc = context.user_data.get("maint_desc_h","")
    pri  = context.user_data.get("maint_pri_h","")
    summary = (f"🔧 Maintenance Ticket\n{'─'*24}\n"
               f"Apartment: {apt}\nType:      {mtype}\n"
               f"Priority:  {PRIO_ICON.get(pri,'')} {pri}\nIssue:     {desc}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="hmaint_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="hmaint_cancel")],
          [_bm()]]
    await q.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return MAINT_CONF


async def hsg_maint_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "hmaint_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_code(str(q.from_user.id))
    try:
        tid = _gen_id("Housing_Log", 1, "HMT")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        maint_type = context.user_data.get("maint_type_h","")
        # Housing_Log cols: Record_ID, Date, Type, Emp_Code, Emp_Name(VLOOKUP),
        #   Apt_ID, Details, Priority, Status, Assigned_To,
        #   Resolution_Date, Resolution_Notes, Cost, Photos, Notes
        row = [tid, now, f"Maintenance_{maint_type}", ec or "", "",
               context.user_data.get("maint_apt_h",""),
               context.user_data.get("maint_desc_h",""),
               context.user_data.get("maint_pri_h",""),
               "Open", "", "", "", "", "", ""]
        get_sheet("Housing_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Maintenance ticket submitted!\nID: {tid}\nStatus: Open",
                                  reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def hsg_maint_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  MAINTENANCE LIST / DASHBOARD / RENT TRACKER (Manager)
# ══════════════════════════════════════════════════════════════════════════════
async def hsg_maint_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading maintenance tickets...")
    try:
        all_rows = get_sheet("Housing_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    rows  = [r for r in all_rows if str(r.get("Type","")).strip().startswith("Maintenance")]
    open_t = [r for r in rows if str(r.get("Status","")).strip() in ("Open","In_Progress")]
    if not open_t:
        await q.edit_message_text("✅ No open maintenance tickets.",
                                  reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]])); return
    lines = [f"🔧 Open Tickets ({len(open_t)})\n{'─'*24}"]
    for r in open_t[:20]:
        pri = str(r.get("Priority",""))
        issue_type = str(r.get("Type","")).replace("Maintenance_","")
        lines.append(f"{PRIO_ICON.get(pri,'❓')} {r.get('Record_ID','')} | "
                     f"{r.get('Apt_ID','')} | {issue_type} | "
                     f"{r.get('Status','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))


async def hsg_dashboard(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading housing dashboard...")
    try:
        apts     = get_sheet("Apartments_Log").get_all_records()
        hsg_log  = get_sheet("Housing_Log").get_all_records()
        tickets  = [r for r in hsg_log if str(r.get("Type","")).strip().startswith("Maintenance")]
        reqs     = [r for r in hsg_log if str(r.get("Type","")).strip() == "Request"]
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    total   = len(apts)
    avail   = sum(1 for a in apts if str(a.get("Status","")) == "Available")
    occ     = sum(1 for a in apts if str(a.get("Status","")) == "Occupied")
    maint   = sum(1 for a in apts if str(a.get("Status","")) == "Maintenance")
    occ_rate= round(occ/total*100,1) if total else 0
    open_t  = sum(1 for t in tickets if str(t.get("Status","")) in ("Open","In_Progress"))
    pending_r= sum(1 for r in reqs if str(r.get("Status","")) == "Requested")
    # Leases expiring in 30 days
    today = datetime.now().date()
    exp30 = 0
    for a in apts:
        exp = str(a.get("Lease_Expiry","")).strip()
        if exp:
            try:
                ed = datetime.strptime(exp, "%d/%m/%Y").date()
                if 0 <= (ed - today).days <= 30: exp30 += 1
            except Exception:
                pass
    msg = (f"📊 Housing Dashboard\n{'─'*28}\n"
           f"Total Apartments: {total}\n"
           f"🟢 Available:      {avail}\n"
           f"🔵 Occupied:       {occ}\n"
           f"🟡 Maintenance:    {maint}\n"
           f"Occupancy Rate:    {occ_rate}%\n"
           f"{'─'*28}\n"
           f"⏳ Pending Requests: {pending_r}\n"
           f"🔧 Open Tickets:     {open_t}\n"
           f"⚠️ Leases exp. 30d:  {exp30}")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))


async def hsg_rent_tracker(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading rent data...")
    try:
        apts = get_sheet("Apartments_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    total_rent = 0
    lines      = [f"💰 Rent Tracker\n{'─'*28}"]
    for a in apts:
        st    = str(a.get("Status",""))
        rent  = str(a.get("Monthly_Rent","")).strip()
        lease = str(a.get("Lease_Expiry","")).strip()
        try: total_rent += float(rent)
        except Exception: pass
        icon = APT_STATUS_ICON.get(st,"❓")
        lines.append(f"{icon} {a.get('Apt_ID','')} | {rent} AED | exp:{lease}")
    lines.append(f"{'─'*28}\nTotal monthly rent: {total_rent:.0f} AED")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bhm(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_housing_handlers():
    apt_add_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(hsg_apt_new_start, pattern="^hsg_apt_new$")],
        states={
            APT_BUILDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_building_inp)],
            APT_FLOOR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_floor_inp)],
            APT_UNIT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_unit_inp)],
            APT_TYPE:     [CallbackQueryHandler(apt_type_cb, pattern="^apt_type_")],
            APT_CAP:      [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_cap_inp)],
            APT_RENT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_rent_inp)],
            APT_LANDLORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, apt_landlord_inp)],
            APT_CONFIRM:  [CallbackQueryHandler(apt_confirm_cb, pattern="^apt_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, apt_cancel_handler)],
        per_message=False,
    )
    assign_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(hsg_assign_start, pattern="^hsg_assign_start$")],
        states={
            ASSIGN_EMP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_emp_inp)],
            ASSIGN_APT:    [CallbackQueryHandler(assign_apt_cb, pattern="^assign_apt_")],
            ASSIGN_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_date_inp)],
            ASSIGN_CONFIRM:[CallbackQueryHandler(assign_confirm_cb, pattern="^assign_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, assign_cancel_handler)],
        per_message=False,
    )
    req_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(hsg_request_new_start, pattern="^hsg_request_new$")],
        states={
            HSG_TYPE:   [CallbackQueryHandler(hsg_req_type_cb, pattern="^hsg_req_type_")],
            HSG_PREF:   [CallbackQueryHandler(hsg_pref_cb, pattern="^hsg_pref_")],
            HSG_URGENCY:[CallbackQueryHandler(hsg_urgency_cb, pattern="^hsg_urg_")],
            HSG_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, hsg_reason_inp)],
            HSG_CONFIRM:[CallbackQueryHandler(hsg_req_confirm_cb, pattern="^hsg_req_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, hsg_req_cancel_handler)],
        per_message=False,
    )
    maint_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(hsg_maint_new_start, pattern="^hsg_maint_new$")],
        states={
            MAINT_APT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, hsg_maint_apt_inp)],
            MAINT_TYPE_H:[CallbackQueryHandler(hsg_maint_type_cb, pattern="^hmaint_type_")],
            MAINT_DESC_H:[MessageHandler(filters.TEXT & ~filters.COMMAND, hsg_maint_desc_inp)],
            MAINT_PRI_H: [CallbackQueryHandler(hsg_maint_pri_cb, pattern="^hmaint_pri_")],
            MAINT_CONF:  [CallbackQueryHandler(hsg_maint_confirm_cb, pattern="^hmaint_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, hsg_maint_cancel_handler)],
        per_message=False,
    )
    return [apt_add_h, assign_h, req_h, maint_h]


def get_housing_static_handlers():
    return [
        CallbackQueryHandler(housing_menu_handler,  pattern="^menu_housing$"),
        CallbackQueryHandler(hsg_my_housing,         pattern="^hsg_my_housing$"),
        CallbackQueryHandler(hsg_apt_list,           pattern="^hsg_apt_list$"),
        CallbackQueryHandler(hsg_requests_list,      pattern="^hsg_requests_list$"),
        CallbackQueryHandler(hsg_maint_list,         pattern="^hsg_maint_list$"),
        CallbackQueryHandler(hsg_dashboard,          pattern="^hsg_dashboard$"),
        CallbackQueryHandler(hsg_rent_tracker,       pattern="^hsg_rent_tracker$"),
    ]
