# TASK 3: Memo System + Notifications + AI Writing + Signature Setup + Self-Approval
# Build the ENTIRE thing in one session non-stop.
# After ALL sections done: "All done — ready to test" → STOP.
#
# SAME RULES AS ALWAYS:
# - Every screen: ↩️ Back + ↩️ Main Menu
# - All AI uses Google Gemini (gemini_key.txt), NEVER Claude
# - Python 3.14: asyncio.run(main())
# - Dates DD/MM/YYYY
# - All PDFs: company_logo.png header, fpdf2, electronic signatures
# - VLOOKUP columns in Google Sheets: write "" (empty), never overwrite formulas
# - Back button on every screen. See BACK_BUTTON_RULE.md

====================================================================
# SECTION A: SIGNATURE SETUP FOR EMP 1049 + SELF-APPROVAL
====================================================================

## A1. Pre-load signature for employee 1049 (Mostafa Abdrabo)
File: 1049_signature.png is in the day1/ folder.
On bot startup, check if employee 1049 has Signature_Link in Employee_DB.
If empty, upload 1049_signature.png to Drive /Signatures/1049_signature.png
and save the link to Employee_DB Signature_Link column.

OR simpler: just hardcode in signature_handler.py that if emp_code == "1049"
and no Signature_Link exists, use the local file 1049_signature.png directly.

## A2. Self-Approval for Bot_Manager role
Currently the bot prevents users from approving their own requests.
Add exception: if user's Bot_Role == "Bot_Manager", they CAN:
- Submit a leave request for themselves
- Approve it themselves (all stages: Manager → HR → Director)
- Their signature is applied at each stage

In approval_handler.py, find where it checks "can this user approve this request"
and add: if approver role is Bot_Manager → always allowed, skip boundary checks.

Bot_Manager can also approve ANY request from ANY employee regardless of
Manager_Code or department boundaries.

## A3. Signature quality in PDFs
When embedding signature images in PDFs:
- Signature image should be at least 4cm wide × 1.5cm tall
- Place it clearly — not overlapping with text
- Below signature: "[Full Name]" in bold
- Below name: "DD/MM/YYYY HH:MM" in small italic
- Signature must be HIGH QUALITY — readable and professional

====================================================================
# SECTION B: MEMO / СЛУЖЕБНАЯ ЗАПИСКА SYSTEM
====================================================================

## B1. What Is It?
A formal internal memo that employees (mainly department managers) submit
to the Director for decisions. Bilingual: Russian + English.

Examples: salary increase request, disciplinary action, policy change,
equipment purchase justification, staffing request, etc.

## B2. Who Can Submit
These roles can submit memos:
- Bot_Manager, Director, HR_Manager, HR_Staff, Direct_Manager, Supervisor
- Any employee with special permission (future: add Memo_Access column)
- For now: Bot_Manager + Director + HR_Manager + HR_Staff + Direct_Manager + Supervisor

## B3. Memo Submission Flow

Step 1: Employee taps 📝 New Memo
Step 2: Select language:
  - 🇷🇺 Russian only
  - 🇬🇧 English only
  - 🇷🇺🇬🇧 Russian + English (both in one document)

Step 3: Enter Topic / Тема (short title)

Step 4: Enter memo body text (can be long — multi-message)
  - Employee types the full text
  - Bot shows: "Your text received. What would you like to do?"
  - Buttons:
    [✨ Improve with AI]
    [✍️ Edit manually]
    [✅ Text is good — continue]

Step 5 (if AI improve selected):
  - Bot sends text to Gemini for improvement
  - Shows BOTH: original vs improved
  - Buttons:
    [✅ Use improved version]
    [🔄 Try again with different style]
    [💬 Tell AI what to change] ← user types custom instruction
    [✍️ Edit manually instead]
    [↩️ Keep original]

Step 5b (if "Tell AI what to change"):
  - User types: "make it more formal" or "add numbers" or "shorter" etc.
  - Bot sends to Gemini with user's instruction
  - Shows result
  - Same buttons again (can iterate unlimited times)

Step 5c (if "Edit manually"):
  - Bot sends the FULL current text as a message
  - User copies, edits, and sends back the modified text
  - Back to Step 4 buttons

