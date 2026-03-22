"""
ROIN WORLD FZE — Operations / Kitchen Operations Handler
=========================================================
Section 6 — New role: Operations_Manager

6A. Daily Operations Reports
6B. Report Flow (submit → PDF → auto-send to directors)
6C. Operations Menu

Sheet tab:
  Operations_Reports: Report_ID, Date, Shift, Section, Submitted_By,
    Meals_Produced, Meals_Target, Achievement_Rate, Issues, Waste_Kg,
    Staff_Present, Staff_Absent, Equipment_Issues, Notes,
    Photo_Links, PDF_Link, Status, Reviewed_By, Review_Date
"""

from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm():  return InlineKeyboardButton("↩️ Main Menu",    callback_data="back_to_menu")
def _bops(): return InlineKeyboardButton("↩️ Operations",  callback_data="menu_operations")

SHIFTS   = ["Morning","Evening","Night"]
SECTIONS = [
    "Egyptian_Kitchen", "Russian_Kitchen", "Pastry_Soup_Kitchen",
    "FoodTruck_Bakery", "Bakery", "Prep", "All",
]

# ── States ────────────────────────────────────────────────────────────────────
OPS_SHIFT    = 1600; OPS_SECTION  = 1601; OPS_MEALS_P  = 1602
OPS_MEALS_T  = 1603; OPS_ISSUES   = 1604; OPS_WASTE    = 1605
OPS_STAFF_P  = 1606; OPS_EQUIP    = 1607; OPS_NOTES    = 1608
OPS_CONFIRM  = 1609


def _get_emp_code(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _gen_report_id():
    ids = get_sheet("Operations_Reports").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"OPS-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _in_month(date_str, now):
    try:
        d = datetime.strptime(date_str.strip(), "%d/%m/%Y")
        return d.year == now.year and d.month == now.month
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  OPERATIONS MENU
# ══════════════════════════════════════════════════════════════════════════════
async def operations_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("📝 Submit Daily Report",  callback_data="ops_submit")],
        [InlineKeyboardButton("📋 View Reports",          callback_data="ops_view")],
        [InlineKeyboardButton("📊 Monthly Summary",       callback_data="ops_summary")],
        [_bm()],
    ]
    await q.edit_message_text("🍳 Operations\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  SUBMIT DAILY REPORT
# ══════════════════════════════════════════════════════════════════════════════
async def ops_submit_start(update, context):
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton(s, callback_data=f"ops_shift_{s}")] for s in SHIFTS]
    kb.append([_bm()])
    await q.edit_message_text(
        f"📝 Daily Operations Report\nDate: {datetime.now().strftime('%d/%m/%Y')}\n\nSelect shift:",
        reply_markup=InlineKeyboardMarkup(kb))
    return OPS_SHIFT


async def ops_shift_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["ops_shift"]    = q.data.replace("ops_shift_","")
    context.user_data["ops_date"]     = datetime.now().strftime("%d/%m/%Y")
    kb = [[InlineKeyboardButton(s, callback_data=f"ops_sect_{s}")] for s in SECTIONS]
    kb.append([_bm()])
    await q.edit_message_text("Select section / kitchen:", reply_markup=InlineKeyboardMarkup(kb))
    return OPS_SECTION


