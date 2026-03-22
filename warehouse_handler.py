"""
ROIN WORLD FZE — Warehouse Management Handler
=============================================
Phase 10:
  10A. Stock IN/OUT/Transfer/Waste logging
  10B. Live Inventory (Current_Balance tab)
  10C. Low Stock Alerts
  10D. Daily Stock Count

Stock_Transactions tab:
  TX_ID, Date, Type, Item, Quantity, Unit, Warehouse,
  From_WH, To_WH, Supplier, Department, Emp_Code, Photo_Link, Notes

Current_Balance tab:
  Item, Unit, WH1, WH2, WH3, Total, Min_Level, Status
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler, MessageHandler, filters)
from config import get_sheet

def bm(): return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def bwh(): return InlineKeyboardButton("↩️ Warehouse", callback_data="menu_warehouse")

TX_ITEM = 1000; TX_QTY = 1001; TX_DETAILS = 1002; TX_CONFIRM = 1003

TX_TYPES = {
    "wh_in":     ("📦 Stock IN",   "IN"),
    "wh_out":    ("📤 Stock OUT",  "OUT"),
    "wh_xfer":   ("🔄 Transfer",   "Transfer"),
    "wh_waste":  ("🗑 Waste/Dmg",  "Waste"),
}

WAREHOUSES = ["WH-1", "WH-2", "WH-3"]


def _gen_tx_id():
    ids = get_sheet("Stock_Transactions").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"TX-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _get_items():
    try:
        rows = get_sheet("Current_Balance").get_all_records()
        return [str(r.get("Item","")).strip() for r in rows if str(r.get("Item","")).strip()]
    except Exception: return []


async def wh_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("📦 Stock IN",       callback_data="wh_in")],
        [InlineKeyboardButton("📤 Stock OUT",      callback_data="wh_out")],
        [InlineKeyboardButton("🔄 Transfer",       callback_data="wh_xfer")],
        [InlineKeyboardButton("🗑 Waste / Damage", callback_data="wh_waste")],
        [InlineKeyboardButton("📊 Inventory",      callback_data="wh_inventory")],
        [InlineKeyboardButton("⚠️ Low Stock",      callback_data="wh_low_stock")],
        [bm()],
    ]
    await q.edit_message_text("📦 Warehouse\n\nSelect action:", reply_markup=InlineKeyboardMarkup(kb))


async def wh_tx_start(update, context):
    q = update.callback_query; await q.answer()
    tx_type = q.data
    context.user_data["wh_tx_type"] = tx_type
    label, code = TX_TYPES.get(tx_type, ("Transaction", tx_type))
    items = _get_items()
    if items:
        kb = [[InlineKeyboardButton(it, callback_data=f"wh_item_{it}")] for it in items[:15]]
        kb.append([bwh(), bm()])
        await q.edit_message_text(f"{label}\n\nSelect item:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await q.edit_message_text(f"{label}\n\nType item name:",
            reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    return TX_ITEM


async def wh_item_sel_cb(update, context):
    q = update.callback_query; await q.answer()
    item = q.data.replace("wh_item_","")
    context.user_data["wh_item"] = item
    await q.edit_message_text(f"Item: {item}\n\nType quantity (number only):",
        reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    return TX_QTY


async def wh_item_txt(update, context):
    context.user_data["wh_item"] = update.message.text.strip()
    await update.message.reply_text("Type quantity:", reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    return TX_QTY


async def wh_qty_inp(update, context):
    text = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bwh(), bm()]])
    try: qty = float(text); assert qty > 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid positive number:", reply_markup=bk)
        return TX_QTY
    context.user_data["wh_qty"] = qty
    tx_type = context.user_data.get("wh_tx_type","wh_in")
    if tx_type == "wh_in":
        await update.message.reply_text("Supplier name (or '-' if none):", reply_markup=bk)
    elif tx_type == "wh_out":
        await update.message.reply_text("Requesting department:", reply_markup=bk)
    elif tx_type == "wh_xfer":
        kb = [[InlineKeyboardButton(wh, callback_data=f"wh_fromwh_{wh}")] for wh in WAREHOUSES]
        kb.append([bwh(), bm()])
        await update.message.reply_text("Transfer FROM warehouse:", reply_markup=InlineKeyboardMarkup(kb))
    elif tx_type == "wh_waste":
        await update.message.reply_text("Reason for waste/damage:", reply_markup=bk)
    return TX_DETAILS


async def wh_details_txt(update, context):
    context.user_data["wh_details"] = update.message.text.strip()
    return await _wh_show_confirm(update.message, context)


async def wh_from_wh(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["wh_from"] = q.data.replace("wh_fromwh_","")
    kb = [[InlineKeyboardButton(wh, callback_data=f"wh_towh_{wh}")] for wh in WAREHOUSES
          if wh != context.user_data["wh_from"]]
    kb.append([bwh(), bm()])
    await q.edit_message_text("Transfer TO warehouse:", reply_markup=InlineKeyboardMarkup(kb))
    return TX_DETAILS


async def wh_to_wh(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["wh_to"] = q.data.replace("wh_towh_","")
    await q.edit_message_text("Any notes? (or '-' to skip):",
        reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    return TX_CONFIRM


async def _wh_show_confirm(msg_obj, context):
    tx_type = context.user_data.get("wh_tx_type","")
    label, code = TX_TYPES.get(tx_type, ("Transaction","TX"))
    item    = context.user_data.get("wh_item","?")
    qty     = context.user_data.get("wh_qty",0)
    details = context.user_data.get("wh_details","")
    summary = f"{label}\nItem: {item}\nQty: {qty}\nDetails: {details}"
    kb = [[InlineKeyboardButton("✅ Confirm", callback_data="wh_confirm"),
           InlineKeyboardButton("❌ Cancel",  callback_data="wh_cancel")],
          [bwh(), bm()]]
    await msg_obj.reply_text(f"📦 Confirm transaction?\n{'─'*24}\n{summary}",
                              reply_markup=InlineKeyboardMarkup(kb))
    return TX_CONFIRM


async def wh_confirm(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "wh_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    tid = str(q.from_user.id)
    ec  = None
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: ec = r[0].strip(); break
    tx_type = context.user_data.get("wh_tx_type","")
    _, code = TX_TYPES.get(tx_type, ("","TX"))
    try:
        tx_id = _gen_tx_id()
        now   = datetime.now().strftime("%d/%m/%Y %H:%M")
        item  = context.user_data.get("wh_item","")
        qty   = context.user_data.get("wh_qty",0)
        det   = context.user_data.get("wh_details","")
        from_wh = context.user_data.get("wh_from","")
        to_wh   = context.user_data.get("wh_to","")
        row = [tx_id, now, code, item, qty, "", from_wh or "WH-1",
               from_wh, to_wh, det if code=="IN" else "",
               det if code=="OUT" else "", ec or "", "", det]
        get_sheet("Stock_Transactions").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(f"✅ Transaction logged!\nID: {tx_id}\n{code} | {item} | {qty} units",
            reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bwh(), bm()]]))
    return ConversationHandler.END


async def wh_inventory_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading inventory...")
    try:
        rows = get_sheet("Current_Balance").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bwh(), bm()]])); return
    lines = [f"📊 Live Inventory ({len(rows)} items)\n{'─'*28}"]
    for r in rows[:20]:
        item   = str(r.get("Item",""))
        total  = str(r.get("Total","?"))
        unit   = str(r.get("Unit",""))
        status = str(r.get("Status","?"))
        icon   = {"OK":"🟢","LOW":"🟡","CRITICAL":"🟠","OUT":"🔴"}.get(status,"❓")
        lines.append(f"{icon} {item}: {total} {unit}")
    if len(rows) > 20: lines.append(f"... +{len(rows)-20} more items")
    kb = [[bwh(), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def wh_low_stock_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Checking low stock...")
    try:
        rows = get_sheet("Current_Balance").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bwh(), bm()]])); return
    low = [r for r in rows if str(r.get("Status","")).strip() in ("LOW","CRITICAL","OUT")]
    if not low:
        await q.edit_message_text("✅ All items above minimum levels.",
            reply_markup=InlineKeyboardMarkup([[bwh(), bm()]])); return
    lines = [f"⚠️ Low Stock Alert ({len(low)} items)\n{'─'*28}"]
    for r in low:
        icon   = {"LOW":"🟡","CRITICAL":"🟠","OUT":"🔴"}.get(str(r.get("Status","")), "❓")
        lines.append(f"{icon} {r.get('Item','')} — {r.get('Total','?')} {r.get('Unit','')} "
                     f"(min: {r.get('Min_Level','?')})")
    kb = [[bwh(), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def wh_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_wh_tx_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(wh_tx_start, pattern="^wh_(in|out|xfer|waste)$")],
        states={
            TX_ITEM:    [CallbackQueryHandler(wh_item_sel_cb, pattern="^wh_item_"),
                         MessageHandler(filters.TEXT & ~filters.COMMAND, wh_item_txt),
                         CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
            TX_QTY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, wh_qty_inp)],
            TX_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wh_details_txt),
                         CallbackQueryHandler(wh_from_wh, pattern="^wh_fromwh_"),
                         CallbackQueryHandler(wh_to_wh,   pattern="^wh_towh_")],
            TX_CONFIRM: [CallbackQueryHandler(wh_confirm,  pattern="^wh_(confirm|cancel)$"),
                         MessageHandler(filters.TEXT & ~filters.COMMAND, wh_details_txt)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, wh_cancel_handler)],
        per_message=False,
    )


def get_wh_static_handlers():
    return [
        CallbackQueryHandler(wh_menu_handler,       pattern="^menu_warehouse$"),
        CallbackQueryHandler(wh_inventory_handler,  pattern="^wh_inventory$"),
        CallbackQueryHandler(wh_low_stock_handler,  pattern="^wh_low_stock$"),
    ]
