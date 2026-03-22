"""
ROIN WORLD FZE — Quality Control Handler
=========================================
Section 7 — New role: Quality_Manager

7A. Incoming Material Inspection
7B. Quality Inspection Flow
7D. Quality Dashboard
7E. Quality Menu

Sheet tab:
  Quality_Inspection_Log: Inspection_ID, Date, Supplier, Item, Quantity, Unit,
    PO_Number, Inspector_Code, Inspector_Name, Result, Rejection_Reason,
    Rejection_Quantity, Temperature_Check, Expiry_Date_Check,
    Certificate_Links, Delivery_Note_Photo, Inspection_Report_Photo,
    Notes, PDF_Report_Link
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm():  return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bqc(): return InlineKeyboardButton("↩️ Quality",    callback_data="menu_quality")

RESULTS    = ["Accepted","Rejected","Partial_Accept"]
RESULT_ICON= {"Accepted":"✅","Rejected":"❌","Partial_Accept":"⚠️"}

# ── States ────────────────────────────────────────────────────────────────────
QC_SUPPLIER = 1700; QC_ITEM     = 1701; QC_QTY      = 1702
QC_RESULT   = 1703; QC_REASON   = 1704; QC_TEMP     = 1705
QC_NOTES    = 1706; QC_CONFIRM  = 1707


def _get_emp_info(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid):
            return r[0].strip()
    return None


def _gen_insp_id():
    ids = get_sheet("Quality_Inspection_Log").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"QC-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _get_suppliers():
    try:
        rows = get_sheet("Suppliers").get_all_records()
        return [str(r.get("Name","")).strip() for r in rows if str(r.get("Name","")).strip()]
    except Exception:
        return []


def _get_inspector_name(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code","")).strip() == str(ec):
                return r.get("Full_Name","")
    except Exception:
        pass
    return ec


def _in_month(date_str, now):
    try:
        d = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return d.year == now.year and d.month == now.month
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  QUALITY MENU
# ══════════════════════════════════════════════════════════════════════════════
async def quality_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("🔍 New Inspection",       callback_data="qc_new")],
        [InlineKeyboardButton("📋 All Inspections",       callback_data="qc_all")],
        [InlineKeyboardButton("📊 Quality Dashboard",     callback_data="qc_dashboard")],
        [InlineKeyboardButton("🏭 Supplier Quality",      callback_data="qc_supplier_quality")],
        [_bm()],
    ]
    await q.edit_message_text("🔍 Quality Control\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  NEW INSPECTION FLOW
# ══════════════════════════════════════════════════════════════════════════════
async def qc_new_start(update, context):
    q = update.callback_query; await q.answer()
    suppliers = _get_suppliers()
    if suppliers:
        kb = [[InlineKeyboardButton(s, callback_data=f"qc_sup_{s}")] for s in suppliers[:15]]
        kb.append([InlineKeyboardButton("✏️ Type Name", callback_data="qc_sup_manual")])
        kb.append([_bm()])
        await q.edit_message_text("🔍 New Inspection\n\nSelect supplier:",
                                  reply_markup=InlineKeyboardMarkup(kb))
    else:
        await q.edit_message_text("🔍 New Inspection\n\nEnter supplier name:",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_SUPPLIER


async def qc_sup_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "qc_sup_manual":
        await q.edit_message_text("Type the supplier name:",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return QC_SUPPLIER
    context.user_data["qc_supplier"] = q.data.replace("qc_sup_","")
    await q.edit_message_text(f"Supplier: {context.user_data['qc_supplier']}\n\nEnter item name:",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_ITEM


async def qc_sup_txt(update, context):
    context.user_data["qc_supplier"] = update.message.text.strip()
    await update.message.reply_text("Enter item name:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_ITEM


async def qc_item_inp(update, context):
    context.user_data["qc_item"] = update.message.text.strip()
    await update.message.reply_text("Enter quantity and unit (e.g. '50 kg' or '100 boxes'):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_QTY


async def qc_qty_inp(update, context):
    context.user_data["qc_qty"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(f"{RESULT_ICON.get(r,'')} {r}", callback_data=f"qc_result_{r}")]
          for r in RESULTS]
    kb.append([_bm()])
    await update.message.reply_text("Inspection result:", reply_markup=InlineKeyboardMarkup(kb))
    return QC_RESULT


async def qc_result_cb(update, context):
    q = update.callback_query; await q.answer()
    result = q.data.replace("qc_result_","")
    context.user_data["qc_result"] = result
    if result in ("Rejected","Partial_Accept"):
        await q.edit_message_text(
            f"Result: {RESULT_ICON.get(result,'')} {result}\n\n"
            "Enter rejection reason and rejected quantity:",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return QC_REASON
    context.user_data["qc_reason"] = ""
    await q.edit_message_text("Temperature check result (or '-' if N/A):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_TEMP


async def qc_reason_inp(update, context):
    context.user_data["qc_reason"] = update.message.text.strip()
    await update.message.reply_text("Temperature check result (or '-' if N/A):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_TEMP


async def qc_temp_inp(update, context):
    context.user_data["qc_temp"] = update.message.text.strip()
    await update.message.reply_text("Additional notes (or '-'):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return QC_NOTES


async def qc_notes_inp(update, context):
    context.user_data["qc_notes"] = update.message.text.strip()
    result = context.user_data.get("qc_result","")
    summary = (f"🔍 Inspection Report\n{'─'*24}\n"
               f"Date:     {datetime.now().strftime('%d/%m/%Y')}\n"
               f"Supplier: {context.user_data.get('qc_supplier','')}\n"
               f"Item:     {context.user_data.get('qc_item','')}\n"
               f"Qty:      {context.user_data.get('qc_qty','')}\n"
               f"Result:   {RESULT_ICON.get(result,'')} {result}\n"
               f"Reason:   {context.user_data.get('qc_reason','-')}\n"
               f"Temp:     {context.user_data.get('qc_temp','-')}\n"
               f"Notes:    {context.user_data.get('qc_notes','-')}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="qc_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="qc_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return QC_CONFIRM


async def qc_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "qc_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec    = _get_emp_info(str(q.from_user.id))
    name  = _get_inspector_name(ec or "")
    result= context.user_data.get("qc_result","")
    try:
        iid = _gen_insp_id()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        qty_str = context.user_data.get("qc_qty","")
        rej_qty = qty_str if result in ("Rejected","Partial_Accept") else ""
        row = [iid,
               datetime.now().strftime("%d/%m/%Y"),
               context.user_data.get("qc_supplier",""),
               context.user_data.get("qc_item",""),
               qty_str, "",  # Quantity, Unit
               "",            # PO_Number
               ec or "", "",  # col I: Inspector_Name (VLOOKUP from col H)
               result,
               context.user_data.get("qc_reason",""),
               rej_qty,
               context.user_data.get("qc_temp",""),
               "",            # Expiry_Date_Check
               "", "", "",    # Certificate_Links, Delivery_Note_Photo, Inspection_Report_Photo
               context.user_data.get("qc_notes",""),
               ""]            # PDF_Report_Link
        get_sheet("Quality_Inspection_Log").append_row(row, value_input_option="USER_ENTERED")
        msg = f"✅ Inspection logged!\nID: {iid}\nResult: {RESULT_ICON.get(result,'')} {result}"
        if result in ("Rejected","Partial_Accept"):
            msg += "\n\n⚠️ Warehouse Manager + Supply Manager notified of rejection."
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def qc_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  ALL INSPECTIONS
# ══════════════════════════════════════════════════════════════════════════════
async def qc_all_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading inspections...")
    try:
        rows = get_sheet("Quality_Inspection_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not rows:
        await q.edit_message_text("📋 No inspections recorded.",
                                  reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]])); return
    lines = [f"📋 All Inspections ({len(rows)})\n{'─'*24}"]
    for r in rows[-20:]:
        res = str(r.get("Result",""))
        lines.append(f"{RESULT_ICON.get(res,'❓')} {r.get('Inspection_ID','')} | "
                     f"{r.get('Date','')} | {r.get('Supplier','')} | {r.get('Item','')}")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  QUALITY DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
async def qc_dashboard_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading quality dashboard...")
    try:
        rows = get_sheet("Quality_Inspection_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    now   = datetime.now()
    month = [r for r in rows if _in_month(str(r.get("Date","")), now)]
    total   = len(month)
    accepted= sum(1 for r in month if str(r.get("Result","")) == "Accepted")
    rejected= sum(1 for r in month if str(r.get("Result","")) == "Rejected")
    partial = sum(1 for r in month if str(r.get("Result","")) == "Partial_Accept")
    rate    = round(accepted/total*100,1) if total else 0
    rate_icon = "🟢" if rate >= 95 else "🟡" if rate >= 85 else "🔴"
    # All time
    all_total    = len(rows)
    all_accepted = sum(1 for r in rows if str(r.get("Result","")) == "Accepted")
    all_rate     = round(all_accepted/all_total*100,1) if all_total else 0
    msg = (f"📊 Quality Dashboard\n{'─'*28}\n"
           f"This Month ({now.strftime('%B %Y')}):\n"
           f"  Inspections: {total}\n"
           f"  ✅ Accepted:   {accepted}\n"
           f"  ❌ Rejected:   {rejected}\n"
           f"  ⚠️ Partial:    {partial}\n"
           f"  Rate: {rate_icon} {rate}%\n"
           f"{'─'*28}\n"
           f"All Time:\n"
           f"  Total: {all_total} | Acceptance: {all_rate}%")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  SUPPLIER QUALITY RATINGS
# ══════════════════════════════════════════════════════════════════════════════
async def qc_supplier_quality(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading supplier quality rankings...")
    try:
        rows = get_sheet("Quality_Inspection_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    # Group by supplier
    sup_data = {}
    for r in rows:
        sup = str(r.get("Supplier","")).strip()
        if not sup: continue
        if sup not in sup_data:
            sup_data[sup] = {"total":0,"accepted":0}
        sup_data[sup]["total"] += 1
        if str(r.get("Result","")) == "Accepted":
            sup_data[sup]["accepted"] += 1
    if not sup_data:
        await q.edit_message_text("🏭 No supplier data yet.",
                                  reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]])); return
    # Sort by acceptance rate
    ranked = sorted(
        [(sup, d["accepted"]/d["total"]*100 if d["total"] else 0, d["total"])
         for sup, d in sup_data.items()],
        key=lambda x: x[1], reverse=True
    )
    lines = [f"🏭 Supplier Quality Rankings ({len(ranked)})\n{'─'*28}"]
    for i, (sup, rate, total) in enumerate(ranked, 1):
        icon = "🟢" if rate >= 95 else "🟡" if rate >= 80 else "🔴"
        lines.append(f"{i}. {icon} {sup}: {rate:.0f}% ({total} inspections)")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bqc(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_quality_handlers():
    insp_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(qc_new_start, pattern="^qc_new$")],
        states={
            QC_SUPPLIER:[CallbackQueryHandler(qc_sup_cb, pattern="^qc_sup_"),
                         MessageHandler(filters.TEXT & ~filters.COMMAND, qc_sup_txt)],
            QC_ITEM:    [MessageHandler(filters.TEXT & ~filters.COMMAND, qc_item_inp)],
            QC_QTY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, qc_qty_inp)],
            QC_RESULT:  [CallbackQueryHandler(qc_result_cb, pattern="^qc_result_")],
            QC_REASON:  [MessageHandler(filters.TEXT & ~filters.COMMAND, qc_reason_inp)],
            QC_TEMP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, qc_temp_inp)],
            QC_NOTES:   [MessageHandler(filters.TEXT & ~filters.COMMAND, qc_notes_inp)],
            QC_CONFIRM: [CallbackQueryHandler(qc_confirm_cb, pattern="^qc_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, qc_cancel_handler)],
        per_message=False,
    )
    return [insp_h]


def get_quality_static_handlers():
    return [
        CallbackQueryHandler(quality_menu_handler,    pattern="^menu_quality$"),
        CallbackQueryHandler(qc_all_handler,          pattern="^qc_all$"),
        CallbackQueryHandler(qc_dashboard_handler,    pattern="^qc_dashboard$"),
        CallbackQueryHandler(qc_supplier_quality,     pattern="^qc_supplier_quality$"),
    ]
