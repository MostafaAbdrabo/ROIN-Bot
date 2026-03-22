"""
ROIN WORLD FZE — Performance Evaluation Handler
=================================================
Phase 9:
Scoring (100 pts):
  Auto (70pts): attendance(20), lateness(10), task_placeholder(20),
                overdue_placeholder(10), leave_pattern(10)
  Manager (30pts): work_quality(10), communication(8), initiative(7), sop_adherence(5)

Triggers: quarterly, contract renewal (-30d), probation end (-15d), on-demand
Flow: Manager sees auto scores → rates 4 criteria → comment → submit → HR reviews → Director approves → PDF

Evaluations_Log tab:
  Eval_ID, Emp_Code, Period, Trigger_Type, Auto_Score, Manager_Score,
  Final_Score, Rating, Recommendation, Eval_Date, HR_Reviewed,
  Director_Approved, Report_Drive_Link, Manager_Comments
"""

import io, os
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler, MessageHandler, filters)
from config import get_sheet, CURRENT_ATTENDANCE_TAB
from attendance_handler import get_my_attendance_summary
from fpdf import FPDF

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")

# Conversation states
EVAL_EMP_SEL    = 900
EVAL_QUALITY    = 901
EVAL_COMM       = 902
EVAL_INITIATIVE = 903
EVAL_SOP        = 904
EVAL_COMMENT    = 905
EVAL_CONFIRM    = 906
EVAL_HR_ACTION  = 910

RATING_SCALE = [
    (90, "Excellent",      "Promote / Salary Increase"),
    (75, "Good",           "Renew Standard Terms"),
    (60, "Acceptable",     "Renew with Improvement Plan"),
    (45, "Weak",           "Warning / Extend Probation"),
    (0,  "Unsatisfactory", "Termination Review"),
]

def _logo_path():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_logo.png")
    return p if os.path.exists(p) else None

def _safe(text):
    if not text: return ""
    return str(text).encode('latin-1', errors='replace').decode('latin-1')

def _gen_eval_id():
    ids = get_sheet("Evaluations_Log").col_values(1)
    yr  = datetime.now().strftime("%Y")
    px  = f"EVL-{yr}-"
    mx  = 0
    for v in ids:
        if str(v).startswith(px):
            try: n = int(str(v).split("-")[-1]); mx = max(mx, n)
            except: pass
    return f"{px}{mx+1:04d}"


def _get_rating(score):
    for threshold, rating, rec in RATING_SCALE:
        if score >= threshold: return rating, rec
    return "Unsatisfactory", "Termination Review"


def _compute_auto_score(ec):
    """Compute automated portion of score (70 pts max)."""
    scores = {}
    # Attendance rate (20 pts)
    try:
        s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
        if s:
            rate = s["rate"]
            if rate >= 97:   scores["attendance"] = 20
            elif rate >= 95: scores["attendance"] = 17
            elif rate >= 92: scores["attendance"] = 14
            elif rate >= 88: scores["attendance"] = 10
            else:            scores["attendance"] = 5
        else: scores["attendance"] = 10  # no data
    except Exception: scores["attendance"] = 10

    # Lateness (10 pts) — check absent count as proxy for lateness
    try:
        s = get_my_attendance_summary(ec, CURRENT_ATTENDANCE_TAB)
        if s:
            ab = s.get("absent",0)
            if ab == 0:   scores["lateness"] = 10
            elif ab <= 3: scores["lateness"] = 7
            elif ab <= 7: scores["lateness"] = 4
            else:         scores["lateness"] = 0
        else: scores["lateness"] = 7
    except Exception: scores["lateness"] = 7

    # Task completion (placeholder until Phase 16)
    scores["task_completion"] = 15

    # Overdue tasks (placeholder)
    scores["overdue_tasks"] = 7

    # Leave pattern (10 pts) — check if has any unexcused absences
    try:
        leave_rows = get_sheet("Leave_Log").get_all_records()
        flagged = sum(1 for r in leave_rows
                      if str(r.get("Emp_Code","")).strip() == ec
                      and str(r.get("Request_Type","")) == "Unpaid"
                      and str(r.get("Final_Status","")) == "Approved")
        if flagged == 0:   scores["leave_pattern"] = 10
        elif flagged <= 1: scores["leave_pattern"] = 5
        else:              scores["leave_pattern"] = 0
    except Exception: scores["leave_pattern"] = 10

    auto_total = sum(scores.values())
    return auto_total, scores


