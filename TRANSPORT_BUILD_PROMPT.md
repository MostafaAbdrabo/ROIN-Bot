# TRANSPORT SYSTEM — Build Session
# Read REQUEST_FLOW_RULES.md + PROJECT_RULES.md first.
# Reference database: ROIN_WORLD_FZE_System_v6 (1).xlsx

====================================================================
# PRE-BUILD: AUDIT
====================================================================

Before writing new code:
1. Read all .py files — understand the existing patterns
2. Read the Excel file — this is the SINGLE SOURCE OF TRUTH for tabs and columns
3. Cross-check: if code uses a column/tab name that doesn't match Excel → fix it
4. If Excel is missing a column the code needs → add it to Excel via openpyxl
5. Fix everything automatically — never ask me to edit manually

====================================================================
# BUILD LIST
====================================================================

## 1. Fix: Director Approval for Far Trips
Existing code, untested. Verify and fix the full chain:
```
Employee submits (trip_type = "Far")
Chain: Direct_Manager → Director → Transport_Manager
```
Standard flow per REQUEST_FLOW_RULES.md applies.

## 2. Fix: Commute Requests
Existing code, untested. Verify the full flow:
```
Build a new Commute Request
Department: Transport
Submitted by: any Employee
Chain: Transport_Manager
Assignment: Transport_Manager → Driver
Fields: date, departure_time, from_location, to_location, employee_codes, employee_count
On completion: vehicle_assigned, driver_assigned
```
Tab: Commute_Log (12 columns — check Excel for exact structure)

## 3. Fix: VLOOKUP Formulas in Excel
Add these VLOOKUP formulas to Transport_Requests tab (row 2+):
- Column D (REQ_Name): =IF(C2="","",VLOOKUP(C2,Employee_DB!A:B,2,0))
- Column E (REQ_Dept): =IF(C2="","",VLOOKUP(C2,Employee_DB!A:E,5,0))
- Column Q (MGR_Name): =IF(P2="","",VLOOKUP(P2,Employee_DB!A:B,2,0))
- Column U (DIR_Name): =IF(T2="","",VLOOKUP(T2,Employee_DB!A:B,2,0))
- Column AA (Driver_Name): =IF(Z2="","",VLOOKUP(Z2,Employee_DB!A:B,2,0))

## 4. Build: Fleet Dashboard
New feature in vehicle_handler.py.

Add to Trip_Log tab (if missing): Last_Lat, Last_Long, Last_Location_Time, Location_Shared, Maps_Link

