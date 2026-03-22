# FULL SYSTEM BUILD — All Departments + Task Management + Employee Reports
# ═══════════════════════════════════════════════════════════════════════════
# Read these files FIRST in this exact order:
# 1. REQUEST_FLOW_RULES.md (standard flow for all requests)
# 2. PROJECT_RULES.md (universal rules)
# 3. SESSION_3_HANDOFF.md (current project state)
# 4. This file
#
# Reference database: ROIN_WORLD_FZE_System_v6 (1).xlsx
# Build ONE section at a time. After each: "Ready to test" → STOP.
# When next step is running bot: python3 bot.py

====================================================================
# GLOBAL: DRIVE FOLDERS — ALL 36 FOLDER IDs
====================================================================

Replace the ENTIRE DRIVE_FOLDERS dict in config.py with this:

```python
DRIVE_FOLDERS = {
    # ── HR Leave ──
    "hr_leave_pending":           "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "hr_leave_approved":          "1Wr1DfpxD3vYnmr8jEamZu1Zy7MU_Cr43",

    # ── HR Memos ──
    "hr_memos_pending":           "1g8kCuwLMXdl5ZioUQSbSQzYkP235DFZL",
    "hr_memos_approved":          "15wgrvLOe1Ru60t7TKHFpQqSXCBVtuCLp",

    # ── HR Warnings ──
    "hr_warnings_pending":        "1pA_l_Nnh5lZ08g5V2y0fWVnTTETQjfx8",
    "hr_warnings_approved":       "1JN-T-S0Pc3BHfWtNULbOiJGF3kNnZIer",

    # ── HR Deductions & Bonuses ──
    "hr_deductions_pending":      "164igINEAOdJ9wDkMqeUiTQZmKwr-Phc0",
    "hr_deductions_approved":     "1eZFetwUPTLj9vU1NrKwWnqlxQAB0cy5j",

    # ── HR Salary Advance ──
    "hr_advance_pending":         "1s_haEeB7x8q-WqkAPc0ZLhdchekTwKs1",
    "hr_advance_approved":        "13hgyFGFPYl5BIs91OpTYBOknsveeXyQ7",

    # ── HR Clearance ──
    "hr_clearance_pending":       "1fKWYQdyEWnzFIS1a6baarGHmpZMB0JvG",
    "hr_clearance_approved":      "13k5QONued8IUFCQUtB_3Zm4rx-wiZxFQ",

    # ── HR Certificates ──
    "hr_certificates_pending":    "1B8BBjCrUK2SUo6jXmbjB-9Q41gY4V1tA",
    "hr_certificates_approved":   "1VjYFI10cLojVUOZR6vuxynbKz76g2JzB",

    # ── HR Evaluations ──
    "hr_evaluations_pending":     "1p0XINtKKS-Vrg4BkY8DlYJYmILrJiiBf",
    "hr_evaluations_approved":    "1tA3IWgyi-9S8e42W_CMVv4dNSdENdpUq",

    # ── Warehouse ──
    "warehouse_pending":          "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "warehouse_approved":         "1GfSUmyBHKES0O1wAve22_PBkvfYDzB-C",

    # ── Translation ──
    "translation_pending":        "1IjBVhPSfJpewzAJkNvgPA3tpCWoxvzRe",
    "translation_approved":       "1CKR3_Uo8oA0C70p7RFGloGy29iH6l5Ib",

    # ── Operations ──
    "operations_pending":         "1jXCdwUcfrLnc0nIhMpt1-o7KCYGyOITZ",
    "operations_approved":        "1Q819q6JQoT8T8aPNoYOrwhcYvoSyWTa7",

    # ── Packaging & Delivery ──
    "packaging_pending":          "1DAhAJr-m83T_eciaAHlAQlxB4VdTi0fr",
    "packaging_approved":         "1YUYfof-t_wDfhuyN3eTWjORNUD-yZKAE",

    # ── Purchasing ──
    "purchasing_pending":         "1OVKS4LC6j5x0BB8w5hYfvROs6425Q4wR",
    "purchasing_approved":        "1dfT_ltnPCsKApgu6i4-iOhcAopxByETc",

    # ── Quality Control ──
    "quality_pending":            "1FowBChZdpmIcQE9hPbLUFLHiArrnHrj2",
    "quality_approved":           "1qtbXInecUhBKu4Uyhv8HoeLFV4l3XuQV",

    # ── Housing ──
    "housing_pending":            "1LG08YDtU4MwJJSl4AbFhbV4PH6e_142j",
    "housing_approved":           "1tEbhKgmDKUGEwuQb0XtLsgEJoPsDnUVO",

    # ── Transport ──
    "transport_pending":          "1KpswSke5iljbUO-HjeZpFG8cCHWR9X5n",
    "transport_approved":         "10gMKjUWaoYfFMgGGjNFo9pLUHWYjtLTA",

    # ── Recruitment ──
    "recruitment_pending":        "1lSHMZircVL183zpvZfza2kddvB_jsplq",
    "recruitment_approved":       "1YthuuMAcEZ9FMtggszVVvliqPz2cBV-E",

    # ── Job Descriptions ──
    "jd_pending":                 "1SRScmun5KKMVzXV9RknE2BqhkWVXOrUt",
    "jd_approved":                "1c2eoj7HNnjB-YsqCZ3n4_NsY9-6TMh_v",

    # ── Legacy aliases (backward compatibility) ──
    "drafts":                     "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "approved":                   "1GfSUmyBHKES0O1wAve22_PBkvfYDzB-C",
    "in_process":                 "1NAfStAs3mcKq8wYlbIcNTlNqgYGDPXlz",
    "memo_drafts":                "1g8kCuwLMXdl5ZioUQSbSQzYkP235DFZL",
    "memo_approved":              "15wgrvLOe1Ru60t7TKHFpQqSXCBVtuCLp",
    "leave_approvals":            "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "leave_orders":               "1PO1W_MmAP0lB7sfxX5InPtoiJcN6FVsa",
    "job_descriptions":           "1SRScmun5KKMVzXV9RknE2BqhkWVXOrUt",
    "certificates":               "1B8BBjCrUK2SUo6jXmbjB-9Q41gY4V1tA",
    "evaluations":                "1p0XINtKKS-Vrg4BkY8DlYJYmILrJiiBf",
    "requisitions":               "1lSHMZircVL183zpvZfza2kddvB_jsplq",
    "safety_reports":             "1jXCdwUcfrLnc0nIhMpt1-o7KCYGyOITZ",
    "transport_requests":         "1KpswSke5iljbUO-HjeZpFG8cCHWR9X5n",
}
```

