# FINAL MASTER PROMPT — ROIN WORLD FZE COMPLETE SYSTEM
# ═══════════════════════════════════════════════════════
# Read PROJECT_HANDBOOK.md and ALL .py files first.
# Build the ENTIRE system. Work through sections in order.
# After EACH section: "Section X done — ready to test" → STOP → I say "next"
#
# UNIVERSAL RULES (apply to EVERYTHING):
# - Every screen: ↩️ Back + ↩️ Main Menu. NO EXCEPTIONS.
# - All AI features use Google Gemini (gemini_key.txt), NEVER Claude.
# - Python 3.14: asyncio.run(main()) pattern.
# - Employee codes are NUMERIC (1007, not EMP-001).
# - Date format: DD/MM/YYYY everywhere.
# - No auto-notifications to approvers. Employees notified on approve/reject only.
# - All PDFs: company_logo.png header, fpdf2, auto-save to Drive via Apps Script.
# - Google Sheets rate limit: 60 reads/min — batch reads.
# - When next step is running bot: python3 bot.py
# - Back button rule: see BACK_BUTTON_RULE.md

====================================================================
# SECTION 1: FIX ALL EXISTING GAPS
====================================================================

## 1A. Eliminate ALL "Coming soon" placeholders
Check menu_catch in bot.py. Every item listed there must have a REAL handler.
If a handler exists but menu_catch catches it first, reorder handlers.
Remove ALL "Coming soon" text from the entire codebase.

Specifically fix these profile sub-pages:
- profile_jd → show employee's latest approved JD from JD_Drafts tab
- profile_perf → show latest evaluation from Evaluations_Log tab (or "No evaluations yet")
- profile_history → show from Promotions_Log (or "No history yet")

## 1B. Early Departure Request (🚪)
NOT YET BUILT. Build it now:
- Add to leave type selection: "🚪 Early Departure"
- Flow: date → time leaving (HH:MM) → reason buttons (Pre-holiday/Personal/Medical/Other)
- Bot calculates hours early = shift end time - leave time
- MAX 2 PER MONTH enforced (count approved Early_Departure this month, reject if ≥2)
- Approval: Manager → HR ONLY (no Director regardless of chain)
- Request_Type: "Early_Departure", prefix: ED-YYYY-NNNN
- Leave_Log: column 6 = hours, column 7 = leave time
- Attendance: if approved + covers gap → P
- PDF: "EARLY DEPARTURE APPROVAL"

## 1C. Overtime Request (⏰)
NOT YET BUILT. Build it now:
- Two types: "⏰ Planned OT" and "🚨 Emergency OT"
- Planned: date must be ≥ tomorrow (24hr advance)
- Emergency: today or yesterday
- Flow: date → hours (1-4) → reason → summary
- Limits: max 4hrs/day, 12hrs/week, 40hrs/month
- If monthly total > 40hrs → add Director to chain
- Normal: Manager → HR
- Request_Type: "Overtime_Planned" or "Overtime_Emergency", prefix: OT-YYYY-NNNN
- Leave_Log: col 6 = hours, col 17 = OT rate (1.5), col 18 = hours × rate
- PDF: "OVERTIME APPROVAL"

## 1D. Admin Functions (⚙️) — make it real, not placeholder
HR_Manager menu → Admin:
- 👥 List Users → all registered with role + last access
- 🔒 Lock User → enter code → lock
- 🔓 Unlock User → enter code → unlock + reset attempts
- 🔑 Reset Password → generate new temp
- Each action logged in Access_Log
- Build as buttons in a menu, NOT slash commands

## 1E. Payroll Input Automation
Create/populate Payroll_Input tab monthly:
Columns: Emp_Code, Full_Name, Department, Days_Present, Days_Absent,
Days_Late, Total_Late_Minutes, Days_Leave_Paid, Days_Leave_Sick,
Days_Leave_Unpaid, OT_Hours, OT_Rate, OT_Payment,
Deduction_Absent, Deduction_Unpaid, Deduction_Late
HR_Manager menu: "💰 Generate Payroll Input" → picks month → auto-calculates from attendance + leave + overtime data

