"""
ROIN WORLD FZE — Bot Feedback System
======================================
Section C of SCHEDULE_FEEDBACK_PROMPT.md

ANY employee can submit: Bug Report / Suggestion / Question / Complaint
Bot_Manager sees and responds to all feedback.

Sheet tab: Bot_Feedback
Columns: Ticket_ID, Date, Emp_Code, Emp_Name(VLOOKUP), Department(VLOOKUP),
         Type, Subject, Description, Photos, Status, Response, Response_Date, Responded_By
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

# ── Helpers ──────────────────────────────────────────────────────────────────
def _bm():  return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _bfb(): return InlineKeyboardButton("↩️ Feedback",  callback_data="menu_bot_feedback")

# States
FB_TYPE    = 2100
FB_SUBJECT = 2101
FB_DESC    = 2102
FB_PHOTOS  = 2103
FB_CONFIRM = 2104
FB_RESP    = 2110

TICKET_TYPES = {
    "bug":        ("🐛 Bug Report",    "BUG"),
    "suggestion": ("💡 Suggestion",    "SUG"),
    "question":   ("❓ Question",      "QST"),
    "complaint":  ("😤 Complaint",     "CMP"),
}

STATUS_OPTIONS = ["Open", "In_Progress", "Resolved", "Closed"]
STATUS_ICON = {
    "Open": "🔴", "In_Progress": "⚙️", "Resolved": "✅", "Closed": "🔒"
}

MGR_ROLES = {"Bot_Manager"}


def _get_user(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            ec   = r[0].strip()
            role = r[3].strip() if len(r) > 3 else "Employee"
            return ec, role
    return None, "Employee"


def _gen_ticket_id(prefix):
    ids = get_sheet("Bot_Feedback").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"{prefix}-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: mx = max(mx, int(str(v).split("-")[-1]))
            except: pass
    return f"{px}{mx+1:04d}"


# ══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE — SUBMIT FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════
async def fb_menu_start(update, context):
    """Entry point — accessible from every role's menu."""
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🐛 Bug Report",  callback_data="fb_type_bug")],
        [InlineKeyboardButton("💡 Suggestion",  callback_data="fb_type_suggestion")],
        [InlineKeyboardButton("❓ Question",     callback_data="fb_type_question")],
        [InlineKeyboardButton("😤 Complaint",   callback_data="fb_type_complaint")],
        [_bm()],
    ])
    await q.edit_message_text(
        "📬 Bot Feedback\n\nHelp us improve the bot!\nSelect feedback type:",
        reply_markup=kb)
    return FB_TYPE


async def fb_type_cb(update, context):
    q = update.callback_query; await q.answer()
    key = q.data.replace("fb_type_","")
    label, prefix = TICKET_TYPES.get(key, ("Feedback", "SUG"))
    context.user_data["fb_type"]   = key
    context.user_data["fb_prefix"] = prefix
    context.user_data["fb_label"]  = label
    await q.edit_message_text(
        f"{label}\n\nEnter a short subject (5–80 characters):",
        reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return FB_SUBJECT


async def fb_subject_inp(update, context):
    text = update.message.text.strip()
    if len(text) < 5:
        await update.message.reply_text("⚠️ Too short. Enter at least 5 characters:",
                                        reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return FB_SUBJECT
    if len(text) > 80:
        await update.message.reply_text("⚠️ Too long. Max 80 characters:",
                                        reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return FB_SUBJECT
    context.user_data["fb_subject"] = text
    await update.message.reply_text(
        f"Subject: {text}\n\nNow describe the issue in detail (10–1000 characters):",
        reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return FB_DESC


async def fb_desc_inp(update, context):
    text = update.message.text.strip()
    if len(text) < 10:
        await update.message.reply_text("⚠️ Too short. Please give more detail:",
                                        reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return FB_DESC
    context.user_data["fb_desc"]   = text
    context.user_data["fb_photos"] = []
    await update.message.reply_text(
        "📸 Optional: Send up to 3 screenshots (photos).\n\n"
        "Tap 'Skip' to submit without photos.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Skip Photos", callback_data="fb_skip_photos")],
            [_bm()],
        ]))
    return FB_PHOTOS


async def fb_photo_inp(update, context):
    """Receive up to 3 photos."""
    photos = context.user_data.get("fb_photos", [])
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        photos.append(file_id)
        context.user_data["fb_photos"] = photos
        count = len(photos)
        if count >= 3:
            return await _show_fb_summary(update, context, use_message=True)
        await update.message.reply_text(
            f"✅ Photo {count}/3 received.\nSend another or tap 'Done'.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done — Submit", callback_data="fb_skip_photos")],
                [_bm()],
            ]))
        return FB_PHOTOS
    await update.message.reply_text(
        "⚠️ Please send a photo (screenshot).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ Skip Photos", callback_data="fb_skip_photos")],
            [_bm()],
        ]))
    return FB_PHOTOS


