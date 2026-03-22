"""
ROIN WORLD FZE -- All Request Type Configurations
===================================================
Each dict defines one request type for the generic engine.
Follows FULL_SYSTEM_BUILD.md Sections 3-13.
"""

# ── Warehouse ────────────────────────────────────────────────────────────────

STOCK_RECEIVING = {
    "name": "Stock Receiving",
    "prefix": "SRI",
    "tab": "Stock_Receiving_Log",
    "department": "Warehouse",
    "menu_callback": "bm_warehouse",
    "can_submit": ["Store_Keeper", "Warehouse_Specialist", "Warehouse_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Warehouse_Specialist", "label": "WH Specialist"},
        {"role": "Warehouse_Manager", "label": "WH Manager"},
    ],
    "fields": [
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "choice", "label": "Unit", "options": ["kg", "liter", "box", "piece"]},
        {"key": "warehouse", "type": "choice", "label": "Warehouse", "options": ["WH-1", "WH-2", "WH-3"]},
        {"key": "supplier_name", "type": "text", "label": "Supplier Name"},
        {"key": "delivery_note_number", "type": "text", "label": "Delivery Note Number"},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
    "pending_folder": "warehouse_pending", "approved_folder": "warehouse_approved",
}

STOCK_ISSUE = {
    "name": "Stock Issue Voucher",
    "prefix": "SIV",
    "tab": "Stock_Issue_Log",
    "department": "Warehouse",
    "menu_callback": "bm_warehouse",
    "can_submit": [],  # any employee
    "chain": [
        {"role": "Direct_Manager", "label": "Direct Manager"},
        {"role": "Warehouse_Manager", "label": "WH Manager"},
    ],
    "fields": [
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "choice", "label": "Unit", "options": ["kg", "liter", "box", "piece"]},
        {"key": "purpose", "type": "text", "label": "Purpose"},
        {"key": "requesting_department", "type": "text", "label": "Requesting Department"},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
    "assignment": {
        "assigner_role": "Warehouse_Manager",
        "executor_roles": ["Warehouse_Specialist", "Store_Keeper"],
    },
    "completion_fields": [
        {"key": "actual_qty_issued", "type": "number", "label": "Actual Qty Issued"},
        {"key": "batch_number", "type": "text", "label": "Batch Number"},
    ],
    "pending_folder": "warehouse_pending", "approved_folder": "warehouse_approved",
}

STOCK_TRANSFER = {
    "name": "Stock Transfer",
    "prefix": "STR",
    "tab": "Stock_Transfer_Log",
    "department": "Warehouse",
    "menu_callback": "bm_warehouse",
    "can_submit": ["Store_Keeper", "Warehouse_Specialist", "Warehouse_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Warehouse_Manager", "label": "WH Manager"},
    ],
    "fields": [
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "choice", "label": "Unit", "options": ["kg", "liter", "box", "piece"]},
        {"key": "from_warehouse", "type": "choice", "label": "From Warehouse", "options": ["WH-1", "WH-2", "WH-3"]},
        {"key": "to_warehouse", "type": "choice", "label": "To Warehouse", "options": ["WH-1", "WH-2", "WH-3"]},
        {"key": "reason", "type": "text", "label": "Reason"},
    ],
    "pending_folder": "warehouse_pending", "approved_folder": "warehouse_approved",
}

WASTE_REPORT = {
    "name": "Waste Report",
    "prefix": "WST",
    "tab": "Waste_Report_Log",
    "department": "Warehouse",
    "menu_callback": "bm_warehouse",
    "can_submit": ["Store_Keeper", "Warehouse_Specialist", "Warehouse_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Warehouse_Manager", "label": "WH Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "choice", "label": "Unit", "options": ["kg", "liter", "box", "piece"]},
        {"key": "warehouse", "type": "choice", "label": "Warehouse", "options": ["WH-1", "WH-2", "WH-3"]},
        {"key": "reason", "type": "choice", "label": "Reason", "options": ["Expired", "Damaged", "Contaminated", "Other"]},
        {"key": "estimated_loss_value", "type": "number", "label": "Estimated Loss Value (EGP)"},
        {"key": "notes", "type": "text", "label": "Notes"},
    ],
    "pending_folder": "warehouse_pending", "approved_folder": "warehouse_approved",
}

# ── Operations ───────────────────────────────────────────────────────────────