## 1F. All Leave Requests (📑) — real data
For HR_Staff + HR_Manager:
- Summary: Pending Manager X, Pending HR X, Approved this month X, Rejected X
- Buttons: View Pending HR / View All This Month / Search by Employee
- Real data from Leave_Log, not placeholder

## 1G. Verify all vehicle, supply, warehouse handlers actually work
Run through each handler file. Fix any that are stubs or incomplete.
Test each menu flow end-to-end.

====================================================================
# SECTION 2: DIRECTOR FEATURES
====================================================================

## 2A. Daily Morning Brief (auto at 8 AM)
Build send_director_daily_brief(bot):
- Today: X present / X absent / X leave / X sick
- Yesterday attendance: X% (🟢>95%, 🟡90-95%, 🔴<90%)
- Pending MY decisions: X items
- Contracts expiring this month: X
- Expired documents: X
- OT this month: X hours
- Critical announcements unread >10%: X
Send to Director's Telegram ID from User_Registry.
For now: /dailybrief command (HR_Manager + Director only).
Later: Apps Script scheduled trigger.

## 2B. Batch Approvals
Add "📋 Quick Batch" button at top of Director's Pending Approvals:
- One scrollable list of ALL pending Director items
- Each: employee name, type, days, manager recommendation
- ✅ ❌ per item
- "✅ Approve All" button for routine requests
- All decisions logged with timestamp

## 2C. Company Dashboard (real data)
When Director taps Company Overview → live numbers:
- Total 600 | Active X | Leave X | Terminated X
- Department breakdown with counts
- This month: hires X, terminations X, turnover X%
- Attendance trend last 3 months
- Leave by type this month
- OT hours + cost
- Expiring contracts list

## 2D. Monthly PDF Report (auto 1st of month)
8 sections:
1. Executive Summary (3 highlights, 3 concerns)
2. Headcount (opening/closing, hires, terminations, turnover %)
3. Attendance (rate vs target, department breakdown, worst 10)
4. Leave (by type, departments, zero-balance employees)
5. Contracts (expiring 30/60, pending decisions)
6. Performance (avg scores by dept — placeholder until eval tested)
7. Document Compliance (expired, expiring, rate %)
8. OT & Payroll Summary
Auto-send PDF to Director + HR_Manager + save to Drive

## 2E. Director Alerts
- Contract expired no decision → immediate
- Department attendance <90% → daily
- Employee absent 3+ consecutive no leave → same day
- Document expired (legal) → immediate
- OT budget exceeded → weekly

====================================================================
# SECTION 3: VEHICLE SYSTEM — COMPLETE REBUILD
====================================================================

## 3A. ALL employees can request a vehicle
New menu button for ALL roles: "🚗 Request Vehicle"
Flow:
1. Select destination (free text)
2. Where from → where to
3. Purpose/reason
4. Date + estimated departure time
5. Estimated hours needed
6. Number of passengers
7. Summary → Submit
8. Goes to DIRECT MANAGER for approval first
9. After manager approves → goes to TRANSPORT MANAGER for assignment
10. Transport Manager assigns car + driver
11. Driver gets notification with trip details
12. Employee gets notification with car plate + driver name + phone

## 3B. Trip Tracking
- Driver logs departure: time, fuel level, odometer → via bot button "🚀 Start Trip"
- Timer starts based on estimated duration
- Overdue: 15min → ping driver, 30min → Transport Manager, 60min → Director
- Driver logs return: time, fuel, odometer, delay reason → "🏁 End Trip"
- All data saved to Trip_Log tab

