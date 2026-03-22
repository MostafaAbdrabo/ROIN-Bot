"""
ROIN WORLD FZE — Announcement System Handler
=============================================
Phase 7A: Announcements System
  - HR creates announcement (title + body)
  - Auto-translate to AR + RU + EN via Gemini
  - Priority: Critical/High/Medium/Normal
  - Target: All / Department / Role
  - Read confirmations tracked

Phase 7B: Contact HR Queue — handled in contact_hr_handler.py

Announcements tab:
  Ann_ID, Title, Body_AR, Body_RU, Body_EN, Priority, Target,
  Total_Recipients, Total_Read, Read_Rate, Status

Read_Tracking tab:
  Ann_ID, Emp_Code, Delivered_At, Read_At, Confirmed
"""

import os, json
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler, MessageHandler, filters)
from config import get_sheet

def bm(): return InlineKeyboardButton("↩️ Main Menu",   callback_data="back_to_menu")
def bhr(): return InlineKeyboardButton("↩️ HR Tools",   callback_data="menu_hr_tools")
def ban(): return InlineKeyboardButton("↩️ Announcements", callback_data="menu_announcements")

# Conversation states
ANN_TITLE    = 700
ANN_BODY     = 701
ANN_PRIORITY = 702
ANN_TARGET   = 703
ANN_CONFIRM  = 704
ANN_CUSTOM_DEPT = 705

PRIORITIES   = [("🔴 Critical", "Critical"), ("🟠 High", "High"),
                ("🟡 Medium", "Medium"),    ("🟢 Normal", "Normal")]
TARGETS      = [("👥 All Employees", "All"), ("🏢 By Department", "Dept"),
                ("🎭 By Role", "Role")]


def _gen_ann_id():
    ids = get_sheet("Announcements").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"ANN-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _translate_with_gemini(text, target_lang):
    """Translate text to target_lang using Gemini AI."""
    try:
        import google.generativeai as genai
        from config import GEMINI_KEY
        if not GEMINI_KEY:
            return f"[{target_lang} translation unavailable — no API key]"
        genai.configure(api_key=GEMINI_KEY)
        model  = genai.GenerativeModel("gemini-pro")
        prompt = (f"Translate the following workplace announcement to {target_lang}. "
                  f"Keep it professional and formal. Output only the translation:\n\n{text}")
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return f"[{target_lang} translation unavailable]"


def _get_recipients(target, target_detail=""):
    """Return list of (emp_code, telegram_id) for target audience."""
    try:
        ur_rows  = get_sheet("User_Registry").get_all_records()
        emp_rows = get_sheet("Employee_DB").get_all_records()
        emp_map  = {str(r.get("Emp_Code","")).strip(): r for r in emp_rows}
        result   = []
        for r in ur_rows:
            ec  = str(r.get("Emp_Code","")).strip()
            tid = str(r.get("Telegram_ID","")).strip()
            st  = str(r.get("Status","")).strip()
            if st != "Active" or not tid: continue
            if target == "All":
                result.append((ec, tid))
            elif target == "Dept":
                emp = emp_map.get(ec, {})
                if str(emp.get("Department","")).strip() == target_detail:
                    result.append((ec, tid))
            elif target == "Role":
                if str(r.get("Bot_Role","")).strip() == target_detail:
                    result.append((ec, tid))
        return result
    except Exception:
        return []


# ── Entry ──────────────────────────────────────────────────────────────────────

async def ann_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton("✏️ Create Announcement",     callback_data="ann_create")],
        [InlineKeyboardButton("📋 View All Announcements",  callback_data="ann_list")],
        [InlineKeyboardButton("📊 Read Confirmations",      callback_data="ann_confirmations")],
        [bhr(), bm()],
    ]
    await q.edit_message_text("📢 Announcements\n\nSelect option:", reply_markup=InlineKeyboardMarkup(kb))


async def ann_list_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading...")
    try:
        rows = get_sheet("Announcements").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[ban(), bm()]])); return
    if not rows:
        await q.edit_message_text("No announcements yet.",
            reply_markup=InlineKeyboardMarkup([[ban(), bm()]])); return
    lines = [f"📢 Announcements ({len(rows)} total)\n{'─'*28}"]
    for r in reversed(rows[-20:]):
        aid   = str(r.get("Ann_ID","?"))
        title = str(r.get("Title","?"))[:30]
        prio  = str(r.get("Priority","?"))
        read_rate = str(r.get("Read_Rate","?"))
        icon  = {"Critical":"🔴","High":"🟠","Medium":"🟡","Normal":"🟢"}.get(prio,"📢")
        lines.append(f"{icon} {aid} — {title} ({read_rate}%)")
    kb = [[ban(), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def ann_confirmations_handler(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading confirmations...")
    try:
        confs = get_sheet("Read_Tracking").get_all_records()
        anns  = get_sheet("Announcements").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[ban(), bm()]])); return
    lines = [f"📊 Read Confirmations\n{'─'*28}"]
    for ann in reversed(anns[-10:]):
        aid   = str(ann.get("Ann_ID",""))
        title = str(ann.get("Title",""))[:25]
        total = int(ann.get("Total_Recipients",0) or 0)
        read  = sum(1 for c in confs if str(c.get("Ann_ID","")) == aid and str(c.get("Read_At","")).strip())
        pct   = round(read/total*100) if total else 0
        icon  = "🔴" if pct < 50 else "🟡" if pct < 80 else "🟢"
        lines.append(f"{icon} {aid}: {title}\n   Read: {read}/{total} ({pct}%)")
    kb = [[ban(), bm()]]
    await q.edit_message_text("\n".join(lines[:25]), reply_markup=InlineKeyboardMarkup(kb))