def _get_team_for_eval(my_code, my_role):
    team = []
    for r in get_sheet("Employee_DB").get_all_records():
        ec = str(r.get("Emp_Code","")).strip()
        if not ec or str(r.get("Status","")).strip() == "Terminated": continue
        if my_role == "Direct_Manager" and str(r.get("Manager_Code","")).strip() == str(my_code):
            team.append(r)
        elif my_role in ("HR_Manager","Director"):
            team.append(r)
    return team


# ── Main eval menu ─────────────────────────────────────────────────────────────

async def eval_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    role = "Employee"
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip(); break
    kb = []
    if role in ("Direct_Manager","HR_Manager","Director"):
        kb.append([InlineKeyboardButton("📋 Start Evaluation",    callback_data="eval_start")])
        kb.append([InlineKeyboardButton("📊 Pending Evaluations", callback_data="eval_pending")])
    if role in ("HR_Manager","Director"):
        kb.append([InlineKeyboardButton("✅ HR Review",           callback_data="eval_hr_review")])
    kb.append([InlineKeyboardButton("📈 My Evaluations",          callback_data="eval_my")])
    kb.append([bm()])
    await q.edit_message_text("📊 Performance Evaluation\n\nSelect option:", reply_markup=InlineKeyboardMarkup(kb))


async def eval_my_handler(update, context):
    """Employee sees their own evaluation history."""
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    ec  = None
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: ec = r[0].strip(); break
    try:
        rows = get_sheet("Evaluations_Log").get_all_records()
        mine = [r for r in rows if str(r.get("Emp_Code","")).strip() == ec]
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    if not mine:
        await q.edit_message_text("📈 My Evaluations\n\nNo evaluations on record yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    lines = ["📈 My Evaluations\n"]
    for r in mine:
        lines.append(f"• {r.get('Eval_ID','')} | {r.get('Period','')} | "
                     f"{r.get('Final_Score','')}pts — {r.get('Rating','')}")
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]]
    await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


# ── Start evaluation flow ──────────────────────────────────────────────────────