## 3C. Vehicle Request Log (complete audit trail)
Trip_Log tab columns:
Trip_ID, Requesting_Emp, Requesting_Dept, From_Location, To_Location,
Purpose, Date, Est_Departure, Est_Hours, Passengers,
Manager_Status, Manager_Date, Transport_Status, Transport_Date,
Car_Plate, Driver_Code, Driver_Name, Driver_Phone,
Actual_Departure, Actual_Return, Fuel_Start, Fuel_End, Odometer_Start,
Odometer_End, Fuel_Used_Liters, Delay_Reason,
Status (Requested/Manager_Approved/Assigned/Departed/Returned/Cancelled)

Director sees: full log of ALL vehicle requests ever made.
Filter by: date range, department, employee, status.

## 3D. Driver License & Permit Daily Upload
Transport Manager MUST upload daily:
- Bot menu: "📄 Upload Driver Permits"
- Upload photos/scans of ALL driver licenses and permits
- Bot combines ALL uploads into ONE PDF per day
- PDF auto-saved to Drive: /Driver_Permits/[YEAR]/[MONTH]/permits_DD-MM-YYYY.pdf
- Director has access to see: monthly log of all daily permit PDFs
- Alert if Transport Manager misses a day (no upload by 10 AM)

Driver_Permits_Log tab:
Date, Uploaded_By, Driver_Count, PDF_Drive_Link, Upload_Time

## 3E. Driver Safety Lectures
Drivers receive periodic safety & occupational health lectures.
Track in Driver_Safety_Log tab:
Lecture_ID, Date, Title, Instructor, Duration_Hours,
Attendees_JSON (list of driver codes), Certificate_Photo_Link,
Next_Due_Date, Status (Completed/Scheduled/Overdue)

Transport Manager uploads lecture certificate/attendance sheet.
Bot generates PDF record → saved to Drive.
Director can view: all lectures, attendance, overdue drivers.
Alert: if any driver is overdue for safety lecture → notify Transport Manager.

## 3F. Fuel Tracking
Fuel_Log tab: Date, Car_Plate, Driver, Odometer, Liters, Cost, Receipt_Photo
Monthly report per vehicle. Flag abnormal consumption.

## 3G. Fleet Dashboard
Transport Manager sees:
- All 30 vehicles: Available / On Trip / Maintenance / Out of Service
- Today: scheduled X, in progress X, completed X
- Available drivers
- Pending vehicle requests

====================================================================
# SECTION 4: SAFETY & OCCUPATIONAL HEALTH DEPARTMENT (NEW)
====================================================================

New role: Safety_Manager
Add to VALID_ROLES in config.py.

## 4A. Safety Menu Structure
Safety_Manager main menu:
- 🔧 Periodic Maintenance Log
- ⚠️ Incident Reports
- 📋 Safety Lectures & Training
- 🎓 Training Courses
- 📊 Safety Dashboard
- 👤 My Profile
- ❓ Help

## 4B. Periodic Maintenance Log
Track routine inspections and repairs:
Maintenance_Log tab:
Log_ID, Date, Location (kitchen/warehouse/office/site), Equipment,
Type (Routine_Inspection/Repair/Emergency_Fix/Replacement),
Description, Issue_Found, Solution, Responsible_Employee,
Completion_Date, Time_To_Resolve, Cost, Photo_Before, Photo_After,
Status (Open/In_Progress/Resolved/Escalated), Priority (Low/Medium/High/Critical)

Safety Manager creates entry → fills details → uploads photos → marks resolved.
Overdue items (not resolved within deadline) → alert to Safety Manager + Director.

## 4C. Incident Reports
When safety incident occurs:
Incident_Log tab:
Incident_ID, Date, Time, Location, Type (Injury/Near_Miss/Fire/Spill/Equipment_Failure/Other),
Description, Employees_Involved, Witnesses, Immediate_Action_Taken,
Root_Cause, Corrective_Action, Preventive_Action,
Investigation_Date, Investigator, Photos, Report_PDF_Link,
Status (Reported/Investigating/Resolved/Closed), Severity (Minor/Moderate/Major/Critical)

