# MASTER BUILD PROMPT — ROIN WORLD FZE COMPLETE SYSTEM
# Read PROJECT_HANDBOOK.md first for existing system context.
# Read all .py files in this folder before starting.
#
# RULES:
# 1. Build ONE phase at a time. After each phase say "Phase X done — ready to test" and STOP.
# 2. I test, say "next" → you build next phase.
# 3. Every screen: ↩️ Back + ↩️ Main Menu. NO EXCEPTIONS.
# 4. All AI features use Google Gemini (gemini_key.txt), NEVER Claude/Anthropic.
# 5. Python 3.14: asyncio.run(main()) pattern required.
# 6. Employee codes are NUMERIC (1007, not EMP-001).
# 7. Date format everywhere: DD/MM/YYYY.
# 8. No auto-notifications to approvers. Employees notified on approve/reject only.
# 9. When next step is running bot: python3 bot.py
# 10. Google Sheets rate limit: 60 reads/min — use SheetCache for batch reads.
# 11. Upload to Drive via Apps Script middleman (URL in config or jd_store.py).
# 12. All PDFs: company_logo.png header, fpdf2 library, auto-save to employee Drive folder.

====================================================================
# PHASE 1: FIX EXISTING ISSUES
====================================================================
Priority: Do this FIRST before any new features.

## 1A. Fix config.py
VALID_ROLES is wrong. Change to:
  ["Employee", "Supervisor", "Direct_Manager", "HR_Staff", "HR_Manager", "Director"]

VALID_LEAVE_TYPES change to:
  ["Paid", "Sick", "Emergency", "Unpaid", "Business_Trip",
   "Early_Departure", "Overtime_Planned", "Overtime_Emergency", "Missing_Punch"]

## 1B. Fix gemini_key.txt
Check if it's .rtf format. Must be plain text containing ONLY the API key.
If .rtf, recreate as plain text.

## 1C. Fix Gemini AI improvement
In jd_ai.py: verify the retry logic works. If AI returns identical text, retry with:
"Rewrite and significantly improve this text. Do NOT return the same text."
Test by calling improve_summary with a sample text.

## 1D. Verify attendance rules
In attendance_handler.py, verify ALL of these:
- Punch ALWAYS wins over schedule (employee works Friday → P, not OFF)
- Off_Type column support: Rotating, Friday, Friday_2ndSat (default if blank)
- Night shift: if Out < In, add 24hrs
- Multi-branch merging: earliest IN, latest OUT across branches
- Approved Missing_Punch → P (when built in Phase 2)
- Processing priority: leave → punch → schedule

## 1E. Back button audit
Check EVERY handler in bot.py, leave_request.py, approval_handler.py,
attendance_handler.py, jd_handler.py. Every screen must have ↩️ Back + ↩️ Main Menu.
Fix any that are missing.

====================================================================
# PHASE 2: MISSING REQUEST TYPES
====================================================================

## 2A. Missing Punch Request (🖐)
- New menu button for Employee, Supervisor, Direct_Manager, HR_Staff, HR_Manager
- Flow: Missing IN / Missing OUT / Both → date (today or yesterday only) → reason → summary → submit
- Request_Type: "Missing_Punch", prefix: MP-YYYY-NNNN
- Follows employee's Approval_Chain
- Add 🖐 category to Pending Approvals
- Attendance integration: approved Missing_Punch + partial punch → P
- PDF: "MISSING PUNCH APPROVAL CERTIFICATE"

## 2B. Early Departure Request (🚪)
- Add to leave type selection with 🚪 emoji
- Flow: date → time leaving (HH:MM) → reason (buttons: Pre-holiday/Personal/Medical/Other) → summary
- Bot calculates hours early = shift end - leave time
- MAX 2 PER MONTH enforced: count approved Early_Departure this month, reject if ≥2
- Approval: Manager → HR ONLY (no Director regardless of chain)
- Request_Type: "Early_Departure", prefix: ED-YYYY-NNNN
- Leave_Log: column 6 = hours, column 7 = leave time
- Attendance: approved + covers gap → P
- PDF: "EARLY DEPARTURE APPROVAL"