DAILY_OPS_REPORT = {
    "name": "Daily Operations Report",
    "prefix": "OPS",
    "tab": "Daily_Ops_Log",
    "department": "Operations",
    "menu_callback": "bm_operations",
    "can_submit": ["Operations_Specialist", "Operations_Coordinator", "Operations_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Operations_Manager", "label": "Ops Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "report_date", "type": "date", "label": "Report Date"},
        {"key": "shift", "type": "choice", "label": "Shift", "options": ["Day", "Night"]},
        {"key": "location", "type": "choice", "label": "Location", "options": ["Russian Kitchen", "Egyptian Kitchen", "Pastry-Soup Kitchen", "FoodTruck & Bakery"]},
        {"key": "hot_meals_produced", "type": "number", "label": "Hot Meals Produced"},
        {"key": "dry_meals_produced", "type": "number", "label": "Dry Meals Produced"},
        {"key": "special_meals_produced", "type": "number", "label": "Special Meals"},
        {"key": "total_meals_target", "type": "number", "label": "Total Meals Target"},
        {"key": "waste_kg", "type": "number", "label": "Waste (kg)"},
        {"key": "staff_present", "type": "number", "label": "Staff Present"},
        {"key": "staff_absent", "type": "number", "label": "Staff Absent"},
        {"key": "notes", "type": "text", "label": "Notes / Incidents (or type -)"},
    ],
}

# ── Packaging & Delivery ─────────────────────────────────────────────────────

DELIVERY_ASSIGNMENT = {
    "name": "Delivery Assignment",
    "prefix": "DEL",
    "tab": "Delivery_Log",
    "department": "Packaging & Delivery",
    "menu_callback": "bm_operations",
    "can_submit": ["Operations_Manager", "Operations_Specialist", "Bot_Manager"],
    "chain": [
        {"role": "Packaging_Manager", "label": "Packaging Manager"},
    ],
    "fields": [
        {"key": "delivery_date", "type": "date", "label": "Delivery Date"},
        {"key": "shift", "type": "choice", "label": "Shift", "options": ["Day", "Night"]},
        {"key": "destination", "type": "text", "label": "Destination"},
        {"key": "meal_type", "type": "choice", "label": "Meal Type", "options": ["Hot", "Dry", "Special", "Mixed"]},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "pickup_location", "type": "choice", "label": "Pickup Location", "options": ["Russian Kitchen", "Egyptian Kitchen", "Pastry-Soup Kitchen", "FoodTruck & Bakery"]},
        {"key": "required_time", "type": "text", "label": "Required Time (HH:MM)"},
        {"key": "special_instructions", "type": "text", "label": "Special Instructions (or type -)"},
    ],
    "assignment": {
        "assigner_role": "Packaging_Manager",
        "executor_roles": ["Packaging_Specialist"],
    },
    "completion_fields": [
        {"key": "actual_quantity_delivered", "type": "number", "label": "Actual Qty Delivered"},
        {"key": "delivery_time", "type": "text", "label": "Delivery Time (HH:MM)"},
        {"key": "issues", "type": "text", "label": "Issues (or type -)"},
    ],
    "pending_folder": "packaging_pending", "approved_folder": "packaging_approved",
}

PACKAGING_DAILY_REPORT = {
    "name": "Packaging Daily Report",
    "prefix": "PKG",
    "tab": "Packaging_Report_Log",
    "department": "Packaging & Delivery",
    "menu_callback": "bm_operations",
    "can_submit": ["Packaging_Specialist", "Packaging_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Packaging_Manager", "label": "Packaging Manager"},
    ],
    "fields": [
        {"key": "report_date", "type": "date", "label": "Report Date"},
        {"key": "shift", "type": "choice", "label": "Shift", "options": ["Day", "Night"]},
        {"key": "total_meals_received", "type": "number", "label": "Total Meals Received"},
        {"key": "total_meals_delivered", "type": "number", "label": "Total Meals Delivered"},
        {"key": "total_meals_damaged", "type": "number", "label": "Total Meals Damaged"},
        {"key": "delivery_points_served", "type": "number", "label": "Delivery Points Served"},
        {"key": "delays", "type": "choice", "label": "Delays?", "options": ["No", "Yes"]},
        {"key": "delay_details", "type": "text", "label": "Delay Details (or type -)"},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
}

# ── Purchasing / Supply ──────────────────────────────────────────────────────