Critical/Major: auto-notify Director immediately.
Generate incident report PDF → save to Drive.

## 4D. Safety Lectures for ALL Employees
Not just drivers — any department can have safety training.
Safety_Lectures tab:
Lecture_ID, Date, Title, Topic_Category (Fire_Safety/First_Aid/PPE/Food_Safety/Chemical_Handling/General),
Instructor, Duration_Hours, Target_Department (All/Kitchen/Warehouse/etc),
Attendees_JSON, Total_Attended, Total_Expected, Attendance_Rate,
Certificate_Photo, Materials_Link, Next_Due_Date

Safety Manager schedules → conducts → uploads attendance → marks complete.
Each employee's profile shows their safety training history.
Alert: employees overdue for mandatory training.

## 4E. Training Courses
Track external and internal training:
Training_Log tab:
Course_ID, Title, Provider (Internal/External), Date_Start, Date_End,
Duration_Hours, Instructor, Cost, Attendees_JSON,
Certificate_Required (Yes/No), Certificates_Uploaded,
Status (Scheduled/In_Progress/Completed/Cancelled)

## 4F. Safety Dashboard
Safety Manager + Director sees:
- Open incidents: X (by severity)
- Overdue maintenance: X items
- Training compliance: X% of employees up to date
- This month: incidents X, lectures X, maintenance tasks X
- Trend: last 3 months

====================================================================
# SECTION 5: TRANSLATION DEPARTMENT (NEW)
====================================================================

New roles: Translation_Manager, Translator
Add to VALID_ROLES.

## 5A. Translation Request Flow
Who can request: any Direct_Manager, Supervisor, HR_Staff, HR_Manager, Director,
or employees with special permission (add Translation_Access column to Employee_DB: Yes/No)

Flow:
1. Requester uploads document (photo/PDF/text) via bot
2. Selects: source language → target language (AR/RU/EN)
3. Adds notes/instructions
4. Submit → goes to Translation_Manager
5. Translation_Manager assigns to a Translator
6. Translator receives notification with the document
7. Translator completes translation → uploads translated document
8. Bot generates PDF of translation → sends to Translation_Manager for review
9. Translation_Manager reviews → approves or sends back for revision
10. On approval → requester gets the translated PDF + notification
11. All files saved to Drive

## 5B. Translation Log
Translation_Log tab:
Request_ID (TR-YYYY-NNNN), Date, Requester_Code, Requester_Dept,
Source_Language, Target_Language, Document_Type, Original_File_Link,
Assigned_To (translator code), Assigned_Date,
Translated_File_Link, Translation_Date,
Reviewer (Translation_Manager), Review_Date, Review_Status (Pending/Approved/Revision),
Final_PDF_Link, Status (Requested/Assigned/In_Progress/Review/Approved/Delivered),
Notes

## 5C. Translator Portfolio
Each translator has a Drive folder:
/Translation/[Translator_Code]_[Name]/Requests/ — original documents assigned to them
/Translation/[Translator_Code]_[Name]/Completed/ — their translated outputs

## 5D. Translation Manager Dashboard
- Pending assignments: X
- In progress: X
- Pending review: X
- Completed this month: X
- Per translator: workload + completion rate

## 5E. Translation Menu Structure
Translation_Manager:
- 📥 New Requests (unassigned)
- 👥 Assign to Translator
- 📋 All Translations (filter by status)
- 🔍 Review Pending
- 📊 Translation Dashboard
- 👤 My Profile / ❓ Help

Translator:
- 📋 My Assignments
- 📤 Upload Translation
- 📊 My Stats
- 👤 My Profile / ❓ Help

====================================================================
# SECTION 6: OPERATIONS / KITCHEN OPERATIONS DEPARTMENT (NEW)
====================================================================

New role: Operations_Manager
Add to VALID_ROLES.