## 2C. Overtime Request (⏰🚨)
- Two types in leave selection: "⏰ Planned OT" and "🚨 Emergency OT"
- Planned: date must be ≥ tomorrow (24hr advance)
- Emergency: today or yesterday
- Flow: date → hours (1-4) → reason → summary
- LIMITS enforced by bot: max 4hrs/day, 12hrs/week, 40hrs/month
- If monthly total > 40hrs → add Director to approval chain
- Normal approval: Manager → HR
- Request_Type: "Overtime_Planned" or "Overtime_Emergency", prefix: OT-YYYY-NNNN
- Leave_Log: column 6 = hours, column 17 = OT rate (1.5), column 18 = hours × rate
- PDF: "OVERTIME APPROVAL"

====================================================================
# PHASE 3: SELF-SERVICE FEATURES
====================================================================

## 3A. My Profile (👤) — Complete
Employee sees:
- Personal: Full Name, Code, Department, Job Title, Nationality, Phone
- Contract: type, start date, expiry date, days remaining
  (🟢 if >60 days, 🟡 if 30-60, 🔴 if <30, ❌ if expired)
- Manager: name (lookup Manager_Code in Employee_DB)
- Leave Balance: available days
- Shift Hours: from Employee_DB
- Drive Folder: link button
Replace the "Coming soon" placeholder.

## 3B. My Attendance (🕐) — Detailed
- Read from attendance sheet (ID: 1_GEamKcub5g8zUXryHJ8PVHydA3hKSFV88hUt98fCTw)
- Current month tab name from config.py CURRENT_ATTENDANCE_TAB
- Count: P, A, V, S, U, B, OFF, H for current month
- Calculate attendance rate: P ÷ (P+A) × 100
- Show day-by-day for current month (compact: "1:P 2:P 3:A 4:OFF...")
- ↩️ Main Menu

## 3C. Help / FAQ (❓)
- Create FAQ tab in master sheet: Question_ID, Question, Answer, Category
- Pre-load 8 questions (Leave, Attendance, HR, General categories)
- Bot shows category buttons → tap → see FAQs in that category
- Each FAQ: question in bold, answer below
- ↩️ Back to categories + ↩️ Main Menu

## 3D. Certificate Requests (📜)
Add to employee menu or under My Profile:
- Employment Confirmation → instant PDF (AR + RU + EN, employee picks language)
- Salary Certificate → requires HR to enable per employee (salary sensitive)
- Experience Letter → requires HR approval
- PDF generated with company letterhead, saved to Drive
- Use pdf_generator.py or new cert_generator.py

## 3E. Contact HR (💬)
- Employee types message → stored in Contact_HR tab (Google Sheet)
- Columns: Msg_ID, Emp_Code, Timestamp, Message, Anonymous (Yes/No), HR_Response, Response_Date
- Anonymous option: checkbox before sending
- HR sees queue in their menu → can respond → employee gets reply
- ↩️ Main Menu

====================================================================
# PHASE 4: MANAGER FEATURES
====================================================================

## 4A. My Team View
Every manager (Direct_Manager, HR_Staff, HR_Manager) sees:
- Today: X present / X absent / X on leave
- Names of absent employees (tap to see detail)
- Pending requests: X waiting for my approval
- Team attendance rate this month: X%
- Team overtime this month: X hours
- Employees with contracts expiring within 30 days

## 4B. Smart Leave Approval Context
When manager opens a leave request to approve/reject, show:
- Employee's remaining balance: "Ahmed has 5 days. This uses 3."
- Same-day conflicts: "2 others from same department off that day"
- Recent absence history: "Ahmed was absent 4 times this month"
- This helps manager make informed decisions
- Add this context to pending_view in approval_handler.py

## 4C. Team Attendance View
Manager taps Team Attendance → sees:
- List of team members with today's status (P/A/V/OFF)
- This month summary per employee
- Tap employee → see their full monthly attendance

