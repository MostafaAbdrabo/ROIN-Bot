"""
ROIN WORLD FZE — Распоряжение (Leave Order) PDF Generator
==========================================================
Generates the official bilingual (Russian + English) leave order document.
Uses fpdf2. Attempts to load a Cyrillic-capable font; falls back to Latin
transliteration if no suitable font is found on the system.

Function: generate_leave_order(...)  → bytes
"""

import io, os, secrets
from datetime import datetime
from fpdf import FPDF
from config import get_sheet
from font_utils import add_dejavu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO     = os.path.join(BASE_DIR, "company_logo.png")

# ── Leave type text mappings ───────────────────────────────────────────────────

LEAVE_TITLE_RU = {
    "Paid":          "О предоставлении оплачиваемого отпуска",
    "Sick":          "О предоставлении больничного отпуска",
    "Emergency":     "О предоставлении экстренного отпуска",
    "Unpaid":        "О предоставлении отпуска за свой счёт",
    "Business_Trip": "О направлении в командировку",
}
LEAVE_BODY_RU = {
    "Paid":          "оплачиваемый отпуск",
    "Sick":          "больничный отпуск",
    "Emergency":     "экстренный отпуск",
    "Unpaid":        "отпуск без сохранения заработной платы",
    "Business_Trip": "командировку",
}
LEAVE_TITLE_EN = {
    "Paid":          "About providing paid vacation",
    "Sick":          "About providing sick leave",
    "Emergency":     "About providing emergency leave",
    "Unpaid":        "About providing unpaid leave",
    "Business_Trip": "About business trip assignment",
}
LEAVE_BODY_EN = {
    "Paid":          "paid leave",
    "Sick":          "sick leave",
    "Emergency":     "emergency leave",
    "Unpaid":        "unpaid leave",
    "Business_Trip": "business trip",
}

RASPORYA_RU   = "Распоряжение"
RASPORYA_BODY = "РАСПОРЯЖАЮСЬ:"


# ── Font helpers ───────────────────────────────────────────────────────────────

def _safe(text):
    """Encode text to latin-1, stripping unsupported chars (English-only fallback)."""
    if not text: return ""
    t = str(text)
    for old, new in {"\u2014": "-", "\u2013": "-", "\u2019": "'", "\u2018": "'",
                     "\u201c": '"', "\u201d": '"', "\u00a0": " ", "\u2026": "..."}.items():
        t = t.replace(old, new)
    return t.encode("latin-1", errors="replace").decode("latin-1")


def _u(text):
    """Return text as Unicode string for DejaVu font rendering."""
    return str(text) if text else ""


# ── Order number tracking ──────────────────────────────────────────────────────

def get_next_order_number():
    """
    Scan Leave_Log column 23 (0-indexed: 22) for existing order numbers
    of the form  OP-YYYY-NNN,  then return the next one.
    """
    year = str(datetime.now().year)
    prefix = f"OP-{year}-"
    max_n  = 0
    try:
        rows = get_sheet("Leave_Log").get_all_values()
        for row in rows[1:]:          # skip header
            if len(row) > 22:
                val = str(row[22]).strip()
                if val.startswith(prefix):
                    try:
                        n = int(val.split("-")[-1])
                        max_n = max(max_n, n)
                    except ValueError:
                        pass
    except Exception:
        pass
    return f"{prefix}{str(max_n + 1).zfill(3)}"


# ── Signature embedding helper ─────────────────────────────────────────────────

def _embed_sig(pdf, sig_bytes, text_sig, label_line1, label_line2="",
               signer_name="", signed_at=""):
    """
    Embed a high-quality signature block on the right side of the page.
    Image is at least 40mm wide × 18mm tall for readability.
    Below image: bold signer name, then italic date/time.
    """
    pdf.ln(3)
    sig_placed = False
    if sig_bytes:
        try:
            img_io = io.BytesIO(sig_bytes)
            x = pdf.w - pdf.r_margin - 55   # right-align, 55mm from right margin
            y = pdf.get_y()
            pdf.image(img_io, x=x, y=y, w=40, h=0)    # 4cm wide, height auto (high quality)
            pdf.ln(22)
            sig_placed = True
        except Exception:
            pass
    if not sig_placed:
        if text_sig:
            pdf.set_font("DejaVu", "I", 9)
            pdf.cell(0, 6, _u(text_sig), new_x="LMARGIN", new_y="NEXT", align="R")
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, "___________________________", new_x="LMARGIN", new_y="NEXT", align="R")

    # Bold signer name below signature
    if signer_name:
        pdf.set_font("DejaVu", "B", 9)
        pdf.cell(0, 5, _u(signer_name), new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, _u(label_line1), new_x="LMARGIN", new_y="NEXT", align="R")
    if label_line2:
        pdf.cell(0, 5, _u(label_line2), new_x="LMARGIN", new_y="NEXT", align="R")
    # Italic date/time
    if signed_at:
        pdf.set_font("DejaVu", "I", 8)
        pdf.cell(0, 4, _u(signed_at), new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(3)


# ── PDF class ──────────────────────────────────────────────────────────────────

class OrderPDF(FPDF):
    def header(self):
        if os.path.exists(LOGO):
            self.image(LOGO, x=85, y=8, w=25)
            self.ln(28)
        else:
            self.ln(10)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 6, "ROIN WORLD FZE EGYPT BRANCH",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, "Building No 1, Gamal Abdel Nasser Street - El Dabaa - Matrouh",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        self.cell(0, 5, "info.egypt@roinworld.com     www.roinworld.com",
                  new_x="LMARGIN", new_y="NEXT", align="C")
        self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 4, "Generated by ROIN WORLD FZE HR System",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 4,
                  f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                  align="C")