async def fb_skip_photos_cb(update, context):
    q = update.callback_query; await q.answer()
    return await _show_fb_summary(update, context, use_message=False)


async def _show_fb_summary(update, context, use_message=False):
    label   = context.user_data.get("fb_label","Feedback")
    subject = context.user_data.get("fb_subject","")
    desc    = context.user_data.get("fb_desc","")
    photos  = context.user_data.get("fb_photos",[])
    summary = (f"📬 {label}\n{'─'*24}\n"
               f"Subject: {subject}\n"
               f"Description: {desc[:200]}{'...' if len(desc)>200 else ''}\n"
               f"Photos: {len(photos)}\n\n"
               "Submit this feedback?")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="fb_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="fb_cancel")],
          [_bm()]]
    if use_message:
        await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return FB_CONFIRM


async def fb_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "fb_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec, role = _get_user(str(q.from_user.id))
    prefix  = context.user_data.get("fb_prefix","SUG")
    label   = context.user_data.get("fb_label","Feedback")
    subject = context.user_data.get("fb_subject","")
    desc    = context.user_data.get("fb_desc","")
    photos  = context.user_data.get("fb_photos",[])
    photos_str = "|".join(photos)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        tid = _gen_ticket_id(prefix)
        # Bot_Feedback cols: Ticket_ID, Date, Emp_Code, Emp_Name(VLOOKUP), Department(VLOOKUP),
        #                    Type, Subject, Description, Photos, Status, Response, Response_Date, Responded_By
        row = [tid, now, ec or "", "", "",
               label, subject, desc, photos_str,
               "Open", "", "", ""]
        get_sheet("Bot_Feedback").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Feedback submitted!\nTicket ID: {tid}\n"
            f"Type: {label}\nStatus: Open\n\n"
            "The Bot Manager will review and respond.",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def fb_cancel_cmd(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  BOT_MANAGER — FEEDBACK DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
async def fb_dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    await q.edit_message_text("⏳ Loading feedback...")
    try:
        rows = get_sheet("Bot_Feedback").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    now = datetime.now()
    total      = len(rows)
    open_t     = sum(1 for r in rows if str(r.get("Status","")).strip() == "Open")
    in_prog    = sum(1 for r in rows if str(r.get("Status","")).strip() == "In_Progress")
    resolved   = sum(1 for r in rows if str(r.get("Status","")).strip() in ("Resolved","Closed"))
    this_month = sum(1 for r in rows
                     if _in_month(str(r.get("Date","")), now))
    type_counts = {}
    for r in rows:
        t = str(r.get("Type","")).strip()
        type_counts[t] = type_counts.get(t, 0) + 1
    lines = [f"💬 Feedback Management\n{'─'*28}",
             f"Total:      {total}",
             f"🔴 Open:     {open_t}",
             f"⚙️ Progress: {in_prog}",
             f"✅ Resolved: {resolved}",
             f"📅 This month: {this_month}",
             f"{'─'*28}"]
    for t, c in type_counts.items():
        lines.append(f"  {t}: {c}")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Open Tickets",       callback_data="fb_list_Open")],
        [InlineKeyboardButton("⚙️ In Progress",        callback_data="fb_list_In_Progress")],
        [InlineKeyboardButton("✅ Resolved",            callback_data="fb_list_Resolved")],
        [InlineKeyboardButton("🐛 Bugs",               callback_data="fb_type_list_bug")],
        [InlineKeyboardButton("💡 Suggestions",        callback_data="fb_type_list_suggestion")],
        [InlineKeyboardButton("❓ Questions",           callback_data="fb_type_list_question")],
        [InlineKeyboardButton("😤 Complaints",         callback_data="fb_type_list_complaint")],
        [_bm()],
    ])
    await q.edit_message_text("\n".join(lines), reply_markup=kb)