RULE: During approval → "[dept]_pending". Final approved → "[dept]_approved".
Update ALL existing handlers to use the correct new folder keys.

====================================================================
# GLOBAL: TEST EMPLOYEES — 40 ACCOUNTS
====================================================================

Add to Employee_DB AND User_Registry.
Password for ALL = Pass@[Emp_Code].
Employee 1007 (Bot_Manager) already exists — DO NOT modify.

## Company Director
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 2001 | Viktor Petrov | Management | Company Director | Director | — |

## HR Department
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 2010 | Layla HR Manager | HR | HR Manager | HR_Manager | 2001 |
| 2011 | Dina HR Staff 1 | HR | HR Specialist | HR_Staff | 2010 |
| 2012 | Nada HR Staff 2 | HR | HR Specialist | HR_Staff | 2010 |

## Egyptian Kitchen
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 2020 | Youssef Kitchen Mgr | Egyptian Kitchen | Head Chef | Direct_Manager | 2001 |
| 2021 | Amr Kitchen Supervisor | Egyptian Kitchen | Shift Supervisor | Supervisor | 2020 |
| 2022 | Tamer Kitchen Worker 1 | Egyptian Kitchen | Cook | Employee | 2020 |
| 2023 | Hossam Kitchen Worker 2 | Egyptian Kitchen | Cook | Employee | 2020 |

## Russian Kitchen
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 2030 | Alexei Russian Kitchen Mgr | Russian Kitchen | Head Chef | Direct_Manager | 2001 |
| 2031 | Igor Russian Cook | Russian Kitchen | Cook | Employee | 2030 |

