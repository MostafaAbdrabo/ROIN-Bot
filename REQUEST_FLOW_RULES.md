# REQUEST FLOW RULES — Standard Process for ALL Approval-Based Requests
# ═══════════════════════════════════════════════════════════════════════
# This is the SINGLE SOURCE OF TRUTH for how requests work in this system.
# Drop this file into the project folder.
# Tell Claude Code: "Read REQUEST_FLOW_RULES.md before building any request."
#
# NEVER rebuild existing working features. Only ADD new ones following these rules.
# All existing handlers (leave, memo, transport, etc.) remain untouched.
#
# Last updated: 22/03/2026 (v2 — added 2-folder pattern)

====================================================================
# HOW TO USE THIS DOCUMENT
====================================================================

## Trigger Phrase (what Mostafa says):
```
Build a new [REQUEST_NAME]
Department: [DEPARTMENT_NAME]
Submitted by: [WHO_CAN_SUBMIT]
Chain: [ROLE_1] → [ROLE_2]
Assignment: [ASSIGNER_ROLE] → [EXECUTOR_ROLE_1], [EXECUTOR_ROLE_2]
Fields: [field1, field2, field3, ...]
On completion: [what the executor does when marking done]
```

## Example 1 — With Assignment:
```
Build a new Warehouse Issue Voucher
Department: Warehouse
Submitted by: any Direct_Manager
Chain: Direct_Manager → Warehouse_Manager
Assignment: Warehouse_Manager → Warehouse_Specialist, Store_Keeper
Fields: item_name, quantity, unit, purpose, requesting_department, notes
On completion: actual_qty_issued, batch_number, photo_of_items
```

## Example 2 — Approval Only (no assignment):
```
Build a new Overtime Request
Department: HR
Submitted by: any Employee
Chain: Direct_Manager → HR_Manager
Fields: date, hours, reason, overtime_type
```

If "Assignment" line is missing → approval-only flow (no Phase 2).
If "On completion" line is missing → executor just taps "✅ Done" with no extra fields.

## What happens automatically (NO need to ask for any of this):
- Google Sheet tab created (if not exists) with correct columns
- Submission flow with form fields → summary → confirm → submit
- Auto-generated ID (PREFIX-YYYY-NNNN)
- PDF generated at EVERY stage → uploaded to Drive → [📄 View PDF] button
- Electronic signatures embedded at each approval step
- Bot_Manager can submit, approve, assign, AND execute at ALL stages
- Submitter notified on each approval/rejection/completion
- Back buttons (↩️ Back to parent + ↩️ Main Menu) on EVERY screen
- Integrated into Pending Approvals for each role in the chain
- Integrated into Pending Tasks for assigned executors
- Integrated into Unified Requests Menu (📋 Requests)
- Searchable by document ID via 🔍 Search Documents
- Rejection always requires a reason

====================================================================
# SECTION 1: SUBMISSION FLOW
====================================================================

## 1.1 Entry Point
The request is accessible from:
- The department's sub-menu (e.g., Warehouse menu → 📋 Issue Voucher)
- Bot_Manager's categorized menu (under the relevant department category)
- ➕ New Request in the Unified Requests Menu (for roles that have access)

## 1.2 Form Steps
Each request has a list of FIELDS defined by Mostafa.
The bot collects them ONE AT A TIME in this order:

1. **Fixed fields** (auto-filled, shown but not editable):
   - Submitter name, code, department (from Employee_DB)
   - Date/time of submission (auto = now)
   - Request ID (auto-generated: PREFIX-YYYY-NNNN)

2. **Input fields** (collected step by step):
   - Each field is either:
     - **Button selection** (for fields with known options — e.g., urgency: Low/Medium/High/Critical)
     - **Text input** (for free text — e.g., reason, description, notes)
     - **Number input** (for quantities, costs — validated as positive number)
     - **Date input** (DD/MM/YYYY — validated format)
     - **Photo upload** (optional — e.g., photo of damaged goods)
   - Every step shows: [↩️ Back to previous step] + [↩️ Main Menu]

3. **Summary screen** (mandatory before submission):
   - Shows ALL fields in a clean format
   - Buttons: [✅ Submit] [✍️ Edit] [❌ Cancel]
   - Edit → goes back to first field (user re-enters from there)