## 4D. Department Attendance Drill-Down (for Catering Director / senior managers)
- This week: daily rate per department
- This month: trend
- Top 5 most absent + top 5 most late employees
- Overtime usage by department

====================================================================
# PHASE 5: HR TOOLS
====================================================================

## 5A. All Leave Requests (📑)
For HR_Staff and HR_Manager:
- Summary: Pending Manager X, Pending HR X, Approved this month X, Rejected X
- Buttons: View Pending HR / View All This Month / Search by Employee
- Real data from Leave_Log, not placeholder
- HR_Manager can approve/reject from this view

## 5B. Employee Lookup (🔍)
For HR_Staff, HR_Manager, Director:
- Type employee code or part of name → search Employee_DB
- Show full profile + contract + leave balance + attendance rate
- Buttons: Leave History / Attendance / Documents
- ↩️ Back + ↩️ Main Menu

## 5C. Admin Functions (⚙️) — HR_Manager only
Menu with buttons (not slash commands):
- 👥 List Users → show all registered with role + last access
- 🔒 Lock User → enter code → lock account
- 🔓 Unlock User → enter code → unlock + reset attempts
- 🔑 Reset Password → enter code → generate new temp password
- Each action logged in Access_Log

## 5D. Generate Letters / Certificates (📝)
HR taps → picks type:
- Employment Confirmation (AR + RU + EN)
- Salary Certificate (HR must enable per employee)
- Experience Letter (on termination)
- Warning Letter (links to evaluation — placeholder until eval built)
- Contract Renewal Letter
- Each: PDF with company letterhead → Telegram + Drive

## 5E. Payroll Input Tab
Auto-calculated monthly from attendance + leave + overtime:
- Columns: Emp_Code, Full_Name, Department, Days_Present, Days_Absent,
  Days_Late, Total_Late_Minutes, Days_Leave_Paid, Days_Leave_Sick,
  Days_Leave_Unpaid, OT_Hours, OT_Rate, OT_Payment,
  Deduction_Absent, Deduction_Unpaid, Deduction_Late
- Populated by bot command or auto after attendance processing
- HR exports to payroll

## 5F. HR Daily Dashboard
When HR_Manager opens bot, show quick stats ABOVE the menu:
- Pending: X mine + X waiting Director
- Absent today (unexcused): X → tap to see list
- Documents expiring this week: X
- Contracts expiring this month: X
- New requests today: X
Then show normal menu below.

====================================================================
# PHASE 6: DOCUMENT & CONTRACT MANAGEMENT
====================================================================

## 6A. Document Expiry Tracking
New tab: Employee_Documents
Columns: Doc_ID, Emp_Code, Document_Type, Document_Number, Issue_Date,
         Expiry_Date, Days_Until_Expiry (formula), Status, Drive_Link,
         Last_Renewed, Renewed_By

Document types: work permit, residency visa, health certificate,
safety certification, first aid cert, professional license, passport, food handler cert

Alert schedule (via Apps Script or bot cron):
- 90 days: info to HR
- 60 days: action alert HR + employee
- 30 days: HR + employee + manager
- 14 days: urgent, daily alerts
- 7 days: critical, daily to all + Director
- 0 days: EXPIRED → immediate to Director + HR

HR can: view all docs, update expiry, upload new scan, mark renewed

## 6B. Contract Expiry Management
Uses Employee_DB columns: Contract_Expiry_Date, Probation_End_Date, Days_Until_Expiry

Alert schedule:
- 60 days: info to HR
- 30 days: manager recommendation required
- 14 days: urgent, daily to HR + Manager + Director
- 7 days: critical daily
- 0 days: EXPIRED immediate

Flow: alert → manager recommends (renew/terminate/amend) → HR reviews → Director decides
Decision logged in Contracts_Log tab
Auto-generate letter based on decision (renewal/termination/amendment) in AR + RU + EN

## 6C. Termination / Offboarding
When HR sets Status=Terminated:
- Bot access revoked immediately
- Auto-generate experience letter
- Archive documents
- Remove from active attendance
- Log in termination history
- Calculate: final settlement days (remaining leave balance × daily rate)

