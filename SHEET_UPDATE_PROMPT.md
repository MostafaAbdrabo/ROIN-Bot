# SHEET STRUCTURE UPDATE — Adjust Bot to New 31-Tab Layout
# The Google Sheet has been restructured. Read this and adjust ALL handlers.

====================================================================
# WHAT CHANGED
====================================================================

## Tabs MERGED (old → new):
| Old Tabs | New Tab | Type Column Values |
|----------|---------|-------------------|
| Contracts_Log + Promotions_Log | Employee_History | Contract_Renewal, Contract_Termination, Promotion, Role_Change, Salary_Change, Warning, etc. |
| Safety_Maintenance_Log + Safety_Incident_Log | Safety_Log | Routine_Inspection, Repair, Emergency_Fix, Injury, Near_Miss, Fire, Spill, etc. |
| Safety_Lectures + Training_Log | Training_Log | Safety_Lecture, Fire_Safety, External_Course, Internal_Course, Certification, etc. |
| Driver_Permits_Log + Driver_Safety_Log | Driver_Compliance | Permit_Upload, Safety_Lecture, License_Renewal, Medical_Check |
| Housing_Assignments + Housing_Requests + Housing_Maintenance | Housing_Log | Assignment, Transfer, Vacate, Request, Maintenance_Plumbing, Maintenance_Electrical, etc. |
| Announcements_Log | Announcements | (same structure, just renamed) |
| Read_Confirmations | Read_Tracking | (same structure + VLOOKUP for name) |

## Tabs DELETED:
Contracts_Log, Promotions_Log, Read_Confirmations, Driver_Permits_Log,
Driver_Safety_Log, Safety_Maintenance_Log, Safety_Incident_Log, Safety_Lectures,
Housing_Assignments, Housing_Requests, Housing_Maintenance, Announcements_Log

## KEY CHANGE: VLOOKUP Auto-Fill
Many tabs now have VLOOKUP formulas. When the bot writes data:
- ONLY write Emp_Code — do NOT write Full_Name or Department
- The VLOOKUP formula in those columns will auto-fill from Employee_DB
- If you write a value to a VLOOKUP cell, it OVERWRITES the formula!

Tabs with VLOOKUP (bot must NOT write to Name/Dept columns):
- Contact_HR: col C (Name) and D (Dept) are VLOOKUP from col B (Emp_Code)
- Employee_Documents: col C, D from col B
- Employee_History: col C, D from col B
- Evaluations_Log: col C, D from col B
- Read_Tracking: col C from col B
- Payroll_Input: col B, C from col A
- Stock_Transactions: col M (Emp_Name) from col L (Emp_Code)
- Trip_Log: col C (Name), D (Dept) from col B (Emp_Code)
- Translation_Log: col D (Requester_Name), E (Dept) from col C; col K (Translator_Name) from col J
- Operations_Reports: col F (Name) from col E (Submitted_By)
- Quality_Inspection_Log: col I (Inspector_Name) from col H (Inspector_Code)
- Purchase_Requests: col E (Manager_Name) from col D (Manager_Code)
- Housing_Log: col E (Emp_Name) from col D (Emp_Code)
- Vehicles: col F (Driver_Name) from col E (Assigned_Driver)

RULE: When appending rows to these tabs, put "" (empty string) in VLOOKUP columns.
The spreadsheet formula handles the rest.

## Formulas in Current_Balance:
- Column F (Total) = C + D + E (sum of 3 warehouses)
- Column H (Status) = auto from Total vs Min_Level

## Formulas in Employee_Documents:
- Column I (Days_Until_Expiry) = Expiry_Date - TODAY()
- Column J (Status) = auto from days (EXPIRED/CRITICAL/URGENT/WARNING/OK)

## Formulas in Operations_Reports:
- Column I (Achievement_Rate) = Meals_Produced / Meals_Target

====================================================================
# WHAT TO UPDATE IN THE BOT CODE
====================================================================

