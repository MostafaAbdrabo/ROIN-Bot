"""
ROIN WORLD FZE — Missing Punch Request Handler
================================================
Employee forgot to punch IN or OUT.
Request_Type : "Missing_Punch"
Request_ID   : MP-YYYY-NNNN
Approval     : follows employee's Approval_Chain (MGR_HR or MGR_HR_DIR)
Attendance   : approved + partial punch → P  (integration in attendance_handler.py)
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from config import get_sheet

# ── State constants ──────────────────────────────────────────────────────────
MP_TYPE    = 150
MP_DATE    = 151
MP_REASON  = 152
MP_CONFIRM = 153

# ── Helpers ──────────────────────────────────────────────────────────────────
def bm():  return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bbt(): return InlineKeyboardButton("↩️ Back",      callback_data="mp_back_to_type")

def _get_menu(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            from bot import build_inline_menu
            return build_inline_menu(r[3].strip() if len(r) > 3 else "Employee")
    from bot import build_inline_menu
    return build_inline_menu("Employee")

def _find_ec(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None

def _emp_name(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code", "")) == str(ec):
            return r.get("Full_Name", ec)
    return str(ec)

def gen_mp_id():
    ids = get_sheet("Leave_Log").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"MP-{yr}-"
    mx  = 0
    for r in ids:
        if str(r).startswith(px):
            try: n = int(str(r).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"

def write_mp_req(ec, punch_type, date_str, reason):
    from approval_handler import get_approval_chain
    ws    = get_sheet("Leave_Log")
    rid   = gen_mp_id()
    now   = datetime.now().strftime("%d/%m/%Y %H:%M")
    chain = get_approval_chain(ec, "Missing_Punch")
    ss    = ["NA", "NA", "NA"]
    for i in range(len(chain)): ss[i] = "Pending"
    full_reason = f"[{punch_type}] {reason}"
    row = [rid, str(ec), "Missing_Punch",
           date_str, date_str, "1",
           "", "", full_reason,
           ss[0], "", ss[1], "", ss[2], "",
           "Pending", "", "", "", "No", "", now]
    ws.append_row(row, value_input_option="USER_ENTERED")
    return rid, now


# ── Type selection ────────────────────────────────────────────────────────────
async def mp_start(update, context):
    q  = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("❌ Not registered.",
            reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    context.user_data["mp_ec"] = ec
    kb = [
        [InlineKeyboardButton("🔑 Missing Check-IN",     callback_data="mp_type_IN")],
        [InlineKeyboardButton("🔒 Missing Check-OUT",    callback_data="mp_type_OUT")],
        [InlineKeyboardButton("🔑🔒 Both IN and OUT",    callback_data="mp_type_Both")],
        [InlineKeyboardButton("↩️ Back", callback_data="back_to_menu"), bm()],
    ]
    await q.edit_message_text(
        "🖐 Missing Punch Request\n\nWhat was missing?",
        reply_markup=InlineKeyboardMarkup(kb))
    return MP_TYPE


async def mp_type_sel(update, context):
    q  = update.callback_query; await q.answer()
    pt = q.data.replace("mp_type_", "")
    context.user_data["mp_punch_type"] = pt
    today     = datetime.now().date()
    yesterday = today - timedelta(days=1)
    kb = [
        [InlineKeyboardButton(
            f"📅 Today ({today.strftime('%d/%m/%Y')})",
            callback_data=f"mp_date_{today.strftime('%d/%m/%Y')}")],
        [InlineKeyboardButton(
            f"📅 Yesterday ({yesterday.strftime('%d/%m/%Y')})",
            callback_data=f"mp_date_{yesterday.strftime('%d/%m/%Y')}")],
        [bbt(), bm()],
    ]
    await q.edit_message_text(
        f"🖐 Missing {pt} Punch\n\nSelect the date:",
        reply_markup=InlineKeyboardMarkup(kb))
    return MP_DATE


# ── Date selection ────────────────────────────────────────────────────────────
async def mp_date_sel(update, context):
    q  = update.callback_query; await q.answer()
    ds = q.data.replace("mp_date_", "")
    context.user_data["mp_date"] = ds
    await q.edit_message_text(
        f"🖐 Date: {ds}\n\nType your reason:",
        reply_markup=InlineKeyboardMarkup([[bbt(), bm()]]))
    return MP_REASON


# ── Reason (text) ─────────────────────────────────────────────────────────────
async def mp_reason_inp(update, context):
    r  = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bbt(), bm()]])
    if len(r) < 3:
        await update.message.reply_text("⚠️ Please type a longer reason:", reply_markup=bk)
        return MP_REASON
    context.user_data["mp_reason"] = r
    ec = context.user_data["mp_ec"]
    pt = context.user_data["mp_punch_type"]
    ds = context.user_data["mp_date"]
    nm = _emp_name(ec)
    from approval_handler import get_approval_chain, ROLE_LABELS
    chain = get_approval_chain(ec, "Missing_Punch")
    ct    = " → ".join(ROLE_LABELS.get(s, s) for s in chain)
    msg = (f"🖐 Missing Punch — Summary\n{'─'*28}\n"
           f"👤 {nm} ({ec})\n"
           f"Type:   {pt}\n"
           f"Date:   {ds}\n"
           f"Reason: {r}\n"
           f"Chain:  {ct}\n"
           f"{'─'*28}\n\nConfirm submission?")
    kb = [
        [InlineKeyboardButton("✅ Submit",  callback_data="mp_yes"),
         InlineKeyboardButton("❌ Cancel",  callback_data="mp_no")],
        [bbt(), bm()],
    ]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return MP_CONFIRM


# ── Confirmation ──────────────────────────────────────────────────────────────
async def mp_confirmed(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "mp_no":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return ConversationHandler.END
    ec     = context.user_data["mp_ec"]
    pt     = context.user_data["mp_punch_type"]
    ds     = context.user_data["mp_date"]
    reason = context.user_data["mp_reason"]
    try:
        rid, sub = write_mp_req(ec, pt, ds, reason)
        await q.edit_message_text(
            f"✅ Missing Punch submitted!\n"
            f"ID: {rid}\nDate: {ds}\nSubmitted: {sub}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


# ── Back to type selection ────────────────────────────────────────────────────
async def mp_back_to_type(update, context):
    return await mp_start(update, context)


async def mp_back_to_menu(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("Choose an option:", reply_markup=_get_menu(str(q.from_user.id)))
    return ConversationHandler.END


async def mp_cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── ConversationHandler builder ───────────────────────────────────────────────
def get_missing_punch_handler():
    back_handlers = [
        CallbackQueryHandler(mp_back_to_type, pattern="^mp_back_to_type$"),
        CallbackQueryHandler(mp_back_to_menu, pattern="^back_to_menu$"),
    ]
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(mp_start, pattern="^menu_missing_punch$")],
        states={
            MP_TYPE: [
                CallbackQueryHandler(mp_type_sel,    pattern="^mp_type_"),
                CallbackQueryHandler(mp_back_to_menu, pattern="^back_to_menu$"),
            ],
            MP_DATE: [
                CallbackQueryHandler(mp_date_sel,    pattern="^mp_date_"),
                *back_handlers,
            ],
            MP_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, mp_reason_inp),
                *back_handlers,
            ],
            MP_CONFIRM: [
                CallbackQueryHandler(mp_confirmed,   pattern="^mp_(yes|no)$"),
                *back_handlers,
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, mp_cancel)],
        per_message=False,
    )
