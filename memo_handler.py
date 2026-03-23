"""
ROIN WORLD FZE — Memo / Служебная Записка System
==================================================
Full submission → HR review → HR_Manager review → Director decision flow.
Bilingual (RU + EN). AI writing assistance via ai_writer.py.
PDF generated with fpdf2. Notification center integration.

States:
  MEMO_LANG      = 3200
  MEMO_TOPIC     = 3201
  MEMO_CATEGORY  = 3202
  MEMO_BODY      = 3203
  MEMO_AI_WAIT   = 3204
  MEMO_AI_INSTR  = 3205
  MEMO_MANUAL    = 3206
  MEMO_CONFIRM   = 3207
  HR_MEMO_CHG    = 3208
  HR_MEMO_REJ    = 3209
  DIR_MEMO_REJ   = 3210
  MEMO_RESUBMIT  = 3211
"""

import io, os, secrets
from datetime import datetime
from fpdf import FPDF
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import get_sheet
from notification_handler import create_notification
from font_utils import add_dejavu, FONT_PATH, FONT_BOLD, FONT_ITALIC
from drive_utils import upload_to_drive

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO     = os.path.join(BASE_DIR, "company_logo.png")

# ConversationHandler states
MEMO_LANG     = 3200
MEMO_TOPIC    = 3201
MEMO_CATEGORY = 3202
MEMO_BODY     = 3203
MEMO_AI_WAIT  = 3204
MEMO_AI_INSTR = 3205
MEMO_MANUAL   = 3206
MEMO_CONFIRM  = 3207
HR_MEMO_CHG   = 3208
HR_MEMO_REJ   = 3209
DIR_MEMO_REJ  = 3210
MEMO_RESUBMIT = 3211

TAB_MEMO = "Memo_Log"
TAB_USER = "User_Registry"

MEMO_ROLES = {"Bot_Manager", "Director", "HR_Manager", "HR_Staff", "Direct_Manager", "Supervisor"}
HR_REVIEW_ROLES = {"HR_Staff", "HR_Manager", "Bot_Manager"}
HR_MGR_ROLES   = {"HR_Manager", "Bot_Manager"}
DIR_ROLES      = {"Director", "Bot_Manager"}

CATEGORIES = [
    ("salary",       "💰 Salary (increase/decrease/bonus)"),
    ("disciplinary", "⚠️ Disciplinary (warning/penalty)"),
    ("staffing",     "👥 Staffing (hire/transfer/role)"),
    ("equipment",    "🔧 Equipment (purchase/repair)"),
    ("policy",       "📋 Policy (change/new/update)"),
    ("other",        "📝 Other"),
]


def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bb(): return InlineKeyboardButton("↩️ Back", callback_data="menu_memos")


# ── Sheet helpers ──────────────────────────────────────────────────────────────

def _find_ec_by_tid(tid):
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if len(r) > 1 and r[1].strip() == str(tid):
                return r[0].strip(), r[3].strip() if len(r) > 3 else "Employee"
    except Exception:
        pass
    return None, "Employee"


