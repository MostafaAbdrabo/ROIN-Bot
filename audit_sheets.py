#!/usr/bin/env python3
"""
ROIN WORLD FZE — Google Sheet Audit & Fix
==========================================
Run: python3 audit_sheets.py
Connects to the live Google Sheet and ensures all tabs exist with correct headers.
Adds missing columns, test data, and VLOOKUP formulas where needed.
"""

import time
from datetime import datetime
from config import WORKBOOK

STATS = {"tabs_checked": 0, "tabs_added": [], "tabs_modified": [], "columns_added": [],
         "test_data_added": [], "issues_found": 0, "issues_fixed": 0}


def _get_or_create(name, headers):
    """Get a tab or create it with headers. Returns worksheet."""
    STATS["tabs_checked"] += 1
    try:
        ws = WORKBOOK.worksheet(name)
        existing = ws.row_values(1)
        if not existing:
            ws.update('A1', [headers])
            STATS["tabs_modified"].append(f"{name} (added headers)")
            STATS["issues_found"] += 1; STATS["issues_fixed"] += 1
        else:
            # Check for missing columns
            missing = [h for h in headers if h not in existing]
            if missing:
                for h in missing:
                    existing.append(h)
                ws.update('A1', [existing])
                STATS["columns_added"].append(f"{name} → {', '.join(missing)}")
                STATS["tabs_modified"].append(f"{name} (added {len(missing)} cols)")
                STATS["issues_found"] += len(missing); STATS["issues_fixed"] += len(missing)
        return ws
    except Exception:
        ws = WORKBOOK.add_worksheet(title=name, rows=1000, cols=max(len(headers), 26))
        ws.update('A1', [headers])
        STATS["tabs_added"].append(name)
        STATS["issues_found"] += 1; STATS["issues_fixed"] += 1
        return ws


def _add_test_rows(ws, tab_name, rows):
    """Add test rows if tab has only headers."""
    try:
        existing = ws.get_all_values()
        if len(existing) <= 1:
            for row in rows:
                ws.append_row(row, value_input_option="USER_ENTERED")
            STATS["test_data_added"].append(f"{tab_name} ({len(rows)} rows)")
            time.sleep(1)
    except Exception as e:
        print(f"  ⚠ Test data for {tab_name}: {e}")


