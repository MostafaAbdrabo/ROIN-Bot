# MEMO FORMAT UPDATE — Add to MEMO_NOTIF_AI_PROMPT.md
# This REPLACES Section B7 (Memo PDF Format) with the exact company format.
# Send this to Claude Code TOGETHER with MEMO_NOTIF_AI_PROMPT.md
#
# Tell Code: "Read MEMO_NOTIF_AI_PROMPT.md first, then read MEMO_FORMAT_UPDATE.md
# which replaces Section B7 with the correct company format. Build everything
# in one session non-stop."

====================================================================
# REPLACE SECTION B7 WITH THIS EXACT FORMAT
====================================================================

## PDF Specifications
- Page: A4 Portrait
- Font: Times New Roman size 12 EVERYWHERE (this is mandatory — Russians prefer it)
- Title "Служебная записка": Times New Roman, Bold, size 14, centered
- Body text: Times New Roman, size 12, justified
- Small text at bottom: Times New Roman, size 10
- NO company header/logo at top (unlike other documents — this is a plain memo)
- Registration stamp uses a different style (see below)

## IMPORTANT: fpdf2 and Times New Roman
fpdf2 built-in "Times" font = Times New Roman equivalent. Use font family "Times".
For Cyrillic (Russian text): fpdf2 Helvetica/Times cannot render Cyrillic.
SOLUTION: Use a Unicode font. Download and register DejaVuSans or FreeSans.
OR: transliterate Russian to Latin for PDF (like order_generator.py does).
OR: use reportlab instead of fpdf2 for this specific PDF (supports Unicode natively).
BEST OPTION: Register a .ttf font that supports Cyrillic in fpdf2:
  pdf.add_font("DejaVu", "", "/path/to/DejaVuSans.ttf", uni=True)
  pdf.add_font("DejaVu", "B", "/path/to/DejaVuSans-Bold.ttf", uni=True)
Download DejaVuSans.ttf to the day1/ folder if not present.
Use it for ALL Russian text. For English sections, can use Times or same DejaVu.

## Exact Layout (from real company document)

```
                                        Директору филиала
                                        ROIN WORLD FZE в АРЕ
                                        [DIRECTOR_LAST_NAME] [DIRECTOR_INITIALS]
                                        От [SUBMITTER_TITLE_RU]
                                        [SUBMITTER_LAST_NAME] [SUBMITTER_INITIALS] ([EMP_CODE])


                    Служебная записка

    [BODY TEXT IN RUSSIAN — justified, Times New Roman 12]

    [Multiple paragraphs as needed]

    [If the memo has bullet points or numbered lists, format them properly]


                                                    [DATE DD.MM.YYYY]

                                        [SUBMITTER_SIGNATURE_IMAGE]
                                        [SUBMITTER_FULL_NAME]


[IF MANAGER APPROVAL NEEDED — left side:]
Согласовано:
[MANAGER_TITLE_RU]
_________________ [MANAGER_NAME]
[MANAGER_SIGNATURE_IMAGE]
[DATE]


[IF ENGLISH VERSION INCLUDED — after a separator line:]
────────────────────────────────────────

                                        To the Branch Director
                                        ROIN WORLD FZE in ARE
                                        [DIRECTOR_NAME]
                                        From [SUBMITTER_TITLE_EN]
                                        [SUBMITTER_NAME] ([EMP_CODE])


                    Internal Memo

    [BODY TEXT IN ENGLISH — same content translated]


                                                    [DATE DD/MM/YYYY]

                                        [SUBMITTER_SIGNATURE_IMAGE]
                                        [SUBMITTER_FULL_NAME]


[BOTTOM CENTER — Registration stamp area:]
─────────────────────────────
ROIN WORLD FZE EGYPT
Incoming № HR [MM]-[SEQUENTIAL_NUMBER]
[REGISTRATION_DATE DD/MM/YYYY]
[HR_STAFF_SIGNATURE_IMAGE]
─────────────────────────────


[VERY BOTTOM LEFT — small text, size 10:]
Исп. [SUBMITTER_FULL_NAME]
Должность: [SUBMITTER_TITLE_RU]
Номер Телефона: [SUBMITTER_PHONE]
Почта: [SUBMITTER_EMAIL or "info.egypt@roinworld.com"]
```

