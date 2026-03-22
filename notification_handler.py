"""
ROIN WORLD FZE — Notification Center
=====================================
Sheet-backed notification system.
No Telegram push messages — notifications are ONLY visible inside the bot.
Exception: approval result messages keep existing behavior.

Sheet tab: Notifications
Columns: Notif_ID, Timestamp, Emp_Code, Type, Title, Message,
         Related_ID, Read, Read_At
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet

TAB = "Notifications"


def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")


# ── Sheet helpers ──────────────────────────────────────────────────────────────

def _next_notif_id():
    try:
        rows = get_sheet(TAB).get_all_values()
        nums = []
        for r in rows[1:]:
            if r and r[0].startswith("NTF-"):
                try:
                    nums.append(int(r[0].split("-")[-1]))
                except ValueError:
                    pass
        return f"NTF-{str(max(nums) + 1 if nums else 1).zfill(5)}"
    except Exception:
        return f"NTF-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _get_rows_for_ec(ec):
    try:
        rows = get_sheet(TAB).get_all_values()
        result = []
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 2 and str(r[2]).strip() == str(ec):
                result.append((i + 1, r))  # (1-based row num, row data)
        return result
    except Exception:
        return []


# ── Public API ─────────────────────────────────────────────────────────────────

def create_notification(ec, notif_type, title, message, related_id=""):
    """
    Write a new notification row for the given employee code.
    Called from leave approval flow, memo flow, etc.
    """
    try:
        nid = _next_notif_id()
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        get_sheet(TAB).append_row([
            nid, ts, str(ec), notif_type, title, message,
            str(related_id), "No", ""
        ])
    except Exception as e:
        print(f"[Notif] Failed to create notification: {e}")


def get_unread_count(ec):
    """Return the number of unread notifications for this employee code."""
    try:
        rows = get_sheet(TAB).get_all_values()
        count = 0
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 7 and str(r[2]).strip() == str(ec) and str(r[7]).strip() == "No":
                count += 1
        return count
    except Exception:
        return 0


def _mark_read(row_num):
    try:
        ts = datetime.now().strftime("%d/%m/%Y %H:%M")
        get_sheet(TAB).update_cell(row_num, 8, "Yes")
        get_sheet(TAB).update_cell(row_num, 9, ts)
    except Exception:
        pass


def _mark_all_read(ec):
    rows_data = _get_rows_for_ec(ec)
    for rn, r in rows_data:
        if len(r) > 7 and str(r[7]).strip() == "No":
            _mark_read(rn)


# ── Handlers ──────────────────────────────────────────────────────────────────

def _find_ec_by_tid(tid):
    try:
        rows = get_sheet("User_Registry").get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 1 and r[1].strip() == str(tid):
                return r[0].strip()
    except Exception:
        pass
    return None


async def notif_menu_handler(update, context):
    """Show unread notifications list (newest first)."""
    q = update.callback_query; await q.answer()
    ec = _find_ec_by_tid(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return

    rows_data = _get_rows_for_ec(ec)
    unread = [(rn, r) for rn, r in rows_data if len(r) > 7 and str(r[7]).strip() == "No"]
    unread.reverse()  # newest first

    if not unread:
        kb = [
            [InlineKeyboardButton("📜 View History", callback_data="notif_history")],
            [bm()],
        ]
        await q.edit_message_text(
            "🔔 Notifications\n\nNo new notifications.",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    kb = [
        [InlineKeyboardButton("✅ Mark All as Read", callback_data="notif_mark_all")],
    ]
    for rn, r in unread[:20]:
        nid = r[0]; title = r[4] if len(r) > 4 else "Notification"
        ts = r[1][:10] if len(r) > 1 else ""
        label = f"🔔 {title[:35]}{'...' if len(title) > 35 else ''} ({ts})"
        kb.append([InlineKeyboardButton(label, callback_data=f"notif_view_{nid}")])

    kb.append([InlineKeyboardButton("📜 View History", callback_data="notif_history")])
    kb.append([bm()])

    await q.edit_message_text(
        f"🔔 Notifications — {len(unread)} unread",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def notif_view_handler(update, context):
    """View a single notification and mark it read."""
    q = update.callback_query; await q.answer()
    nid = q.data.replace("notif_view_", "")
    ec = _find_ec_by_tid(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_notifications"), bm()]]))
        return

    rows_data = _get_rows_for_ec(ec)
    target_rn, target_r = None, None
    for rn, r in rows_data:
        if r[0].strip() == nid:
            target_rn, target_r = rn, r; break

    if not target_r:
        await q.edit_message_text("Notification not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_notifications"), bm()]]))
        return

    # Mark as read
    if len(target_r) > 7 and str(target_r[7]).strip() == "No":
        _mark_read(target_rn)

    title   = target_r[4] if len(target_r) > 4 else "Notification"
    message = target_r[5] if len(target_r) > 5 else ""
    ts      = target_r[1] if len(target_r) > 1 else ""
    rel_id  = target_r[6] if len(target_r) > 6 else ""

    detail = f"🔔 {title}\n\n{message}\n\n🕐 {ts}"
    if rel_id:
        detail += f"\n📎 Ref: {rel_id}"

    kb = [
        [InlineKeyboardButton("↩️ Back to Notifications", callback_data="menu_notifications")],
        [bm()],
    ]
    await q.edit_message_text(detail, reply_markup=InlineKeyboardMarkup(kb))


async def notif_mark_all_handler(update, context):
    """Mark all notifications as read for this employee."""
    q = update.callback_query; await q.answer()
    ec = _find_ec_by_tid(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return

    _mark_all_read(ec)
    kb = [
        [InlineKeyboardButton("📜 View History", callback_data="notif_history")],
        [bm()],
    ]
    await q.edit_message_text(
        "✅ All notifications marked as read.",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def notif_history_handler(update, context):
    """Show last 50 read notifications."""
    q = update.callback_query; await q.answer()
    ec = _find_ec_by_tid(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_notifications"), bm()]]))
        return

    rows_data = _get_rows_for_ec(ec)
    read = [(rn, r) for rn, r in rows_data if len(r) > 7 and str(r[7]).strip() == "Yes"]
    read.reverse()
    read = read[:50]

    if not read:
        kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_notifications")], [bm()]]
        await q.edit_message_text("📜 No notification history.", reply_markup=InlineKeyboardMarkup(kb))
        return

    kb = []
    for rn, r in read:
        nid = r[0]; title = r[4] if len(r) > 4 else "Notification"
        ts = r[1][:10] if len(r) > 1 else ""
        label = f"📩 {title[:35]}{'...' if len(title) > 35 else ''} ({ts})"
        kb.append([InlineKeyboardButton(label, callback_data=f"notif_view_{nid}")])

    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_notifications")])
    kb.append([bm()])

    await q.edit_message_text(
        f"📜 Notification History — {len(read)} entries",
        reply_markup=InlineKeyboardMarkup(kb)
    )


def get_notif_handlers():
    return [
        CallbackQueryHandler(notif_menu_handler,    pattern="^menu_notifications$"),
        CallbackQueryHandler(notif_view_handler,    pattern="^notif_view_"),
        CallbackQueryHandler(notif_mark_all_handler, pattern="^notif_mark_all$"),
        CallbackQueryHandler(notif_history_handler,  pattern="^notif_history$"),
    ]