## 6A. Daily Operations Reports
Operations team submits daily reports per kitchen section:
Operations_Reports tab:
Report_ID, Date, Shift (Morning/Evening/Night), Section (Egyptian_Kitchen/Russian_Kitchen/Bakery/Prep),
Submitted_By, Meals_Produced, Meals_Target, Achievement_Rate,
Issues, Waste_Kg, Staff_Present, Staff_Absent,
Equipment_Issues, Notes, Photo_Links, PDF_Link,
Status (Submitted/Reviewed), Reviewed_By, Review_Date

## 6B. Report Flow
1. Operations staff submits via bot (template with fields)
2. Bot generates PDF report → saves to Drive
3. Auto-sent to: Kitchen Director (Catering Director) + Head Chef + Company Director
4. Drive folder: /Operations_Reports/[YEAR]/[MONTH]/report_DD-MM-YYYY_shift.pdf

## 6C. Operations Menu
Operations_Manager:
- 📝 Submit Daily Report
- 📋 View Reports (by date/section)
- 📊 Monthly Summary
- 👤 My Profile / ❓ Help

NOTE: I will send you the exact report template/form later. For now build the structure
and submission flow with the fields above. We can adjust the form later.

====================================================================
# SECTION 7: QUALITY CONTROL DEPARTMENT (NEW)
====================================================================

New role: Quality_Manager
Add to VALID_ROLES.

## 7A. Incoming Material Inspection
When materials arrive at warehouse, Quality team inspects:
Quality_Inspection_Log tab:
Inspection_ID, Date, Supplier, Item, Quantity, Unit,
PO_Number (link to purchase order if exists),
Inspector_Code, Inspector_Name,
Result (Accepted/Rejected/Partial_Accept),
Rejection_Reason, Rejection_Quantity,
Temperature_Check (for food items), Expiry_Date_Check,
Certificate_Links (health certs, lab reports uploaded),
Delivery_Note_Photo, Inspection_Report_Photo,
Notes, PDF_Report_Link

## 7B. Quality Inspection Flow
1. Quality inspector opens bot → "🔍 New Inspection"
2. Select supplier (from Suppliers tab) or type name
3. Enter item + quantity
4. Enter result: Accept ✅ / Reject ❌ / Partial Accept ⚠️
5. If rejected/partial: reason + rejected quantity
6. Upload photos: delivery note, certificates, inspection report
7. Summary → Confirm → saved to log
8. If rejected: auto-notify Warehouse Manager + Supply Manager
9. PDF report generated → saved to Drive

## 7C. Who Sees Quality Records
- Quality_Manager: full access, all inspections, dashboard
- Kitchen Director (Catering Director): read access to all
- Head Chef: read access to all
- Supply_Manager: read access (to track supplier quality)
- Director: read access + summary dashboard

## 7D. Quality Dashboard
- This month: total inspections X, accepted X, rejected X, acceptance rate X%
- By supplier: acceptance rate ranking
- Rejected items this month with reasons
- Trend: last 3 months

## 7E. Quality Menu
Quality_Manager:
- 🔍 New Inspection
- 📋 All Inspections (filter by date/supplier/result)
- 📊 Quality Dashboard
- 🏭 Supplier Quality Ratings
- 👤 My Profile / ❓ Help

====================================================================
# SECTION 8: PURCHASE REQUESTS — ALL DEPARTMENTS
====================================================================

## 8A. Department Purchase Requests
ALL department managers can request materials/supplies:
New menu button for Direct_Manager, HR_Manager, and any manager role:
"🛒 Purchase Request"

Flow:
1. Manager selects items needed (text description + quantity)
2. Sets urgency: Normal / Urgent / Emergency
3. Adds notes/justification
4. Submit → goes to DIRECTOR for approval
5. Director approves → request goes to Supply_Manager + Finance
6. Supply_Manager processes the purchase
7. Employee who requested gets notification at each stage