## Warehouse
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3001 | Khaled Warehouse Mgr | Warehouse | Warehouse Manager | Warehouse_Manager | 2001 |
| 3002 | Hassan WH Assistant | Warehouse | Warehouse Supervisor | Warehouse_Specialist | 3001 |
| 3003 | Ali Store Keeper 1 | Warehouse | Store Keeper WH-1 | Store_Keeper | 3001 |
| 3004 | Omar Store Keeper 2 | Warehouse | Store Keeper WH-2 | Store_Keeper | 3001 |
| 3005 | Mahmoud Store Keeper 3 | Warehouse | Store Keeper WH-3 | Store_Keeper | 3001 |

## Translation
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3010 | Natalia Translation Mgr | Translation | Translation Manager | Translation_Manager | 2001 |
| 3011 | Dmitry Translator RU | Translation | Translator RU-AR | Translator | 3010 |
| 3012 | Fatma Translator AR | Translation | Translator AR-EN | Translator | 3010 |
| 3013 | Sergei Translator RU2 | Translation | Translator RU-EN | Translator | 3010 |
| 3014 | Maha Translator AR2 | Translation | Translator AR-RU | Translator | 3010 |
| 3015 | Pavel Translator RU3 | Translation | Translator EN-RU | Translator | 3010 |

## Operations
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3020 | Ahmed Operations Mgr | Operations | Operations Manager | Operations_Manager | 2001 |
| 3021 | Yasser Operations Spec | Operations | Operations Specialist | Operations_Specialist | 3020 |
| 3022 | Tarek Operations Coord | Operations | Operations Coordinator | Operations_Coordinator | 3020 |

## Packaging & Delivery (NEW)
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3030 | Samir Packaging Mgr | Packaging & Delivery | Packaging Manager | Packaging_Manager | 3020 |
| 3031 | Hany Packaging Spec | Packaging & Delivery | Packaging Specialist | Packaging_Specialist | 3030 |
| 3032 | Wael Delivery Coord | Packaging & Delivery | Delivery Coordinator | Packaging_Specialist | 3030 |

## Purchasing
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3040 | Ibrahim Supply Mgr | Purchasing | Supply Manager | Supply_Manager | 2001 |
| 3041 | Ayman Supply Spec | Purchasing | Supply Specialist | Supply_Specialist | 3040 |

## Quality Control
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3050 | Rami Quality Mgr | Quality Control | Quality Manager | Quality_Manager | 2001 |
| 3051 | Nour Quality Spec | Quality Control | Quality Specialist | Quality_Specialist | 3050 |

## Housing
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3060 | Fathi Housing Mgr | Housing | Housing Manager | Housing_Manager | 2001 |
| 3061 | Samy Housing Spec | Housing | Housing Specialist | Housing_Specialist | 3060 |

## Transport
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3070 | Magdy Transport Mgr | Transportation | Transport Manager | Transport_Manager | 2001 |
| 3071 | Walid Driver 1 | Transportation | Driver | Driver | 3070 |
| 3072 | Tarek Driver 2 | Transportation | Driver | Driver | 3070 |

## Safety
| Code | Full_Name | Department | Job_Title | Bot_Role | Manager_Code |
|------|-----------|------------|-----------|----------|-------------|
| 3080 | Sherif Safety Mgr | Safety | Safety Manager | Safety_Manager | 2001 |

## For ALL test employees:
- Status: Active
- Approval_Chain: MGR_HR_DIR
- Shift_Hours: 8
- Off_Type: Friday
- Preferred_Language: EN
- Annual_Leave_Balance: 21
- Work_Location: per department (kitchen staff → their kitchen, warehouse → Warehouse, etc.)
- Supervisor_Code: same as Manager_Code

## New Roles → add to config.py VALID_ROLES:
"Packaging_Manager", "Packaging_Specialist"

====================================================================
# SECTION 1: VERIFY LEAVE SYSTEM
====================================================================

Already built. Verify end-to-end. All types working.
PDF at every stage → "hr_leave_pending". Final → "hr_leave_approved".
If broken → fix. If working → skip.

====================================================================
# SECTION 2: РАСПОРЯЖЕНИЕ FLOW UPDATE
====================================================================