# ── Create announcement flow ───────────────────────────────────────────────────

async def ann_create_start(update, context):
    q = update.callback_query; await q.answer()
    context.user_data.clear()
    await q.edit_message_text(
        "✏️ New Announcement\n\nStep 1/4: Type the title:",
        reply_markup=InlineKeyboardMarkup([[ban(), bm()]]))
    return ANN_TITLE


async def ann_title_inp(update, context):
    context.user_data["ann_title"] = update.message.text.strip()
    await update.message.reply_text(
        "Step 2/4: Type the announcement body (in any language):",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ANN_BODY


async def ann_body_inp(update, context):
    context.user_data["ann_body"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(label, callback_data=f"ann_pri_{code}")]
          for label, code in PRIORITIES]
    kb.append([bm()])
    await update.message.reply_text("Step 3/4: Select priority:",
                                     reply_markup=InlineKeyboardMarkup(kb))
    return ANN_PRIORITY


async def ann_priority_sel(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["ann_priority"] = q.data.replace("ann_pri_","")
    kb = [[InlineKeyboardButton(label, callback_data=f"ann_tgt_{code}")]
          for label, code in TARGETS]
    kb.append([bm()])
    await q.edit_message_text("Step 4/4: Select target audience:",
                               reply_markup=InlineKeyboardMarkup(kb))
    return ANN_TARGET


async def ann_target_sel(update, context):
    q = update.callback_query; await q.answer()
    target = q.data.replace("ann_tgt_","")
    context.user_data["ann_target"] = target

    if target == "Dept":
        try:
            depts = sorted(set(str(r.get("Department","")).strip()
                               for r in get_sheet("Employee_DB").get_all_records()
                               if str(r.get("Department","")).strip()))
        except Exception: depts = []
        kb = [[InlineKeyboardButton(d, callback_data=f"ann_dept_{d}")] for d in depts]
        kb.append([bm()])
        await q.edit_message_text("Select department:", reply_markup=InlineKeyboardMarkup(kb))
        return ANN_CUSTOM_DEPT

    elif target == "Role":
        from config import VALID_ROLES
        kb = [[InlineKeyboardButton(r, callback_data=f"ann_role_{r}")] for r in VALID_ROLES]
        kb.append([bm()])
        await q.edit_message_text("Select role:", reply_markup=InlineKeyboardMarkup(kb))
        return ANN_CUSTOM_DEPT

    return await _ann_show_confirm(q, context)


async def ann_custom_dept_sel(update, context):
    q = update.callback_query; await q.answer()
    if q.data.startswith("ann_dept_"):
        context.user_data["ann_target_detail"] = q.data.replace("ann_dept_","")
    elif q.data.startswith("ann_role_"):
        context.user_data["ann_target_detail"] = q.data.replace("ann_role_","")
    return await _ann_show_confirm(q, context)


async def _ann_show_confirm(q, context):
    title    = context.user_data.get("ann_title","?")
    body     = context.user_data.get("ann_body","?")[:100]
    priority = context.user_data.get("ann_priority","Normal")
    target   = context.user_data.get("ann_target","All")
    detail   = context.user_data.get("ann_target_detail","")
    target_str = f"{target}" + (f" ({detail})" if detail else "")
    msg = (f"📢 Announcement Preview\n{'─'*28}\n"
           f"Title:    {title}\n"
           f"Body:     {body}...\n"
           f"Priority: {priority}\n"
           f"Target:   {target_str}\n\n"
           f"⚙️ Gemini will auto-translate to AR + RU + EN.\n\n"
           f"Confirm and send?")
    kb = [[InlineKeyboardButton("✅ Send", callback_data="ann_send"),
           InlineKeyboardButton("❌ Cancel", callback_data="ann_cancel")],
          [bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return ANN_CONFIRM


async def ann_send_confirm(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "ann_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return ConversationHandler.END

    await q.edit_message_text("⏳ Translating and sending...")
    title    = context.user_data.get("ann_title","")
    body     = context.user_data.get("ann_body","")
    priority = context.user_data.get("ann_priority","Normal")
    target   = context.user_data.get("ann_target","All")
    detail   = context.user_data.get("ann_target_detail","")

    # Translate
    body_en = _translate_with_gemini(body, "English")
    body_ar = _translate_with_gemini(body, "Arabic (transliterated, Latin characters)")
    body_ru = _translate_with_gemini(body, "Russian")

    try:
        ann_id = _gen_ann_id()
        recipients = _get_recipients(target, detail)
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Save to Announcements
        ws = get_sheet("Announcements")
        ws.append_row([ann_id, title, body_ar, body_ru, body_en, priority,
                       f"{target}" + (f":{detail}" if detail else ""),
                       len(recipients), 0, 0, "Active"],
                      value_input_option="USER_ENTERED")

        # Send to recipients
        icon_map = {"Critical":"🔴","High":"🟠","Medium":"🟡","Normal":"🟢"}
        icon = icon_map.get(priority,"📢")
        sent = 0
        conf_ws = get_sheet("Read_Tracking")
        conf_rows = []
        for ec, tid in recipients:
            try:
                msg_text = (f"{icon} {priority.upper()} ANNOUNCEMENT\n{'─'*28}\n"
                            f"📌 {title}\n\n{body_en}\n\n"
                            f"{'─'*28}\n🆔 {ann_id}")
                await context._application.bot.send_message(chat_id=int(tid), text=msg_text)
                # Cols: Ann_ID, Emp_Code, Name(VLOOKUP=""), Delivered_At, Read_At, Confirmed
                conf_rows.append([ann_id, ec, "", now, "", ""])
                sent += 1
            except Exception: pass
        if conf_rows:
            conf_ws.append_rows(conf_rows, value_input_option="USER_ENTERED")

        await q.edit_message_text(
            f"✅ Announcement sent!\nID: {ann_id}\nSent to: {sent}/{len(recipients)} recipients.",
            reply_markup=InlineKeyboardMarkup([[ban(), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


async def ann_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


# ── Employee: view announcements ───────────────────────────────────────────────

async def emp_announcements_handler(update, context):
    """Employee sees latest 5 announcements."""
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    ec  = None
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: ec = r[0].strip(); break
    try:
        rows = list(reversed(get_sheet("Announcements").get_all_records()[-5:]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_announcements"), bm()]])); return
    if not rows:
        await q.edit_message_text("No announcements yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_announcements"), bm()]])); return
    icon_map = {"Critical":"🔴","High":"🟠","Medium":"🟡","Normal":"🟢"}
    lines = ["📢 Latest Announcements\n"]
    for r in rows:
        icon = icon_map.get(str(r.get("Priority","")), "📢")
        lines.append(f"{icon} {r.get('Ann_ID','')} — {r.get('Title','')}")
    lines.append("\nTap below to confirm reading:")
    kb_rows = []
    for r in rows:
        aid = str(r.get("Ann_ID",""))
        kb_rows.append([InlineKeyboardButton(f"✅ Confirm read: {aid}", callback_data=f"ann_read_{aid}")])
    kb_rows.append([bm()])
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb_rows))


async def ann_read_confirm(update, context):
    q = update.callback_query; await q.answer()
    aid = q.data.replace("ann_read_","")
    tid = str(q.from_user.id)
    ec  = None
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: ec = r[0].strip(); break
    try:
        ws   = get_sheet("Read_Tracking")
        rows = ws.get_all_records()
        for i, r in enumerate(rows):
            if str(r.get("Ann_ID","")) == aid and str(r.get("Emp_Code","")) == ec:
                if not str(r.get("Read_At","")):
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    # Col 5 = Read_At, Col 6 = Confirmed (col C is VLOOKUP Name)
                    ws.update_cell(i+2, 5, now)
                    ws.update_cell(i+2, 6, "Yes")
        await q.answer("✅ Marked as read!", show_alert=True)
    except Exception as e:
        await q.answer(f"❌ {e}", show_alert=True)


def get_ann_create_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(ann_create_start, pattern="^ann_create$")],
        states={
            ANN_TITLE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_title_inp),
                              CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
            ANN_BODY:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_body_inp)],
            ANN_PRIORITY:    [CallbackQueryHandler(ann_priority_sel,   pattern="^ann_pri_")],
            ANN_TARGET:      [CallbackQueryHandler(ann_target_sel,     pattern="^ann_tgt_")],
            ANN_CUSTOM_DEPT: [CallbackQueryHandler(ann_custom_dept_sel,pattern="^ann_(dept|role)_")],
            ANN_CONFIRM:     [CallbackQueryHandler(ann_send_confirm,   pattern="^ann_(send|cancel)$"),
                              CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^back_to_menu$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, ann_cancel_handler)],
        per_message=False,
    )


def get_ann_static_handlers():
    return [
        CallbackQueryHandler(ann_menu_handler,          pattern="^menu_announcements$"),
        CallbackQueryHandler(ann_list_handler,          pattern="^ann_list$"),
        CallbackQueryHandler(ann_confirmations_handler, pattern="^ann_confirmations$"),
        CallbackQueryHandler(emp_announcements_handler, pattern="^menu_emp_announcements$"),
        CallbackQueryHandler(ann_read_confirm,          pattern="^ann_read_"),
    ]
