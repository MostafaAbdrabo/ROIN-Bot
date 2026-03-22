"""
ROIN WORLD FZE — Unified Requests Menu
=======================================
One place for ALL request types: Leave, Missing Punch, Early Departure,
Overtime, Memos. Organized by mode (upcoming/past/archive) → month → type → list.

Callback patterns:
  menu_requests            → main menu
  req_new                  → new request type picker
  req_upcoming             → upcoming: month list (own/role-filtered)
  req_past                 → past: month list
  req_archive              → archive: month list
  req_team_upcoming        → team requests: month list (managers)
  req_all_upcoming         → all requests: month list (HR/Director)
  req_balance              → leave balance quick view
  req_m_{mode}_{ym}        → month detail: type buttons (own scope)
  req_tm_{mode}_{ym}       → month detail: team scope
  req_am_{mode}_{ym}       → month detail: all scope
  req_t_{mode}_{ym}_{tc}   → item list (own scope)
  req_tt_{mode}_{ym}_{tc}  → item list (team scope)
  req_at_{mode}_{ym}_{tc}  → item list (all scope)
  req_av_{ym}_{sub}        → archive sub-view: type/sub/sum
  req_avs_{ym}_{ec}        → archive by submitter: person items
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet

# ── Role constants ─────────────────────────────────────────────────────────────
HR_ALL_ROLES = {"HR_Staff", "HR_Manager", "Director", "Bot_Manager"}
TEAM_ROLES   = {"Supervisor", "Direct_Manager"}

# ── Type mappings ──────────────────────────────────────────────────────────────
TYPE_EMOJI = {
    "Paid": "🏖️", "Sick": "🤒", "Emergency": "🚨", "Unpaid": "📋",
    "Business_Trip": "🚗", "Missing_Punch": "🖐", "Early_Departure": "🚪",
    "Overtime_Planned": "⏰", "Overtime_Emergency": "🚨",
}
LEAVE_TYPES = {"Paid", "Sick", "Emergency", "Unpaid", "Business_Trip"}
MP_TYPES    = {"Missing_Punch"}
ED_TYPES    = {"Early_Departure"}
OT_TYPES    = {"Overtime_Planned", "Overtime_Emergency"}

# Short type codes (kept short for callback_data budget)
TC_LV, TC_MP, TC_ED, TC_OT, TC_MO, TC_AL = "lv", "mp", "ed", "ot", "mo", "al"
TCODE_NAMES = {
    TC_LV: "🏖️ Leave",
    TC_MP: "🖐 Missing Punch",
    TC_ED: "🚪 Early Departure",
    TC_OT: "⏰ Overtime",
    TC_MO: "📝 Memos",
    TC_AL: "📋 All",
}
MODE_LABELS = {"upcoming": "📅 Upcoming", "past": "📜 Past", "archive": "📂 Archive"}
MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]

# ── Buttons ────────────────────────────────────────────────────────────────────
def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def br(): return InlineKeyboardButton("↩️ Requests",  callback_data="menu_requests")

# ── Utility helpers ────────────────────────────────────────────────────────────

def _find_ec(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            return r[0].strip(), (r[3].strip() if len(r) > 3 else "Employee")
    return None, "Employee"

def _get_team(ec, role):
    codes = []
    for r in get_sheet("Employee_DB").get_all_records():
        if role == "Supervisor" and str(r.get("Supervisor_Code","")).strip() == str(ec):
            codes.append(str(r.get("Emp_Code","")))
        elif role in ("Direct_Manager","HR_Manager") and str(r.get("Manager_Code","")).strip() == str(ec):
            codes.append(str(r.get("Emp_Code","")))
    return codes

def _allowed_ecs(ec, role):
    """Return frozenset of allowed emp codes, or None meaning all."""
    if role in HR_ALL_ROLES:
        return None
    if role in TEAM_ROLES:
        return frozenset([ec] + _get_team(ec, role))
    return frozenset([ec])

def _parse_date(ds):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(ds.strip()[:10], fmt).date()
        except: pass
    return None

def _ym_key(d):
    return f"{d.year}-{d.month:02d}"

def _ym_label(ym):
    try:
        y, m = ym.split("-")
        return f"{MONTH_NAMES[int(m)-1]} {y}"
    except:
        return ym

def _emp_name(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code","")).strip() == str(ec):
                return r.get("Full_Name", ec)
    except:
        pass
    return ec

def _classify_leave(lt):
    if lt in LEAVE_TYPES: return TC_LV
    if lt in MP_TYPES:    return TC_MP
    if lt in ED_TYPES:    return TC_ED
    if lt in OT_TYPES:    return TC_OT
    return TC_AL

def _status_icon(status):
    s = status.lower()
    if "approved" in s:                         return "✅"
    if "rejected" in s or "declined" in s:      return "❌"
    if "pending" in s or "submitted" in s:      return "⏳"
    return "📋"

# ── Data fetching ──────────────────────────────────────────────────────────────

def _fetch_leave(allowed_ecs):
    try:
        rows = get_sheet("Leave_Log").get_all_values()
        return [
            r for i, r in enumerate(rows)
            if i > 0 and r and r[0].strip()
            and (allowed_ecs is None or r[1].strip() in allowed_ecs)
        ]
    except:
        return []

def _fetch_memos(allowed_ecs):
    try:
        rows = get_sheet("Memo_Log").get_all_values()
        return [
            r for i, r in enumerate(rows)
            if i > 0 and r and r[0].strip()
            and (allowed_ecs is None or (len(r) > 2 and r[2].strip() in allowed_ecs))
        ]
    except:
        return []

def _build_unified(allowed_ecs, mode):
    """Build merged, sorted list of request dicts."""
    today = datetime.now().date()
    items = []

    for r in _fetch_leave(allowed_ecs):
        lt      = r[2].strip() if len(r) > 2 else ""
        start   = _parse_date(r[3]) if len(r) > 3 else None
        end     = _parse_date(r[4]) if len(r) > 4 else None
        status  = r[15].strip() if len(r) > 15 else "Pending"
        ref_d   = start or end or today

        if mode == "upcoming":
            is_pending = status.lower() in ("pending", "submitted", "")
            if not (is_pending or (start and start >= today)):
                continue
        elif mode == "past":
            if not (end and end < today and
                    status.lower() in ("approved", "rejected", "cancelled")):
                continue
        # archive: all rows pass

        items.append({
            "id":        r[0].strip(),
            "type_code": _classify_leave(lt),
            "emp_code":  r[1].strip(),
            "date":      ref_d,
            "ym":        _ym_key(ref_d),
            "status":    status,
            "source":    "leave",
            "row":       r,
        })

    for r in _fetch_memos(allowed_ecs):
        date_str = r[1].strip() if len(r) > 1 else ""
        submitted = _parse_date(date_str) or today
        status    = r[20].strip() if len(r) > 20 else "Submitted"

        if mode == "upcoming":
            if status.lower() in ("director_approved", "approved"):
                continue
        elif mode == "past":
            if status.lower() not in ("director_approved", "approved", "rejected"):
                continue

        items.append({
            "id":        r[0].strip(),
            "type_code": TC_MO,
            "emp_code":  r[2].strip() if len(r) > 2 else "",
            "date":      submitted,
            "ym":        _ym_key(submitted),
            "status":    status,
            "source":    "memo",
            "row":       r,
        })

    items.sort(key=lambda x: x["date"], reverse=True)
    return items

def _item_button(item):
    si = _status_icon(item["status"])
    r  = item["row"]
    if item["source"] == "leave":
        lt    = r[2].strip() if len(r) > 2 else ""
        em    = TYPE_EMOJI.get(lt, "📋")
        start = r[3][:5] if len(r) > 3 else ""
        label = f"{em} {si} {r[0]} | {lt[:10]} | {start}"
        cb    = f"rview_{r[0]}"
    else:
        mid   = r[0]
        topic = (r[6][:20] if len(r) > 6 else "Memo").strip()
        sz    = (r[9].strip() if len(r) > 9 else "") or mid
        label = f"📝 {si} {sz} | {topic}"
        cb    = f"memo_view_{mid}"
    return InlineKeyboardButton(label, callback_data=cb)

# ── Scope helpers ──────────────────────────────────────────────────────────────

def _scope_allowed(ec, role, scope):
    if scope == "all":                      return None
    if scope == "team":                     return frozenset(_get_team(ec, role))
    if role in HR_ALL_ROLES:                return None   # own for HR still = all
    return _allowed_ecs(ec, role)

def _back_cb_for_scope(scope, mode):
    if scope == "team": return "req_team_upcoming"
    if scope == "all":  return "req_all_upcoming"
    return f"req_{mode}"

def _month_prefix(scope, mode):
    if scope == "team": return f"req_tm_{mode}"
    if scope == "all":  return f"req_am_{mode}"
    return f"req_m_{mode}"

def _type_prefix(scope, mode):
    if scope == "team": return f"req_tt_{mode}"
    if scope == "all":  return f"req_at_{mode}"
    return f"req_t_{mode}"

# ── Handlers ───────────────────────────────────────────────────────────────────

async def requests_main_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec(str(q.from_user.id))
    kb = [
        [InlineKeyboardButton("📅 Upcoming Requests", callback_data="req_upcoming")],
        [InlineKeyboardButton("📜 Past Requests",     callback_data="req_past")],
        [InlineKeyboardButton("📂 Requests Archive",  callback_data="req_archive")],
        [InlineKeyboardButton("➕ New Request",        callback_data="req_new")],
        [InlineKeyboardButton("📊 Leave Balance",     callback_data="req_balance")],
    ]
    if role in TEAM_ROLES:
        kb.insert(4, [InlineKeyboardButton("👥 Team Requests",
                                           callback_data="req_team_upcoming")])
    if role in HR_ALL_ROLES:
        kb.insert(4, [InlineKeyboardButton("📑 All Requests",
                                           callback_data="req_all_upcoming")])
    kb.append([bm()])
    await q.edit_message_text("📋 Requests\n\nSelect an option:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def requests_new_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec(str(q.from_user.id))
    kb = [
        [InlineKeyboardButton("🏖️ Leave Request",    callback_data="menu_request_leave")],
        [InlineKeyboardButton("🖐 Missing Punch",     callback_data="menu_missing_punch")],
        [InlineKeyboardButton("📝 Memo / Служебная записка", callback_data="menu_memos")],
    ]
    if role in (TEAM_ROLES | HR_ALL_ROLES):
        kb.append([InlineKeyboardButton("👔 Hiring Request",   callback_data="menu_recruitment")])
        kb.append([InlineKeyboardButton("🛒 Purchase Request", callback_data="menu_supply")])
    kb.append([InlineKeyboardButton("🚗 Vehicle Request", callback_data="menu_vehicles")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_requests"), bm()])
    await q.edit_message_text("➕ New Request — Select Type:",
                              reply_markup=InlineKeyboardMarkup(kb))


async def req_balance_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, _ = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("❌ Not registered.",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return
    try:
        emp = next(
            (r for r in get_sheet("Leave_Balance").get_all_records()
             if str(r.get("Emp_Code","")) == str(ec)), None)
        if not emp:
            await q.edit_message_text("❌ No leave balance record found.",
                reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return
        msg = (
            f"📊 Leave Balance — {emp.get('Full_Name', ec)}\n{'─'*28}\n\n"
            f"✅ Available: {emp.get('Total_Balance_Remaining', 0)} days\n\n{'─'*28}\n"
            f"  🏖️ Paid Used:      {emp.get('Annual_Used', 0)}\n"
            f"  🤒 Sick Used:      {emp.get('Sick_Used', 0)}\n"
            f"  🚨 Emergency Used: {emp.get('Emergency_Used', 0)}\n"
            f"  📋 Unpaid Used:    {emp.get('Unpaid_Used', 0)}\n"
            f"{'─'*28}\nUpdated: {emp.get('Last_Updated', '-')}"
        )
        await q.edit_message_text(msg,
            reply_markup=InlineKeyboardMarkup([[br(), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]]))


async def _month_list(update, context, mode, scope):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec(str(q.from_user.id))
    await q.edit_message_text("⏳ Loading...")
    allowed = _scope_allowed(ec, role, scope)
    try:
        items = _build_unified(allowed, mode)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    if not items:
        label = MODE_LABELS.get(mode, mode)
        await q.edit_message_text(f"ℹ️ No {label.lower()} requests found.",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    ym_counts = {}
    for item in items:
        ym_counts[item["ym"]] = ym_counts.get(item["ym"], 0) + 1

    pfx   = _month_prefix(scope, mode)
    scope_label = " (Team)" if scope == "team" else " (All)" if scope == "all" else ""
    kb = [
        [InlineKeyboardButton(f"{_ym_label(ym)} ({ym_counts[ym]})",
                              callback_data=f"{pfx}_{ym}")]
        for ym in sorted(ym_counts, reverse=True)[:12]
    ]
    kb.append([br(), bm()])
    await q.edit_message_text(
        f"{MODE_LABELS.get(mode, mode)}{scope_label}\n\nSelect month:",
        reply_markup=InlineKeyboardMarkup(kb))


async def req_upcoming_handler(update, context):
    return await _month_list(update, context, "upcoming", "own")

async def req_past_handler(update, context):
    return await _month_list(update, context, "past", "own")

async def req_archive_handler(update, context):
    return await _month_list(update, context, "archive", "own")

async def req_team_upcoming_handler(update, context):
    return await _month_list(update, context, "upcoming", "team")

async def req_all_upcoming_handler(update, context):
    return await _month_list(update, context, "upcoming", "all")


async def _month_detail(update, context, mode, scope, ym):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec(str(q.from_user.id))
    await q.edit_message_text("⏳ Loading...")
    allowed = _scope_allowed(ec, role, scope)
    try:
        all_items = _build_unified(allowed, mode)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    items = [x for x in all_items if x["ym"] == ym]
    if not items:
        await q.edit_message_text("ℹ️ No requests found for this month.",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    type_counts = {}
    for item in items:
        type_counts[item["type_code"]] = type_counts.get(item["type_code"], 0) + 1

    tpfx     = _type_prefix(scope, mode)
    back_cb  = _back_cb_for_scope(scope, mode)
    kb = [[InlineKeyboardButton(f"📋 All ({len(items)})",
                                callback_data=f"{tpfx}_{ym}_al")]]
    for tc, label in TCODE_NAMES.items():
        if tc == TC_AL: continue
        cnt = type_counts.get(tc, 0)
        if cnt > 0:
            kb.append([InlineKeyboardButton(f"{label} ({cnt})",
                                            callback_data=f"{tpfx}_{ym}_{tc}")])
    if mode == "archive":
        kb.append([InlineKeyboardButton("👤 By Submitter",
                                        callback_data=f"req_av_{ym}_sub")])
        kb.append([InlineKeyboardButton("📊 Summary",
                                        callback_data=f"req_av_{ym}_sum")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()])
    await q.edit_message_text(
        f"{MODE_LABELS.get(mode, mode)} — {_ym_label(ym)} ({len(items)} total)\n\nSelect type:",
        reply_markup=InlineKeyboardMarkup(kb))


async def _type_list(update, context, mode, scope, ym, tc):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec(str(q.from_user.id))
    await q.edit_message_text("⏳ Loading...")
    allowed = _scope_allowed(ec, role, scope)
    try:
        all_items = _build_unified(allowed, mode)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    items = [x for x in all_items if x["ym"] == ym]
    if tc != TC_AL:
        items = [x for x in items if x["type_code"] == tc]

    if not items:
        await q.edit_message_text("ℹ️ No requests found.",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return

    back_cb = f"{_month_prefix(scope, mode)}_{ym}"
    kb = [[_item_button(item)] for item in items[:20]]
    if len(items) > 20:
        kb.append([InlineKeyboardButton(f"... +{len(items)-20} more (see archive)",
                                        callback_data="noop_more")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()])
    type_label  = TCODE_NAMES.get(tc, "Requests")
    mode_label  = MODE_LABELS.get(mode, mode)
    await q.edit_message_text(
        f"{type_label} — {_ym_label(ym)}\n{mode_label} ({len(items)} total)\n\nTap to view:",
        reply_markup=InlineKeyboardMarkup(kb))


# ── Route dispatchers ──────────────────────────────────────────────────────────

async def req_month_handler(update, context):
    """Dispatch req_m_{mode}_{ym}, req_tm_{mode}_{ym}, req_am_{mode}_{ym}."""
    data = update.callback_query.data
    if   data.startswith("req_tm_"): scope, rest = "team", data[7:]
    elif data.startswith("req_am_"): scope, rest = "all",  data[7:]
    else:                            scope, rest = "own",  data[6:]   # req_m_
    for mode in ("upcoming", "past", "archive"):
        if rest.startswith(mode + "_"):
            ym = rest[len(mode)+1:]
            return await _month_detail(update, context, mode, scope, ym)


async def req_type_handler(update, context):
    """Dispatch req_t_{mode}_{ym}_{tc}, req_tt_*, req_at_*."""
    data = update.callback_query.data
    if   data.startswith("req_tt_"): scope, rest = "team", data[7:]
    elif data.startswith("req_at_"): scope, rest = "all",  data[7:]
    else:                            scope, rest = "own",  data[6:]   # req_t_
    for mode in ("upcoming", "past", "archive"):
        if rest.startswith(mode + "_"):
            ym_tc = rest[len(mode)+1:]   # "2026-03_lv"
            ym    = ym_tc[:7]            # "2026-03"
            tc    = ym_tc[8:]            # "lv"
            return await _type_list(update, context, mode, scope, ym, tc)


# ── Archive sub-views ──────────────────────────────────────────────────────────

async def req_archive_sub_handler(update, context):
    """req_av_{ym}_{sub}  where sub in (type, sub, sum)."""
    q = update.callback_query; await q.answer()
    rest  = update.callback_query.data[7:]   # strip "req_av_"
    parts = rest.split("_", 1)
    if len(parts) < 2: return
    ym, sub = parts[0], parts[1]

    ec, role = _find_ec(str(q.from_user.id))
    allowed  = _allowed_ecs(ec, role)
    try:
        all_items = _build_unified(allowed, "archive")
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return
    items = [x for x in all_items if x["ym"] == ym]
    back_cb = f"req_m_archive_{ym}"

    if sub == "sum":
        type_counts, status_counts = {}, {}
        for item in items:
            tc = item["type_code"]
            st = item["status"].lower()
            type_counts[tc] = type_counts.get(tc, 0) + 1
            key = f"{tc}__{st}"
            status_counts[key] = status_counts.get(key, 0) + 1
        lines = [f"📊 Summary — {_ym_label(ym)}\n{'─'*28}"]
        for tc, label in TCODE_NAMES.items():
            if tc == TC_AL: continue
            cnt = type_counts.get(tc, 0)
            if cnt == 0: continue
            ap = status_counts.get(f"{tc}__approved", 0)
            pe = (status_counts.get(f"{tc}__pending", 0) +
                  status_counts.get(f"{tc}__submitted", 0))
            rj = status_counts.get(f"{tc}__rejected", 0)
            lines.append(f"{label}: {cnt}  ✅{ap} ⏳{pe} ❌{rj}")
        lines.append(f"{'─'*28}\nTotal: {len(items)} requests")
        await q.edit_message_text("\n".join(lines),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()]]))

    elif sub == "sub":
        submitters = {}
        for item in items:
            ec2 = item["emp_code"]
            submitters[ec2] = submitters.get(ec2, 0) + 1
        kb = []
        for ec2, cnt in sorted(submitters.items(), key=lambda x: -x[1])[:20]:
            name = _emp_name(ec2)
            cb   = f"req_avs_{ym}_{ec2}"
            if len(cb) <= 64:
                kb.append([InlineKeyboardButton(f"👤 {name} ({cnt})", callback_data=cb)])
        kb.append([InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()])
        await q.edit_message_text(
            f"👤 By Submitter — {_ym_label(ym)} ({len(submitters)} people)",
            reply_markup=InlineKeyboardMarkup(kb))

    else:
        return await _month_detail(update, context, "archive", "own", ym)


async def req_archive_person_handler(update, context):
    """req_avs_{ym}_{ec} — show one person's archive items."""
    q = update.callback_query; await q.answer()
    rest      = update.callback_query.data[9:]   # strip "req_avs_"
    ym, p_ec  = rest.split("_", 1)

    ec, role = _find_ec(str(q.from_user.id))
    allowed  = _allowed_ecs(ec, role)
    try:
        all_items = _build_unified(allowed, "archive")
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[br(), bm()]])); return
    items = [x for x in all_items if x["ym"] == ym and x["emp_code"] == p_ec]
    back_cb = f"req_av_{ym}_sub"
    if not items:
        await q.edit_message_text("ℹ️ No requests found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()]])
        ); return
    name = _emp_name(p_ec)
    kb   = [[_item_button(item)] for item in items[:20]]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data=back_cb), bm()])
    await q.edit_message_text(
        f"👤 {name} — {_ym_label(ym)} ({len(items)} requests)",
        reply_markup=InlineKeyboardMarkup(kb))


