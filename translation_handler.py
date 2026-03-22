"""
ROIN WORLD FZE — Translation Department Handler
================================================
Rebuilt to match Excel Translation_Log (21 columns).

Flow:
  1. Direct_Manager / Bot_Manager submits text translation request
  2. Translation_Manager reviews, assigns to Translator
  3. Translator types translated text, submits
  4. Translation_Manager reviews → Approve / Request Revision

Excel tab: Translation_Log (21 cols — see TL class)
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet


# ── Back-button helpers ──────────────────────────────────────────────────────
def _bm():  return InlineKeyboardButton("↩️ Main Menu",        callback_data="back_to_menu")
def _btm(): return InlineKeyboardButton("↩️ Translation Menu", callback_data="menu_translation")


# ── Column constants (1-based, matches Excel exactly) ────────────────────────
class TL:
    REQ_ID          = 1
    DATE            = 2
    REQ_CODE        = 3
    REQ_NAME        = 4   # VLOOKUP — write ""
    REQ_DEPT        = 5   # VLOOKUP — write ""
    SOURCE_LANG     = 6
    TARGET_LANG     = 7
    DOC_TYPE        = 8   # we store "Text" here
    DOC_TEXT        = 9   # Original_File_Link — stores the document text
    ASSIGNED_TO     = 10
    TRANSLATOR_NAME = 11  # VLOOKUP — write ""
    ASSIGNED_DATE   = 12
    TRANSLATED_TEXT = 13  # Translated_File_Link — stores the translated text
    TRANSLATION_DATE = 14
    REVIEWER        = 15
    REVIEW_DATE     = 16
    REVIEW_STATUS   = 17
    FINAL_PDF_LINK  = 18
    STATUS          = 19
    NOTES           = 20
    DEADLINE        = 21


# ── Constants ────────────────────────────────────────────────────────────────
LANGUAGES  = ["Arabic", "Russian", "English"]

# Conversation states
ST_SRC      = 1500
ST_TGT      = 1501
ST_TEXT     = 1502
ST_DEADLINE = 1503
ST_CONFIRM  = 1504
ST_ASSIGN   = 1510
ST_TRANS_TEXT = 1520
ST_TRANS_NOTES = 1521
ST_TRANS_CONFIRM = 1522

# AI Translation states (translator)
ST_WORK_CHOICE = 1525
ST_AI_CONTEXT   = 1530
ST_AI_RESULT    = 1531
ST_AI_EDIT      = 1532
ST_AI_INSTRUCT  = 1533

# Manager review states
ST_MGR_REVIEW      = 1540
ST_MGR_AI_INSTRUCT = 1541
ST_MGR_AI_RESULT   = 1542
ST_MGR_AI_EDIT     = 1543
ST_MGR_SENDBACK    = 1545


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_emp_info(tid):
    """Return (emp_code, role) from User_Registry by Telegram ID."""
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0:
            continue
        if r[1].strip() == str(tid):
            return r[0].strip(), r[3].strip() if len(r) > 3 else "Employee"
    return None, None


def _get_emp_name(ec):
    """Return Full_Name for an employee code."""
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r.get("Full_Name", ec)
    except Exception:
        pass
    return str(ec)


def _get_emp_dept(ec):
    """Return Department for an employee code."""
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r.get("Department", "")
    except Exception:
        pass
    return ""


def _gen_tr_id():
    """Generate next Translation request ID: TR-YYYY-NNNN."""
    ids = get_sheet("Translation_Log").col_values(1)
    yr = datetime.now().strftime("%Y")
    px = f"TR-{yr}-"
    mx = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx + 1:04d}"


def _find_request(req_id):
    """Return (row_num_1based, row_list) or (None, None)."""
    try:
        rows = get_sheet("Translation_Log").get_all_values()
        for i, r in enumerate(rows):
            if i == 0:
                continue
            if r[0].strip() == str(req_id):
                return i + 1, r
    except Exception:
        pass
    return None, None


def _update_tl(rn, col, val):
    """Update a single cell in Translation_Log."""
    get_sheet("Translation_Log").update_cell(rn, col, val)


def _get_translators():
    """Return list of active Translator employees."""
    try:
        emps = get_sheet("Employee_DB").get_all_records()
        return [e for e in emps
                if str(e.get("Bot_Role", "")).strip() == "Translator"
                and str(e.get("Status", "")).strip() != "Terminated"]
    except Exception:
        return []


def _status_icon(s):
    return {"Requested": "📩", "Assigned": "👤", "In_Progress": "⚙️",
            "Review": "🔍", "Approved": "✅", "Rejected": "❌"}.get(str(s).strip(), "❓")


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _g(rd, col):
    """Get value from row data by column constant (1-based)."""
    return rd[col - 1].strip() if len(rd) >= col else ""


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════

async def translation_menu_handler(update, context):
    q = update.callback_query
    await q.answer()
    ec, role = _get_emp_info(str(q.from_user.id))

    kb = []

    # Direct_Manager and Bot_Manager can submit requests
    if role in ("Direct_Manager", "Supervisor", "Bot_Manager"):
        kb.append([InlineKeyboardButton("📤 New Translation Request", callback_data="trl_new")])

    # Everyone can see their own requests
    kb.append([InlineKeyboardButton("📋 My Requests", callback_data="trl_my")])

    # Translation_Manager and Bot_Manager see management options
    if role in ("Translation_Manager", "Bot_Manager"):
        kb += [
            [InlineKeyboardButton("📩 Pending Requests",        callback_data="trl_pending")],
            [InlineKeyboardButton("👤 Assign to Translator",    callback_data="trl_assign_list")],
            [InlineKeyboardButton("🔍 Review Completed",        callback_data="trl_review")],
            [InlineKeyboardButton("📂 All Translations",        callback_data="trl_all")],
            [InlineKeyboardButton("📊 Dashboard",               callback_data="trl_dashboard")],
        ]

    # Translator sees their assignments
    if role in ("Translator",):
        kb += [
            [InlineKeyboardButton("📋 My Assignments",   callback_data="trl_my_assign")],
            [InlineKeyboardButton("📊 My Stats",          callback_data="trl_my_stats")],
        ]

    kb.append([_bm()])
    await q.edit_message_text("🌐 Translation Department\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  A. NEW TRANSLATION REQUEST
# ══════════════════════════════════════════════════════════════════════════════

async def trl_new_start(update, context):
    q = update.callback_query
    await q.answer()
    ec, role = _get_emp_info(str(q.from_user.id))
    if role not in ("Direct_Manager", "Supervisor", "Bot_Manager"):
        await q.edit_message_text("❌ Only managers can submit translation requests.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    kb = [[InlineKeyboardButton(lang, callback_data=f"trl_src_{lang}")] for lang in LANGUAGES]
    kb.append([_btm(), _bm()])
    await q.edit_message_text("🌐 New Translation Request\n\n"
                              "Select the SOURCE language (document is written in):",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_SRC


async def trl_src_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["trl_src"] = q.data.replace("trl_src_", "")
    src = context.user_data["trl_src"]
    kb = [[InlineKeyboardButton(lang, callback_data=f"trl_tgt_{lang}")]
          for lang in LANGUAGES if lang != src]
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"✅ Source: {src}\n\n"
                              "Select the TARGET language (translate TO):",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_TGT


async def trl_tgt_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["trl_tgt"] = q.data.replace("trl_tgt_", "")
    await q.edit_message_text(
        f"✅ {context.user_data['trl_src']} → {context.user_data['trl_tgt']}\n\n"
        "Type or paste the text to translate:",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TEXT


async def trl_text_inp(update, context):
    text = update.message.text.strip()
    if len(text) < 3:
        await update.message.reply_text("⚠️ Text too short. Type the text to translate:")
        return ST_TEXT
    context.user_data["trl_text"] = text
    await update.message.reply_text(
        "📅 Enter the deadline (DD/MM/YYYY), or type *urgent* for today:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_DEADLINE


async def trl_deadline_inp(update, context):
    raw = update.message.text.strip().lower()
    if raw == "urgent":
        context.user_data["trl_deadline"] = datetime.now().strftime("%d/%m/%Y")
    else:
        try:
            datetime.strptime(raw, "%d/%m/%Y")
            context.user_data["trl_deadline"] = raw
        except ValueError:
            await update.message.reply_text("⚠️ Use DD/MM/YYYY or type *urgent*:",
                                            parse_mode="Markdown")
            return ST_DEADLINE

    d = context.user_data
    # Truncate text preview to 200 chars
    text_preview = d["trl_text"][:200]
    if len(d["trl_text"]) > 200:
        text_preview += "..."

    summary = (
        f"🌐 *Translation Request Summary*\n"
        f"{'─' * 28}\n"
        f"Source:   {d['trl_src']}\n"
        f"Target:   {d['trl_tgt']}\n"
        f"Deadline: {d['trl_deadline']}\n"
        f"Text:\n{text_preview}"
    )
    kb = [
        [InlineKeyboardButton("✅ Submit", callback_data="trl_confirm_yes"),
         InlineKeyboardButton("❌ Cancel", callback_data="trl_confirm_no")],
        [_btm(), _bm()],
    ]
    await update.message.reply_text(summary, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(kb))
    return ST_CONFIRM


async def trl_confirm(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "trl_confirm_no":
        await q.edit_message_text("❌ Cancelled.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    ec, role = _get_emp_info(str(q.from_user.id))
    d = context.user_data
    now_str = _now()

    try:
        req_id = _gen_tr_id()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    # Build row matching Excel 21 columns
    row = [""] * TL.DEADLINE
    row[TL.REQ_ID - 1]      = req_id
    row[TL.DATE - 1]         = now_str
    row[TL.REQ_CODE - 1]     = ec or ""
    row[TL.REQ_NAME - 1]     = ""           # VLOOKUP
    row[TL.REQ_DEPT - 1]     = ""           # VLOOKUP
    row[TL.SOURCE_LANG - 1]  = d.get("trl_src", "")
    row[TL.TARGET_LANG - 1]  = d.get("trl_tgt", "")
    row[TL.DOC_TYPE - 1]     = "Text"
    row[TL.DOC_TEXT - 1]     = d.get("trl_text", "")
    row[TL.STATUS - 1]       = "Requested"
    row[TL.NOTES - 1]        = ""
    row[TL.DEADLINE - 1]     = d.get("trl_deadline", "")

    try:
        get_sheet("Translation_Log").append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        await q.edit_message_text(f"❌ Could not save: {e}",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    await q.edit_message_text(
        f"✅ Translation request submitted!\n"
        f"🔖 ID: {req_id}\n"
        f"🕐 {now_str}\n"
        f"📅 Deadline: {d.get('trl_deadline', '')}\n\n"
        f"Translation Manager will review and assign.",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ConversationHandler.END


async def trl_cancel(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    elif update.message:
        await update.message.reply_text(
            "❌ Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  B. MY REQUESTS (requester view)
# ══════════════════════════════════════════════════════════════════════════════

async def trl_my_requests(update, context):
    q = update.callback_query
    await q.answer()
    ec, _ = _get_emp_info(str(q.from_user.id))
    try:
        rows = get_sheet("Translation_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    my = [r for i, r in enumerate(rows) if i > 0
          and _g(r, TL.REQ_CODE) == str(ec)]

    if not my:
        await q.edit_message_text("📋 No translation requests yet.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    kb = []
    for r in my[-20:]:
        rid = _g(r, TL.REQ_ID)
        st  = _g(r, TL.STATUS)
        src = _g(r, TL.SOURCE_LANG)[:2]
        tgt = _g(r, TL.TARGET_LANG)[:2]
        dl  = _g(r, TL.DEADLINE)
        label = f"{_status_icon(st)} {rid} | {src}→{tgt} | {dl} | {st}"
        kb.append([InlineKeyboardButton(label, callback_data=f"trl_view_{rid}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"📋 My Translation Requests ({len(my)}):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def trl_view_request(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_view_", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    # Resolve names
    req_name = _g(rd, TL.REQ_NAME) or _get_emp_name(_g(rd, TL.REQ_CODE))
    trans_name = _g(rd, TL.TRANSLATOR_NAME) or (
        _get_emp_name(_g(rd, TL.ASSIGNED_TO)) if _g(rd, TL.ASSIGNED_TO) else "—")

    text_preview = _g(rd, TL.DOC_TEXT)[:300]
    translated = _g(rd, TL.TRANSLATED_TEXT)

    msg = (
        f"🌐 *{_g(rd, TL.REQ_ID)}*\n"
        f"{'─' * 28}\n"
        f"Submitted:  {_g(rd, TL.DATE)}\n"
        f"By:         {req_name} ({_g(rd, TL.REQ_CODE)})\n"
        f"From:       {_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n"
        f"Deadline:   {_g(rd, TL.DEADLINE)}\n"
        f"Status:     {_g(rd, TL.STATUS)}\n"
        f"Translator: {trans_name}\n\n"
        f"📝 Original:\n{text_preview}\n"
    )
    if translated:
        trans_preview = translated[:300]
        msg += f"\n📗 Translation:\n{trans_preview}\n"

    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  C. TRANSLATION MANAGER — Pending + Assign
# ══════════════════════════════════════════════════════════════════════════════

async def trl_pending(update, context):
    """Show unassigned (Requested) translations."""
    q = update.callback_query
    await q.answer()
    try:
        rows = get_sheet("Translation_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    pending = [(i + 1, r) for i, r in enumerate(rows)
               if i > 0 and _g(r, TL.STATUS) == "Requested"]

    if not pending:
        await q.edit_message_text("✅ No pending translation requests.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    kb = []
    for rn, r in pending[-15:]:
        rid = _g(r, TL.REQ_ID)
        src = _g(r, TL.SOURCE_LANG)[:2]
        tgt = _g(r, TL.TARGET_LANG)[:2]
        dl  = _g(r, TL.DEADLINE)
        label = f"📩 {rid} | {src}→{tgt} | DL:{dl}"
        kb.append([InlineKeyboardButton(label, callback_data=f"trl_asgn_{rid}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"📩 Pending Requests ({len(pending)}):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def trl_assign_list(update, context):
    """Same as pending — separate entry point from menu."""
    return await trl_pending(update, context)


async def trl_assign_start(update, context):
    """Show the request + list of translators to assign."""
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_asgn_", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    context.user_data["trl_assign_id"] = req_id
    context.user_data["trl_assign_rn"] = rn

    translators = _get_translators()
    if not translators:
        await q.edit_message_text("❌ No active translators available.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    text_preview = _g(rd, TL.DOC_TEXT)[:150]
    msg = (
        f"📩 *{req_id}*\n"
        f"{'─' * 28}\n"
        f"{_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n"
        f"Deadline: {_g(rd, TL.DEADLINE)}\n"
        f"Text: {text_preview}...\n\n"
        f"Assign to:"
    )
    kb = [[InlineKeyboardButton(
        f"{t.get('Full_Name', '')} [{t.get('Emp_Code', '')}]",
        callback_data=f"trl_to_{t.get('Emp_Code', '')}"
    )] for t in translators[:15]]
    kb.append([_btm(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_ASSIGN


async def trl_assign_confirm(update, context):
    q = update.callback_query
    await q.answer()
    translator_ec = q.data.replace("trl_to_", "")
    req_id = context.user_data.get("trl_assign_id", "")
    rn = context.user_data.get("trl_assign_rn")

    if not rn:
        rn, _ = _find_request(req_id)
    if not rn:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    now_str = _now()
    _update_tl(rn, TL.ASSIGNED_TO,     translator_ec)
    _update_tl(rn, TL.TRANSLATOR_NAME, "")  # VLOOKUP
    _update_tl(rn, TL.ASSIGNED_DATE,   now_str)
    _update_tl(rn, TL.STATUS,          "Assigned")

    trans_name = _get_emp_name(translator_ec)
    await q.edit_message_text(
        f"✅ {req_id} assigned to {trans_name} ({translator_ec})\n{now_str}",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  D. TRANSLATOR — My Assignments + Submit Translation
# ══════════════════════════════════════════════════════════════════════════════

async def trl_my_assignments(update, context):
    q = update.callback_query
    await q.answer()
    ec, _ = _get_emp_info(str(q.from_user.id))
    try:
        rows = get_sheet("Translation_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    mine = [r for i, r in enumerate(rows) if i > 0
            and _g(r, TL.ASSIGNED_TO) == str(ec)
            and _g(r, TL.STATUS) in ("Assigned", "In_Progress")]

    if not mine:
        await q.edit_message_text("📋 No active assignments.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    kb = []
    for r in mine:
        rid = _g(r, TL.REQ_ID)
        src = _g(r, TL.SOURCE_LANG)[:2]
        tgt = _g(r, TL.TARGET_LANG)[:2]
        dl  = _g(r, TL.DEADLINE)
        label = f"📝 {rid} | {src}→{tgt} | DL:{dl}"
        kb.append([InlineKeyboardButton(label, callback_data=f"trl_work_{rid}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"📋 My Assignments ({len(mine)}):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def trl_work_start(update, context):
    """Translator opens a request — choose AI or manual translation."""
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_work_", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    context.user_data["trl_work_id"] = req_id
    context.user_data["trl_work_rn"] = rn

    original = _g(rd, TL.DOC_TEXT)
    preview = original[:500] + ("..." if len(original) > 500 else "")
    msg = (
        f"📋 *Translation Request {req_id}*\n"
        f"{'─' * 28}\n"
        f"Language: {_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n"
        f"Deadline: {_g(rd, TL.DEADLINE)}\n\n"
        f"📄 Original text:\n{preview}"
    )
    kb = []
    import ai_writer
    if ai_writer.ai_available():
        kb.append([InlineKeyboardButton("🤖 Translate with AI",
                                        callback_data=f"trl_aistart_{req_id}")])
    kb.append([InlineKeyboardButton("✍️ Translate Manually",
                                    callback_data=f"trl_manual_{req_id}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_WORK_CHOICE


# ── Translator AI helpers ─────────────────────────────────────────────────────

async def _show_ai_result(update, context, translated):
    """Display AI translation result with action buttons."""
    context.user_data["trl_ai_result"] = translated
    preview = translated[:1500]
    if len(translated) > 1500:
        preview += "\n..."
    msg = (
        f"🤖 *AI Translation Result:*\n"
        f"{'━' * 28}\n\n"
        f"{preview}\n\n"
        f"{'━' * 28}"
    )
    kb = [
        [InlineKeyboardButton("✅ Accept Translation", callback_data="trl_ai_accept")],
        [InlineKeyboardButton("✍️ Edit Translation",   callback_data="trl_ai_edit")],
        [InlineKeyboardButton("💬 Give AI Instructions", callback_data="trl_ai_instr")],
        [InlineKeyboardButton("🔄 Try Again",           callback_data="trl_ai_retry")],
        [InlineKeyboardButton("↩️ Translate Manually",  callback_data="trl_ai_manual")],
        [_btm(), _bm()],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ST_AI_RESULT


async def _do_ai_translate(update, context, ctx_text=""):
    """Call Gemini to translate and show result."""
    import ai_writer
    req_id = context.user_data.get("trl_work_id", "")
    rn, rd = _find_request(req_id)
    if not rd:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        else:
            await update.message.reply_text(
                "❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    original = _g(rd, TL.DOC_TEXT)
    source = _g(rd, TL.SOURCE_LANG)
    target_lang = _g(rd, TL.TARGET_LANG)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing")

    result, err = await ai_writer.translate_with_context(
        original, source, target_lang, ctx_text)
    if err:
        msg = f"❌ AI error: {err}\n\nPlease try again or translate manually."
        kb = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="trl_ai_retry")],
            [InlineKeyboardButton("✍️ Translate Manually", callback_data="trl_ai_manual")],
            [_btm(), _bm()],
        ]
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        return ST_AI_RESULT

    return await _show_ai_result(update, context, result)


async def trl_manual_choice(update, context):
    """Translator chose to translate manually."""
    q = update.callback_query
    await q.answer()
    req_id = context.user_data.get("trl_work_id", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END
    original = _g(rd, TL.DOC_TEXT)
    msg = (
        f"📝 *{req_id}*\n"
        f"{'─' * 28}\n"
        f"{_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n\n"
        f"📄 Original text:\n{original}\n\n"
        f"Type your translation below:"
    )
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TRANS_TEXT


async def trl_ai_choice(update, context):
    """Translator chose AI — ask for context."""
    q = update.callback_query
    await q.answer()
    req_id = context.user_data.get("trl_work_id", "")
    msg = (
        f"🤖 *AI Translation* — {req_id}\n\n"
        f"Describe the context for better translation (optional):\n"
        f"_Example: 'This is a formal HR letter about contract renewal'_\n\n"
        f"Or tap Skip to translate directly."
    )
    kb = [
        [InlineKeyboardButton("⏩ Skip — translate directly",
                              callback_data="trl_ai_skip")],
        [_btm(), _bm()],
    ]
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_AI_CONTEXT


async def trl_ai_skip(update, context):
    """Skip context — translate directly."""
    q = update.callback_query
    await q.answer()
    context.user_data["trl_ai_ctx"] = ""
    return await _do_ai_translate(update, context, "")


async def trl_ai_context_text(update, context):
    """Translator provided context — call AI."""
    ctx = update.message.text.strip()
    context.user_data["trl_ai_ctx"] = ctx
    return await _do_ai_translate(update, context, ctx)


async def trl_ai_accept(update, context):
    """Accept AI translation — save and ask for notes."""
    q = update.callback_query
    await q.answer()
    context.user_data["trl_translated"] = context.user_data.get("trl_ai_result", "")
    await q.edit_message_text(
        "✅ AI translation accepted!\n\n"
        "📝 Any notes for the reviewer? (or type *-* to skip):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TRANS_NOTES


async def trl_ai_edit_start(update, context):
    """Start editing AI translation."""
    q = update.callback_query
    await q.answer()
    ai_text = context.user_data.get("trl_ai_result", "")
    await q.edit_message_text(
        f"✍️ Edit the translation below and send it back:\n\n{ai_text}",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_AI_EDIT


async def trl_ai_edit_text(update, context):
    """Receive edited translation — save and ask for notes."""
    edited = update.message.text.strip()
    if len(edited) < 3:
        await update.message.reply_text("⚠️ Translation too short. Try again:")
        return ST_AI_EDIT
    context.user_data["trl_translated"] = edited
    await update.message.reply_text(
        "✅ Translation saved!\n\n"
        "📝 Any notes for the reviewer? (or type *-* to skip):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TRANS_NOTES


async def trl_ai_instruct_start(update, context):
    """Give AI instructions."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "💬 Type your instructions for the AI:\n"
        "_Example: 'more formal', 'simpler words', 'use Egyptian Arabic'_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_AI_INSTRUCT


