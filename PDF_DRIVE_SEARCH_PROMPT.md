# IMPROVEMENTS: PDF Viewing + Drive Auto-Upload + Universal Search + Sound Alert
# Build ALL sections non-stop. After done: "All done — ready to test" → STOP.
# Then run: afplay /System/Library/Sounds/Hero.aiff

====================================================================
# SECTION A: PDF PREVIEW VIA DRIVE LINK (not download)
====================================================================

## The Problem
Currently, viewing a PDF requires downloading the file. 
Better: upload to Drive FIRST, then show a clickable link that opens in browser.

## The Solution
For ALL PDFs in the entire system:

1. When PDF is generated (at any stage — draft, preview, or final):
   - Upload to Google Drive via Apps Script middleman
   - Get back the file URL
   - Show as an inline button: [📄 View PDF] → opens Drive link in browser
   - User taps → opens in their phone browser → sees the PDF instantly
   - No download needed

2. The button uses Telegram's URL button:
   ```python
   InlineKeyboardButton("📄 View PDF", url=drive_url)
   ```
   This opens the link directly — no download.

3. Drive folders for DRAFT/PREVIEW (not yet approved):
   Folder ID: 1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5
   Link: https://drive.google.com/drive/folders/1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5
   
4. Drive folders for APPROVED documents:
   See Section B below for each type.

## Apply to ALL document types:
- Leave approval certificates
- Распоряжение (leave orders)
- Memos (Служебная записка)
- Job Descriptions
- Employment certificates
- Personnel Requisition Forms
- Monthly schedule PDFs
- Evaluation reports
- Any other PDF the bot generates

## Who sees the PDF link:
- ALL parties involved in the document can see the [📄 View PDF] button
- Submitter sees it after submission (draft in preview folder)
- Each approver sees it when reviewing (draft in preview folder)
- After final approval, everyone involved gets the FINAL link (approved folder)

====================================================================
# SECTION B: DRIVE AUTO-UPLOAD — ORGANIZED FOLDERS
====================================================================

## MEMO FOLDERS (already created — use these NOW):

DRIVE_FOLDERS in config.py:
```python
DRIVE_FOLDERS = {
    # Memos — REAL FOLDER IDs (use immediately)
    "memo_drafts": "1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5",
    "memo_approved": "1rol_SQCWW9kLGedFwXuFvw61dN61qT7Z",
    
    # All drafts/previews for any document type (reuse memo drafts for now)
    "drafts": "1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5",
    
    # Others — Mostafa will create folders and add IDs later
    "leave_approvals": "",
    "leave_orders": "",
    "job_descriptions": "",
    "certificates": "",
    "evaluations": "",
    "requisitions": "",
    "schedules": "",
    "safety_reports": "",
    "quality_reports": "",
    "operations_reports": "",
    "contracts": "",
}
```

## Memo flow specifically:
1. Submitter writes memo → previews → PDF uploaded to `memo_drafts` folder
   → [📄 View PDF] button shown (opens Drive link in browser)
2. HR reviews → sees same draft PDF via [📄 View PDF] button  
3. HR registers → PDF regenerated with registration number + HR signature
   → uploaded to `memo_drafts` (new version)
4. HR Manager approves → PDF regenerated with HR Manager signature
   → still in `memo_drafts`
5. Director approves → FINAL PDF with all signatures
   → uploaded to `memo_approved` folder
   → Drive link saved to Memo_Log column "Drive_Link"
   → [📄 View PDF] button shows the APPROVED folder link
   → Everyone involved gets the final link

## For all OTHER document types:
If folder ID is empty (""), skip the upload gracefully:
- Don't crash
- Log: "Drive folder not configured for [type] — skipping upload"
- Still generate the PDF and send as Telegram document (fallback)
- When Mostafa adds folder IDs later, uploads start working automatically

## Store the Drive link in the sheet:
After upload, save the Drive URL back to the relevant log tab:
- Leave_Log → PDF_Drive_Link column (col 21)
- Memo_Log → Drive_Link column (col 24)
- JD_Drafts → PDF_Drive_Link column
- Evaluations_Log → Report_Drive_Link column
- Hiring_Requests → PDF_Link column (add if missing)

====================================================================
# SECTION C: UNIVERSAL DOCUMENT SEARCH
====================================================================

## New menu item for authorized roles:
🔍 Search Documents

Available to: Bot_Manager, Director, HR_Manager, HR_Staff

## How it works:
1. User taps 🔍 Search Documents
2. Types any document ID:
   - LVE-2026-0042 (leave request)
   - OP-2026-015 (Распоряжение/leave order)
   - MEMO-2026-0001 or СЗ-2026-0001 (memo)
   - JD-20260320162057 (job description)
   - EVL-2026-0045 (evaluation)
   - MP-2026-0001 (missing punch)
   - ED-2026-0001 (early departure)
   - OT-2026-0001 (overtime)
   - HR_REQ-2026-0001 (hiring request)
   - JP-2026-0001 (job posting)
   - CND-2026-0001 (candidate)
   - TX-2026-0001 (stock transaction)
   - BUG-/SUG-/QST-/CMP- (feedback tickets)

