"""
ROIN WORLD FZE -- Task Management Handler
==========================================
Section 14 of FULL_SYSTEM_BUILD.md

Manager assigns tasks to employees. Employees see My Tasks.
Overdue checking via JobQueue.

Tab: Tasks_Log
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet


def _bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def _bt(): return InlineKeyboardButton("↩️ Tasks", callback_data="menu_tasks")

HEADERS = [
    "Task_ID", "Created_At", "Assigned_By", "Assigned_To", "Emp_Name",
    "Department", "Task_Title", "Description", "Priority", "Deadline",
    "Status", "Started_At", "Completed_At", "Completion_Notes", "Manager_Verified"
]

# Conversation states
TSK_EMP    = 7000
TSK_TITLE  = 7001
TSK_DESC   = 7002
TSK_PRIO   = 7003
TSK_DEAD   = 7004
TSK_CONFIRM = 7005
TSK_DONE_NOTES = 7006

PRIORITIES = ["Low", "Medium", "High", "Critical"]


def _get_emp_by_tid(tid):
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0: continue
            if r[1].strip() == str(tid):
                ec = r[0].strip()
                role = r[3].strip() if len(r) > 3 else "Employee"
                for j, e in enumerate(get_sheet("Employee_DB").get_all_values()):
                    if j == 0: continue
                    if e[0].strip() == ec:
                        return {"code": ec, "name": e[1].strip() if len(e) > 1 else ec,
                                "dept": e[6].strip() if len(e) > 6 else "", "role": role}
                return {"code": ec, "name": ec, "dept": "", "role": role}
    except Exception:
        pass
    return None


def _get_emp_name(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r.get("Full_Name", ec)
    except Exception:
        pass
    return str(ec)


def _get_tid_by_code(ec):
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0: continue
            if r[0].strip() == str(ec) and r[1].strip():
                return r[1].strip()
    except Exception:
        pass
    return None


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _gen_task_id():
    try:
        ids = get_sheet("Tasks_Log").col_values(1)
    except Exception:
        ids = []
    yr = datetime.now().strftime("%Y")
    px = f"TSK-{yr}-"
    mx = 0
    for v in ids:
        if str(v).startswith(px):
            try: mx = max(mx, int(str(v).split("-")[-1]))
            except: pass
    return f"{px}{mx + 1:04d}"


def _ensure_tab():
    try:
        get_sheet("Tasks_Log")
    except Exception:
        try:
            from config import WORKBOOK
            ws = WORKBOOK.add_worksheet("Tasks_Log", rows=1000, cols=len(HEADERS))
            ws.update('A1', [HEADERS])
        except Exception as e:
            print(f"[task] Could not create Tasks_Log: {e}")


def _find_task(task_id):
    try:
        rows = get_sheet("Tasks_Log").get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if r[0].strip() == str(task_id):
                return i + 1, r
    except Exception:
        pass
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
#  TASK MENU
# ══════════════════════════════════════════════════════════════════════════════

async def task_menu_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return
    role = emp["role"]
    kb = [
        [InlineKeyboardButton("📋 My Tasks", callback_data="tsk_my")],
    ]
    if role in ("Direct_Manager", "Supervisor", "Warehouse_Manager", "Operations_Manager",
                "Transport_Manager", "Quality_Manager", "Housing_Manager", "Packaging_Manager",
                "Supply_Manager", "Safety_Manager", "Translation_Manager",
                "HR_Manager", "Director", "Bot_Manager"):
        kb.insert(0, [InlineKeyboardButton("➕ Assign Task", callback_data="tsk_assign_start")])
        kb.append([InlineKeyboardButton("📊 Team Tasks", callback_data="tsk_team")])
    if role == "Bot_Manager":
        kb.append([InlineKeyboardButton("📂 All Tasks", callback_data="tsk_all")])
    kb.append([_bm()])
    await q.edit_message_text("📌 Task Management\n\nSelect action:",
                              reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  ASSIGN TASK
# ══════════════════════════════════════════════════════════════════════════════

async def tsk_assign_start(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Enter employee code to assign task to:",
                              reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return TSK_EMP


async def tsk_emp_inp(update, context):
    ec = update.message.text.strip()
    name = _get_emp_name(ec)
    if name == ec:
        await update.message.reply_text(f"Employee {ec} not found. Try again:",
                                        reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
        return TSK_EMP
    context.user_data["tsk_to"] = ec
    context.user_data["tsk_to_name"] = name
    await update.message.reply_text(f"Assigning to: {name} ({ec})\n\nEnter task title:",
                                    reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return TSK_TITLE


async def tsk_title_inp(update, context):
    context.user_data["tsk_title"] = update.message.text.strip()
    await update.message.reply_text("Enter task description:",
                                    reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return TSK_DESC


async def tsk_desc_inp(update, context):
    context.user_data["tsk_desc"] = update.message.text.strip()
    kb = [[InlineKeyboardButton(p, callback_data=f"tsk_prio_{p}")] for p in PRIORITIES]
    kb.append([_bt(), _bm()])
    await update.message.reply_text("Select priority:", reply_markup=InlineKeyboardMarkup(kb))
    return TSK_PRIO


async def tsk_prio_cb(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["tsk_prio"] = q.data.replace("tsk_prio_", "")
    await q.edit_message_text("Enter deadline (DD/MM/YYYY):",
                              reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return TSK_DEAD


async def tsk_dead_inp(update, context):
    raw = update.message.text.strip().lower()
    if raw == "today":
        dl = datetime.now().strftime("%d/%m/%Y")
    elif raw == "tomorrow":
        dl = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    else:
        try:
            datetime.strptime(raw, "%d/%m/%Y")
            dl = raw
        except ValueError:
            await update.message.reply_text("Use DD/MM/YYYY, 'today', or 'tomorrow':")
            return TSK_DEAD
    context.user_data["tsk_deadline"] = dl

    d = context.user_data
    summary = (f"📌 Task Assignment\n{'_' * 28}\n"
               f"To: {d['tsk_to_name']} ({d['tsk_to']})\n"
               f"Title: {d['tsk_title']}\n"
               f"Description: {d['tsk_desc'][:80]}\n"
               f"Priority: {d['tsk_prio']}\n"
               f"Deadline: {dl}")
    kb = [[InlineKeyboardButton("Submit", callback_data="tsk_cfm_yes"),
           InlineKeyboardButton("Cancel", callback_data="tsk_cfm_no")],
          [_bm()]]
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(kb))
    return TSK_CONFIRM


async def tsk_confirm(update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "tsk_cfm_no":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    emp = _get_emp_by_tid(q.from_user.id)
    d = context.user_data
    _ensure_tab()
    task_id = _gen_task_id()
    now_str = _now()

    row = [""] * len(HEADERS)
    row[0] = task_id           # Task_ID
    row[1] = now_str           # Created_At
    row[2] = emp["code"] if emp else ""  # Assigned_By
    row[3] = d.get("tsk_to", "")  # Assigned_To
    row[4] = ""                # Emp_Name (VLOOKUP)
    row[5] = ""                # Department (VLOOKUP)
    row[6] = d.get("tsk_title", "")
    row[7] = d.get("tsk_desc", "")
    row[8] = d.get("tsk_prio", "Medium")
    row[9] = d.get("tsk_deadline", "")
    row[10] = "New"            # Status
    try:
        get_sheet("Tasks_Log").append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    # Notify employee
    tid = _get_tid_by_code(d.get("tsk_to", ""))
    if tid:
        try:
            by_name = emp["name"] if emp else "Manager"
            await context.bot.send_message(
                chat_id=tid,
                text=f"📌 New task assigned: {task_id}\n"
                     f"Title: {d['tsk_title']}\nPriority: {d['tsk_prio']}\n"
                     f"Deadline: {d['tsk_deadline']}\nAssigned by: {by_name}")
        except Exception:
            pass

    await q.edit_message_text(f"Task assigned!\nID: {task_id}",
                              reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return ConversationHandler.END


async def tsk_cancel(update, context):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.",
                                                       reply_markup=InlineKeyboardMarkup([[_bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  MY TASKS
# ══════════════════════════════════════════════════════════════════════════════

async def tsk_my_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    if not emp:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    _ensure_tab()
    try:
        rows = get_sheet("Tasks_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    now = datetime.now()
    my = []
    for i, r in enumerate(rows):
        if i == 0 or len(r) < 11: continue
        if r[3].strip() == emp["code"] and r[10].strip() not in ("Completed", "Cancelled"):
            my.append(r)

    if not my:
        await q.edit_message_text("No active tasks.",
                                  reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
        return

    # Group by status
    overdue = []
    due_today = []
    upcoming = []
    for r in my:
        status = r[10].strip()
        deadline = r[9].strip()
        try:
            dl_dt = datetime.strptime(deadline, "%d/%m/%Y")
        except Exception:
            dl_dt = None

        prio_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵"}.get(r[8].strip(), "⚪")

        entry = {"id": r[0], "title": r[6][:30], "deadline": deadline, "prio": prio_icon, "status": status}
        if dl_dt and dl_dt.date() < now.date() and status != "Completed":
            overdue.append(entry)
        elif dl_dt and dl_dt.date() == now.date():
            due_today.append(entry)
        else:
            upcoming.append(entry)

    kb = []
    if overdue:
        for e in overdue:
            kb.append([InlineKeyboardButton(f"⚠️ {e['id']} — {e['title']} — OVERDUE",
                                            callback_data=f"tsk_view_{e['id']}")])
    if due_today:
        for e in due_today:
            kb.append([InlineKeyboardButton(f"🟡 {e['id']} — {e['title']} — Today",
                                            callback_data=f"tsk_view_{e['id']}")])
    if upcoming:
        for e in upcoming[:10]:
            kb.append([InlineKeyboardButton(f"{e['prio']} {e['id']} — {e['title']} — {e['deadline']}",
                                            callback_data=f"tsk_view_{e['id']}")])
    kb.append([_bt(), _bm()])

    total = len(overdue) + len(due_today) + len(upcoming)
    header = f"📋 My Tasks ({total})"
    if overdue:
        header += f"\n⚠️ {len(overdue)} overdue!"
    await q.edit_message_text(header, reply_markup=InlineKeyboardMarkup(kb))


async def tsk_view_handler(update, context):
    q = update.callback_query
    await q.answer()
    task_id = q.data.replace("tsk_view_", "")
    rn, rd = _find_task(task_id)
    if not rd:
        await q.edit_message_text("Not found.", reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
        return

    assigned_by_name = _get_emp_name(rd[2]) if rd[2] else ""
    msg = (f"📌 {rd[0]}\n{'_' * 28}\n"
           f"Title: {rd[6]}\n"
           f"Description: {rd[7]}\n"
           f"Priority: {rd[8]}\n"
           f"Deadline: {rd[9]}\n"
           f"Status: {rd[10]}\n"
           f"Assigned by: {assigned_by_name}\n"
           f"Created: {rd[1]}")

    kb = []
    status = rd[10].strip()
    if status == "New":
        kb.append([InlineKeyboardButton("▶️ Start", callback_data=f"tsk_start_{task_id}")])
    if status in ("New", "In_Progress"):
        kb.append([InlineKeyboardButton("✅ Mark Done", callback_data=f"tsk_done_{task_id}")])
    kb.append([_bt(), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def tsk_start_handler(update, context):
    q = update.callback_query
    await q.answer()
    task_id = q.data.replace("tsk_start_", "")
    rn, _ = _find_task(task_id)
    if rn:
        ws = get_sheet("Tasks_Log")
        ws.update_cell(rn, 11, "In_Progress")  # Status
        ws.update_cell(rn, 12, _now())          # Started_At
    await q.edit_message_text(f"▶️ {task_id} started!",
                              reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))


async def tsk_done_start(update, context):
    q = update.callback_query
    await q.answer()
    task_id = q.data.replace("tsk_done_", "")
    context.user_data["tsk_done_id"] = task_id
    await q.edit_message_text(f"Completing {task_id}.\n\nAny completion notes? (or type '-'):")
    return TSK_DONE_NOTES


async def tsk_done_notes_inp(update, context):
    notes = update.message.text.strip()
    if notes == "-":
        notes = ""
    task_id = context.user_data.get("tsk_done_id", "")
    rn, rd = _find_task(task_id)
    if rn:
        ws = get_sheet("Tasks_Log")
        ws.update_cell(rn, 11, "Completed")
        ws.update_cell(rn, 13, _now())
        ws.update_cell(rn, 14, notes)
        # Notify assigner
        assigner_tid = _get_tid_by_code(rd[2]) if rd[2] else None
        if assigner_tid:
            emp = _get_emp_by_tid(update.message.from_user.id)
            emp_name = emp["name"] if emp else "Employee"
            try:
                await context.bot.send_message(
                    chat_id=assigner_tid,
                    text=f"✅ Task {task_id} completed by {emp_name}.\n"
                         f"Notes: {notes or '—'}")
            except Exception:
                pass

    await update.message.reply_text(f"✅ {task_id} completed!",
                                    reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  TEAM TASKS + ALL TASKS
# ══════════════════════════════════════════════════════════════════════════════

async def tsk_team_handler(update, context):
    q = update.callback_query
    await q.answer()
    emp = _get_emp_by_tid(q.from_user.id)
    _ensure_tab()
    try:
        rows = get_sheet("Tasks_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    # Show tasks assigned BY this manager
    ec = emp["code"] if emp else ""
    team = [r for i, r in enumerate(rows) if i > 0 and len(r) > 10 and r[2].strip() == ec]
    if not team:
        await q.edit_message_text("No team tasks.",
                                  reply_markup=InlineKeyboardMarkup([[_bt(), _bm()]]))
        return

    active = [r for r in team if r[10].strip() not in ("Completed", "Cancelled")]
    done = [r for r in team if r[10].strip() == "Completed"]

    msg = f"📊 Team Tasks\n{'_' * 28}\nActive: {len(active)} | Completed: {len(done)}"
    kb = []
    for r in active[-15:]:
        icon = "⚠️" if r[10].strip() == "Overdue" else "📌"
        name = _get_emp_name(r[3]) if r[3] else "?"
        kb.append([InlineKeyboardButton(f"{icon} {r[0]} — {name[:15]} — {r[10]}",
                                        callback_data=f"tsk_view_{r[0]}")])
    kb.append([_bt(), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


async def tsk_all_handler(update, context):
    q = update.callback_query
    await q.answer()
    _ensure_tab()
    try:
        rows = get_sheet("Tasks_Log").get_all_values()
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return

    data = [r for i, r in enumerate(rows) if i > 0 and len(r) > 10 and r[0].strip()]
    active = [r for r in data if r[10].strip() not in ("Completed", "Cancelled")]
    msg = f"📂 All Tasks\n{'_' * 28}\nTotal: {len(data)} | Active: {len(active)}"
    kb = []
    for r in active[-20:]:
        name = _get_emp_name(r[3]) if r[3] else "?"
        kb.append([InlineKeyboardButton(f"{r[0]} — {name[:12]} — {r[8]} — {r[10]}",
                                        callback_data=f"tsk_view_{r[0]}")])
    kb.append([_bt(), _bm()])
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════════════════════════════════════
#  OVERDUE CHECKER (JobQueue — runs every hour)
# ══════════════════════════════════════════════════════════════════════════════

async def check_overdue_tasks(context):
    """Called every hour. Marks overdue tasks and notifies."""
    try:
        ws = get_sheet("Tasks_Log")
        rows = ws.get_all_values()
    except Exception:
        return

    now = datetime.now()
    for i, r in enumerate(rows):
        if i == 0 or len(r) < 11: continue
        status = r[10].strip()
        if status in ("Completed", "Cancelled", "Overdue"): continue
        deadline = r[9].strip()
        try:
            dl_dt = datetime.strptime(deadline, "%d/%m/%Y")
        except Exception:
            continue
        if dl_dt.date() < now.date():
            ws.update_cell(i + 1, 11, "Overdue")
            # Notify employee
            tid = _get_tid_by_code(r[3].strip())
            if tid:
                try:
                    await context.bot.send_message(
                        chat_id=tid,
                        text=f"⚠️ Task {r[0]} is OVERDUE!\n"
                             f"Title: {r[6]}\nDeadline was: {deadline}")
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def get_task_handlers():
    assign_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tsk_assign_start, pattern="^tsk_assign_start$")],
        states={
            TSK_EMP:    [MessageHandler(filters.TEXT & ~filters.COMMAND, tsk_emp_inp)],
            TSK_TITLE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, tsk_title_inp)],
            TSK_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, tsk_desc_inp)],
            TSK_PRIO:   [CallbackQueryHandler(tsk_prio_cb, pattern="^tsk_prio_")],
            TSK_DEAD:   [MessageHandler(filters.TEXT & ~filters.COMMAND, tsk_dead_inp)],
            TSK_CONFIRM:[CallbackQueryHandler(tsk_confirm, pattern="^tsk_cfm_")],
        },
        fallbacks=[CallbackQueryHandler(tsk_cancel, pattern="^(back_to_menu|menu_tasks)$")],
        allow_reentry=True,
    )
    done_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(tsk_done_start, pattern="^tsk_done_")],
        states={
            TSK_DONE_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, tsk_done_notes_inp)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    return [assign_conv, done_conv]


def get_task_static_handlers():
    from telegram.ext import CallbackQueryHandler as CQH
    return [
        CQH(task_menu_handler,   pattern="^menu_tasks$"),
        CQH(tsk_my_handler,      pattern="^tsk_my$"),
        CQH(tsk_view_handler,    pattern="^tsk_view_"),
        CQH(tsk_start_handler,   pattern="^tsk_start_"),
        CQH(tsk_team_handler,    pattern="^tsk_team$"),
        CQH(tsk_all_handler,     pattern="^tsk_all$"),
    ]