PURCHASE_REQUEST = {
    "name": "Purchase Request",
    "prefix": "PUR",
    "tab": "Purchase_Request_Log",
    "pending_folder": "purchasing_pending", "approved_folder": "purchasing_approved",
    "department": "Purchasing",
    "menu_callback": "bm_supply",
    "can_submit": ["Direct_Manager", "Supervisor", "Bot_Manager"],
    "chain": [
        {"role": "Director", "label": "Director"},
        {"role": "Supply_Manager", "label": "Supply Manager"},
    ],
    "fields": [
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "text", "label": "Unit"},
        {"key": "estimated_unit_cost", "type": "number", "label": "Estimated Unit Cost (EGP)"},
        {"key": "estimated_total_cost", "type": "number", "label": "Estimated Total Cost (EGP)"},
        {"key": "urgency", "type": "choice", "label": "Urgency", "options": ["Normal", "Urgent", "Critical"]},
        {"key": "required_by_date", "type": "date", "label": "Required By Date"},
        {"key": "category", "type": "choice", "label": "Category", "options": ["Food", "Equipment", "Cleaning", "Office", "Safety", "Other"]},
        {"key": "justification", "type": "text", "label": "Justification"},
    ],
    "assignment": {
        "assigner_role": "Supply_Manager",
        "executor_roles": ["Supply_Specialist"],
    },
    "completion_fields": [
        {"key": "actual_supplier", "type": "text", "label": "Actual Supplier"},
        {"key": "actual_total_cost", "type": "number", "label": "Actual Total Cost (EGP)"},
        {"key": "invoice_number", "type": "text", "label": "Invoice Number"},
    ],
}

DELIVERY_CONFIRMATION = {
    "name": "Delivery Confirmation",
    "prefix": "DCF",
    "tab": "Delivery_Confirm_Log",
    "pending_folder": "purchasing_pending", "approved_folder": "purchasing_approved",
    "department": "Purchasing",
    "menu_callback": "bm_supply",
    "can_submit": ["Supply_Specialist", "Supply_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Supply_Manager", "label": "Supply Manager"},
        {"role": "Warehouse_Manager", "label": "WH Manager"},
    ],
    "fields": [
        {"key": "linked_purchase_id", "type": "text", "label": "Linked Purchase Request ID"},
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity_ordered", "type": "number", "label": "Quantity Ordered"},
        {"key": "quantity_received", "type": "number", "label": "Quantity Received"},
        {"key": "unit", "type": "text", "label": "Unit"},
        {"key": "condition", "type": "choice", "label": "Condition", "options": ["Good", "Partial_Damage", "Major_Damage", "Wrong_Item"]},
        {"key": "supplier_name", "type": "text", "label": "Supplier Name"},
        {"key": "delivery_note_number", "type": "text", "label": "Delivery Note Number"},
        {"key": "discrepancy_notes", "type": "text", "label": "Discrepancy Notes (or type -)"},
    ],
}

# ── Quality Control ──────────────────────────────────────────────────────────

MATERIAL_INSPECTION = {
    "name": "Material Inspection",
    "prefix": "QMI",
    "tab": "Material_Inspection_Log",
    "pending_folder": "quality_pending", "approved_folder": "quality_approved",
    "department": "Quality Control",
    "menu_callback": "bm_quality",
    "can_submit": ["Quality_Specialist", "Quality_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Quality_Manager", "label": "Quality Manager"},
    ],
    "fields": [
        {"key": "inspection_date", "type": "date", "label": "Inspection Date"},
        {"key": "supplier_name", "type": "text", "label": "Supplier Name"},
        {"key": "item_name", "type": "text", "label": "Item Name"},
        {"key": "quantity", "type": "number", "label": "Quantity"},
        {"key": "unit", "type": "text", "label": "Unit"},
        {"key": "temperature_check", "type": "choice", "label": "Temperature Check", "options": ["Pass", "Fail", "N/A"]},
        {"key": "visual_check", "type": "choice", "label": "Visual Check", "options": ["Pass", "Fail"]},
        {"key": "packaging_check", "type": "choice", "label": "Packaging Check", "options": ["Pass", "Fail"]},
        {"key": "expiry_date_check", "type": "choice", "label": "Expiry Date Check", "options": ["Pass", "Fail"]},
        {"key": "overall_result", "type": "choice", "label": "Overall Result", "options": ["Accepted", "Rejected", "Accepted_With_Notes"]},
        {"key": "rejection_reason_detail", "type": "text", "label": "Rejection Reason (or type -)"},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
}

