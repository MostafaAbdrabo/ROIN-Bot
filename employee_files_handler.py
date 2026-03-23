"""
ROIN WORLD FZE — Employee Files Handler
========================================
Browse employee documents organized by category.
HR/Director/Bot_Manager can view any employee's files.
Employees can view their own via My Documents.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _bf(): return InlineKeyboardButton("↩️ Employee Files", callback_data="emp_files_menu")

ST_EMP_CODE = 2700


def _get_emp_info(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0:
            continue
        if r[1].strip() == str(tid):
            return r[0].strip(), r[3].strip() if len(r) > 3 else "Employee"
    return None, None


def _get_emp_name(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r.get("Full_Name", str(ec))
    except Exception:
        pass
    return str(ec)


def _get_drive_folder_link(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return str(r.get("Drive_Folder_Link", "")).strip()
    except Exception:
        pass
    return ""


def _safe_tab(name):
    try:
        return get_sheet(name).get_all_values()
    except Exception:
        return []


def _collect_docs(ec):
    """Collect all Drive-linked documents for an employee, grouped by category."""
    docs = {}

    # Leave documents
    rows = _safe_tab("Leave_Log")
    if rows:
        hdr = rows[0]
        ec_idx = next((i for i, h in enumerate(hdr) if "Emp_Code" in h), None)
        link_idx = next((i for i, h in enumerate(hdr) if "PDF_Drive_Link" in h or "Drive_Link" in h), None)
        id_idx = next((i for i, h in enumerate(hdr) if "Request_ID" in h), None)
        type_idx = next((i for i, h in enumerate(hdr) if "Request_Type" in h or "Leave_Type" in h), None)
        date_idx = next((i for i, h in enumerate(hdr) if h.strip() in ("Start_Date", "Date")), None)
        if ec_idx is not None and link_idx is not None:
            leaves = []
            for r in rows[1:]:
                if len(r) > max(ec_idx, link_idx) and r[ec_idx].strip() == str(ec) and r[link_idx].strip():
                    rid = r[id_idx].strip() if id_idx is not None and len(r) > id_idx else ""
                    lt = r[type_idx].strip() if type_idx is not None and len(r) > type_idx else ""
                    dt = r[date_idx].strip() if date_idx is not None and len(r) > date_idx else ""
                    label = f"{rid} — {lt} {dt}" if rid else f"Leave {dt}"
                    leaves.append((label, r[link_idx].strip()))
            if leaves:
                docs["🏖️ Leave Documents"] = leaves

    # Memos
    rows = _safe_tab("Memo_Log")
    if rows:
        hdr = rows[0]
        ec_idx = next((i for i, h in enumerate(hdr) if "Emp_Code" in h or "Requester_Code" in h), None)
        link_idx = next((i for i, h in enumerate(hdr) if "Drive_Link" in h or "PDF_Drive_Link" in h), None)
        id_idx = next((i for i, h in enumerate(hdr) if "Memo_ID" in h or "Request_ID" in h or "SZ_Number" in h), None)
        subj_idx = next((i for i, h in enumerate(hdr) if "Subject" in h or "Topic" in h), None)
        if ec_idx is not None and link_idx is not None:
            memos = []
            for r in rows[1:]:
                if len(r) > max(ec_idx, link_idx) and r[ec_idx].strip() == str(ec) and r[link_idx].strip():
                    rid = r[id_idx].strip() if id_idx is not None and len(r) > id_idx else ""
                    subj = r[subj_idx].strip()[:30] if subj_idx is not None and len(r) > subj_idx else ""
                    label = f"{rid} — {subj}" if rid else f"Memo {subj}"
                    memos.append((label, r[link_idx].strip()))
            if memos:
                docs["📝 Memos"] = memos

    # Generic tab scanner for common pattern
    _scan = [
        ("Evaluations_Log",  "📊 Evaluations",  ["Report_Drive_Link", "PDF_Drive_Link", "Drive_Link"]),
        ("Warning_Letters",  "⚠️ Warnings",      ["PDF_Drive_Link", "Drive_Link"]),
        ("Certificates",     "📜 Certificates",   ["PDF_Drive_Link", "Drive_Link"]),
        ("Salary_Advance",   "💰 Salary Advances", ["PDF_Drive_Link", "Drive_Link"]),
    ]
    for tab_name, cat_label, link_cols in _scan:
        rows = _safe_tab(tab_name)
        if not rows:
            continue
        hdr = rows[0]
        ec_idx = next((i for i, h in enumerate(hdr) if "Emp_Code" in h), None)
        link_idx = None
        for lc in link_cols:
            link_idx = next((i for i, h in enumerate(hdr) if h.strip() == lc), None)
            if link_idx is not None:
                break
        id_idx = next((i for i, h in enumerate(hdr) if "ID" in h or "Request_ID" in h), None)
        date_idx = next((i for i, h in enumerate(hdr) if h.strip() in ("Date", "Created_At")), None)
        if ec_idx is None or link_idx is None:
            continue
        items = []
        for r in rows[1:]:
            if len(r) > max(ec_idx, link_idx) and r[ec_idx].strip() == str(ec) and r[link_idx].strip():
                rid = r[id_idx].strip() if id_idx is not None and len(r) > id_idx else ""
                dt = r[date_idx].strip() if date_idx is not None and len(r) > date_idx else ""
                label = f"{rid} {dt}".strip() or tab_name
                items.append((label, r[link_idx].strip()))
        if items:
            docs[cat_label] = items

    return docs


# ══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE FILES MENU (HR / Manager view)
# ══════════════════════════════════════════════════════════════════════════════

async def emp_files_menu(update, context):
    q = update.callback_query
    await q.answer()
    ec, role = _get_emp_info(str(q.from_user.id))
    if role not in ("Bot_Manager", "HR_Manager", "HR_Staff", "Director"):
        await q.edit_message_text("❌ Access denied.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END
    await q.edit_message_text(
        "📁 Employee Files\n\nEnter employee code:",
        reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ST_EMP_CODE


async def emp_files_code_input(update, context):
    code = update.message.text.strip()
    name = _get_emp_name(code)
    if name == code:
        await update.message.reply_text(
            f"❌ Employee code '{code}' not found. Try again:",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ST_EMP_CODE
    return await _show_employee_files(update, context, code, name)


async def _show_employee_files(update, context, ec, name, is_callback=False):
    docs = _collect_docs(ec)
    folder_link = _get_drive_folder_link(ec)

    if not docs and not folder_link:
        msg = f"📁 {name} ({ec})\n\nNo documents found."
        kb = [[_bf(), _bm()] if not is_callback else [_bm()]]
        if is_callback:
            await update.callback_query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    msg = f"📁 Employee Files — {name} ({ec})\n{'━' * 28}\n"
    kb = []
    for cat, items in docs.items():
        msg += f"\n{cat} ({len(items)})\n"
        for label, url in items[-10:]:  # last 10 per category
            kb.append([InlineKeyboardButton(f"📄 {label}", url=url)])

    if folder_link:
        kb.append([InlineKeyboardButton("📁 Open Drive Folder", url=folder_link)])
    kb.append([_bf(), _bm()] if not is_callback else [_bm()])

    if is_callback:
        await update.callback_query.edit_message_text(
            msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(kb))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  MY DOCUMENTS (employee self-view)
# ══════════════════════════════════════════════════════════════════════════════

async def my_documents(update, context):
    q = update.callback_query
    await q.answer()
    ec, _ = _get_emp_info(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("❌ Not registered.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    name = _get_emp_name(ec)
    docs = _collect_docs(ec)
    folder_link = _get_drive_folder_link(ec)

    if not docs and not folder_link:
        await q.edit_message_text(
            f"📁 My Documents\n\nNo documents found yet.",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    msg = f"📁 My Documents — {name}\n{'━' * 28}\n"
    kb = []
    for cat, items in docs.items():
        msg += f"\n{cat} ({len(items)})\n"
        for label, url in items[-10:]:
            kb.append([InlineKeyboardButton(f"📄 {label}", url=url)])

    if folder_link:
        kb.append([InlineKeyboardButton("📁 Open My Drive Folder", url=folder_link)])
    kb.append([_bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_emp_files_handlers():
    files_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(emp_files_menu, pattern="^emp_files_menu$")],
        states={
            ST_EMP_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, emp_files_code_input)],
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^back_to_menu$"),
        ],
        allow_reentry=True,
    )
    return [files_conv]


def get_emp_files_static_handlers():
    from telegram.ext import CallbackQueryHandler as CQH
    return [
        CQH(my_documents, pattern="^my_documents$"),
    ]