def _in_month(date_str, now):
    try:
        d = datetime.strptime(date_str.strip(), "%d/%m/%Y %H:%M")
        return d.year == now.year and d.month == now.month
    except Exception:
        return False


async def fb_list_handler(update, context):
    """List tickets by status."""
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    status_filter = q.data.replace("fb_list_","")
    try:
        rows = get_sheet("Bot_Feedback").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if status_filter in STATUS_OPTIONS:
        filtered = [r for r in rows if str(r.get("Status","")).strip() == status_filter]
        title = f"{STATUS_ICON.get(status_filter,'❓')} {status_filter} Tickets"
    else:
        filtered = rows
        title = "📋 All Tickets"
    if not filtered:
        await q.edit_message_text(f"{title}\n\nNo tickets found.",
                                  reply_markup=InlineKeyboardMarkup([[_bfb(), _bm()]])); return
    kb = []
    for r in filtered[:20]:
        tid  = str(r.get("Ticket_ID","?"))
        subj = str(r.get("Subject",""))[:25]
        ec_r = str(r.get("Emp_Code",""))
        kb.append([InlineKeyboardButton(f"{tid} — {subj} [{ec_r}]",
                                        callback_data=f"fb_view_{tid}")])
    kb.append([_bfb(), _bm()])
    await q.edit_message_text(
        f"{title} ({len(filtered)})\n\nSelect a ticket:",
        reply_markup=InlineKeyboardMarkup(kb))


async def fb_type_list_handler(update, context):
    """List tickets by type (for Bot_Manager filter)."""
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    type_key = q.data.replace("fb_type_list_","")
    label, _ = TICKET_TYPES.get(type_key, ("Feedback","SUG"))
    try:
        rows = get_sheet("Bot_Feedback").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    filtered = [r for r in rows if type_key in str(r.get("Type","")).lower()]
    if not filtered:
        await q.edit_message_text(f"{label}\n\nNo tickets found.",
                                  reply_markup=InlineKeyboardMarkup([[_bfb(), _bm()]])); return
    kb = []
    for r in filtered[:20]:
        tid  = str(r.get("Ticket_ID","?"))
        subj = str(r.get("Subject",""))[:25]
        st   = str(r.get("Status",""))
        kb.append([InlineKeyboardButton(
            f"{STATUS_ICON.get(st,'❓')} {tid} — {subj}",
            callback_data=f"fb_view_{tid}")])
    kb.append([_bfb(), _bm()])
    await q.edit_message_text(
        f"{label} ({len(filtered)})\n\nSelect a ticket:",
        reply_markup=InlineKeyboardMarkup(kb))