**Dashboard view** for Transport_Manager + Bot_Manager:
Shows all trips where Status = "In_Progress":
- 🟢 Active (on time) — driver name, plate, destination, duration, [📍 Maps link]
- 🔴 Overdue — same + "OVERDUE X min" + [Mark Returned] [Escalate to Director]
- 🟡 No location — same + "No location shared" + [Remind driver]
- Footer: available vehicle count + [🔄 Refresh] [📊 Today's Report] [↩️ Main Menu]

## 5. Build: Driver Start/End Trip + Live Location

**Start Trip:**
- Driver taps My Assigned Trips → [🚀 Start Trip]
- Bot logs Actual_Depart, sets Status = "In_Progress"
- Bot prompts driver to share live location (explains how: 📎 → Location → Share Live → 8 hours)
- Buttons: [✅ I'll share now] [Skip for now]

**Live Location Handler — CRITICAL TECHNICAL DETAILS:**

Telegram sends live location updates in TWO ways:
1. First share → arrives as `update.message.location`
2. Every subsequent update → arrives as `update.edited_message.location`

You need BOTH handlers registered in bot.py:

```python
# Handler 1: First location share (new message)
app.add_handler(MessageHandler(filters.LOCATION, handle_location_update))

# Handler 2: Live location updates (edited message)
# This is the one most people miss — Telegram sends updates as edited messages
app.add_handler(MessageHandler(filters.LOCATION, handle_location_update), group=1)
```

The handler function must check BOTH:
```python
async def handle_location_update(update, context):
    # Live updates come via edited_message, first share via message
    msg = update.edited_message or update.message
    if not msg or not msg.location:
        return
    lat = msg.location.latitude
    lng = msg.location.longitude
    # ... save to Trip_Log
```

IMPORTANT: Register the location handler with `group=1` or higher so it doesn't
conflict with ConversationHandlers. ConversationHandlers use group=0 by default.

On each location update:
- Find driver's active trip in Trip_Log (Status = "In_Progress", driver matches)
- Save: Last_Lat, Last_Long, Last_Location_Time (DD/MM/YYYY HH:MM)
- Save: Location_Shared = "Yes"
- Save: Maps_Link = f"https://maps.google.com/?q={lat},{lng}"
- Do NOT reply to the driver on every update — silent save only
- Only reply on FIRST location share: "✅ Location received. Drive safe!"

Edge cases:
- Driver has no active trip but sends location → ignore silently
- Driver shares location for a different reason → check Trip_Log first, skip if no active trip
- Multiple drivers sharing location simultaneously → each matched to their own Trip_Log row

**Background Scheduler — for reminders and overdue alerts:**

Use `python-telegram-bot`'s built-in `JobQueue` (already available, no extra library):

```python
# In bot.py main(), AFTER app is built:
app.job_queue.run_repeating(
    check_overdue_trips,    # async function
    interval=300,           # every 5 minutes
    first=60,               # start 1 minute after bot starts
    name="overdue_checker"
)
```

The check_overdue_trips function:
1. Read all Trip_Log rows where Status = "In_Progress"
2. For each:
   - If no Location_Shared after 5 min since Actual_Depart → send reminder to driver
   - If no Location_Shared after 15 min → alert Transport_Manager
   - If current time > Expected_Return + 15 min → ping driver "Are you delayed?"
   - If current time > Expected_Return + 30 min → alert Transport_Manager
   - If current time > Expected_Return + 60 min → alert Director
3. To avoid spamming: add column "Last_Alert_Sent" to Trip_Log
   - Only send each alert type ONCE per trip
   - Values: "none", "5min_reminder", "15min_alert", "overdue_15", "overdue_30", "overdue_60"

IMPORTANT: JobQueue requires the bot to be running continuously.
On Railway (production), this works. Locally, it works while python3 bot.py is running.

**End Trip:**
- Driver taps [🏁 End Trip] → "Are you back at base?" → confirms
- Collects: final_odometer, issues_or_delays (or skip)
- Bot logs: Actual_Return, Odo_End, Delay_Reason, Status = "Completed"
- Bot logs: Location_Shared stays as-is (historical record)
- Notifies: Transport_Manager + original requester
- The overdue checker automatically skips completed trips

**What if driver never shares location:**
- Trip still works — location is encouraged, not mandatory
- Dashboard shows 🟡 "No location shared" for that trip
- Transport_Manager can still see trip details and mark it returned manually
- No blocking — the trip flow continues regardless

**What if driver closes Telegram or loses internet:**
- Live location updates stop — this is a Telegram limitation
- Last known location stays in Trip_Log
- Dashboard shows last location + "Last updated: X min ago"
- If stale > 30 min: dashboard shows ⚠️ "Location stale"

====================================================================
# REGISTRATION
====================================================================

After building, update bot.py:
- Import vehicle_handler
- Add location MessageHandler for BOTH new messages AND edited messages (group=1)
- Add JobQueue.run_repeating for check_overdue_trips (interval=300 seconds)
- Add /dashboard command handler
- Add [Fleet Dashboard] to Transport_Manager + Bot_Manager menus
- Do NOT remove or modify any existing handler

Required columns in Trip_Log (add to Excel if missing):
Last_Lat, Last_Long, Last_Location_Time, Location_Shared, Maps_Link, Last_Alert_Sent

====================================================================
# END: Give me summary of changes + run command
====================================================================
