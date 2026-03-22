"""
ROIN WORLD FZE — Universal Document Search
==========================================
Allows authorized roles to search for any document by ID prefix.

Supported ID prefixes:
  LVE-   → Leave_Log   col 1
  OP-    → Leave_Log   col 23 (Order_Number)
  MEMO-  → Memo_Log    col 1
  СЗ-    → Memo_Log    col 10 (Registration_Number)
  JD-    → JD_Drafts   col 1
  EVL-   → Evaluations_Log col 1
  MP-    → Leave_Log   col 1 (type=Missing_Punch)
  ED-    → Leave_Log   col 1 (type=Early_Departure)
  OT-    → Leave_Log   col 1 (type=Overtime*)
  HR_REQ-→ Hiring_Requests col 1
  JP-    → Job_Postings col 1
  CND-   → Candidates  col 1
  TX-    → Stock_Transactions col 1
  BUG-/SUG-/QST-/CMP- → Bot_Feedback col 1

Access Control:
  Bot_Manager / Director   → everything
  HR_Manager / HR_Staff    → all HR documents (memos, leave, evaluations, JDs)
  Direct_Manager           → documents from their department
  Supervisor / Employee    → own documents only
"""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import get_sheet

logger = logging.getLogger(__name__)

SEARCH_INPUT = 4500   # ConversationHandler state

FULL_ACCESS_ROLES  = {"Bot_Manager", "Director"}
HR_ACCESS_ROLES    = {"HR_Manager", "HR_Staff"}
MGMT_ACCESS_ROLES  = {"Direct_Manager", "Supervisor"}
ALL_SEARCH_ROLES   = FULL_ACCESS_ROLES | HR_ACCESS_ROLES | MGMT_ACCESS_ROLES | {"Employee"}


def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bs(): return InlineKeyboardButton("🔍 New Search", callback_data="menu_search")


# ── Identity helpers ────────────────────────────────────────────────────────────

def _find_user(tid):
    """Return (emp_code, role) or (None, None)."""
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0: continue
            if len(r) > 1 and r[1].strip() == str(tid):
                return r[0].strip(), (r[3].strip() if len(r) > 3 else "Employee")
    except Exception:
        pass
    return None, None


def _get_emp(ec):
    try:
        for r in get_sheet("Employee_DB").get_all_records():
            if str(r.get("Emp_Code", "")).strip() == str(ec):
                return r
    except Exception:
        pass
    return {}


# ── Prefix routing ───────────────────────────────────────────────────────────────

def _detect_prefix(doc_id: str):
    """
    Return (sheet_tab, search_col_0indexed, extra_filter) or None.
    extra_filter is a dict {"col": int, "value": str} for additional column match.
    """
    u = doc_id.upper().strip()
    if u.startswith("LVE-"):
        return "Leave_Log", 0, None
    if u.startswith("OP-"):
        return "Leave_Log", 22, None          # col 23 = Order_Number (0-indexed 22)
    if u.startswith("MEMO-"):
        return "Memo_Log", 0, None
    if u.startswith("СЗ-") or u.startswith("СЗ-"):
        return "Memo_Log", 9, None            # Registration_Number
    if u.startswith("JD-"):
        return "JD_Drafts", 0, None
    if u.startswith("EVL-"):
        return "Evaluations_Log", 0, None
    if u.startswith("MP-"):
        return "Leave_Log", 0, {"col": 3, "value": "Missing_Punch"}
    if u.startswith("ED-"):
        return "Leave_Log", 0, {"col": 3, "value": "Early_Departure"}
    if u.startswith("OT-"):
        return "Leave_Log", 0, {"col": 3, "extra_startswith": "Overtime"}
    if u.startswith("HR_REQ-"):
        return "Hiring_Requests", 0, None
    if u.startswith("JP-"):
        return "Job_Postings", 0, None
    if u.startswith("CND-"):
        return "Candidates", 0, None
    if u.startswith("TX-"):
        return "Stock_Transactions", 0, None
    for fb_prefix in ("BUG-", "SUG-", "QST-", "CMP-"):
        if u.startswith(fb_prefix):
            return "Bot_Feedback", 0, None
    return None


def _search_sheet(tab, col, doc_id, extra_filter=None):
    """Return the first matching row (list) or None."""
    try:
        rows = get_sheet(tab).get_all_values()
        for i, r in enumerate(rows):
            if i == 0: continue
            if len(r) <= col: continue
            if r[col].strip().upper() != doc_id.upper().strip(): continue
            if extra_filter:
                ef_col = extra_filter.get("col", -1)
                if ef_col >= 0 and len(r) > ef_col:
                    cell = r[ef_col].strip()
                    if "extra_startswith" in extra_filter:
                        if not cell.upper().startswith(extra_filter["extra_startswith"].upper()):
                            continue
                    elif cell != extra_filter.get("value", ""):
                        continue
            return r
    except Exception as e:
        logger.error("search_sheet %s col%d: %s", tab, col, e)
    return None


# ── Access control ───────────────────────────────────────────────────────────────

def _can_view(role, ec, row, tab):
    """Return True if user with (role, ec) may view this row from tab."""
    if role in FULL_ACCESS_ROLES:
        return True
    if role in HR_ACCESS_ROLES:
        # HR sees all HR-relevant tabs
        if tab in ("Leave_Log", "Memo_Log", "JD_Drafts", "Evaluations_Log",
                   "Hiring_Requests", "Job_Postings", "Candidates"):
            return True
        # Stock/vehicles not for HR
        return False
    # Employee / Supervisor / Direct_Manager: own documents only
    if len(row) > 2:
        row_ec = str(row[2]).strip()
        if row_ec == str(ec):
            return True
    # Also check col 1 (requester in some sheets)
    if len(row) > 1:
        row_ec1 = str(row[1]).strip()
        if row_ec1 == str(ec):
            return True
    return False


