"""
ROIN WORLD FZE — Document & Contract Management Handler
=========================================================
Phase 6:
  6A. Document Expiry Tracking — Employee_Documents tab
  6B. Contract Expiry Management — Employee_DB + Contracts_Log
  6C. Termination / Offboarding — set Status=Terminated, lock bot access, generate experience letter

Document types: work permit, residency visa, health certificate, safety certification,
first aid cert, professional license, passport, food handler cert

Alert thresholds (days): 90 → info HR, 60 → action HR+emp,
30 → HR+emp+mgr, 14 → urgent daily, 7 → critical daily+Dir, 0 → EXPIRED immediate
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler, MessageHandler, filters)
from config import get_sheet

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bhr(): return InlineKeyboardButton("↩️ HR Tools",  callback_data="menu_hr_tools")
def bdc(): return InlineKeyboardButton("↩️ Back",      callback_data="menu_doc_contracts")

DOC_TYPES = [
    "Work Permit", "Residency Visa", "Health Certificate", "Safety Certification",
    "First Aid Cert", "Professional License", "Passport", "Food Handler Cert",
]

# Conversation states
DOC_EMP_CODE  = 600
DOC_TYPE_SEL  = 601
DOC_NUMBER    = 602
DOC_ISSUE_DATE= 603
DOC_EXP_DATE  = 604
DOC_CONFIRM   = 605
TERM_CODE     = 610
CONT_ACTION   = 620
CONT_CODE     = 621


# ── Helpers ───────────────────────────────────────────────────────────────────

def _days_until(date_str):
    try:
        d = datetime.strptime(str(date_str).strip(), "%d/%m/%Y").date()
        return (d - datetime.now().date()).days
    except Exception:
        return None


def _expiry_icon(days):
    if days is None:   return "❓"
    if days < 0:       return "❌"
    if days < 14:      return "🔴"
    if days < 30:      return "🟠"
    if days < 60:      return "🟡"
    return "🟢"


def _gen_doc_id():
    ids = get_sheet("Employee_Documents").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"DOC-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


# ══════════════════════════════════════════════════════════════════
#  6. DOC & CONTRACT MAIN MENU
# ══════════════════════════════════════════════════════════════════

async def doc_contracts_menu(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("📄 Document Expiry",     callback_data="menu_doc_expiry")],
        [InlineKeyboardButton("📋 Contract Expiry",     callback_data="menu_contract_expiry")],
        [InlineKeyboardButton("🚪 Offboarding",         callback_data="menu_offboarding")],
        [bhr(), bm()],
    ]
    await q.edit_message_text("📂 Document & Contract Management\n\nSelect option:",
                               reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════
#  6A. DOCUMENT EXPIRY
# ══════════════════════════════════════════════════════════════════

async def doc_expiry_menu(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading document status...")
    try:
        rows = get_sheet("Employee_Documents").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bdc(), bm()]])); return

    now = datetime.now().date()
    expired = critical = urgent = warning = ok = 0
    for r in rows:
        if str(r.get("Status","")).strip().lower() == "renewed": continue
        d = _days_until(r.get("Expiry_Date",""))
        if d is None: continue
        if d < 0:    expired  += 1
        elif d < 14: critical += 1
        elif d < 30: urgent   += 1
        elif d < 60: warning  += 1
        else:        ok       += 1

    kb = [
        [InlineKeyboardButton(f"❌ Expired ({expired})",      callback_data="doc_list_expired")],
        [InlineKeyboardButton(f"🔴 Critical <14d ({critical})", callback_data="doc_list_critical")],
        [InlineKeyboardButton(f"🟠 Urgent <30d ({urgent})",   callback_data="doc_list_urgent")],
        [InlineKeyboardButton(f"🟡 Warning <60d ({warning})", callback_data="doc_list_warning")],
        [InlineKeyboardButton(f"🟢 OK ({ok})",                callback_data="doc_list_ok")],
        [InlineKeyboardButton("➕ Add Document",               callback_data="doc_add_start")],
        [bdc(), bm()],
    ]
    msg = (f"📄 Document Expiry Dashboard\n{'─'*28}\n"
           f"❌ Expired:  {expired}\n🔴 Critical: {critical}\n"
           f"🟠 Urgent:  {urgent}\n🟡 Warning:  {warning}\n🟢 OK:       {ok}")
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def doc_list_handler(update, context):
    q = update.callback_query; await q.answer()
    mode = q.data.replace("doc_list_","")
    await q.edit_message_text("⏳ Loading...")
    try:
        rows = get_sheet("Employee_Documents").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_contracts"), bm()]])); return

    thresholds = {"expired":(-999,-1),"critical":(0,13),"urgent":(14,29),"warning":(30,59),"ok":(60,9999)}
    lo, hi = thresholds.get(mode, (0,9999))
    filtered = []
    for r in rows:
        if str(r.get("Status","")).strip().lower() == "renewed" and mode != "ok": continue
        d = _days_until(r.get("Expiry_Date",""))
        if d is None: continue
        if lo <= d <= hi: filtered.append((r, d))
    filtered.sort(key=lambda x: x[1])

    if not filtered:
        await q.edit_message_text(f"No documents in '{mode}' status.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_expiry"), bm()]])); return

    lines = [f"📄 Documents — {mode.upper()} ({len(filtered)})\n{'─'*28}"]
    for r, d in filtered[:20]:
        icon = _expiry_icon(d)
        ec   = str(r.get("Emp_Code","?"))
        dt   = str(r.get("Document_Type","?"))
        exp  = str(r.get("Expiry_Date","?"))
        lines.append(f"{icon} {ec} | {dt} | exp:{exp} ({d}d)")
    if len(filtered) > 20: lines.append(f"... +{len(filtered)-20} more")
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_expiry"), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


# ── Add Document flow ──────────────────────────────────────────────────────────

async def doc_add_start(update, context):
    q = update.callback_query; await q.answer()
    context.user_data.clear()
    await q.edit_message_text(
        "➕ Add Document\n\nStep 1/4: Type employee code:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_expiry"), bm()]]))
    return DOC_EMP_CODE


async def doc_emp_code_inp(update, context):
    ec = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bm()]])
    # Verify exists
    try:
        found = any(str(r.get("Emp_Code","")).strip() == ec
                    for r in get_sheet("Employee_DB").get_all_records())
    except Exception: found = False
    if not found:
        await update.message.reply_text(f"❌ Employee {ec} not found. Try again:", reply_markup=bk)
        return DOC_EMP_CODE
    context.user_data["doc_ec"] = ec
    kb = [[InlineKeyboardButton(dt, callback_data=f"doc_type_{i}")] for i, dt in enumerate(DOC_TYPES)]
    kb.append([bm()])
    await update.message.reply_text(
        f"Step 2/4: Select document type for {ec}:",
        reply_markup=InlineKeyboardMarkup(kb))
    return DOC_TYPE_SEL


async def doc_type_sel(update, context):
    q = update.callback_query; await q.answer()
    idx = int(q.data.replace("doc_type_",""))
    context.user_data["doc_type"] = DOC_TYPES[idx]
    await q.edit_message_text(
        f"Step 3/4: Type document number (or '-' if none):",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return DOC_NUMBER


async def doc_number_inp(update, context):
    context.user_data["doc_number"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 4a/4: Issue date (DD/MM/YYYY) or '-':",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return DOC_ISSUE_DATE


async def doc_issue_date_inp(update, context):
    context.user_data["doc_issue"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 4b/4: Expiry date (DD/MM/YYYY):",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return DOC_EXP_DATE


async def doc_exp_date_inp(update, context):
    exp_str = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bm()]])
    try: datetime.strptime(exp_str, "%d/%m/%Y")
    except Exception:
        await update.message.reply_text("⚠️ Invalid date. Use DD/MM/YYYY:", reply_markup=bk)
        return DOC_EXP_DATE
    context.user_data["doc_exp"] = exp_str
    d = _days_until(exp_str)
    icon = _expiry_icon(d)
    msg = (f"📄 Add Document — Summary\n{'─'*28}\n"
           f"Employee: {context.user_data['doc_ec']}\n"
           f"Type:     {context.user_data['doc_type']}\n"
           f"Number:   {context.user_data['doc_number']}\n"
           f"Issue:    {context.user_data['doc_issue']}\n"
           f"Expiry:   {exp_str} {icon} ({d}d)\n\n"
           f"Confirm?")
    kb = [[InlineKeyboardButton("✅ Save", callback_data="doc_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="doc_cancel")],
          [bm()]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return DOC_CONFIRM


async def doc_confirm(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "doc_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return ConversationHandler.END
    try:
        doc_id = _gen_doc_id()
        now    = datetime.now().strftime("%d/%m/%Y %H:%M")
        d      = _days_until(context.user_data["doc_exp"])
        ws     = get_sheet("Employee_Documents")
        # Cols: Doc_ID, Emp_Code, Full_Name(VLOOKUP=""), Department(VLOOKUP=""),
        #       Document_Type, Doc_Number, Issue_Date, Expiry_Date,
        #       Days_Until_Expiry(formula=""), Status(formula=""), Notes
        row    = [doc_id, context.user_data["doc_ec"], "", "",
                  context.user_data["doc_type"], context.user_data["doc_number"],
                  context.user_data["doc_issue"], context.user_data["doc_exp"],
                  "", "", ""]
        ws.append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Document added!\nID: {doc_id}\nType: {context.user_data['doc_type']}\nExpiry: {context.user_data['doc_exp']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_expiry"), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


async def doc_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_doc_add_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(doc_add_start, pattern="^doc_add_start$")],
        states={
            DOC_EMP_CODE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, doc_emp_code_inp),
                            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
            DOC_TYPE_SEL:  [CallbackQueryHandler(doc_type_sel, pattern="^doc_type_"),
                            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
            DOC_NUMBER:    [MessageHandler(filters.TEXT & ~filters.COMMAND, doc_number_inp)],
            DOC_ISSUE_DATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, doc_issue_date_inp)],
            DOC_EXP_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, doc_exp_date_inp)],
            DOC_CONFIRM:   [CallbackQueryHandler(doc_confirm, pattern="^doc_(confirm|cancel)$"),
                            CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, doc_cancel_handler)],
        per_message=False,
    )


# ══════════════════════════════════════════════════════════════════
#  6B. CONTRACT EXPIRY
# ══════════════════════════════════════════════════════════════════

async def contract_expiry_menu(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading contract status...")
    try:
        rows = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bdc(), bm()]])); return

    active = [r for r in rows if str(r.get("Status","")).strip() not in ("Terminated",)]
    expired = []; critical = []; urgent = []; warning = []; ok_list = []
    for r in active:
        d = _days_until(r.get("Contract_Expiry_Date",""))
        if d is None: continue
        if d < 0:    expired.append((r, d))
        elif d < 14: critical.append((r, d))
        elif d < 30: urgent.append((r, d))
        elif d < 60: warning.append((r, d))
        else:        ok_list.append((r, d))

    lines = [f"📋 Contract Expiry\n{'─'*28}",
             f"❌ Expired:   {len(expired)}",
             f"🔴 <14 days:  {len(critical)}",
             f"🟠 <30 days:  {len(urgent)}",
             f"🟡 <60 days:  {len(warning)}",
             f"🟢 OK:        {len(ok_list)}"]
    msg = "\n".join(lines)

    # Show the urgent ones inline
    if critical or urgent:
        msg += f"\n\n⚠️ Needs attention:"
        for r, d in (critical + urgent)[:10]:
            ec   = str(r.get("Emp_Code",""))
            nm   = str(r.get("Full_Name",""))[:20]
            exp  = str(r.get("Contract_Expiry_Date",""))
            msg += f"\n{_expiry_icon(d)} {nm} ({ec}) — {d}d ({exp})"

    kb = [
        [InlineKeyboardButton("📋 All Expiring This Month",  callback_data="contract_list_month")],
        [InlineKeyboardButton("❌ Expired",                  callback_data="contract_list_expired")],
        [InlineKeyboardButton("📝 Log Decision",             callback_data="contract_log_decision")],
        [bdc(), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def contract_list_handler(update, context):
    q = update.callback_query; await q.answer()
    mode = q.data.replace("contract_list_","")
    await q.edit_message_text("⏳ Loading...")
    try:
        rows = get_sheet("Employee_DB").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_doc_contracts"), bm()]])); return

    now = datetime.now().date()
    month_end = datetime(now.year, now.month + 1 if now.month < 12 else 1, 1).date() \
        if now.month < 12 else datetime(now.year + 1, 1, 1).date()

    filtered = []
    for r in rows:
        if str(r.get("Status","")).strip() == "Terminated": continue
        d = _days_until(r.get("Contract_Expiry_Date",""))
        if d is None: continue
        if mode == "expired" and d < 0: filtered.append((r, d))
        elif mode == "month" and 0 <= d <= (month_end - now).days: filtered.append((r, d))
    filtered.sort(key=lambda x: x[1])

    if not filtered:
        await q.edit_message_text("No contracts matching this filter.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_contract_expiry"), bm()]])); return

    lines = [f"📋 Contracts — {mode.upper()} ({len(filtered)})\n{'─'*28}"]
    for r, d in filtered[:20]:
        icon = _expiry_icon(d)
        lines.append(f"{icon} {r.get('Emp_Code','')} {r.get('Full_Name','')[:20]} | exp:{r.get('Contract_Expiry_Date','')} ({d}d)")
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_contract_expiry"), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def contract_log_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "📝 Log Contract Decision\n\nType employee code:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_contract_expiry"), bm()]]))
    return CONT_CODE


async def contract_code_inp(update, context):
    ec = update.message.text.strip()
    bk = InlineKeyboardMarkup([[bm()]])
    context.user_data["cont_ec"] = ec
    kb = [
        [InlineKeyboardButton("✅ Renew",    callback_data="cont_dec_Renew")],
        [InlineKeyboardButton("🚪 Terminate",callback_data="cont_dec_Terminate")],
        [InlineKeyboardButton("📋 Amend",    callback_data="cont_dec_Amend")],
        [bm()],
    ]
    await update.message.reply_text(f"Contract decision for {ec}:", reply_markup=InlineKeyboardMarkup(kb))
    return CONT_ACTION


async def contract_action_sel(update, context):
    q = update.callback_query; await q.answer()
    decision = q.data.replace("cont_dec_","")
    ec = context.user_data.get("cont_ec","?")
    try:
        ws  = get_sheet("Employee_History")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        log_id = f"CL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        event_type = "Contract_Termination" if decision == "Terminate" else "Contract_Renewal"
        # Cols: Log_ID, Emp_Code, Full_Name(VLOOKUP=""), Department(VLOOKUP=""),
        #       Event_Type, Event_Date, Details, Old_Value, New_Value,
        #       Approved_By, Eval_Score, Drive_Link, Notes
        ws.append_row([log_id, ec, "", "", event_type, now, decision, "", "", "", "", "", ""],
                      value_input_option="USER_ENTERED")
        if decision == "Terminate":
            # Lock user in User_Registry
            ur_ws = get_sheet("User_Registry")
            ur_rows = ur_ws.get_all_values()
            for i, row in enumerate(ur_rows):
                if i == 0: continue
                if row[0].strip() == ec:
                    try: ur_ws.update_cell(i+1, 6, "Terminated")
                    except Exception: pass
                    break
            # Set Status=Terminated in Employee_DB
            db_ws = get_sheet("Employee_DB")
            db_rows = db_ws.get_all_records()
            for i, r in enumerate(db_rows):
                if str(r.get("Emp_Code","")).strip() == ec:
                    try: db_ws.update_cell(i+2, list(r.keys()).index("Status")+1, "Terminated")
                    except Exception: pass
                    break
        await q.edit_message_text(
            f"✅ Logged: {decision} for {ec}\nID: {log_id}\nDate: {now}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_contract_expiry"), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


def get_contract_log_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(contract_log_start, pattern="^contract_log_decision$")],
        states={
            CONT_CODE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, contract_code_inp),
                          CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
            CONT_ACTION: [CallbackQueryHandler(contract_action_sel, pattern="^cont_dec_"),
                          CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, lambda u,c: ConversationHandler.END)],
        per_message=False,
    )


# ══════════════════════════════════════════════════════════════════
#  6C. OFFBOARDING
# ══════════════════════════════════════════════════════════════════

async def offboarding_menu(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "🚪 Offboarding\n\nTermination/offboarding is handled through:\n\n"
        "📋 Contract Expiry → Log Decision → Terminate\n\n"
        "This automatically:\n"
        "• Locks bot access\n"
        "• Sets Status = Terminated in Employee_DB\n"
        "• Logs in Employee_History\n\n"
        "Experience letter generation: use 📝 Generate Letters.",
        reply_markup=InlineKeyboardMarkup([[bdc(), bm()]]))


def get_doc_contract_static_handlers():
    return [
        CallbackQueryHandler(doc_contracts_menu,      pattern="^menu_doc_contracts$"),
        CallbackQueryHandler(doc_expiry_menu,         pattern="^menu_doc_expiry$"),
        CallbackQueryHandler(doc_list_handler,        pattern="^doc_list_"),
        CallbackQueryHandler(contract_expiry_menu,    pattern="^menu_contract_expiry$"),
        CallbackQueryHandler(contract_list_handler,   pattern="^contract_list_"),
        CallbackQueryHandler(offboarding_menu,        pattern="^menu_offboarding$"),
    ]