## 8B. Purchase Request Log
Purchase_Requests tab:
PR_ID (PR-YYYY-NNNN), Date, Requesting_Dept, Requesting_Manager_Code,
Items_Description, Quantity, Estimated_Cost, Urgency,
Justification, Director_Status, Director_Date,
Supply_Status (Pending/Quoted/Ordered/Delivered/Received),
Supplier, Actual_Cost, PO_Number, Delivery_Date,
Received_Date, Received_By, Quality_Status (links to inspection),
PDF_Link, Status (Requested/Director_Approved/In_Progress/Delivered/Closed/Rejected)

## 8C. Company Purchase Registry
Master view for Director + Supply_Manager:
- All purchases ever made, filterable by date/department/supplier
- Per department spending this month vs last month
- Total company spending trend

## 8D. Department Spending View
Each manager sees: their department's purchase history + total spent this month.

====================================================================
# SECTION 9: HOUSING / ACCOMMODATION DEPARTMENT (NEW)
====================================================================

New role: Housing_Manager
Add to VALID_ROLES.

## 9A. Apartment Registry
Apartments_Log tab:
Apartment_ID, Building_Name, Floor, Unit_Number, Address,
Type (Studio/1BR/2BR/3BR/Shared), Capacity (max persons),
Current_Occupants_JSON (list of Emp_Codes),
Occupancy_Count, Status (Available/Occupied/Maintenance/Reserved),
Furnished (Yes/No), Monthly_Rent, Lease_Start, Lease_Expiry,
Landlord_Name, Landlord_Phone, Contract_Link, Photos_Link, Notes

## 9B. Employee Housing Assignment
Link employees to apartments:
Housing_Assignments tab:
Assignment_ID, Emp_Code, Apartment_ID, Move_In_Date, Move_Out_Date,
Status (Active/Ended/Pending), Deposit_Paid, Monthly_Deduction,
Notes

## 9C. Housing Request Flow
Employee or HR submits housing request:
Housing_Requests tab:
Request_ID (HSG-YYYY-NNNN), Emp_Code, Request_Type (New/Transfer/Vacate),
Preferred_Type, Roommate_Preference, Urgency, Reason,
Housing_Manager_Status, Housing_Manager_Date,
HR_Status, HR_Date, Assigned_Apartment,
Status (Requested/Approved/Assigned/Moved_In/Rejected)

## 9D. Maintenance Requests (Housing)
Employees report issues in their apartment:
Housing_Maintenance tab:
Ticket_ID, Date, Emp_Code, Apartment_ID, Issue_Type (Plumbing/Electrical/AC/Furniture/Other),
Description, Priority (Low/Medium/High/Emergency), Photos,
Assigned_To, Resolution_Date, Resolution_Notes, Cost,
Status (Open/In_Progress/Resolved/Closed)

## 9E. Housing Dashboard
Housing_Manager sees:
- Total apartments: X | Occupied: X | Available: X | Maintenance: X
- Occupancy rate: X%
- Pending requests: X
- Open maintenance tickets: X
- Leases expiring within 30 days: X

## 9F. Housing Menu
Housing_Manager:
- 🏠 Apartment Registry (view all, add new, edit)
- 👤 Assign Employee
- 📋 Housing Requests
- 🔧 Maintenance Tickets
- 📊 Housing Dashboard
- 💰 Rent & Lease Tracker
- 👤 My Profile / ❓ Help

Employee sees (in My Profile or separate menu):
- 🏠 My Housing: apartment details, roommates, maintenance request button

====================================================================
# SECTION 10: PERFORMANCE EVALUATION — VERIFY & COMPLETE
====================================================================

eval_handler.py exists. Verify it fully works:
- 70% auto-scored (attendance, lateness, leave pattern)
- 30% manager input (4 criteria, 1-5 each)
- Rating scale: Excellent/Good/Acceptable/Weak/Unsatisfactory
- Triggers: quarterly, contract renewal, probation end, on-demand
- PDF report generated
- HR reviews → Director approves
- Evaluations_Log tab complete

