# DAY 3 — BUILD LIST FOR CLAUDE CODE
# Read PROJECT_HANDBOOK.md first for full context.
# Build ONE task at a time. After each task, say "Ready to test" and STOP.
# I will test it and say "next" when ready to continue.
# NEVER batch multiple tasks without me testing in between.
# When the next step is running the bot, write: python3 bot.py

====================================================================
TASKS TO BUILD TODAY — IN THIS EXACT ORDER
====================================================================

## TASK 1: My Profile (👤)
When employee taps My Profile:
- Read Employee_DB for their Emp_Code
- Show: Full Name, Emp_Code, Department, Job Title, Hire Date,
  Contract Type, Contract Expiry, Direct Manager name
- Manager name: look up Manager_Code in Employee_DB to get Full_Name
- Add ↩️ Main Menu button
- This replaces the "Coming soon" placeholder in menu_catch

## TASK 2: My Attendance (🕐)
When employee taps My Attendance:
- Read the attendance sheet (ID: 1_GEamKcub5g8zUXryHJ8PVHydA3hKSFV88hUt98fCTw)
- Find employee's row by code in column C (starting row 7)
- Count statuses for current month: P, A, V, S, U, B, OFF, H
- Show summary:
  "Your Attendance — March 2026
   Present: X | Absent: X | Leave: X
   Off Days: X | Holidays: X
   Attendance Rate: X%"
- ↩️ Main Menu button
- NOTE: The tab name for the current month needs to be configurable
  (right now it's "Copy of 3-K" for testing)

## TASK 3: Help / FAQ (❓)
- Create FAQ tab in master Google Sheet with columns:
  Question_ID, Question, Answer, Category
- Pre-load 8 questions (see below)
- When employee taps Help: show categories, pick one, see FAQ
- Categories: Leave, Attendance, HR, General
- FAQs:
  1. When is payday? → 28th of each month. If Friday, paid on 27th. (Category: HR)
  2. Working hours? → Sun-Thu, shifts vary by department. (Category: Attendance)
  3. How to request leave? → Main Menu → Request Leave. (Category: Leave)
  4. Emergency leave limit? → 3 days per year. (Category: Leave)
  5. Annual leave days? → Per your contract — check My Leave Balance. (Category: Leave)
  6. Report absence? → Contact manager and HR same day. (Category: Attendance)
  7. HR issues? → Main Menu → Contact HR (future) or message HR directly. (Category: HR)
  8. Check leave balance? → Main Menu → My Leave Balance. (Category: General)
- ↩️ Back + ↩️ Main Menu on every screen

## TASK 4: Missing Punch Request (🖐)
Full spec in PROJECT_HANDBOOK.md → TASK B.
Summary:
- New button in employee menu: 🖐 Missing Punch
- Employee selects: Missing IN / Missing OUT / Both
- Enter date (today or yesterday only)
- Enter reason
- Summary → Submit
- Goes to Leave_Log with Request_Type = "Missing_Punch", prefix MP-YYYY-NNNN
- Follows employee's approval chain
- Add to Pending Approvals with 🖐 emoji
- Add to all role menus (Employee, Supervisor, Manager, HR_Staff, HR_Manager)
- Update attendance_handler.py: if employee has approved Missing_Punch for a date
  AND has partial punch → status = P

## TASK 5: Early Departure Request (🚪)
Full spec in PROJECT_HANDBOOK.md → TASK C.
Summary:
- Add "🚪 Early Departure" to Request Leave type selection
- Employee enters: date, time leaving (HH:MM), reason (buttons: Pre-holiday/Personal/Medical/Other)
- Bot calculates hours leaving early
- Max 2 per month enforced by bot
- Approval: Manager → HR only (no Director)
- Request_Type: "Early_Departure", prefix ED-YYYY-NNNN
- Column 6 = hours, Column 7 = leave time
- Update attendance: if approved Early_Departure covers gap → P

## TASK 6: Overtime Request (⏰)
Full spec in PROJECT_HANDBOOK.md → TASK D.
Summary:
- Add "⏰ Planned OT" and "🚨 Emergency OT" to request types
- Planned: 24hr advance, Emergency: same day or next day
- Enter: date, hours (1-4), reason
- Max 4hrs/day, 12hrs/week, 40hrs/month
- Approval: Manager → HR (Director if monthly limit exceeded)
- Request_Type: "Overtime_Planned" or "Overtime_Emergency"
- Prefix: OT-YYYY-NNNN
- Column 6 = hours, Column 17 = OT rate, Column 18 = equivalent hours

## TASK 7: All Leave Requests View (📑)
For HR_Staff and HR_Manager roles:
- Show summary: Pending Manager X, Pending HR X, Approved this month X, Rejected X
- Buttons: View Pending HR / View All This Month / Search by Employee
- View Pending HR: list all requests where HR_Status = Pending
- Each request: detail + Approve/Reject (for HR_Manager only)
- Search by Employee: type employee code → see all their requests
- ↩️ Back + ↩️ Main Menu

## TASK 8: Employee Lookup (🔍)
For HR_Staff, HR_Manager, Director:
- Type employee code or name
- Shows full profile (same as My Profile but for any employee)
- Links to: their leave history, attendance, documents
- ↩️ Back + ↩️ Main Menu

## TASK 9: Security Hardening
- Unregistered Telegram IDs: log to Access_Log, show nothing
- Wrong password 3x: lock account (already built — verify it works)
- Admin command /listusers: DIRECTOR and HR_MANAGER only
- Admin command /lockuser EMP-CODE: HR_MANAGER only
- Admin command /unlockuser EMP-CODE: HR_MANAGER only
- Add these to ⚙️ Admin Functions menu for HR_Manager

## TASK 10: Polish Bot Messages
- All messages clear and professional
- Date format consistent: DD/MM/YYYY
- Error messages friendly
- All confirmations include Request ID
- Typing indicator before long responses (send_chat_action)

====================================================================
IMPORTANT REMINDERS
====================================================================
- BACK BUTTON on every screen. No exceptions. See BACK_BUTTON_RULE.md
- Python 3.14: use asyncio.run(main()) pattern
- Test command: python3 bot.py
- Employee codes are NUMERIC (1007, not EMP-001)
- Google Sheets rate limit: 60 reads/min — batch reads when possible
- Every new request type needs: bot menu button + conversation flow +
  Leave_Log entry + Pending Approvals category + PDF support

====================================================================
START: Read PROJECT_HANDBOOK.md, then build TASK 1. Say "Ready to test" and stop.
====================================================================