def _get_emp(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r
    except Exception:
        pass
    return {}


def _get_director():
    """Return (ec, telegram_id, full_name) for first Director."""
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if len(r) > 3 and r[3].strip() == "Director":
                ec = r[0].strip(); tid = r[1].strip() if len(r) > 1 else ""
                emp = _get_emp(ec)
                return ec, tid, emp.get("Full_Name", "Director")
    except Exception:
        pass
    return None, None, "Director"


def _get_hr_staff_tids():
    """Return list of telegram_ids for HR_Staff and HR_Manager."""
    tids = []
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if len(r) > 3 and r[3].strip() in ("HR_Staff", "HR_Manager"):
                tid = r[1].strip() if len(r) > 1 else ""
                if tid: tids.append(tid)
    except Exception:
        pass
    return tids


def _get_hr_manager_tids():
    tids = []
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if len(r) > 3 and r[3].strip() in ("HR_Manager", "Bot_Manager"):
                tid = r[1].strip() if len(r) > 1 else ""
                if tid: tids.append(tid)
    except Exception:
        pass
    return tids


def _get_hr_ecs():
    """Return list of emp_codes for HR_Staff/HR_Manager."""
    ecs = []
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if len(r) > 3 and r[3].strip() in ("HR_Staff", "HR_Manager"):
                ec = r[0].strip()
                if ec: ecs.append(ec)
    except Exception:
        pass
    return ecs


def _next_memo_id():
    year = str(datetime.now().year)
    prefix = f"MEMO-{year}-"
    max_n = 0
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        for r in rows[1:]:
            if r and str(r[0]).startswith(prefix):
                try:
                    max_n = max(max_n, int(r[0].split("-")[-1]))
                except ValueError:
                    pass
    except Exception:
        pass
    return f"{prefix}{str(max_n + 1).zfill(4)}"


def _next_sz_number():
    """
    Generate registration number in HR MM-NNNN format.
    MM  = current month number (01-12)
    NNNN = yearly sequential, continues all year (e.g. HR 12-316).
    """
    month = datetime.now().strftime("%m")
    prefix_hr = "HR "
    max_n = 0
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        for r in rows[1:]:
            if len(r) > 9 and str(r[9]).startswith(prefix_hr):
                try:
                    # format: "HR MM-NNNN" → split on "-" → last part is NNNN
                    parts = str(r[9]).strip().split("-")
                    max_n = max(max_n, int(parts[-1]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass
    return f"HR {month}-{str(max_n + 1).zfill(3)}"


def _find_memo(memo_id):
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r and r[0].strip() == memo_id:
                return i + 1, r
    except Exception:
        pass
    return None, None


def _get_tid_by_ec(ec):
    try:
        for i, r in enumerate(get_sheet(TAB_USER).get_all_values()):
            if i == 0: continue
            if r[0].strip() == str(ec):
                return r[1].strip() if len(r) > 1 else None
    except Exception:
        pass
    return None


# ── PDF generation ─────────────────────────────────────────────────────────────

def _u(text):
    """Return text as-is (Unicode string) for DejaVu font — no stripping."""
    return str(text) if text else ""


def _sig_right(pdf, sig_bytes, sig_text, signer_name, signed_at=""):
    """Place a signature block right-aligned (submitter / director style)."""
    placed = False
    if sig_bytes:
        try:
            x = pdf.w - pdf.r_margin - 50
            pdf.image(io.BytesIO(sig_bytes), x=x, y=pdf.get_y(), w=45, h=18)
            pdf.ln(20); placed = True
        except Exception:
            pass
    if not placed:
        if sig_text:
            pdf.set_font("DejaVu", "I", 9)
            pdf.cell(0, 6, _u(sig_text), new_x="LMARGIN", new_y="NEXT", align="R")
        else:
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 6, "___________________________", new_x="LMARGIN", new_y="NEXT", align="R")
    if signer_name:
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(0, 5, _u(signer_name), new_x="LMARGIN", new_y="NEXT", align="R")
    if signed_at:
        pdf.set_font("DejaVu", "I", 8)
        pdf.cell(0, 4, _u(signed_at), new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("DejaVu", "", 12)
    pdf.ln(3)


def _sig_left(pdf, sig_bytes, sig_text, label, signer_name, signed_at=""):
    """Place a 'Согласовано' signature block left-aligned (manager approval)."""
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, _u(label), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    placed = False
    if sig_bytes:
        try:
            pdf.image(io.BytesIO(sig_bytes), x=pdf.l_margin, y=pdf.get_y(), w=40, h=16)
            pdf.ln(18); placed = True
        except Exception:
            pass
    if not placed:
        if sig_text:
            pdf.set_font("DejaVu", "I", 9)
            pdf.cell(0, 6, _u(sig_text), new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 6, "_________________", new_x="LMARGIN", new_y="NEXT")
    if signer_name:
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(0, 5, _u(signer_name), new_x="LMARGIN", new_y="NEXT")
    if signed_at:
        pdf.set_font("DejaVu", "I", 8)
        pdf.cell(0, 4, _u(signed_at), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 12)
    pdf.ln(3)


def generate_memo_pdf(memo_data, sigs=None):
    """
    Generate official Служебная записка PDF in exact company format.

    memo_data keys:
      memo_id, sz_number, date, emp_code, emp_name, job_title, job_title_ru,
      department, language, topic, body_ru, body_en,
      director_name, director_last_name, director_initials,
      submitter_last_name, submitter_initials,
      final_status, rejection_reason, director_resolution,
      hr_staff_name, hr_staff_date, hr_manager_name, hr_manager_date,
      director_date, submitter_name, submitter_date,
      emp_phone, emp_email

    sigs dict: {role: (bytes_or_None, text_or_None)}
      roles: "submitter", "hr_staff", "hr_manager", "director"
    Returns bytes.
    """
    if sigs is None: sigs = {}

    pdf = FPDF()
    add_dejavu(pdf)
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    sz       = memo_data.get("sz_number", "")
    memo_id  = memo_data.get("memo_id", "")
    date_str = memo_data.get("date", datetime.now().strftime("%d.%m.%Y"))
    # Normalise date separator for display
    date_disp = date_str.replace("/", ".")
    lang     = memo_data.get("language", "EN")
    body_ru  = memo_data.get("body_ru", "")
    body_en  = memo_data.get("body_en", "")
    final    = memo_data.get("final_status", "Draft")
    ver      = f"SIG-{secrets.token_hex(4).upper()}"

    # Names
    dir_name      = memo_data.get("director_name", "Director")
    dir_last      = memo_data.get("director_last_name", dir_name.split()[-1] if dir_name else "")
    dir_initials  = memo_data.get("director_initials", "")
    sub_name      = memo_data.get("submitter_name", memo_data.get("emp_name", ""))
    sub_last      = memo_data.get("submitter_last_name", sub_name.split()[-1] if sub_name else "")
    sub_initials  = memo_data.get("submitter_initials", "")
    job_title_ru  = memo_data.get("job_title_ru", memo_data.get("job_title", ""))
    emp_code      = memo_data.get("emp_code", "")
    emp_phone     = memo_data.get("emp_phone", "")
    emp_email     = memo_data.get("emp_email", "info.egypt@roinworld.com")
    resolution    = memo_data.get("director_resolution", "")

    # ── Director resolution (top-left corner, italic blue, only if approved) ──
    if resolution and final == "Director_Approved":
        pdf.set_text_color(0, 0, 180)
        pdf.set_font("DejaVu", "I", 10)
        pdf.multi_cell(pdf.epw, 6, _u(resolution))
        pdf.set_text_color(0, 0, 0)
        sb_dir, st_dir = sigs.get("director", (None, None))
        if sb_dir:
            try:
                pdf.image(io.BytesIO(sb_dir), x=pdf.l_margin, y=pdf.get_y(), w=35, h=14)
                pdf.ln(16)
            except Exception:
                pass
        pdf.ln(4)
    else:
        pdf.ln(5)

    # ── Right-side "To/From" header block ─────────────────────────────────────
    pdf.set_font("DejaVu", "", 12)
    right_x = pdf.w - pdf.r_margin - 70   # start x of right block (~120mm from left)
    line_h  = 6

    def rline(text):
        pdf.set_x(right_x)
        pdf.cell(70, line_h, _u(text), new_x="LMARGIN", new_y="NEXT")

    if lang in ("RU", "BOTH"):
        rline("Директору филиала")
        rline("ROIN WORLD FZE в АРЕ")
        if dir_last:
            rline(f"{dir_last} {dir_initials}".strip())
        else:
            rline(dir_name)
        rline(f"От {job_title_ru}")
        if sub_last:
            rline(f"{sub_last} {sub_initials} ({emp_code})".strip())
        else:
            rline(f"{sub_name} ({emp_code})")
    else:
        rline("To the Branch Director")
        rline("ROIN WORLD FZE in ARE")
        rline(dir_name)
        rline(f"From {memo_data.get('job_title', '')}")
        rline(f"{sub_name} ({emp_code})")

    pdf.ln(10)

    # ── Title ─────────────────────────────────────────────────────────────────
    if lang in ("RU", "BOTH"):
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Служебная записка", new_x="LMARGIN", new_y="NEXT", align="C")
    if lang in ("EN", "BOTH"):
        if lang == "BOTH":
            pdf.set_font("DejaVu", "", 11)
            pdf.cell(0, 7, "Internal Memo", new_x="LMARGIN", new_y="NEXT", align="C")
        else:
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, "Internal Memo", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # ── Russian body text ──────────────────────────────────────────────────────
    if lang in ("RU", "BOTH") and body_ru:
        pdf.set_font("DejaVu", "", 12)
        for para in body_ru.split("\n"):
            if para.strip():
                pdf.multi_cell(pdf.epw, 7, _u(para.strip()), align="J")
            else:
                pdf.ln(3)
        pdf.ln(4)

    # ── English body text ──────────────────────────────────────────────────────
    if lang in ("EN", "BOTH") and body_en:
        if lang == "BOTH":
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(4)
            # English "To/From" block
            pdf.set_font("DejaVu", "", 12)
            rline("To the Branch Director")
            rline("ROIN WORLD FZE in ARE")
            rline(dir_name)
            rline(f"From {memo_data.get('job_title', '')}")
            rline(f"{sub_name} ({emp_code})")
            pdf.ln(8)
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, "Internal Memo", new_x="LMARGIN", new_y="NEXT", align="C")
            pdf.ln(6)
        pdf.set_font("DejaVu", "", 12)
        for para in body_en.split("\n"):
            if para.strip():
                pdf.multi_cell(pdf.epw, 7, _u(para.strip()), align="J")
            else:
                pdf.ln(3)
        pdf.ln(4)

    # ── Date (right-aligned) ───────────────────────────────────────────────────
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 7, date_disp, new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(3)

    # ── Submitter signature (right side) ───────────────────────────────────────
    sb, st = sigs.get("submitter", (None, None))
    _sig_right(pdf, sb, st, sub_name, memo_data.get("submitter_date", date_disp))

    # ── Manager approval "Согласовано" (left side, if applicable) ─────────────
    mgr_name = memo_data.get("hr_manager_name", "")
    if mgr_name:
        pdf.ln(4)
        sb3, st3 = sigs.get("hr_manager", (None, None))
        if lang in ("RU", "BOTH"):
            _sig_left(pdf, sb3, st3,
                      "Согласовано:", mgr_name,
                      memo_data.get("hr_manager_date", ""))
        if lang in ("EN", "BOTH"):
            _sig_left(pdf, None, None,
                      "Approved by:", mgr_name,
                      memo_data.get("hr_manager_date", ""))

    # ── Registration stamp (centered, bottom area) ────────────────────────────
    if sz:
        reg_date = memo_data.get("hr_staff_date", date_disp)
        pdf.ln(6)
        cw = 80   # stamp box width
        cx = (pdf.w - cw) / 2
        pdf.set_x(cx)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_draw_color(100, 100, 100)
        # Draw a simple box-style stamp
        y0 = pdf.get_y()
        pdf.set_x(cx); pdf.cell(cw, 6, "─" * 30, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_x(cx); pdf.cell(cw, 6, "ROIN WORLD FZE EGYPT", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_x(cx); pdf.cell(cw, 6, f"Incoming № {sz}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_x(cx); pdf.cell(cw, 6, reg_date, new_x="LMARGIN", new_y="NEXT", align="C")
        # HR staff signature in stamp area
        sb2, st2 = sigs.get("hr_staff", (None, None))
        if sb2:
            try:
                sig_x = cx + (cw - 35) / 2
                pdf.image(io.BytesIO(sb2), x=sig_x, y=pdf.get_y(), w=35, h=12)
                pdf.ln(14)
            except Exception:
                pdf.ln(4)
        else:
            pdf.set_x(cx)
            pdf.cell(cw, 6, memo_data.get("hr_staff_name", "HR Staff"),
                     new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_x(cx); pdf.cell(cw, 6, "─" * 30, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_draw_color(0, 0, 0)
        pdf.ln(4)

    # ── Director decision banner (if rejected) ─────────────────────────────────
    if final == "Rejected":
        pdf.ln(3)
        pdf.set_text_color(200, 0, 0)
        pdf.set_font("DejaVu", "B", 12)
        rej_label = "ОТКЛОНЕНО / REJECTED"
        pdf.cell(0, 8, rej_label, new_x="LMARGIN", new_y="NEXT", align="C")
        rej = memo_data.get("rejection_reason", "")
        if rej:
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(pdf.epw, 6, _u(f"Reason: {rej}"), align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        # Director signature for rejection too
        if not resolution:
            sb4, st4 = sigs.get("director", (None, None))
            if sb4 or st4:
                _sig_right(pdf, sb4, st4, dir_name, memo_data.get("director_date", ""))

    # ── Bottom left: Исп. contact info ────────────────────────────────────────
    pdf.ln(4)
    pdf.set_font("DejaVu", "", 10)
    contact_lines = [f"Исп. {sub_name}"]
    if job_title_ru:
        contact_lines.append(f"Должность: {job_title_ru}")
    if emp_phone:
        contact_lines.append(f"Номер Телефона: {emp_phone}")
    contact_lines.append(f"Почта: {emp_email or 'info.egypt@roinworld.com'}")
    for cl in contact_lines:
        pdf.cell(0, 5, _u(cl), new_x="LMARGIN", new_y="NEXT")

    # ── Footer verification line ───────────────────────────────────────────────
    pdf.ln(3)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(1)
    pdf.set_font("DejaVu", "I", 7)
    parts = [f"Ref: {memo_id}"]
    if sz: parts.append(f"Reg: {sz}")
    parts.append(f"Verified: {ver}")
    pdf.cell(0, 4, "   |   ".join(parts), new_x="LMARGIN", new_y="NEXT", align="C")

    return bytes(pdf.output())


# ── Memo Log helpers ───────────────────────────────────────────────────────────

def _append_memo_row(memo_id, ec, lang, topic, category, body_ru, body_en):
    """Write initial Draft row to Memo_Log."""
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Columns: Memo_ID, Date, Emp_Code, Emp_Name(VLOOKUP), Department(VLOOKUP),
    #   Language, Topic, Topic_Category, Body_Text, Registration_Number,
    #   Registration_Date, HR_Staff_Code, HR_Staff_Status, HR_Staff_Date,
    #   HR_Staff_Notes, HR_Manager_Status, HR_Manager_Date,
    #   Director_Status, Director_Date, Director_Notes,
    #   Final_Status, PDF_Preview_Link, PDF_Final_Link, Drive_Link
    body_combined = f"[RU]: {body_ru}\n\n[EN]: {body_en}" if body_ru and body_en else (body_ru or body_en)
    get_sheet(TAB_MEMO).append_row([
        memo_id, date_str, str(ec), "", "",
        lang, topic, category, body_combined, "",
        "", "", "", "", "",
        "", "",
        "", "", "",
        "Submitted", "", "", ""
    ])


def _update_memo_cell(rn, col, val):
    get_sheet(TAB_MEMO).update_cell(rn, col, val)


# ── Submitter flow ─────────────────────────────────────────────────────────────

async def memo_start(update, context):
    """Entry: 📝 New Memo — choose language."""
    q = update.callback_query; await q.answer()
    ec, role = _find_ec_by_tid(str(q.from_user.id))
    if not ec or role not in MEMO_ROLES:
        await q.edit_message_text("⛔ You don't have permission to submit memos.",
                                  reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END
    context.user_data["memo_ec"] = ec
    context.user_data["memo_role"] = role
    kb = [
        [InlineKeyboardButton("🇷🇺 Russian only", callback_data="mlang_RU")],
        [InlineKeyboardButton("🇬🇧 English only", callback_data="mlang_EN")],
        [InlineKeyboardButton("🇷🇺🇬🇧 Russian + English", callback_data="mlang_BOTH")],
        [InlineKeyboardButton("Cancel", callback_data="menu_memos")],
    ]
    await q.edit_message_text("📝 New Memo\n\nSelect language:", reply_markup=InlineKeyboardMarkup(kb))
    return MEMO_LANG


async def memo_lang_chosen(update, context):
    q = update.callback_query; await q.answer()
    lang = q.data.replace("mlang_", "")
    context.user_data["memo_lang"] = lang
    await q.edit_message_text("📝 Enter the topic / title of your memo:\n\n(Short descriptive title)")
    return MEMO_TOPIC


async def memo_topic_received(update, context):
    topic = update.message.text.strip()
    if len(topic) < 3:
        await update.message.reply_text("Topic too short. Try again:"); return MEMO_TOPIC
    context.user_data["memo_topic"] = topic
    kb = [[InlineKeyboardButton(label, callback_data=f"mcat_{key}")] for key, label in CATEGORIES]
    await update.message.reply_text("Select topic category:", reply_markup=InlineKeyboardMarkup(kb))
    return MEMO_CATEGORY


async def memo_category_chosen(update, context):
    q = update.callback_query; await q.answer()
    cat = q.data.replace("mcat_", "")
    context.user_data["memo_category"] = cat
    lang = context.user_data.get("memo_lang", "EN")
    if lang == "BOTH":
        prompt = "Enter your memo body text.\n\n🇷🇺 First, type the RUSSIAN text:"
    elif lang == "RU":
        prompt = "Enter your memo body text in Russian:"
    else:
        prompt = "Enter your memo body text in English:"
    context.user_data["memo_body_stage"] = "ru" if lang in ("RU", "BOTH") else "en"
    await q.edit_message_text(f"📝 {prompt}")
    return MEMO_BODY


async def memo_body_received(update, context):
    text = update.message.text.strip()
    if len(text) < 10:
        await update.message.reply_text("Text too short. Please write more detail:"); return MEMO_BODY
    stage = context.user_data.get("memo_body_stage", "en")
    lang  = context.user_data.get("memo_lang", "EN")
    if stage == "ru":
        context.user_data["memo_body_ru"] = text
        if lang == "BOTH":
            context.user_data["memo_body_stage"] = "en"
            await update.message.reply_text("🇬🇧 Now enter the ENGLISH text:")
            return MEMO_BODY
    else:
        context.user_data["memo_body_en"] = text

    # Both parts collected — show action buttons
    return await _show_body_options(update, context)


async def _show_body_options(update, context, from_query=False):
    lang = context.user_data.get("memo_lang", "EN")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    display_text = body_en if lang == "EN" else (body_ru if lang == "RU" else
                                                  f"[RU]: {body_ru[:100]}...\n[EN]: {body_en[:100]}...")
    preview = display_text[:300] + ("..." if len(display_text) > 300 else "")
    msg = f"📝 Your text:\n\"{preview}\"\n\nWhat would you like to do?"
    kb = [
        [InlineKeyboardButton("✨ Improve with AI", callback_data="memo_ai_improve")],
        [InlineKeyboardButton("✍️ Edit manually",   callback_data="memo_manual_edit")],
        [InlineKeyboardButton("✅ Text is good — continue", callback_data="memo_confirm_text")],
        [bm()],
    ]
    if from_query:
        q = update.callback_query; await q.answer()
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return MEMO_AI_WAIT


async def memo_ai_improve(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("✨ Improving with AI...")
    from ai_writer import improve_text
    lang = context.user_data.get("memo_lang", "EN")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    errors = []
    if body_ru:
        improved_ru, err = await improve_text(body_ru, context="memo", lang="RU")
        if err: errors.append(f"RU: {err}")
        else: context.user_data["memo_ai_ru"] = improved_ru
    if body_en:
        improved_en, err = await improve_text(body_en, context="memo", lang="EN")
        if err: errors.append(f"EN: {err}")
        else: context.user_data["memo_ai_en"] = improved_en

    if errors:
        kb = [[InlineKeyboardButton("↩️ Back", callback_data="memo_back_to_options")], [bm()]]
        await q.edit_message_text(f"❌ AI error: {'; '.join(errors)}\n\nPlease try again or edit manually.",
                                  reply_markup=InlineKeyboardMarkup(kb)); return MEMO_AI_WAIT

    ai_ru = context.user_data.get("memo_ai_ru", "")
    ai_en = context.user_data.get("memo_ai_en", "")
    if lang == "RU":
        ai_preview = (ai_ru or "")[:300]
        orig_preview = body_ru[:200]
    elif lang == "EN":
        ai_preview = (ai_en or "")[:300]
        orig_preview = body_en[:200]
    else:
        ai_preview = f"[RU]: {ai_ru[:150]}...\n[EN]: {ai_en[:150]}..."
        orig_preview = f"[RU]: {body_ru[:100]}...\n[EN]: {body_en[:100]}..."
    if len(ai_preview) > 300: ai_preview += "..."
    msg = (f"✨ AI Version:\n\"{ai_preview}\"\n\n"
           f"📝 Your Original:\n\"{orig_preview[:200]}{'...' if len(orig_preview)>200 else ''}\"\n\n"
           f"What would you like to do?")
    kb = [
        [InlineKeyboardButton("✅ Use AI version",          callback_data="memo_use_ai")],
        [InlineKeyboardButton("🔄 Try different style",     callback_data="memo_ai_improve")],
        [InlineKeyboardButton("💬 Give AI specific instructions", callback_data="memo_ai_instruct")],
        [InlineKeyboardButton("✍️ Edit AI version manually", callback_data="memo_manual_edit_ai")],
        [InlineKeyboardButton("↩️ Keep my original",        callback_data="memo_back_to_options")],
        [bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return MEMO_AI_WAIT


async def memo_use_ai(update, context):
    """Accept AI-improved text as the final body."""
    q = update.callback_query; await q.answer()
    lang = context.user_data.get("memo_lang", "EN")
    if lang in ("RU", "BOTH") and context.user_data.get("memo_ai_ru"):
        context.user_data["memo_body_ru"] = context.user_data.pop("memo_ai_ru")
    if lang in ("EN", "BOTH") and context.user_data.get("memo_ai_en"):
        context.user_data["memo_body_en"] = context.user_data.pop("memo_ai_en")
    return await _show_body_options(update, context, from_query=True)


async def memo_ai_instruct_prompt(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "💬 Type your instruction for the AI:\n\n"
        "(e.g. \"make it shorter\", \"more formal\", \"add specific numbers\", \"focus on cost savings\")"
    )
    return MEMO_AI_INSTR


async def memo_ai_instruction_received(update, context):
    instruction = update.message.text.strip()
    await update.message.reply_text("⏳ Applying your instruction...")
    from ai_writer import improve_with_instruction
    lang = context.user_data.get("memo_lang", "EN")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    errors = []
    if body_ru:
        result_ru, err = await improve_with_instruction(body_ru, instruction, lang="RU")
        if err: errors.append(f"RU: {err}")
        else: context.user_data["memo_ai_ru"] = result_ru
    if body_en:
        result_en, err = await improve_with_instruction(body_en, instruction, lang="EN")
        if err: errors.append(f"EN: {err}")
        else: context.user_data["memo_ai_en"] = result_en

    if errors:
        await update.message.reply_text(f"❌ AI error: {'; '.join(errors)}")
        return MEMO_AI_INSTR

    ai_ru = context.user_data.get("memo_ai_ru", "")
    ai_en = context.user_data.get("memo_ai_en", "")
    if lang == "RU": preview = (ai_ru or "")[:300]
    elif lang == "EN": preview = (ai_en or "")[:300]
    else: preview = f"[RU]: {ai_ru[:150]}...\n[EN]: {ai_en[:150]}..."
    kb = [
        [InlineKeyboardButton("✅ Use this version",         callback_data="memo_use_ai")],
        [InlineKeyboardButton("💬 Give another instruction", callback_data="memo_ai_instruct")],
        [InlineKeyboardButton("✍️ Edit manually",            callback_data="memo_manual_edit_ai")],
        [InlineKeyboardButton("↩️ Keep original",            callback_data="memo_back_to_options")],
        [bm()],
    ]
    await update.message.reply_text(
        f"✨ Result:\n\"{preview}{'...' if len(preview) >= 300 else ''}\"\n\nWhat would you like to do?",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return MEMO_AI_WAIT


async def memo_manual_edit(update, context):
    """Send current text for user to edit and resend."""
    q = update.callback_query; await q.answer()
    lang = context.user_data.get("memo_lang", "EN")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    if lang == "RU":
        await q.message.reply_text(f"Copy and edit, then send back:\n\n{body_ru}")
    elif lang == "EN":
        await q.message.reply_text(f"Copy and edit, then send back:\n\n{body_en}")
    else:
        await q.message.reply_text(f"[Russian text — copy and edit]\n\n{body_ru}")
        await q.message.reply_text(f"[English text — copy and edit]\n\n{body_en}")
        await q.message.reply_text("Send your edited Russian text first:")
        context.user_data["memo_body_stage"] = "ru"
        return MEMO_BODY
    context.user_data["memo_body_stage"] = "ru" if lang == "RU" else "en"
    return MEMO_BODY


async def memo_manual_edit_ai(update, context):
    """Send AI text for user to edit (use AI version as starting point)."""
    q = update.callback_query; await q.answer()
    lang = context.user_data.get("memo_lang", "EN")
    ai_ru = context.user_data.get("memo_ai_ru", context.user_data.get("memo_body_ru", ""))
    ai_en = context.user_data.get("memo_ai_en", context.user_data.get("memo_body_en", ""))
    # Temporarily set as current body so edit flow works
    if lang in ("RU", "BOTH"): context.user_data["memo_body_ru"] = ai_ru
    if lang in ("EN", "BOTH"): context.user_data["memo_body_en"] = ai_en
    if lang == "RU":
        await q.message.reply_text(f"Copy and edit, then send back:\n\n{ai_ru}")
        context.user_data["memo_body_stage"] = "ru"
    elif lang == "EN":
        await q.message.reply_text(f"Copy and edit, then send back:\n\n{ai_en}")
        context.user_data["memo_body_stage"] = "en"
    else:
        await q.message.reply_text(f"[Russian] Copy and edit:\n\n{ai_ru}")
        await q.message.reply_text(f"[English] Copy and edit:\n\n{ai_en}")
        await q.message.reply_text("Send your edited Russian text first:")
        context.user_data["memo_body_stage"] = "ru"
    return MEMO_BODY


async def memo_back_to_options(update, context):
    return await _show_body_options(update, context, from_query=True)


def _build_memo_data_from_row(r, dir_name):
    """Build memo_data dict from a Memo_Log sheet row."""
    ec = r[2] if len(r) > 2 else ""
    emp = _get_emp(ec)
    lang = r[5] if len(r) > 5 else "EN"
    body_text = r[8] if len(r) > 8 else ""
    body_ru, body_en = "", ""
    if "[RU]:" in body_text and "[EN]:" in body_text:
        parts = body_text.split("\n\n[EN]:")
        body_ru = parts[0].replace("[RU]: ", "").strip()
        body_en = parts[1].strip() if len(parts) > 1 else ""
    elif lang == "RU":
        body_ru = body_text
    else:
        body_en = body_text
    hr_ec = r[11] if len(r) > 11 else ""
    hr_emp = _get_emp(hr_ec) if hr_ec else {}
    hr_mgr_rows = [row for i, row in enumerate(get_sheet(TAB_USER).get_all_values())
                   if i > 0 and len(row) > 3 and row[3].strip() in ("HR_Manager", "Bot_Manager")]
    hr_mgr_ec  = hr_mgr_rows[0][0] if hr_mgr_rows else ""
    hr_mgr_emp = _get_emp(hr_mgr_ec) if hr_mgr_ec else {}
    return {
        "memo_id":          r[0] if r else "",
        "sz_number":        r[9]  if len(r) > 9  else "",
        "date":             r[1][:10] if len(r) > 1 else "",
        "emp_code":         ec,
        "emp_name":         emp.get("Full_Name", ec),
        "job_title":        emp.get("Job_Title", ""),
        "department":       emp.get("Department", ""),
        "language":         lang,
        "topic":            r[6] if len(r) > 6 else "",
        "body_ru":          body_ru,
        "body_en":          body_en,
        "director_name":    dir_name,
        "final_status":     r[20] if len(r) > 20 else "Draft",
        "submitter_name":   emp.get("Full_Name", ec),
        "submitter_date":   r[1][:10] if len(r) > 1 else "",
        "hr_staff_name":    hr_emp.get("Full_Name", "HR Staff"),
        "hr_staff_date":    r[13] if len(r) > 13 else "",
        "hr_manager_name":  hr_mgr_emp.get("Full_Name", ""),
        "hr_manager_date":  r[16] if len(r) > 16 else "",
        "director_date":    r[18] if len(r) > 18 else "",
        "_hr_mgr_ec":       hr_mgr_ec,
        "_hr_ec":           hr_ec,
    }


_CONFIRM_KB = [
    [InlineKeyboardButton("✅ Submit to HR", callback_data="memo_submit")],
    [InlineKeyboardButton("✍️ Edit text",   callback_data="memo_back_to_options")],
    [InlineKeyboardButton("❌ Cancel",       callback_data="menu_memos")],
]


async def memo_confirm_text(update, context):
    """Generate PDF preview and ask for final confirmation."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Generating preview PDF...")
    ec   = context.user_data.get("memo_ec")
    lang = context.user_data.get("memo_lang", "EN")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    topic   = context.user_data.get("memo_topic", "")
    emp  = _get_emp(ec)
    _, _, dir_name = _get_director()

    memo_data = {
        "memo_id": "(draft)",
        "sz_number": "",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "emp_code": ec,
        "emp_name": emp.get("Full_Name", ec),
        "job_title": emp.get("Job_Title", ""),
        "department": emp.get("Department", ""),
        "language": lang,
        "topic": topic,
        "topic_category": context.user_data.get("memo_category", "other"),
        "body_ru": body_ru,
        "body_en": body_en,
        "director_name": dir_name,
        "final_status": "Draft",
        "submitter_name": emp.get("Full_Name", ec),
        "submitter_date": datetime.now().strftime("%d/%m/%Y"),
    }
    try:
        from signature_handler import get_sig_bytes
        sub_sig_b, sub_sig_t = await get_sig_bytes(context.bot, ec)
        sigs = {"submitter": (sub_sig_b, sub_sig_t)}
        pdf_bytes = generate_memo_pdf(memo_data, sigs)
        drive_url = upload_to_drive(pdf_bytes, f"DRAFT_{ec}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf", "memo_drafts")
        if drive_url:
            kb_extra = list(_CONFIRM_KB) + [[InlineKeyboardButton("📄 View PDF", url=drive_url)]]
            await q.message.reply_text("📄 Memo preview ready:", reply_markup=InlineKeyboardMarkup(kb_extra))
        else:
            await q.message.reply_document(
                document=io.BytesIO(pdf_bytes),
                filename="MemoPreview.pdf",
                caption="📄 Here's your memo preview:"
            )
            await q.message.reply_text("What would you like to do?", reply_markup=InlineKeyboardMarkup(_CONFIRM_KB))
    except Exception as e:
        await q.message.reply_text(f"⚠️ Could not generate PDF preview: {e}")
        await q.message.reply_text("What would you like to do?", reply_markup=InlineKeyboardMarkup(_CONFIRM_KB))
    return MEMO_CONFIRM


async def memo_submit(update, context):
    """Submit the memo: write to Memo_Log, generate submitted PDF, notify HR."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Submitting memo...")
    ec     = context.user_data.get("memo_ec")
    lang   = context.user_data.get("memo_lang", "EN")
    topic  = context.user_data.get("memo_topic", "")
    cat    = context.user_data.get("memo_category", "other")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    emp    = _get_emp(ec)
    name   = emp.get("Full_Name", ec)
    memo_id = _next_memo_id()
    context.user_data["memo_id"] = memo_id
    try:
        _append_memo_row(memo_id, ec, lang, topic, cat, body_ru, body_en)

        # Generate submitted PDF with submitter signature → save to col 22
        sub_url = None
        try:
            from signature_handler import get_sig_bytes
            _, _, dir_name = _get_director()
            submitted_data = {
                "memo_id": memo_id, "sz_number": "",
                "date": datetime.now().strftime("%d/%m/%Y"),
                "emp_code": ec, "emp_name": emp.get("Full_Name", ec),
                "job_title": emp.get("Job_Title", ""), "department": emp.get("Department", ""),
                "language": lang, "topic": topic, "topic_category": cat,
                "body_ru": body_ru, "body_en": body_en,
                "director_name": dir_name, "final_status": "Submitted",
                "submitter_name": emp.get("Full_Name", ec),
                "submitter_date": datetime.now().strftime("%d/%m/%Y"),
            }
            sub_sb, sub_st = await get_sig_bytes(context.bot, ec)
            pdf_bytes = generate_memo_pdf(submitted_data, {"submitter": (sub_sb, sub_st)})
            sub_url = upload_to_drive(pdf_bytes, f"{memo_id}_submitted.pdf", "memo_drafts")
            if sub_url:
                rn2, _ = _find_memo(memo_id)
                if rn2:
                    _update_memo_cell(rn2, 22, sub_url)   # PDF_Preview_Link col 22
        except Exception:
            pass

        # Notify HR Staff and HR Manager
        for hr_ec in _get_hr_ecs():
            create_notification(hr_ec, "memo_submitted",
                                f"New Memo from {name}",
                                f"New memo submitted: {topic} ({memo_id})",
                                related_id=memo_id)

        conf_kb = [[bb(), bm()]]
        if sub_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Submitted Memo", url=sub_url)])
        await q.edit_message_text(
            f"✅ Memo submitted!\n\n{memo_id}\nTopic: {topic}\n\nHR will review and register it shortly.",
            reply_markup=InlineKeyboardMarkup(conf_kb)
        )
    except Exception as e:
        await q.edit_message_text(f"❌ Error submitting: {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))
    return ConversationHandler.END


async def memo_cancel(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))
    else:
        await update.message.reply_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))
    return ConversationHandler.END


# ── My Memos ───────────────────────────────────────────────────────────────────

async def my_memos_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec_by_tid(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        my_rows = []
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) > 2 and str(r[2]).strip() == str(ec):
                my_rows.append(r)
        my_rows.reverse()
        if not my_rows:
            await q.edit_message_text("📋 My Memos\n\nYou have no submitted memos.",
                                      reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
        kb = []
        for r in my_rows[:15]:
            mid = r[0]; topic = r[6] if len(r) > 6 else "?"
            status = r[20] if len(r) > 20 else "?"
            date = r[1][:10] if len(r) > 1 else ""
            emoji = {"Draft": "📝", "Submitted": "📤", "Registered": "📋",
                     "HR_Approved": "✅", "Director_Approved": "🎉",
                     "Rejected": "❌", "Revision_Requested": "🔄"}.get(status, "📄")
            label = f"{emoji} {topic[:30]} ({date})"
            kb.append([InlineKeyboardButton(label, callback_data=f"memo_view_{mid}")])
        kb.append([bb(), bm()])
        await q.edit_message_text(f"📋 My Memos ({len(my_rows)} total):",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


async def memo_view_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("memo_view_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Memo not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ My Memos", callback_data="menu_my_memos"), bm()]])); return
    topic  = r[6] if len(r) > 6 else "?"
    status = r[20] if len(r) > 20 else "?"
    date   = r[1][:10] if len(r) > 1 else ""
    sz     = r[9] if len(r) > 9 else ""
    notes  = r[14] if len(r) > 14 else ""
    drive_link = r[23] if len(r) > 23 else ""
    msg = (f"📄 Memo: {memo_id}\n"
           f"Topic: {topic}\n"
           f"Date: {date}\n"
           f"Status: {status}")
    if sz: msg += f"\nRegistration: {sz}"
    if notes and status == "Revision_Requested": msg += f"\n\n📝 HR Notes:\n{notes}"
    kb_rows = []
    if drive_link and drive_link.startswith("http"):
        kb_rows.append([InlineKeyboardButton("📄 View PDF", url=drive_link)])
    if status == "Revision_Requested":
        kb_rows.append([InlineKeyboardButton("✏️ Edit and Resubmit", callback_data=f"memo_resubmit_{memo_id}")])
    kb_rows.append([InlineKeyboardButton("↩️ My Memos", callback_data="menu_my_memos"), bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb_rows))


# ── Resubmit after revision request ───────────────────────────────────────────

async def memo_resubmit_start(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("memo_resubmit_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Memo not found.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))
        return ConversationHandler.END
    ec, role = _find_ec_by_tid(str(q.from_user.id))
    context.user_data["memo_ec"] = ec
    context.user_data["memo_id"] = memo_id
    context.user_data["memo_rn"] = rn
    context.user_data["memo_lang"] = r[5] if len(r) > 5 else "EN"
    context.user_data["memo_topic"] = r[6] if len(r) > 6 else ""
    context.user_data["memo_category"] = r[7] if len(r) > 7 else "other"
    body_text = r[8] if len(r) > 8 else ""
    # Parse RU/EN from combined body
    if "[RU]:" in body_text and "[EN]:" in body_text:
        parts = body_text.split("\n\n[EN]:")
        context.user_data["memo_body_ru"] = parts[0].replace("[RU]: ", "").strip()
        context.user_data["memo_body_en"] = parts[1].strip() if len(parts) > 1 else ""
    else:
        context.user_data["memo_body_ru"] = body_text
        context.user_data["memo_body_en"] = body_text
    await q.edit_message_text(
        f"✏️ Edit and Resubmit\n\nMemo: {memo_id}\n\nYour current body text has been loaded.\n\n"
        "Enter your updated body text:"
    )
    context.user_data["memo_body_stage"] = "ru" if context.user_data["memo_lang"] in ("RU", "BOTH") else "en"
    return MEMO_RESUBMIT


async def memo_resubmit_received(update, context):
    text = update.message.text.strip()
    stage = context.user_data.get("memo_body_stage", "en")
    lang  = context.user_data.get("memo_lang", "EN")
    if stage == "ru":
        context.user_data["memo_body_ru"] = text
        if lang == "BOTH":
            context.user_data["memo_body_stage"] = "en"
            await update.message.reply_text("🇬🇧 Now enter the ENGLISH text:")
            return MEMO_RESUBMIT
    else:
        context.user_data["memo_body_en"] = text

    memo_id = context.user_data.get("memo_id")
    rn      = context.user_data.get("memo_rn")
    body_ru = context.user_data.get("memo_body_ru", "")
    body_en = context.user_data.get("memo_body_en", "")
    body_combined = f"[RU]: {body_ru}\n\n[EN]: {body_en}" if body_ru and body_en else (body_ru or body_en)
    try:
        _update_memo_cell(rn, 9, body_combined)
        _update_memo_cell(rn, 21, "Submitted")
        _update_memo_cell(rn, 13, "")  # Clear HR_Staff_Status
        await update.message.reply_text(
            f"✅ Memo {memo_id} updated and resubmitted.\n\nHR will review shortly.",
            reply_markup=InlineKeyboardMarkup([[bb(), bm()]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END


# ── Memo menu ──────────────────────────────────────────────────────────────────

async def memo_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    _, role = _find_ec_by_tid(str(q.from_user.id))
    is_hr = role in HR_REVIEW_ROLES
    is_hr_mgr = role in HR_MGR_ROLES
    is_dir = role in DIR_ROLES
    kb = [
        [InlineKeyboardButton("📝 New Memo",    callback_data="memo_new")],
        [InlineKeyboardButton("📋 My Memos",    callback_data="menu_my_memos")],
    ]
    if is_hr:
        kb.append([InlineKeyboardButton("📥 Pending Review (HR)", callback_data="memo_pending_hr")])
    if is_hr_mgr:
        kb.append([InlineKeyboardButton("📥 Pending Review (HR Mgr)", callback_data="memo_pending_hr_mgr")])
        kb.append([InlineKeyboardButton("📋 All Memos",              callback_data="memo_all")])
    if is_dir:
        kb.append([InlineKeyboardButton("📝 Memo Decisions", callback_data="memo_pending_dir")])
    kb.append([InlineKeyboardButton("📂 Memo Archive",       callback_data="memo_archive")])
    kb.append([bm()])
    await q.edit_message_text("📝 Memos", reply_markup=InlineKeyboardMarkup(kb))


# ── HR Pending Review ──────────────────────────────────────────────────────────

async def memo_pending_hr_handler(update, context):
    q = update.callback_query; await q.answer()
    _, role = _find_ec_by_tid(str(q.from_user.id))
    if role not in HR_REVIEW_ROLES:
        await q.edit_message_text("No permission.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        pending = []
        for i, r in enumerate(rows):
            if i == 0: continue
            status = r[20] if len(r) > 20 else ""
            if status in ("Submitted", "Revision_Requested"):
                pending.append(r)
        if not pending:
            await q.edit_message_text("✅ No memos pending HR review.",
                                      reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
        kb = []
        for r in pending[:20]:
            mid   = r[0]; topic = r[6] if len(r) > 6 else "?"
            ec    = r[2] if len(r) > 2 else "?"
            date  = r[1][:10] if len(r) > 1 else ""
            status = r[20] if len(r) > 20 else "?"
            emoji = "📤" if status == "Submitted" else "🔄"
            label = f"{emoji} {topic[:30]} — {ec} ({date})"
            kb.append([InlineKeyboardButton(label, callback_data=f"hr_memo_view_{mid}")])
        kb.append([bb(), bm()])
        await q.edit_message_text(f"📥 Pending HR Review — {len(pending)} memos:",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


async def hr_memo_view_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_memo_view_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]])); return
    topic  = r[6] if len(r) > 6 else "?"
    body   = r[8] if len(r) > 8 else ""
    ec     = r[2] if len(r) > 2 else "?"
    emp    = _get_emp(ec)
    name   = emp.get("Full_Name", ec)
    date   = r[1][:10] if len(r) > 1 else ""
    status = r[20] if len(r) > 20 else "?"

    sub_link = r[21] if len(r) > 21 else ""   # col 22 = PDF_Preview_Link (submitted)
    msg = (f"📄 Memo {memo_id}\n"
           f"From: {name} ({ec})\nDate: {date}\n"
           f"Topic: {topic}\nStatus: {status}\n\n"
           f"Body:\n{body[:800]}{'...' if len(body) > 800 else ''}")
    kb = []
    if sub_link:
        kb.append([InlineKeyboardButton("📄 View Submitted Memo", url=sub_link)])
    kb += [
        [InlineKeyboardButton("✅ Register & Forward", callback_data=f"hr_memo_register_{memo_id}")],
        [InlineKeyboardButton("📝 Request Changes",    callback_data=f"hr_memo_changes_{memo_id}")],
        [InlineKeyboardButton("❌ Reject",              callback_data=f"hr_memo_reject_{memo_id}")],
        [InlineKeyboardButton("↩️ Back",               callback_data="memo_pending_hr"), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def hr_memo_register_handler(update, context):
    """Register the memo: assign SZ number, add HR signature, forward to HR_Manager."""
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_memo_register_", "")
    ec_hr, role = _find_ec_by_tid(str(q.from_user.id))
    await q.edit_message_text("⏳ Registering memo...")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]])); return
    sz_num = _next_sz_number()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        _update_memo_cell(rn, 10, sz_num)       # Registration_Number
        _update_memo_cell(rn, 11, now)          # Registration_Date
        _update_memo_cell(rn, 12, str(ec_hr))   # HR_Staff_Code
        _update_memo_cell(rn, 13, "Registered") # HR_Staff_Status
        _update_memo_cell(rn, 14, now)          # HR_Staff_Date
        _update_memo_cell(rn, 21, "Registered") # Final_Status

        # Generate registered PDF (submitter + HR Staff sigs) → save to col 23
        reg_url = None
        try:
            from signature_handler import get_sig_bytes
            _, _, dir_name = _get_director()
            rn2, r2 = _find_memo(memo_id)
            memo_data = _build_memo_data_from_row(r2, dir_name)
            sub_sb, sub_st = await get_sig_bytes(context.bot, memo_data["emp_code"])
            hr_sb,  hr_st  = await get_sig_bytes(context.bot, ec_hr)
            pdf_bytes = generate_memo_pdf(memo_data, {
                "submitter": (sub_sb, sub_st),
                "hr_staff":  (hr_sb,  hr_st),
            })
            sz_clean = sz_num.replace("/", "-").replace(" ", "_")
            reg_url = upload_to_drive(pdf_bytes, f"{sz_clean}_registered.pdf", "memo_drafts")
            if reg_url:
                _update_memo_cell(rn, 23, reg_url)   # PDF_Final_Link col 23
        except Exception:
            pass

        # Notify submitter
        submitter_ec = r[2] if len(r) > 2 else None
        if submitter_ec:
            create_notification(submitter_ec, "memo_registered",
                                f"Memo Registered: {sz_num}",
                                f"Your memo '{r[6] if len(r)>6 else memo_id}' has been registered as {sz_num}.",
                                related_id=memo_id)

        # Notify HR Managers
        for hr_mgr_ec in [row[0] for i, row in enumerate(get_sheet(TAB_USER).get_all_values())
                          if i > 0 and len(row) > 3 and row[3].strip() in ("HR_Manager", "Bot_Manager")]:
            create_notification(hr_mgr_ec, "memo_for_review",
                                f"Memo for Review: {sz_num}",
                                f"Registered memo pending your review: {sz_num}",
                                related_id=memo_id)

        conf_kb = [[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]]
        if reg_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Registered PDF", url=reg_url)])
        await q.edit_message_text(
            f"✅ Memo registered as {sz_num}\n\nForwarded to HR Manager for review.",
            reply_markup=InlineKeyboardMarkup(conf_kb))
    except Exception as e:
        await q.edit_message_text(f"❌ Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]]))


async def hr_memo_changes_start(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_memo_changes_", "")
    context.user_data["hr_memo_id"] = memo_id
    await q.edit_message_text(f"📝 Request Changes — Memo {memo_id}\n\nType your message to the submitter:")
    return HR_MEMO_CHG


async def hr_memo_changes_received(update, context):
    note = update.message.text.strip()
    memo_id = context.user_data.get("hr_memo_id")
    rn, r = _find_memo(memo_id)
    if not r:
        await update.message.reply_text("Memo not found."); return ConversationHandler.END
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 15, note)     # HR_Staff_Notes
    _update_memo_cell(rn, 13, "Revision_Requested")
    _update_memo_cell(rn, 21, "Revision_Requested")
    submitter_ec = r[2] if len(r) > 2 else None
    if submitter_ec:
        create_notification(submitter_ec, "memo_revision",
                            "HR Requested Changes on Your Memo",
                            f"HR requested changes on memo {memo_id}: {note}",
                            related_id=memo_id)
    await update.message.reply_text(
        f"✅ Change request sent for {memo_id}.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]]))
    return ConversationHandler.END


async def hr_memo_reject_start(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_memo_reject_", "")
    context.user_data["hr_memo_id"] = memo_id
    await q.edit_message_text(f"❌ Reject Memo {memo_id}\n\nType the rejection reason:")
    return HR_MEMO_REJ


async def hr_memo_reject_received(update, context):
    reason  = update.message.text.strip()
    memo_id = context.user_data.get("hr_memo_id")
    rn, r   = _find_memo(memo_id)
    if not r:
        await update.message.reply_text("Memo not found."); return ConversationHandler.END
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 13, "Rejected")
    _update_memo_cell(rn, 14, now)
    _update_memo_cell(rn, 15, reason)
    _update_memo_cell(rn, 21, "Rejected")
    submitter_ec = r[2] if len(r) > 2 else None
    if submitter_ec:
        create_notification(submitter_ec, "memo_rejected",
                            f"Memo {memo_id} Rejected by HR",
                            f"Your memo has been rejected. Reason: {reason}",
                            related_id=memo_id)
    await update.message.reply_text(
        f"❌ Memo {memo_id} rejected.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr"), bm()]]))
    return ConversationHandler.END


async def hr_conv_cancel(update, context):
    if update.message:
        await update.message.reply_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


# ── HR Manager Review ──────────────────────────────────────────────────────────

async def memo_pending_hr_mgr_handler(update, context):
    q = update.callback_query; await q.answer()
    _, role = _find_ec_by_tid(str(q.from_user.id))
    if role not in HR_MGR_ROLES:
        await q.edit_message_text("No permission.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        pending = [r for i, r in enumerate(rows) if i > 0 and len(r) > 20 and r[20] == "Registered"]
        if not pending:
            await q.edit_message_text("✅ No memos awaiting HR Manager review.",
                                      reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
        kb = []
        for r in pending[:20]:
            mid = r[0]; sz = r[9] if len(r) > 9 else "?"
            topic = r[6] if len(r) > 6 else "?"
            kb.append([InlineKeyboardButton(f"📋 {sz} — {topic[:30]}", callback_data=f"hr_mgr_view_{mid}")])
        kb.append([bb(), bm()])
        await q.edit_message_text(f"📥 HR Manager Review — {len(pending)} memos:",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


async def hr_mgr_view_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_mgr_view_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr_mgr"), bm()]])); return
    sz       = r[9]  if len(r) > 9  else "?"
    topic    = r[6]  if len(r) > 6  else "?"
    ec       = r[2]  if len(r) > 2  else "?"
    emp      = _get_emp(ec)
    name     = emp.get("Full_Name", ec)
    body     = r[8]  if len(r) > 8  else ""
    reg_link = r[22] if len(r) > 22 else ""   # col 23 = PDF_Final_Link (registered)
    msg = (f"📋 {sz}\nFrom: {name} ({ec})\nTopic: {topic}\n\n"
           f"Body:\n{body[:600]}{'...' if len(body) > 600 else ''}")
    kb = []
    if reg_link:
        kb.append([InlineKeyboardButton("📄 View Registered PDF", url=reg_link)])
    kb += [
        [InlineKeyboardButton("✅ Approve & Forward to Director", callback_data=f"hr_mgr_approve_{memo_id}")],
        [InlineKeyboardButton("📝 Send Back to HR",               callback_data=f"hr_mgr_sendback_{memo_id}")],
        [InlineKeyboardButton("❌ Reject",                         callback_data=f"hr_mgr_reject_{memo_id}")],
        [InlineKeyboardButton("↩️ Back",                          callback_data="memo_pending_hr_mgr"), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def hr_mgr_approve_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_mgr_approve_", "")
    ec_hr, _ = _find_ec_by_tid(str(q.from_user.id))
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr_mgr"), bm()]])); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 16, "Approved")    # HR_Manager_Status
    _update_memo_cell(rn, 17, now)           # HR_Manager_Date
    _update_memo_cell(rn, 21, "HR_Approved") # Final_Status

    # Generate HR Manager signed PDF (submitter + HR Staff + HR Manager sigs) → save to col 24
    mgr_url = None
    try:
        from signature_handler import get_sig_bytes
        _, _, dir_name = _get_director()
        rn2, r2 = _find_memo(memo_id)
        memo_data = _build_memo_data_from_row(r2, dir_name)
        memo_data["final_status"] = "HR_Approved"
        sub_sb,    sub_st    = await get_sig_bytes(context.bot, memo_data["emp_code"])
        hr_sb,     hr_st     = (await get_sig_bytes(context.bot, memo_data["_hr_ec"]))     if memo_data["_hr_ec"]     else (None, None)
        hr_mgr_sb, hr_mgr_st = await get_sig_bytes(context.bot, ec_hr)
        pdf_bytes = generate_memo_pdf(memo_data, {
            "submitter":  (sub_sb,    sub_st),
            "hr_staff":   (hr_sb,     hr_st),
            "hr_manager": (hr_mgr_sb, hr_mgr_st),
        })
        sz = r[9] if len(r) > 9 else memo_id
        sz_clean = str(sz).replace("/", "-").replace(" ", "_")
        mgr_url = upload_to_drive(pdf_bytes, f"{sz_clean}_hr_manager_approved.pdf", "memo_drafts")
        if mgr_url:
            _update_memo_cell(rn, 24, mgr_url)   # Drive_Link col 24 (intermediate; overwritten at final)
    except Exception:
        pass

    # Notify Director
    dir_ec, _, _ = _get_director()
    if dir_ec:
        sz = r[9] if len(r) > 9 else memo_id
        create_notification(dir_ec, "memo_for_director",
                            f"Memo Decision Required: {sz}",
                            f"Memo {sz} awaiting your approval.",
                            related_id=memo_id)

    conf_kb = [[InlineKeyboardButton("↩️ Back", callback_data="memo_pending_hr_mgr"), bm()]]
    if mgr_url:
        conf_kb.insert(0, [InlineKeyboardButton("📄 View Approved PDF", url=mgr_url)])
    await q.edit_message_text(
        f"✅ Approved. Forwarded to Director.",
        reply_markup=InlineKeyboardMarkup(conf_kb))


async def hr_mgr_sendback_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_mgr_sendback_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr_mgr"), bm()]])); return
    _update_memo_cell(rn, 16, "Sent_Back")
    _update_memo_cell(rn, 21, "Submitted")   # back to Submitted for HR
    await q.edit_message_text(
        f"✅ Memo sent back to HR for revision.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="memo_pending_hr_mgr"), bm()]]))


async def hr_mgr_reject_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("hr_mgr_reject_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Pending", callback_data="memo_pending_hr_mgr"), bm()]])); return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 16, "Rejected")
    _update_memo_cell(rn, 17, now)
    _update_memo_cell(rn, 21, "Rejected")
    submitter_ec = r[2] if len(r) > 2 else None
    if submitter_ec:
        create_notification(submitter_ec, "memo_rejected",
                            f"Memo {r[9] if len(r)>9 else memo_id} Rejected",
                            "Your memo was rejected by HR Manager.",
                            related_id=memo_id)
    await q.edit_message_text(
        f"❌ Memo rejected.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="memo_pending_hr_mgr"), bm()]]))


# ── Director Review ────────────────────────────────────────────────────────────

async def memo_pending_dir_handler(update, context):
    q = update.callback_query; await q.answer()
    _, role = _find_ec_by_tid(str(q.from_user.id))
    if role not in DIR_ROLES:
        await q.edit_message_text("No permission.", reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        pending = [r for i, r in enumerate(rows) if i > 0 and len(r) > 20 and r[20] == "HR_Approved"]
        if not pending:
            await q.edit_message_text("✅ No memos awaiting Director decision.",
                                      reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
        kb = []
        for r in pending[:20]:
            mid = r[0]; sz = r[9] if len(r) > 9 else "?"
            topic = r[6] if len(r) > 6 else "?"
            kb.append([InlineKeyboardButton(f"📄 {sz} — {topic[:30]}", callback_data=f"dir_memo_view_{mid}")])
        kb.append([bb(), bm()])
        await q.edit_message_text(f"📝 Memo Decisions — {len(pending)} pending:",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


async def dir_memo_view_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("dir_memo_view_", "")
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Decisions", callback_data="memo_pending_dir"), bm()]])); return
    sz       = r[9]  if len(r) > 9  else "?"
    topic    = r[6]  if len(r) > 6  else "?"
    ec       = r[2]  if len(r) > 2  else "?"
    emp      = _get_emp(ec)
    name     = emp.get("Full_Name", ec)
    body     = r[8]  if len(r) > 8  else ""
    mgr_link = r[23] if len(r) > 23 else ""   # col 24 = Drive_Link (HR Manager approved PDF)
    msg = (f"📄 {sz}\nFrom: {name} ({ec})\nTopic: {topic}\n\n"
           f"Body:\n{body[:600]}{'...' if len(body) > 600 else ''}")
    kb = []
    if mgr_link:
        kb.append([InlineKeyboardButton("📄 View HR Manager PDF", url=mgr_link)])
    kb += [
        [InlineKeyboardButton("✅ Approve",  callback_data=f"dir_memo_approve_{memo_id}")],
        [InlineKeyboardButton("❌ Reject",   callback_data=f"dir_memo_reject_{memo_id}")],
        [InlineKeyboardButton("↩️ Back",    callback_data="memo_pending_dir"), bm()],
    ]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def dir_memo_approve_handler(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("dir_memo_approve_", "")
    ec_dir, _ = _find_ec_by_tid(str(q.from_user.id))
    rn, r = _find_memo(memo_id)
    if not r:
        await q.edit_message_text("Not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Decisions", callback_data="memo_pending_dir"), bm()]])); return
    await q.edit_message_text("⏳ Approving and generating final PDF...")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 18, "Approved")     # Director_Status
    _update_memo_cell(rn, 19, now)            # Director_Date
    _update_memo_cell(rn, 21, "Director_Approved")

    # Build PDF with all signatures
    ec      = r[2] if len(r) > 2 else ""
    emp     = _get_emp(ec)
    hr_ec   = r[11] if len(r) > 11 else ""
    dir_ec, _, dir_name = _get_director()
    hr_emp  = _get_emp(hr_ec) if hr_ec else {}
    hr_mgr_rows = [row for i, row in enumerate(get_sheet(TAB_USER).get_all_values())
                   if i > 0 and len(row) > 3 and row[3].strip() in ("HR_Manager", "Bot_Manager")]
    hr_mgr_ec = hr_mgr_rows[0][0] if hr_mgr_rows else ""
    hr_mgr_emp = _get_emp(hr_mgr_ec) if hr_mgr_ec else {}

    memo_data = {
        "memo_id": memo_id,
        "sz_number": r[9] if len(r) > 9 else "",
        "date": r[1][:10] if len(r) > 1 else now[:10],
        "emp_code": ec,
        "emp_name": emp.get("Full_Name", ec),
        "job_title": emp.get("Job_Title", ""),
        "department": emp.get("Department", ""),
        "language": r[5] if len(r) > 5 else "EN",
        "topic": r[6] if len(r) > 6 else "",
        "topic_category": r[7] if len(r) > 7 else "",
        "body_ru": "", "body_en": "",
        "director_name": dir_name,
        "final_status": "Director_Approved",
        "submitter_name": emp.get("Full_Name", ec),
        "submitter_date": r[1][:10] if len(r) > 1 else "",
        "hr_staff_name": hr_emp.get("Full_Name", "HR Staff"),
        "hr_staff_date": r[13] if len(r) > 13 else "",
        "hr_manager_name": hr_mgr_emp.get("Full_Name", ""),
        "hr_manager_date": r[16] if len(r) > 16 else "",
        "director_date": now,
    }
    # Parse body
    body_text = r[8] if len(r) > 8 else ""
    if "[RU]:" in body_text and "[EN]:" in body_text:
        parts = body_text.split("\n\n[EN]:")
        memo_data["body_ru"] = parts[0].replace("[RU]: ", "").strip()
        memo_data["body_en"] = parts[1].strip() if len(parts) > 1 else ""
    elif memo_data["language"] == "RU":
        memo_data["body_ru"] = body_text
    else:
        memo_data["body_en"] = body_text

    try:
        from signature_handler import get_sig_bytes
        bot = context.bot
        sub_sb, sub_st = await get_sig_bytes(bot, ec)
        hr_sb, hr_st = (await get_sig_bytes(bot, hr_ec)) if hr_ec else (None, None)
        hr_mgr_sb, hr_mgr_st = (await get_sig_bytes(bot, hr_mgr_ec)) if hr_mgr_ec else (None, None)
        dir_sb, dir_st = (await get_sig_bytes(bot, dir_ec)) if dir_ec else (None, None)
        sigs = {
            "submitter": (sub_sb, sub_st),
            "hr_staff": (hr_sb, hr_st),
            "hr_manager": (hr_mgr_sb, hr_mgr_st),
            "director": (dir_sb, dir_st),
        }
        pdf_bytes = generate_memo_pdf(memo_data, sigs)

        # Upload final PDF to approved folder
        sz_num = memo_data.get("sz_number", memo_id).replace("/", "-").replace(" ", "_")
        from drive_utils import upload_and_archive
        drive_url = upload_and_archive(pdf_bytes, f"{sz_num}_APPROVED.pdf", "memo_approved",
                                       emp_code=ec, emp_name=memo_data.get("requester_name", ""))
        if drive_url:
            _update_memo_cell(rn, 24, drive_url)   # Drive_Link col

        # Send final PDF link to submitter
        submitter_tid = _get_tid_by_ec(ec)
        if submitter_tid:
            try:
                if drive_url:
                    await bot.send_message(
                        chat_id=submitter_tid,
                        text=f"✅ Your memo {memo_data['sz_number']} has been approved by the Director.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View Final PDF", url=drive_url)]]))
                else:
                    await bot.send_message(
                        chat_id=submitter_tid,
                        text=f"✅ Your memo {memo_data['sz_number']} has been approved by the Director.")
            except Exception:
                pass

        # Notification to submitter
        create_notification(ec, "memo_approved",
                            f"Memo {memo_data['sz_number']} Approved by Director",
                            f"Your memo has been approved. PDF attached.",
                            related_id=memo_id)

        conf_kb = [[InlineKeyboardButton("↩️ Back", callback_data="memo_pending_dir"), bm()]]
        if drive_url:
            conf_kb.insert(0, [InlineKeyboardButton("📄 View Final PDF", url=drive_url)])
        await q.edit_message_text(
            f"✅ Memo {memo_data['sz_number']} approved.\nFinal PDF sent to submitter.",
            reply_markup=InlineKeyboardMarkup(conf_kb))
    except Exception as e:
        await q.edit_message_text(f"❌ Error generating final PDF: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Decisions", callback_data="memo_pending_dir"), bm()]]))


async def dir_memo_reject_start(update, context):
    q = update.callback_query; await q.answer()
    memo_id = q.data.replace("dir_memo_reject_", "")
    context.user_data["dir_memo_id"] = memo_id
    await q.edit_message_text(f"❌ Reject Memo {memo_id}\n\nType the rejection reason:")
    return DIR_MEMO_REJ


async def dir_memo_reject_received(update, context):
    reason  = update.message.text.strip()
    memo_id = context.user_data.get("dir_memo_id")
    rn, r   = _find_memo(memo_id)
    if not r:
        await update.message.reply_text("Memo not found."); return ConversationHandler.END
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    _update_memo_cell(rn, 18, "Rejected")
    _update_memo_cell(rn, 19, now)
    _update_memo_cell(rn, 20, reason)       # Director_Notes
    _update_memo_cell(rn, 21, "Rejected")
    submitter_ec = r[2] if len(r) > 2 else None
    sz = r[9] if len(r) > 9 else memo_id
    if submitter_ec:
        create_notification(submitter_ec, "memo_rejected",
                            f"Memo {sz} Rejected by Director",
                            f"Your memo was rejected by the Director. Reason: {reason}",
                            related_id=memo_id)
    await update.message.reply_text(
        f"❌ Memo {sz} rejected.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="memo_pending_dir"), bm()]]))
    return ConversationHandler.END


async def dir_conv_cancel(update, context):
    if update.message:
        await update.message.reply_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


# ── Memo Archive ───────────────────────────────────────────────────────────────

async def memo_archive_handler(update, context):
    q = update.callback_query; await q.answer()
    ec, role = _find_ec_by_tid(str(q.from_user.id))
    is_admin = role in {"Bot_Manager", "Director", "HR_Manager"}
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        # Collect distinct months
        months = {}
        for i, r in enumerate(rows):
            if i == 0 or not r: continue
            if not is_admin and str(r[2]).strip() != str(ec): continue
            if len(r) > 20 and r[20] not in ("Director_Approved", "Rejected"): continue
            if len(r) > 1 and r[1]:
                try:
                    dt = datetime.strptime(r[1][:10], "%d/%m/%Y")
                    key = dt.strftime("%Y-%m")
                    months[key] = dt.strftime("%B %Y")
                except Exception:
                    pass
        if not months:
            await q.edit_message_text("📂 Memo Archive\n\nNo archived memos.",
                                      reply_markup=InlineKeyboardMarkup([[bb(), bm()]])); return
        kb = []
        for key in sorted(months.keys(), reverse=True)[:12]:
            kb.append([InlineKeyboardButton(f"📅 {months[key]}", callback_data=f"memo_arch_month_{key}")])
        kb.append([bb(), bm()])
        await q.edit_message_text("📂 Memo Archive — Select Month:", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


async def memo_archive_month_handler(update, context):
    q = update.callback_query; await q.answer()
    month_key = q.data.replace("memo_arch_month_", "")
    ec, role = _find_ec_by_tid(str(q.from_user.id))
    is_admin = role in {"Bot_Manager", "Director", "HR_Manager"}
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        month_rows = []
        for i, r in enumerate(rows):
            if i == 0 or not r: continue
            if not is_admin and str(r[2]).strip() != str(ec): continue
            if len(r) > 1 and r[1]:
                try:
                    dt = datetime.strptime(r[1][:10], "%d/%m/%Y")
                    if dt.strftime("%Y-%m") == month_key:
                        month_rows.append(r)
                except Exception:
                    pass
        if not month_rows:
            await q.edit_message_text("No memos in this month.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Archive", callback_data="memo_archive"), bm()]])); return
        kb = []
        for r in month_rows[:20]:
            mid  = r[0]; sz = r[9] if len(r) > 9 else mid
            topic = r[6] if len(r) > 6 else "?"
            status = r[20] if len(r) > 20 else "?"
            ec_sub = r[2] if len(r) > 2 else "?"
            emoji = "✅" if status == "Director_Approved" else "❌"
            label = f"{emoji} {sz or mid} — {topic[:25]} ({ec_sub})"
            kb.append([InlineKeyboardButton(label, callback_data=f"memo_view_{mid}")])
        kb.append([InlineKeyboardButton("↩️ Archive", callback_data="memo_archive"), bm()])
        await q.edit_message_text(f"📂 {month_key} — {len(month_rows)} memos:",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Archive", callback_data="memo_archive"), bm()]]))


# ── All Memos (HR/Admin) ───────────────────────────────────────────────────────

async def memo_all_handler(update, context):
    q = update.callback_query; await q.answer()
    _, role = _find_ec_by_tid(str(q.from_user.id))
    if role not in HR_MGR_ROLES:
        await q.edit_message_text("No permission.", reply_markup=InlineKeyboardMarkup([[bm()]])); return
    try:
        rows = get_sheet(TAB_MEMO).get_all_values()
        all_rows = [r for i, r in enumerate(rows) if i > 0 and r]
        all_rows.reverse()
        kb = []
        for r in all_rows[:20]:
            mid = r[0]; sz = r[9] if len(r) > 9 else ""
            topic = r[6] if len(r) > 6 else "?"
            status = r[20] if len(r) > 20 else "?"
            ec = r[2] if len(r) > 2 else "?"
            status_emoji = {"Director_Approved": "✅", "Rejected": "❌",
                            "Submitted": "📤", "Registered": "📋",
                            "HR_Approved": "🔵"}.get(status, "📄")
            label = f"{status_emoji} {sz or mid} — {topic[:25]} ({ec})"
            kb.append([InlineKeyboardButton(label, callback_data=f"memo_view_{mid}")])
        kb.append([bb(), bm()])
        await q.edit_message_text(f"📋 All Memos ({len(all_rows)} total, showing latest 20):",
                                  reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bb(), bm()]]))