Step 6: Bot generates PDF PREVIEW (not uploaded to Drive yet)
  - Sends PDF in Telegram as a document
  - "📄 Here's your memo preview:"
  - Buttons:
    [✅ Submit to HR]
    [✍️ Edit text]
    [❌ Cancel]

Step 7: Submitted → goes to HR for review

## B4. HR Review Flow

HR_Staff or HR_Manager sees in their menu: 📝 Pending Memos

Opens a memo → sees full text + PDF preview
Options:
  [✅ Register & Forward] — memo is good, register it
  [📝 Request Changes] — type message to submitter explaining what to fix
  [❌ Reject] — with reason

If "Request Changes":
  - HR types the required changes
  - Submitter gets notification: "HR requested changes on your memo: [message]"
  - Submitter edits and resubmits (back to Step 4)
  - Memo status: Revision_Requested

If "Register & Forward":
  - HR assigns registration number: СЗ-YYYY-NNNN (Служебная Записка)
  - Registration date + time recorded
  - HR's electronic signature added to PDF
  - PDF regenerated with registration number + HR signature
  - Forwarded to HR_Manager for review

## B5. HR Manager Review
HR_Manager sees registered memo:
  [✅ Approve & Forward to Director]
  [📝 Send Back to HR]
  [❌ Reject]

If approved: HR_Manager signature added → forwarded to Director

## B6. Director Decision
Director sees memo with all signatures so far:
  [✅ Approve] — Director signs electronically
  [❌ Reject] — with reason

If approved:
  - Director's signature added to PDF
  - Final PDF generated with ALL signatures:
    1. Submitter signature (bottom)
    2. HR registration (registration number + HR signature)
    3. HR Manager signature
    4. Director signature (top, most prominent)
  - PDF auto-uploaded to Drive: /Memos/[YEAR]/[MONTH]/СЗ-YYYY-NNNN.pdf
  - Submitter notified: "Your memo СЗ-YYYY-NNNN has been approved by the Director"
  - PDF link saved in Memo_Log

## B7. Memo PDF Format

Page: A4 Portrait
Header: Company logo + address (same as all other documents)

Body (Russian + English version):

```
                СЛУЖЕБНАЯ ЗАПИСКА / INTERNAL MEMO
                        № СЗ-YYYY-NNNN
Дата / Date: DD/MM/YYYY
Кому / To: Director — [Director Name]
От / From: [Submitter Title] — [Submitter Name] ([Emp_Code])
Отдел / Department: [Department]

Тема / Topic: [TOPIC TITLE]

────────────────────────────────

[RUSSIAN TEXT - if selected]

────────────────────────────────

[ENGLISH TEXT - if selected]

────────────────────────────────

                                    [Submitter Signature]
                                    [Submitter Name]
                                    [Date]

Регистрация / Registration:
№ СЗ-YYYY-NNNN от DD/MM/YYYY HH:MM
                                    [HR Staff Signature]
                                    [HR Staff Name]

Согласовано / Reviewed:
                                    [HR Manager Signature]
                                    [HR Manager Name]
                                    [Date]

РЕШЕНИЕ / DECISION: УТВЕРЖДЕНО / APPROVED
                                    [Director Signature]
                                    [Director Name]
                                    [Date]

Verification: SIG-XXXXXXXX
```

If rejected, "DECISION: ОТКЛОНЕНО / REJECTED" + reason.

## B8. Memo Log (Google Sheet tab)

Add new tab: Memo_Log
Columns:
Memo_ID, Date, Emp_Code, Emp_Name(VLOOKUP), Department(VLOOKUP),
Language, Topic, Body_Text, Registration_Number, Registration_Date,
HR_Staff_Code, HR_Staff_Status, HR_Staff_Date, HR_Staff_Notes,
HR_Manager_Status, HR_Manager_Date,
Director_Status, Director_Date, Director_Notes,
Final_Status (Draft/Submitted/Revision_Requested/Registered/HR_Approved/Director_Approved/Rejected),
PDF_Preview_Link, PDF_Final_Link, Drive_Link

## B9. Memo Archive View

Add menu item for Bot_Manager, HR_Manager, Director:
📝 Memo Archive

Structure:
1. Select month: [March 2026] [February 2026] etc.
2. Inside month, TWO views:
   a) 👤 By Submitter → list of people who submitted → tap → see their memos
   b) 📋 By Topic → categories:
      - Salary (increase/decrease)
      - Disciplinary
      - Staffing
      - Equipment
      - Policy
      - Other
   Each memo in the list shows: СЗ number, date, topic, status, submitter name
   Tap → full detail + PDF download

