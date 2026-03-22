"""
ROIN WORLD FZE — Vehicle / Transport Handler
=============================================
Section 3 — Complete Rebuild

3A. Any employee requests a vehicle (Direct Manager approves → Transport Manager assigns)
3B. Driver: Start Trip / End Trip buttons
3C. Transport Manager: daily driver permit PDF upload
3D. Driver safety lectures
3E. Fleet dashboard + overdue trip alerts

Sheet tabs:
  Trip_Log: Trip_ID, Requesting_Emp, Requesting_Dept, From_Location,
    To_Location, Purpose, Date, Est_Departure, Est_Hours, Passengers,
    Manager_Status, Manager_Date, Transport_Status, Transport_Date,
    Car_Plate, Driver_Code, Driver_Name, Driver_Phone,
    Actual_Departure, Actual_Return, Fuel_Start, Fuel_End,
    Odometer_Start, Odometer_End, Fuel_Used_Liters, Delay_Reason, Status

  Driver_Permits_Log: Permit_ID, Date, Driver_Code, PDF_Link, Uploaded_By, Upload_Time
  Driver_Safety_Log: Log_ID, Date, Driver_Code, Lecture_Title, Duration_Min, Facilitator, Notes
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

# ── Back-button helpers ────────────────────────────────────────────────────────
def _bm():   return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bveh(): return InlineKeyboardButton("↩️ Vehicles",   callback_data="menu_vehicles")

# ── Constants ──────────────────────────────────────────────────────────────────
PURPOSES = ["Official Business", "Airport Transfer", "Site Visit",
            "Medical", "Government", "Supplies", "Other"]
HOURS_OPTS = ["1", "2", "3", "4", "6", "8", "Half Day", "Full Day"]
LECT_DURATIONS = ["15", "30", "45", "60", "90"]

# ── States ─────────────────────────────────────────────────────────────────────
# Request flow
VEH_FROM      = 1100
VEH_TO        = 1101
VEH_PURPOSE   = 1102
VEH_PURPOSE_T = 1103
VEH_DATE      = 1104
VEH_DEPART    = 1105
VEH_HOURS     = 1106
VEH_PASS      = 1107
VEH_CONFIRM   = 1108

# Transport Manager — assign driver
VEH_TRIP_SEL  = 1120
VEH_PLATE     = 1121
VEH_DRV_CODE  = 1122
VEH_DRV_NAME  = 1123
VEH_DRV_PHONE = 1124
VEH_ASSIGN_OK = 1125

# Driver — start trip
VEH_ST_TRIP   = 1130
VEH_ST_FUEL   = 1131
VEH_ST_ODO    = 1132
VEH_ST_OK     = 1133

# Driver — end trip
VEH_EN_TRIP   = 1140
VEH_EN_FUEL   = 1141
VEH_EN_ODO    = 1142
VEH_EN_DELAY  = 1143
VEH_EN_OK     = 1144

# Permit upload
VEH_PERMIT    = 1150

# Safety lecture
VEH_LECT_TITLE  = 1160
VEH_LECT_DRIVER = 1161
VEH_LECT_DUR    = 1162
VEH_LECT_FAC    = 1163
VEH_LECT_NOTES  = 1164
VEH_LECT_OK     = 1165


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _get_emp(tid):
    """Return (emp_code, dept, role, manager_code) or None."""
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if r[1].strip() == str(tid):
                ec = r[0].strip()
                for j, e in enumerate(get_sheet("Employee_DB").get_all_values()):
                    if j == 0:
                        continue
                    if e[0].strip() == ec:
                        dept = e[4].strip() if len(e) > 4 else ""
                        mgr  = e[8].strip() if len(e) > 8 else ""
                        role = r[2].strip() if len(r) > 2 else "Employee"
                        return ec, dept, role, mgr
                return ec, "", r[2].strip() if len(r) > 2 else "Employee", ""
    except Exception:
        pass
    return None


def _gen_trip_id():
    ids = get_sheet("Trip_Log").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"TRIP-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx+1:04d}"


def _gen_permit_id():
    ids = get_sheet("Driver_Compliance").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"PERM-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx+1:04d}"


def _gen_lect_id():
    ids = get_sheet("Driver_Compliance").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"SLEC-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx+1:04d}"


def _find_col(headers, name):
    for i, h in enumerate(headers):
        if h.strip().lower() == name.lower():
            return i
    return -1


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN VEHICLES MENU
# ══════════════════════════════════════════════════════════════════════════════
async def vehicles_menu_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp  = _get_emp(q.from_user.id)
    role = emp[2] if emp else "Employee"

    buttons = [
        [InlineKeyboardButton("🚗 Request Vehicle", callback_data="veh_request")],
        [InlineKeyboardButton("📋 My Requests",     callback_data="veh_my_requests")],
    ]

    if role == "Driver":
        buttons.insert(1, [InlineKeyboardButton("🚀 Start Trip", callback_data="veh_start_trip")])
        buttons.insert(2, [InlineKeyboardButton("🏁 End Trip",   callback_data="veh_end_trip")])

    if role == "Transport_Manager":
        buttons += [
            [InlineKeyboardButton("📋 Pending Assignments",  callback_data="veh_pending_assign")],
            [InlineKeyboardButton("📄 Upload Driver Permits", callback_data="veh_upload_permit")],
            [InlineKeyboardButton("📚 Log Safety Lecture",   callback_data="veh_log_lecture")],
            [InlineKeyboardButton("📊 Fleet Dashboard",      callback_data="veh_fleet_dash")],
            [InlineKeyboardButton("⚠️ Overdue Trips",        callback_data="veh_overdue")],
        ]

    if role == "Director":
        buttons += [
            [InlineKeyboardButton("📊 Fleet Dashboard", callback_data="veh_fleet_dash")],
            [InlineKeyboardButton("⚠️ Overdue Trips",   callback_data="veh_overdue")],
        ]

    buttons.append([_bm()])
    await q.edit_message_text(
        "🚗 Vehicle / Transport\n\nSelect action:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ══════════════════════════════════════════════════════════════════════════════
#  REQUEST VEHICLE — conversation
# ══════════════════════════════════════════════════════════════════════════════
async def veh_request_start(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🚗 Vehicle Request\n\nEnter FROM location:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_FROM


async def veh_from_inp(update, context):
    context.user_data["veh_from"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter TO location:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_TO


async def veh_to_inp(update, context):
    context.user_data["veh_to"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(p, callback_data=f"veh_purp_{i}")] for i, p in enumerate(PURPOSES)]
    kb.append([_bm()])
    await update.message.reply_text(
        "Select purpose:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return VEH_PURPOSE


async def veh_purpose_cb(update, context):
    q = update.callback_query
    await q.answer()
    idx     = int(q.data.replace("veh_purp_", ""))
    purpose = PURPOSES[idx]
    if purpose == "Other":
        await q.edit_message_text(
            "Type your purpose:",
            reply_markup=InlineKeyboardMarkup([[_bm()]])
        )
        return VEH_PURPOSE_T
    context.user_data["veh_purpose"] = purpose
    await q.edit_message_text(
        "Enter trip date (DD/MM/YYYY), or type 'today':",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DATE


async def veh_purpose_text_inp(update, context):
    context.user_data["veh_purpose"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter trip date (DD/MM/YYYY), or type 'today':",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DATE


async def veh_date_inp(update, context):
    raw = update.message.text.strip().lower()
    if raw == "today":
        context.user_data["veh_date"] = datetime.now().strftime("%d/%m/%Y")
    else:
        try:
            datetime.strptime(raw, "%d/%m/%Y")
            context.user_data["veh_date"] = raw
        except ValueError:
            await update.message.reply_text("⚠️ Use DD/MM/YYYY or 'today':")
            return VEH_DATE
    await update.message.reply_text(
        "Estimated departure time (e.g. 08:30):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DEPART


async def veh_depart_inp(update, context):
    context.user_data["veh_depart"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(h, callback_data=f"veh_hrs_{h}")] for h in HOURS_OPTS]
    kb.append([_bm()])
    await update.message.reply_text(
        "Estimated trip duration:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return VEH_HOURS


async def veh_hours_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["veh_hours"] = q.data.replace("veh_hrs_", "")
    await q.edit_message_text(
        "Number of passengers (including yourself):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_PASS


async def veh_pass_inp(update, context):
    txt = update.message.text.strip()
    try:
        n = int(txt)
        assert n >= 1
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:")
        return VEH_PASS
    context.user_data["veh_pass"] = n
    ud = context.user_data
    summary = (
        f"🚗 Vehicle Request Summary\n{'─'*24}\n"
        f"From:      {ud.get('veh_from','')}\n"
        f"To:        {ud.get('veh_to','')}\n"
        f"Purpose:   {ud.get('veh_purpose','')}\n"
        f"Date:      {ud.get('veh_date','')}\n"
        f"Departure: {ud.get('veh_depart','')}\n"
        f"Duration:  {ud.get('veh_hours','')} hr(s)\n"
        f"Passengers:{ud.get('veh_pass',1)}"
    )
    kb = [
        [InlineKeyboardButton("✅ Submit", callback_data="veh_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="veh_cancel")],
        [_bm()],
    ]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return VEH_CONFIRM


async def veh_confirm_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "veh_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    emp  = _get_emp(q.from_user.id)
    ec   = emp[0] if emp else ""
    dept = emp[1] if emp else ""
    ud   = context.user_data
    try:
        tid = _gen_trip_id()
        row = [
            tid,
            ec, "", "",  # Emp_Code, Name (VLOOKUP), Dept (VLOOKUP)
            ud.get("veh_from",""), ud.get("veh_to",""),
            ud.get("veh_purpose",""),
            ud.get("veh_date",""), ud.get("veh_depart",""),
            ud.get("veh_hours",""), str(ud.get("veh_pass",1)),
            "Pending", "",   # Manager_Status, Manager_Date
            "Pending", "",   # Transport_Status, Transport_Date
            "", "", "", "",  # Car_Plate, Driver_Code, Driver_Name, Driver_Phone
            "", "",          # Actual_Departure, Actual_Return
            "", "",          # Fuel_Start, Fuel_End
            "", "", "",      # Odometer_Start, Odometer_End, Fuel_Used_Liters
            "",              # Delay_Reason
            "Pending_Manager"
        ]
        get_sheet("Trip_Log").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Vehicle request submitted!\nID: {tid}\nAwaiting manager approval.",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def veh_cancel_cmd(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  MY REQUESTS
# ══════════════════════════════════════════════════════════════════════════════
async def veh_my_requests_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp(q.from_user.id)
    ec  = emp[0] if emp else None
    if not ec:
        await q.edit_message_text("⚠️ Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    my = [r for r in rows if str(r.get("Requesting_Emp","")).strip() == ec]
    if not my:
        await q.edit_message_text("📋 No vehicle requests found.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    status_icon = {
        "Pending_Manager": "⏳", "Approved": "✅", "Rejected": "❌",
        "In_Progress": "🚗", "Completed": "🏁", "Assigned": "🔄"
    }
    lines = [f"🚗 My Vehicle Requests ({len(my)})\n{'─'*24}"]
    for r in my[-10:]:
        st  = str(r.get("Status",""))
        ico = status_icon.get(st, "❓")
        lines.append(f"{ico} {r.get('Trip_ID','')} | {r.get('Date','')} | "
                     f"{r.get('From_Location','')} → {r.get('To_Location','')} | {st}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSPORT MANAGER — PENDING ASSIGNMENTS
# ══════════════════════════════════════════════════════════════════════════════
async def veh_pending_assign_handler(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ Loading pending trips...")
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    pending = [r for r in rows
               if str(r.get("Manager_Status","")).strip() == "Approved"
               and str(r.get("Transport_Status","")).strip() in ("Pending", "")]
    if not pending:
        await q.edit_message_text("✅ No pending assignments.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return
    kb = []
    for r in pending[:15]:
        tid = r.get("Trip_ID","")
        lbl = (f"{tid} | {r.get('Date','')} | {r.get('Requesting_Emp','')} | "
               f"{r.get('From_Location','')}→{r.get('To_Location','')}")
        kb.append([InlineKeyboardButton(lbl[:60], callback_data=f"veh_assign_{tid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text(
        f"📋 Trips awaiting driver assignment ({len(pending)}):",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def veh_assign_start(update, context):
    q = update.callback_query
    await q.answer()
    trip_id = q.data.replace("veh_assign_", "")
    context.user_data["assign_trip_id"] = trip_id
    await q.edit_message_text(
        f"Assigning driver for: {trip_id}\n\nEnter vehicle plate number:",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
    )
    return VEH_PLATE


async def veh_plate_inp(update, context):
    context.user_data["assign_plate"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "Enter driver employee code:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DRV_CODE


async def veh_drv_code_inp(update, context):
    context.user_data["assign_drv_code"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter driver full name:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DRV_NAME


async def veh_drv_name_inp(update, context):
    context.user_data["assign_drv_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter driver phone number:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_DRV_PHONE


async def veh_drv_phone_inp(update, context):
    context.user_data["assign_drv_phone"] = update.message.text.strip()
    ud = context.user_data
    summary = (
        f"📋 Driver Assignment\n{'─'*24}\n"
        f"Trip ID:  {ud.get('assign_trip_id','')}\n"
        f"Plate:    {ud.get('assign_plate','')}\n"
        f"Driver:   {ud.get('assign_drv_name','')} ({ud.get('assign_drv_code','')})\n"
        f"Phone:    {ud.get('assign_drv_phone','')}"
    )
    kb = [
        [InlineKeyboardButton("✅ Confirm", callback_data="veh_assign_confirm"),
         InlineKeyboardButton("❌ Cancel",  callback_data="veh_assign_cancel")],
        [_bm()],
    ]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return VEH_ASSIGN_OK


async def veh_assign_confirm_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "veh_assign_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ud  = context.user_data
    tid = ud.get("assign_trip_id","")
    try:
        ws   = get_sheet("Trip_Log")
        hdrs = ws.row_values(1)
        rows = ws.get_all_values()
        now  = datetime.now().strftime("%d/%m/%Y %H:%M")
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if row[0].strip() == tid:
                rn = i + 1
                def col(name): return _find_col(hdrs, name) + 1
                ws.update_cell(rn, col("Car_Plate"),        ud.get("assign_plate",""))
                ws.update_cell(rn, col("Driver_Code"),      ud.get("assign_drv_code",""))
                ws.update_cell(rn, col("Driver_Name"),      ud.get("assign_drv_name",""))
                ws.update_cell(rn, col("Driver_Phone"),     ud.get("assign_drv_phone",""))
                ws.update_cell(rn, col("Transport_Status"), "Assigned")
                ws.update_cell(rn, col("Transport_Date"),   now)
                ws.update_cell(rn, col("Status"),           "Assigned")
                break
        await q.edit_message_text(
            f"✅ Driver assigned to {tid}!",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVER — START TRIP
# ══════════════════════════════════════════════════════════════════════════════
async def veh_start_trip_start(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp(q.from_user.id)
    ec  = emp[0] if emp else None
    if not ec:
        await q.edit_message_text("⚠️ Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    assigned = [r for r in rows
                if str(r.get("Driver_Code","")).strip() == ec
                and str(r.get("Status","")).strip() == "Assigned"]
    if not assigned:
        await q.edit_message_text("✅ No trips assigned to you.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END
    kb = []
    for r in assigned[:10]:
        tid = r.get("Trip_ID","")
        lbl = f"{tid} | {r.get('Date','')} | {r.get('From_Location','')}→{r.get('To_Location','')}"
        kb.append([InlineKeyboardButton(lbl[:60], callback_data=f"veh_st_{tid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("🚀 Select trip to START:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return VEH_ST_TRIP


async def veh_st_trip_cb(update, context):
    q = update.callback_query
    await q.answer()
    tid = q.data.replace("veh_st_", "")
    context.user_data["st_trip_id"] = tid
    await q.edit_message_text(
        f"Trip: {tid}\n\nEnter starting FUEL level (litres or %):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_ST_FUEL


async def veh_st_fuel_inp(update, context):
    context.user_data["st_fuel"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter starting ODOMETER reading (km):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_ST_ODO


async def veh_st_odo_inp(update, context):
    context.user_data["st_odo"] = update.message.text.strip()
    ud = context.user_data
    kb = [
        [InlineKeyboardButton("✅ Start Trip", callback_data="veh_st_confirm"),
         InlineKeyboardButton("❌ Cancel",     callback_data="veh_st_cancel")],
        [_bm()],
    ]
    await update.message.reply_text(
        f"🚀 Start Trip: {ud.get('st_trip_id','')}\n"
        f"Fuel: {ud.get('st_fuel','')} | Odometer: {ud.get('st_odo','')} km",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return VEH_ST_OK


async def veh_st_confirm_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "veh_st_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ud  = context.user_data
    tid = ud.get("st_trip_id","")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        ws   = get_sheet("Trip_Log")
        hdrs = ws.row_values(1)
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if row[0].strip() == tid:
                rn = i + 1
                def col(n): return _find_col(hdrs, n) + 1
                ws.update_cell(rn, col("Actual_Departure"), now)
                ws.update_cell(rn, col("Fuel_Start"),       ud.get("st_fuel",""))
                ws.update_cell(rn, col("Odometer_Start"),   ud.get("st_odo",""))
                ws.update_cell(rn, col("Status"),           "In_Progress")
                break
        await q.edit_message_text(
            f"🚀 Trip {tid} started!\nDeparture logged: {now}",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  DRIVER — END TRIP
# ══════════════════════════════════════════════════════════════════════════════
async def veh_end_trip_start(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp(q.from_user.id)
    ec  = emp[0] if emp else None
    if not ec:
        await q.edit_message_text("⚠️ Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    active = [r for r in rows
              if str(r.get("Driver_Code","")).strip() == ec
              and str(r.get("Status","")).strip() == "In_Progress"]
    if not active:
        await q.edit_message_text("✅ No active trips.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return ConversationHandler.END
    kb = []
    for r in active[:10]:
        tid = r.get("Trip_ID","")
        lbl = (f"{tid} | {r.get('Actual_Departure','')} | "
               f"{r.get('From_Location','')}→{r.get('To_Location','')}")
        kb.append([InlineKeyboardButton(lbl[:60], callback_data=f"veh_en_{tid}")])
    kb.append([_bveh(), _bm()])
    await q.edit_message_text("🏁 Select trip to END:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return VEH_EN_TRIP


async def veh_en_trip_cb(update, context):
    q = update.callback_query
    await q.answer()
    tid = q.data.replace("veh_en_", "")
    context.user_data["en_trip_id"] = tid
    await q.edit_message_text(
        f"Trip: {tid}\n\nEnter ending FUEL level (litres or %):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_EN_FUEL


async def veh_en_fuel_inp(update, context):
    context.user_data["en_fuel"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter ending ODOMETER reading (km):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_EN_ODO


async def veh_en_odo_inp(update, context):
    context.user_data["en_odo"] = update.message.text.strip()
    await update.message.reply_text(
        "Any delay or notes? (type '-' for none):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_EN_DELAY


async def veh_en_delay_inp(update, context):
    context.user_data["en_delay"] = update.message.text.strip()
    ud = context.user_data
    kb = [
        [InlineKeyboardButton("✅ End Trip", callback_data="veh_en_confirm"),
         InlineKeyboardButton("❌ Cancel",   callback_data="veh_en_cancel")],
        [_bm()],
    ]
    await update.message.reply_text(
        f"🏁 End Trip: {ud.get('en_trip_id','')}\n"
        f"Fuel: {ud.get('en_fuel','')} | Odometer: {ud.get('en_odo','')} km\n"
        f"Delay: {ud.get('en_delay','')}",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return VEH_EN_OK


async def veh_en_confirm_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "veh_en_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ud  = context.user_data
    tid = ud.get("en_trip_id","")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        ws   = get_sheet("Trip_Log")
        hdrs = ws.row_values(1)
        rows = ws.get_all_values()
        for i, row in enumerate(rows):
            if i == 0:
                continue
            if row[0].strip() == tid:
                rn = i + 1
                def col(n): return _find_col(hdrs, n) + 1
                # Calculate fuel used
                try:
                    fs   = float(str(row[col("Fuel_Start") - 1]).replace("%","").strip())
                    fe   = float(ud.get("en_fuel","0").replace("%","").strip())
                    used = str(round(abs(fs - fe), 1))
                except Exception:
                    used = ""
                ws.update_cell(rn, col("Actual_Return"),    now)
                ws.update_cell(rn, col("Fuel_End"),         ud.get("en_fuel",""))
                ws.update_cell(rn, col("Odometer_End"),     ud.get("en_odo",""))
                ws.update_cell(rn, col("Fuel_Used_Liters"), used)
                ws.update_cell(rn, col("Delay_Reason"),     ud.get("en_delay",""))
                ws.update_cell(rn, col("Status"),           "Completed")
                break
        await q.edit_message_text(
            f"🏁 Trip {tid} completed!\nReturn logged: {now}",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSPORT MANAGER — UPLOAD DAILY DRIVER PERMITS
# ══════════════════════════════════════════════════════════════════════════════
async def veh_upload_permit_start(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📄 Upload Daily Driver Permits\n\n"
        "Enter the driver employee code first:",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
    )
    return VEH_PERMIT


async def veh_permit_driver_code_inp(update, context):
    context.user_data["permit_driver_code"] = update.message.text.strip()
    await update.message.reply_text(
        f"Driver code: {context.user_data['permit_driver_code']}\n\n"
        "Now send the permit PDF or document:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_PERMIT


async def veh_permit_doc(update, context):
    emp = _get_emp(update.message.from_user.id)
    ec  = emp[0] if emp else ""
    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ Please send a PDF or document file.")
        return VEH_PERMIT
    driver_code = context.user_data.get("permit_driver_code", "Unknown")
    now = datetime.now()
    try:
        pid = _gen_permit_id()
        # Driver_Compliance cols: Record_ID, Date, Type, Title, Uploaded_By,
        #   Driver_Count, Attendees_JSON, Instructor, Duration_Hours,
        #   Certificate_Link, PDF_Drive_Link, Next_Due_Date, Status, Notes
        row = [
            pid,
            now.strftime("%d/%m/%Y"),
            "Permit_Upload",
            "",             # Title
            ec,             # Uploaded_By
            1,              # Driver_Count
            driver_code,    # Attendees_JSON (driver code)
            "",             # Instructor
            "",             # Duration_Hours
            "",             # Certificate_Link
            doc.file_id,    # PDF_Drive_Link
            "",             # Next_Due_Date
            "Active",
            "",             # Notes
        ]
        get_sheet("Driver_Compliance").append_row(row, value_input_option="USER_ENTERED")
        await update.message.reply_text(
            f"✅ Permit uploaded!\nID: {pid}\nDriver: {driver_code}\nDate: {now.strftime('%d/%m/%Y')}",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSPORT MANAGER — LOG SAFETY LECTURE
# ══════════════════════════════════════════════════════════════════════════════
async def veh_log_lecture_start(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📚 Log Driver Safety Lecture\n\nEnter lecture title:",
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
    )
    return VEH_LECT_TITLE


async def veh_lect_title_inp(update, context):
    context.user_data["lect_title"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter driver employee code(s) (comma-separated if multiple):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_LECT_DRIVER


async def veh_lect_driver_inp(update, context):
    context.user_data["lect_drivers"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(d, callback_data=f"veh_ldur_{d}")] for d in LECT_DURATIONS]
    kb.append([_bm()])
    await update.message.reply_text(
        "Lecture duration (minutes):",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return VEH_LECT_DUR


async def veh_lect_dur_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["lect_dur"] = q.data.replace("veh_ldur_", "")
    await q.edit_message_text(
        "Facilitator name:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_LECT_FAC


async def veh_lect_fac_inp(update, context):
    context.user_data["lect_fac"] = update.message.text.strip()
    await update.message.reply_text(
        "Additional notes (or '-' to skip):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return VEH_LECT_NOTES


async def veh_lect_notes_inp(update, context):
    context.user_data["lect_notes"] = update.message.text.strip()
    ud = context.user_data
    summary = (
        f"📚 Safety Lecture Log\n{'─'*24}\n"
        f"Title:      {ud.get('lect_title','')}\n"
        f"Drivers:    {ud.get('lect_drivers','')}\n"
        f"Duration:   {ud.get('lect_dur','')} min\n"
        f"Facilitator:{ud.get('lect_fac','')}\n"
        f"Notes:      {ud.get('lect_notes','')}"
    )
    kb = [
        [InlineKeyboardButton("✅ Save",   callback_data="veh_lect_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="veh_lect_cancel")],
        [_bm()],
    ]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return VEH_LECT_OK


async def veh_lect_confirm_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "veh_lect_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ud  = context.user_data
    now = datetime.now()
    drivers = [d.strip() for d in ud.get("lect_drivers","").split(",") if d.strip()]
    try:
        ws = get_sheet("Driver_Compliance")
        for drv in drivers:
            lid = _gen_lect_id()
            # Driver_Compliance cols: Record_ID, Date, Type, Title, Uploaded_By,
            #   Driver_Count, Attendees_JSON, Instructor, Duration_Hours,
            #   Certificate_Link, PDF_Drive_Link, Next_Due_Date, Status, Notes
            row = [
                lid,
                now.strftime("%d/%m/%Y"),
                "Safety_Lecture",
                ud.get("lect_title",""),  # Title
                "",                        # Uploaded_By
                1,                         # Driver_Count
                drv,                       # Attendees_JSON (driver code)
                ud.get("lect_fac",""),     # Instructor
                ud.get("lect_dur",""),     # Duration_Hours
                "",                        # Certificate_Link
                "",                        # PDF_Drive_Link
                "",                        # Next_Due_Date
                "Completed",
                ud.get("lect_notes",""),   # Notes
            ]
            ws.append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Safety lecture logged for {len(drivers)} driver(s)!",
            reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  FLEET DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
async def veh_fleet_dash_handler(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ Loading fleet dashboard...")
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    total     = len(rows)
    pending_m = sum(1 for r in rows if r.get("Status","") == "Pending_Manager")
    in_prog   = sum(1 for r in rows if r.get("Status","") == "In_Progress")
    assigned  = sum(1 for r in rows if r.get("Status","") == "Assigned")
    completed = sum(1 for r in rows if r.get("Status","") == "Completed")
    rejected  = sum(1 for r in rows if r.get("Status","") == "Rejected")

    # Trips this month
    now        = datetime.now()
    this_month = []
    for r in rows:
        try:
            d = datetime.strptime(str(r.get("Date","")), "%d/%m/%Y")
            if d.year == now.year and d.month == now.month:
                this_month.append(r)
        except Exception:
            pass

    active_drivers = set(
        r.get("Driver_Code","") for r in rows
        if r.get("Status","") == "In_Progress" and r.get("Driver_Code","")
    )

    msg = (
        f"📊 Fleet Dashboard\n{'─'*28}\n"
        f"Total trips:        {total}\n"
        f"This month:         {len(this_month)}\n"
        f"{'─'*28}\n"
        f"⏳ Pending Manager:  {pending_m}\n"
        f"🔄 Assigned:         {assigned}\n"
        f"🚗 In Progress:      {in_prog}\n"
        f"✅ Completed:        {completed}\n"
        f"❌ Rejected:         {rejected}\n"
        f"{'─'*28}\n"
        f"Drivers active now: {len(active_drivers)}"
    )
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  OVERDUE TRIPS
# ══════════════════════════════════════════════════════════════════════════════
async def veh_overdue_handler(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("⏳ Checking overdue trips...")
    try:
        rows = get_sheet("Trip_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    now     = datetime.now()
    overdue = []
    for r in rows:
        if str(r.get("Status","")) != "In_Progress":
            continue
        dep_str = str(r.get("Actual_Departure","")).strip()
        if not dep_str:
            continue
        try:
            dep     = datetime.strptime(dep_str, "%d/%m/%Y %H:%M")
            hrs_raw = str(r.get("Est_Hours","2")).replace("Half Day","4").replace("Full Day","8")
            try:
                est_hrs = float(hrs_raw)
            except ValueError:
                est_hrs = 4.0
            expected_ts = dep.timestamp() + est_hrs * 3600
            if now.timestamp() > expected_ts + 3600:  # 1hr grace
                overdue.append((r, now.timestamp() - expected_ts))
        except Exception:
            pass

    if not overdue:
        await q.edit_message_text("✅ No overdue trips.",
                                  reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]]))
        return

    lines = [f"⚠️ Overdue Trips ({len(overdue)})\n{'─'*28}"]
    for r, over_sec in overdue:
        over_hrs = round(over_sec / 3600, 1)
        lines.append(
            f"🔴 {r.get('Trip_ID','')} | Driver: {r.get('Driver_Name','Unknown')} "
            f"({r.get('Driver_Code','')})\n"
            f"   {r.get('From_Location','')}→{r.get('To_Location','')} | "
            f"Overdue: {over_hrs}h | Phone: {r.get('Driver_Phone','N/A')}"
        )
    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[_bveh(), _bm()]])
    )


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_vehicle_handlers():
    # 1. Vehicle request
    request_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_request_start, pattern="^veh_request$")],
        states={
            VEH_FROM:      [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_from_inp)],
            VEH_TO:        [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_to_inp)],
            VEH_PURPOSE:   [CallbackQueryHandler(veh_purpose_cb, pattern="^veh_purp_")],
            VEH_PURPOSE_T: [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_purpose_text_inp)],
            VEH_DATE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_date_inp)],
            VEH_DEPART:    [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_depart_inp)],
            VEH_HOURS:     [CallbackQueryHandler(veh_hours_cb, pattern="^veh_hrs_")],
            VEH_PASS:      [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_pass_inp)],
            VEH_CONFIRM:   [CallbackQueryHandler(veh_confirm_cb, pattern="^veh_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    # 2. Driver assignment
    assign_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_assign_start, pattern="^veh_assign_")],
        states={
            VEH_PLATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_plate_inp)],
            VEH_DRV_CODE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_drv_code_inp)],
            VEH_DRV_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_drv_name_inp)],
            VEH_DRV_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_drv_phone_inp)],
            VEH_ASSIGN_OK: [CallbackQueryHandler(veh_assign_confirm_cb,
                                                  pattern="^veh_assign_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    # 3. Start trip
    start_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_start_trip_start, pattern="^veh_start_trip$")],
        states={
            VEH_ST_TRIP: [CallbackQueryHandler(veh_st_trip_cb, pattern="^veh_st_")],
            VEH_ST_FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_st_fuel_inp)],
            VEH_ST_ODO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_st_odo_inp)],
            VEH_ST_OK:   [CallbackQueryHandler(veh_st_confirm_cb,
                                                pattern="^veh_st_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    # 4. End trip
    end_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_end_trip_start, pattern="^veh_end_trip$")],
        states={
            VEH_EN_TRIP:  [CallbackQueryHandler(veh_en_trip_cb, pattern="^veh_en_")],
            VEH_EN_FUEL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_en_fuel_inp)],
            VEH_EN_ODO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_en_odo_inp)],
            VEH_EN_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_en_delay_inp)],
            VEH_EN_OK:    [CallbackQueryHandler(veh_en_confirm_cb,
                                                 pattern="^veh_en_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    # 5. Permit upload
    permit_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_upload_permit_start, pattern="^veh_upload_permit$")],
        states={
            VEH_PERMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, veh_permit_driver_code_inp),
                MessageHandler(filters.Document.ALL, veh_permit_doc),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    # 6. Safety lecture
    lecture_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(veh_log_lecture_start, pattern="^veh_log_lecture$")],
        states={
            VEH_LECT_TITLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_lect_title_inp)],
            VEH_LECT_DRIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_lect_driver_inp)],
            VEH_LECT_DUR:    [CallbackQueryHandler(veh_lect_dur_cb, pattern="^veh_ldur_")],
            VEH_LECT_FAC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_lect_fac_inp)],
            VEH_LECT_NOTES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, veh_lect_notes_inp)],
            VEH_LECT_OK:     [CallbackQueryHandler(veh_lect_confirm_cb,
                                                    pattern="^veh_lect_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, veh_cancel_cmd)],
        per_message=False,
    )

    return [request_h, assign_h, start_h, end_h, permit_h, lecture_h]


def get_vehicle_static_handlers():
    return [
        CallbackQueryHandler(vehicles_menu_handler,      pattern="^menu_vehicles$"),
        CallbackQueryHandler(veh_my_requests_handler,    pattern="^veh_my_requests$"),
        CallbackQueryHandler(veh_pending_assign_handler, pattern="^veh_pending_assign$"),
        CallbackQueryHandler(veh_fleet_dash_handler,     pattern="^veh_fleet_dash$"),
        CallbackQueryHandler(veh_overdue_handler,        pattern="^veh_overdue$"),
    ]