## 1. doc_contract_handler.py
- Change all references to "Contracts_Log" → "Employee_History"
- Change all references to "Promotions_Log" → "Employee_History"
- When writing contract decisions: add Event_Type column = "Contract_Renewal" etc.
- When writing promotions: add Event_Type column = "Promotion"
- Column order changed — update column indices
- New columns: [Log_ID, Emp_Code, Full_Name(VLOOKUP), Department(VLOOKUP), Event_Type, Event_Date, Details, Old_Value, New_Value, Approved_By, Eval_Score, Drive_Link, Notes]
- When appending row: leave col 3 and 4 as "" (VLOOKUP fills them)

## 2. safety_handler.py (if exists)
- Merge maintenance + incident writes into "Safety_Log" tab
- Use "Type" column to distinguish: Routine_Inspection vs Injury vs Fire etc.
- Column order: [Log_ID, Date, Type, Location, Equipment_or_Subject, Description, Severity, Priority, Employees_Involved, Root_Cause, Action_Taken, Solution, Responsible, Completion_Date, Time_To_Resolve, Cost, Photos, Report_PDF_Link, Status]

## 3. Training/lecture handlers
- All training writes go to "Training_Log" tab
- Use "Category" column: Safety_Lecture, External_Course, etc.
- Column order: [Record_ID, Date, Category, Title, Topic, Provider, Instructor, Duration_Hours, Target_Dept, Attendees_JSON, Total_Attended, Total_Expected, Attendance_Rate, Cost, Certificate_Link, Materials_Link, Next_Due_Date, Status]

## 4. vehicles_handler.py
- Driver permits + safety lectures → "Driver_Compliance" tab
- Use "Type" column: Permit_Upload, Safety_Lecture, etc.
- Column order: [Record_ID, Date, Type, Title, Uploaded_By, Driver_Count, Attendees_JSON, Instructor, Duration_Hours, Certificate_Link, PDF_Drive_Link, Next_Due_Date, Status, Notes]

## 5. housing_handler.py (if exists)
- All housing operations → "Housing_Log" tab
- Use "Type" column: Assignment, Transfer, Vacate, Request, Maintenance_*
- Column order: [Record_ID, Date, Type, Emp_Code, Emp_Name(VLOOKUP), Apartment_ID, Details, Priority, Status, Assigned_To, Resolution_Date, Resolution_Notes, Cost, Photos, Notes]
- Apartments tab stays separate (reference data)

## 6. announcement_handler.py
- "Announcements_Log" → "Announcements"
- "Read_Confirmations" → "Read_Tracking"
- Read_Tracking now has col C as VLOOKUP — don't write name there

## 7. contact_hr_handler.py
- Contact_HR now has VLOOKUP cols C (Name) and D (Dept)
- When writing: [Msg_ID, Emp_Code, "", "", Timestamp, Message, Anonymous, "", ""]
- Leave cols 3,4 empty for VLOOKUP

## 8. All other handlers that write employee data
- Check every append_row call
- If the tab has VLOOKUP columns, leave them as ""
- Only write Emp_Code — name and department auto-fill

====================================================================
# NEW ROLES TO ADD
====================================================================

config.py VALID_ROLES must be:
["Director","HR_Manager","HR_Staff","Direct_Manager","Supervisor","Employee",
 "Warehouse","Warehouse_Manager","Warehouse_Specialist","Store_Keeper",
 "Driver","Transport_Manager",
 "Supply_Manager","Supply_Specialist",
 "Safety_Manager",
 "Translation_Manager","Translator",
 "Operations_Manager","Operations_Specialist","Operations_Coordinator",
 "Quality_Manager","Quality_Specialist",
 "Housing_Manager","Housing_Specialist"]

Total: 24 roles. Each needs a menu in bot.py.

Specialist/Coordinator roles get same menu as their Manager but WITHOUT:
- Approval authority (no Pending Approvals)
- Admin functions
- They CAN: submit reports, log data, view dashboards (read-only)

====================================================================
# WORK THROUGH EACH HANDLER FILE
====================================================================

1. Read each .py file
2. Find every get_sheet("OLD_TAB_NAME") call
3. Update tab name to new name
4. Find every append_row call — check if VLOOKUP columns need to be ""
5. Update column indices for merged tabs
6. Test after each file

After all updates: "Updates done — ready to test" → STOP.

====================================================================