KITCHEN_INSPECTION = {
    "name": "Kitchen Inspection",
    "prefix": "QKI",
    "tab": "Kitchen_Inspection_Log",
    "pending_folder": "quality_pending", "approved_folder": "quality_approved",
    "department": "Quality Control",
    "menu_callback": "bm_quality",
    "can_submit": ["Quality_Specialist", "Quality_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Quality_Manager", "label": "Quality Manager"},
        {"role": "Operations_Manager", "label": "Ops Manager"},
    ],
    "fields": [
        {"key": "inspection_date", "type": "date", "label": "Inspection Date"},
        {"key": "location", "type": "choice", "label": "Location", "options": ["Russian Kitchen", "Egyptian Kitchen", "Pastry-Soup Kitchen", "FoodTruck & Bakery"]},
        {"key": "food_handling_score", "type": "choice", "label": "Food Handling (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "cleanliness_score", "type": "choice", "label": "Cleanliness (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "temperature_compliance", "type": "choice", "label": "Temperature Compliance (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "pest_control_score", "type": "choice", "label": "Pest Control (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "staff_hygiene_score", "type": "choice", "label": "Staff Hygiene (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "equipment_condition", "type": "choice", "label": "Equipment Condition (1-5)", "options": ["1", "2", "3", "4", "5"]},
        {"key": "critical_violations", "type": "text", "label": "Critical Violations (or type -)"},
        {"key": "corrective_actions", "type": "text", "label": "Corrective Actions Required (or type -)"},
    ],
}

MEAL_SAMPLE_TEST = {
    "name": "Meal Sample Test",
    "prefix": "QMS",
    "tab": "Meal_Sample_Log",
    "pending_folder": "quality_pending", "approved_folder": "quality_approved",
    "department": "Quality Control",
    "menu_callback": "bm_quality",
    "can_submit": ["Quality_Specialist", "Quality_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Quality_Manager", "label": "Quality Manager"},
    ],
    "fields": [
        {"key": "test_date", "type": "date", "label": "Test Date"},
        {"key": "meal_type", "type": "choice", "label": "Meal Type", "options": ["Hot", "Dry", "Special"]},
        {"key": "sample_location", "type": "choice", "label": "Sample Location", "options": ["Russian Kitchen", "Egyptian Kitchen", "Pastry-Soup Kitchen", "FoodTruck & Bakery"]},
        {"key": "temperature_at_serving", "type": "number", "label": "Temperature at Serving (C)"},
        {"key": "taste_check", "type": "choice", "label": "Taste Check", "options": ["Pass", "Fail"]},
        {"key": "appearance_check", "type": "choice", "label": "Appearance Check", "options": ["Pass", "Fail"]},
        {"key": "portion_size_check", "type": "choice", "label": "Portion Size Check", "options": ["Pass", "Fail"]},
        {"key": "overall_result", "type": "choice", "label": "Overall Result", "options": ["Pass", "Fail"]},
        {"key": "failure_details", "type": "text", "label": "Failure Details (or type -)"},
    ],
}

# ── Housing ──────────────────────────────────────────────────────────────────

HOUSING_ASSIGNMENT = {
    "name": "Housing Assignment",
    "prefix": "HSA",
    "tab": "Housing_Assignment_Log",
    "pending_folder": "housing_pending", "approved_folder": "housing_approved",
    "department": "Housing",
    "menu_callback": "bm_housing",
    "can_submit": ["HR_Staff", "Housing_Specialist", "Housing_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Housing_Manager", "label": "Housing Manager"},
    ],
    "fields": [
        {"key": "emp_code_assigned", "type": "text", "label": "Employee Code to Assign"},
        {"key": "apartment_id", "type": "text", "label": "Apartment ID (e.g. APT-001)"},
        {"key": "move_in_date", "type": "date", "label": "Move-in Date"},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
}

HOUSING_VACATE = {
    "name": "Housing Vacate",
    "prefix": "HSV",
    "tab": "Housing_Vacate_Log",
    "pending_folder": "housing_pending", "approved_folder": "housing_approved",
    "department": "Housing",
    "menu_callback": "bm_housing",
    "can_submit": ["HR_Staff", "Housing_Specialist", "Housing_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Housing_Manager", "label": "Housing Manager"},
    ],
    "fields": [
        {"key": "emp_code_vacating", "type": "text", "label": "Employee Code Vacating"},
        {"key": "apartment_id", "type": "text", "label": "Apartment ID"},
        {"key": "vacate_date", "type": "date", "label": "Vacate Date"},
        {"key": "reason", "type": "choice", "label": "Reason", "options": ["Termination", "Transfer", "Voluntary"]},
        {"key": "room_condition", "type": "choice", "label": "Room Condition", "options": ["Good", "Damaged", "Needs_Repair"]},
        {"key": "damage_notes", "type": "text", "label": "Damage Notes (or type -)"},
    ],
}

