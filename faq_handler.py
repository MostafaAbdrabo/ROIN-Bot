"""
ROIN WORLD FZE — FAQ / Help Handler
=====================================
Reads from FAQ tab in master sheet.
FAQ tab columns: Question_ID, Question, Answer, Category
Categories: Leave, Attendance, HR, General
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from config import get_sheet

FAQ_CATEGORIES = ["Leave", "Attendance", "HR", "General"]
CATEGORY_EMOJI = {"Leave": "🏖️", "Attendance": "🕐", "HR": "🛠️", "General": "❓"}

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")


def _load_faqs():
    try:
        return get_sheet("FAQ").get_all_records()
    except Exception:
        return []


async def faq_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    kb = [
        [InlineKeyboardButton(f"{CATEGORY_EMOJI.get(c, '❓')} {c}", callback_data=f"faq_cat_{c}")]
        for c in FAQ_CATEGORIES
    ]
    kb.append([bm()])
    await q.edit_message_text(
        "❓ Help / FAQ\n\nSelect a category to see frequently asked questions:",
        reply_markup=InlineKeyboardMarkup(kb))


async def faq_category_handler(update, context):
    q = update.callback_query; await q.answer()
    cat = q.data.replace("faq_cat_", "")
    rows = _load_faqs()
    faqs = [r for r in rows if str(r.get("Category", "")).strip() == cat]
    if not faqs:
        msg = (f"{CATEGORY_EMOJI.get(cat, '❓')} {cat} — FAQ\n{'─'*28}\n\n"
               f"No questions found in this category yet.\n"
               f"Contact HR directly via 💬 Contact HR for assistance.")
    else:
        lines = [f"{CATEGORY_EMOJI.get(cat, '❓')} {cat} — FAQ\n{'─'*28}"]
        for i, faq in enumerate(faqs, 1):
            q_text = str(faq.get("Question", "")).strip()
            a_text = str(faq.get("Answer", "")).strip()
            lines.append(f"\n{i}. {q_text}\n   {a_text}")
        msg = "\n".join(lines)
    kb = [[InlineKeyboardButton("↩️ Back", callback_data="menu_help"), bm()]]
    await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))


def get_faq_handlers():
    return [
        CallbackQueryHandler(faq_menu_handler,     pattern="^menu_help$"),
        CallbackQueryHandler(faq_category_handler, pattern="^faq_cat_"),
    ]