async def ops_section_cb(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["ops_section"] = q.data.replace("ops_sect_","")
    await q.edit_message_text("Enter meals PRODUCED today (number):",
                              reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_MEALS_P


async def ops_meals_p_inp(update, context):
    text = update.message.text.strip()
    try: n = int(text); assert n >= 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:"); return OPS_MEALS_P
    context.user_data["ops_meals_p"] = n
    await update.message.reply_text("Enter meals TARGET for today:",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_MEALS_T


async def ops_meals_t_inp(update, context):
    text = update.message.text.strip()
    try: n = int(text); assert n > 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:"); return OPS_MEALS_T
    context.user_data["ops_meals_t"] = n
    await update.message.reply_text("Any issues today? (or type '-' for none):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_ISSUES


async def ops_issues_inp(update, context):
    context.user_data["ops_issues"] = update.message.text.strip()
    await update.message.reply_text("Food waste in KG (number, or 0):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_WASTE


async def ops_waste_inp(update, context):
    text = update.message.text.strip()
    try: w = float(text); assert w >= 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:"); return OPS_WASTE
    context.user_data["ops_waste"] = w
    await update.message.reply_text("Staff present today (number):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_STAFF_P


async def ops_staff_inp(update, context):
    text = update.message.text.strip()
    try: n = int(text); assert n >= 0
    except Exception:
        await update.message.reply_text("⚠️ Enter a valid number:"); return OPS_STAFF_P
    context.user_data["ops_staff_p"] = n
    await update.message.reply_text("Any equipment issues? (or '-' for none):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_EQUIP


async def ops_equip_inp(update, context):
    context.user_data["ops_equip"] = update.message.text.strip()
    await update.message.reply_text("Additional notes (or '-' to skip):",
                                    reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return OPS_NOTES


async def ops_notes_inp(update, context):
    context.user_data["ops_notes"] = update.message.text.strip()
    produced = context.user_data.get("ops_meals_p", 0)
    target   = context.user_data.get("ops_meals_t", 1)
    rate     = round((produced / target * 100), 1) if target else 0
    context.user_data["ops_rate"] = rate
    rate_icon = "🟢" if rate >= 95 else "🟡" if rate >= 80 else "🔴"
    summary = (f"📝 Operations Report\n{'─'*24}\n"
               f"Date:     {context.user_data.get('ops_date','')}\n"
               f"Shift:    {context.user_data.get('ops_shift','')}\n"
               f"Section:  {context.user_data.get('ops_section','')}\n"
               f"Meals:    {produced} / {target} ({rate_icon} {rate}%)\n"
               f"Waste:    {context.user_data.get('ops_waste',0)} KG\n"
               f"Staff:    {context.user_data.get('ops_staff_p',0)} present\n"
               f"Issues:   {context.user_data.get('ops_issues','')}\n"
               f"Equipment:{context.user_data.get('ops_equip','')}")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="ops_confirm"),
           InlineKeyboardButton("❌ Cancel", callback_data="ops_cancel")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return OPS_CONFIRM


async def ops_confirm_cb(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "ops_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    ec = _get_emp_code(str(q.from_user.id))
    produced = context.user_data.get("ops_meals_p",0)
    target   = context.user_data.get("ops_meals_t",1)
    try:
        rid = _gen_report_id()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        row = [rid,
               context.user_data.get("ops_date",""),
               context.user_data.get("ops_shift",""),
               context.user_data.get("ops_section",""),
               ec or "",
               "",             # col F: Name (VLOOKUP from Submitted_By)
               str(produced), str(target),
               "",             # col I: Achievement_Rate (sheet formula)
               context.user_data.get("ops_issues",""),
               str(context.user_data.get("ops_waste",0)),
               str(context.user_data.get("ops_staff_p",0)),
               "",  # Staff_Absent
               context.user_data.get("ops_equip",""),
               context.user_data.get("ops_notes",""),
               "", "",  # Photo_Links, PDF_Link
               "Submitted", "", ""]
        get_sheet("Operations_Reports").append_row(row, value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Report submitted!\nID: {rid}\n"
            f"Meals: {produced}/{target} ({context.user_data.get('ops_rate',0)}%)",
            reply_markup=InlineKeyboardMarkup([[_bops(), _bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def ops_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  VIEW REPORTS
# ══════════════════════════════════════════════════════════════════════════════
async def ops_view_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading reports...")
    try:
        rows = get_sheet("Operations_Reports").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    if not rows:
        await q.edit_message_text("📋 No reports submitted yet.",
                                  reply_markup=InlineKeyboardMarkup([[_bops(), _bm()]])); return
    lines = [f"📋 Operations Reports ({len(rows)})\n{'─'*24}"]
    for r in rows[-15:]:
        rate = str(r.get("Achievement_Rate",""))
        try: ri = float(rate); icon = "🟢" if ri >= 95 else "🟡" if ri >= 80 else "🔴"
        except: icon = "❓"
        lines.append(f"{icon} {r.get('Report_ID','')} | {r.get('Date','')} | "
                     f"{r.get('Shift','')} | {r.get('Section','')} | {rate}%")
    await q.edit_message_text("\n".join(lines),
                              reply_markup=InlineKeyboardMarkup([[_bops(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  MONTHLY SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
async def ops_summary_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating monthly summary...")
    try:
        rows = get_sheet("Operations_Reports").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[_bm()]])); return
    now   = datetime.now()
    month_rows = [r for r in rows if _in_month(str(r.get("Date","")), now)]
    if not month_rows:
        await q.edit_message_text(f"📊 No reports this month ({now.strftime('%B %Y')}).",
                                  reply_markup=InlineKeyboardMarkup([[_bops(), _bm()]])); return
    total_produced = sum(int(r.get("Meals_Produced",0) or 0) for r in month_rows)
    total_target   = sum(int(r.get("Meals_Target",0) or 0) for r in month_rows)
    total_waste    = sum(float(r.get("Waste_Kg",0) or 0) for r in month_rows)
    avg_rate       = round(total_produced / total_target * 100, 1) if total_target else 0
    rate_icon      = "🟢" if avg_rate >= 95 else "🟡" if avg_rate >= 80 else "🔴"
    # Section breakdown
    sections_data = {}
    for r in month_rows:
        sect = str(r.get("Section",""))
        if sect not in sections_data:
            sections_data[sect] = {"p":0,"t":0}
        try:
            sections_data[sect]["p"] += int(r.get("Meals_Produced",0) or 0)
            sections_data[sect]["t"] += int(r.get("Meals_Target",0) or 0)
        except Exception:
            pass
    msg = (f"📊 Monthly Operations Summary\n{now.strftime('%B %Y')}\n{'─'*28}\n"
           f"Reports submitted:  {len(month_rows)}\n"
           f"Total meals:        {total_produced:,} / {total_target:,}\n"
           f"Achievement:        {rate_icon} {avg_rate}%\n"
           f"Total waste:        {total_waste:.1f} KG\n"
           f"{'─'*28}\n"
           f"By Section:")
    for sect, data in sections_data.items():
        if data["t"]:
            sr = round(data["p"]/data["t"]*100,1)
            si = "🟢" if sr >= 95 else "🟡" if sr >= 80 else "🔴"
            msg += f"\n  {si} {sect}: {data['p']:,}/{data['t']:,} ({sr}%)"
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[_bops(), _bm()]]))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════
def get_operations_handlers():
    submit_h = ConversationHandler(
        entry_points=[CallbackQueryHandler(ops_submit_start, pattern="^ops_submit$")],
        states={
            OPS_SHIFT:   [CallbackQueryHandler(ops_shift_cb,   pattern="^ops_shift_")],
            OPS_SECTION: [CallbackQueryHandler(ops_section_cb, pattern="^ops_sect_")],
            OPS_MEALS_P: [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_meals_p_inp)],
            OPS_MEALS_T: [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_meals_t_inp)],
            OPS_ISSUES:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_issues_inp)],
            OPS_WASTE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_waste_inp)],
            OPS_STAFF_P: [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_staff_inp)],
            OPS_EQUIP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_equip_inp)],
            OPS_NOTES:   [MessageHandler(filters.TEXT & ~filters.COMMAND, ops_notes_inp)],
            OPS_CONFIRM: [CallbackQueryHandler(ops_confirm_cb, pattern="^ops_(confirm|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, ops_cancel_handler)],
        per_message=False,
    )
    return [submit_h]


def get_operations_static_handlers():
    return [
        CallbackQueryHandler(operations_menu_handler, pattern="^menu_operations$"),
        CallbackQueryHandler(ops_view_handler,        pattern="^ops_view$"),
        CallbackQueryHandler(ops_summary_handler,     pattern="^ops_summary$"),
    ]
