"""
ROIN WORLD FZE — Contact HR Handler
======================================
Employee sends message to HR (named or anonymous).
HR can view queue and respond from their menu.
Contact_HR tab: Msg_ID, Emp_Code, Timestamp, Message, Anonymous, HR_Response, Response_Date
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from config import get_sheet

CHR_TYPE = 200
CHR_MSG  = 201

# ── HR view states ──
CHR_HR_VIEW  = 202
CHR_HR_REPLY = 203


def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")


def _find_ec(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _get_role(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[3].strip() if len(r) > 3 else "Employee"
    return "Employee"


def _gen_chr_id():
    ids = get_sheet("Contact_HR").col_values(1)
    yr = datetime.now().strftime("%Y")
    px = f"CHR-{yr}-"
    mx = 0
    for r in ids:
        if str(r).startswith(px):
            try: n = int(str(r).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


# ── Employee side ──────────────────────────────────────────────────────────────

async def contact_hr_start(update, context):
    q = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("❌ Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return ConversationHandler.END
    context.user_data["chr_ec"] = ec
    kb = [
        [InlineKeyboardButton("👤 Send with my name",  callback_data="chr_named")],
        [InlineKeyboardButton("🕵️ Send anonymously",  callback_data="chr_anon")],
        [bm()],
    ]
    await q.edit_message_text(
        "💬 Contact HR\n\nHow would you like to send your message?",
        reply_markup=InlineKeyboardMarkup(kb))
    return CHR_TYPE


async def chr_type_sel(update, context):
    q = update.callback_query; await q.answer()
    anon = q.data == "chr_anon"
    context.user_data["chr_anon"] = anon
    label = "anonymously" if anon else "with your name"
    await q.edit_message_text(
        f"💬 Contact HR ({label})\n\nType your message (5–500 characters):",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return CHR_MSG


async def chr_message_inp(update, context):
    text = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bm()]])
    if len(text) < 5:
        await update.message.reply_text("⚠️ Too short. Please type at least 5 characters:", reply_markup=bk)
        return CHR_MSG
    if len(text) > 500:
        await update.message.reply_text("⚠️ Too long. Max 500 characters:", reply_markup=bk)
        return CHR_MSG
    ec    = context.user_data["chr_ec"]
    anon  = context.user_data.get("chr_anon", False)
    try:
        msg_id = _gen_chr_id()
        now    = datetime.now().strftime("%d/%m/%Y %H:%M")
        ws     = get_sheet("Contact_HR")
        # Cols: Msg_ID, Emp_Code, Name(VLOOKUP=""), Dept(VLOOKUP=""),
        #       Timestamp, Message, Anonymous, HR_Response, Response_Date
        row    = [msg_id, ec if not anon else "Anonymous", "", "",
                  now, text, "Yes" if anon else "No", "", ""]
        ws.append_row(row, value_input_option="USER_ENTERED")
        reply = (f"✅ Message sent to HR!\n\n"
                 f"ID: {msg_id}\nSent: {now}\n"
                 + ("(Sent anonymously)" if anon else ""))
    except Exception as e:
        reply = f"❌ Error: {e}"
    await update.message.reply_text(reply, reply_markup=bk)
    return ConversationHandler.END


async def chr_back_to_menu(update, context):
    from bot import build_inline_menu
    q = update.callback_query; await q.answer()
    role = _get_role(str(q.from_user.id))
    await q.edit_message_text("Choose an option:", reply_markup=build_inline_menu(role))
    return ConversationHandler.END


async def chr_cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_contact_hr_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(contact_hr_start, pattern="^menu_contact_hr$")],
        states={
            CHR_TYPE: [
                CallbackQueryHandler(chr_type_sel,     pattern="^chr_(named|anon)$"),
                CallbackQueryHandler(chr_back_to_menu, pattern="^back_to_menu$"),
            ],
            CHR_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, chr_message_inp),
                CallbackQueryHandler(chr_back_to_menu, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, chr_cancel)],
        per_message=False,
    )


# ── HR side: view queue ────────────────────────────────────────────────────────

async def hr_messages_menu(update, context):
    """HR taps 💬 HR Messages → see pending messages."""
    q = update.callback_query; await q.answer()
    try:
        rows = get_sheet("Contact_HR").get_all_records()
        pending = [r for r in rows if not str(r.get("HR_Response", "")).strip()]
        total   = len(rows)
        unanswered = len(pending)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_hr_tools"), bm()]])); return
    kb = []
    if pending:
        kb.append([InlineKeyboardButton(f"📬 View Unanswered ({unanswered})", callback_data="hr_chr_pending")])
    kb.append([InlineKeyboardButton(f"📂 All Messages ({total})",        callback_data="hr_chr_all")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_hr_tools"), bm()])
    await q.edit_message_text(
        f"💬 HR Messages Queue\n\nUnanswered: {unanswered}\nTotal: {total}",
        reply_markup=InlineKeyboardMarkup(kb))


async def hr_chr_list(update, context):
    """Show list of messages (pending or all)."""
    q = update.callback_query; await q.answer()
    mode = "pending" if q.data == "hr_chr_pending" else "all"
    try:
        rows = get_sheet("Contact_HR").get_all_records()
        if mode == "pending":
            msgs = [r for r in rows if not str(r.get("HR_Response", "")).strip()]
        else:
            msgs = rows
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_hr_messages"), bm()]])); return
    if not msgs:
        await q.edit_message_text("No messages found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_hr_messages"), bm()]])); return
    kb = []
    for r in msgs[:20]:
        mid = str(r.get("Msg_ID", "?"))
        ec  = str(r.get("Emp_Code", "?"))
        ts  = str(r.get("Timestamp", "?"))[:10]
        answered = "✅" if str(r.get("HR_Response", "")).strip() else "🔴"
        kb.append([InlineKeyboardButton(f"{answered} {mid} — {ec} ({ts})",
                                        callback_data=f"hr_chr_view_{mid}")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_hr_messages"), bm()])
    await q.edit_message_text(
        f"💬 {'Unanswered' if mode == 'pending' else 'All'} Messages:",
        reply_markup=InlineKeyboardMarkup(kb))


async def hr_chr_view(update, context):
    """Show one message detail."""
    q = update.callback_query; await q.answer()
    mid = q.data.replace("hr_chr_view_", "")
    try:
        rows = get_sheet("Contact_HR").get_all_records()
        row  = next((r for r in rows if str(r.get("Msg_ID", "")) == mid), None)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_hr_messages"), bm()]])); return
    if not row:
        await q.edit_message_text("Message not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_hr_messages"), bm()]])); return
    anon     = str(row.get("Anonymous", "No")).strip() == "Yes"
    response = str(row.get("HR_Response", "")).strip()
    msg = (f"💬 Message {mid}\n{'─'*28}\n"
           f"From:      {'Anonymous' if anon else row.get('Emp_Code','?')}\n"
           f"Sent:      {row.get('Timestamp','?')}\n\n"
           f"Message:\n{row.get('Message','')}\n\n"
           f"{'─'*28}\n"
           f"Response: {response if response else '(none yet)'}")
    kb = []
    if not response:
        kb.append([InlineKeyboardButton("✍️ Reply", callback_data=f"hr_chr_reply_{mid}")])
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="hr_chr_pending"), bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    context.user_data["hr_chr_viewing"] = mid


async def hr_chr_reply_start(update, context):
    q = update.callback_query; await q.answer()
    mid = q.data.replace("hr_chr_reply_", "")
    context.user_data["hr_chr_reply_id"] = mid
    await q.edit_message_text(
        f"✍️ Reply to {mid}\n\nType your response:",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return CHR_HR_REPLY


async def hr_chr_reply_inp(update, context):
    text = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bm()]])
    if len(text) < 3:
        await update.message.reply_text("⚠️ Too short:", reply_markup=bk)
        return CHR_HR_REPLY
    mid = context.user_data.get("hr_chr_reply_id")
    try:
        ws   = get_sheet("Contact_HR")
        rows = ws.get_all_values()
        hdr  = rows[0] if rows else []
        try: msg_col = hdr.index("Msg_ID") + 1
        except: msg_col = 1
        try: resp_col = hdr.index("HR_Response") + 1
        except: resp_col = 6
        try: date_col = hdr.index("Response_Date") + 1
        except: date_col = 7
        for i, row in enumerate(rows):
            if i == 0: continue
            if len(row) >= msg_col and row[msg_col - 1] == mid:
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                ws.update_cell(i + 1, resp_col, text)
                ws.update_cell(i + 1, date_col, now)
                break
        reply = f"✅ Response sent for {mid}."
    except Exception as e:
        reply = f"❌ {e}"
    await update.message.reply_text(reply, reply_markup=bk)
    return ConversationHandler.END


async def hr_chr_cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_hr_chr_reply_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(hr_chr_reply_start, pattern="^hr_chr_reply_")],
        states={
            CHR_HR_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, hr_chr_reply_inp),
                CallbackQueryHandler(chr_back_to_menu, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, hr_chr_cancel)],
        per_message=False,
    )