# ── Handler registration ───────────────────────────────────────────────────────

def get_memo_handlers():
    def mk(entry_pattern, entry_fn, states, cancel_fn):
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(entry_fn, pattern=entry_pattern)],
            states=states,
            fallbacks=[MessageHandler(filters.COMMAND, cancel_fn)],
            per_message=False,
        )

    # Main submission flow
    submission_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(memo_start, pattern="^memo_new$")],
        states={
            MEMO_LANG: [
                CallbackQueryHandler(memo_lang_chosen, pattern="^mlang_"),
            ],
            MEMO_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, memo_topic_received),
            ],
            MEMO_CATEGORY: [
                CallbackQueryHandler(memo_category_chosen, pattern="^mcat_"),
            ],
            MEMO_BODY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, memo_body_received),
            ],
            MEMO_AI_WAIT: [
                CallbackQueryHandler(memo_ai_improve,        pattern="^memo_ai_improve$"),
                CallbackQueryHandler(memo_use_ai,            pattern="^memo_use_ai$"),
                CallbackQueryHandler(memo_ai_instruct_prompt, pattern="^memo_ai_instruct$"),
                CallbackQueryHandler(memo_manual_edit,       pattern="^memo_manual_edit$"),
                CallbackQueryHandler(memo_manual_edit_ai,    pattern="^memo_manual_edit_ai$"),
                CallbackQueryHandler(memo_back_to_options,   pattern="^memo_back_to_options$"),
                CallbackQueryHandler(memo_confirm_text,      pattern="^memo_confirm_text$"),
            ],
            MEMO_AI_INSTR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, memo_ai_instruction_received),
                CallbackQueryHandler(memo_ai_instruct_prompt, pattern="^memo_ai_instruct$"),
                CallbackQueryHandler(memo_use_ai,            pattern="^memo_use_ai$"),
                CallbackQueryHandler(memo_manual_edit_ai,    pattern="^memo_manual_edit_ai$"),
                CallbackQueryHandler(memo_back_to_options,   pattern="^memo_back_to_options$"),
            ],
            MEMO_CONFIRM: [
                CallbackQueryHandler(memo_submit,          pattern="^memo_submit$"),
                CallbackQueryHandler(memo_back_to_options, pattern="^memo_back_to_options$"),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, memo_cancel),
            CallbackQueryHandler(memo_cancel, pattern="^menu_memos$"),
        ],
        per_message=False,
    )

    # HR changes request
    hr_changes_conv = mk(
        "^hr_memo_changes_",
        hr_memo_changes_start,
        {HR_MEMO_CHG: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_memo_changes_received)]},
        hr_conv_cancel,
    )

    # HR rejection
    hr_reject_conv = mk(
        "^hr_memo_reject_",
        hr_memo_reject_start,
        {HR_MEMO_REJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, hr_memo_reject_received)]},
        hr_conv_cancel,
    )

    # Director rejection
    dir_reject_conv = mk(
        "^dir_memo_reject_",
        dir_memo_reject_start,
        {DIR_MEMO_REJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, dir_memo_reject_received)]},
        dir_conv_cancel,
    )

    # Resubmit
    resubmit_conv = mk(
        "^memo_resubmit_",
        memo_resubmit_start,
        {MEMO_RESUBMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, memo_resubmit_received)]},
        memo_cancel,
    )

    static_handlers = [
        CallbackQueryHandler(memo_menu_handler,           pattern="^menu_memos$"),
        CallbackQueryHandler(my_memos_handler,            pattern="^menu_my_memos$"),
        CallbackQueryHandler(memo_view_handler,           pattern="^memo_view_"),
        CallbackQueryHandler(memo_pending_hr_handler,     pattern="^memo_pending_hr$"),
        CallbackQueryHandler(hr_memo_view_handler,        pattern="^hr_memo_view_"),
        CallbackQueryHandler(hr_memo_register_handler,    pattern="^hr_memo_register_"),
        CallbackQueryHandler(memo_pending_hr_mgr_handler, pattern="^memo_pending_hr_mgr$"),
        CallbackQueryHandler(hr_mgr_view_handler,         pattern="^hr_mgr_view_"),
        CallbackQueryHandler(hr_mgr_approve_handler,      pattern="^hr_mgr_approve_"),
        CallbackQueryHandler(hr_mgr_sendback_handler,     pattern="^hr_mgr_sendback_"),
        CallbackQueryHandler(hr_mgr_reject_handler,       pattern="^hr_mgr_reject_"),
        CallbackQueryHandler(memo_pending_dir_handler,    pattern="^memo_pending_dir$"),
        CallbackQueryHandler(dir_memo_view_handler,       pattern="^dir_memo_view_"),
        CallbackQueryHandler(dir_memo_approve_handler,    pattern="^dir_memo_approve_"),
        CallbackQueryHandler(memo_archive_handler,        pattern="^memo_archive$"),
        CallbackQueryHandler(memo_archive_month_handler,  pattern="^memo_arch_month_"),
        CallbackQueryHandler(memo_all_handler,            pattern="^memo_all$"),
    ]

    return [submission_conv, hr_changes_conv, hr_reject_conv,
            dir_reject_conv, resubmit_conv] + static_handlers