====================================================================
# PHASE 7: ANNOUNCEMENTS & COMMUNICATION
====================================================================

## 7A. Announcements System
HR creates announcement:
- Title + Body (one language)
- Auto-translate to AR + RU + EN via Gemini
- Select priority: Critical 🔴 / High 🟠 / Medium 🟡 / Normal 🟢
- Select target: All / Department / Role / Custom employee list
- Preview → Confirm → Sent

Announcements_Log tab: Ann_ID, Title, Body_AR, Body_RU, Body_EN,
Priority, Target, Total_Recipients, Total_Read, Read_Rate, Status

Read_Confirmations tab: Ann_ID, Emp_Code, Delivered_At, Read_At, Confirmed

Employee sees latest announcements in their menu.
Critical: must confirm within 1 hour. Escalate: 2hrs→manager, 4hrs→HR, EOD→Director.

## 7B. Contact HR Queue
Contact_HR tab: Msg_ID, Emp_Code, Timestamp, Message, Anonymous, HR_Response, Response_Date
Employee sends → HR sees queue → responds → employee notified.

====================================================================
# PHASE 8: REPORTING & DASHBOARDS
====================================================================

## 8A. Director Daily Morning Brief (auto at 8 AM)
One message with:
- Workforce: X present / X absent / X leave / X sick
- Yesterday attendance: X% with color indicator
- Pending MY decisions: X items
- Contracts expiring this month: X
- Expired documents: X
- OT hours this month: X
- Critical announcements unread >10%: X
Implementation: Google Apps Script scheduled trigger OR Python scheduler in bot

## 8B. Director Company Dashboard
When Director taps Company Overview:
- Total: 600 | Active: X | Leave: X | Terminated: X
- Department breakdown with counts
- This month: hires X, terminations X, turnover X%
- Attendance trend: last 3 months
- Leave usage by type
- OT hours + cost
- Expiring contracts with days remaining

## 8C. Monthly PDF Report (auto-generated 1st of month)
8 sections:
1. Executive Summary (3 highlights, 3 concerns)
2. Headcount Analysis
3. Attendance Analysis (rate, departments, worst 10)
4. Leave Analysis (by type, departments)
5. Contract Status (expiring, decisions pending)
6. Performance (placeholder until eval system)
7. Document Compliance (expired, expiring, rate %)
8. Overtime & Payroll Summary
PDF sent to Director + HR_Manager via Telegram + saved to Drive

## 8D. Director Alerts (critical only)
- Contract expired no decision → immediate
- Department attendance <90% → daily
- Employee absent 3+ consecutive days no leave → same day
- Document expired (legal risk) → immediate
- OT budget exceeded → weekly

## 8E. Kitchen Staffing View (for Catering Director)
Daily auto-message at 6 AM:
- Per branch: present / expected / absent / on leave
- Flag if any section <80% staffed
- List absent employees per section
- "Need X replacements in [branch] today"

## 8F. Shift Coverage Alert
When approving leave, check:
- How many from same department already off that day
- If below minimum staffing → warn approver
- "WARNING: Approving this would leave Egyptian Kitchen with only 60% staff on March 25"

====================================================================
# PHASE 9: PERFORMANCE EVALUATION (Task 11)
====================================================================

## 9A. Evaluation System
Scoring (100 points):
- Attendance rate: 20pts (auto from attendance data)
- Lateness: 10pts (auto: 0 late=10, 1-3=7, 4-7=4, 8+=0)
- Task completion: 20pts (placeholder=15 until Task 16 built)
- Overdue tasks: 10pts (placeholder=7 until Task 16)
- Leave pattern: 10pts (auto: clean=10, 2+ unplanned=5, flagged=0)
- Work quality: 10pts (manager rates 1-5 × 2)
- Communication: 8pts (manager 1-5 × 1.6)
- Initiative: 7pts (manager 1-5 × 1.4)
- SOP adherence: 5pts (manager 1-5 × 1)

