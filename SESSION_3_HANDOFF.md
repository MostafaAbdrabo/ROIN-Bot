# ROIN WORLD FZE — COMPLETE PROJECT HANDOFF
# ═══════════════════════════════════════════════
# Date: 21 March 2026
# From: Chat Session covering Sessions 2-3
# To: New chat session to continue development
#
# READ THIS ENTIRE DOCUMENT BEFORE RESPONDING.
# This is the COMPLETE state of the project.

====================================================================
# 1. COMPANY CONTEXT
====================================================================

Company: ROIN WORLD FZE
Location: El Dabaa Nuclear Power Plant project, Egypt
Operation: Catering company producing 30,000 meals/day
Workforce: 600+ employees (990 in database)
Languages: Arabic (Egyptian staff) + Russian (management) + English (admin)
User: Mostafa Abdrabo (Emp_Code: 1049, but testing as 1007)
User's role: HR Specialist — owns all HR systems, complete beginner in coding
5 Work Locations: Office, Russian Kitchen, Egyptian Kitchen, Pastry-Soup Kitchen, FoodTruck & Bakery

====================================================================
# 2. TECHNOLOGY STACK
====================================================================

- Google Sheets: all databases — one master workbook (68+ tabs, audited 23/03/2026)
- Google Drive: all documents and PDFs (organized by department folders + employee personal folders)
- Telegram Bot: ONE bot for ALL tasks, role-based access
- Python 3.11 on Railway (runtime.txt = python-3.11)
- Railway: deployed via GitHub auto-deploy (push to main → auto-deploy)
- fpdf2: PDF generation with DejaVu font for Cyrillic support
- pypdf: PDF merging for bulk export
- Google Gemini API: ALL AI features — model: gemini-2.5-pro-exp-03-25
- Google Apps Script: Drive upload + folder creation middleman
- bcrypt: password hashing (salt rounds = 12)
- gspread + google-auth: Google Sheets/Drive API access

====================================================================
# 3. CRITICAL IDs AND CREDENTIALS
====================================================================

Master Google Sheet ID: 1mqHdGhuiL36l6ByAVwFXsj95R3iCatS5V7Gg29jZOPQ
Master Google Sheet URL: https://docs.google.com/spreadsheets/d/1mqHdGhuiL36l6ByAVwFXsj95R3iCatS5V7Gg29jZOPQ
Attendance Google Sheet ID: 1_GEamKcub5g8zUXryHJ8PVHydA3hKSFV88hUt98fCTw
Service account: roin-hr-bot@roin-hr-bot.iam.gserviceaccount.com
Apps Script URL: https://script.google.com/macros/s/AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec
Employee Folders Parent: 14hfkfjC-9qu8KrvAhFZw8a5H1JN8FgXx

Drive Folders: (see config.py DRIVE_FOLDERS for full list — 40+ folder IDs)

GitHub Repo: https://github.com/MostafaAbdrabo/ROIN-Bot (private)
Railway: auto-deploys on push to main

Railway Environment Variables:
- BOT_TOKEN (Telegram bot token)
- SHEET_ID = 1mqHdGhuiL36l6ByAVwFXsj95R3iCatS5V7Gg29jZOPQ
- GOOGLE_CREDENTIALS (full JSON content of credentials.json)
- GEMINI_KEY (Google Gemini API key)

Employee codes: NUMERIC (1007, 1049, 2393, etc.) — NOT "EMP-001"
Test user: 1007 (Sokolov Aleksei) — role Bot_Manager — password Pass@1007
Mostafa's code: 1049 — HR Specialist

====================================================================
# 4. ALL 25 ROLES
====================================================================

Bot_Manager (Mostafa/Director — unlimited access to everything)
Director
HR_Manager
HR_Staff
Direct_Manager
Supervisor
Employee
Warehouse
Warehouse_Manager
Warehouse_Specialist
Store_Keeper
Driver
Transport_Manager
Supply_Manager
Supply_Specialist
Safety_Manager
Translation_Manager
Translator
Operations_Manager
Operations_Specialist
Operations_Coordinator
Quality_Manager
Quality_Specialist
Housing_Manager
Housing_Specialist

====================================================================
# 5. ALL FILES IN day1/ FOLDER
====================================================================

