"""
ROIN WORLD FZE — Supply & Purchasing Management Handler
=========================================================
Phase 12:
  12A. Purchase Requests (PR creation & approval)
  12B. Supplier Database (view & add)
  12C. Budget Tracker
  12D. Supply Report

Sheets:
  Purchase_Requests: PR_ID, Date, Emp_Code, Department, Item, Quantity, Unit,
                     Estimated_Cost, Supplier, Priority, Status, Approver,
                     Approved_Date, Notes
  Suppliers:         Supplier_ID, Name, Category, Contact_Person, Phone,
                     Email, Payment_Terms, Rating, Notes
  Budget_Tracker:    Budget_ID, Department, Category, Budget_AED, Spent_AED,
                     Period, Notes
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm():  return InlineKeyboardButton("↩️ Main Menu",  callback_data="back_to_menu")
def _bsp(): return InlineKeyboardButton("↩️ Supply",     callback_data="menu_supply")


async def supply_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("🛒 New Purchase Request", callback_data="menu_purchase_requests")],
        [InlineKeyboardButton("📋 My Requests",          callback_data="menu_my_prs")],
        [InlineKeyboardButton("✅ Approve Requests",     callback_data="menu_approve_prs")],
        [InlineKeyboardButton("🏭 Supplier Database",    callback_data="menu_supplier_db")],
        [InlineKeyboardButton("💰 Budget Tracker",       callback_data="menu_budget_tracker")],
        [InlineKeyboardButton("📊 Supply Report",        callback_data="menu_supply_report")],
        [_bm()],
    ]
    await q.edit_message_text("🛒 Supply & Purchasing\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))

# ── ConversationHandler states ────────────────────────────────────────────────
PR_ITEM     = 1200
PR_QTY      = 1201
PR_COST     = 1202
PR_SUPPLIER = 1203
PR_PRIORITY = 1204
PR_CONFIRM  = 1205

SUP_NAME    = 1210
SUP_CAT     = 1211
SUP_CONTACT = 1212
SUP_PHONE   = 1213
SUP_TERMS   = 1214
SUP_CONFIRM = 1215

PRIORITIES = ["Critical", "High", "Medium", "Low"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _gen_pr_id():
    ids = get_sheet("Purchase_Requests").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"PR-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _gen_sup_id():
    ids = get_sheet("Suppliers").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"SUP-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _get_emp_info(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _priority_icon(p):
    return {"Critical":"🔴","High":"🟠","Medium":"🟡","Low":"🟢"}.get(str(p).strip(),"❓")


def _status_icon(s):
    return {"Pending":"⏳","Approved":"✅","Rejected":"❌","Ordered":"📦",
            "Received":"🏁","Cancelled":"🚫"}.get(str(s).strip(),"❓")


# ── Purchase Request flow ─────────────────────────────────────────────────────
async def pr_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "🛒 New Purchase Request\n\nDescribe the item / service needed:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return PR_ITEM


async def pr_item_inp(update, context):
    context.user_data["pr_item"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter quantity and unit (e.g. '5 boxes' or '10 kg'):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return PR_QTY


async def pr_qty_inp(update, context):
    context.user_data["pr_qty"] = update.message.text.strip()
    await update.message.reply_text(
        "Estimated cost in AED (enter 0 if unknown):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return PR_COST


async def pr_cost_inp(update, context):
    text = update.message.text.strip()
    bk   = InlineKeyboardMarkup([[_bm()]])
    try: c = float(text); assert c >= 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid amount (0 or more):", reply_markup=bk)
        return PR_COST
    context.user_data["pr_cost"] = c
    await update.message.reply_text(
        "Preferred supplier name (or '-' if unknown):",
        reply_markup=bk
    )
    return PR_SUPPLIER


async def pr_supplier_inp(update, context):
    context.user_data["pr_supplier"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(f"{_priority_icon(p)} {p}", callback_data=f"pr_pri_{p}")]
          for p in PRIORITIES]
    kb.append([_bm()])
    await update.message.reply_text("Select priority:", reply_markup=InlineKeyboardMarkup(kb))
    return PR_PRIORITY


async def pr_priority_cb(update, context):
    q = update.callback_query; await q.answer()
    pri = q.data.replace("pr_pri_","")
    context.user_data["pr_priority"] = pri
    item = context.user_data.get("pr_item","")
    qty  = context.user_data.get("pr_qty","")
    cost = context.user_data.get("pr_cost",0)
    sup  = context.user_data.get("pr_supplier","")
    summary = (f"🛒 Purchase Request\n{'─'*24}\n"
               f"Item:      {item}\n"
               f"Quantity:  {qty}\n"
               f"Est. Cost: {cost} AED\n"
               f"Supplier:  {sup}\n"
               f"Priority:  {_priority_icon(pri)} {pri}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="pr_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="pr_cancel")],
          [_bm()]]
    await q.edit_message_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return PR_CONFIRM


async def pr_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "pr_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_info(str(q.from_user.id))
    try:
        emp_rows = get_sheet("Employee_DB").get_all_records()
        dept = next((r.get("Department","") for r in emp_rows
                     if str(r.get("Emp_Code","")).strip() == str(ec)), "")
    except Exception:
        dept = ""
    try:
        prid = _gen_pr_id()
        now  = datetime.now().strftime("%d/%m/%Y %H:%M")
        row  = [prid, now, ec or "",
                "",  # col D: Manager_Code (filled during approval)
                "",  # col E: Manager_Name (VLOOKUP from col D)
                context.user_data.get("pr_item",""),
                context.user_data.get("pr_qty",""),
                "",   # Unit (embedded in qty field)
                context.user_data.get("pr_cost",""),
                context.user_data.get("pr_supplier",""),
                context.user_data.get("pr_priority",""),
                "Pending", "", "", ""]
        get_sheet("Purchase_Requests").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Purchase request submitted!\nID: {prid}\nStatus: Pending approval",
            reply_markup=InlineKeyboardMarkup([[_bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def pr_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── View My Purchase Requests ─────────────────────────────────────────────────
async def my_prs_handler(update, context):
    q = update.callback_query; await q.answer()
    ec = _get_emp_info(str(q.from_user.id))
    await q.edit_message_text("⏳ Loading...")
    try:
        rows = get_sheet("Purchase_Requests").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    mine = [r for r in rows if str(r.get("Emp_Code","")).strip() == str(ec)]
    if not mine:
        await q.edit_message_text("📋 No purchase requests found.",
            reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    lines = [f"🛒 My Purchase Requests ({len(mine)})\n{'─'*24}"]
    for r in mine[-10:]:
        lines.append(f"{_status_icon(r.get('Status',''))} {r.get('PR_ID','')} | "
                     f"{_priority_icon(r.get('Priority',''))} {r.get('Item','')} | "
                     f"{r.get('Status','')}")
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[_bm()]]))


# ── Approve PRs (Supply_Manager) ──────────────────────────────────────────────
async def approve_prs_menu(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading pending PRs...")
    try:
        rows = get_sheet("Purchase_Requests").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    pending = [r for r in rows if str(r.get("Status","")).strip() == "Pending"]
    if not pending:
        await q.edit_message_text("✅ No pending purchase requests.",
            reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    lines = [f"🛒 Pending PRs ({len(pending)})\n{'─'*24}"]
    kb = []
    for r in pending[:15]:
        prid = str(r.get("PR_ID",""))
        lines.append(f"{_priority_icon(r.get('Priority',''))} {prid} | "
                     f"{r.get('Emp_Code','')} | {r.get('Item','')} | {r.get('Estimated_Cost','')} AED")
        kb.append([InlineKeyboardButton(f"📋 {prid}", callback_data=f"pr_view_{prid}")])
    kb.append([_bm()])
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def pr_view_cb(update, context):
    q = update.callback_query; await q.answer()
    prid = q.data.replace("pr_view_","")
    try:
        rows = get_sheet("Purchase_Requests").get_all_records()
        r = next((x for x in rows if str(x.get("PR_ID","")) == prid), None)
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not r:
        await q.edit_message_text("Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    msg = (f"🛒 PR: {prid}\n{'─'*24}\n"
           f"Employee:  {r.get('Emp_Code','')}\n"
           f"Dept:      {r.get('Department','')}\n"
           f"Item:      {r.get('Item','')}\n"
           f"Quantity:  {r.get('Quantity','')}\n"
           f"Est. Cost: {r.get('Estimated_Cost','')} AED\n"
           f"Supplier:  {r.get('Supplier','')}\n"
           f"Priority:  {_priority_icon(r.get('Priority',''))} {r.get('Priority','')}\n"
           f"Status:    {r.get('Status','')}")
    kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"pr_approve_{prid}"),
           InlineKeyboardButton("❌ Reject",  callback_data=f"pr_reject_{prid}")],
          [InlineKeyboardButton("↩️ Back", callback_data="menu_approve_prs"), _bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def pr_approve_cb(update, context):
    q = update.callback_query; await q.answer()
    action = "Approved" if "approve" in q.data else "Rejected"
    prid   = q.data.replace("pr_approve_","").replace("pr_reject_","")
    ec     = _get_emp_info(str(q.from_user.id))
    try:
        ws   = get_sheet("Purchase_Requests")
        rows = ws.get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == prid:
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                ws.update_cell(i+1, 11, action)
                ws.update_cell(i+1, 12, ec or "")
                ws.update_cell(i+1, 13, now)
                break
        await q.edit_message_text(
            f"{'✅' if action=='Approved' else '❌'} PR {prid} {action}.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_approve_prs"), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))


# ── Supplier Database ─────────────────────────────────────────────────────────
async def supplier_db_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading suppliers...")
    try:
        rows = get_sheet("Suppliers").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not rows:
        await q.edit_message_text(
            "🏭 No suppliers registered yet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Supplier", callback_data="menu_add_supplier")],
                [_bm()]
            ])
        ); return
    lines = [f"🏭 Supplier DB ({len(rows)})\n{'─'*28}"]
    for r in rows[:20]:
        rating = str(r.get("Rating","")).strip()
        stars  = "⭐" * min(int(rating), 5) if rating.isdigit() else rating or "-"
        lines.append(f"• {r.get('Name','')} [{r.get('Category','')}] {stars}")
    if len(rows) > 20: lines.append(f"... +{len(rows)-20} more")
    kb = [[InlineKeyboardButton("➕ Add Supplier", callback_data="menu_add_supplier")],
          [_bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


# ── Add Supplier flow ─────────────────────────────────────────────────────────
async def add_supplier_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "🏭 Add Supplier\n\nEnter supplier name:",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return SUP_NAME


async def sup_name_inp(update, context):
    context.user_data["sup_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Enter category (e.g. Food, Cleaning, Equipment, Stationery):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return SUP_CAT


async def sup_cat_inp(update, context):
    context.user_data["sup_cat"] = update.message.text.strip()
    await update.message.reply_text(
        "Contact person name (or '-'):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return SUP_CONTACT


async def sup_contact_inp(update, context):
    context.user_data["sup_contact"] = update.message.text.strip()
    await update.message.reply_text(
        "Phone number (or '-'):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return SUP_PHONE


async def sup_phone_inp(update, context):
    context.user_data["sup_phone"] = update.message.text.strip()
    await update.message.reply_text(
        "Payment terms (e.g. '30 days', 'Cash', 'COD'):",
        reply_markup=InlineKeyboardMarkup([[_bm()]])
    )
    return SUP_TERMS


async def sup_terms_inp(update, context):
    context.user_data["sup_terms"] = update.message.text.strip()
    nm   = context.user_data.get("sup_name","")
    cat  = context.user_data.get("sup_cat","")
    con  = context.user_data.get("sup_contact","")
    ph   = context.user_data.get("sup_phone","")
    terms= context.user_data.get("sup_terms","")
    summary = (f"🏭 New Supplier\n{'─'*24}\n"
               f"Name:    {nm}\nCategory:{cat}\n"
               f"Contact: {con}\nPhone:   {ph}\nTerms:   {terms}")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="sup_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="sup_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return SUP_CONFIRM


async def sup_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "sup_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    try:
        sid = _gen_sup_id()
        row = [sid,
               context.user_data.get("sup_name",""),
               context.user_data.get("sup_cat",""),
               context.user_data.get("sup_contact",""),
               context.user_data.get("sup_phone",""),
               "",   # Email
               context.user_data.get("sup_terms",""),
               "",   # Rating
               ""]   # Notes
        get_sheet("Suppliers").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Supplier saved!\nID: {sid}",
            reply_markup=InlineKeyboardMarkup([[_bm()]])
        )
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def sup_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── Budget Tracker ────────────────────────────────────────────────────────────
async def budget_tracker_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading budgets...")
    try:
        rows = get_sheet("Budget_Tracker").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not rows:
        await q.edit_message_text("💰 No budget data found.",
            reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    lines = [f"💰 Budget Tracker\n{'─'*28}"]
    total_budget = 0; total_spent = 0
    for r in rows:
        budget = float(r.get("Budget_AED",0) or 0)
        spent  = float(r.get("Spent_AED",0) or 0)
        remain = budget - spent
        pct    = int((spent / budget) * 100) if budget > 0 else 0
        icon   = "🔴" if pct >= 90 else "🟡" if pct >= 70 else "🟢"
        total_budget += budget; total_spent += spent
        lines.append(f"{icon} {r.get('Department','')} [{r.get('Category','')}]\n"
                     f"   Budget: {budget:.0f} | Spent: {spent:.0f} | Left: {remain:.0f} ({pct}%)")
    lines.append(f"{'─'*28}")
    lines.append(f"TOTAL: {total_budget:.0f} AED | Spent: {total_spent:.0f} AED | "
                 f"Left: {total_budget-total_spent:.0f} AED")
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[_bm()]]))


# ── Supply Report ─────────────────────────────────────────────────────────────
async def supply_report_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating report...")
    try:
        prs  = get_sheet("Purchase_Requests").get_all_records()
        sups = get_sheet("Suppliers").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    total  = len(prs)
    pending  = sum(1 for r in prs if str(r.get("Status","")) == "Pending")
    approved = sum(1 for r in prs if str(r.get("Status","")) == "Approved")
    rejected = sum(1 for r in prs if str(r.get("Status","")) == "Rejected")
    ordered  = sum(1 for r in prs if str(r.get("Status","")) == "Ordered")
    total_cost = sum(float(r.get("Estimated_Cost",0) or 0)
                     for r in prs if str(r.get("Status","")) in ("Approved","Ordered","Received"))
    by_priority = {}
    for r in prs:
        p = str(r.get("Priority","")).strip() or "Unknown"
        by_priority[p] = by_priority.get(p, 0) + 1
    lines = [f"📊 Supply Report\n{'─'*28}",
             f"Total PRs:     {total}",
             f"⏳ Pending:     {pending}",
             f"✅ Approved:    {approved}",
             f"❌ Rejected:    {rejected}",
             f"📦 Ordered:     {ordered}",
             f"💰 Approved Cost: {total_cost:.2f} AED",
             f"{'─'*28}",
             f"By Priority:"]
    for p, cnt in sorted(by_priority.items()):
        lines.append(f"  {_priority_icon(p)} {p}: {cnt}")
    lines.append(f"{'─'*28}")
    lines.append(f"🏭 Suppliers: {len(sups)}")
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup([[_bm()]]))


# ── Warehouse shortcut (from Supply_Manager menu) ─────────────────────────────
async def supply_warehouse_handler(update, context):
    q = update.callback_query; await q.answer()
    from warehouse_handler import wh_menu_handler
    return await wh_menu_handler(update, context)


# ── Handler registration ──────────────────────────────────────────────────────
def get_supply_handlers():
    pr_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(pr_start, pattern="^menu_purchase_requests$")],
        states={
            PR_ITEM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pr_item_inp)],
            PR_QTY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, pr_qty_inp)],
            PR_COST:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pr_cost_inp)],
            PR_SUPPLIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, pr_supplier_inp)],
            PR_PRIORITY: [CallbackQueryHandler(pr_priority_cb, pattern="^pr_pri_")],
            PR_CONFIRM:  [CallbackQueryHandler(pr_confirm_cb, pattern="^pr_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, pr_cancel_handler)],
        per_message=False,
    )
    sup_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_supplier_start, pattern="^menu_add_supplier$")],
        states={
            SUP_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_name_inp)],
            SUP_CAT:     [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_cat_inp)],
            SUP_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_contact_inp)],
            SUP_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_phone_inp)],
            SUP_TERMS:   [MessageHandler(filters.TEXT & ~filters.COMMAND, sup_terms_inp)],
            SUP_CONFIRM: [CallbackQueryHandler(sup_confirm_cb, pattern="^sup_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, sup_cancel_handler)],
        per_message=False,
    )
    return [pr_handler, sup_handler]


def get_supply_static_handlers():
    return [
        CallbackQueryHandler(supply_menu_handler,    pattern="^menu_supply$"),
        CallbackQueryHandler(my_prs_handler,         pattern="^menu_my_prs$"),
        CallbackQueryHandler(approve_prs_menu,       pattern="^menu_approve_prs$"),
        CallbackQueryHandler(pr_view_cb,             pattern="^pr_view_"),
        CallbackQueryHandler(pr_approve_cb,          pattern="^pr_(approve|reject)_"),
        CallbackQueryHandler(supplier_db_handler,    pattern="^menu_supplier_db$"),
        CallbackQueryHandler(budget_tracker_handler, pattern="^menu_budget_tracker$"),
        CallbackQueryHandler(supply_report_handler,  pattern="^menu_supply_report$"),
        CallbackQueryHandler(supply_warehouse_handler,pattern="^menu_warehouse$"),
    ]
