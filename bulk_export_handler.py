"""
ROIN WORLD FZE — Bulk PDF Export Handler
========================================
Merge multiple approved PDFs into one combined document.
Available to: Bot_Manager, HR_Manager, Director.
"""

import io
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet

def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _bb(): return InlineKeyboardButton("↩️ Bulk Export", callback_data="bulk_export_menu")

ST_MONTH = 2800
ST_SCOPE = 2801
ST_DEPT  = 2802
ST_EMP   = 2803
ST_CONFIRM = 2804

DOC_TYPES = {
    "leave":       ("🏖️ Leave Approvals",   "Leave_Log"),
    "memo":        ("📝 Memos",              "Memo_Log"),
    "warning":     ("⚠️ Warning Letters",    "Warning_Letters"),
    "evaluation":  ("📊 Evaluations",        "Evaluations_Log"),
    "certificate": ("📜 Certificates",       "Certificates"),
    "advance":     ("💰 Salary Advances",    "Salary_Advance"),
}


def _get_emp_info(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
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


def _safe_tab(name):
    try:
        return get_sheet(name).get_all_values()
    except Exception:
        return []


def _get_months():
    now = datetime.now()
    months = []
    for i in range(6):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        months.append((f"{m:02d}", str(y), f"{datetime(y, m, 1).strftime('%B')} {y}"))
    return months


def _parse_date_month(date_str):
    """Extract MM, YYYY from a date string (DD/MM/YYYY or YYYY-MM-DD)."""
    s = str(date_str).strip()
    if not s:
        return None, None
    parts = s.split("/")
    if len(parts) >= 3:
        return parts[1], parts[2][:4]
    parts = s.split("-")
    if len(parts) >= 2:
        return parts[1], parts[0]
    return None, None


def _find_link_col(hdr):
    for name in ("PDF_Drive_Link", "Drive_Link", "Report_Drive_Link"):
        idx = next((i for i, h in enumerate(hdr) if h.strip() == name), None)
        if idx is not None:
            return idx
    return None


def _collect_pdfs(doc_type, mm, yyyy, dept=None, emp_code=None):
    """Return list of Drive URLs matching the filters."""
    info = DOC_TYPES.get(doc_type)
    if not info:
        return []
    _, tab = info
    rows = _safe_tab(tab)
    if len(rows) < 2:
        return []
    hdr = rows[0]
    link_idx = _find_link_col(hdr)
    date_idx = next((i for i, h in enumerate(hdr) if h.strip() in ("Date", "Start_Date", "Created_At")), None)
    ec_idx = next((i for i, h in enumerate(hdr) if "Emp_Code" in h), None)
    dept_idx = next((i for i, h in enumerate(hdr) if "Department" in h), None)
    if link_idx is None:
        return []

    urls = []
    for r in rows[1:]:
        if len(r) <= link_idx or not r[link_idx].strip():
            continue
        if date_idx is not None and len(r) > date_idx:
            m, y = _parse_date_month(r[date_idx])
            if m != mm or y != yyyy:
                continue
        if emp_code and ec_idx is not None and len(r) > ec_idx:
            if r[ec_idx].strip() != str(emp_code):
                continue
        if dept and dept_idx is not None and len(r) > dept_idx:
            if r[dept_idx].strip() != dept:
                continue
        urls.append(r[link_idx].strip())
    return urls


# ══════════════════════════════════════════════════════════════════════════════
#  FLOW
# ══════════════════════════════════════════════════════════════════════════════

async def bulk_export_menu(update, context):
    q = update.callback_query
    await q.answer()
    _, role = _get_emp_info(str(q.from_user.id))
    if role not in ("Bot_Manager", "HR_Manager", "Director"):
        await q.edit_message_text("❌ Access denied.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    kb = []
    for key, (label, _) in DOC_TYPES.items():
        kb.append([InlineKeyboardButton(label, callback_data=f"bex_type_{key}")])
    kb.append([_bm()])
    await q.edit_message_text("📚 Bulk PDF Export\n\nSelect document type:",
                              reply_markup=InlineKeyboardMarkup(kb))
    return ST_MONTH  # next step picks month


async def bex_type_cb(update, context):
    q = update.callback_query
    await q.answer()
    doc_type = q.data.replace("bex_type_", "")
    context.user_data["bex_type"] = doc_type
    context.user_data["bex_label"] = DOC_TYPES.get(doc_type, ("", ""))[0]

    months = _get_months()
    kb = [[InlineKeyboardButton(label, callback_data=f"bex_mo_{mm}_{yyyy}")]
          for mm, yyyy, label in months]
    kb.append([_bb(), _bm()])
    await q.edit_message_text(
        f"📚 {context.user_data['bex_label']}\n\nSelect month:",
        reply_markup=InlineKeyboardMarkup(kb))
    return ST_SCOPE


async def bex_month_cb(update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.replace("bex_mo_", "").split("_")
    context.user_data["bex_mm"] = parts[0]
    context.user_data["bex_yyyy"] = parts[1]

    kb = [
        [InlineKeyboardButton("🏢 All Departments", callback_data="bex_scope_all")],
        [InlineKeyboardButton("👤 Specific Employee", callback_data="bex_scope_emp")],
        [_bb(), _bm()],
    ]
    await q.edit_message_text("Select scope:", reply_markup=InlineKeyboardMarkup(kb))
    return ST_CONFIRM


async def bex_scope_cb(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "bex_scope_emp":
        await q.edit_message_text("Enter employee code:",
                                  reply_markup=InlineKeyboardMarkup([[_bb(), _bm()]]))
        return ST_EMP
    context.user_data["bex_scope"] = "All Departments"
    context.user_data["bex_emp"] = None
    return await _show_preview(update, context)


async def bex_emp_input(update, context):
    code = update.message.text.strip()
    name = _get_emp_name(code)
    if name == code:
        await update.message.reply_text(f"❌ Code '{code}' not found. Try again:")
        return ST_EMP
    context.user_data["bex_scope"] = f"{name} ({code})"
    context.user_data["bex_emp"] = code
    return await _show_preview(update, context, is_callback=False)


async def _show_preview(update, context, is_callback=True):
    d = context.user_data
    urls = _collect_pdfs(d["bex_type"], d["bex_mm"], d["bex_yyyy"],
                         emp_code=d.get("bex_emp"))
    context.user_data["bex_urls"] = urls
    label = d.get("bex_label", "")
    month_label = f"{d['bex_mm']}/{d['bex_yyyy']}"
    scope = d.get("bex_scope", "All")

    if not urls:
        msg = f"📚 No documents found.\n\nType: {label}\nMonth: {month_label}\nScope: {scope}"
        kb = [[_bb(), _bm()]]
        if is_callback:
            await update.callback_query.edit_message_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text(
                msg, reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    msg = (
        f"📚 Bulk Export Preview\n{'━' * 28}\n\n"
        f"Type: {label}\n"
        f"Month: {month_label}\n"
        f"Scope: {scope}\n"
        f"Documents found: {len(urls)}"
    )
    kb = [
        [InlineKeyboardButton("✅ Generate Combined PDF", callback_data="bex_generate")],
        [_bb(), _bm()],
    ]
    if is_callback:
        await update.callback_query.edit_message_text(
            msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(kb))
    return ST_CONFIRM


async def bex_generate(update, context):
    q = update.callback_query
    await q.answer()
    urls = context.user_data.get("bex_urls", [])
    if not urls:
        await q.edit_message_text("❌ No documents to merge.",
                                  reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    await q.edit_message_text(f"⏳ Downloading and merging {len(urls)} PDFs...\nThis may take a moment.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    from drive_utils import download_pdf_from_drive, upload_to_drive_by_id
    from config import EMPLOYEE_FOLDERS_PARENT

    # Download PDFs
    pdf_list = []
    for url in urls:
        try:
            data = download_pdf_from_drive(url)
            if data:
                pdf_list.append(data)
        except Exception:
            pass

    if not pdf_list:
        await q.edit_message_text("❌ Could not download any PDFs from Drive.",
                                  reply_markup=InlineKeyboardMarkup([[_bb(), _bm()]]))
        return ConversationHandler.END

    # Generate cover page
    from fpdf import FPDF
    from font_utils import add_dejavu
    cover = FPDF()
    cover.add_page()
    add_dejavu(cover)
    cover.set_font("DejaVu", size=18)
    cover.cell(0, 20, "ROIN WORLD FZE EGYPT BRANCH", ln=True, align="C")
    cover.ln(15)
    cover.set_font("DejaVu", size=14)
    cover.cell(0, 10, "BULK DOCUMENT EXPORT", ln=True, align="C")
    cover.ln(10)
    cover.set_font("DejaVu", size=11)
    d = context.user_data
    lines = [
        f"Type: {d.get('bex_label', '')}",
        f"Period: {d.get('bex_mm', '')}/{d.get('bex_yyyy', '')}",
        f"Scope: {d.get('bex_scope', 'All')}",
        f"Total Documents: {len(pdf_list)}",
        f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]
    ec, _ = _get_emp_info(str(q.from_user.id))
    if ec:
        lines.append(f"Generated by: {_get_emp_name(ec)}")
    for line in lines:
        cover.cell(0, 8, line, ln=True, align="C")
    cover_bytes = cover.output()

    # Merge PDFs
    try:
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        # Add cover
        reader = PdfReader(io.BytesIO(cover_bytes))
        for page in reader.pages:
            writer.add_page(page)
        # Add each PDF
        for pdf_bytes in pdf_list:
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception:
                pass
        output = io.BytesIO()
        writer.write(output)
        merged_bytes = output.getvalue()
    except Exception as e:
        await q.edit_message_text(f"❌ PDF merge failed: {e}",
                                  reply_markup=InlineKeyboardMarkup([[_bb(), _bm()]]))
        return ConversationHandler.END

    # Upload merged PDF
    type_label = d.get("bex_type", "ALL").upper()
    filename = f"BULK_{type_label}_{d.get('bex_mm', '')}-{d.get('bex_yyyy', '')}.pdf"
    drive_url = upload_to_drive_by_id(merged_bytes, filename, EMPLOYEE_FOLDERS_PARENT)

    if drive_url:
        kb = [
            [InlineKeyboardButton("📄 View Combined PDF", url=drive_url)],
            [_bm()],
        ]
        await q.edit_message_text(
            f"✅ Combined PDF generated!\n"
            f"{len(pdf_list)} documents merged into one file.",
            reply_markup=InlineKeyboardMarkup(kb))
    else:
        await q.edit_message_text(
            f"✅ Merged {len(pdf_list)} PDFs but Drive upload failed.",
            reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


async def bex_cancel(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_bulk_export_handlers():
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bulk_export_menu, pattern="^bulk_export_menu$")],
        states={
            ST_MONTH: [
                CallbackQueryHandler(bex_type_cb, pattern="^bex_type_"),
            ],
            ST_SCOPE: [
                CallbackQueryHandler(bex_month_cb, pattern="^bex_mo_"),
            ],
            ST_CONFIRM: [
                CallbackQueryHandler(bex_scope_cb, pattern="^bex_scope_"),
                CallbackQueryHandler(bex_generate, pattern="^bex_generate$"),
            ],
            ST_EMP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bex_emp_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(bex_cancel, pattern="^back_to_menu$"),
            CallbackQueryHandler(bex_cancel, pattern="^bulk_export_menu$"),
        ],
        allow_reentry=True,
    )
    return [conv]