## Core Bot Files:
- bot.py — Main bot (v14+) with 25 role menus
- config.py — Dual mode (local/Railway), DRIVE_FOLDERS, VALID_ROLES
- leave_request.py — Leave system (Paid/Sick/Emergency/Unpaid/Business_Trip)
- approval_handler.py — Multi-stage approval chain + electronic signatures
- attendance_handler.py — ZKTeco upload + processing (multi-tab xlsx, calamine/openpyxl)
- missing_punch.py — Missing punch requests (MP-YYYY-NNNN)
- pdf_generator.py — Leave approval certificate PDF
- order_generator.py — Распоряжение (bilingual RU+EN leave order)

## Department Handlers:
- memo_handler.py — Служебная записка (formal memos with approval chain)
- jd_handler.py — Job description creation + AI + multi-stage review
- jd_ai.py — Gemini AI for JD text improvement
- jd_generator.py — JD PDF generator
- jd_store.py — JD Google Sheets CRUD
- eval_handler.py — Performance evaluation (70% auto + 30% manager)
- announcement_handler.py — Company announcements with read tracking
- schedule_handler.py — Monthly schedule plan (upload/view/review/PDF)
- warehouse_handler.py — Stock IN/OUT/Transfer/Waste + inventory
- vehicles_handler.py — Vehicle requests + trip tracking + driver compliance
- supply_handler.py — Purchase requests + supplier database
- safety_handler.py — Maintenance log + incident reports + training
- translation_handler.py — Translation requests + assignment + review
- operations_handler.py — Daily kitchen operations reports
- quality_handler.py — Incoming material inspections
- housing_handler.py — Apartments + assignments + maintenance
- recruitment_handler.py — Full hiring pipeline
- feedback_handler.py — Bot bug reports + suggestions

## HR Tools:
- hr_tools_handler.py — Employee lookup, admin functions, letters
- manager_handler.py — Team view, smart approval context
- cert_handler.py — Employment/salary/experience certificates
- contact_hr_handler.py — Employee → HR messaging queue
- doc_contract_handler.py — Document + contract expiry tracking
- report_handler.py — Director morning brief + monthly PDF report
- signature_handler.py — Electronic signature setup + management
- faq_handler.py — FAQ from Google Sheet
- bulk_import_handler.py — CSV bulk employee import

## Utilities:
- generate_hashes.py — bcrypt password generator for User_Registry
- generate_sample_jd.py — Sample JD PDF generator
- test_setup.py — Connection diagnostics

## Assets:
- company_logo.png — PDF header logo
- 1007_signature.png — Electronic signature for employee 1007 (M.Abdrabo)
- 1049_signature.png — Same signature for testing
- JD_Template.docx — Landscape Word template for JDs
- word_template.docx — Portrait Word template

## Config Files:
- credentials.json — Google service account key (LOCAL ONLY)
- bot_token.txt — Telegram bot token (LOCAL ONLY)
- sheet_id.txt — Current Google Sheet ID
- gemini_key.txt — Google Gemini API key
- requirements.txt — All Python dependencies
- Procfile — "worker: python3 bot.py"
- runtime.txt — "python-3.14.0a6"
- .gitignore — Excludes secrets

## Documentation:
- PROJECT_RULES.md — Universal rules for ALL projects (70+ rules)
- PROJECT_HANDBOOK.md — Full system specification
- BACK_BUTTON_RULE.md — Navigation rule
- SESSION_2_HANDOFF_PROMPT.txt — Previous session handoff
- MASTER_BUILD_PROMPT.md — 13-phase build plan
- FINAL_MASTER_PROMPT.md — Complete 16-section system spec
- SHEET_UPDATE_PROMPT.md — Tab merge instructions
- SIGNATURE_ORDER_PROMPT.md — Signature + Распоряжение spec
- MEMO_NOTIF_AI_PROMPT.md — Memo + notifications + AI writing
- MEMO_FORMAT_UPDATE.md — Exact memo PDF format
- RECRUITMENT_SYSTEM_PROMPT.md — Full hiring pipeline
- RECRUITMENT_FORM_UPDATE.md — Personnel requisition form format
- SCHEDULE_FEEDBACK_PROMPT.md — Monthly schedule + bot feedback
- ZERO_FILES_IN_CHAT.md — No files in chat rule
- PDF_DRIVE_SEARCH_PROMPT.md — Drive links + universal search
- UNIFIED_REQUESTS_PROMPT.md — Unified requests menu

