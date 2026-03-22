# ROIN WORLD FZE — COMPLETE PROJECT HANDBOOK
## For Claude Code: Read this before building anything.

====================================================================
# SECTION 1: PROJECT CONTEXT
====================================================================

Company: ROIN WORLD FZE
Location: El Dabaa Nuclear Power Plant project, Egypt
Operation: Catering company producing 30,000 meals/day
Workforce: 600 employees
Languages: Arabic (Egyptian staff) + Russian (management) + English (admin)
User: Mostafa — HR Specialist — complete beginner, zero coding experience

## Stack
- Google Sheets: all databases — one master workbook
- Google Drive: all documents and PDFs
- Telegram Bot: ONE bot for all tasks, role-based access
- Python 3.14 on Mac (asyncio.run pattern required)
- Railway free tier for deployment
- fpdf2: PDF generation
- Claude API: AI translation + JD generation (future)
- Google Apps Script: Drive upload middleman

## Critical IDs
- Master Google Sheet: 1-N3Ge3RZGf6ie9YNbYlur4sQOMVGQQ3rgG1lMMThpkk
- Attendance Google Sheet: 1_GEamKcub5g8zUXryHJ8PVHydA3hKSFV88hUt98fCTw
- Service account: roin-hr-bot@roin-hr-bot.iam.gserviceaccount.com
- Apps Script URL: https://script.google.com/macros/s/AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec

## Employee Codes
NUMERIC only: 1007, 1008, 2001, 2393, etc. NOT "EMP-001" format.

====================================================================
# SECTION 2: WHAT IS ALREADY BUILT AND WORKING
====================================================================

## Roles (6 total)
Employee, Supervisor, Direct_Manager, HR_Staff, HR_Manager, Director

## Features Working
1. Login: employee code + bcrypt password + Telegram ID binding
2. 6 role-based menus
3. Leave request (self): Paid, Sick, Emergency, Unpaid, Business_Trip
4. Leave request for employee (Supervisor/Manager/HR on behalf)
5. Categorized pending approvals with approve/reject
6. My Requests + Team Requests (Previous/Upcoming → detail → PDF)
7. PDF generation with company logo + Drive upload
8. Attendance: ZKTeco upload (.xls/.xlsx/.csv/.zip) → process → write P/A/V/S/U/B/OFF/H
9. Multi-tab .xlsx support (4 branches in 1 file)
10. Branch auto-detection (Russian Kitchen, Egyptian Kitchen, Bakery, Office)

## Approval Chains
- MGR_HR: Direct Manager → HR Manager → Done
- MGR_HR_DIR: Direct Manager → HR Manager → Director → Done
- Stored in Employee_DB column: Approval_Chain
- ALL leave types follow the employee's chain. No exceptions.

## Attendance Status Codes
P = Present, A = Absent, V = Vacation (Paid/Emergency), S = Sick
U = Unpaid, B = Business Trip, OFF = Day off, H = Holiday

## Leave_Log Column Map (0-indexed)
 0: Request_ID (LVE-YYYY-NNNN)
 1: Emp_Code
 2: Request_Type (Paid/Sick/Emergency/Unpaid/Business_Trip)
 3: Start_Date
 4: End_Date
 5: Days_Requested
 6: Hours (for early departure / overtime)
 7: Leave_Early_Time (for early departure)
 8: Reason
 9: Manager_Status (Pending/Approved/Rejected/NA)
10: Manager_Date
11: HR_Status
12: HR_Date
13: Director_Status
14: Director_Date
15: Final_Status (Pending/Approved/Rejected)
16: Rejection_Reason
17: OT_Rate (for overtime: 1.5x or 2x)
18: OT_Equivalent_Hours (OT hours × rate)
19: PDF_Generated (Yes/No)
20: PDF_Drive_Link
21: Created_At (DD/MM/YYYY HH:MM)

## Attendance Sheet Layout
- Row 6 = day number headers (1, 2, 3... 31)
- Row 7 onward = employee data
- Column C (index 3) = employee code
- Column F (index 6) = day 1, G = day 2, etc.