New flow after Director approves leave:
→ HR_Staff gets notification → opens → generates draft Распоряжение
→ Reviews → submits → HR_Manager approves → Director signs → employee gets final PDF.

```
Build a new Распоряжение
Department: HR
Submitted by: HR_Staff (triggered after leave Director-approval)
Chain: HR_Manager → Director
Fields: linked_leave_id, order_number (auto: ОП-YYYY-NNN), document_text (auto bilingual RU+EN)
```
Reuse order_generator.py. Pending → "hr_leave_pending". Final → "hr_leave_approved".

====================================================================
# SECTION 3: WAREHOUSE
====================================================================

## 3A. Stock Receiving (IN)
```
Build a new Stock Receiving
Department: Warehouse
Submitted by: Store_Keeper
Chain: Warehouse_Specialist → Warehouse_Manager
Fields: item_name, quantity, unit (kg/liter/box/piece), warehouse (WH-1/WH-2/WH-3), supplier_name, delivery_note_number, photo_of_delivery_note, notes
```

## 3B. Stock Issue Voucher (OUT)
```
Build a new Stock Issue Voucher
Department: Warehouse
Submitted by: any Employee
Chain: Direct_Manager → Warehouse_Manager
Assignment: Warehouse_Manager → Warehouse_Specialist → Store_Keeper
Fields: item_name, quantity, unit, purpose, requesting_department, notes
On completion: actual_qty_issued, batch_number, photo_of_items
```

## 3C. Stock Transfer
```
Build a new Stock Transfer
Department: Warehouse
Submitted by: Store_Keeper, Warehouse_Specialist
Chain: Warehouse_Manager
Fields: item_name, quantity, unit, from_warehouse (WH-1/WH-2/WH-3), to_warehouse, reason
```

## 3D. Waste Report
```
Build a new Waste Report
Department: Warehouse
Submitted by: Store_Keeper, Warehouse_Specialist
Chain: Warehouse_Manager → Director
Fields: item_name, quantity, unit, warehouse, reason (Expired/Damaged/Contaminated/Other), photo_of_items, estimated_loss_value, notes
```

## 3E. Live Inventory
Current_Balance tab auto-updated: IN adds, OUT subtracts, Transfer moves, Waste subtracts.
LOW if below Min_Level. OUT if zero.

## 3F. Director Daily Warehouse Report
Scheduled (JobQueue) + on-demand. Shows received/issued/current stock/waste for today.

All warehouse docs: pending → "warehouse_pending". Approved → "warehouse_approved".

====================================================================
# SECTION 4: TRANSLATION
====================================================================

```
Build a new Translation Request
Department: Translation
Submitted by: any Direct_Manager, HR_Staff, HR_Manager
Chain: Translation_Manager
Assignment: Translation_Manager → Translator
Fields: document_title, source_language (AR/RU/EN), target_language (AR/RU/EN), deadline, urgency (Normal/Urgent/Critical), description, attached_file (upload)
On completion: translated_file (upload), translator_notes
```
Pending → "translation_pending". Done → "translation_approved".

====================================================================
# SECTION 5: OPERATIONS
====================================================================

## 5A. Daily Operations Report
```
Build a new Daily Operations Report
Department: Operations
Submitted by: Operations_Specialist, Operations_Coordinator
Chain: Operations_Manager → Director
Fields: report_date, shift (Day/Night), location, hot_meals_produced, dry_meals_produced, special_meals_produced, total_meals_target, meat_used_kg, chicken_used_kg, rice_used_kg, vegetables_used_kg, oil_used_liters, waste_kg, waste_reason, staff_present, staff_absent, incidents (optional), notes (optional)
```
Pending → "operations_pending". Approved → "operations_approved".

## 5B. Operations Dashboard
Today's production totals, ingredients, waste %, staff, per-location. For Director + Bot_Manager.

====================================================================
# SECTION 6: PACKAGING & DELIVERY (NEW)
====================================================================

New roles: Packaging_Manager, Packaging_Specialist