## Registration Number Format
Format: HR [MONTH_NUMBER]-[SEQUENTIAL_NUMBER_IN_MONTH]
Examples:
- HR 03-001 (first memo registered in March)
- HR 03-002 (second memo in March)
- HR 12-316 (316th memo in December — from the real document)

Track via Memo_Log: scan existing entries for the current month, increment.
The sequential number resets each month (or continues yearly — match company practice).
Based on the real doc showing "HR 12-316", it looks like it continues all year.
So: HR [MONTH]-[YEARLY_SEQUENTIAL]

## Director's Resolution (top left, handwritten style)
In the real document, the Director writes a resolution by hand in the top-left corner.
In the digital version:
- When Director approves, they can type a short resolution text
- This text appears in the top-left corner of the PDF in a "handwriting" style
  (or just italic blue text to simulate handwritten note)
- Example from real doc: "Согласовано. В работу. ОРП" + Director signature
- In bot: Director types resolution → appears as italic text top-left + Director signature

## Who Signs Where

| Position in PDF | Who Signs | When |
|----------------|-----------|------|
| Top-left corner (resolution) | Director | On approval — types resolution + signs |
| After body text (right side) | Submitter | On submission |
| "Согласовано" (left side) | Direct Manager (if applicable) | On manager approval |
| Registration stamp (center bottom) | HR Staff who registers | On registration |
| Below registration | HR Manager | On HR Manager approval |

## Manager Approval Section ("Согласовано")
Only appears if the submitter is NOT a department head.
If submitter is Direct_Manager → skip this section (they report directly to Director).
If submitter is Employee/Supervisor → their Direct_Manager must approve first.

Format:
```
Согласовано:
[MANAGER_TITLE]
_________________ [MANAGER_FULL_NAME]
[MANAGER_SIGNATURE]
[DATE]
```

If English version included, add below:
```
Approved by:
[MANAGER_TITLE_EN]
_________________ [MANAGER_FULL_NAME]
[MANAGER_SIGNATURE]
[DATE]
```

====================================================================
# ADDITIONAL: Download DejaVuSans Font
====================================================================

Claude Code should download the font on first run:
```python
import urllib.request, os
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(FONT_DIR, "DejaVuSans.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_ITALIC = os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")

if not os.path.exists(FONT_PATH):
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/main/ttf/DejaVuSans.ttf"
    urllib.request.urlretrieve(url, FONT_PATH)
if not os.path.exists(FONT_BOLD):
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/main/ttf/DejaVuSans-Bold.ttf"
    urllib.request.urlretrieve(url, FONT_BOLD)
if not os.path.exists(FONT_ITALIC):
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/main/ttf/DejaVuSans-Oblique.ttf"
    urllib.request.urlretrieve(url, FONT_ITALIC)
```

Register in fpdf2:
```python
pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
pdf.add_font("DejaVu", "B", FONT_BOLD, uni=True)
pdf.add_font("DejaVu", "I", FONT_ITALIC, uni=True)
```

Use "DejaVu" font for ALL memo PDFs. This supports Russian, Arabic, and English.

====================================================================
# APPLY SAME FONT FIX TO ALL RUSSIAN PDFs
====================================================================

Update order_generator.py (Распоряжение) to also use DejaVu font
instead of transliterated Helvetica. This way Russian text renders
properly as actual Cyrillic characters, not transliterated Latin.

Update ALL PDF generators that contain Russian text:
- order_generator.py (Распоряжение)
- memo_generator.py (new — Служебная записка)
- cert_handler.py (Russian certificates)
- Any other PDF that has Russian content

====================================================================
# ALSO ADD TO EMPLOYEE_DB
====================================================================

New columns needed (if not already present):
- Email (employee email address)
- Phone is already there

The memo bottom section needs:
- Исп. [name] → from Full_Name
- Должность [title] → from Job_Title  
- Номер Телефона → from Phone column
- Почта → from Email column (new)

Add Email column to Employee_DB if missing.

====================================================================
