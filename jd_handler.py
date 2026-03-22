"""
ROIN WORLD FZE — JD Conversation Handlers
==========================================
Four flows, three ConversationHandlers:

  1. get_jd_create_handler()       — Manager creates JD (with AI)
  2. get_jd_hr_handler()           — HR Staff/Manager review & edit
  3. get_jd_manager_dir_handler()  — Manager reviews HR edits + Director approves
"""

import io
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet, TAB_USER_REGISTRY, TAB_EMPLOYEE_DB
from jd_generator import generate_jd_pdf
from jd_store import (create_jd, get_jd, update_jd,
                       get_jds_by_status, get_jds_by_creator,
                       merge_jd, upload_to_drive,
                       S_PENDING_HR, S_PENDING_MGR,
                       S_PENDING_DIR, S_APPROVED, S_REJECTED)
from jd_ai import ai_available, improve_summary, improve_tasks, improve_qualifications, improve_section

# ── State constants ────────────────────────────────────────────────────────────
# Creation (manager)
JD_EMP = 400;  JD_TITLE = 401
JD_SUMMARY = 402;  JD_SUM_AI = 403
JD_TASKS = 404;    JD_TSK_AI = 405
JD_QUALS = 406;    JD_QLS_AI = 407
JD_WRKCON = 408;   JD_PREVIEW = 409

# HR review
JD_HR_LIST = 420;  JD_HR_VIEW = 421
JD_HR_EDIT_PICK = 422;  JD_HR_EDIT_TEXT = 423;  JD_HR_EDIT_AI = 424
JD_HR_REJECT_TXT = 425

# Manager review of HR edits
JD_MGR_LIST = 430;  JD_MGR_VIEW = 431;  JD_MGR_RETURN_TXT = 432

# Director review
JD_DIR_LIST = 440;  JD_DIR_VIEW = 441
JD_DIR_CHANGE_TXT = 442;  JD_DIR_REJECT_TXT = 443


# ── Shared helpers ─────────────────────────────────────────────────────────────

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _ckb(): return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="jd_cancel"), bm()]])


async def _send_tasks_comparison(msg, original: list, improved: list,
                                  use_cb: str, keep_cb: str):
    """Send full side-by-side task comparison across as many messages as needed,
    then a final message with the choice buttons."""
    orig_lines  = "\n".join(f"{i}. {t}" for i, t in enumerate(original, 1))
    impr_lines  = "\n".join(f"{i}. {t}" for i, t in enumerate(improved, 1))

    header_orig = f"📋 YOUR ORIGINAL ({len(original)} tasks):\n{'─'*30}\n"
    header_impr = f"✨ AI VERSION ({len(improved)} tasks):\n{'─'*30}\n"

    # Send original block (split if > 4000 chars)
    orig_full = header_orig + orig_lines
    for chunk in _split_message(orig_full):
        await msg.reply_text(chunk)

    # Send improved block
    impr_full = header_impr + impr_lines
    for chunk in _split_message(impr_full):
        await msg.reply_text(chunk)

    # Choice buttons
    await msg.reply_text(
        "Which version do you want to use?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Use AI version", callback_data=use_cb),
             InlineKeyboardButton("✅ Keep mine",      callback_data=keep_cb)]]))


