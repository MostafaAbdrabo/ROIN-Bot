# CRITICAL FIX: ZERO FILES IN CHAT — EVERYTHING VIA DRIVE LINK
# This is a FUNDAMENTAL RULE. Apply to the ENTIRE project.
# Build non-stop. After done: "All done" → STOP
# Then run: afplay /System/Library/Sounds/Hero.aiff

====================================================================
# THE RULE (non-negotiable)
====================================================================

NEVER use send_document() or send_photo() to send PDFs in chat.
NEVER. NOT ONCE. NOT ANYWHERE IN THE ENTIRE CODEBASE.

Instead, ALWAYS:
1. Generate PDF
2. Upload to Google Drive (correct folder)
3. Get the Drive URL back
4. Send a Telegram message with a URL button: [📄 View PDF]
5. User taps → opens in browser → sees the PDF

This applies to:
- ALL document types
- ALL roles
- ALL stages (draft, review, approved)
- ALL handlers
- The archive
- Search results
- Notifications
- Everything

====================================================================
# DRIVE FOLDERS
====================================================================

TWO folders for memos (apply same pattern for all doc types later):

DRAFTS (not yet Director-approved):
  Folder ID: 1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5

APPROVED (Director signed):
  Folder ID: 1rol_SQCWW9kLGedFwXuFvw61dN61qT7Z

For ALL other document types: use the DRAFTS folder for now.
When Mostafa creates specific folders later, he'll update config.py.

config.py addition:
```python
DRIVE_FOLDERS = {
    "drafts": "1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5",
    "approved": "1rol_SQCWW9kLGedFwXuFvw61dN61qT7Z",
}
```

====================================================================
# MEMO FLOW — EXACT STEPS WITH DRIVE
====================================================================

## Step 1: Employee submits memo
- PDF generated (draft, no signatures except submitter)
- Uploaded to DRAFTS folder
- Filename: MEMO-2026-0001_draft.pdf
- Employee sees: "✅ Memo submitted!" + [📄 View PDF] (Drive link)
- NO file sent in chat

## Step 2: HR Staff registers
- PDF regenerated WITH: registration number + HR signature
- Uploaded to DRAFTS folder
- Filename: HR_03-001_MEMO-2026-0001_registered.pdf
- HR Staff sees confirmation + [📄 View PDF]
- Original submitter gets notification: "📝 Your memo registered: HR 03-001" + [📄 View PDF]
- NO file sent in chat

## Step 3: HR Manager approves
- PDF regenerated WITH: all previous + HR Manager signature
- Uploaded to DRAFTS folder
- Filename: HR_03-001_MEMO-2026-0001_hr_approved.pdf
- HR Manager sees confirmation + [📄 View PDF]
- Submitter gets notification: "✅ HR Manager approved your memo" + [📄 View PDF]
- NO file sent in chat

## Step 4: Director approves
- FINAL PDF with ALL signatures (submitter + HR + HR Manager + Director)
- Uploaded to APPROVED folder (different folder!)
- Filename: HR_03-001_MEMO-2026-0001_APPROVED.pdf
- Director sees confirmation + [📄 View PDF]
- Submitter gets notification: "✅ Director approved your memo!" + [📄 View PDF]
- HR Manager gets notification + [📄 View PDF]
- Drive link saved to Memo_Log → Drive_Link column
- NO file sent in chat

## Step 5: Archive
- Anyone viewing this memo in the archive sees [📄 View PDF]
- Link points to the APPROVED folder version
- NO file sent in chat

====================================================================
# APPLY SAME PATTERN TO ALL DOCUMENT TYPES
====================================================================

## Leave Approval Certificate
- Generated on final approval
- Upload to DRAFTS folder (until specific leave folder is created)
- Show [📄 View PDF] to employee
- Save link to Leave_Log → PDF_Drive_Link

## Распоряжение (Leave Order)
- Generated on final approval
- Upload to DRAFTS folder
- Show [📄 View PDF] to employee + HR
- Save link to Leave_Log

## Job Description PDF
- Upload to DRAFTS folder
- Show [📄 View PDF] at each review stage
- Final approved → upload to APPROVED folder

## Employment Certificate
- Generate → upload to DRAFTS → show [📄 View PDF]

## Evaluation PDF
- Generate → upload → show [📄 View PDF]

## Personnel Requisition Form
- Generate → upload → show [📄 View PDF] at each stage

## Monthly Schedule PDF
- Generate → upload → show [📄 View PDF]

## ANY other PDF anywhere in the system
- Generate → upload to Drive → show link → NEVER send file

====================================================================
# HOW TO IMPLEMENT
====================================================================

## Step 1: Create a universal upload function