====================================================================
# SECTION 11: ANNOUNCEMENTS — VERIFY & COMPLETE
====================================================================

announcement_handler.py exists. Verify it fully works:
- HR creates: title + body → auto-translate AR/RU/EN via Gemini
- Priority levels: 🔴🟠🟡🟢
- Target: All / Department / Role / Custom
- Track: delivered, read, confirmed
- Critical escalation: 2hrs→manager, 4hrs→HR, EOD→Director
- Announcements_Log + Read_Confirmations tabs

====================================================================
# SECTION 12: DOCUMENT & CONTRACT EXPIRY — VERIFY
====================================================================

doc_contract_handler.py exists. Verify:
- Employee_Documents tab with all document types tracked
- Alert timeline: 90/60/30/14/7/3/0 days
- Contract expiry alerts
- Manager recommendation → HR review → Director decision
- Letter generation (renewal/termination/amendment)
- Contracts_Log tab

====================================================================
# SECTION 13: UPDATED ROLES LIST
====================================================================

After all sections, config.py VALID_ROLES must be:
[
  "Employee", "Supervisor", "Direct_Manager",
  "HR_Staff", "HR_Manager", "Director",
  "Warehouse", "Driver", "Transport_Manager", "Supply_Manager",
  "Safety_Manager", "Translation_Manager", "Translator",
  "Operations_Manager", "Quality_Manager", "Housing_Manager"
]

Total: 16 roles. Each must have its own menu in bot.py.

====================================================================
# SECTION 14: UPDATED MENU PER ROLE
====================================================================

## Employee
🏖️ Leave | 🖐 Missing Punch | 🚗 Request Vehicle
🕐 My Attendance | 👤 My Profile | 📜 Certificates
💬 Contact HR | 🏠 My Housing | ❓ Help

## Supervisor
Everything Employee + 👥 My Team | 📂 Team Requests | 👥 Request for Employee

## Direct_Manager
Everything Supervisor + 🔔 Pending Approvals | 📄 Job Descriptions
🛒 Purchase Request | 📌 Assign Tasks

## HR_Staff
Everything Employee + 👥 Team | 📄 JDs | 🛠️ HR Tools (Lookup, Letters, Attendance, All Leave)
💬 HR Messages | 📊 Doc/Contract Expiry

## HR_Manager
Everything HR_Staff + 🔔 Pending Approvals | ⚙️ Admin | 💰 Payroll | 📢 Announcements

## Director
🔔 Pending Approvals (batch) | 🏢 Company Dashboard | 📈 Reports
🔍 Employee Lookup | 📄 JDs (approve) | 🚗 Vehicle Log | 📊 All Dashboards

## Warehouse
📦 Stock IN | 📤 Stock OUT | 🔄 Transfer | 🗑 Waste
📊 Inventory | ⚠️ Low Stock | 🚗 Request Vehicle
🕐 My Attendance | 👤 My Profile | ❓ Help

## Driver
🚗 My Trips | 🚀 Start Trip | 🏁 End Trip | ⛽ Log Fuel
🕐 My Attendance | 👤 My Profile | ❓ Help

## Transport_Manager
🚗 Trip Requests | ✅ Approve/Assign Trips | 🚙 Fleet Dashboard
⛽ Fuel Report | 👥 Driver Roster | 📄 Upload Driver Permits
📋 Driver Safety Lectures | 📊 Transport Report
🕐 My Attendance | 👤 My Profile | ❓ Help

## Supply_Manager
🛒 Purchase Requests | ✅ Process Orders | 🏭 Supplier Database
💰 Budget Tracker | 📦 Warehouse View | 📊 Supply Report
🕐 My Attendance | 👤 My Profile | ❓ Help