## Smart Day Calculation (for leave)
Excludes: Fridays, 2nd Saturday of month (if employee eligible), official holidays from Holidays tab.

## Back Button Rule — MANDATORY
Every screen must have ↩️ Back + ↩️ Main Menu. No exceptions.
See BACK_BUTTON_RULE.md. This applies to EVERY new feature.

## No Auto-Notifications on Submit
Managers/HR/Director are NOT interrupted when requests come in.
They check Pending Approvals from their menu when ready.
Employees ARE notified when their request is approved or rejected.

====================================================================
# SECTION 3: GOOGLE SHEET TABS (Master Workbook)
====================================================================

Employee_DB — 26+ columns:
  Emp_Code, Full_Name, National_ID, Date_of_Birth, Nationality, Phone,
  Department, Job_Title, Job_Grade, Hire_Date, Contract_Type,
  Contract_Start_Date, Contract_Expiry_Date, Probation_End_Date,
  Contract_Status, Days_Until_Expiry, Manager_Code, Telegram_ID,
  Bot_Password_Hash, Bot_Role, Preferred_Language, Annual_Leave_Balance,
  Status, Drive_Folder_Link, Has_Expired_Docs, Notes,
  Saturday_Type ("2nd_Saturday_Off" or "No_2nd_Saturday"),
  Approval_Chain ("MGR_HR" or "MGR_HR_DIR"),
  Supervisor_Code, Shift_Hours (9, 10, 12, etc.),
  Off_Type ("Rotating" or "Friday" or "Friday_2ndSat")

Leave_Balance — per employee leave entitlements and usage
Leave_Log — all leave/request records (22 columns, see map above)
Holidays — Date, Name, Type (2026 Egyptian official holidays)
User_Registry — Emp_Code, Telegram_ID, Password_Hash, Bot_Role, Registration_Date, Status, Failed_Attempts, Last_Access
Access_Log — all bot access attempts

## Attendance Workbook (separate sheet)
Raw_ZKT tab — Code, Date, Clock_In, Clock_Out, In_Branch, Out_Branch
Monthly tabs (e.g. "Copy of 3-K") — employee attendance grid

====================================================================
# SECTION 4: REMAINING TASKS TO BUILD
====================================================================

## TASK A: Off_Type Column (5 minutes)
STATUS: Code already handles it. Just add the column to Employee_DB.
- Column name: Off_Type
- Values: Rotating, Friday, Friday_2ndSat
- Default if blank: Friday_2ndSat
- Logic in attendance_handler.py load_off_types() already works
- NO CODE CHANGES NEEDED — just verify it works after column is added

## TASK B: Missing Punch Request
Employee forgot to punch in or out. They submit this request.

RULES:
- Can only be submitted for yesterday or today (max 1 day retroactive)
- Request_Type in Leave_Log: "Missing_Punch"
- Request_ID prefix: MP-YYYY-NNNN
- Follows the employee's Approval_Chain (MGR_HR or MGR_HR_DIR)
- Employee must specify: date, whether IN or OUT was missing, reason
- If fully approved: attendance_handler should treat this day as P
  (check Missing_Punch approved requests when processing attendance)
- If not approved or not submitted: stays A

BOT FLOW:
1. Employee menu → new button "🖐 Missing Punch"
2. Select: Missing IN / Missing OUT / Both
3. Enter date (today or yesterday only)
4. Enter reason
5. Summary → Submit
6. Goes to Pending Approvals

ATTENDANCE INTEGRATION:
- In process_attendance(), after checking punch data:
  If employee has partial punch (IN only or OUT only) AND has an approved
  Missing_Punch request for that date → status = P
- Add to Leave_Log with Request_Type = "Missing_Punch"
- Column 6 (Hours) = empty
- Column 7 (Leave_Early_Time) = empty

APPROVAL DISPLAY:
- In Pending Approvals, add "Missing Punch" category with emoji 🖐
- TYPE_EMOJI: {"Missing_Punch": "🖐"}

## TASK C: Early Departure Request
Employee needs to leave before shift ends.