## 6A. Delivery Assignment
```
Build a new Delivery Assignment
Department: Packaging & Delivery
Submitted by: Operations_Manager, Operations_Specialist
Chain: Packaging_Manager
Assignment: Packaging_Manager → Packaging_Specialist
Fields: delivery_date, shift, destination, meal_type (Hot/Dry/Special/Mixed), quantity, pickup_location, required_time, special_instructions (optional)
On completion: actual_quantity_delivered, delivery_time, photo_of_delivery, issues (optional)
```

## 6B. Packaging Daily Report
```
Build a new Packaging Daily Report
Department: Packaging & Delivery
Submitted by: Packaging_Specialist
Chain: Packaging_Manager
Fields: report_date, shift, total_meals_received, total_meals_delivered, total_meals_damaged, damaged_reason (optional), delivery_points_served, delays (Yes/No), delay_details (optional), notes
```
Pending → "packaging_pending". Approved → "packaging_approved".

====================================================================
# SECTION 7: PURCHASING
====================================================================

## 7A. Purchase Request
```
Build a new Purchase Request
Department: Purchasing
Submitted by: any Direct_Manager
Chain: Director → Supply_Manager
Assignment: Supply_Manager → Supply_Specialist
Fields: item_name, quantity, unit, estimated_unit_cost, estimated_total_cost, urgency (Normal/Urgent/Critical), required_by_date, suggested_supplier (optional), justification, category (Food/Equipment/Cleaning/Office/Safety/Other)
On completion: actual_supplier, actual_unit_cost, actual_total_cost, invoice_number, delivery_date, photo_of_invoice
```

## 7B. Delivery Confirmation
```
Build a new Delivery Confirmation
Department: Purchasing
Submitted by: Supply_Specialist
Chain: Supply_Manager → Warehouse_Manager
Fields: linked_purchase_id, item_name, quantity_ordered, quantity_received, unit, condition (Good/Partial_Damage/Major_Damage/Wrong_Item), supplier_name, delivery_note_number, photo_of_goods, photo_of_delivery_note, discrepancy_notes (optional)
```
Approved by Warehouse_Manager → auto-triggers Stock Receiving (IN).

## 7C. Purchase Status Tracking
Supply_Specialist updates: Ordered → Shipped → Delivered → Completed. Each logged with timestamp.

Pending → "purchasing_pending". Approved → "purchasing_approved".

====================================================================
# SECTION 8: QUALITY CONTROL
====================================================================

## 8A. Material Inspection
```
Build a new Material Inspection
Department: Quality Control
Submitted by: Quality_Specialist
Chain: Quality_Manager
Fields: inspection_date, supplier_name, item_name, quantity, unit, delivery_note_number, temperature_check (Pass/Fail), visual_check (Pass/Fail), smell_check (Pass/Fail), packaging_check (Pass/Fail), expiry_date_check (Pass/Fail), overall_result (Accepted/Rejected/Accepted_With_Notes), rejection_reason (if rejected), photo_of_items, photo_of_label, notes
```
Rejected → notify Quality_Manager + Supply_Manager.

## 8B. Kitchen Hygiene Inspection
```
Build a new Kitchen Inspection
Department: Quality Control
Submitted by: Quality_Specialist
Chain: Quality_Manager → Operations_Manager
Fields: inspection_date, location, food_handling_score (1-5), cleanliness_score (1-5), temperature_compliance_score (1-5), pest_control_score (1-5), staff_hygiene_score (1-5), equipment_condition_score (1-5), overall_score (auto-avg), critical_violations (optional), corrective_actions_required (optional), photos (up to 3), follow_up_date (optional)
```

## 8C. Meal Sample Test
```
Build a new Meal Sample Test
Department: Quality Control
Submitted by: Quality_Specialist
Chain: Quality_Manager
Fields: test_date, meal_type (Hot/Dry/Special), sample_location, temperature_at_serving, taste_check (Pass/Fail), appearance_check (Pass/Fail), portion_size_check (Pass/Fail), foreign_object_check (Pass/Fail), overall_result (Pass/Fail), failure_details (if fail), corrective_action (if fail), photo_of_sample
```

## 8D. Quality Dashboard
Pass/reject rates, kitchen scores, sample results, top issues. For Director + Quality_Manager.

Pending → "quality_pending". Approved → "quality_approved".

====================================================================
# SECTION 9: HOUSING
====================================================================