Department managers see ONLY their own submitted memos in the archive.

## B10. Memo Topic Categories (for filtering)
When submitting, after entering topic text, select category:
- 💰 Salary (increase/decrease/bonus)
- ⚠️ Disciplinary (warning/penalty/deduction)
- 👥 Staffing (hire/transfer/role change)
- 🔧 Equipment (purchase/repair/replace)
- 📋 Policy (change/new/update)
- 📝 Other

====================================================================
# SECTION C: NOTIFICATION CENTER
====================================================================

## C1. What Is It?
Every employee has a 🔔 Notifications button in their main menu.
Shows all unread notifications. Badge count in menu.

## C2. Main Menu Change
Add to ALL role menus (first row, prominent position):
🔔 Notifications (X)
Where X = count of unread notifications. If 0, show just 🔔 Notifications.

When employee opens bot (after login), BEFORE showing menu, check:
If unread notifications > 0:
"🔔 You have X new notification(s)!"
Then show normal menu.

## C3. What Creates Notifications

| Event | Who Gets Notified | Message |
|-------|------------------|---------|
| Leave request submitted | Each approver in chain (when it's their turn) | "📋 New leave request from [Name] waiting for your approval" |
| Leave approved (each stage) | Employee | "✅ Your leave [ID] approved by [Role]" |
| Leave fully approved | Employee | "✅ Your leave [ID] is fully approved! PDF ready." |
| Leave rejected | Employee | "❌ Your leave [ID] rejected by [Role]. Reason: [text]" |
| Memo submitted | HR Staff | "📝 New memo from [Name]: [Topic]" |
| Memo changes requested | Submitter | "📝 HR requested changes on your memo: [message]" |
| Memo approved by Director | Submitter | "✅ Your memo [ID] approved by Director" |
| Memo rejected | Submitter | "❌ Your memo [ID] rejected. Reason: [text]" |
| New task assigned | Employee | "📌 New task from [Manager]: [Title]" |
| Document expiring | Employee + HR | "⚠️ Your [doc_type] expires in X days" |
| Contract expiring | Employee + Manager + HR | "📄 Contract expires in X days" |
| Announcement (critical) | All targets | "🔴 Critical announcement: [Title]" |
| Schedule published | Department employees | "📅 [Month] schedule published for [Dept]" |
| Missing punch reminder | Employee | "🖐 You have a missing punch for [date]" |
| Vehicle request approved | Employee | "🚗 Your vehicle request approved: [car] + [driver]" |
| Feedback response | Employee | "💬 Response to your ticket [ID]" |

## C4. Notification Storage

Add new tab: Notifications
Columns:
Notif_ID, Timestamp, Emp_Code, Type, Title, Message, Related_ID,
Read (Yes/No), Read_At

## C5. Notification Flow
1. System creates notification → writes to Notifications tab
2. User opens bot → bot counts unread for their Emp_Code
3. Menu shows "🔔 Notifications (3)" with count
4. User taps → sees list of unread (newest first)
5. Each notification: title + short message + timestamp
6. Tap one → see full detail + ↩️ Back
7. Mark as read automatically when opened
8. "Mark All as Read" button at top
9. "📜 View History" → shows last 50 read notifications

## C6. DO NOT send Telegram push messages
Notifications are ONLY visible inside the bot menu.
No auto-sending messages to chat. The user sees them when they open the bot.
This is consistent with our "no auto-notifications to approvers" rule.

EXCEPTION: Employee notifications (approval results) are ALSO sent as regular
Telegram messages (keep existing behavior). The notification center is
ADDITIONAL — it's a log they can review later.

====================================================================
# SECTION D: AI WRITING ASSISTANT — IMPROVED
====================================================================

## D1. Universal AI Text Improvement Flow
This applies EVERYWHERE the AI suggests improvements:
- Memo writing
- JD creation (summary, tasks, qualifications)
- Announcement creation
- Any future text creation feature

## D2. The Flow (same everywhere)

After user enters text, show:
```
📝 Your text:
"[their text displayed]"

What would you like to do?
[✨ Improve with AI]
[✍️ Edit manually]
[✅ Keep as is — continue]
```

If ✨ Improve with AI:
```
✨ AI Version:
"[improved text]"

📝 Your Original:
"[original text]"

[✅ Use AI version]
[🔄 Try different style]
[💬 Give AI specific instructions]
[✍️ Edit the AI version manually]
[↩️ Keep my original]
```

If 💬 Give AI specific instructions:
```
Type what you want the AI to change:
(e.g. "make it shorter", "add numbers", "more formal", "focus on cost savings")
```
User types instruction → AI applies it → shows result → same buttons again.
User can iterate UNLIMITED times until satisfied.

If ✍️ Edit manually (at any point):
- Bot sends the CURRENT text (original or AI version, whichever is active) as a plain message
- User copies it, edits, sends back
- Bot receives the edited text → back to the main choice buttons
- This way user can fix a single word or add a number without rewriting everything

## D3. Gemini Prompts for Different Contexts

For Memos:
"You are a professional workplace communication writer for ROIN WORLD FZE.
Improve this internal memo to be clear, professional, and persuasive.
Maintain the same meaning and key facts. Use formal business language.
Language: [Russian/English as specified].
Output ONLY the improved text."

For JDs (already exists in jd_ai.py — keep as is)

For Announcements:
"You are writing an official company announcement for ROIN WORLD FZE.
Make it clear, concise, and professional. Appropriate for all employees.
Language: [as specified]. Output ONLY the improved text."

For custom instructions from user:
"You are improving text for ROIN WORLD FZE internal documents.
Apply this specific change requested by the user: [USER INSTRUCTION]
Original text: [TEXT]
Output ONLY the modified text. Do not add explanations."

## D4. Implementation
Create or update: ai_writer.py (or expand jd_ai.py → rename to ai_helper.py)

Functions:
- async improve_text(text, context="memo", lang="EN") → (improved, error)
- async improve_with_instruction(text, instruction, lang="EN") → (improved, error)
- async translate_text(text, from_lang, to_lang) → (translated, error)

All use Gemini. All have retry logic (if identical, retry with stronger prompt).
All return (result, error_msg) tuple.

====================================================================
# SECTION E: GOOGLE SHEET UPDATES
====================================================================

## E1. New tab: Memo_Log
Columns: Memo_ID, Date, Emp_Code, Emp_Name, Department, Language, Topic,
Topic_Category, Body_Text, Registration_Number, Registration_Date,
HR_Staff_Code, HR_Staff_Status, HR_Staff_Date, HR_Staff_Notes,
HR_Manager_Status, HR_Manager_Date,
Director_Status, Director_Date, Director_Notes,
Final_Status, PDF_Preview_Link, PDF_Final_Link, Drive_Link

Emp_Name and Department: VLOOKUP from Emp_Code (leave as "" when writing)

## E2. New tab: Notifications
Columns: Notif_ID, Timestamp, Emp_Code, Type, Title, Message,
Related_ID, Read, Read_At

## E3. Memo_Log numbering
Registration numbers: СЗ-YYYY-NNNN (e.g. СЗ-2026-0001)
Auto-increment per year. Track via scanning existing Memo_Log entries.

====================================================================
# SECTION F: MENU UPDATES
====================================================================

## F1. Add to ALL role menus (prominent position, first row):
🔔 Notifications (X) — where X is unread count

## F2. Add 📝 Memo to these roles:
Bot_Manager, Director, HR_Manager, HR_Staff, Direct_Manager, Supervisor

Menu item: "📝 Memos"
Sub-menu:
- 📝 New Memo (submit)
- 📋 My Memos (my submitted memos)
- 📥 Pending Review (HR roles: memos waiting for review)
- 📂 Memo Archive (by month → by submitter or by topic)
- ↩️ Back

## F3. HR roles additionally see:
- 📝 Register Memo (assign registration number)
- 📋 All Memos (full list with filters)

## F4. Director sees:
- 📝 Memo Decisions (pending Director approval)
- 📂 Memo Archive (full access, all departments)

====================================================================
# SECTION G: DRIVE FOLDER STRUCTURE
====================================================================

Add: /Memos/[YEAR]/[MONTH]/СЗ-YYYY-NNNN_[EMP_CODE].pdf

====================================================================
# BUILD ORDER (all in one session)
====================================================================

A → B → C → D → E → F → G

Build everything. Register all handlers in bot.py.
After ALL sections: "All done — ready to test" → STOP.

START NOW.
====================================================================