====================================================================
# 6. GOOGLE SHEET TABS (41 tabs)
====================================================================

## Core HR:
- Employee_DB (990 employees, 34 columns including Work_Location, Signature_Link, Email)
- User_Registry (login credentials, 25 valid roles)
- Leave_Balance (entitlements per employee)
- Leave_Log (all leave/OT/ED/MP requests, 22+ columns)
- Holidays (16 Egyptian 2026 holidays)

## Documents:
- JD_Drafts (job descriptions with approval flow)
- Employee_Documents (document expiry tracking with auto-status formulas)
- Employee_History (MERGED: contracts + promotions + changes)
- Evaluations_Log (performance evaluations)

## Communication:
- Announcements (company announcements)
- Read_Tracking (announcement read confirmations)
- Contact_HR (employee → HR messages)
- FAQ (8 pre-loaded questions)
- Notifications (notification center storage)
- Bot_Feedback (bug reports + suggestions)

## Finance:
- Payroll_Input (monthly payroll calculations)
- Purchase_Requests (department purchase orders)

## Warehouse:
- Stock_Transactions (IN/OUT/Transfer/Waste)
- Current_Balance (live inventory with auto Total + Status formulas)

## Transport:
- Vehicles (fleet registry)
- Trip_Log (vehicle requests + tracking, 28 columns)
- Fuel_Log (fuel consumption)
- Driver_Compliance (MERGED: permits + safety lectures)

## Safety:
- Safety_Log (MERGED: maintenance + incidents)
- Training_Log (MERGED: safety lectures + courses)

## Other Departments:
- Translation_Log (translation requests)
- Operations_Reports (daily kitchen reports with auto Achievement_Rate)
- Quality_Inspection_Log (incoming inspections)
- Suppliers (supplier database)
- Memo_Log (formal memos with registration, 24 columns)
- Hiring_Requests (personnel requisitions, 29 columns)
- Job_Postings (recruitment postings)
- Candidates (applicant tracking)
- Onboarding_Checklist (new hire checklist)

## Planning:
- Monthly_Schedule (shift/location/leave plan per month, 31 day columns)
- Attendance_Actual (plan vs actual comparison)

## Housing:
- Apartments (apartment registry)
- Housing_Log (MERGED: assignments + requests + maintenance)

## System:
- Access_Log (security audit trail)
- Order_Counter (Распоряжение numbering)
- 📋 INDEX (table of contents + role reference)

## KEY SHEET FEATURES:
- VLOOKUP auto-fill: type Emp_Code → name + department appear automatically
- 14 tabs have VLOOKUP formulas — bot must write "" to those columns
- Dropdown validations on all categorical fields
- Auto-calculated formulas: Days_Until_Expiry, inventory Status, Achievement_Rate

====================================================================
# 7. WHAT IS FULLY BUILT AND WORKING
====================================================================

✅ Login (bcrypt + Telegram ID binding + account locking)
✅ 25 role-based menus
✅ Leave requests (5 types + approval chain + PDF)
✅ Missing Punch requests
✅ Business Trip (retroactive 2 days)
✅ Approval system (Manager → HR → Director chain)
✅ Electronic signatures (image + text fallback)
✅ Распоряжение PDF (bilingual RU+EN leave order)
✅ Leave approval certificate PDF
✅ Attendance (ZKTeco upload, multi-tab xlsx, process P/A/V/S/U/B/OFF/H)
✅ JD system (create + AI improve + HR review + Director approve + PDF)
✅ Memo system (submit + AI improve + HR register + HR Manager + Director + PDF)
✅ My Profile (basic info, drive folder, JD, performance, history)
✅ My Attendance (year → month → detail view)
✅ FAQ / Help
✅ Certificates (employment confirmation PDF in EN/RU/AR)
✅ Contact HR (messaging queue + anonymous option)
✅ Announcements (create + translate + priority + read tracking)
✅ Monthly Schedule (upload plan + view + review + approve + landscape PDF)
✅ Warehouse (stock IN/OUT/transfer/waste + inventory + low stock)
✅ Vehicles (request + assign + trip tracking + driver compliance)
✅ Supply (purchase requests + supplier database)
✅ Safety (maintenance + incidents + training)
✅ Translation (request + assign + review)
✅ Operations (daily reports)
✅ Quality (incoming inspections)
✅ Housing (apartments + assignments + maintenance)
✅ Recruitment (hiring requests + postings + candidates + interviews)
✅ Bot Feedback (bug reports + suggestions)
✅ Bulk Employee Import (/import CSV)
✅ Evaluation system (70% auto + 30% manager)
✅ Document/Contract expiry tracking
✅ Notification center (🔔 with unread count)
✅ Bot_Manager role (unlimited access)