RULES:
- Max 2 per month (bot enforces — count approved Early_Departure in current month)
- Approval chain: Manager → HR ONLY (no Director regardless of employee's chain)
- Employee specifies: date, time leaving, reason
- Bot auto-calculates hours leaving early: official end time - leave time
- Request_Type: "Early_Departure"
- Request_ID prefix: ED-YYYY-NNNN
- Attendance result when approved: P (covers the gap)
- Reason options (bot buttons): Pre-holiday / Personal / Medical / Other

BOT FLOW:
1. Employee menu → new button (add to Request Leave type selection)
2. Or: separate menu item "🚪 Early Departure"
3. Enter date (today or future)
4. Enter time leaving (HH:MM)
5. Select reason from buttons
6. Summary shows: hours leaving early, remaining count this month
7. Submit → Pending Approvals (Manager → HR only)

ATTENDANCE INTEGRATION:
- If employee's punch hours are short AND they have approved Early_Departure
  for that date → check if the gap is covered by the approved early departure hours
- If covered → P
- Column 6 (Hours) = hours leaving early
- Column 7 (Leave_Early_Time) = time employee is leaving

MONTHLY LIMIT ENFORCEMENT:
- Before allowing submission: count approved Early_Departure requests
  for this employee in current month
- If already 2: reject with message "Maximum 2 early departures per month reached"

## TASK D: Overtime Request
Two types: Planned and Emergency.

RULES:
- Planned OT: must be submitted 24 hours in advance
- Emergency OT: submitted same day or retroactively (next day)
- Approval: Manager → HR (no Director, unless monthly limit exceeded)
- Max 4 hours per day
- Max 12 hours per week
- Max 40 hours per month
- If monthly limit exceeded: Director approval also required
- OT rate: 1.5x (configurable in config.py)
- Request_Type: "Overtime_Planned" or "Overtime_Emergency"
- Request_ID prefix: OT-YYYY-NNNN

BOT FLOW:
1. Add to Request Leave type selection: "⏰ Planned OT" and "🚨 Emergency OT"
2. Enter date
3. Enter OT hours (1-4)
4. Enter reason
5. Summary shows: OT hours, rate, equivalent hours, month total so far
6. Submit → Pending Approvals

LEAVE_LOG COLUMNS USED:
- Column 6 (Hours) = OT hours requested
- Column 17 (OT_Rate) = 1.5 or 2.0
- Column 18 (OT_Equivalent_Hours) = Hours × Rate

ATTENDANCE INTEGRATION:
- Not needed — OT doesn't change P/A status
- OT data feeds into Payroll_Input tab (future)

## TASK E: Contract & Probation Expiry Alerts (Task 09)
Automated alerts when contracts or probation periods are expiring.

RULES:
- Alert timeline: 60, 30, 14, 7, 3, 0 days before expiry
- 60 days: info alert to HR
- 30 days: action alert — manager recommendation required
- 14 days: urgent — daily alerts to HR + Manager + Director
- 7 days: critical — daily to all parties
- 0 days: EXPIRED — immediate critical alert
- Uses Employee_DB columns: Contract_Expiry_Date, Probation_End_Date
- Auto-calculated: Days_Until_Expiry = Expiry - TODAY()
- Alerts sent via Telegram to HR_Manager and Director
- When decision is logged, all alerts stop for that employee

IMPLEMENTATION:
- Google Apps Script runs daily (e.g. 8 AM)
- Script checks Employee_DB for approaching expiries
- Sends Telegram messages via bot API
- OR: bot command /expiry_check that HR runs manually
- Logs to Contracts_Log tab

CONTRACTS_LOG TAB:
  Log_ID, Emp_Code, Event_Type, Decision, Decision_Date,
  Approved_By, Manager_Recommendation, Eval_Score,
  Old_Expiry_Date, New_Expiry_Date, Letter_Drive_Link

## TASK F: Document Expiry Tracking (Task 10)
Track employee documents (work permits, visas, health certs, etc.)

RULES:
- Same alert timeline as contracts: 90, 60, 30, 14, 7, 3, 0 days
- Documents tracked: work permit, residency visa, health certificate,
  safety certification, first aid cert, professional license, passport, food handler cert
- Employee_Documents tab in master sheet

EMPLOYEE_DOCUMENTS TAB:
  Doc_ID, Emp_Code, Document_Type, Document_Number, Issue_Date,
  Expiry_Date, Days_Until_Expiry, Status, Drive_Link, Last_Renewed, Renewed_By

IMPLEMENTATION:
- Same Apps Script as Task E, or combined
- Bot command for HR: /doc_expiry or menu item
- HR can update: upload new scan, set new expiry date

## TASK G: Performance Evaluation (Task 11)
70% auto-scored from system data + 30% manager input.

SCORING:
- Attendance rate: 20 points (Present days ÷ Working days × 20)
- Lateness frequency: 10 points (0 late=10, 1-3=7, 4-7=4, 8+=0)
- Task completion rate: 20 points (requires Task 16 — skip for now, use placeholder)
- Overdue task rate: 10 points (requires Task 16 — skip for now)
- Leave abuse pattern: 10 points (No issues=10, 2+ unplanned=5, HR flagged=0)
- Work quality (manager input 1-5): 10 points (Score × 2)
- Communication (manager input 1-5): 8 points (Score × 1.6)
- Initiative (manager input 1-5): 7 points (Score × 1.4)
- SOP adherence (manager input 1-5): 5 points (Score × 1)

RATING SCALE:
- 90-100: Excellent (ممتاز) — Promote/Salary increase
- 75-89: Good (جيد جداً) — Renew standard terms
- 60-74: Acceptable (مقبول) — Renew with improvement plan
- 45-59: Weak (ضعيف) — Extend probation / Warning
- 0-44: Unsatisfactory (غير مقبول) — Termination review

TRIGGERS:
- Quarterly: every 3 months, all managers get evaluation prompts
- Event: probation end within 15 days, contract expiry within 30 days
- On-demand: HR/Director triggers via /evaluate EMP-CODE

EVALUATIONS_LOG TAB:
  Eval_ID, Emp_Code, Period, Trigger_Type, Auto_Score, Manager_Score,
  Final_Score, Rating, Recommendation, Eval_Date, HR_Reviewed,
  Director_Approved, Report_Drive_Link, Manager_Comments

BOT FLOW FOR MANAGER:
1. Bot sends evaluation prompt (or manager opens from menu)
2. Shows auto-calculated scores (attendance, lateness, leave pattern)
3. Manager rates 4 criteria (1-5 each) via buttons
4. Adds optional comment
5. Submit → HR reviews → Director approves
6. PDF report generated

## TASK H: Translation Bot (Task 12)
Real-time AR ↔ RU ↔ EN translation using Claude API.

RULES:
- All 6 directions: AR→RU, RU→AR, AR→EN, EN→AR, RU→EN, EN→RU
- Company glossary locks specific terms (200+ terms)
- Cost: ~$0.02 per message
- Translation_Glossary tab has: Arabic, Russian, English, Category columns

BOT FLOW:
1. Employee sends message to bot
2. Bot detects source language
3. Shows buttons: "Translate to Arabic" / "Translate to Russian" / "Translate to English"
4. Calls Claude API with glossary-aware system prompt
5. Returns translation

CLAUDE API SYSTEM PROMPT:
"You are a professional workplace translator for a Russian catering company in Egypt.
Translate {source_lang} → {target_lang} using formal register.
This is official workplace communication.
The following terms MUST appear EXACTLY as given: {glossary_matches}
Translate only — no explanations, no preamble."

TRANSLATION_LOG TAB:
  Log_ID, Timestamp, Emp_Code, Department, Source_Language,
  Target_Language, Word_Count, Glossary_Terms_Used, Status

## TASK I: Self-Service Bot (Task 13)
Employee access to own data + certificate PDFs.

MENU STRUCTURE:
[1] My Information → profile summary, docs status, eval history
[2] Leave Services → balance, request, status, cancel pending
[3] Attendance & Payroll → this month summary, lateness, 6-month history
[4] Documents & Certificates → employment letter PDF, salary cert PDF, experience letter PDF
[5] Company Announcements → latest 5, holiday calendar
[6] FAQ → 20 pre-loaded questions from FAQ tab
[7] Contact HR → message HR, report issue (anonymous option), book appointment

PDF CERTIFICATES:
- Employment confirmation: AR + RU + EN, optional HR review
- Salary certificate: AR + RU + EN, requires HR to enable per employee
- Experience letter: AR + RU + EN, requires HR approval

FAQ TAB:
  Question, Answer_AR, Answer_RU, Answer_EN
  HR edits directly in Google Sheet, bot pulls dynamically

## TASK J: Company Announcements (Task 14)
Official company communications with read tracking.

PRIORITY LEVELS:
- Critical (🔴): confirm within 1 hour, escalate if unread
- High (🟠): confirm within 24 hours
- Medium (🟡): optional confirmation
- Normal (🟢): no confirmation needed
- HR Notice (🔵): confirm within 48 hours

BOT FLOW FOR HR:
1. HR → Announcements menu → New Announcement
2. Type title + body in one language
3. Bot auto-translates to all 3 languages via Task 12 engine
4. Select priority + target audience (All / Department / Role / Custom)
5. Confirm → sent to all recipients

ANNOUNCEMENTS_LOG TAB:
  Ann_ID, Title, Body_AR, Body_RU, Body_EN, Priority, Target,
  Total_Recipients, Total_Read, Read_Rate, Confirmation_Required, Status

READ_CONFIRMATIONS TAB:
  Ann_ID, Emp_Code, Delivered_At, Read_At, Confirmed

ESCALATION (Critical only):
- 2 hours unread → manager notified
- 4 hours → HR notified
- End of day → Director notified

## TASK K: HR Dashboard & Reports (Task 15)
Automated daily brief + weekly summary + monthly PDF report.

DAILY BRIEF (8 AM via Telegram):
- Workforce today: active, on leave, absent, sick
- Yesterday attendance: present %, late count, worst department
- Action needed: expiring contracts, pending decisions
- Document alerts: anything expiring within 14 days

MONTHLY PDF (auto-generated 1st of each month):
8 sections: Executive Summary, Headcount, Attendance Analysis,
Leave Analysis, Contract Status, Performance Overview,
Document Compliance, Payroll Input Summary

KPIs:
- Attendance rate target: ≥ 95% (alert if below 92%)
- Unexcused absence: ≤ 2% (alert if above 3%)
- Late arrival: ≤ 5% (alert if above 8%)
- Contract renewal: 100% before expiry
- Document compliance: 100%

## TASK L: Task Management (Task 16) — FUTURE
Department task assignment and tracking. Build after all HR tasks.

## TASK M: SOP Documentation (Task 17) — FUTURE
Standard operating procedures library. Build after all HR tasks.

## TASK N: Warehouse Management (Task 18) — FUTURE
3 warehouses, stock IN/OUT, photo documentation. Build after HR tasks.

## TASK O: Vehicle Management (Task 19) — FUTURE
30 vehicles, trip logging, fuel tracking. Build after HR tasks.

## TASK P: Deploy to Railway
- Railway project already exists from Session 1
- runtime.txt: python-3.14.0a6
- Procfile: worker: python3 bot.py
- Environment variables needed: BOT_TOKEN, SHEET_ID, GOOGLE_CREDENTIALS
- Currently running locally — deploy after all core features tested

====================================================================
# SECTION 5: RULES THAT APPLY TO EVERYTHING
====================================================================

## Back Button Rule
Every screen: ↩️ Back + ↩️ Main Menu. See BACK_BUTTON_RULE.md.

## No Auto-Notifications
Managers check Pending Approvals when ready. Only employees get notified.

## Access Boundaries
- Supervisor: self + employees where Supervisor_Code = their code
- Manager: self + employees where Manager_Code = their code
- HR_Staff: same as HR_Manager but no Admin Functions or Pending Approvals
- Director: self for requests; sees only Manager+HR approved items in Pending

## PDF Generation
- Library: fpdf2 with company_logo.png
- Filename: EmpCode-type-RequestID-StartDate.pdf
- Auto-upload to employee's Drive folder via Apps Script
- Available after request is fully Approved or Rejected

## Google Sheets Rate Limit
60 reads/min. Use SheetCache class (see approval_handler.py) for batch reads.

## Python 3.14 Specifics
- asyncio.run(main()) pattern required
- app.run_polling() does NOT work
- Ctrl+C traceback is normal

## Sick Photos
- Stored in bot_data memory (lost on restart)
- Auto-appear when approver opens sick request
- Auto-delete when navigating away

## Drive Upload
- Service accounts CANNOT upload to free Gmail Drive
- Solution: Apps Script middleman (URL in Section 1)
- Bot sends PDF as base64 → Apps Script uploads to Drive folder

====================================================================
# SECTION 6: MENU STRUCTURE PER ROLE (CURRENT + PLANNED)
====================================================================

## Employee
📊 My Leave Balance | ✈️ Request Leave
🖐 Missing Punch (NEW)
📋 My Requests
🕐 My Attendance | 👤 My Profile
❓ Help

## Supervisor
📊 My Leave Balance | ✈️ Request Leave
🖐 Missing Punch (NEW)
👥 Request for Employee | 📋 My Requests
📂 Team Requests
🕐 My Attendance | 👤 My Profile
❓ Help

## Direct_Manager
📊 My Leave Balance | ✈️ Request Leave
🖐 Missing Punch (NEW)
👥 Request for Employee | 📋 My Requests
🔔 Pending Approvals | 📂 Team Requests
🕐 Team Attendance | 📌 Assign Tasks
👤 My Profile | ❓ Help

## HR_Staff
📊 My Leave Balance | ✈️ Request Leave
🖐 Missing Punch (NEW)
👥 Request for Employee | 📋 My Requests
📂 Team Requests
📑 All Leave Requests | 🔍 Employee Lookup
🕐 Attendance Overview | 📝 Generate Letters
📢 Announcements
👤 My Profile | ❓ Help

## HR_Manager
📊 My Leave Balance | ✈️ Request Leave
🖐 Missing Punch (NEW)
👥 Request for Employee | 📋 My Requests
🔔 Pending Approvals | 📂 Team Requests
📑 All Leave Requests | 🔍 Employee Lookup
🕐 Attendance Overview | 📝 Generate Letters
📢 Announcements | ⚙️ Admin Functions
👤 My Profile | ❓ Help

## Director
📊 My Leave Balance | ✈️ Request Leave
🔔 Pending Approvals | 📋 My Requests
🏢 Company Overview | 🔍 Employee Lookup
📈 Reports | ❓ Help

====================================================================
# SECTION 7: BUILD ORDER (DO THESE IN THIS EXACT SEQUENCE)
====================================================================

1. TASK A: Off_Type column — verify attendance works with it
2. TASK B: Missing Punch request
3. TASK C: Early Departure request
4. TASK D: Overtime request
5. TASK E: Contract & document expiry alerts (Tasks 09+10)
6. TASK G: Performance evaluation (Task 11)
7. TASK H: Translation bot (Task 12) — needs Claude API key
8. TASK I+J: Self-service + Announcements (Tasks 13+14)
9. TASK K: HR Dashboard & Reports (Task 15)
10. TASK P: Deploy to Railway
11. Future: Tasks 16-19 (operations)

====================================================================
# SECTION 8: HOW TO WORK WITH MOSTAFA
====================================================================

- Complete beginner — explain every step
- Uses Mac with python3, pip3
- Uses VS Code with Claude Code
- Provide COMPLETE files — never ask to manually edit code
- If error is pasted, fix it immediately
- Default language: English
- When the next step is running the bot: python3 bot.py
- MANDATORY: Every screen has ↩️ Back + ↩️ Main Menu
- Test after every change — don't batch multiple features without testing

====================================================================
END OF HANDBOOK
====================================================================