4. **Submission**:
   - Row written to Google Sheet tab
   - Auto-generated ID returned to user
   - PDF generated (draft — submitter signature only)
   - PDF uploaded to Drive → "[dept]_pending" folder
   - Confirmation message: "✅ [Request Name] submitted!\nID: [ID]\n[📄 View PDF]"
   - Notification created for submitter (logged in Notifications tab)

## 1.3 Auto-Generated ID Format
Every request type has a unique PREFIX:
- Format: PREFIX-YYYY-NNNN
- Bot scans existing IDs in the sheet tab → finds max → increments
- Examples: PO-2026-0001, WIV-2026-0001, GDR-2026-0001

The PREFIX is defined when Mostafa says "Build a new X request."
Claude Code picks a short, logical prefix (2-4 letters).
If Mostafa specifies a prefix, use that instead.

====================================================================
# SECTION 2: APPROVAL CHAIN
====================================================================

## 2.1 Chain Definition
Each request type has a FIXED chain defined at build time.
The chain is a list of ROLES that must approve in order.

Example: Chain: Director → Supply_Manager
- Stage 0: Director must approve
- Stage 1: Supply_Manager must approve
- After all stages: Final_Status = Approved

## 2.2 Chain Columns in Google Sheet
For each stage in the chain, the sheet has 2 columns:
- [Role]_Status: Pending / Approved / Rejected / NA
- [Role]_Date: timestamp of decision (DD/MM/YYYY HH:MM)

Plus a Final_Status column: Pending / Approved / Rejected

## 2.3 How Approval Works
1. Request submitted → all statuses set to "Pending" (or "NA" if not in chain)
2. Stage 0 approver opens Pending Approvals → sees the request
3. Approver taps request → sees full detail + [📄 View Current PDF]
4. Approver taps [✅ Approve] → their signature captured → status = Approved → date saved
5. PDF regenerated with new signature → uploaded to Drive (overwrites previous)
6. Next stage approver now sees it in THEIR Pending Approvals
7. Process repeats until all stages complete
8. Final approval → Final_Status = Approved → final PDF with ALL signatures → notify submitter

## 2.4 Rejection
At ANY stage, any approver can reject:
1. Approver taps [❌ Reject] → bot asks for reason (MANDATORY — cannot be empty)
2. Approver types reason → confirmation
3. Final_Status = Rejected
4. Rejection reason saved
5. PDF regenerated showing REJECTED status + reason
6. Submitter notified: "❌ Your [request type] was rejected. Reason: [reason]"
7. No further approvals needed — chain stops

## 2.5 Bot_Manager Override
Bot_Manager (Mostafa) can:
- **Submit** any request type as if they are any role
- **Approve** at ANY stage of ANY chain — regardless of which role is expected
- When Bot_Manager approves, their name + signature appears as the approver
- Bot_Manager sees ALL pending requests from ALL departments in their Pending Approvals
- This is already implemented in approval_handler.py — new request types MUST follow the same pattern

## 2.6 Pending Approvals Integration
Every new request type MUST appear in the Pending Approvals menu:
- Grouped by category (with emoji)
- Shows count per category: "📦 Issue Vouchers (3)"
- Each approver sees ONLY requests at their stage
- Bot_Manager sees ALL pending at any stage

====================================================================
# SECTION 2B: ASSIGNMENT & EXECUTION (Phase 2)
====================================================================

This section applies ONLY to request types that have an "Assignment" line.
If no Assignment line → skip this entire section (approval-only flow).

## 2B.1 The Two Phases
```
PHASE 1 — APPROVAL:     Submitter → Approver(s) → Approved ✅
PHASE 2 — EXECUTION:    Assigner picks executor → Executor does the work → Done ✅
```

Phase 2 starts ONLY after Phase 1 is fully approved.
The request lifecycle:
```
Submitted → [Approval stages] → Approved → Assigned → In_Progress → Completed
```

## 2B.2 Assignment Flow
After the final approver in the chain approves:

1. The ASSIGNER (defined in the Assignment line — e.g., Warehouse_Manager) sees
   the request in a new section: **📋 Pending Assignment**
   (separate from Pending Approvals — this is for approved requests awaiting assignment)

2. Assigner opens the request → sees full detail + [📄 View PDF]

3. Assigner has two options:
   - **[👤 Assign to specific person]** → shows a list of employees with the executor role(s)
     (e.g., all Warehouse_Specialists and Store_Keepers in that department)
   - **[👥 Assign to role]** → assigns to the role itself. Any person with that role sees it
     in their **📋 My Tasks** menu. First one to tap "🖐 Take" claims it.