# ── Main generator ─────────────────────────────────────────────────────────────

def generate_leave_order(request_data, emp_data, director_data, hr_name,
                         director_sig_bytes=None, director_sig_text=None,
                         order_number=None):
    """
    Generate the bilingual Rasporyazhenie PDF.

    Args:
        request_data:      dict — request_id, leave_type, start_date, end_date,
                                  working_days, reason, submitted_at
        emp_data:          dict — Full_Name, Job_Title, Emp_Code (from Employee_DB)
        director_data:     dict — Full_Name (from Employee_DB); may be {}
        hr_name:           str  — HR staff who processed the request
        director_sig_bytes: bytes or None — director's signature image
        director_sig_text:  str or None   — director's text fallback signature
        order_number:      str  — e.g. "OP-2026-001"  (auto-generated if None)

    Returns: PDF bytes
    """
    if not order_number:
        order_number = get_next_order_number()

    lt        = request_data.get("leave_type", "Paid")
    title_ru  = LEAVE_TITLE_RU.get(lt, f"O predostavlenii {lt}")
    body_ru   = LEAVE_BODY_RU.get(lt, lt)
    title_en  = LEAVE_TITLE_EN.get(lt, f"About {lt}")
    body_en   = LEAVE_BODY_EN.get(lt, lt.replace("_", " ").lower())

    rid       = request_data.get("request_id", "-")
    start     = request_data.get("start_date", "-")
    end       = request_data.get("end_date", "-")
    days      = str(request_data.get("working_days", "-"))
    sub_at    = str(request_data.get("submitted_at", "-"))
    # Extract date only from datetime string
    sub_date  = sub_at.split(" ")[0] if " " in sub_at else sub_at

    emp_name  = str(emp_data.get("Full_Name", "-"))
    job_title = str(emp_data.get("Job_Title",  "-"))
    emp_code  = str(emp_data.get("Emp_Code", "-"))
    dir_name  = str(director_data.get("Full_Name", "Director") if director_data else "Director")

    date_str  = datetime.now().strftime("%d.%m.%Y")
    ver_code  = f"SIG-{secrets.token_hex(4).upper()}"

    pdf = OrderPDF()
    add_dejavu(pdf)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Header: Order title + date/city ──────────────────────────────────────
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8,
             _u(f"{RASPORYA_RU}  №  {order_number}"),
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("DejaVu", "", 10)
    pdf.cell(95, 7, _u(date_str))
    pdf.cell(95, 7, "АРЕ, Эль-Дааба", align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Russian section ───────────────────────────────────────────────────────
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 7, "  [ Русский ]", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)

    pdf.set_font("DejaVu", "I", 11)
    pdf.multi_cell(0, 7, _u(f"    {title_ru}"))
    pdf.ln(2)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, _u(RASPORYA_BODY), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("DejaVu", "", 10)
    ru_body = (
        f"    Предоставить {body_ru}  {job_title}  ({emp_code})\n"
        f"{emp_name}  продолжительностью {days} календарных дней\n"
        f"с {start}  по  {end}.\n\n"
        f"    Основание: заявление о предоставлении отпуска  №{rid}\n"
        f"от {sub_date}."
    )
    pdf.multi_cell(0, 6, _u(ru_body))
    pdf.ln(5)

    # Divider between RU and EN
    pdf.set_draw_color(180, 180, 180)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(5)

    # ── English section ───────────────────────────────────────────────────────
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(0, 7, "  [ English ]", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)

    pdf.set_font("DejaVu", "I", 11)
    pdf.multi_cell(0, 7, _u(f"    {title_en}"))
    pdf.ln(2)

    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(0, 7, "ORDER:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("DejaVu", "", 10)
    en_body = (
        f"    Provide {body_en} to {job_title}  ({emp_code})\n"
        f"{emp_name}  for a period of {days} calendar days\n"
        f"from {start}  to  {end}.\n\n"
        f"    Reason: application for leave No. {rid}  dated {sub_date}."
    )
    pdf.multi_cell(0, 6, _u(en_body))
    pdf.ln(12)

    # ── Director signature ────────────────────────────────────────────────────
    _embed_sig(
        pdf,
        director_sig_bytes,
        director_sig_text,
        label_line1="Branch Director — ROIN WORLD FZE in ARE",
        label_line2="Директор филиала «ROIN WORLD FZE» в АРЕ",
        signer_name=dir_name,
        signed_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    # ── Company logo/stamp (centred) ──────────────────────────────────────────
    if os.path.exists(LOGO):
        logo_w  = 22
        x_stamp = (pdf.w - logo_w) / 2
        y_stamp = pdf.get_y()
        pdf.image(LOGO, x=x_stamp, y=y_stamp, w=logo_w)
        pdf.ln(26)

    # ── HR specialist ─────────────────────────────────────────────────────────
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 7, _u(f"Исп. / Prepared by:   {hr_name}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # ── Footer verification ───────────────────────────────────────────────────
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("DejaVu", "I", 7)
    pdf.cell(0, 4,
             _u(f"Verified: {ver_code}   |   Order: {order_number}   |   Request: {rid}"),
             align="C")

    return bytes(pdf.output())