HOUSING_MAINTENANCE = {
    "name": "Housing Maintenance Request",
    "prefix": "HSM",
    "tab": "Housing_Maintenance_Log",
    "pending_folder": "housing_pending", "approved_folder": "housing_approved",
    "department": "Housing",
    "menu_callback": "bm_housing",
    "can_submit": [],  # any employee
    "chain": [
        {"role": "Housing_Manager", "label": "Housing Manager"},
    ],
    "fields": [
        {"key": "apartment_id", "type": "text", "label": "Apartment ID"},
        {"key": "problem_type", "type": "choice", "label": "Problem Type", "options": ["Plumbing", "Electrical", "Door_Window", "AC_Heating", "Furniture", "Pest", "Other"]},
        {"key": "description", "type": "text", "label": "Problem Description"},
        {"key": "urgency", "type": "choice", "label": "Urgency", "options": ["Normal", "Urgent", "Emergency"]},
    ],
    "assignment": {
        "assigner_role": "Housing_Manager",
        "executor_roles": ["Housing_Specialist"],
    },
    "completion_fields": [
        {"key": "fix_description", "type": "text", "label": "Fix Description"},
        {"key": "fix_cost", "type": "number", "label": "Fix Cost (EGP, 0 if free)"},
    ],
}

HOUSING_COMPLAINT = {
    "name": "Housing Complaint",
    "prefix": "HSC",
    "tab": "Housing_Complaint_Log",
    "pending_folder": "housing_pending", "approved_folder": "housing_approved",
    "department": "Housing",
    "menu_callback": "bm_housing",
    "can_submit": [],  # any employee
    "chain": [
        {"role": "Housing_Manager", "label": "Housing Manager"},
        {"role": "HR_Manager", "label": "HR Manager"},
    ],
    "fields": [
        {"key": "complaint_type", "type": "choice", "label": "Complaint Type", "options": ["Noise", "Cleanliness", "Behavior", "Safety", "Other"]},
        {"key": "description", "type": "text", "label": "Description"},
        {"key": "apartment_id", "type": "text", "label": "Apartment ID"},
    ],
}

# ── HR: Deductions & Bonuses ─────────────────────────────────────────────────

