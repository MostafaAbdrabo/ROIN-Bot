"""
ROIN WORLD FZE — Recruitment PDF Generator
==========================================
Generates:
  1. Personnel Requisition Form (Заявка на подбор персонала) — bilingual RU+EN
  2. Job Offer Letter — bilingual RU+EN
"""

import io, os, secrets
from datetime import datetime
from fpdf import FPDF
from font_utils import add_dejavu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO     = os.path.join(BASE_DIR, "company_logo.png")


def _u(t):
    return str(t) if t else ""


def _embed_sig(pdf, sig_bytes, x, y, w=40, h=14):
    """Embed signature image at position, or draw blank line."""
    if sig_bytes:
        try:
            pdf.image(io.BytesIO(sig_bytes), x=x, y=y, w=w, h=h)
            return True
        except Exception:
            pass
    pdf.set_xy(x, y + 6)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(w, 5, "__________", align="C")
    return False


# ── Personnel Requisition Form ─────────────────────────────────────────────────

def generate_requisition_pdf(req, sigs=None):
    """
    Generate Personnel Requisition Form PDF.

    req keys:
      req_id, date, position_title, department, num_positions,
      current_headcount, scheduled_headcount, priority, justification,
      required_start_date, contract_type, shift, work_location, salary_range,
      special_req, manager_name, director_name_ru, director_name_en,
      hr_head_name_ru, hr_head_name_en,
      hr_manager_name_ru, hr_manager_name_en,
      catering_dir_name_ru, catering_dir_name_en,
      recruiter_name, recruiter_date

    sigs keys:
      manager_sig, hr_head_sig, hr_manager_sig, catering_dir_sig,
      director_sig, recruiter_sig
    """
    if sigs is None:
        sigs = {}

    pdf = FPDF()
    add_dejavu(pdf)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 15)

    date_str = req.get("date", datetime.now().strftime("%d.%m.%Y"))

    # ── Top addressing block: two-column (RU left | EN right) ─────────────────
    y = pdf.get_y()
    ru_addr = ["Директору филиала", "ROIN WORLD FZE в АРЕ",
               _u(req.get("director_name_ru", ""))]
    en_addr = ["To the Director of the Branch", "ROIN WORLD FZE in ARE",
               _u(req.get("director_name_en", ""))]
    pdf.set_font("DejaVu", "", 10)
    for ru, en in zip(ru_addr, en_addr):
        pdf.set_xy(20, y)
        pdf.cell(87, 6, _u(ru), align="L")
        pdf.set_xy(107, y)
        pdf.cell(88, 6, _u(en), align="L")
        y += 6
    pdf.set_y(y + 6)

    # ── Bilingual centred title ────────────────────────────────────────────────
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, "Заявка на подбор персонала", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, "Personnel Requisition Form", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # ── Intro line ─────────────────────────────────────────────────────────────
    pdf.set_font("DejaVu", "", 11)
    pdf.cell(0, 6, "Прошу принять на работу в ROIN WORLD FZE в АРЕ",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, "I request to hire at ROIN WORLD FZE in ARE",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # ── Form fields ────────────────────────────────────────────────────────────
    def field(ru_lbl, en_lbl, value, bold_val=False):
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(0, 6, f"{ru_lbl} / {en_lbl}:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "B" if bold_val else "", 11)
        pdf.cell(0, 6, _u(value), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    field("Количество вакансий", "Number of staff required",
          req.get("num_positions", "1"), bold_val=True)
    field("Вакансия (Должность)", "Job Title",
          req.get("position_title", "-"), bold_val=True)
    field("В отдел", "Department", req.get("department", "-"))
    field("Текущее количество сотрудников",
          "Current headcount in department", req.get("current_headcount", "-"))
    field("Количество сотрудников согласно ШР",
          "Headcount as per staff schedule (HR)",
          req.get("scheduled_headcount", "(HR)"))

    for ru_lbl, en_lbl, key in [
        ("Приоритет",          "Priority",         "priority"),
        ("Требуемая дата начала", "Required start date", "required_start_date"),
        ("Тип контракта",      "Contract type",    "contract_type"),
        ("График работы",      "Shift",            "shift"),
        ("Место работы",       "Work location",    "work_location"),
        ("Диапазон зарплат",   "Salary range",     "salary_range"),
    ]:
        if req.get(key):
            field(ru_lbl, en_lbl, req[key])

    pdf.ln(2)

    # Justification
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "Причина запроса / Request Reason:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 11)
    pdf.multi_cell(0, 6, _u(req.get("justification", "")), align="J")

    if req.get("special_req"):
        pdf.ln(2)
        pdf.set_font("DejaVu", "B", 10)
        pdf.cell(0, 6, "Особые требования / Special requirements:",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 10)
        pdf.multi_cell(0, 6, _u(req["special_req"]), align="J")

    pdf.ln(3)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), 195, pdf.get_y())
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(5)

    # ── Department Head signature ──────────────────────────────────────────────
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "Руководитель отдела / Department Head",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    y_sig = pdf.get_y()
    rx = pdf.w - pdf.r_margin - 70
    _embed_sig(pdf, sigs.get("manager_sig"), rx, y_sig, w=45, h=14)
    pdf.set_xy(rx, y_sig + 15)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(70, 4, "(Подпись и дата / signature and date)", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(rx, pdf.get_y())
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(70, 5, _u(req.get("manager_name", "")), align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(rx, pdf.get_y())
    pdf.cell(70, 5, _u(date_str), align="C")
    pdf.set_y(y_sig + 28)
    pdf.ln(6)

    # ── Согласовано section ────────────────────────────────────────────────────
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, "Согласовано / موافق عليه:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def approval_row(ru_title, en_title, name_ru, name_en, sig_bytes):
        y0 = pdf.get_y()
        # Left: title lines
        pdf.set_xy(20, y0)
        pdf.set_font("DejaVu", "", 10)
        for i, line in enumerate(ru_title.split("\n")):
            pdf.set_xy(20, y0 + i * 5)
            pdf.cell(75, 5, _u(line))
        pdf.set_xy(20, y0 + len(ru_title.split("\n")) * 5)
        pdf.set_font("DejaVu", "", 9)
        pdf.cell(75, 5, _u(en_title))
        # Centre: signature
        cx = 97
        _embed_sig(pdf, sig_bytes, cx, y0, w=35, h=12)
        # Right: sub-label + name
        rx2 = 138
        pdf.set_xy(rx2, y0)
        pdf.set_font("DejaVu", "", 8)
        pdf.cell(57, 4, "(подпись/signature)  (ФИО / full name)")
        disp = f"{name_ru} / {name_en}" if name_en else _u(name_ru)
        pdf.set_xy(rx2, y0 + 5)
        pdf.set_font("DejaVu", "", 10)
        pdf.multi_cell(57, 5, _u(disp), align="L")
        pdf.set_y(max(pdf.get_y(), y0 + 20))
        pdf.ln(3)

    approval_row("Начальник ОРП", "Head of HRD",
                 req.get("hr_head_name_ru", ""), req.get("hr_head_name_en", ""),
                 sigs.get("hr_head_sig"))
    approval_row("HR Manager", "HR Менеджер",
                 req.get("hr_manager_name_ru", ""), req.get("hr_manager_name_en", ""),
                 sigs.get("hr_manager_sig"))
    approval_row("Директор по развитию\nобщественного питания",
                 "Director of Catering Development",
                 req.get("catering_dir_name_ru", ""), req.get("catering_dir_name_en", ""),
                 sigs.get("catering_dir_sig"))
    approval_row("Директор филиала", "Branch Director",
                 req.get("director_name_ru", ""), req.get("director_name_en", ""),
                 sigs.get("director_sig"))

    # Company logo/stamp near Director row
    if os.path.exists(LOGO):
        try:
            stamp_y = pdf.get_y() - 22
            pdf.image(LOGO, x=pdf.w - pdf.r_margin - 22, y=stamp_y, w=18)
        except Exception:
            pass

    pdf.ln(5)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(20, pdf.get_y(), 195, pdf.get_y())
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(5)

    # ── Recruiter acceptance (bottom left) ────────────────────────────────────
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 6, "Принял заявку:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, "Рекрутер", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _u(req.get("recruiter_name", "")), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Дата: {req.get('recruiter_date', date_str)}",
             new_x="LMARGIN", new_y="NEXT")
    rec_sig = sigs.get("recruiter_sig")
    if rec_sig:
        try:
            pdf.image(io.BytesIO(rec_sig), x=20, y=pdf.get_y(), w=35, h=12)
            pdf.ln(14)
        except Exception:
            pass

    # ── Footer ─────────────────────────────────────────────────────────────────
    pdf.set_y(-12)
    ver = f"REQ-{secrets.token_hex(3).upper()}"
    pdf.set_font("DejaVu", "I", 7)
    pdf.cell(0, 4,
             f"Ref: {req.get('req_id', '-')} | {ver} | "
             f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
             align="C")

    return bytes(pdf.output())


# ── Job Offer Letter ───────────────────────────────────────────────────────────

def generate_offer_pdf(offer, sigs=None):
    """
    Generate bilingual (RU + EN) Job Offer Letter PDF.

    offer keys:
      offer_id, candidate_name, position_title, department,
      salary, start_date, contract_type, contract_duration,
      benefits, special_conditions, director_name, hr_name, date

    sigs keys:
      director_sig
    """
    if sigs is None:
        sigs = {}

    pdf = FPDF()
    add_dejavu(pdf)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(25, 20, 20)

    date_str  = offer.get("date", datetime.now().strftime("%d.%m.%Y"))
    cand      = _u(offer.get("candidate_name", ""))
    position  = _u(offer.get("position_title", ""))
    dept      = _u(offer.get("department", ""))
    salary    = _u(offer.get("salary", ""))
    start     = _u(offer.get("start_date", ""))
    contract  = _u(offer.get("contract_type", ""))
    duration  = _u(offer.get("contract_duration", ""))
    benefits  = _u(offer.get("benefits", ""))
    special   = _u(offer.get("special_conditions", ""))
    director  = _u(offer.get("director_name", ""))
    hr_name   = _u(offer.get("hr_name", ""))
    offer_id  = _u(offer.get("offer_id", ""))

    # Logo + header
    if os.path.exists(LOGO):
        try:
            pdf.image(LOGO, x=88, y=8, w=24)
            pdf.ln(32)
        except Exception:
            pdf.ln(10)
    else:
        pdf.ln(10)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 7, "ROIN WORLD FZE EGYPT BRANCH",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 8)
    pdf.cell(0, 5, "Building No 1, Gamal Abdel Nasser Street - El Dabaa - Matrouh",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.line(25, pdf.get_y() + 2, 190, pdf.get_y() + 2)
    pdf.ln(8)

    # Russian offer
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, "ПРЕДЛОЖЕНИЕ О РАБОТЕ", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 11)
    pdf.cell(0, 6, f"Уважаемый(-ая) {cand},", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    ru_body = (
        f"С удовольствием предлагаем Вам должность {position} "
        f"в отделе {dept} компании ROIN WORLD FZE EGYPT BRANCH.\n\n"
        f"Условия трудоустройства:\n"
        f"• Заработная плата: {salary}\n"
        f"• Дата начала работы: {start}\n"
        f"• Тип контракта: {contract}"
        + (f"\n• Срок действия: {duration}" if duration else "")
        + (f"\n• Льготы: {benefits}" if benefits else "")
        + (f"\n\nОсобые условия:\n{special}" if special else "")
        + f"\n\nПросим подтвердить Ваше согласие в течение 3 рабочих дней.\n\n"
          f"С уважением,\n{director}\nДиректор филиала ROIN WORLD FZE в АРЕ"
    )
    pdf.set_font("DejaVu", "", 10)
    pdf.multi_cell(0, 6, ru_body, align="J")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, f"Дата: {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    y_sig = pdf.get_y()
    dir_sig = sigs.get("director_sig")
    if dir_sig:
        try:
            pdf.image(io.BytesIO(dir_sig),
                      x=pdf.w - pdf.r_margin - 50, y=y_sig, w=40, h=15)
            pdf.ln(18)
        except Exception:
            pdf.ln(5)
    else:
        pdf.cell(0, 8, "_____________________", align="R",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, director, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Divider
    pdf.set_draw_color(150, 150, 150)
    pdf.line(25, pdf.get_y(), 190, pdf.get_y())
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(8)

    # English offer
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, "JOB OFFER LETTER", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 11)
    pdf.cell(0, 6, f"Dear {cand},", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    en_body = (
        f"We are pleased to offer you the position of {position} "
        f"in the {dept} Department at ROIN WORLD FZE EGYPT BRANCH.\n\n"
        f"Terms of Employment:\n"
        f"• Salary: {salary}\n"
        f"• Start Date: {start}\n"
        f"• Contract Type: {contract}"
        + (f"\n• Duration: {duration}" if duration else "")
        + (f"\n• Benefits: {benefits}" if benefits else "")
        + (f"\n\nSpecial Conditions:\n{special}" if special else "")
        + f"\n\nPlease confirm your acceptance within 3 working days.\n\n"
          f"Sincerely,\n{director}\nBranch Director, ROIN WORLD FZE in ARE"
    )
    pdf.set_font("DejaVu", "", 10)
    pdf.multi_cell(0, 6, en_body, align="J")
    pdf.ln(3)
    pdf.cell(0, 5, f"Date: {date_str}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Footer
    pdf.set_y(-12)
    ver = f"OFF-{secrets.token_hex(3).upper()}"
    pdf.set_font("DejaVu", "I", 7)
    pdf.cell(0, 4,
             f"Offer ID: {offer_id} | {ver} | HR: {hr_name} | "
             f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
             align="C")

    return bytes(pdf.output())