# ── Result formatters ─────────────────────────────────────────────────────────────

def _format_leave(row, doc_id):
    """Format a Leave_Log row."""
    fields = [
        ("ID", row[0] if row else ""),
        ("Date", row[1][:10] if len(row) > 1 else ""),
        ("Employee", row[2] if len(row) > 2 else ""),
        ("Type", row[3] if len(row) > 3 else ""),
        ("Start", row[4] if len(row) > 4 else ""),
        ("End", row[5] if len(row) > 5 else ""),
        ("Days", row[6] if len(row) > 6 else ""),
        ("Status", row[15] if len(row) > 15 else ""),
        ("Order#", row[22] if len(row) > 22 else ""),
    ]
    msg = "🔍 Leave Request\n" + "─" * 24 + "\n"
    for label, val in fields:
        if val: msg += f"{label}: {val}\n"
    drive_link = row[20] if len(row) > 20 else ""  # PDF_Drive_Link col 21
    return msg, drive_link


def _format_memo(row, doc_id):
    """Format a Memo_Log row."""
    fields = [
        ("ID", row[0] if row else ""),
        ("Date", row[1][:10] if len(row) > 1 else ""),
        ("Employee", row[2] if len(row) > 2 else ""),
        ("Topic", row[6] if len(row) > 6 else ""),
        ("Registration", row[9] if len(row) > 9 else ""),
        ("Status", row[20] if len(row) > 20 else ""),
    ]
    msg = "🔍 Memo\n" + "─" * 24 + "\n"
    for label, val in fields:
        if val: msg += f"{label}: {val}\n"
    drive_link = row[23] if len(row) > 23 else ""  # Drive_Link col 24
    return msg, drive_link


def _format_generic(row, doc_id, tab):
    """Generic formatter — show first 8 non-empty cells."""
    msg = f"🔍 {tab}\n" + "─" * 24 + "\n"
    msg += f"ID: {row[0] if row else doc_id}\n"
    for i, val in enumerate(row[1:8], start=2):
        if val: msg += f"Col {i}: {val}\n"
    return msg, ""


def _format_row(row, tab, doc_id):
    """Dispatch to appropriate formatter."""
    if tab == "Leave_Log":
        return _format_leave(row, doc_id)
    if tab == "Memo_Log":
        return _format_memo(row, doc_id)
    return _format_generic(row, doc_id, tab)


# ── Handler flow ──────────────────────────────────────────────────────────────────

async def search_menu_handler(update, context):
    """Entry: 🔍 Search Documents."""
    q = update.callback_query; await q.answer()
    ec, role = _find_user(str(q.from_user.id))
    if not ec or role not in ALL_SEARCH_ROLES:
        await q.edit_message_text(
            "⛔ You don't have permission to search documents.",
            reply_markup=InlineKeyboardMarkup([[bm()]])
        )
        return ConversationHandler.END
    context.user_data["search_ec"] = ec
    context.user_data["search_role"] = role
    await q.edit_message_text(
        "🔍 Search Documents\n\nType the document ID and send:\n\n"
        "Examples:\n"
        "  LVE-2026-0042\n"
        "  MEMO-2026-0001\n"
        "  OP-2026-015\n"
        "  JD-20260320162057\n"
        "  EVL-2026-0045\n"
        "  HR_REQ-2026-0001\n"
        "  BUG-0001\n\n"
        "Send the ID now:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="back_to_menu")]])
    )
    return SEARCH_INPUT


async def search_input_received(update, context):
    """Handle incoming document ID."""
    doc_id = update.message.text.strip()
    ec     = context.user_data.get("search_ec")
    role   = context.user_data.get("search_role")

    result = _detect_prefix(doc_id)
    if not result:
        await update.message.reply_text(
            "⚠️ Unknown document prefix.\n\nCheck the ID format and try again.",
            reply_markup=InlineKeyboardMarkup([[bs(), bm()]])
        )
        return SEARCH_INPUT

    tab, col, extra_filter = result
    row = _search_sheet(tab, col, doc_id, extra_filter)
    if row is None:
        await update.message.reply_text(
            f"❌ Document not found: {doc_id}\n\nCheck the ID and try again.",
            reply_markup=InlineKeyboardMarkup([[bs(), bm()]])
        )
        return SEARCH_INPUT

    if not _can_view(role, ec, row, tab):
        await update.message.reply_text(
            "⛔ You don't have permission to view this document.",
            reply_markup=InlineKeyboardMarkup([[bs(), bm()]])
        )
        return SEARCH_INPUT

    msg, drive_link = _format_row(row, tab, doc_id)
    kb = []
    if drive_link and drive_link.startswith("http"):
        kb.append([InlineKeyboardButton("📄 View PDF", url=drive_link)])
    kb.append([bs(), bm()])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    return SEARCH_INPUT


async def search_cancel(update, context):
    if update.message:
        await update.message.reply_text("Search cancelled.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    return ConversationHandler.END


# ── Handler registration ──────────────────────────────────────────────────────────

def get_search_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(search_menu_handler, pattern="^menu_search$")],
        states={
            SEARCH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_input_received),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, search_cancel),
            CallbackQueryHandler(search_cancel, pattern="^back_to_menu$"),
        ],
        per_message=False,
    )