Rating scale:
90-100: Excellent → promote/raise
75-89: Good → renew standard
60-74: Acceptable → renew with improvement plan
45-59: Weak → warning/extend probation
0-44: Unsatisfactory → termination review

Triggers: quarterly, contract renewal (30 days before), probation end (15 days before), on-demand

Manager flow: sees auto scores → rates 4 criteria via buttons → comment → submit
HR reviews → Director approves → PDF generated

Evaluations_Log tab: Eval_ID, Emp_Code, Period, Trigger, Auto_Score, Manager_Score,
Final_Score, Rating, Recommendation, Date, HR_Reviewed, Director_Approved, PDF_Link

====================================================================
# PHASE 10: OPERATIONS — WAREHOUSE (Task 18)
====================================================================

## 10A. Stock IN/OUT Logging
WAREHOUSE role in bot:
- Log Stock IN: item (from item list), quantity, unit, supplier, photo of delivery note
- Log Stock OUT: item, quantity, requesting department, photo of issue form
- Transfer: item, quantity, from WH-X to WH-Y, photo
- Waste/Damage: item, quantity, reason, supervisor sign-off photo
All transactions: Emp_Code + timestamp + photo saved to Drive

Stock_Transactions tab: TX_ID, Date, Type (IN/OUT/Transfer/Waste),
Item, Quantity, Unit, Warehouse, From_WH, To_WH, Supplier, Department,
Emp_Code, Photo_Link, Notes

## 10B. Live Inventory
Current_Balance tab: Item, Unit, WH1, WH2, WH3, Total, Min_Level, Status
Status auto-calculated: OK / LOW / CRITICAL / OUT
Updated after every transaction

## 10C. Low Stock Alerts
When item drops below Min_Level → notify Warehouse Manager + Supply Manager
Daily summary of all items below minimum
Weekly full inventory report

## 10D. Daily Stock Count
Warehouse keeper uploads count
Bot compares physical vs system
Discrepancy flagged + logged

====================================================================
# PHASE 11: OPERATIONS — VEHICLES (Task 19)
====================================================================

## 11A. Vehicle Request
Employee requests via bot: destination, purpose, time needed, passengers
Fleet/Transport Manager approves → assigns car + driver
Driver notified with trip details

Vehicles tab: Plate, Model, Status (Available/On_Trip/Maintenance/Out_of_Service)
Drivers tab: linked to Employee_DB, license info

## 11B. Trip Tracking
Driver logs: departure time, fuel level, odometer → trip timer starts
Overdue alerts: 15min→driver, 30min→manager, 60min→Director
Driver logs return: time, fuel, odometer, delay reason

Trip_Log tab: Trip_ID, Requesting_Emp, Car_Plate, Driver_Code,
Destination, Purpose, Est_Duration, Depart_Time, Return_Time,
Fuel_Used, Delay_Reason, Status

## 11C. Fuel Tracking
Fuel_Log tab: Date, Car_Plate, Driver, Odometer, Liters, Cost, Receipt_Photo
Monthly report per vehicle
Flag abnormal consumption

## 11D. Fleet Dashboard
Transport Manager sees:
- All 30 vehicles: status
- Today: scheduled / in progress / completed trips
- Available drivers

====================================================================
# PHASE 12: OPERATIONS — SUPPLY & PURCHASING
====================================================================

## 12A. Purchase Request Flow
Department submits material request → Supply Manager reviews → quotes → approves → orders
Track lifecycle: Requested → Quoted → Approved → Ordered → Delivered → Received

Purchase_Requests tab: PR_ID, Date, Dept, Item, Quantity, Requested_By,
Status, Supplier, Quoted_Price, Approved_By, PO_Number, Delivery_Date, Received

## 12B. Supplier Database
Suppliers tab: Supplier_ID, Name, Contact, Items, Rating, On_Time_Rate, Notes

## 12C. Budget Tracking
Monthly budget per department
Alert at 80% spent
Director approval if over budget

## 12D. Auto Purchase Alerts
Low stock → auto-notify Supply Manager with item + preferred supplier