## 9A. Apartments Tab
Pre-fill APT-001 to APT-120, Capacity=4, Status="Available".

## 9B. Housing Assignment
```
Build a new Housing Assignment
Department: Housing
Submitted by: HR_Staff, Housing_Specialist
Chain: Housing_Manager
Fields: emp_code, apartment_id (from available list), move_in_date, notes
On completion: key_handed (Yes/No), welcome_kit_given (Yes/No)
```
Auto-updates apartment occupancy.

## 9C. Housing Vacate
```
Build a new Housing Vacate
Department: Housing
Submitted by: HR_Staff, Housing_Specialist
Chain: Housing_Manager
Fields: emp_code, apartment_id, vacate_date, reason (Termination/Transfer/Voluntary), room_condition (Good/Damaged/Needs_Repair), damage_notes (optional), photo_of_room
On completion: key_returned (Yes/No), deductions_amount
```

## 9D. Housing Maintenance
```
Build a new Housing Maintenance Request
Department: Housing
Submitted by: any Employee
Chain: Housing_Manager
Assignment: Housing_Manager → Housing_Specialist
Fields: apartment_id (auto-filled), problem_type (Plumbing/Electrical/Door_Window/AC_Heating/Furniture/Pest/Other), description, urgency (Normal/Urgent/Emergency), photo_of_problem
On completion: fix_description, fix_cost, photo_after_fix
```
Final report: before/after photos + cost + timeline. Employee notified.

## 9E. Housing Complaint
```
Build a new Housing Complaint
Department: Housing
Submitted by: any Employee
Chain: Housing_Manager → HR_Manager
Fields: complaint_type (Noise/Cleanliness/Behavior/Safety/Other), description, apartment_id, accused_employee_code (optional), photo_evidence (optional)
```

## 9F. Housing Dashboard
Occupancy %, available beds, maintenance stats, assignments/vacates.

Pending → "housing_pending". Approved → "housing_approved".

====================================================================
# SECTION 10: DEDUCTIONS & BONUSES
====================================================================

## 10A. Salary Deduction
```
Build a new Salary Deduction
Department: HR
Submitted by: Direct_Manager, HR_Staff
Chain: HR_Manager → Director
Fields: emp_code, deduction_type (Late_Arrival/Absence/Violation/Damage/Other), amount, currency (EGP), month (MM/YYYY), description, supporting_evidence (optional)
```

## 10B. Bonus Request
```
Build a new Bonus Request
Department: HR
Submitted by: Direct_Manager
Chain: HR_Manager → Director
Fields: emp_code, bonus_type (Performance/Overtime_Bonus/Holiday_Bonus/Special/Other), amount, currency (EGP), month (MM/YYYY), justification
```
Pending → "hr_deductions_pending". Approved → "hr_deductions_approved".

====================================================================
# SECTION 11: WARNING LETTERS
====================================================================

```
Build a new Warning Letter
Department: HR
Submitted by: Direct_Manager, HR_Staff
Chain: HR_Manager → Director
Fields: emp_code, warning_level (Verbal/First_Written/Second_Written/Final/Termination_Review), violation_type (Attendance/Misconduct/Safety_Violation/Insubordination/Theft/Other), description, date_of_incident, witnesses (optional), previous_warnings_count (auto from history)
```
PDF: bilingual Arabic + English formal warning.
If Termination_Review → triggers separate process.
Pending → "hr_warnings_pending". Approved → "hr_warnings_approved".

====================================================================
# SECTION 12: SALARY ADVANCE
====================================================================

```
Build a new Salary Advance Request
Department: HR
Submitted by: any Employee
Chain: Direct_Manager → HR_Manager → Director
Fields: amount_requested, currency (EGP), reason, repayment_plan (Next_Salary/2_Installments/3_Installments), supporting_documents (optional)
```
Pending → "hr_advance_pending". Approved → "hr_advance_approved".

====================================================================
# SECTION 13: END OF SERVICE / CLEARANCE
====================================================================