3. Bot detects the PREFIX and searches the correct tab:
   | Prefix | Tab to Search | ID Column |
   |--------|--------------|-----------|
   | LVE- | Leave_Log | col 1 |
   | OP- | Leave_Log | col 23 (Order_Number) |
   | MEMO- or СЗ- | Memo_Log | col 1 or col 9 |
   | JD- | JD_Drafts | col 1 |
   | EVL- | Evaluations_Log | col 1 |
   | MP- | Leave_Log | col 1 (type=Missing_Punch) |
   | ED- | Leave_Log | col 1 (type=Early_Departure) |
   | OT- | Leave_Log | col 1 (type=Overtime) |
   | HR_REQ- | Hiring_Requests | col 1 |
   | JP- | Job_Postings | col 1 |
   | CND- | Candidates | col 1 |
   | TX- | Stock_Transactions | col 1 |
   | BUG-/SUG-/QST-/CMP- | Bot_Feedback | col 1 |

4. If found: show full detail + [📄 View PDF] (if PDF/Drive link exists)
5. If not found: "Document not found. Check the ID and try again." + ↩️ Back to search

## Access Control:
| Role | Can Search |
|------|-----------|
| Bot_Manager | Everything — no restrictions |
| Director | Everything — no restrictions |
| HR_Manager | All HR documents, all memos, all leave, all evaluations |
| HR_Staff | Same as HR_Manager but read-only (no approve from search) |
| Direct_Manager | Only documents from their department employees |
| Supervisor | Only their own documents + their team's |
| Employee | Only their own documents |

If a user searches for a document they don't have access to:
"You don't have permission to view this document." + ↩️ Back to search

====================================================================
# SECTION D: APPLY [📄 View PDF] BUTTON EVERYWHERE
====================================================================

Go through EVERY handler that shows document details and add the
[📄 View PDF] button if a Drive link exists for that document.

Specifically update ALL of these:

### Leave system:
- leave_request.py → My Requests → request detail → add [📄 View PDF]
- leave_request.py → Team Requests → request detail → add [📄 View PDF]
- approval_handler.py → Pending Approvals → request detail → add [📄 View PDF]

### Memo system:
- memo_handler.py → submitter preview → [📄 View PDF] (draft folder link)
- memo_handler.py → HR review screen → [📄 View PDF]
- memo_handler.py → HR Manager review → [📄 View PDF]
- memo_handler.py → Director review → [📄 View PDF]
- memo_handler.py → archive view → [📄 View PDF] (approved folder link)

### JD system:
- jd_handler.py → JD detail view → [📄 View PDF]

### Evaluations:
- eval_handler.py → evaluation detail → [📄 View PDF]

### Recruitment:
- recruitment_handler.py → hiring request detail → [📄 View PDF]

### Certificates:
- cert_handler.py → after generating cert → [📄 View PDF]

### Universal Search:
- search results → [📄 View PDF] if link exists

The button is a URL button (opens in browser):
```python
if drive_link and drive_link.startswith("http"):
    kb.append([InlineKeyboardButton("📄 View PDF", url=drive_link)])
```

If no Drive link yet: don't show the button.
If document is in draft stage: upload to drafts folder first, then show link.

====================================================================
# SECTION E: BACK BUTTON FIX — PREVIOUS MENU NOT MAIN MENU
====================================================================

CRITICAL: Check ALL handlers across the ENTIRE codebase.

When a user taps an option and sees an error/empty/unavailable screen:
- ↩️ Back → goes to the PARENT MENU (not main menu)
- ↩️ Main Menu → goes to main menu

Example flow:
Memo Archive → March 2026 → By Submitter → taps name → "No memos"
↩️ Back should go to → "By Submitter" list
NOT to main menu.

Every error/empty screen needs TWO buttons:
```python
kb = [
    [InlineKeyboardButton("↩️ Back", callback_data="PARENT_MENU_CALLBACK")],
    [InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")]
]
```

Go through EVERY handler file and fix any screen where ↩️ Back 
incorrectly goes to "back_to_menu" when it should go to the parent.

Files to check — EVERY SINGLE FILE:
- bot.py
- leave_request.py
- approval_handler.py
- memo_handler.py
- jd_handler.py
- attendance_handler.py
- eval_handler.py
- recruitment_handler.py
- warehouse_handler.py
- vehicles_handler.py
- supply_handler.py
- housing_handler.py
- safety_handler.py
- translation_handler.py
- operations_handler.py
- quality_handler.py
- feedback_handler.py
- cert_handler.py
- contact_hr_handler.py
- schedule_handler.py
- hr_tools_handler.py
- manager_handler.py
- doc_contract_handler.py
- announcement_handler.py
- signature_handler.py
- missing_punch.py
- order_generator.py
- Any other handler file

NO EXCEPTIONS. Every file checked.

====================================================================
# SECTION F: SOUND NOTIFICATION ON COMPLETION
====================================================================

When you finish ALL the above changes, run this as your FINAL command:
```
afplay /System/Library/Sounds/Hero.aiff
```

====================================================================
# BUILD ORDER: A → B → C → D → E → F
# Build everything non-stop.
# After all done: "All done" → STOP → play sound.
====================================================================