====================================================================
# PHASE 13: BULK OPERATIONS
====================================================================

## 13A. Bulk Employee Import
HR fills Google Sheet template → bot reads + creates all records
Auto-generate passwords (Pass@CODE)
Auto-create Drive folders
/import command for HR_Manager only

====================================================================
# FINAL: MENU STRUCTURE (after all phases)
====================================================================

## EMPLOYEE
- Leave (Balance / Request / My Requests)
- 🖐 Missing Punch
- 🕐 My Attendance
- 👤 My Profile (info + contract + drive folder)
- 📜 Certificates (employment / salary / experience)
- 💬 Contact HR
- ❓ Help / FAQ

## SUPERVISOR
- Everything Employee has PLUS:
- 👥 Request for Employee
- 📂 Team Requests
- 👥 My Team View

## DIRECT_MANAGER
- Everything Supervisor has PLUS:
- 🔔 Pending Approvals
- 👥 Team Attendance
- 📋 Job Descriptions (Create / My JDs / Reviews)
- 📌 Assign Tasks (placeholder until Phase Task 16)

## HR_STAFF
- Everything Employee has PLUS:
- 👥 Request for Employee / Team Requests
- 📑 All Leave Requests
- 🔍 Employee Lookup
- 🕐 Attendance Overview (Upload ZKTeco / Process)
- 📋 Job Descriptions (Create / Reviews / Approvals)
- 📝 Generate Letters
- 📢 Announcements
- 💬 HR Messages Queue
- 📊 Document Expiry Dashboard
- 📄 Contract Expiry Dashboard

## HR_MANAGER
- Everything HR_Staff has PLUS:
- 🔔 Pending Approvals
- ⚙️ Admin Functions (list/lock/unlock/reset/import)
- 📊 HR Dashboard (stats at top)
- 💰 Payroll Input

## DIRECTOR
- 🔔 Pending Approvals (with batch approve)
- 🏢 Company Dashboard (live numbers)
- 🔍 Employee Lookup
- 📈 Reports (monthly PDF)
- 📋 Job Descriptions (final approval only)
- 📊 My Leave Balance / Request Leave
- ❓ Help

## WAREHOUSE (new role — add to bot)
- 📦 Stock IN
- 📤 Stock OUT
- 🔄 Transfer
- 🗑 Waste/Damage
- 📊 Inventory Balance
- 🕐 My Attendance
- 👤 My Profile
- ❓ Help

## DRIVER (new role — add to bot)
- 🚗 My Trips (assigned trips)
- 🚀 Start Trip (log departure)
- 🏁 End Trip (log return)
- ⛽ Log Fuel
- 🕐 My Attendance
- 👤 My Profile
- ❓ Help

## TRANSPORT_MANAGER (new role — add to bot)
- 🚗 Trip Requests (approve/assign)
- 📊 Fleet Status
- 🚗 All Trips Today
- ⛽ Fuel Report
- 👥 Driver Availability
- 🕐 My Attendance
- 👤 My Profile
- ❓ Help

## SUPPLY_MANAGER (new role — add to bot)
- 📋 Purchase Requests
- 📦 Low Stock Alerts
- 🏢 Supplier Database
- 💰 Budget Status
- 🕐 My Attendance
- 👤 My Profile
- ❓ Help

====================================================================
# ROLES UPDATE: 6 → 10
====================================================================
Add 4 new roles to config.py VALID_ROLES and bot.py:
Employee, Supervisor, Direct_Manager, HR_Staff, HR_Manager, Director,
Warehouse, Driver, Transport_Manager, Supply_Manager

Update User_Registry Bot_Role to accept these new values.

====================================================================
# BUILD ORDER
====================================================================
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 →
Phase 7 → Phase 8 → Phase 9 → Phase 10 → Phase 11 → Phase 12 → Phase 13

After EACH phase: "Phase X done — ready to test" → STOP.
I test → "next" → continue.

Do NOT skip phases. Do NOT batch phases.
START WITH PHASE 1.