```
Build a new End of Service Clearance
Department: HR
Submitted by: HR_Staff
Chain: Direct_Manager → Warehouse_Manager → Housing_Manager → Safety_Manager → HR_Manager → Director
Fields: emp_code, last_working_day, reason (Resignation/Termination/Contract_End/Mutual_Agreement), notes
On completion: final_settlement_amount, all_items_returned (Yes/No), outstanding_deductions
```
Each approver checks their department. Final PDF = full clearance with all sign-offs.
Pending → "hr_clearance_pending". Final → "hr_clearance_approved".

====================================================================
# SECTION 14: TASK MANAGEMENT
====================================================================

## 14A. Manager Assigns Tasks
Any Direct_Manager, Supervisor, or department manager can assign.

Tab: Tasks_Log
Columns: Task_ID (TSK-YYYY-NNNN), Created_At, Assigned_By, Assigned_To, Emp_Name (VLOOKUP=""), Department (VLOOKUP=""), Task_Title, Description, Priority (Low/Medium/High/Critical), Deadline, Status (New/In_Progress/Completed/Overdue/Cancelled), Started_At, Completed_At, Completion_Notes, Manager_Verified

Flow: Manager → 📌 Tasks → [➕ Assign Task] → pick employee → title, description, priority, deadline → submit → employee notified.

## 14B. Employee Task View
📋 My Tasks in EVERY employee's menu:

```
🔴 Overdue (1)
  TSK-2026-0042 — Clean cold storage — Due: 20/03 ⚠️ 2 days overdue

🟡 Due Today (2)
  TSK-2026-0045 — Prepare inventory report
  TSK-2026-0046 — Check freezer temps

🔵 Upcoming (3)
  TSK-2026-0047 — Monthly equipment check — Due: 25/03
  ...

✅ Completed Recently
  [View completed]
```

Tap task → detail → [▶️ Start] [✅ Mark Done] [💬 Add Note]

## 14C. Manager Task Dashboard
All team tasks: active, overdue, completed this week. View by employee or by status.

## 14D. Bot_Manager sees ALL tasks across all departments.

## 14E. Overdue check via JobQueue every hour.

====================================================================
# SECTION 15: EMPLOYEE SELF-REPORTS
====================================================================

## 15A. Add to ALL menus: 📊 My Reports

## 15B. Report types:
```
📊 My Reports
├── 💰 My Salary History (last 6 months)
├── 📉 My Deductions
├── ⏰ My Overtime Hours
├── 🕐 My Lateness Record
├── 🏖️ My Leave Summary
├── 📋 My Task Performance
├── ↩️ Main Menu
```

## 15C. Dummy Data
Create Payroll_History tab with 6 months dummy data for all test employees:
Columns: Emp_Code, Month, Basic_Salary, Deductions, Bonuses, OT_Payment, Net_Salary

## 15D. Report format example:
```
💰 My Salary — Last 6 Months
Oct 2025: Basic 8,000 | Ded -200 | OT +500 | Net: 8,300 EGP
Nov 2025: Basic 8,000 | Ded -0   | OT +750 | Net: 8,750 EGP
...
Average Net: 8,383 EGP
Total Deductions: 700 EGP
```

Each report reads from existing tabs (Payroll_History, Leave_Log, Leave_Balance, Attendance, Tasks_Log).

====================================================================
# BUILD ORDER
====================================================================

1. Global: Drive folders + test employees + new roles → "Ready to test"
2. Section 1: Verify leave → "Ready to test"
3. Section 2: Распоряжение update → "Ready to test"
4. Section 3: Warehouse → "Ready to test"
5. Section 4: Translation → "Ready to test"
6. Section 5: Operations → "Ready to test"
7. Section 6: Packaging → "Ready to test"
8. Section 7: Purchasing → "Ready to test"
9. Section 8: Quality → "Ready to test"
10. Section 9: Housing → "Ready to test"
11. Section 10: Deductions & Bonuses → "Ready to test"
12. Section 11: Warning Letters → "Ready to test"
13. Section 12: Salary Advance → "Ready to test"
14. Section 13: End of Service → "Ready to test"
15. Section 14: Task Management → "Ready to test"
16. Section 15: Employee Self-Reports → "Ready to test"

After EACH: "Section X done — ready to test" → STOP.

====================================================================
# END
====================================================================