## Safety_Manager
🔧 Maintenance Log | ⚠️ Incident Reports | 📋 Safety Lectures
🎓 Training Courses | 📊 Safety Dashboard
🕐 My Attendance | 👤 My Profile | ❓ Help

## Translation_Manager
📥 New Requests | 👥 Assign to Translator | 📋 All Translations
🔍 Review Pending | 📊 Translation Dashboard
🕐 My Attendance | 👤 My Profile | ❓ Help

## Translator
📋 My Assignments | 📤 Upload Translation | 📊 My Stats
🕐 My Attendance | 👤 My Profile | ❓ Help

## Operations_Manager
📝 Submit Daily Report | 📋 View Reports | 📊 Monthly Summary
🕐 My Attendance | 👤 My Profile | ❓ Help

## Quality_Manager
🔍 New Inspection | 📋 All Inspections | 📊 Quality Dashboard
🏭 Supplier Quality | 🕐 My Attendance | 👤 My Profile | ❓ Help

## Housing_Manager
🏠 Apartments | 👤 Assign Employee | 📋 Housing Requests
🔧 Maintenance Tickets | 📊 Housing Dashboard | 💰 Rent Tracker
🕐 My Attendance | 👤 My Profile | ❓ Help

====================================================================
# SECTION 15: GOOGLE SHEET TABS (complete list after all sections)
====================================================================

MASTER WORKBOOK tabs needed:
Employee_DB, Leave_Balance, Leave_Log, Holidays, User_Registry, Access_Log,
Promotions_Log, FAQ, Contact_HR, JD_Drafts,
Employee_Documents, Contracts_Log, Evaluations_Log, Improvement_Plans,
Announcements_Log, Read_Confirmations, Payroll_Input,
Stock_Transactions, Current_Balance,
Trip_Log, Vehicles, Fuel_Log, Driver_Permits_Log, Driver_Safety_Log,
Safety_Maintenance_Log, Safety_Incident_Log, Safety_Lectures, Training_Log,
Translation_Log, Translation_Assignments,
Operations_Reports,
Quality_Inspection_Log, Suppliers,
Purchase_Requests, Purchase_Registry,
Apartments_Log, Housing_Assignments, Housing_Requests, Housing_Maintenance

Auto-create any missing tabs when their handler first runs.

====================================================================
# SECTION 16: DRIVE FOLDER STRUCTURE
====================================================================

/HR_Employees/[EMP_CODE]_[NAME]/ — personal documents
/Approval_PDFs/[YEAR]/[MONTH]/ — leave, OT, early departure approvals
/Certificates/ — employment, salary, experience letters
/JD_Documents/ — job descriptions
/Evaluation_Reports/ — performance evaluations
/Driver_Permits/[YEAR]/[MONTH]/ — daily permit PDFs
/Translation/[Translator_Code]_[Name]/Requests/ — originals
/Translation/[Translator_Code]_[Name]/Completed/ — translations
/Operations_Reports/[YEAR]/[MONTH]/ — daily ops reports
/Quality_Reports/[YEAR]/[MONTH]/ — inspection reports
/Safety_Reports/ — incident reports, maintenance logs
/Purchase_Orders/ — PO documents
/Housing/ — lease contracts, apartment photos

====================================================================
# BUILD ORDER
====================================================================

Section 1 (fix gaps) → Section 2 (Director) → Section 3 (Vehicles) →
Section 4 (Safety) → Section 5 (Translation) → Section 6 (Operations) →
Section 7 (Quality) → Section 8 (Purchasing) → Section 9 (Housing) →
Section 10 (Evaluation verify) → Section 11 (Announcements verify) →
Section 12 (Doc/Contract verify) → Section 13 (Roles update) →
Section 14 (Menus update) → Section 15 (Tabs) → Section 16 (Drive)

After EACH section: "Section X done — ready to test" → STOP.
I test → "next" → continue.

START WITH SECTION 1.
====================================================================