In a shared utility file (e.g., drive_utils.py or update existing upload code):

```python
import base64, json, urllib.request

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec"

DRIVE_FOLDERS = {
    "drafts": "1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5",
    "approved": "1rol_SQCWW9kLGedFwXuFvw61dN61qT7Z",
}

def upload_pdf_to_drive(pdf_bytes, filename, folder_key="drafts"):
    """Upload PDF to Drive. Returns file URL or None."""
    folder_id = DRIVE_FOLDERS.get(folder_key, DRIVE_FOLDERS.get("drafts", ""))
    if not folder_id:
        print(f"[DRIVE] No folder configured for '{folder_key}' — skipping upload")
        return None
    try:
        payload = json.dumps({
            "folder_id": folder_id,
            "filename": filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
        }).encode("utf-8")
        req = urllib.request.Request(
            APPS_SCRIPT_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        response = opener.open(req, timeout=30)
        result = json.loads(response.read().decode("utf-8"))
        if result.get("success"):
            return result.get("file_url", "")
        print(f"[DRIVE] Upload error: {result.get('error')}")
        return None
    except Exception as e:
        print(f"[DRIVE] Upload failed: {e}")
        return None
```

## Step 2: Replace ALL send_document calls

Find EVERY instance of:
```python
send_document(chat_id, document=..., filename=...)
```
or
```python
reply_document(document=..., filename=...)
```

Replace with:
```python
# Upload to Drive
drive_url = upload_pdf_to_drive(pdf_bytes, filename, folder_key="drafts")
if drive_url:
    kb = [[InlineKeyboardButton("📄 View PDF", url=drive_url)]]
    await message.reply_text("✅ Document ready!", reply_markup=InlineKeyboardMarkup(kb))
else:
    # Fallback ONLY if Drive upload fails
    await message.reply_document(document=io.BytesIO(pdf_bytes), filename=filename)
```

## Step 3: Search EVERY file for send_document

Files to check and fix:
- leave_request.py (PDF download handler)
- approval_handler.py (final approval PDF send)
- order_generator.py (Распоряжение)
- memo_handler.py (all stages)
- jd_handler.py (JD PDF)
- cert_handler.py (certificates)
- eval_handler.py (evaluation PDF)
- pdf_generator.py (if it sends directly)
- schedule_handler.py (schedule PDF)
- recruitment_handler.py (requisition form)
- quality_handler.py (inspection reports)
- safety_handler.py (incident reports)
- operations_handler.py (daily reports)
- ANY other file that generates or sends a PDF

Use this command to find all instances:
```
grep -rn "send_document\|reply_document" *.py
```

Replace EVERY SINGLE ONE.

====================================================================
# NOTIFICATIONS WITH DRIVE LINKS
====================================================================

When creating notifications (Notifications tab), include the Drive URL:

Example notification messages:
- "📝 Your memo MEMO-2026-0001 registered by HR. Registration: HR 03-001"
  + [📄 View PDF] button with Drive link
  
- "✅ HR Manager approved your memo MEMO-2026-0001"
  + [📄 View PDF] button with updated Drive link

- "✅ Director approved your memo MEMO-2026-0001"
  + [📄 View PDF] button with FINAL Drive link (approved folder)

The notification in the 🔔 Notifications menu should also show
the [📄 View PDF] button when the user opens the notification detail.

Store the Drive URL in the Notifications tab → add column if needed:
Notif_ID, Timestamp, Emp_Code, Type, Title, Message, Related_ID, 
Drive_Link, Read, Read_At

====================================================================
# ARCHIVE — ALWAYS DRIVE LINKS
====================================================================

In ALL archive views (memo archive, leave archive, etc.):
- Show [📄 View PDF] button with the Drive link
- NEVER send the file as a document
- If no Drive link stored: show "PDF not available" text

====================================================================
# ADD TO PROJECT_RULES.md
====================================================================

New fundamental rule:

5.9 ZERO FILES IN CHAT — all PDFs via Google Drive link.
    NEVER use send_document() to send PDFs in Telegram chat.
    ALWAYS: generate PDF → upload to Drive → send URL button.
    [📄 View PDF] opens in browser via InlineKeyboardButton(url=...).
    This applies to ALL document types, ALL stages, ALL roles.
    Fallback to send_document ONLY if Drive upload fails (network error).

====================================================================
# FINAL STEP
====================================================================

After ALL changes:
1. Run: grep -rn "send_document\|reply_document" *.py
   → Verify ZERO results (except the fallback in drive_utils.py)
2. Say "All done — ready to test"
3. Run: afplay /System/Library/Sounds/Hero.aiff
====================================================================
