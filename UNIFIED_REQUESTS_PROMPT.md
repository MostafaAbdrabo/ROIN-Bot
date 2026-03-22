# UNIFIED REQUESTS MENU — One place for ALL requests
# Build non-stop. After done: "All done" → STOP
# Then run: afplay /System/Library/Sounds/Hero.aiff

====================================================================
# THE CONCEPT
====================================================================

Replace all separate request menus with ONE unified "📋 Requests" menu.
Every employee sees it in their main menu. It contains ALL request types
in one organized place.

====================================================================
# MAIN MENU CHANGE
====================================================================

Remove these separate items from all role menus:
- ✈️ Request Leave (move inside Requests)
- 📋 My Requests (move inside Requests)
- 🖐 Missing Punch (move inside Requests)

Replace with ONE item:
📋 Requests

====================================================================
# REQUESTS MENU STRUCTURE
====================================================================

User taps 📋 Requests → sees 3 options:

```
📋 Requests

[📅 Upcoming Requests]     ← future dates, approved or pending
[📜 Past Requests]         ← dates already passed
[📂 Requests Archive]      ← full archive by month
[➕ New Request]            ← submit a new request
[↩️ Main Menu]
```

====================================================================
# ➕ NEW REQUEST
====================================================================

User taps ➕ New Request → sees ALL request types:

```
➕ New Request — Select Type:

[🏖️ Paid Leave]
[🤒 Sick Leave]
[🚨 Emergency Leave]
[💰 Unpaid Leave]
[✈️ Business Trip]
[🖐 Missing Punch]
[🚪 Early Departure]
[⏰ Planned Overtime]
[🚨 Emergency Overtime]
[📝 Memo / Служебная записка]
[↩️ Back]  [↩️ Main Menu]
```

Each one opens the EXISTING flow (leave_request.py, missing_punch.py,
memo_handler.py, etc.) — no need to rebuild the flows, just route to them.

For roles with additional request types, add:
- Direct_Manager + HR: [👔 Hiring Request] (links to recruitment)
- Direct_Manager + HR: [🛒 Purchase Request] (links to supply)
- Warehouse: [📦 Stock Request] (links to warehouse)
- Any role: [🚗 Vehicle Request] (links to vehicles)

====================================================================
# 📅 UPCOMING REQUESTS
====================================================================

Shows requests where:
- Start_Date >= today (future)
- OR Status = Pending (not yet decided, regardless of date)

Structure:
```
📅 Upcoming Requests

Select month:
[March 2026 (3)]
[April 2026 (5)]
[May 2026 (1)]
[↩️ Back]  [↩️ Main Menu]
```

User picks month → filter by type:
```
📅 March 2026 — Upcoming (3 requests)

[🏖️ Leave (2)]
[📝 Memos (1)]
[🖐 Missing Punch (0)]
[⏰ Overtime (0)]
[📋 All (3)]
[↩️ Back to Months]  [↩️ Main Menu]
```

User picks type → sees list:
```
🏖️ Leave — March 2026

[LVE-2026-0042 | Paid | 25-28 Mar | ✅ Approved]
[LVE-2026-0045 | Sick | 30 Mar | ⏳ Pending HR]
[↩️ Back to Types]  [↩️ Main Menu]
```

User taps a request → full detail + [📄 View PDF] if exists.

====================================================================
# 📜 PAST REQUESTS
====================================================================

Same structure as Upcoming but shows requests where:
- End_Date < today (already happened)
- AND Status is final (Approved / Rejected / Cancelled)

```
📜 Past Requests

Select month:
[March 2026 (8)]
[February 2026 (12)]
[January 2026 (5)]
[↩️ Back]  [↩️ Main Menu]
```

→ Month → Type filter → List → Detail + [📄 View PDF]

====================================================================
# 📂 REQUESTS ARCHIVE
====================================================================

Full archive — ALL requests regardless of date or status.

```
📂 Requests Archive

Select month:
[March 2026 (15)]
[February 2026 (20)]
[January 2026 (10)]
[↩️ Back]  [↩️ Main Menu]
```

Inside each month, TWO views:

```
📂 March 2026 — Archive

[📋 By Type]          ← Leave, Memo, OT, etc.
[👤 By Submitter]     ← grouped by who submitted
[📊 Summary]          ← counts per type + status
[↩️ Back to Months]  [↩️ Main Menu]
```

