# NEW FEATURE: Распоряжение (Leave Order) + Electronic Signatures
# Build ONE section at a time. "Section X done" → STOP → I test → "next"

====================================================================
# SECTION A: ELECTRONIC SIGNATURE SYSTEM
====================================================================

## A1. How It Works
Every user who approves/signs documents has a digital signature.
The signature is TIED to their Telegram ID — nobody else can use it.

## A2. Signature Setup
Add to Employee_DB: new column "Signature_Link" (Google Drive link to signature image)

First-time setup flow (any user):
1. User opens bot → My Profile → ✍️ Setup Signature
2. Bot explains: "Write your signature on white paper, take a clear photo, send it"
3. User sends photo
4. Bot crops/processes → saves to Drive: /Signatures/[EMP_CODE]_signature.png
5. Bot saves Drive link to Employee_DB Signature_Link column
6. Confirmation: "✅ Signature saved! It will appear on all documents you approve."

Alternative: user can type "USE TEXT SIGNATURE" → bot generates text-based:
"[Full Name] — Electronically signed — [DD/MM/YYYY HH:MM]"

## A3. Signature in PDFs
When generating any PDF (leave approval, Распоряжение, certificates, etc.):
- For each approver in the chain: embed their signature image (if exists) or text signature
- Add below each signature: "[Role] — [Full Name] — [DD/MM/YYYY HH:MM]"
- Add verification code: "Verified: SIG-[random 8 chars]" (unique per document)

## A4. Signature Security Rules
- Only the authenticated Telegram user can trigger their signature
- Signature is applied AUTOMATICALLY when they tap "✅ Approve" — no extra step
- If employee submits leave themselves → their signature is applied on submission
- If supervisor submits on behalf → supervisor's signature (not employee's)
- The approval chain signatures are applied at each stage:
  1. Submitter signs on submission
  2. Manager signs on approval
  3. HR signs on approval
  4. Director signs on approval
- Final PDF shows ALL signatures in order

## A5. Signature Storage
Store in Google Sheet Employee_DB column "Signature_Link"
Store image in Drive: /Signatures/[EMP_CODE]_signature.png
Bot downloads the image when generating PDFs.

====================================================================
# SECTION B: РАСПОРЯЖЕНИЕ (LEAVE ORDER DOCUMENT)
====================================================================

## B1. What Is It?
When a leave request is FULLY APPROVED (all stages complete),
the bot generates a formal bilingual order document (Russian + English).
This is the official company document — not just the approval certificate.

## B2. Document Format (from company template)

Page: A4 Portrait
Header: Company logo centered + "ROIN WORLD FZE EGYPT BRANCH" +
        "Building № 1, Gamal Abdel Nasser Street - El Dabaa - Matrouh" +
        "info.egypt@roinworld.com    www.roinworld.com"
Horizontal line under header.

Then the body:

```
                    Распоряжение № ОП-[NUMBER]
[DATE]                                          АРЕ, г. Эль-Дабаа

    О предоставлении [LEAVE_TYPE_RU]

РАСПОРЯЖАЮСЬ:

    Предоставить [LEAVE_TYPE_RU_FULL] [JOB_TITLE_RU] ([EMP_CODE])
[FULL_NAME_RU] продолжительностью [DAYS] календарных дней
с [START_DATE] по [END_DATE].

    Основание: заявление о предоставлении отпуска №[REQUEST_ID]
от [SUBMISSION_DATE].

─────────────────────────────────────────────────

    About providing [LEAVE_TYPE_EN]

ORDER:

    Provide [LEAVE_TYPE_EN_FULL] to [JOB_TITLE_EN] ([EMP_CODE])
[FULL_NAME] for a period of [DAYS] calendar days
from [START_DATE] to [END_DATE].

    Reason: application for leave No. [REQUEST_ID] dated [SUBMISSION_DATE]


                                            [DIRECTOR_SIGNATURE]
Директор филиала «ROIN WORLD FZE» в АРЕ     [DIRECTOR_NAME]
Branch director «ROIN WORLD FZE» in ARE

                    [COMPANY_STAMP/LOGO]


Исп.[HR_SPECIALIST_NAME]
```

## B3. Leave Type Text Mapping