====================================================================
# 8. WHAT WAS RECENTLY BUILT/CHANGED (latest tasks)
====================================================================

## Task 1: Bot_Manager + Monthly Schedule + Feedback
- Bot_Manager role with 16-category super-menu
- Monthly schedule upload/view/review/approve/PDF
- Bot feedback system (Bug/Suggestion/Question/Complaint)
- Work_Location column + 17 departments

## Task 2: Electronic Signatures + Распоряжение
- Signature setup (photo upload → Drive → embed in PDFs)
- Bilingual Распоряжение PDF generator
- All existing PDFs updated with signatures
- Approval flow captures signatures at each stage

## Task 3: Memo System + Notifications + AI Writing
- Служебная записка with full approval chain
- Registration numbering: HR [MM]-[NNN]
- AI writing assistant (unlimited iterations, custom instructions)
- Notification center with unread count
- DejaVu font for proper Cyrillic rendering

## Task 4: Recruitment System
- Personnel Requisition Form (exact company format, bilingual)
- Full hiring pipeline: request → posting → candidates → interview → offer → onboard
- AI job post generator for social media
- Candidate screening + interview feedback

====================================================================
# 9. PENDING / IN PROGRESS ISSUES
====================================================================

## CRITICAL: Zero Files in Chat Rule
RECENTLY SENT TO CLAUDE CODE but may not be fully implemented yet.
Rule: NEVER send PDF files in Telegram chat. Always:
1. Upload PDF to Google Drive
2. Send a [📄 View PDF] URL button that opens in browser
3. This applies to ALL document types, ALL stages, ALL roles
Check: grep -rn "send_document\|reply_document" *.py
If any remain (except fallback), they need to be replaced.

## CRITICAL: Unified Requests Menu
RECENTLY SENT TO CLAUDE CODE but may not be implemented yet.
Replace all separate request menu items with ONE "📋 Requests" menu:
- 📅 Upcoming Requests (future dates)
- 📜 Past Requests (past dates)
- 📂 Requests Archive (by month → by type or by submitter)
- ➕ New Request (all types in one place)

## PDF Drive Upload
Memo drafts go to: folder 1Z4ADgTWuqSaypOrNhv5Q0vkMyHrFokG5
Approved docs go to: folder 1rol_SQCWW9kLGedFwXuFvw61dN61qT7Z
Other document types: folder IDs not yet created (use drafts folder for now)
Both folders shared with service account as Editor.

## Back Button Fix
Every ↩️ Back must go to PREVIOUS menu, not Main Menu.
This needs checking across ALL handler files.

## Drive folder IDs for other doc types
Mostafa hasn't created Drive folders for: leave approvals, leave orders,
JDs, certificates, evaluations, etc. When he does, IDs go in config.py DRIVE_FOLDERS.

## Old Requests Missing Drive Links
Requests created before the Drive upload feature don't have PDF links.
Solution: /regenerate_pdfs command for Bot_Manager to backfill.

## Early Departure + Overtime
These request types were specified in prompts but need verification
that they're fully working (submission + approval + PDF + attendance integration).

## Self-Registration
Planned but not built: employee without password can create their own
on first bot login (instead of HR generating passwords).

## Railway Deployment
Currently running locally. Railway was set up in Session 1 but stopped.
Needs: set environment variables BOT_TOKEN, SHEET_ID, GOOGLE_CREDENTIALS, GEMINI_KEY.