async def trl_ai_instruct_text(update, context):
    """Apply AI instructions and show new result."""
    import ai_writer
    instruction = update.message.text.strip()
    current = context.user_data.get("trl_ai_result", "")
    req_id = context.user_data.get("trl_work_id", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await update.message.reply_text("❌ Not found.",
                                         reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    target_lang = _g(rd, TL.TARGET_LANG)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing")

    result, err = await ai_writer.improve_translation(
        current, target_lang, instruction)
    if err:
        await update.message.reply_text(
            f"❌ AI error: {err}\n\nTry again or edit manually.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="trl_ai_retry")],
                [_btm(), _bm()],
            ]))
        return ST_AI_RESULT

    return await _show_ai_result(update, context, result)


async def trl_ai_retry(update, context):
    """Retry AI translation from scratch."""
    q = update.callback_query
    await q.answer()
    return await _do_ai_translate(
        update, context, context.user_data.get("trl_ai_ctx", ""))


async def trl_ai_to_manual(update, context):
    """Fall back to manual translation."""
    q = update.callback_query
    await q.answer()
    req_id = context.user_data.get("trl_work_id", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END
    original = _g(rd, TL.DOC_TEXT)
    msg = (
        f"📝 *{req_id}*\n"
        f"{'─' * 28}\n"
        f"{_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n\n"
        f"📄 Original text:\n{original}\n\n"
        f"Type your translation below:"
    )
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TRANS_TEXT


async def trl_trans_text_inp(update, context):
    text = update.message.text.strip()
    if len(text) < 3:
        await update.message.reply_text("⚠️ Translation too short. Try again:")
        return ST_TRANS_TEXT
    context.user_data["trl_translated"] = text
    await update.message.reply_text(
        "📝 Any notes for the reviewer? (or type *-* to skip):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_TRANS_NOTES


async def trl_trans_notes_inp(update, context):
    notes = update.message.text.strip()
    if notes == "-":
        notes = ""
    context.user_data["trl_trans_notes"] = notes

    req_id = context.user_data.get("trl_work_id", "")
    translated_preview = context.user_data.get("trl_translated", "")[:200]
    summary = (
        f"📤 Submit Translation for {req_id}\n"
        f"{'─' * 28}\n"
        f"Translation: {translated_preview}{'...' if len(context.user_data.get('trl_translated', '')) > 200 else ''}\n"
        f"Notes: {notes or '—'}\n\n"
        f"Confirm?"
    )
    kb = [
        [InlineKeyboardButton("✅ Submit", callback_data="trl_wk_yes"),
         InlineKeyboardButton("❌ Cancel", callback_data="trl_wk_no")],
        [_btm(), _bm()],
    ]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return ST_TRANS_CONFIRM


async def trl_trans_confirm(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "trl_wk_no":
        await q.edit_message_text("❌ Cancelled.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    req_id = context.user_data.get("trl_work_id", "")
    rn = context.user_data.get("trl_work_rn")
    if not rn:
        rn, _ = _find_request(req_id)
    if not rn:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    now_str = _now()
    _update_tl(rn, TL.TRANSLATED_TEXT,   context.user_data.get("trl_translated", ""))
    _update_tl(rn, TL.TRANSLATION_DATE, now_str)
    _update_tl(rn, TL.NOTES,            context.user_data.get("trl_trans_notes", ""))
    _update_tl(rn, TL.STATUS,           "Review")

    await q.edit_message_text(
        f"✅ Translation submitted for {req_id}!\n"
        f"Status: Pending Review by Translation Manager.",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  E. TRANSLATION MANAGER — Review Completed
# ══════════════════════════════════════════════════════════════════════════════

async def trl_review(update, context):
    q = update.callback_query
    await q.answer()
    try:
        rows = get_sheet("Translation_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    pending = [r for i, r in enumerate(rows) if i > 0 and _g(r, TL.STATUS) == "Review"]
    if not pending:
        await q.edit_message_text("✅ No translations pending review.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    kb = []
    for r in pending[-15:]:
        rid = _g(r, TL.REQ_ID)
        src = _g(r, TL.SOURCE_LANG)[:2]
        tgt = _g(r, TL.TARGET_LANG)[:2]
        label = f"🔍 {rid} | {src}→{tgt}"
        kb.append([InlineKeyboardButton(label, callback_data=f"trl_rv_{rid}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"🔍 Pending Review ({len(pending)}):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def trl_review_detail(update, context):
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_rv_", "")
    rn, rd = _find_request(req_id)
    if not rd:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return ConversationHandler.END

    context.user_data["trl_rv_id"] = req_id
    context.user_data["trl_rv_rn"] = rn

    original = _g(rd, TL.DOC_TEXT)[:300]
    translated = _g(rd, TL.TRANSLATED_TEXT)[:300]
    notes = _g(rd, TL.NOTES)
    trans_name = _g(rd, TL.TRANSLATOR_NAME) or _get_emp_name(_g(rd, TL.ASSIGNED_TO))

    msg = (
        f"🔍 *Review — {req_id}*\n"
        f"{'─' * 28}\n"
        f"Translator: {trans_name}\n"
        f"{_g(rd, TL.SOURCE_LANG)} → {_g(rd, TL.TARGET_LANG)}\n\n"
        f"📄 Original:\n{original}\n\n"
        f"📗 Translation:\n{translated}\n"
    )
    if notes:
        msg += f"\n📝 Notes: {notes}\n"

    kb = []
    import ai_writer
    if ai_writer.ai_available():
        kb.append([InlineKeyboardButton("🤖 Improve with AI",
                                        callback_data=f"trl_mgr_ai_{req_id}")])
    kb.append([InlineKeyboardButton("✅ Approve",
                                    callback_data=f"trl_approve_{req_id}")])
    kb.append([InlineKeyboardButton("📝 Send Back to Translator",
                                    callback_data=f"trl_sendback_{req_id}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_MGR_REVIEW


async def trl_approve_conv(update, context):
    """Approve translation from review ConversationHandler."""
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_approve_", "")
    ec, _ = _get_emp_info(str(q.from_user.id))
    rn, _ = _find_request(req_id)
    if not rn:
        await q.edit_message_text("❌ Not found.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    now_str = _now()
    _update_tl(rn, TL.REVIEWER,      ec or "")
    _update_tl(rn, TL.REVIEW_DATE,   now_str)
    _update_tl(rn, TL.REVIEW_STATUS, "Approved")
    _update_tl(rn, TL.STATUS,        "Approved")

    await q.edit_message_text(
        f"✅ {req_id} approved! Translation complete.",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ConversationHandler.END


# ── Manager AI + Send-Back handlers ──────────────────────────────────────────

async def _show_mgr_ai_result(update, context, improved):
    """Show AI improvement result with action buttons."""
    context.user_data["trl_mgr_ai_text"] = improved
    preview = improved[:1500]
    if len(improved) > 1500:
        preview += "\n..."
    msg = (
        f"🤖 *AI Improved Translation:*\n"
        f"{'━' * 28}\n\n"
        f"{preview}\n\n"
        f"{'━' * 28}"
    )
    kb = [
        [InlineKeyboardButton("✅ Use This",           callback_data="trl_mgr_ai_use")],
        [InlineKeyboardButton("✍️ Edit",               callback_data="trl_mgr_ai_edit")],
        [InlineKeyboardButton("💬 Give Instructions",  callback_data="trl_mgr_ai_instr")],
        [InlineKeyboardButton("🔄 Try Again",          callback_data="trl_mgr_ai_retry")],
        [InlineKeyboardButton("↩️ Keep Original",      callback_data="trl_mgr_ai_keep")],
        [_btm(), _bm()],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return ST_MGR_AI_RESULT


async def _do_mgr_ai(update, context, instruction=""):
    """Call AI to improve translation and show result."""
    import ai_writer
    req_id = context.user_data.get("trl_mgr_ai_id", "")
    rn, rd = _find_request(req_id)
    if not rd:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        else:
            await update.message.reply_text(
                "❌ Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    translated = _g(rd, TL.TRANSLATED_TEXT)
    target_lang = _g(rd, TL.TARGET_LANG)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing")

    result, err = await ai_writer.improve_translation(
        translated, target_lang, instruction)
    if err:
        msg = f"❌ AI error: {err}\n\nPlease try again or keep original."
        kb = [
            [InlineKeyboardButton("🔄 Try Again",     callback_data="trl_mgr_ai_retry")],
            [InlineKeyboardButton("↩️ Keep Original", callback_data="trl_mgr_ai_keep")],
            [_btm(), _bm()],
        ]
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        return ST_MGR_AI_RESULT

    return await _show_mgr_ai_result(update, context, result)


async def trl_mgr_ai_start(update, context):
    """Manager chose Improve with AI — ask for instructions."""
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_mgr_ai_", "")
    context.user_data["trl_mgr_ai_id"] = req_id
    msg = (
        f"🤖 *Improve Translation* — {req_id}\n\n"
        f"Give specific instructions (optional):\n"
        f"_Example: 'more formal', 'simpler words', 'use Egyptian dialect'_\n\n"
        f"Or tap Skip to improve automatically."
    )
    kb = [
        [InlineKeyboardButton("⏩ Skip — improve automatically",
                              callback_data="trl_mgr_ai_skip")],
        [_btm(), _bm()],
    ]
    await q.edit_message_text(msg, parse_mode="Markdown",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_MGR_AI_INSTRUCT


async def trl_mgr_ai_skip(update, context):
    """Skip instructions — improve directly."""
    q = update.callback_query
    await q.answer()
    return await _do_mgr_ai(update, context, "")


async def trl_mgr_ai_instruct_text(update, context):
    """Manager provided instructions — call AI."""
    instruction = update.message.text.strip()
    return await _do_mgr_ai(update, context, instruction)


async def trl_mgr_ai_use(update, context):
    """Use AI improvement — save to sheet."""
    q = update.callback_query
    await q.answer()
    req_id = context.user_data.get("trl_mgr_ai_id", "")
    improved = context.user_data.get("trl_mgr_ai_text", "")
    rn, _ = _find_request(req_id)
    if rn and improved:
        _update_tl(rn, TL.TRANSLATED_TEXT, improved)
    await q.edit_message_text(
        f"✅ Translation updated for {req_id}.\n"
        f"Return to review to approve or continue editing.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Review Again",
                                  callback_data=f"trl_rv_{req_id}")],
            [_btm()],
        ]))
    return ConversationHandler.END


async def trl_mgr_ai_edit_start(update, context):
    """Start editing AI improvement."""
    q = update.callback_query
    await q.answer()
    ai_text = context.user_data.get("trl_mgr_ai_text", "")
    await q.edit_message_text(
        f"✍️ Edit the improved translation and send it back:\n\n{ai_text}",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_MGR_AI_EDIT


async def trl_mgr_ai_edit_text(update, context):
    """Receive edited text — save to sheet."""
    edited = update.message.text.strip()
    req_id = context.user_data.get("trl_mgr_ai_id", "")
    rn, _ = _find_request(req_id)
    if rn and edited:
        _update_tl(rn, TL.TRANSLATED_TEXT, edited)
    await update.message.reply_text(
        f"✅ Translation updated for {req_id}.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Review Again",
                                  callback_data=f"trl_rv_{req_id}")],
            [_btm()],
        ]))
    return ConversationHandler.END


async def trl_mgr_ai_instr_start(update, context):
    """Give more AI instructions."""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "💬 Type your instructions for the AI:\n"
        "_Example: 'more formal', 'simpler words'_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_MGR_AI_INSTRUCT


async def trl_mgr_ai_retry(update, context):
    """Retry AI improvement."""
    q = update.callback_query
    await q.answer()
    return await _do_mgr_ai(update, context, "")


async def trl_mgr_ai_keep(update, context):
    """Keep original — return to review."""
    q = update.callback_query
    await q.answer()
    req_id = context.user_data.get("trl_mgr_ai_id", "")
    await q.edit_message_text(
        f"↩️ Keeping original translation for {req_id}.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Back to Review",
                                  callback_data=f"trl_rv_{req_id}")],
            [_btm()],
        ]))
    return ConversationHandler.END


async def trl_sendback_start(update, context):
    """Manager sends back to translator — ask for feedback."""
    q = update.callback_query
    await q.answer()
    req_id = q.data.replace("trl_sendback_", "")
    context.user_data["trl_sendback_id"] = req_id
    await q.edit_message_text(
        f"📝 *Send Back — {req_id}*\n\n"
        f"Type your feedback for the translator:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ST_MGR_SENDBACK


async def trl_sendback_text(update, context):
    """Manager typed feedback — save and send back."""
    feedback = update.message.text.strip()
    if len(feedback) < 2:
        await update.message.reply_text("⚠️ Please type your feedback:")
        return ST_MGR_SENDBACK

    req_id = context.user_data.get("trl_sendback_id", "")
    rn, _ = _find_request(req_id)
    if not rn:
        await update.message.reply_text("❌ Not found.",
                                         reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    ec, _ = _get_emp_info(str(update.effective_user.id))
    now_str = _now()
    _update_tl(rn, TL.REVIEWER,      ec or "")
    _update_tl(rn, TL.REVIEW_DATE,   now_str)
    _update_tl(rn, TL.REVIEW_STATUS, "Revision")
    _update_tl(rn, TL.STATUS,        "Assigned")
    _update_tl(rn, TL.NOTES,         f"Manager feedback: {feedback}")

    await update.message.reply_text(
        f"🔄 {req_id} sent back to translator.\n"
        f"📝 Feedback: {feedback}",
        reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  F. ALL TRANSLATIONS + DASHBOARD + STATS
# ══════════════════════════════════════════════════════════════════════════════

async def trl_all_handler(update, context):
    q = update.callback_query
    await q.answer()
    try:
        rows = get_sheet("Translation_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    data_rows = [r for i, r in enumerate(rows) if i > 0 and _g(r, TL.REQ_ID)]
    if not data_rows:
        await q.edit_message_text("📋 No translations yet.",
                                  reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))
        return

    kb = []
    for r in data_rows[-20:]:
        rid = _g(r, TL.REQ_ID)
        st  = _g(r, TL.STATUS)
        src = _g(r, TL.SOURCE_LANG)[:2]
        tgt = _g(r, TL.TARGET_LANG)[:2]
        label = f"{_status_icon(st)} {rid} | {src}→{tgt} | {st}"
        kb.append([InlineKeyboardButton(label, callback_data=f"trl_view_{rid}")])
    kb.append([_btm(), _bm()])
    await q.edit_message_text(f"📂 All Translations ({len(data_rows)}):",
                              reply_markup=InlineKeyboardMarkup(kb))


async def trl_dashboard(update, context):
    q = update.callback_query
    await q.answer()
    try:
        rows = get_sheet("Translation_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    total    = len(rows)
    requested = sum(1 for r in rows if str(r.get("Status", "")) == "Requested")
    assigned  = sum(1 for r in rows if str(r.get("Status", "")) == "Assigned")
    in_prog   = sum(1 for r in rows if str(r.get("Status", "")) == "In_Progress")
    review    = sum(1 for r in rows if str(r.get("Status", "")) == "Review")
    approved  = sum(1 for r in rows if str(r.get("Status", "")) == "Approved")
    translators = _get_translators()

    msg = (
        f"📊 Translation Dashboard\n"
        f"{'─' * 28}\n"
        f"Total requests:     {total}\n"
        f"📩 Unassigned:       {requested}\n"
        f"👤 Assigned:         {assigned}\n"
        f"⚙️ In Progress:      {in_prog}\n"
        f"🔍 Pending Review:   {review}\n"
        f"✅ Approved:          {approved}\n"
        f"{'─' * 28}\n"
        f"Active translators: {len(translators)}"
    )
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))


async def trl_my_stats(update, context):
    q = update.callback_query
    await q.answer()
    ec, _ = _get_emp_info(str(q.from_user.id))
    try:
        rows = get_sheet("Translation_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    mine   = [r for r in rows if str(r.get("Assigned_To", "")).strip() == str(ec)]
    done   = sum(1 for r in mine if str(r.get("Status", "")) == "Approved")
    active = sum(1 for r in mine if str(r.get("Status", "")) in ("Assigned", "In_Progress"))
    review = sum(1 for r in mine if str(r.get("Status", "")) == "Review")

    msg = (
        f"📊 My Translation Stats\n"
        f"{'─' * 24}\n"
        f"Total assigned:    {len(mine)}\n"
        f"✅ Completed:       {done}\n"
        f"⚙️ Active:          {active}\n"
        f"🔍 Awaiting review: {review}"
    )
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_btm(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_translation_handlers():
    """Return ConversationHandlers."""
    # New request flow
    request_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(trl_new_start, pattern="^trl_new$")],
        states={
            ST_SRC:      [CallbackQueryHandler(trl_src_cb,      pattern="^trl_src_")],
            ST_TGT:      [CallbackQueryHandler(trl_tgt_cb,      pattern="^trl_tgt_")],
            ST_TEXT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, trl_text_inp)],
            ST_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, trl_deadline_inp)],
            ST_CONFIRM:  [CallbackQueryHandler(trl_confirm,     pattern="^trl_confirm_")],
        },
        fallbacks=[
            CallbackQueryHandler(trl_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(trl_cancel, pattern="^menu_translation$"),
        ],
        allow_reentry=True,
    )

    # Assign flow
    assign_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(trl_assign_start, pattern="^trl_asgn_")],
        states={
            ST_ASSIGN: [CallbackQueryHandler(trl_assign_confirm, pattern="^trl_to_")],
        },
        fallbacks=[
            CallbackQueryHandler(trl_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(trl_cancel, pattern="^menu_translation$"),
        ],
        allow_reentry=True,
    )

    # Translator work flow (with AI translation option)
    work_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(trl_work_start, pattern="^trl_work_")],
        states={
            ST_WORK_CHOICE: [
                CallbackQueryHandler(trl_manual_choice, pattern="^trl_manual_"),
                CallbackQueryHandler(trl_ai_choice,     pattern="^trl_aistart_"),
            ],
            ST_AI_CONTEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_ai_context_text),
                CallbackQueryHandler(trl_ai_skip, pattern="^trl_ai_skip$"),
            ],
            ST_AI_RESULT: [
                CallbackQueryHandler(trl_ai_accept,         pattern="^trl_ai_accept$"),
                CallbackQueryHandler(trl_ai_edit_start,     pattern="^trl_ai_edit$"),
                CallbackQueryHandler(trl_ai_instruct_start, pattern="^trl_ai_instr$"),
                CallbackQueryHandler(trl_ai_retry,          pattern="^trl_ai_retry$"),
                CallbackQueryHandler(trl_ai_to_manual,      pattern="^trl_ai_manual$"),
            ],
            ST_AI_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_ai_edit_text),
            ],
            ST_AI_INSTRUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_ai_instruct_text),
            ],
            ST_TRANS_TEXT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, trl_trans_text_inp)],
            ST_TRANS_NOTES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, trl_trans_notes_inp)],
            ST_TRANS_CONFIRM:[CallbackQueryHandler(trl_trans_confirm, pattern="^trl_wk_")],
        },
        fallbacks=[
            CallbackQueryHandler(trl_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(trl_cancel, pattern="^menu_translation$"),
        ],
        allow_reentry=True,
    )

    # Manager review flow (with AI improvement + send-back)
    review_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(trl_review_detail, pattern="^trl_rv_")],
        states={
            ST_MGR_REVIEW: [
                CallbackQueryHandler(trl_approve_conv,   pattern="^trl_approve_"),
                CallbackQueryHandler(trl_mgr_ai_start,   pattern="^trl_mgr_ai_"),
                CallbackQueryHandler(trl_sendback_start,  pattern="^trl_sendback_"),
            ],
            ST_MGR_AI_INSTRUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_mgr_ai_instruct_text),
                CallbackQueryHandler(trl_mgr_ai_skip, pattern="^trl_mgr_ai_skip$"),
            ],
            ST_MGR_AI_RESULT: [
                CallbackQueryHandler(trl_mgr_ai_use,        pattern="^trl_mgr_ai_use$"),
                CallbackQueryHandler(trl_mgr_ai_edit_start, pattern="^trl_mgr_ai_edit$"),
                CallbackQueryHandler(trl_mgr_ai_instr_start, pattern="^trl_mgr_ai_instr$"),
                CallbackQueryHandler(trl_mgr_ai_retry,      pattern="^trl_mgr_ai_retry$"),
                CallbackQueryHandler(trl_mgr_ai_keep,       pattern="^trl_mgr_ai_keep$"),
            ],
            ST_MGR_AI_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_mgr_ai_edit_text),
            ],
            ST_MGR_SENDBACK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, trl_sendback_text),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(trl_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(trl_cancel, pattern="^menu_translation$"),
        ],
        allow_reentry=True,
    )

    return [request_conv, assign_conv, work_conv, review_conv]


def get_translation_static_handlers():
    """Return static CallbackQueryHandlers."""
    from telegram.ext import CallbackQueryHandler as CQH
    return [
        CQH(translation_menu_handler,  pattern="^menu_translation$"),
        CQH(trl_my_requests,           pattern="^trl_my$"),
        CQH(trl_view_request,          pattern="^trl_view_"),
        CQH(trl_pending,               pattern="^trl_pending$"),
        CQH(trl_assign_list,           pattern="^trl_assign_list$"),
        CQH(trl_my_assignments,        pattern="^trl_my_assign$"),
        CQH(trl_review,                pattern="^trl_review$"),
        CQH(trl_all_handler,           pattern="^trl_all$"),
        CQH(trl_dashboard,             pattern="^trl_dashboard$"),
        CQH(trl_my_stats,              pattern="^trl_my_stats$"),
    ]