| Leave Type | Russian Title | English Title |
|-----------|--------------|---------------|
| Paid | О предоставлении оплачиваемого отпуска | About providing paid vacation |
| Paid (body) | оплачиваемый отпуск | paid leave |
| Sick | О предоставлении больничного отпуска | About providing sick leave |
| Sick (body) | больничный отпуск | sick leave |
| Emergency | О предоставлении экстренного отпуска | About providing emergency leave |
| Emergency (body) | экстренный отпуск | emergency leave |
| Unpaid | О предоставлении отпуска за свой счёт | About providing unpaid leave |
| Unpaid (body) | отпуск без сохранения заработной платы | unpaid leave |
| Business_Trip | О направлении в командировку | About business trip assignment |
| Business_Trip (body) | командировку | business trip |

## B4. Auto-Numbering
Распоряжение numbers: ОП-[sequential number per year]
Track in a counter: either in config or in a Google Sheet cell.
Format: ОП-001, ОП-002, etc. Reset each year.
Store in Leave_Log: add column "Order_Number" (or use existing columns)

## B5. When Is It Generated?
- ONLY when Final_Status = "Approved" (all approvers signed)
- Auto-generated immediately after last approval
- Sent to:
  1. Employee (in Telegram chat)
  2. HR_Manager (in Telegram chat)
  3. Saved to Drive: /Orders/[YEAR]/[MONTH]/ОП-[NUMBER]_[EMP_CODE].pdf
- Link saved in Leave_Log: PDF_Drive_Link column

## B6. Signatures in the Распоряжение
- Director's signature image (from Signature_Link) placed at the signature area
- Company logo/stamp placed at the center bottom
- "Исп." (Prepared by) = the HR staff who processed it (HR_Staff or HR_Manager)
- If image signature exists → embed image
- If no image → text: "[Name] — Электронная подпись / Electronic signature — [datetime]"

## B7. Implementation
Create new file: order_generator.py
- Function: generate_leave_order(request_data, emp_data, director_data, hr_name)
- Uses fpdf2
- Returns PDF bytes
- Called from approval_handler.py after final approval

## B8. The Leave Approval PDF (existing) vs Распоряжение (new)
Keep BOTH:
- Leave Approval Certificate (existing pdf_generator.py) — internal HR document
- Распоряжение (new order_generator.py) — official company order

Both are generated when leave is fully approved.
Employee gets both in Telegram.
Both saved to Drive (different filenames).

====================================================================
# SECTION C: UPDATE ALL EXISTING PDFs WITH SIGNATURES
====================================================================

Update pdf_generator.py (leave approval certificate):
- Add signature images for each approver in the approval chain
- Below each approval line: embed signature image (or text if no image)
- Add verification code at the bottom

Update jd_generator.py (job description):
- "Prepared By" → HR signature
- "Reviewed By" → Manager signature
- "Approved By" → HR Manager or Director signature

Update cert_handler.py (employment certificates):
- "Authorized Signature" → HR Manager signature image

All PDFs now show real signatures, not blank lines.

====================================================================
# SECTION D: APPROVAL FLOW WITH SIGNATURES
====================================================================

Current flow (no change to logic, just add signature capture):

1. Employee submits leave → their signature auto-applied (timestamp saved)
2. Manager taps ✅ Approve → manager's signature auto-applied
3. HR taps ✅ Approve → HR signature auto-applied
4. Director taps ✅ Approve → Director signature auto-applied
5. Final PDF generated with ALL 3-4 signatures embedded
6. Распоряжение generated with Director signature + stamp

The signature is captured at the MOMENT of approval — timestamp is exact.
No extra steps for the user. Tap Approve = signed.

If supervisor submits on behalf of employee:
- Supervisor's signature replaces employee signature
- Rest of chain same

====================================================================
# SECTION E: SIGNATURE MANAGEMENT
====================================================================

My Profile → ✍️ My Signature:
- View current signature (show image preview)
- Update signature (upload new photo)
- Switch to text signature
- Remove signature

Admin (HR_Manager / Bot_Manager):
- ⚙️ Admin → Signatures → View all employees with/without signatures
- Can reset an employee's signature

====================================================================
# BUILD ORDER
====================================================================

Section A (signature system + setup flow + storage) →
Section B (Распоряжение PDF generator with bilingual text) →
Section C (update existing PDFs with signatures) →
Section D (approval flow captures signatures) →
Section E (signature management in profile)

After EACH section: "Section X done — ready to test" → STOP.

START WITH SECTION A.
====================================================================