4. After assignment:
   - Request status changes: Approved → Assigned
   - Assigned_To column updated (emp_code of specific person, or role name)
   - Assigned_By column updated (assigner's emp_code)
   - Assigned_At column updated (timestamp)
   - PDF regenerated (shows assignment info)
   - If assigned to specific person → they get notified:
     "📋 New task: [Request Name] #[ID] assigned to you by [Assigner Name]"

## 2B.3 Executor's View
The assigned person (or anyone with the assigned role) sees the task in:
- **📋 My Tasks** menu (accessible from their department menu)
- Shows: request details, what's needed, [📄 View PDF]

When ready to complete, executor taps **[✅ Mark as Done]**

## 2B.4 Completion Fields (On completion)
What happens when executor taps Done depends on the request definition:

| "On completion" says | What executor does |
|---------------------|-------------------|
| (not specified) | Just taps ✅ Done — no extra input needed |
| field names (e.g., actual_qty, batch_no) | Fills in those fields step by step, then confirms |
| "photo" or "photo_of_items" | Must upload a photo before marking done |
| Multiple items | All required fields collected, then summary, then confirm |

Example — Warehouse Issue Voucher completion:
```
Executor taps ✅ Mark as Done →
  Enter actual quantity issued: [number input]
  Enter batch number: [text input]
  Upload photo of items: [photo]
  Summary → [✅ Confirm Done] [↩️ Back]
```

## 2B.5 After Completion
1. Status changes: In_Progress → Completed
2. Completed_At timestamp saved
3. Completed_By emp_code saved
4. All completion fields saved to the sheet row
5. **Final PDF generated** — includes ALL info:
   - Original request details
   - Approval chain with signatures
   - Assignment info (who assigned, when)
   - Completion info (who completed, when, fields filled, photo)
6. Final PDF uploaded to Drive → "[dept]_approved" folder
7. Submitter notified: "✅ Your [Request Name] #[ID] has been completed by [Executor Name]"
8. [📄 View Final PDF] button included

## 2B.6 No Verification Step
Once executor marks Done → the request is COMPLETE. No further action needed.
No one needs to verify or confirm after completion.

## 2B.7 Bot_Manager Override (Assignment)
Bot_Manager can:
- **See** all Pending Assignment items across all departments
- **Assign** to any person or role (even in departments they don't manage)
- **Take** any assigned task themselves (act as executor)
- **Mark Done** on any task (with or without completing the fields)
- Effectively: Bot_Manager can do everything at every phase

## 2B.8 Google Sheet Columns for Assignment
In addition to the standard approval columns (Section 5.1), add:

| Column | Description | Auto/Manual |
|--------|-------------|-------------|
| Assigned_To | Emp_Code or role name | Set by assigner |
| Assigned_By | Assigner's emp_code | Auto |
| Assigned_At | DD/MM/YYYY HH:MM | Auto |
| Execution_Status | Pending_Assignment / Assigned / In_Progress / Completed | Auto |
| Completed_By | Executor's emp_code | Auto |
| Completed_At | DD/MM/YYYY HH:MM | Auto |
| [completion_field_1] | Defined per request type | Manual (executor) |
| [completion_field_2] | ... | Manual (executor) |
| Completion_Photo | Drive link to uploaded photo | Auto |

## 2B.9 Status Lifecycle (full)
```
Submitted
  → [Approval Phase]
    → Approved
      → Pending_Assignment (waiting for assigner to pick executor)
        → Assigned (executor picked)
          → In_Progress (executor tapped "Start" or it's auto)
            → Completed (executor marked done)

OR at any approval stage:
  → Rejected (chain stops, submitter notified)
```

## 2B.10 Menu Integration

### For Assigners (e.g., Warehouse_Manager):
Their department menu shows:
```
📦 Warehouse
├── 📋 Pending Assignment (3)    ← approved requests needing assignment
├── 📊 Active Tasks (5)          ← assigned but not yet completed
├── ✅ Completed Today (2)       ← completed tasks
├── [other department options...]
├── ↩️ Main Menu
```

### For Executors (e.g., Store_Keeper):
Their menu shows:
```
📋 My Tasks
├── 🔴 New (2)         ← assigned to me, not started
├── 🟡 In Progress (1) ← I started but not done
├── ✅ Done Today (3)   ← completed today
├── ↩️ Main Menu
```

### For Bot_Manager:
Sees everything under the department category:
```
📦 Warehouse (Bot_Manager view)
├── 📋 Pending Assignment (3)
├── 📊 All Active Tasks (8)
├── ✅ Completed Today (5)
├── 📜 Full History
├── [all other warehouse options...]
```

====================================================================
# SECTION 3: PDF AT EVERY STAGE
====================================================================

## 3.1 Rule (non-negotiable)
At EVERY point in the approval chain, a PDF exists and is viewable via Drive link.
No person ever approves or decides without seeing the current PDF first.

## 3.2 PDF Generation Points
| Event | PDF Contains | Upload Folder |
|-------|-------------|---------------|
| Submission | Request details + submitter signature | [dept]_pending |
| Each approval | All details + ALL signatures so far | [dept]_pending (overwrite) |
| Final approval | Complete PDF with ALL signatures | [dept]_approved |
| Rejection | All details + REJECTED stamp + reason | [dept]_pending |

## 3.3 PDF Layout
Every request PDF follows the company standard:
- **Header**: Company logo centered + "ROIN WORLD FZE EGYPT BRANCH" + address + email + website
- **Title**: "[REQUEST TYPE NAME]" centered, bold
- **Request Info**: ID, date, status
- **Submitter Details**: Name, code, department, job title
- **Request Details**: All form fields with labels and values
- **Approval Chain**: Each approver with status + signature + date
- **Final Status**: APPROVED (green) or REJECTED (red) or PENDING
- **Footer**: "Generated by ROIN WORLD FZE HR System" + datetime
- **Verification**: SIG-[random hex code]

## 3.4 Drive Upload — 2-Folder Pattern
Every department has TWO Drive folders:
- **[dept]_pending**: documents still in approval process (drafts, partial approvals)
- **[dept]_approved**: final approved documents (archive)

Rules:
- During approval (any stage before final) → upload to "[dept]_pending"
- On final approval → upload to "[dept]_approved"
- On rejection → stays in "[dept]_pending"
- Drive link in the sheet is ALWAYS the latest version (overwritten at each stage)
- Use drive_utils.upload_to_drive(pdf_bytes, filename, folder_key)
- folder_key = the key from config.py DRIVE_FOLDERS (e.g., "warehouse_pending", "warehouse_approved")
- If folder not configured → use "drafts" as fallback
- Button shown: InlineKeyboardButton("📄 View PDF", url=drive_url)

## 3.5 Font
- Use DejaVu font (font_utils.py) for any Russian/Arabic text
- Use Helvetica for English-only PDFs
- Company logo: company_logo.png

====================================================================
# SECTION 4: ELECTRONIC SIGNATURES
====================================================================

## 4.1 How Signatures Work
- Each employee may have a signature image stored in Employee_DB → Signature_Link
- When they approve/submit, their signature is embedded in the PDF
- If no image signature → text fallback: "[Name] — Electronically signed — [datetime]"
- Use signature_handler.get_sig_bytes(bot, emp_code) to retrieve

## 4.2 Signature Capture Points
- **Submission**: submitter's signature applied automatically
- **Each approval**: approver's signature applied when they tap ✅ Approve
- **No extra step** — tapping Approve = signed

## 4.3 In the PDF
Each approval line shows:
1. Status icon: [APPROVED] / [REJECTED] / [PENDING]
2. Role name + approver name + date
3. Signature image (or text fallback)
4. Bold name below signature
5. Italic date below name

====================================================================
# SECTION 5: GOOGLE SHEET TAB STRUCTURE
====================================================================

## 5.1 Standard Columns (every request tab has these)
| Column | Description | Auto/Manual |
|--------|-------------|-------------|
| Request_ID | PREFIX-YYYY-NNNN | Auto |
| Date | Submission date DD/MM/YYYY HH:MM | Auto |
| Emp_Code | Submitter's code | Auto |
| Full_Name | VLOOKUP from Employee_DB — write "" | Auto (VLOOKUP) |
| Department | VLOOKUP from Employee_DB — write "" | Auto (VLOOKUP) |
| [Custom fields...] | Defined per request type | Manual (form) |
| [Stage1]_Status | Pending/Approved/Rejected/NA | Auto |
| [Stage1]_Date | Timestamp | Auto |
| [Stage2]_Status | Same | Auto |
| [Stage2]_Date | Same | Auto |
| [StageN]_Status | Same | Auto |
| [StageN]_Date | Same | Auto |
| Final_Status | Pending/Approved/Rejected | Auto |
| Rejection_Reason | Free text | Manual (approver) |
| PDF_Generated | Yes/No | Auto |
| PDF_Drive_Link | Google Drive URL | Auto |
| Created_At | DD/MM/YYYY HH:MM | Auto |

## 5.2 VLOOKUP Rule
Columns that have VLOOKUP formulas (Full_Name, Department):
- Bot writes "" (empty string) to these cells
- The spreadsheet formula auto-fills from Employee_DB
- NEVER write actual values to VLOOKUP columns

## 5.3 Tab Auto-Creation
If the tab doesn't exist when the handler first runs:
- Create it with all headers
- This prevents manual sheet setup errors

====================================================================
# SECTION 6: NOTIFICATIONS
====================================================================

## 6.1 Who Gets Notified (via Telegram message + Notifications tab)
| Event | Notified |
|-------|----------|
| Request submitted | Submitter only (confirmation) |
| Approved at stage | Submitter ("Your request approved by [Role]") |
| Rejected at any stage | Submitter ("Your request rejected. Reason: [reason]") |
| Final approval | Submitter + all approvers who signed |
| Assigned to specific person | That person ("New task assigned to you by [Name]") |
| Task completed | Submitter ("Your [request] completed by [Executor Name]") |

## 6.2 Who Does NOT Get Notified
- Approvers are NEVER auto-notified when a new request arrives
- They check Pending Approvals from their menu when THEY are ready
- This is rule 2.1 in PROJECT_RULES.md — non-negotiable

## 6.3 Notification Format
Message includes:
- Request type + ID
- Current status
- [📄 View PDF] button (if Drive link exists)

====================================================================
# SECTION 7: NAVIGATION
====================================================================

## 7.1 Back Buttons — EVERY Screen
Every screen in the flow has:
- [↩️ Back] → goes to the PREVIOUS step/menu (NOT main menu)
- [↩️ Main Menu] → goes to role-based home screen

## 7.2 After Submission
- "✅ Submitted! ID: XXX" + [📄 View PDF] + [↩️ Main Menu]

## 7.3 After Approval/Rejection
- Return to the category list in Pending Approvals (with updated counts)
- NOT to main menu

## 7.4 Error/Empty Screens
- "No pending requests" + [↩️ Back to parent menu] + [↩️ Main Menu]
- Error messages + [↩️ Back] + [↩️ Main Menu]

====================================================================
# SECTION 8: UNIFIED REQUESTS MENU INTEGRATION
====================================================================

## 8.1 New Request Types Auto-Added
Every new request type must appear in:
- ➕ New Request menu (for roles that can submit)
- 📅 Upcoming / 📜 Past / 📂 Archive views
- The request detail view when user taps a specific request

## 8.2 How to Integrate
In requests_menu.py:
- Add the new type code to TCODE_NAMES
- Add the sheet tab to the data source list
- Add the type filter logic

## 8.3 Search Integration
In search_handler.py:
- Add the new PREFIX to _detect_prefix()
- Map to the correct tab and column

====================================================================
# SECTION 9: DEPARTMENT-SPECIFIC MENUS
====================================================================

## 9.1 Menu Structure
Each department has a sub-menu in bot.py.
New request types are added as buttons in their department menu.

Example for Warehouse:
```
📦 Warehouse
├── 📋 Issue Voucher
├── 🗑 Goods Destruction Request
├── 📊 Inventory
├── ⚠️ Low Stock
├── ↩️ Main Menu
```

## 9.2 Bot_Manager Menu
Bot_Manager's categorized menu has ALL departments.
New request types auto-appear under the correct department category.

## 9.3 Role Access
| Role | What they see |
|------|--------------|
| Department staff | Submit requests for their department |
| Department Manager | Submit + approve first stage |
| HR/Director | Approve at their stage |
| Bot_Manager | Everything — submit + approve all stages |

====================================================================
# SECTION 10: FILE STRUCTURE
====================================================================

## 10.1 One Handler File Per Department
Each department has ONE handler file (e.g., warehouse_handler.py).
New request types for that department are ADDED to the existing file.
Do NOT create a new file for each request type.

## 10.2 Shared Utilities
- config.py: DRIVE_FOLDERS, tab names, role lists
- drive_utils.py: upload_to_drive()
- pdf_generator.py: base PDF class (or create a new generator for the department)
- signature_handler.py: get_sig_bytes()
- notification_handler.py: create_notification()
- approval_handler.py: approval chain logic (extend for new types)
- font_utils.py: DejaVu font for Cyrillic

## 10.3 Registration in bot.py
Every new handler must be:
1. Imported in bot.py
2. Registered with app.add_handler()
3. Added to the correct role menus
4. Added to Bot_Manager's sub-menu

====================================================================
# SECTION 11: TRIGGER PHRASES — QUICK COMMANDS
====================================================================

## Full Build Command:
```
Build a new [NAME]
Department: [DEPT]
Submitted by: [ROLES]
Chain: [ROLE1] → [ROLE2]
Assignment: [ASSIGNER] → [EXECUTOR_ROLE1], [EXECUTOR_ROLE2]
Fields: [field1, field2, field3, ...]
On completion: [completion_field1, completion_field2, photo]
```

Notes:
- "Assignment" line is OPTIONAL. If missing → approval-only flow (Phase 1 only).
- "On completion" line is OPTIONAL. If missing → executor just taps Done.
- Chain can have 1, 2, or 3 approval stages.
- Assignment executor roles can be 1, 2, or more (assigner picks from all).

## Short Commands (after the request type exists):
| Mostafa says | Claude Code does |
|-------------|-----------------|
| "Add [field] to [request]" | Add a new form field to existing request |
| "Add completion field [field] to [request]" | Add a field the executor must fill on completion |
| "Change chain for [request] to [new chain]" | Update approval chain |
| "Add assignment to [request]: [assigner] → [executor roles]" | Add Phase 2 to an approval-only request |
| "Add [request] to [role] menu" | Add menu button for that role |
| "Fix back button in [handler]" | Check all screens in that handler |
| "Show me all request types" | List all built request types with status |

## Universal Short Commands:
| Mostafa says | Meaning |
|-------------|---------|
| "شغال" / "working" | Test passed — move to next task |
| "مش شغال" / "not working" | Something is broken — will paste error |
| "next" / "التاني" | Move to next feature/section |
| "done" / "خلاص" | Finished for now |
| "اعمل ده" / "build this" | Start building what was just described |

====================================================================
# SECTION 12: WHAT THIS DOCUMENT DOES NOT COVER
====================================================================

These are handled by other documents and existing code:
- Login/authentication flow → SESSION_3_HANDOFF.md
- Leave-specific rules (balance, holidays, smart day calc) → leave_request.py
- Memo-specific format (bilingual RU+EN) → memo_handler.py
- Attendance processing → attendance_handler.py
- JD generation with AI → jd_handler.py + jd_ai.py
- Recruitment pipeline → recruitment_handler.py
- Monthly schedule → schedule_handler.py
- General project rules → PROJECT_RULES.md
- Back button implementation → BACK_BUTTON_RULE.md

====================================================================
# SECTION 13: CHECKLIST — VERIFY BEFORE MARKING DONE
====================================================================

Before saying "Ready to test" for any new request type:

### Phase 1 — Approval (always):
- [ ] Google Sheet tab created with all columns
- [ ] VLOOKUP columns write "" (not actual values)
- [ ] Auto-ID generation works (PREFIX-YYYY-NNNN)
- [ ] All form fields collected step by step
- [ ] Summary screen before submission
- [ ] PDF generated on submission (with submitter signature)
- [ ] PDF uploaded to Drive → [📄 View PDF] button shown
- [ ] Approval chain works — each stage sees it in Pending Approvals
- [ ] Bot_Manager can approve at every stage
- [ ] PDF regenerated at each approval (with new signature)
- [ ] Rejection requires reason
- [ ] Submitter notified on approve/reject
- [ ] Back buttons on EVERY screen (↩️ Back to parent + ↩️ Main Menu)
- [ ] Added to Unified Requests Menu
- [ ] Added to Search Documents prefix map
- [ ] Added to Bot_Manager's department sub-menu
- [ ] No existing code broken — only additions

### Phase 2 — Assignment (only if Assignment line exists):
- [ ] Pending Assignment view works for the assigner role
- [ ] Assigner can pick a specific person from employee list
- [ ] Assigner can assign to role (any person with role sees it)
- [ ] Assigned person sees task in My Tasks
- [ ] Completion fields collected (if On completion defined)
- [ ] Photo upload works (if photo required)
- [ ] Done marks request as Completed
- [ ] Final PDF includes assignment + completion info
- [ ] Submitter notified on completion
- [ ] Bot_Manager can assign and complete at every phase

====================================================================
END OF REQUEST FLOW RULES
====================================================================