====================================================================
# 10. FUNDAMENTAL PROJECT RULES (from PROJECT_RULES.md)
====================================================================

Read PROJECT_RULES.md for the full 70+ rules. Key ones:

1. NESTED MENUS — never flat lists. Menu → sub-menu → sub-sub-menu
2. BACK BUTTON on every screen (↩️ Back to parent + ↩️ Main Menu)
3. ↩️ Back goes to PREVIOUS menu, NOT main menu
4. NO auto-notifications to approvers — they check when ready
5. Employees notified on approve/reject
6. SINGLE SOURCE OF TRUTH — Employee_DB, VLOOKUP everywhere
7. VLOOKUP columns: write "" — never overwrite formulas
8. ALL AI uses Gemini, never Claude
9. AI improvement optional + unlimited iterations + custom instructions + manual edit
10. ALL PDFs via Drive link, NEVER send files in chat (rule 5.9)
11. Electronic signatures on all approved documents
12. DejaVu font for Russian/Arabic text
13. UNIFIED REQUESTS MENU — one place for all request types
14. Dropdowns on all categorical fields
15. Auto-generate IDs (PREFIX-YYYY-NNNN)
16. Rejection always requires a reason
17. PDF preview at every stage via Drive link
18. Sound alert when Claude Code finishes: afplay /System/Library/Sounds/Hero.aiff
19. Complete files only — never placeholders
20. Employee codes NUMERIC, dates DD/MM/YYYY

====================================================================
# 11. APPROVAL CHAINS
====================================================================

Two standard chains stored in Employee_DB column Approval_Chain:
- MGR_HR: Direct Manager → HR Manager → Done
- MGR_HR_DIR: Direct Manager → HR Manager → Director → Done

Special cases:
- Early Departure: Manager → HR only (no Director)
- Memo: Submitter → HR Staff registers → HR Manager → Director
- Hiring Request: Manager → HR → Catering Director (if kitchen) → Director
- Bot_Manager: can approve everything including own requests

====================================================================
# 12. ATTENDANCE SYSTEM DETAILS
====================================================================

- 4 ZKTeco branches: Russian Kitchen, Egyptian Kitchen, Bakery, Office
- Non-standard .xls format — user saves as .xlsx via Numbers, sends to bot
- Multi-tab support: one xlsx with 4 tabs, branch detected from tab name
- Processing: punch always wins over schedule
- Off_Type: Rotating (23/7), Friday, Friday_2ndSat
- Night shift: if Out < In, add 24hrs
- Separate attendance sheet (different Sheet ID)
- Row 6 = headers, Row 7+ = data, Col C = code, Col F = day 1

====================================================================
# 13. HOW TO WORK WITH MOSTAFA
====================================================================

- Complete beginner — zero coding experience
- Uses Mac with python3, pip3
- Uses VS Code with Claude Code extension
- Give ONE terminal command at a time
- Provide COMPLETE files — never ask to manually edit code
- If error pasted — fix immediately, no questions
- Default language: English (responds in English even when asked in Arabic)
- When next step is running bot: python3 bot.py
- MANDATORY: Every screen has ↩️ Back + ↩️ Main Menu
- Sound alert when done: afplay /System/Library/Sounds/Hero.aiff
- Test after every change — don't batch without testing

====================================================================
# 14. WHAT TO DO NEXT (priority order)
====================================================================

1. VERIFY: Zero files in chat rule is fully implemented
2. VERIFY: Unified requests menu is built and working
3. VERIFY: All Back buttons go to previous menu (not main)
4. VERIFY: Drive upload works for memos (both folders)
5. BUILD: /regenerate_pdfs command for old requests
6. VERIFY: Early Departure + Overtime fully working
7. BUILD: Self-registration (employee creates own password on first login)
8. TEST: All 25 role menus work correctly
9. DEPLOY: to Railway when ready
10. ONGOING: Mostafa will add more features and report bugs

====================================================================
# 15. STARTING THE BOT
====================================================================

```
cd ~/Desktop/ROIN_World/ROIN_System/day1
python3 bot.py
```

Login as 1007 (Bot_Manager): password Pass@1007
This account has unlimited access to test everything.

====================================================================
END OF HANDOFF — 21 March 2026
====================================================================