async def eval_start(update, context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    my_code = None; my_role = "Employee"
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: my_code = r[0].strip(); my_role = r[3].strip(); break
    team = _get_team_for_eval(my_code, my_role)
    if not team:
        await q.edit_message_text("No team members to evaluate.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    kb = [[InlineKeyboardButton(f"👤 {r.get('Full_Name','?')} ({r.get('Emp_Code','?')})",
                                callback_data=f"eval_emp_{r.get('Emp_Code','')}")] for r in team[:15]]
    kb.append([bm()])
    await q.edit_message_text("📋 Select employee to evaluate:", reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_EMP_SEL


async def eval_emp_sel(update, context):
    q = update.callback_query; await q.answer()
    ec = q.data.replace("eval_emp_","")
    context.user_data["eval_ec"] = ec
    await q.edit_message_text("⏳ Computing auto scores...")
    auto_score, scores = _compute_auto_score(ec)
    context.user_data["eval_auto"]   = auto_score
    context.user_data["eval_scores"] = scores
    # Get employee name
    name = ec
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code","")).strip() == ec: name = r.get("Full_Name", ec); break
    except Exception: pass
    context.user_data["eval_name"] = name
    msg = (f"📋 Evaluating: {name} ({ec})\n{'─'*28}\n"
           f"AUTO SCORES (70 pts max):\n"
           f"  Attendance:      {scores.get('attendance',0)}/20\n"
           f"  Lateness:        {scores.get('lateness',0)}/10\n"
           f"  Task Completion: {scores.get('task_completion',0)}/20 (placeholder)\n"
           f"  Overdue Tasks:   {scores.get('overdue_tasks',0)}/10 (placeholder)\n"
           f"  Leave Pattern:   {scores.get('leave_pattern',0)}/10\n"
           f"  AUTO TOTAL:      {auto_score}/70\n\n"
           f"Now rate 4 criteria (1-5):\n"
           f"Step 1/4: Work Quality (×2 = up to 10pts)")
    kb = [[InlineKeyboardButton(str(i), callback_data=f"eval_q_{i}") for i in range(1,6)], [bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_QUALITY


async def eval_quality(update, context):
    q = update.callback_query; await q.answer()
    score = int(q.data.replace("eval_q_",""))
    context.user_data["eval_quality"] = score * 2  # ×2
    kb = [[InlineKeyboardButton(str(i), callback_data=f"eval_c_{i}") for i in range(1,6)], [bm()]]
    await q.edit_message_text(
        f"Step 2/4: Communication (×1.6 = up to 8pts)\n"
        f"Work Quality: {score}/5 → {score*2}pts",
        reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_COMM


async def eval_comm(update, context):
    q = update.callback_query; await q.answer()
    score = int(q.data.replace("eval_c_",""))
    context.user_data["eval_comm"] = round(score * 1.6)
    kb = [[InlineKeyboardButton(str(i), callback_data=f"eval_i_{i}") for i in range(1,6)], [bm()]]
    await q.edit_message_text(
        f"Step 3/4: Initiative (×1.4 = up to 7pts)\n"
        f"Communication: {score}/5 → {context.user_data['eval_comm']}pts",
        reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_INITIATIVE


async def eval_initiative(update, context):
    q = update.callback_query; await q.answer()
    score = int(q.data.replace("eval_i_",""))
    context.user_data["eval_init"] = round(score * 1.4)
    kb = [[InlineKeyboardButton(str(i), callback_data=f"eval_s_{i}") for i in range(1,6)], [bm()]]
    await q.edit_message_text(
        f"Step 4/4: SOP Adherence (×1 = up to 5pts)\n"
        f"Initiative: {score}/5 → {context.user_data['eval_init']}pts",
        reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_SOP


async def eval_sop(update, context):
    q = update.callback_query; await q.answer()
    score = int(q.data.replace("eval_s_",""))
    context.user_data["eval_sop"] = score
    mgr_score = (context.user_data["eval_quality"] + context.user_data["eval_comm"] +
                 context.user_data["eval_init"] + score)
    context.user_data["eval_mgr"] = mgr_score
    total = context.user_data["eval_auto"] + mgr_score
    context.user_data["eval_total"] = total
    rating, rec = _get_rating(total)
    context.user_data["eval_rating"] = rating
    context.user_data["eval_rec"]    = rec
    await q.edit_message_text(
        f"Step 5/5: Add a comment (or type '-' to skip):",
        reply_markup=InlineKeyboardMarkup([[bm()]]))
    return EVAL_COMMENT


async def eval_comment_inp(update, context):
    comment = update.message.text.strip()
    if comment == "-": comment = ""
    context.user_data["eval_comment"] = comment
    total  = context.user_data["eval_total"]
    rating = context.user_data["eval_rating"]
    rec    = context.user_data["eval_rec"]
    name   = context.user_data["eval_name"]
    ec     = context.user_data["eval_ec"]
    msg = (f"📋 Evaluation Summary\n{'─'*28}\n"
           f"Employee:     {name} ({ec})\n"
           f"Auto Score:   {context.user_data['eval_auto']}/70\n"
           f"Manager Score:{context.user_data['eval_mgr']}/30\n"
           f"TOTAL:        {total}/100\n"
           f"Rating:       {rating}\n"
           f"Recommendation: {rec}\n"
           f"Comment: {comment or '(none)'}\n\n"
           f"Submit for HR review?")
    kb = [[InlineKeyboardButton("✅ Submit", callback_data="eval_submit"),
           InlineKeyboardButton("❌ Cancel", callback_data="eval_cancel")],
          [bm()]]
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return EVAL_CONFIRM


async def eval_submit(update, context):
    q = update.callback_query; await q.answer()
    if q.data == "eval_cancel":
        await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
        return ConversationHandler.END
    try:
        eval_id = _gen_eval_id()
        now     = datetime.now().strftime("%d/%m/%Y %H:%M")
        ws      = get_sheet("Evaluations_Log")
        ws.append_row([
            eval_id,
            context.user_data["eval_ec"],
            "",  # Full_Name (VLOOKUP col C)
            "",  # Department (VLOOKUP col D)
            now[:7],  # period: MM/YYYY
            "On_Demand",
            context.user_data["eval_auto"],
            context.user_data["eval_mgr"],
            context.user_data["eval_total"],
            context.user_data["eval_rating"],
            context.user_data["eval_rec"],
            now,
            "No", "No", "",
            context.user_data.get("eval_comment","")
        ], value_input_option="USER_ENTERED")
        await q.edit_message_text(
            f"✅ Evaluation submitted!\nID: {eval_id}\nScore: {context.user_data['eval_total']}/100\n"
            f"Rating: {context.user_data['eval_rating']}\nAwaiting HR review.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]]))
    return ConversationHandler.END


# ── HR Review ──────────────────────────────────────────────────────────────────

async def eval_hr_review(update, context):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("⏳ Loading pending evaluations...")
    try:
        rows = get_sheet("Evaluations_Log").get_all_records()
        pending = [r for r in rows if str(r.get("HR_Reviewed","")).strip() != "Yes"]
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    if not pending:
        await q.edit_message_text("✅ No evaluations pending HR review.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    kb = [[InlineKeyboardButton(f"📋 {r.get('Eval_ID','')} — {r.get('Emp_Code','')} {r.get('Rating','')} ({r.get('Final_Score','')}pts)",
                                callback_data=f"eval_hr_approve_{r.get('Eval_ID','')}")] for r in pending[:10]]
    kb.append([bm()])
    await q.edit_message_text(f"📋 Pending HR Review ({len(pending)}):", reply_markup=InlineKeyboardMarkup(kb))


async def eval_hr_approve(update, context):
    q = update.callback_query; await q.answer()
    eval_id = q.data.replace("eval_hr_approve_","")
    try:
        ws   = get_sheet("Evaluations_Log")
        rows = ws.get_all_values()
        hdr  = rows[0] if rows else []
        try: id_col = hdr.index("Eval_ID") + 1
        except: id_col = 1
        try: hr_col = hdr.index("HR_Reviewed") + 1
        except: hr_col = 11
        for i, row in enumerate(rows):
            if i == 0: continue
            if len(row) >= id_col and row[id_col-1] == eval_id:
                ws.update_cell(i+1, hr_col, "Yes")
                break
        await q.edit_message_text(f"✅ Evaluation {eval_id} marked as HR Reviewed.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="eval_hr_review"), bm()]]))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="eval_hr_review"), bm()]]))


async def eval_pending_handler(update, context):
    q = update.callback_query; await q.answer()
    tid = str(q.from_user.id)
    my_code = None; my_role = "Employee"
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: my_code = r[0].strip(); my_role = r[3].strip(); break
    try:
        rows = get_sheet("Evaluations_Log").get_all_records()
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]])); return
    lines = ["📊 Evaluations\n"]
    for r in rows[-10:]:
        lines.append(f"• {r.get('Eval_ID','')} {r.get('Emp_Code','')} — {r.get('Rating','')} {r.get('Final_Score','')}pts")
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_eval"), bm()]]
    await q.edit_message_text("\n".join(lines) or "No evaluations yet.",
                               reply_markup=InlineKeyboardMarkup(kb))


async def eval_cancel_handler(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


def get_eval_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(eval_start, pattern="^eval_start$")],
        states={
            EVAL_EMP_SEL:    [CallbackQueryHandler(eval_emp_sel,    pattern="^eval_emp_")],
            EVAL_QUALITY:    [CallbackQueryHandler(eval_quality,    pattern="^eval_q_")],
            EVAL_COMM:       [CallbackQueryHandler(eval_comm,       pattern="^eval_c_")],
            EVAL_INITIATIVE: [CallbackQueryHandler(eval_initiative, pattern="^eval_i_")],
            EVAL_SOP:        [CallbackQueryHandler(eval_sop,        pattern="^eval_s_")],
            EVAL_COMMENT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, eval_comment_inp)],
            EVAL_CONFIRM:    [CallbackQueryHandler(eval_submit, pattern="^eval_(submit|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, eval_cancel_handler)],
        per_message=False,
    )


def get_eval_static_handlers():
    return [
        CallbackQueryHandler(eval_menu_handler,   pattern="^menu_eval$"),
        CallbackQueryHandler(eval_my_handler,     pattern="^eval_my$"),
        CallbackQueryHandler(eval_hr_review,      pattern="^eval_hr_review$"),
        CallbackQueryHandler(eval_hr_approve,     pattern="^eval_hr_approve_"),
        CallbackQueryHandler(eval_pending_handler,pattern="^eval_pending$"),
    ]