async def fb_view_ticket_handler(update, context):
    """Show one ticket detail."""
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    tid = q.data.replace("fb_view_","")
    try:
        rows = get_sheet("Bot_Feedback").get_all_records()
        row  = next((r for r in rows if str(r.get("Ticket_ID","")) == tid), None)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not row:
        await q.edit_message_text("❌ Ticket not found.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    st       = str(row.get("Status","")).strip()
    response = str(row.get("Response","")).strip()
    msg = (f"💬 Ticket {tid}\n{'─'*28}\n"
           f"From:    {row.get('Emp_Code','-')}\n"
           f"Type:    {row.get('Type','-')}\n"
           f"Date:    {row.get('Date','-')}\n"
           f"Status:  {STATUS_ICON.get(st,'❓')} {st}\n"
           f"{'─'*28}\n"
           f"Subject:\n{row.get('Subject','')}\n\n"
           f"Description:\n{row.get('Description','')}\n"
           f"{'─'*28}\n"
           f"Response: {response or '(none yet)'}")
    context.user_data["fb_viewing_id"] = tid
    kb = []
    if not response:
        kb.append([InlineKeyboardButton("✍️ Reply", callback_data=f"fb_respond_{tid}")])
    # Status change buttons
    kb.append([InlineKeyboardButton(f"➡️ {s}", callback_data=f"fb_status_{tid}_{s}")
               for s in STATUS_OPTIONS if s != st][:3])
    kb.append([_bfb(), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def fb_respond_start(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    tid = q.data.replace("fb_respond_","")
    context.user_data["fb_resp_id"] = tid
    await q.edit_message_text(
        f"✍️ Reply to {tid}\n\nType your response:",
        reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return FB_RESP


async def fb_respond_inp(update, context):
    text = update.message.text.strip()
    bk   = InlineKeyboardMarkup([[_bm()]])
    if len(text) < 3:
        await update.message.reply_text("⚠️ Too short:", reply_markup=bk)
        return FB_RESP
    ec, _  = _get_user(str(update.message.from_user.id))
    tid    = context.user_data.get("fb_resp_id","")
    now    = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        ws   = get_sheet("Bot_Feedback")
        rows = ws.get_all_values()
        hdr  = rows[0] if rows else []
        def _col(name, default):
            try: return hdr.index(name) + 1
            except: return default
        resp_col   = _col("Response",     11)
        rdate_col  = _col("Response_Date",12)
        rby_col    = _col("Responded_By", 13)
        status_col = _col("Status",       10)
        tid_col    = _col("Ticket_ID",     1)
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) >= tid_col and r[tid_col-1].strip() == tid:
                ws.update_cell(i+1, resp_col,  text)
                ws.update_cell(i+1, rdate_col, now)
                ws.update_cell(i+1, rby_col,   ec or "")
                ws.update_cell(i+1, status_col,"Resolved")
                break
        await update.message.reply_text(
            f"✅ Response sent for {tid}.\nStatus set to Resolved.",
            reply_markup=bk)
    except Exception as e:
        await update.message.reply_text(f"❌ {e}", reply_markup=bk)
    return ConversationHandler.END


async def fb_status_cb(update, context):
    """Change ticket status."""
    q = update.callback_query; await q.answer()
    ec, role = _get_user(str(q.from_user.id))
    if role not in MGR_ROLES:
        await q.edit_message_text("❌ Access denied.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    parts = q.data.replace("fb_status_","").split("_")
    # tid can contain dashes (BUG-2026-0001) so split on last _ segments that match status
    new_status = parts[-1]
    if new_status not in STATUS_OPTIONS:
        # try two parts
        new_status = f"{parts[-2]}_{parts[-1]}"
    tid = q.data.replace("fb_status_","").replace(f"_{new_status}","")
    try:
        ws   = get_sheet("Bot_Feedback")
        rows = ws.get_all_values()
        hdr  = rows[0] if rows else []
        try: status_col = hdr.index("Status") + 1
        except: status_col = 10
        try: tid_col = hdr.index("Ticket_ID") + 1
        except: tid_col = 1
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) >= tid_col and r[tid_col-1].strip() == tid:
                ws.update_cell(i+1, status_col, new_status)
                break
        await q.edit_message_text(
            f"✅ Status updated to: {new_status}\nTicket: {tid}",
            reply_markup=InlineKeyboardMarkup([[_bfb(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


async def fb_resp_cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_feedback_handler():
    """Employee feedback submission conversation."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(fb_menu_start, pattern="^menu_bot_feedback$")],
        states={
            FB_TYPE:    [CallbackQueryHandler(fb_type_cb, pattern="^fb_type_")],
            FB_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fb_subject_inp)],
            FB_DESC:    [MessageHandler(filters.TEXT & ~filters.COMMAND, fb_desc_inp)],
            FB_PHOTOS:  [
                MessageHandler(filters.PHOTO, fb_photo_inp),
                CallbackQueryHandler(fb_skip_photos_cb, pattern="^fb_skip_photos$"),
            ],
            FB_CONFIRM: [
                CallbackQueryHandler(fb_confirm_cb, pattern="^fb_(confirm|cancel)$"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fb_cancel_cmd)],
        per_message=False,
    )


def get_fb_mgr_handler():
    """Bot_Manager response conversation."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(fb_respond_start, pattern="^fb_respond_")],
        states={
            FB_RESP: [MessageHandler(filters.TEXT & ~filters.COMMAND, fb_respond_inp)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, fb_resp_cancel)],
        per_message=False,
    )


def get_fb_static_handlers():
    """Static callback handlers for feedback dashboard."""
    return [
        CallbackQueryHandler(fb_dashboard_handler,   pattern="^bm_feedback$"),
        CallbackQueryHandler(fb_list_handler,        pattern="^fb_list_"),
        CallbackQueryHandler(fb_type_list_handler,   pattern="^fb_type_list_"),
        CallbackQueryHandler(fb_view_ticket_handler, pattern="^fb_view_"),
        CallbackQueryHandler(fb_status_cb,           pattern="^fb_status_"),
    ]