### By Type:
```
📋 March 2026 — By Type

[🏖️ Leave (8)]
[📝 Memos (4)]
[⏰ Overtime (2)]
[🖐 Missing Punch (1)]
[🚪 Early Departure (0)]
[↩️ Back]  [↩️ Main Menu]
```

### By Submitter:
```
👤 March 2026 — By Submitter

[Mostafa Abdrabo (5 requests)]
[Ahmed Mohamed (3 requests)]
[Sara Ali (2 requests)]
[↩️ Back]  [↩️ Main Menu]
```

Tap a person → see their requests for that month.

### Summary:
```
📊 March 2026 — Summary

Leave: 8 (5 approved, 2 pending, 1 rejected)
Memos: 4 (3 approved, 1 pending)
Overtime: 2 (2 approved)
Missing Punch: 1 (1 approved)
Early Departure: 0
Total: 15 requests
```

====================================================================
# DATA SOURCES
====================================================================

The unified view pulls from MULTIPLE tabs:

| Request Type | Tab | Type Filter |
|-------------|-----|-------------|
| Paid/Sick/Emergency/Unpaid/Business_Trip Leave | Leave_Log | Request_Type column |
| Missing Punch | Leave_Log | Request_Type = "Missing_Punch" |
| Early Departure | Leave_Log | Request_Type = "Early_Departure" |
| Overtime (Planned/Emergency) | Leave_Log | Request_Type = "Overtime_*" |
| Memo | Memo_Log | — |
| Hiring Request | Hiring_Requests | — |
| Purchase Request | Purchase_Requests | — |
| Vehicle Request | Trip_Log | — |

When building the lists, query each relevant tab and merge results.
Sort by date (newest first).

====================================================================
# ACCESS CONTROL
====================================================================

| Role | Sees |
|------|------|
| Employee | Only their own requests |
| Supervisor | Own + their team's requests |
| Direct_Manager | Own + their department's requests |
| HR_Staff | ALL requests from ALL employees |
| HR_Manager | ALL requests + can act on them |
| Director | ALL requests |
| Bot_Manager | EVERYTHING |

====================================================================
# WHAT TO KEEP vs REMOVE
====================================================================

## KEEP (existing flows work, just route from new menu):
- leave_request.py → leave submission flow (all types)
- missing_punch.py → missing punch flow
- memo_handler.py → memo submission flow
- All approval handlers
- All PDF generation

## REMOVE from main menus:
- "✈️ Request Leave" as a standalone menu item → now inside ➕ New Request
- "📋 My Requests" as standalone → now inside 📋 Requests
- "🖐 Missing Punch" as standalone → now inside ➕ New Request
- "📂 Team Requests" → now inside 📋 Requests (for managers, filtered to team)

## ADD:
- 📋 Requests → in ALL role menus (prominent position)
- The unified menu handler (new file: requests_menu.py)

====================================================================
# FOR MANAGERS / HR — ADDITIONAL VIEW
====================================================================

Managers and HR see extra options in the Requests menu:

```
📋 Requests

[📅 Upcoming Requests]
[📜 Past Requests]
[📂 Requests Archive]
[➕ New Request]
[👥 Team Requests]        ← managers see their team's requests
[📑 All Requests]         ← HR sees all company requests
[↩️ Main Menu]
```

👥 Team Requests → same Month → Type → List structure
but filtered to employees under this manager.

📑 All Requests → same structure but ALL employees (HR only).

====================================================================
# IMPLEMENTATION
====================================================================

Create: requests_menu.py

This file:
1. Shows the main Requests menu (3 options + New Request)
2. Handles month selection
3. Handles type filtering
4. Queries Leave_Log + Memo_Log + other tabs
5. Merges and sorts results
6. Shows unified list with correct emoji per type
7. Tapping a request → shows detail from the correct handler
8. [📄 View PDF] button if Drive link exists

Route from bot.py:
- "menu_requests" → requests_menu.py main handler
- All sub-callbacks handled inside requests_menu.py

The EXISTING handlers (leave detail, memo detail, etc.) are reused.
requests_menu.py just provides the unified navigation layer on top.

====================================================================
# BUILD IT
# After done: "All done" → STOP
# Then: afplay /System/Library/Sounds/Hero.aiff
====================================================================