def audit():
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    print("═" * 50)
    print("ROIN WORLD FZE — Sheet Audit")
    print("═" * 50)

    # ── Core tabs ──────────────────────────────────────────
    print("\n[1/6] Core tabs...")

    _get_or_create("Employee_DB", [
        "Emp_Code", "Full_Name", "National_ID", "Date_of_Birth", "Nationality",
        "Phone", "Email", "Department", "Job_Title", "Job_Grade",
        "Hire_Date", "Contract_Type", "Contract_Start", "Contract_Expiry",
        "Manager_Code", "Preferred_Language", "Shift_Hours", "Off_Type",
        "Work_Location", "Bank_Account", "Emergency_Contact_Name", "Emergency_Contact_Phone",
        "Status", "Bot_Role", "Signature_Link", "Signature_Type",
        "Profile_Photo", "Drive_Folder_Link",
        "Planned_Resignation_Date", "Resignation_Status",
    ])
    time.sleep(1)

    _get_or_create("User_Registry", [
        "Emp_Code", "Telegram_ID", "Password_Hash", "Bot_Role",
        "Created_At", "Status", "Failed_Attempts", "Last_Login",
    ])
    time.sleep(1)

    _get_or_create("Access_Log", [
        "Timestamp", "Telegram_ID", "Emp_Code", "Action", "Result", "Details",
    ])
    time.sleep(1)

    _get_or_create("Notifications", [
        "Notif_ID", "Date", "Emp_Code", "Type", "Title", "Message",
        "Related_ID", "Read", "Read_Date",
    ])
    time.sleep(1)

    # ── Leave tabs ─────────────────────────────────────────
    print("[2/6] Leave & Attendance tabs...")

    _get_or_create("Leave_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Request_Type", "Start_Date", "End_Date", "Days", "Reason",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Director_Status", "Director_Date",
        "Final_Status", "Rejection_Reason",
        "Approval_Chain", "Approver_Code",
        "PDF_Drive_Link", "Created_At", "Order_Number",
    ])
    time.sleep(1)

    _get_or_create("Leave_Balance", [
        "Emp_Code", "Full_Name", "Annual_Total", "Annual_Used", "Annual_Remaining",
        "Sick_Total", "Sick_Used", "Sick_Remaining",
        "Emergency_Total", "Emergency_Used", "Emergency_Remaining",
    ])
    time.sleep(1)

    _get_or_create("Holidays", [
        "Date", "Name_EN", "Name_AR", "Type",
    ])
    time.sleep(1)

    _get_or_create("Attendance_Sheet", [
        "Date", "Emp_Code", "Full_Name", "Department",
        "Check_In", "Check_Out", "Status", "Late_Minutes", "OT_Hours", "Notes",
    ])
    time.sleep(1)

    # ── Memo tab ───────────────────────────────────────────
    print("[3/6] Memo, Feedback, FAQ tabs...")

    _get_or_create("Memo_Log", [
        "Memo_ID", "Date", "Requester_Code", "Requester_Name", "Department",
        "Type", "Subject", "Body_RU", "Body_EN",
        "To_Name", "To_Code", "To_Department", "To_Job_Title",
        "SZ_Number", "Registration_Date",
        "HR_Status", "HR_Date",
        "HR_Manager_Status", "HR_Manager_Date",
        "Director_Status", "Director_Date",
        "Final_Status", "Rejection_Reason",
        "Drive_Link", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Bot_Feedback", [
        "Feedback_ID", "Date", "Emp_Code", "Full_Name", "Category",
        "Description", "Status", "Response", "Responded_By", "Response_Date",
    ])
    time.sleep(1)

    _get_or_create("FAQ", [
        "Question_EN", "Answer_EN", "Question_AR", "Answer_AR",
        "Question_RU", "Answer_RU", "Category",
    ])
    time.sleep(1)

    _get_or_create("Contact_HR", [
        "Message_ID", "Date", "Emp_Code", "Full_Name", "Message",
        "Reply", "Replied_By", "Reply_Date", "Status",
    ])
    time.sleep(1)

    _get_or_create("Announcements", [
        "Ann_ID", "Date", "Created_By", "Target", "Target_Detail",
        "Body", "Body_EN", "Body_AR", "Body_RU", "Status",
    ])
    time.sleep(1)

    _get_or_create("Read_Tracking", [
        "Ann_ID", "Emp_Code", "Read_Date",
    ])
    time.sleep(1)

    # ── HR Documents & Reports ─────────────────────────────
    print("[4/6] HR documents, evaluations, recruitment tabs...")

    _get_or_create("Employee_Documents", [
        "Emp_Code", "Doc_Type", "Doc_Name", "Drive_Link", "Upload_Date", "Notes",
    ])
    time.sleep(1)

    _get_or_create("Employee_History", [
        "Emp_Code", "Date", "Action", "Details", "Done_By",
    ])
    time.sleep(1)

    _get_or_create("Evaluations_Log", [
        "Eval_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Period", "Evaluator_Code", "Evaluator_Name",
        "Score_Technical", "Score_Communication", "Score_Teamwork",
        "Score_Attendance", "Score_Initiative", "Total_Score", "Grade",
        "Strengths", "Improvements", "Comments",
        "Report_Drive_Link", "Status", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Deduction_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Type", "Amount", "Reason", "Month",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Final_Status", "PDF_Drive_Link", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Bonus_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Type", "Amount", "Reason", "Month",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Final_Status", "PDF_Drive_Link", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Warning_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Warning_Type", "Reason", "Details",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Final_Status", "PDF_Drive_Link", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Advance_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Amount", "Reason", "Repayment_Plan",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Final_Status", "PDF_Drive_Link", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("End_Of_Service_Log", [
        "Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
        "Reason", "Last_Working_Day", "Clearance_Status",
        "Manager_Status", "Manager_Date",
        "HR_Status", "HR_Date",
        "Final_Status", "PDF_Drive_Link", "Created_At",
    ])
    time.sleep(1)

    ws_pay = _get_or_create("Payroll_History", [
        "Month", "Emp_Code", "Full_Name", "Department", "Basic_Salary",
        "Allowances", "Deductions", "Overtime_Pay", "Net_Salary",
    ])
    time.sleep(1)
    # Add test payroll data
    _add_test_rows(ws_pay, "Payroll_History", [
        ["10/2025", "1007", "", "", "5000", "1000", "200", "0", "5800"],
        ["11/2025", "1007", "", "", "5000", "1000", "0",   "500", "6500"],
        ["12/2025", "1007", "", "", "5000", "1000", "300", "0", "5700"],
        ["01/2026", "1007", "", "", "5500", "1000", "0",   "0", "6500"],
        ["02/2026", "1007", "", "", "5500", "1000", "150", "750", "7100"],
        ["03/2026", "1007", "", "", "5500", "1000", "0",   "0", "6500"],
    ])
    time.sleep(1)

    _get_or_create("Payroll_Input", [
        "Month", "Emp_Code", "OT_Hours", "Deduction_Amount", "Bonus_Amount", "Notes",
    ])
    time.sleep(1)

    _get_or_create("Promotions_Log", [
        "Date", "Emp_Code", "Full_Name", "From_Title", "To_Title",
        "From_Grade", "To_Grade", "Effective_Date", "Approved_By", "Notes",
    ])
    time.sleep(1)

    _get_or_create("Signatures", [
        "Emp_Code", "Signature_Data", "Signature_Type", "Updated_At",
    ])
    time.sleep(1)

    _get_or_create("Training_Log", [
        "Training_ID", "Date", "Emp_Code", "Full_Name", "Training_Type",
        "Description", "Status", "Certificate_Link",
    ])
    time.sleep(1)

    # ── Recruitment ────────────────────────────────────────
    _get_or_create("Hiring_Requests", [
        "HR_ID", "Date", "Manager_Code", "Manager_Name", "Department",
        "Position_Title", "Num_Positions", "Priority", "Justification",
        "Required_Start_Date", "Contract_Type", "Shift", "Work_Location",
        "Salary_Range", "Special_Requirements",
        "HR_Status", "HR_Date", "HR_Notes", "Scheduled_Headcount",
        "Director_Status", "Director_Date", "Director_Notes",
        "Final_Status", "Job_Posting_ID",
        "Current_Status", "Last_Update", "Positions_Filled", "Total_Requested",
        "Reason", "Replacement_For", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Job_Postings", [
        "Posting_ID", "HR_Request_ID", "Date", "Position_Title", "Department",
        "Location", "Description_AR", "Description_EN", "Description_RU",
        "Requirements", "Benefits", "Deadline", "Status",
        "Candidates_Count", "Created_By", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Candidates", [
        "Candidate_ID", "Posting_ID", "Name", "Phone", "National_ID",
        "Source", "Education", "Experience_Years", "Previous_Employer",
        "Skills_Notes", "Resume_Link", "Screening_Rating", "Screening_Notes",
        "Screening_By", "Interview_Date", "Interview_Time",
        "Interview_Panel_JSON", "Interview_Feedback_JSON", "Final_Rating",
        "Status", "Rejection_Reason", "Offer_Salary", "Offer_Date",
        "Start_Date", "Emp_Code_Assigned", "Referred_By", "Created_At",
    ])
    time.sleep(1)

    _get_or_create("Onboarding_Checklist", [
        "Emp_Code", "Candidate_ID", "Item", "Status", "Date_Completed", "Notes",
    ])
    time.sleep(1)

    ws_hc = _get_or_create("Department_Headcount", [
        "Department", "Job_Title", "Max_Allowed", "Current_Count", "Available_Slots",
    ])
    time.sleep(1)
    _add_test_rows(ws_hc, "Department_Headcount", [
        ["Egyptian Kitchen", "Head Chef", "1", "", ""],
        ["Egyptian Kitchen", "Cook", "25", "", ""],
        ["Egyptian Kitchen", "Shift Supervisor", "4", "", ""],
        ["Russian Kitchen", "Head Chef", "1", "", ""],
        ["Russian Kitchen", "Cook", "2", "", ""],
        ["Warehouse", "Warehouse Manager", "1", "", ""],
        ["Warehouse", "Store Keeper", "6", "", ""],
        ["Quality Control", "Quality Manager", "1", "", ""],
        ["Quality Control", "Quality Specialist", "12", "", ""],
        ["Translation", "Translation Manager", "1", "", ""],
        ["Translation", "Translator", "5", "", ""],
        ["Operations", "Operations Manager", "1", "", ""],
        ["Purchasing", "Supply Manager", "1", "", ""],
        ["Housing", "Housing Manager", "1", "", ""],
        ["Safety", "Safety Manager", "1", "", ""],
        ["Transportation", "Transport Manager", "1", "", ""],
        ["Transportation", "Driver", "15", "", ""],
        ["HR", "HR Manager", "1", "", ""],
        ["HR", "HR Specialist", "5", "", ""],
    ])
    time.sleep(1)

    # ── Operations tabs ────────────────────────────────────
    print("[5/6] Operations, warehouse, transport, housing tabs...")

    for tab, headers in [
        ("Tasks_Log", ["Task_ID", "Date", "Emp_Code", "Full_Name", "Department",
                        "Task_Type", "Title", "Description", "Assigned_By",
                        "Priority", "Deadline", "Status", "Completed_At", "Notes"]),
        ("Translation_Log", ["Request_ID", "Date", "Requester_Code", "Requester_Name",
                              "Requester_Dept", "Source_Language", "Target_Language",
                              "Document_Type", "Original_File_Link", "Assigned_To",
                              "Translator_Name", "Assigned_Date", "Translated_File_Link",
                              "Translation_Date", "Reviewer", "Review_Date", "Review_Status",
                              "Final_PDF_Link", "Status", "Notes", "Deadline"]),
        ("Transport_Requests", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
                                 "Destination", "Purpose", "Passengers", "Date_Needed",
                                 "Time_Needed", "Return_Time", "Vehicle_Type",
                                 "Manager_Status", "Manager_Date",
                                 "Director_Status", "Director_Date",
                                 "Transport_Manager_Status", "Transport_Manager_Date",
                                 "Final_Status", "Assigned_Vehicle", "Assigned_Driver",
                                 "Notes", "PDF_Drive_Link", "Created_At"]),
        ("Commute_Log", ["Commute_ID", "Date", "Emp_Code", "Full_Name",
                          "Route", "Direction", "Vehicle_ID", "Driver_Code",
                          "Departure_Time", "Arrival_Time", "Status", "Notes"]),
        ("Trip_Log", ["Trip_ID", "Date", "Driver_Code", "Vehicle_ID",
                       "Start_KM", "End_KM", "Destination", "Purpose",
                       "Departure", "Arrival", "Status", "Fuel_Litres", "Notes"]),
        ("Vehicles", ["Vehicle_ID", "Plate_Number", "Type", "Brand", "Model",
                       "Year", "Color", "Capacity", "Status", "Assigned_Driver",
                       "Insurance_Expiry", "Registration_Expiry", "Last_Service_Date",
                       "Next_Service_KM", "Current_KM", "Notes"]),
        ("Driver_Compliance", ["Record_ID", "Date", "Driver_Code", "Check_Type",
                                "Result", "Notes", "Checked_By"]),
        ("Housing_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
                          "Request_Type", "Apartment_ID", "Details",
                          "Status", "Handled_By", "Notes", "Created_At"]),
        ("Apartments_Log", ["Apartment_ID", "Building", "Floor", "Unit",
                             "Capacity", "Current_Occupants", "Status",
                             "Condition", "Last_Inspection", "Notes"]),
        ("Safety_Log", ["Report_ID", "Date", "Emp_Code", "Full_Name", "Department",
                         "Incident_Type", "Description", "Location", "Severity",
                         "Action_Taken", "Status", "PDF_Drive_Link", "Created_At"]),
        ("Quality_Inspection_Log", ["Inspection_ID", "Date", "Inspector_Code",
                                     "Type", "Location", "Score", "Findings",
                                     "Corrective_Action", "Status", "PDF_Drive_Link"]),
        ("Operations_Reports", ["Report_ID", "Date", "Emp_Code", "Department",
                                 "Type", "Title", "Details", "Status",
                                 "PDF_Drive_Link", "Created_At"]),
        ("Purchase_Requests", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department",
                                "Item_Description", "Quantity", "Unit", "Estimated_Cost",
                                "Urgency", "Justification",
                                "Manager_Status", "Manager_Date",
                                "Supply_Status", "Supply_Date",
                                "Final_Status", "PDF_Drive_Link", "Created_At"]),
        ("Suppliers", ["Supplier_ID", "Name", "Contact_Person", "Phone", "Email",
                        "Category", "Rating", "Status", "Notes"]),
        ("Budget_Tracker", ["Month", "Department", "Category", "Budget", "Spent", "Remaining"]),
        ("Stock_Transactions", ["TX_ID", "Date", "Type", "Item_Code", "Item_Name",
                                 "Quantity", "Unit", "From_Location", "To_Location",
                                 "Emp_Code", "Notes", "Status"]),
        ("Current_Balance", ["Item_Code", "Item_Name", "Category", "Unit",
                              "Balance", "Min_Stock", "Location"]),
        ("JD_Drafts", ["JD_ID", "Date", "Emp_Code", "Department", "Position_Title",
                         "Status", "Content_JSON", "PDF_Drive_Link", "Created_At"]),
        ("Monthly_Schedule", ["Month", "Emp_Code", "Full_Name", "Department",
                               "Schedule_JSON", "Status", "Created_At"]),
    ]:
        _get_or_create(tab, headers)
        time.sleep(1)

    # ── Generic request engine tabs ────────────────────────
    print("[6/6] Generic request engine tabs...")

    generic_tabs = [
        ("Stock_Receiving_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Stock_Issue_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Stock_Transfer_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Waste_Report_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Daily_Ops_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Delivery_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Packaging_Report_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Purchase_Request_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Delivery_Confirm_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Material_Inspection_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Kitchen_Inspection_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Meal_Sample_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Housing_Assignment_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Housing_Vacate_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Housing_Maintenance_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Housing_Complaint_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
        ("Clearance_Log", ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]),
    ]
    for tab, headers in generic_tabs:
        _get_or_create(tab, headers)
        time.sleep(1)

    # ── Summary ────────────────────────────────────────────
    print("\n" + "═" * 50)
    print("AUDIT COMPLETE")
    print("═" * 50)
    print(f"Tabs checked:   {STATS['tabs_checked']}")
    print(f"Issues found:   {STATS['issues_found']}")
    print(f"Issues fixed:   {STATS['issues_fixed']}")
    if STATS["tabs_added"]:
        print(f"\nTabs ADDED ({len(STATS['tabs_added'])}):")
        for t in STATS["tabs_added"]:
            print(f"  + {t}")
    if STATS["tabs_modified"]:
        print(f"\nTabs MODIFIED ({len(STATS['tabs_modified'])}):")
        for t in STATS["tabs_modified"]:
            print(f"  ~ {t}")
    if STATS["columns_added"]:
        print(f"\nColumns ADDED ({len(STATS['columns_added'])}):")
        for c in STATS["columns_added"]:
            print(f"  + {c}")
    if STATS["test_data_added"]:
        print(f"\nTest data ADDED ({len(STATS['test_data_added'])}):")
        for t in STATS["test_data_added"]:
            print(f"  + {t}")
    if not STATS["tabs_added"] and not STATS["tabs_modified"] and not STATS["columns_added"]:
        print("\n✅ All tabs and columns are correct. No changes needed.")
    print("═" * 50)


if __name__ == "__main__":
    audit()