SALARY_DEDUCTION = {
    "name": "Salary Deduction",
    "prefix": "DED",
    "tab": "Deduction_Log",
    "pending_folder": "hr_deductions_pending", "approved_folder": "hr_deductions_approved",
    "department": "HR",
    "menu_callback": "bm_hr",
    "can_submit": ["Direct_Manager", "HR_Staff", "HR_Manager", "Bot_Manager"],
    "chain": [
        {"role": "HR_Manager", "label": "HR Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "target_emp_code", "type": "text", "label": "Employee Code"},
        {"key": "deduction_type", "type": "choice", "label": "Deduction Type", "options": ["Late_Arrival", "Absence", "Violation", "Damage", "Other"]},
        {"key": "amount", "type": "number", "label": "Amount (EGP)"},
        {"key": "month", "type": "text", "label": "Month (MM/YYYY)"},
        {"key": "description", "type": "text", "label": "Description"},
    ],
}

BONUS_REQUEST = {
    "name": "Bonus Request",
    "prefix": "BON",
    "tab": "Bonus_Log",
    "pending_folder": "hr_deductions_pending", "approved_folder": "hr_deductions_approved",
    "department": "HR",
    "menu_callback": "bm_hr",
    "can_submit": ["Direct_Manager", "Bot_Manager"],
    "chain": [
        {"role": "HR_Manager", "label": "HR Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "target_emp_code", "type": "text", "label": "Employee Code"},
        {"key": "bonus_type", "type": "choice", "label": "Bonus Type", "options": ["Performance", "Overtime_Bonus", "Holiday_Bonus", "Special", "Other"]},
        {"key": "amount", "type": "number", "label": "Amount (EGP)"},
        {"key": "month", "type": "text", "label": "Month (MM/YYYY)"},
        {"key": "justification", "type": "text", "label": "Justification"},
    ],
}

# ── HR: Warning Letters ──────────────────────────────────────────────────────

WARNING_LETTER = {
    "name": "Warning Letter",
    "prefix": "WRN",
    "tab": "Warning_Log",
    "pending_folder": "hr_warnings_pending", "approved_folder": "hr_warnings_approved",
    "department": "HR",
    "menu_callback": "bm_hr",
    "can_submit": ["Direct_Manager", "HR_Staff", "HR_Manager", "Bot_Manager"],
    "chain": [
        {"role": "HR_Manager", "label": "HR Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "target_emp_code", "type": "text", "label": "Employee Code"},
        {"key": "warning_level", "type": "choice", "label": "Warning Level", "options": ["Verbal", "First_Written", "Second_Written", "Final", "Termination_Review"]},
        {"key": "violation_type", "type": "choice", "label": "Violation Type", "options": ["Attendance", "Misconduct", "Safety_Violation", "Insubordination", "Theft", "Other"]},
        {"key": "description", "type": "text", "label": "Description of Incident"},
        {"key": "date_of_incident", "type": "date", "label": "Date of Incident"},
        {"key": "witnesses", "type": "text", "label": "Witnesses (or type -)"},
    ],
}

# ── HR: Salary Advance ──────────────────────────────────────────────────────

SALARY_ADVANCE = {
    "name": "Salary Advance Request",
    "prefix": "ADV",
    "tab": "Advance_Log",
    "pending_folder": "hr_advance_pending", "approved_folder": "hr_advance_approved",
    "department": "HR",
    "menu_callback": "bm_hr",
    "can_submit": [],  # any employee
    "chain": [
        {"role": "Direct_Manager", "label": "Direct Manager"},
        {"role": "HR_Manager", "label": "HR Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "amount_requested", "type": "number", "label": "Amount Requested (EGP)"},
        {"key": "reason", "type": "text", "label": "Reason"},
        {"key": "repayment_plan", "type": "choice", "label": "Repayment Plan", "options": ["Next_Salary", "2_Installments", "3_Installments"]},
    ],
}

# ── HR: End of Service Clearance ─────────────────────────────────────────────

END_OF_SERVICE = {
    "name": "End of Service Clearance",
    "prefix": "EOS",
    "tab": "End_Of_Service_Log",
    "pending_folder": "hr_clearance_pending", "approved_folder": "hr_clearance_approved",
    "department": "HR",
    "menu_callback": "bm_hr",
    "can_submit": ["HR_Staff", "HR_Manager", "Bot_Manager"],
    "chain": [
        {"role": "Direct_Manager", "label": "Direct Manager"},
        {"role": "Warehouse_Manager", "label": "Warehouse Manager"},
        {"role": "Housing_Manager", "label": "Housing Manager"},
        {"role": "Safety_Manager", "label": "Safety Manager"},
        {"role": "HR_Manager", "label": "HR Manager"},
        {"role": "Director", "label": "Director"},
    ],
    "fields": [
        {"key": "target_emp_code", "type": "text", "label": "Employee Code"},
        {"key": "last_working_day", "type": "date", "label": "Last Working Day"},
        {"key": "reason", "type": "choice", "label": "Reason", "options": ["Resignation", "Termination", "Contract_End", "Mutual_Agreement"]},
        {"key": "notes", "type": "text", "label": "Notes (or type -)"},
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
# MASTER LIST — import this in generic_request_engine.py
# ══════════════════════════════════════════════════════════════════════════════

ALL_REQUEST_TYPES = [
    # Warehouse (Section 3)
    STOCK_RECEIVING,
    STOCK_ISSUE,
    STOCK_TRANSFER,
    WASTE_REPORT,
    # Operations (Section 5)
    DAILY_OPS_REPORT,
    # Packaging & Delivery (Section 6)
    DELIVERY_ASSIGNMENT,
    PACKAGING_DAILY_REPORT,
    # Purchasing (Section 7)
    PURCHASE_REQUEST,
    DELIVERY_CONFIRMATION,
    # Quality Control (Section 8)
    MATERIAL_INSPECTION,
    KITCHEN_INSPECTION,
    MEAL_SAMPLE_TEST,
    # Housing (Section 9)
    HOUSING_ASSIGNMENT,
    HOUSING_VACATE,
    HOUSING_MAINTENANCE,
    HOUSING_COMPLAINT,
    # HR: Deductions & Bonuses (Section 10)
    SALARY_DEDUCTION,
    BONUS_REQUEST,
    # HR: Warning Letters (Section 11)
    WARNING_LETTER,
    # HR: Salary Advance (Section 12)
    SALARY_ADVANCE,
    # HR: End of Service (Section 13)
    END_OF_SERVICE,
]