async def noop_handler(update, context):
    q = update.callback_query; await q.answer("Use archive for full history.")


# ── Handler list ───────────────────────────────────────────────────────────────

def get_requests_handlers():
    return [
        CallbackQueryHandler(requests_main_handler,      pattern="^menu_requests$"),
        CallbackQueryHandler(requests_new_handler,       pattern="^req_new$"),
        CallbackQueryHandler(req_balance_handler,        pattern="^req_balance$"),
        CallbackQueryHandler(req_upcoming_handler,       pattern="^req_upcoming$"),
        CallbackQueryHandler(req_past_handler,           pattern="^req_past$"),
        CallbackQueryHandler(req_archive_handler,        pattern="^req_archive$"),
        CallbackQueryHandler(req_team_upcoming_handler,  pattern="^req_team_upcoming$"),
        CallbackQueryHandler(req_all_upcoming_handler,   pattern="^req_all_upcoming$"),
        CallbackQueryHandler(req_month_handler,
            pattern="^req_(m|tm|am)_(upcoming|past|archive)_"),
        CallbackQueryHandler(req_type_handler,
            pattern="^req_(t|tt|at)_(upcoming|past|archive)_"),
        CallbackQueryHandler(req_archive_sub_handler,    pattern="^req_av_"),
        CallbackQueryHandler(req_archive_person_handler, pattern="^req_avs_"),
        CallbackQueryHandler(noop_handler,               pattern="^noop_"),
    ]