def _split_message(text: str, limit: int = 4000) -> list:
    """Split a long string into chunks that fit within Telegram's message limit."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text); break
        # Split at last newline before limit
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks

def _get_mgr_info(tid: str):
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid:
            return r[0].strip(), (r[3].strip() if len(r) > 3 else "Employee")
    return None, "Employee"

def _get_emp(ec: str) -> dict | None:
    for r in get_sheet(TAB_EMPLOYEE_DB).get_all_records():
        if str(r.get("Emp_Code", "")).strip() == str(ec):
            return r
    return None

def _get_emp_tid(ec: str) -> str | None:
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[0].strip() == str(ec):
            t = r[1].strip(); return t if t else None
    return None

def _emp_list_for_role(my_code: str, my_role: str) -> list:
    result = []
    for r in get_sheet(TAB_EMPLOYEE_DB).get_all_records():
        ec = str(r.get("Emp_Code", "")).strip()
        nm = r.get("Full_Name", ec)
        if not ec: continue
        if my_role in ("HR_Staff", "HR_Manager", "Director"):
            result.append((ec, nm))
        elif my_role == "Direct_Manager" and str(r.get("Manager_Code", "")).strip() == str(my_code):
            result.append((ec, nm))
        elif my_role == "Supervisor" and str(r.get("Supervisor_Code", "")).strip() == str(my_code):
            result.append((ec, nm))
    return result

async def _notify_by_role(bot, role: str, text: str, kb=None):
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[3].strip() == role:
            tid = r[1].strip()
            if tid:
                try: await bot.send_message(int(tid), text, reply_markup=kb)
                except: pass

async def _notify_ec(bot, ec: str, text: str, kb=None):
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0: continue
        if r[0].strip() == str(ec):
            tid = r[1].strip()
            if tid:
                try: await bot.send_message(int(tid), text, reply_markup=kb)
                except: pass
            break

def _jd_summary_text(jd: dict, show_hr_edits=False) -> str:
    hr = jd.get("hr_edits", {})
    lines = [
        f"📄 JD: {jd.get('jd_id', '')}",
        f"Employee:   {jd.get('emp_name', '')} ({jd.get('emp_code', '')})",
        f"Status:     {jd.get('status', '')}",
        f"Created:    {jd.get('created_at', '')}",
    ]
    return "\n".join(lines)

async def _send_jd_view(target, jd: dict, merged: bool, kb, note: str = ""):
    """Send JD for review across as many messages as needed, buttons on the last one.
    `target` is a CallbackQuery (edit first message) or a chat_id int (send fresh).
    Works for HR review, Director review, Manager review of HR edits.
    """
    if merged:
        d = merge_jd(jd)
        title = d["job_title"]; summary = d["summary"]
        tasks = d["tasks"]; quals = d["qualifications"]; wc = d["working_conditions"]
        label = "FINAL (HR edits applied)"
    else:
        title = jd["job_title"]; summary = jd["summary"]
        tasks = jd["tasks"]; quals = jd["qualifications"]; wc = jd["working_conditions"]
        label = "MANAGER'S ORIGINAL"

    header = (
        f"━━━ {label} ━━━\n"
        f"Employee: {jd.get('emp_name','')} ({jd.get('emp_code','')})\n"
        f"Title:    {title}\n"
        f"─────────────────────────\n"
        f"Summary:\n{summary}\n"
        f"─────────────────────────\n"
        f"Qualifications:\n{quals}\n"
        f"─────────────────────────\n"
        f"Working Conditions:\n{wc}"
    )
    tasks_block = f"📋 Tasks ({len(tasks)}):\n" + "\n".join(
        f"{i}. {t}" for i, t in enumerate(tasks, 1))

    # Send header (may itself be long)
    header_chunks = _split_message(header)
    tasks_chunks  = _split_message(tasks_block + (f"\n\n{note}" if note else ""))
    all_chunks    = header_chunks + tasks_chunks

    # First chunk: edit the existing message if we have a CallbackQuery
    first = True
    for i, chunk in enumerate(all_chunks):
        is_last = (i == len(all_chunks) - 1)
        reply_markup = kb if is_last else None
        if first and hasattr(target, "edit_message_text"):
            await target.edit_message_text(chunk, reply_markup=reply_markup)
            first = False
        else:
            await target.message.reply_text(chunk, reply_markup=reply_markup) \
                if hasattr(target, "message") else \
                await target.reply_text(chunk, reply_markup=reply_markup)


# ══════════════════════════════════════════════════════════════════════════════
# FLOW 1 — MANAGER CREATES JD
# ══════════════════════════════════════════════════════════════════════════════

async def jd_start(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading team list...")
    tid = str(q.from_user.id)
    my_code, my_role = _get_mgr_info(tid)
    if my_role not in ("Direct_Manager", "Supervisor", "HR_Staff", "HR_Manager", "Director"):
        await q.edit_message_text("❌ Access denied.",
            reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    team = _emp_list_for_role(my_code, my_role)
    if not team:
        await q.edit_message_text("ℹ️ No employees found under your management.",
            reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    context.user_data.update({"jd_my_code": my_code, "jd_my_role": my_role, "jd_tasks": []})
    kb = [[InlineKeyboardButton(f"👤 {nm} ({ec})", callback_data=f"jd_emp_{ec}")]
          for ec, nm in team[:25]]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="jd_cancel"), bm()])
    await q.edit_message_text("📄 Generate Job Description\n\nSelect employee:",
                               reply_markup=InlineKeyboardMarkup(kb))
    return JD_EMP


async def jd_emp_select(update, context):
    q = update.callback_query; await q.answer()
    ec = q.data.replace("jd_emp_", "")
    emp = _get_emp(ec)
    if not emp:
        await q.edit_message_text("❌ Employee not found.",
            reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    context.user_data.update({"jd_ec": ec, "jd_emp": emp, "jd_tasks": []})
    title = str(emp.get("Job_Title", "")).strip() or "—"
    await q.edit_message_text(
        f"📄 JD for: {emp.get('Full_Name', ec)}\n"
        f"Department: {emp.get('Department', '—')}\n\n"
        f"Current Job Title:\n  👉 {title}\n\n"
        f"Type a new title to change it, or type OK to confirm:", reply_markup=_ckb())
    return JD_TITLE


# ── Title ─────────────────────────────────────────────────────────────────────

async def jd_title(update, context):
    text = update.message.text.strip()
    emp = context.user_data.get("jd_emp", {})
    context.user_data["jd_title"] = text if text.upper() != "OK" else str(emp.get("Job_Title", "")).strip()
    await update.message.reply_text(
        f"Title: {context.user_data['jd_title']}\n\n"
        f"Now type the Job Summary paragraph:", reply_markup=_ckb())
    return JD_SUMMARY


# ── Summary ───────────────────────────────────────────────────────────────────

async def jd_summary(update, context):
    text = update.message.text.strip()
    context.user_data["jd_summary_orig"] = text
    if ai_available():
        await update.message.reply_text("⏳ Running AI improvement...")
        improved, err = await improve_summary(text, context.user_data.get("jd_title", ""))
        if err:
            await update.message.reply_text(f"⚠️ AI unavailable: {err}\nContinuing with your original.")
            context.user_data["jd_summary"] = text
            return await _ask_tasks(update.message)
        context.user_data["jd_summary_ai"] = improved
        await update.message.reply_text(
            f"✅ Your Summary:\n{text[:400]}\n\n"
            f"{'─'*30}\n"
            f"✨ AI Version:\n{improved[:400]}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Use AI version", callback_data="jd_sum_use_ai"),
                 InlineKeyboardButton("✅ Keep mine", callback_data="jd_sum_keep")]]))
        return JD_SUM_AI
    context.user_data["jd_summary"] = text
    return await _ask_tasks(update.message)


async def jd_sum_use_ai(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_summary"] = context.user_data.get("jd_summary_ai", context.user_data.get("jd_summary_orig", ""))
    await q.edit_message_text("✨ AI summary saved.")
    return await _ask_tasks(q.message)


async def jd_sum_keep(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_summary"] = context.user_data.get("jd_summary_orig", "")
    await q.edit_message_text("✅ Your original summary saved.")
    return await _ask_tasks(q.message)


async def _ask_tasks(msg):
    await msg.reply_text(
        "Type all Key Responsibilities at once — one per line:\n\n"
        "Example:\n"
        "Manage daily meal production schedule\n"
        "Supervise kitchen staff across all shifts\n"
        "Ensure HACCP compliance at all times\n"
        "...",
        reply_markup=_ckb())
    return JD_TASKS


def _parse_tasks(text: str) -> list:
    """Split a multi-line task block into individual task strings."""
    import re
    lines = text.split("\n")
    tasks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Strip leading number/bullet: "1.", "1)", "-", "•", "*"
        line = re.sub(r"^[\d]+[.\)]\s*", "", line)
        line = re.sub(r"^[-•*]\s*", "", line).strip()
        if line:
            tasks.append(line)
    return tasks


# ── Tasks ─────────────────────────────────────────────────────────────────────

async def jd_tasks(update, context):
    tasks = _parse_tasks(update.message.text)
    if not tasks:
        await update.message.reply_text("Couldn't parse any tasks. Type each task on its own line.")
        return JD_TASKS
    context.user_data["jd_tasks"] = tasks
    context.user_data["jd_tasks_orig"] = list(tasks)
    if ai_available():
        await update.message.reply_text(f"Parsed {len(tasks)} tasks. ⏳ Running AI improvement...")
        improved, err = await improve_tasks(tasks, context.user_data.get("jd_title", ""))
        if err:
            await update.message.reply_text(f"⚠️ AI unavailable: {err}\nContinuing with your original.")
            return await _ask_quals(update.message)
        context.user_data["jd_tasks_ai"] = improved
        await _send_tasks_comparison(
            update.message, tasks, improved,
            use_cb="jd_tsk_use_ai", keep_cb="jd_tsk_keep")
        return JD_TSK_AI
    await update.message.reply_text(f"{len(tasks)} tasks saved.")
    return await _ask_quals(update.message)


async def jd_tsk_use_ai(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_tasks"] = context.user_data.get("jd_tasks_ai", context.user_data.get("jd_tasks_orig", []))
    await q.edit_message_text("✨ AI tasks saved.")
    return await _ask_quals(q.message)


async def jd_tsk_keep(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_tasks"] = context.user_data.get("jd_tasks_orig", [])
    await q.edit_message_text("✅ Your original tasks saved.")
    return await _ask_quals(q.message)


async def _ask_quals(msg):
    await msg.reply_text(
        "Now type the Required Qualifications.\n"
        "Include education, experience, skills, certifications:", reply_markup=_ckb())
    return JD_QUALS


# ── Qualifications ────────────────────────────────────────────────────────────

async def jd_quals(update, context):
    text = update.message.text.strip()
    context.user_data["jd_quals_orig"] = text
    if ai_available():
        await update.message.reply_text("⏳ Running AI improvement...")
        improved, err = await improve_qualifications(text, context.user_data.get("jd_title", ""))
        if err:
            await update.message.reply_text(f"⚠️ AI unavailable: {err}\nContinuing with your original.")
            context.user_data["jd_quals"] = text
            return await _ask_wrkcon(update.message)
        context.user_data["jd_quals_ai"] = improved
        await update.message.reply_text(
            f"✅ Your Qualifications:\n{text[:350]}\n\n"
            f"{'─'*30}\n"
            f"✨ AI Version:\n{improved[:350]}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Use AI version", callback_data="jd_qls_use_ai"),
                 InlineKeyboardButton("✅ Keep mine", callback_data="jd_qls_keep")]]))
        return JD_QLS_AI
    context.user_data["jd_quals"] = text
    return await _ask_wrkcon(update.message)


async def jd_qls_use_ai(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_quals"] = context.user_data.get("jd_quals_ai", context.user_data.get("jd_quals_orig", ""))
    await q.edit_message_text("✨ AI qualifications saved.")
    return await _ask_wrkcon(q.message)


async def jd_qls_keep(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_quals"] = context.user_data.get("jd_quals_orig", "")
    await q.edit_message_text("✅ Your original qualifications saved.")
    return await _ask_wrkcon(q.message)


async def _ask_wrkcon(msg):
    default = "8:00 AM - 5:00 PM, 6 days per week. PPE required on site."
    await msg.reply_text(
        f"Working Conditions (default):\n{default}\n\n"
        f"Tap Use Default or type custom conditions:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Use Default", callback_data="jd_wc_default")],
            [InlineKeyboardButton("❌ Cancel", callback_data="jd_cancel"), bm()]]))
    return JD_WRKCON


async def jd_wrkcon_text(update, context):
    context.user_data["jd_wrkcon"] = update.message.text.strip()
    return await _show_preview(update.message, context)


async def jd_wrkcon_default(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["jd_wrkcon"] = "8:00 AM - 5:00 PM, 6 days per week. PPE required on site."
    return await _show_preview(q.message, context)


# ── Preview + Submit ───────────────────────────────────────────────────────────

async def _show_preview(msg, context):
    emp = context.user_data.get("jd_emp", {})
    ec = context.user_data.get("jd_ec", "?")
    tasks = context.user_data.get("jd_tasks", [])
    tasks_block = "\n".join(f"  {i}. {t}" for i, t in enumerate(tasks, 1))
    header = (
        f"📄 JD PREVIEW\n{'━'*32}\n"
        f"Employee: {emp.get('Full_Name', ec)} ({ec})\n"
        f"Title: {context.user_data.get('jd_title', '')}\n"
        f"Dept: {emp.get('Department', '—')}\n"
        f"{'─'*32}\n"
        f"Summary:\n{context.user_data.get('jd_summary', '')}\n"
        f"{'─'*32}\n"
        f"Qualifications:\n{context.user_data.get('jd_quals', '')}\n"
        f"{'─'*32}\n"
        f"Working Conditions:\n{context.user_data.get('jd_wrkcon', '')}"
    )
    tasks_section = f"📋 Tasks ({len(tasks)}):\n{tasks_block}\n{'─'*32}\nTap Submit to send for HR review."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit for HR Review", callback_data="jd_submit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="jd_cancel"), bm()]])
    all_chunks = _split_message(header) + _split_message(tasks_section)
    for i, chunk in enumerate(all_chunks):
        is_last = (i == len(all_chunks) - 1)
        await msg.reply_text(chunk, reply_markup=kb if is_last else None)
    return JD_PREVIEW


async def jd_submit(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Submitting...")
    try:
        emp = context.user_data.get("jd_emp", {})
        ec = context.user_data.get("jd_ec", "")
        my_code = context.user_data.get("jd_my_code", "")
        mgr_rec = _get_emp(my_code)
        mgr_name = mgr_rec.get("Full_Name", "HR Department") if mgr_rec else "HR Department"
        jd_id = create_jd({
            "emp_code": ec,
            "emp_name": emp.get("Full_Name", ec),
            "creator_code": my_code,
            "job_title": context.user_data.get("jd_title", ""),
            "summary": context.user_data.get("jd_summary", ""),
            "tasks": context.user_data.get("jd_tasks", []),
            "qualifications": context.user_data.get("jd_quals", ""),
            "working_conditions": context.user_data.get("jd_wrkcon", ""),
        })
        # Extra fields stored in sheet via update for PDF generation later
        update_jd(jd_id,
                  department=emp.get("Department", ""),
                  manager_name=mgr_name,
                  location=emp.get("Work_Location", "El Dabaa Nuclear Power Plant Site, Matrouh"),
                  employment_type=emp.get("Contract_Type", "Full-Time"),
                  grade=emp.get("Grade", ""),
                  created_by=mgr_name)
        _clear_create(context)
        await q.edit_message_text(
            f"JD submitted for HR review!\n\nJD ID: {jd_id}\n"
            f"HR has been notified and will review shortly.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 My JDs", callback_data="menu_jd_my_jds"), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ Error: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My JDs", callback_data="menu_jd_my_jds"), bm()]]))
    return ConversationHandler.END


def _clear_create(ctx):
    for k in ("jd_ec","jd_emp","jd_tasks","jd_tasks_orig","jd_tasks_ai",
              "jd_my_code","jd_my_role","jd_title","jd_summary","jd_summary_orig",
              "jd_summary_ai","jd_quals","jd_quals_orig","jd_quals_ai","jd_wrkcon"):
        ctx.user_data.pop(k, None)


async def jd_cancel(update, context):
    q = update.callback_query; await q.answer()
    _clear_create(context)
    _clear_hr(context)
    _clear_dir(context)
    await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
# FLOW 2 — HR REVIEW & EDIT
# ══════════════════════════════════════════════════════════════════════════════

async def jd_hr_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading pending JDs...")
    pending = get_jds_by_status(S_PENDING_HR)
    if not pending:
        await q.edit_message_text("✅ No JDs pending HR review.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()]])); return ConversationHandler.END
    kb = [[InlineKeyboardButton(
                f"📄 {j['emp_name']} ({j['emp_code']}) — {j['job_title'][:25]}",
                callback_data=f"jdhr_view_{j['jd_id']}")]
           for j in pending[:20]]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()])
    await q.edit_message_text(f"📋 JDs Pending HR Review ({len(pending)}):",
                               reply_markup=InlineKeyboardMarkup(kb))
    return JD_HR_VIEW


async def jd_hr_view(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdhr_view_", "")
    jd = get_jd(jd_id)
    if not jd:
        await q.edit_message_text("❌ JD not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd_reviews"), bm()]])); return ConversationHandler.END
    context.user_data["jd_hr_jd_id"] = jd_id
    context.user_data["jd_hr_edits"] = {}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve as-is", callback_data=f"jdhr_approve_{jd_id}")],
        [InlineKeyboardButton("✏️ Edit sections", callback_data=f"jdhr_edit_{jd_id}")],
        [InlineKeyboardButton("❌ Reject",         callback_data=f"jdhr_reject_{jd_id}")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_jd_reviews"), bm()],
    ])
    await _send_jd_view(q, jd, merged=False, kb=kb)
    return JD_HR_VIEW


async def jd_hr_approve(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdhr_approve_", "")
    jd = get_jd(jd_id)
    update_jd(jd_id, status=S_PENDING_DIR)
    await q.edit_message_text(
        f"JD approved and sent to Director.\nJD ID: {jd_id}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 More reviews", callback_data="menu_jd_reviews"), bm()]]))
    return ConversationHandler.END


async def jd_hr_edit_start(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdhr_edit_", "")
    context.user_data["jd_hr_jd_id"] = jd_id
    context.user_data["jd_hr_edits"] = {}
    context.user_data["jd_hr_tasks_buf"] = []
    return await _show_hr_section_menu(q, jd_id)


async def _show_hr_section_menu(q_or_msg, jd_id: str, is_msg=False):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Job Title",          callback_data="jdhre_sec_title")],
        [InlineKeyboardButton("✏️ Summary",            callback_data="jdhre_sec_summary")],
        [InlineKeyboardButton("✏️ Tasks",              callback_data="jdhre_sec_tasks")],
        [InlineKeyboardButton("✏️ Qualifications",     callback_data="jdhre_sec_quals")],
        [InlineKeyboardButton("✏️ Working Conditions", callback_data="jdhre_sec_wrkcon")],
        [InlineKeyboardButton("✅ Done — Submit edits", callback_data="jdhre_done")],
        [InlineKeyboardButton("↩️ Back", callback_data=f"jdhr_view_{jd_id}"), bm()],
    ])
    text = f"✏️ Editing JD: {jd_id}\n\nTap a section to edit it, then Done when finished:"
    if is_msg:
        await q_or_msg.reply_text(text, reply_markup=kb)
    else:
        await q_or_msg.edit_message_text(text, reply_markup=kb)
    return JD_HR_EDIT_PICK


async def jd_hr_edit_menu(update, context):
    """Re-show section menu after each edit."""
    q = update.callback_query; await q.answer()
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    return await _show_hr_section_menu(q, jd_id)


async def jd_hr_pick_section(update, context):
    q = update.callback_query; await q.answer()
    section = q.data.replace("jdhre_sec_", "")
    context.user_data["jd_hr_editing_section"] = section
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    jd = get_jd(jd_id) or {}
    prompts = {
        "title":   f"Current title: {jd.get('job_title', '')}\n\nType new job title:",
        "summary": f"Current summary:\n{jd.get('summary', '')[:300]}\n\nType new summary:",
        "tasks":   f"Current tasks: {len(jd.get('tasks', []))}\n\nType all new tasks at once — one per line:",
        "quals":   f"Current qualifications:\n{jd.get('qualifications', '')[:300]}\n\nType new qualifications:",
        "wrkcon":  f"Current working conditions:\n{jd.get('working_conditions', '')[:200]}\n\nType new working conditions:",
    }
    if section == "tasks":
        context.user_data["jd_hr_tasks_buf"] = []
    await q.edit_message_text(prompts.get(section, "Type new content:"),
                               reply_markup=_ckb())
    return JD_HR_EDIT_TEXT


async def jd_hr_edit_text(update, context):
    text = update.message.text.strip()
    section = context.user_data.get("jd_hr_editing_section", "")
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    jd = get_jd(jd_id) or {}
    title = jd.get("job_title", "")

    if section == "tasks":
        tasks = _parse_tasks(text)
        if not tasks:
            await update.message.reply_text("Couldn't parse any tasks. Type each task on its own line.")
            return JD_HR_EDIT_TEXT
        context.user_data["jd_hr_pending_content"] = tasks
        if ai_available():
            await update.message.reply_text(f"Parsed {len(tasks)} tasks. ⏳ AI improving...")
            improved, err = await improve_tasks(tasks, title)
            if err:
                await update.message.reply_text(f"⚠️ AI unavailable: {err}")
                context.user_data.setdefault("jd_hr_edits", {})[section] = tasks
                await update.message.reply_text(f"Tasks saved ({len(tasks)}).")
                return await _show_hr_section_menu(update.message, jd_id, is_msg=True)
            context.user_data["jd_hr_ai_content"] = improved
            await _send_tasks_comparison(
                update.message, tasks, improved,
                use_cb="jdhr_ai_use", keep_cb="jdhr_ai_keep")
            return JD_HR_EDIT_AI
        context.user_data.setdefault("jd_hr_edits", {})[section] = tasks
        await update.message.reply_text(f"Tasks saved ({len(tasks)}).")
        return await _show_hr_section_menu(update.message, jd_id, is_msg=True)

    # Single-text sections
    context.user_data["jd_hr_pending_content"] = text
    if ai_available() and section in ("summary", "qualifications"):
        await update.message.reply_text("⏳ AI improving...")
        improved, err = await improve_section(section, text, title)
        if err:
            await update.message.reply_text(f"⚠️ AI unavailable: {err}")
            context.user_data.setdefault("jd_hr_edits", {})[section] = text
            await update.message.reply_text("Saved (without AI improvement).")
            return await _show_hr_section_menu(update.message, jd_id, is_msg=True)
        context.user_data["jd_hr_ai_content"] = improved
        await update.message.reply_text(
            f"✅ Your input:\n{text[:300]}\n\n{'─'*28}\n✨ AI version:\n{improved[:300]}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✨ Use AI", callback_data="jdhr_ai_use"),
                 InlineKeyboardButton("✅ Keep mine", callback_data="jdhr_ai_keep")]]))
        return JD_HR_EDIT_AI

    context.user_data.setdefault("jd_hr_edits", {})[section] = text
    await update.message.reply_text("Saved.")
    return await _show_hr_section_menu(update.message, jd_id, is_msg=True)


async def jdhr_ai_use(update, context):
    q = update.callback_query; await q.answer()
    section = context.user_data.get("jd_hr_editing_section", "")
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    content = context.user_data.get("jd_hr_ai_content")
    context.user_data.setdefault("jd_hr_edits", {})[section] = content
    await q.edit_message_text("✨ AI version saved.")
    return await _show_hr_section_menu(q, jd_id)


async def jdhr_ai_keep(update, context):
    q = update.callback_query; await q.answer()
    section = context.user_data.get("jd_hr_editing_section", "")
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    content = context.user_data.get("jd_hr_pending_content")
    context.user_data.setdefault("jd_hr_edits", {})[section] = content
    await q.edit_message_text("✅ Your version saved.")
    return await _show_hr_section_menu(q, jd_id)


async def jd_hr_edit_done(update, context):
    """HR finished editing — store edits and decide next status."""
    q = update.callback_query; await q.answer()
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    edits = context.user_data.get("jd_hr_edits", {})
    tid = str(q.from_user.id)
    my_code, _ = _get_mgr_info(tid)

    if edits:
        # HR made changes → send back to manager for review
        update_jd(jd_id, status=S_PENDING_MGR, hr_edits=edits, hr_editor=my_code or "HR")
        msg = f"Edits saved and sent back to manager for review.\nJD ID: {jd_id}"
    else:
        # No edits — approve directly
        update_jd(jd_id, status=S_PENDING_DIR)
        msg = f"No edits made. JD approved and sent to Director.\nJD ID: {jd_id}"

    _clear_hr(context)
    await q.edit_message_text(msg,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 More reviews", callback_data="menu_jd_reviews"), bm()]]))
    return ConversationHandler.END


async def jd_hr_reject_start(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdhr_reject_", "")
    context.user_data["jd_hr_jd_id"] = jd_id
    await q.edit_message_text("Type the rejection reason:", reply_markup=_ckb())
    return JD_HR_REJECT_TXT


async def jd_hr_reject_text(update, context):
    reason = update.message.text.strip()
    jd_id = context.user_data.get("jd_hr_jd_id", "")
    jd = get_jd(jd_id)
    update_jd(jd_id, status=S_REJECTED, rejection_reason=reason)
    _clear_hr(context)
    await update.message.reply_text(f"JD {jd_id} rejected.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 More reviews", callback_data="menu_jd_reviews"), bm()]]))
    return ConversationHandler.END


def _clear_hr(ctx):
    for k in ("jd_hr_jd_id","jd_hr_edits","jd_hr_editing_section",
              "jd_hr_pending_content","jd_hr_ai_content","jd_hr_tasks_buf"):
        ctx.user_data.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════════
# FLOW 3A — MANAGER REVIEWS HR EDITS
# ══════════════════════════════════════════════════════════════════════════════

async def jd_mgr_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading...")
    my_code, _ = _get_mgr_info(str(q.from_user.id))
    jds = get_jds_by_creator(my_code, S_PENDING_MGR)
    if not jds:
        # Also show all JDs this manager submitted (any status)
        all_jds = get_jds_by_creator(my_code)
        if all_jds:
            kb = [[InlineKeyboardButton(
                f"[{j['status']}] {j['emp_name']} — {j['job_title'][:20]}",
                callback_data=f"jdmgr_view_{j['jd_id']}")] for j in all_jds[:15]]
            kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()])
            await q.edit_message_text("📋 My JDs:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("No JDs found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()]]))
        return ConversationHandler.END
    kb = [[InlineKeyboardButton(
                f"✏️ {j['emp_name']} ({j['emp_code']}) — HR has edits",
                callback_data=f"jdmgr_view_{j['jd_id']}")]
           for j in jds[:15]]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()])
    await q.edit_message_text(f"📋 JDs with HR edits — your review needed ({len(jds)}):",
                               reply_markup=InlineKeyboardMarkup(kb))
    return JD_MGR_VIEW


async def jd_mgr_view(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdmgr_view_", "")
    jd = get_jd(jd_id)
    if not jd or not jd.get("hr_edits"):
        # Just view status
        await q.edit_message_text(
            f"JD: {jd_id}\nStatus: {jd.get('status','') if jd else 'Not found'}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd_my_jds"), bm()]])); return ConversationHandler.END
    context.user_data["jd_mgr_jd_id"] = jd_id
    # Show comparison
    hr = jd["hr_edits"]
    changed = [k for k in ("job_title","summary","tasks","qualifications","working_conditions") if hr.get(k)]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept HR changes", callback_data=f"jdmgr_accept_{jd_id}")],
        [InlineKeyboardButton("↩️ Return to HR", callback_data=f"jdmgr_return_{jd_id}")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_jd_my_jds"), bm()]])
    # Build diff blocks; tasks get their own full listing
    header = f"📄 HR Edits Review\nJD: {jd_id}\nHR changed: {', '.join(changed) if changed else 'nothing'}\n{'─'*30}"
    diff_parts = [header]
    tasks_part = None
    for field in changed:
        orig = jd.get(field, "")
        new_val = hr[field]
        if field == "tasks":
            orig_lines = "\n".join(f"  {i}. {t}" for i, t in enumerate(orig, 1))
            new_lines  = "\n".join(f"  {i}. {t}" for i, t in enumerate(new_val, 1))
            tasks_part = (
                f"📋 TASKS — BEFORE ({len(orig)}):\n{orig_lines}\n"
                f"{'─'*30}\n"
                f"📋 TASKS — AFTER HR ({len(new_val)}):\n{new_lines}"
            )
        else:
            diff_parts.append(f"\n{field.upper()}\n  Before: {str(orig)[:300]}\n  After:  {str(new_val)[:300]}")
    all_chunks = _split_message("\n".join(diff_parts))
    if tasks_part:
        all_chunks += _split_message(tasks_part)
    for i, chunk in enumerate(all_chunks):
        is_last = (i == len(all_chunks) - 1)
        if i == 0:
            await q.edit_message_text(chunk, reply_markup=kb if is_last else None)
        else:
            await q.message.reply_text(chunk, reply_markup=kb if is_last else None)
    return JD_MGR_VIEW


async def jd_mgr_accept(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdmgr_accept_", "")
    jd = get_jd(jd_id)
    update_jd(jd_id, status=S_PENDING_DIR)
    await q.edit_message_text(f"HR edits accepted. JD sent to Director.\nJD ID: {jd_id}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()]]))
    return ConversationHandler.END


async def jd_mgr_return_start(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jdmgr_return_", "")
    context.user_data["jd_mgr_jd_id"] = jd_id
    await q.edit_message_text("Type your comment for HR (what needs to change):",
                               reply_markup=_ckb())
    return JD_MGR_RETURN_TXT


async def jd_mgr_return_text(update, context):
    comment = update.message.text.strip()
    jd_id = context.user_data.get("jd_mgr_jd_id", "")
    jd = get_jd(jd_id)
    # Clear HR edits, put back to Pending_HR with manager's comment in director_notes field
    update_jd(jd_id, status=S_PENDING_HR, hr_edits={},
              director_notes=f"Manager returned with comment: {comment}")
    await update.message.reply_text(f"Sent back to HR with your comment.\nJD ID: {jd_id}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
# FLOW 3B — DIRECTOR FINAL APPROVAL + PDF GENERATION
# ══════════════════════════════════════════════════════════════════════════════

async def jd_dir_list(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading...")
    pending = get_jds_by_status(S_PENDING_DIR)
    if not pending:
        await q.edit_message_text("✅ No JDs pending your approval.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()]])); return ConversationHandler.END
    kb = [[InlineKeyboardButton(
                f"📄 {j['emp_name']} ({j['emp_code']}) — {j['job_title'][:25]}",
                callback_data=f"jddir_view_{j['jd_id']}")]
           for j in pending[:20]]
    kb.append([InlineKeyboardButton("↩️ Back", callback_data="menu_jd"), bm()])
    await q.edit_message_text(f"📋 JDs Pending Director Approval ({len(pending)}):",
                               reply_markup=InlineKeyboardMarkup(kb))
    return JD_DIR_VIEW


async def jd_dir_view(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jddir_view_", "")
    jd = get_jd(jd_id)
    if not jd:
        await q.edit_message_text("❌ JD not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd_approvals"), bm()]])); return ConversationHandler.END
    context.user_data["jd_dir_jd_id"] = jd_id
    has_edits = bool(jd.get("hr_edits"))
    note = f"📝 Previous note: {jd['director_notes']}" if jd.get("director_notes") else ""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve — Generate PDF", callback_data=f"jddir_approve_{jd_id}")],
        [InlineKeyboardButton("💬 Request Changes",        callback_data=f"jddir_change_{jd_id}")],
        [InlineKeyboardButton("❌ Reject",                 callback_data=f"jddir_reject_{jd_id}")],
        [InlineKeyboardButton("↩️ Back", callback_data="menu_jd_approvals"), bm()],
    ])
    await _send_jd_view(q, jd, merged=has_edits, kb=kb, note=note)
    return JD_DIR_VIEW


async def jd_dir_approve(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jddir_approve_", "")
    await q.edit_message_text("⏳ Generating final PDF...")
    try:
        jd = get_jd(jd_id)
        if not jd:
            await q.edit_message_text("❌ JD not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd_approvals"), bm()]])); return ConversationHandler.END

        # Get extra data from Employee_DB
        emp = _get_emp(jd["emp_code"]) or {}
        mgr_rec = _get_emp(jd.get("creator_code", "")) or {}
        mgr_name = mgr_rec.get("Full_Name", "HR Department")

        merged = merge_jd(jd)
        merged.update({
            "department":       emp.get("Department", jd.get("department", "—")),
            "manager_name":     mgr_name,
            "location":         emp.get("Work_Location", "El Dabaa Nuclear Power Plant Site, Matrouh"),
            "employment_type":  emp.get("Contract_Type", "Full-Time"),
            "grade":            emp.get("Grade", "—"),
            "created_by":       mgr_name,
            "created_at":       datetime.now().strftime("%d/%m/%Y"),
        })

        pdf_bytes = generate_jd_pdf(merged)
        dept_code = "".join(w[0].upper() for w in str(merged["department"]).split()[:2])
        safe_name = merged["full_name"].replace(" ", "_")[:15]
        filename = f"JD-{dept_code}-{jd['emp_code']}-{safe_name}.pdf"

        # Upload to Drive (approved folder)
        from drive_utils import upload_to_drive as drive_upload
        await q.edit_message_text("⏳ Uploading to Drive...")
        pdf_link = drive_upload(pdf_bytes, filename, "approved")

        # Update JD status
        update_jd(jd_id, status=S_APPROVED, pdf_link=pdf_link or "")

        conf_kb = [[InlineKeyboardButton("📋 More approvals", callback_data="menu_jd_approvals"), bm()]]
        if pdf_link:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View PDF", url=pdf_link)])
        await q.edit_message_text(
            f"✅ JD APPROVED!\n\nEmployee: {merged['full_name']}\n"
            f"Title: {merged['job_title']}\nJD ID: {jd_id}"
            + ("\n✅ Uploaded to Drive." if pdf_link else "\n⚠️ Drive upload failed — no link."),
            reply_markup=InlineKeyboardMarkup(conf_kb))

    except Exception as e:
        await q.edit_message_text(f"❌ Error: {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_jd_approvals"), bm()]]))

    _clear_dir(context)
    return ConversationHandler.END


async def jd_dir_change_start(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jddir_change_", "")
    context.user_data["jd_dir_jd_id"] = jd_id
    await q.edit_message_text("Type your change request (what needs to be revised):",
                               reply_markup=_ckb())
    return JD_DIR_CHANGE_TXT


async def jd_dir_change_text(update, context):
    note = update.message.text.strip()
    jd_id = context.user_data.get("jd_dir_jd_id", "")
    jd = get_jd(jd_id)
    update_jd(jd_id, status=S_PENDING_HR, director_notes=note)
    _clear_dir(context)
    await update.message.reply_text(f"Change request sent to HR.\nJD ID: {jd_id}\nNote: {note}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 More approvals", callback_data="menu_jd_approvals"), bm()]]))
    return ConversationHandler.END


async def jd_dir_reject_start(update, context):
    q = update.callback_query; await q.answer()
    jd_id = q.data.replace("jddir_reject_", "")
    context.user_data["jd_dir_jd_id"] = jd_id
    await q.edit_message_text("Type the rejection reason:", reply_markup=_ckb())
    return JD_DIR_REJECT_TXT


async def jd_dir_reject_text(update, context):
    reason = update.message.text.strip()
    jd_id = context.user_data.get("jd_dir_jd_id", "")
    jd = get_jd(jd_id)
    update_jd(jd_id, status=S_REJECTED, rejection_reason=reason)
    _clear_dir(context)
    await update.message.reply_text(f"JD {jd_id} rejected.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 More approvals", callback_data="menu_jd_approvals"), bm()]]))
    return ConversationHandler.END


def _clear_dir(ctx):
    for k in ("jd_dir_jd_id",):
        ctx.user_data.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATION HANDLER FACTORIES
# ══════════════════════════════════════════════════════════════════════════════

def get_jd_create_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(jd_start, pattern="^menu_generate_jd$")],
        states={
            JD_EMP: [
                CallbackQueryHandler(jd_emp_select, pattern="^jd_emp_"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_title),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_SUMMARY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_summary),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_SUM_AI: [
                CallbackQueryHandler(jd_sum_use_ai, pattern="^jd_sum_use_ai$"),
                CallbackQueryHandler(jd_sum_keep, pattern="^jd_sum_keep$"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_TASKS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_tasks),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_TSK_AI: [
                CallbackQueryHandler(jd_tsk_use_ai, pattern="^jd_tsk_use_ai$"),
                CallbackQueryHandler(jd_tsk_keep, pattern="^jd_tsk_keep$"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_QUALS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_quals),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_QLS_AI: [
                CallbackQueryHandler(jd_qls_use_ai, pattern="^jd_qls_use_ai$"),
                CallbackQueryHandler(jd_qls_keep, pattern="^jd_qls_keep$"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_WRKCON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_wrkcon_text),
                CallbackQueryHandler(jd_wrkcon_default, pattern="^jd_wc_default$"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_PREVIEW: [
                CallbackQueryHandler(jd_submit, pattern="^jd_submit$"),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$")],
        allow_reentry=True,
    )


def get_jd_hr_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(jd_hr_list, pattern="^menu_jd_reviews$")],
        states={
            JD_HR_VIEW: [
                CallbackQueryHandler(jd_hr_view,        pattern="^jdhr_view_"),
                CallbackQueryHandler(jd_hr_approve,     pattern="^jdhr_approve_"),
                CallbackQueryHandler(jd_hr_edit_start,  pattern="^jdhr_edit_"),
                CallbackQueryHandler(jd_hr_reject_start,pattern="^jdhr_reject_"),
                CallbackQueryHandler(jd_hr_list,        pattern="^menu_jd_reviews$"),
                CallbackQueryHandler(jd_cancel,         pattern="^jd_cancel$"),
            ],
            JD_HR_EDIT_PICK: [
                CallbackQueryHandler(jd_hr_pick_section, pattern="^jdhre_sec_"),
                CallbackQueryHandler(jd_hr_edit_done,   pattern="^jdhre_done$"),
                CallbackQueryHandler(jd_cancel,         pattern="^jd_cancel$"),
            ],
            JD_HR_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_hr_edit_text),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_HR_EDIT_AI: [
                CallbackQueryHandler(jdhr_ai_use,  pattern="^jdhr_ai_use$"),
                CallbackQueryHandler(jdhr_ai_keep, pattern="^jdhr_ai_keep$"),
                CallbackQueryHandler(jd_cancel,    pattern="^jd_cancel$"),
            ],
            JD_HR_REJECT_TXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_hr_reject_text),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$")],
        allow_reentry=True,
    )


def get_jd_manager_dir_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(jd_mgr_list, pattern="^menu_jd_my_jds$"),
            CallbackQueryHandler(jd_dir_list, pattern="^menu_jd_approvals$"),
        ],
        states={
            JD_MGR_VIEW: [
                CallbackQueryHandler(jd_mgr_view,        pattern="^jdmgr_view_"),
                CallbackQueryHandler(jd_mgr_accept,      pattern="^jdmgr_accept_"),
                CallbackQueryHandler(jd_mgr_return_start,pattern="^jdmgr_return_"),
                CallbackQueryHandler(jd_mgr_list,        pattern="^menu_jd_my_jds$"),
                CallbackQueryHandler(jd_cancel,          pattern="^jd_cancel$"),
            ],
            JD_MGR_RETURN_TXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_mgr_return_text),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_DIR_VIEW: [
                CallbackQueryHandler(jd_dir_view,         pattern="^jddir_view_"),
                CallbackQueryHandler(jd_dir_approve,      pattern="^jddir_approve_"),
                CallbackQueryHandler(jd_dir_change_start, pattern="^jddir_change_"),
                CallbackQueryHandler(jd_dir_reject_start, pattern="^jddir_reject_"),
                CallbackQueryHandler(jd_dir_list,         pattern="^menu_jd_approvals$"),
                CallbackQueryHandler(jd_cancel,           pattern="^jd_cancel$"),
            ],
            JD_DIR_CHANGE_TXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_dir_change_text),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
            JD_DIR_REJECT_TXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, jd_dir_reject_text),
                CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(jd_cancel, pattern="^jd_cancel$")],
        allow_reentry=True,
    )
