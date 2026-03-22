"""
ROIN WORLD FZE — Electronic Signature Handler
==============================================
Handles per-employee signature setup, storage (Telegram file_id in
Employee_DB.Signature_Link), and retrieval for embedding in PDFs.

Signature_Link column values:
  ""      — no signature set
  "TEXT"  — text-based signature only
  "<fid>" — Telegram photo file_id (image signature)
"""

import io, os, secrets
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import get_sheet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SIG_PHOTO = 3100   # ConversationHandler state

def bm(): return InlineKeyboardButton("↩️ Main Menu",   callback_data="back_to_menu")
def bp(): return InlineKeyboardButton("↩️ My Profile",  callback_data="menu_my_profile")


# ── Sheet helpers ──────────────────────────────────────────────────────────────

def _find_ec(tid):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == str(tid): return r[0].strip()
    return None


def _get_emp(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code", "")).strip() == str(ec):
            return r
    return None


def _get_emp_row_num(ec):
    for i, r in enumerate(get_sheet("Employee_DB").get_all_values()):
        if i == 0: continue
        if r[0].strip() == str(ec): return i + 1
    return None


def _get_sig_col():
    """1-based column index of Signature_Link in Employee_DB; None if missing."""
    headers = get_sheet("Employee_DB").row_values(1)
    try:
        return headers.index("Signature_Link") + 1
    except ValueError:
        return None


# ── Public API (used by PDF generators) ──────────────────────────────────────

def get_signature_info(ec):
    """
    Returns (file_id_or_None, has_text_sig: bool, emp_name: str).
      file_id is a Telegram photo file_id if an image signature exists.
      has_text_sig is True when Signature_Link == "TEXT".
    """
    emp = _get_emp(ec)
    if not emp:
        return None, False, str(ec)
    name = str(emp.get("Full_Name", ec))
    sig  = str(emp.get("Signature_Link", "")).strip()
    if not sig or sig.upper().startswith("LOCAL:"):
        return None, False, name   # triggers local-file lookup in get_sig_bytes
    if sig.upper() == "TEXT":
        return None, True, name
    return sig, False, name   # sig = Telegram file_id


def make_text_sig(name, dt=None):
    """Return the standard text-signature string."""
    ts = (dt or datetime.now()).strftime("%d/%m/%Y %H:%M")
    return f"{name} -- Electronically signed -- {ts}"


def gen_verification_code():
    return f"SIG-{secrets.token_hex(4).upper()}"


async def get_sig_bytes(bot, ec):
    """
    Async helper: downloads signature image bytes for an employee.
    Returns (image_bytes_or_None, text_sig_or_None).
      If image available  → (bytes, None)
      If text sig only    → (None, text_string)
      If no signature     → (None, None)

    Special: if no Signature_Link is set, checks for a local file
    named <ec>_signature.png in the bot directory (e.g. 1049_signature.png).
    """
    file_id, has_text, name = get_signature_info(ec)

    # Check local pre-loaded signature file (e.g. 1049_signature.png)
    if not file_id and not has_text:
        local = os.path.join(BASE_DIR, f"{ec}_signature.png")
        if os.path.exists(local):
            try:
                with open(local, "rb") as f:
                    return f.read(), None
            except Exception:
                pass

    if file_id:
        try:
            f    = await bot.get_file(file_id)
            data = await f.download_as_bytearray()
            return bytes(data), None
        except Exception:
            pass    # fall through to text
    if has_text:
        return None, make_text_sig(name)
    return None, None


# ── Conversation: Setup Signature ─────────────────────────────────────────────

async def sig_setup_start(update, context):
    """Entry point: My Profile → ✍️ Setup Signature."""
    q  = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]])); return ConversationHandler.END

    context.user_data["sig_ec"] = ec
    file_id, has_text, _ = get_signature_info(ec)
    current = "Image signature" if file_id else ("Text signature" if has_text else "None")

    await q.edit_message_text(
        f"Setup Signature\n\nCurrent: {current}\n\n"
        "Write your signature on white paper, take a clear photo, and send it here.\n\n"
        "Or type exactly:  USE TEXT SIGNATURE\n"
        "to use a name-based electronic signature instead.\n\n"
        "Send photo or type now:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Cancel", callback_data="menu_my_profile")
        ]])
    )
    return SIG_PHOTO


async def sig_photo_received(update, context):
    """Handle photo or text response during signature setup."""
    ec = context.user_data.get("sig_ec")
    if not ec:
        await update.message.reply_text("Session expired. Try again."); return ConversationHandler.END

    if update.message.photo:
        val   = update.message.photo[-1].file_id   # highest resolution
        label = "image signature"
    elif update.message.text and update.message.text.strip().upper() == "USE TEXT SIGNATURE":
        val   = "TEXT"
        label = "text signature"
    else:
        await update.message.reply_text(
            "Please send a photo of your signature, or type:  USE TEXT SIGNATURE"
        )
        return SIG_PHOTO

    try:
        col = _get_sig_col()
        if not col:
            await update.message.reply_text(
                "Signature_Link column not found in Employee_DB. Ask the admin to add it."
            ); return ConversationHandler.END

        rn = _get_emp_row_num(ec)
        if not rn:
            await update.message.reply_text("Employee record not found."); return ConversationHandler.END

        get_sheet("Employee_DB").update_cell(rn, col, val)
        emp  = _get_emp(ec)
        name = emp.get("Full_Name", ec) if emp else ec

        preview = ""
        if val == "TEXT":
            preview = f"\nPreview: {make_text_sig(name)}"

        await update.message.reply_text(
            f"Signature saved!\n\nType: {label.capitalize()}{preview}\n\n"
            "It will appear on all documents you approve.",
            reply_markup=InlineKeyboardMarkup([[bp(), bm()]])
        )
    except Exception as e:
        await update.message.reply_text(f"Error saving: {e}")
    return ConversationHandler.END


async def sig_cancel(update, context):
    await update.message.reply_text(
        "Cancelled.", reply_markup=InlineKeyboardMarkup([[bp(), bm()]])
    )
    return ConversationHandler.END


# ── Static handlers: View / Manage / Admin ────────────────────────────────────

async def sig_view_handler(update, context):
    """My Profile → My Signature — view + manage options."""
    q  = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]])); return

    file_id, has_text, name = get_signature_info(ec)

    if file_id:
        status = "Image signature set"
        try:
            await q.message.reply_photo(file_id, caption="Your current signature")
        except Exception:
            pass
    elif has_text:
        status = f"Text signature:\n{make_text_sig(name)}"
    else:
        status = "No signature set"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Update Signature",   callback_data="sig_setup")],
        [InlineKeyboardButton("Switch to Text Sig", callback_data="sig_set_text")],
        [InlineKeyboardButton("Remove Signature",   callback_data="sig_remove")],
        [bp(), bm()],
    ])
    await q.edit_message_text(f"My Signature\n\nStatus: {status}", reply_markup=kb)


async def sig_set_text_handler(update, context):
    """Switch to text-based signature."""
    q  = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]])); return
    try:
        col = _get_sig_col(); rn = _get_emp_row_num(ec)
        if col and rn:
            get_sheet("Employee_DB").update_cell(rn, col, "TEXT")
            emp  = _get_emp(ec)
            name = emp.get("Full_Name", ec) if emp else ec
            await q.edit_message_text(
                f"Switched to text signature.\n\nPreview: {make_text_sig(name)}",
                reply_markup=InlineKeyboardMarkup([[bp(), bm()]])
            )
        else:
            await q.edit_message_text("Could not update — column not found.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))


async def sig_remove_handler(update, context):
    """Remove signature."""
    q  = update.callback_query; await q.answer()
    ec = _find_ec(str(q.from_user.id))
    if not ec:
        await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[bm()]])); return
    try:
        col = _get_sig_col(); rn = _get_emp_row_num(ec)
        if col and rn:
            get_sheet("Employee_DB").update_cell(rn, col, "")
            await q.edit_message_text("Signature removed.", reply_markup=InlineKeyboardMarkup([[bp(), bm()]]))
        else:
            await q.edit_message_text("Could not update — column not found.", reply_markup=InlineKeyboardMarkup([[bm()]]))
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))


async def sig_admin_handler(update, context):
    """HR/Bot_Manager: view all employees with/without signatures."""
    q = update.callback_query; await q.answer()
    await q.edit_message_text("Loading signatures...")
    try:
        rows        = get_sheet("Employee_DB").get_all_records()
        with_sig    = []
        without_sig = []
        for r in rows:
            ec   = str(r.get("Emp_Code", "")).strip()
            name = str(r.get("Full_Name", "")).strip()
            sig  = str(r.get("Signature_Link", "")).strip()
            if not ec or not name: continue
            if str(r.get("Status", "")).strip() == "Terminated": continue
            if sig:
                kind = "text" if sig.upper() == "TEXT" else "image"
                with_sig.append(f"{ec} — {name} ({kind})")
            else:
                without_sig.append(f"{ec} — {name}")

        msg = (f"Signature Overview\n{'─'*28}\n"
               f"With signature:    {len(with_sig)}\n"
               f"Without signature: {len(without_sig)}\n")
        if without_sig:
            sample = without_sig[:20]
            msg   += "\nNo signature:\n" + "\n".join(sample)
            if len(without_sig) > 20:
                msg += f"\n... and {len(without_sig) - 20} more"

        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[bm()]]))
    except Exception as e:
        await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))


# ── Handler registration ──────────────────────────────────────────────────────

def get_sig_setup_handler():
    """ConversationHandler for photo upload flow."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(sig_setup_start, pattern="^sig_setup$")],
        states={
            SIG_PHOTO: [
                MessageHandler(
                    (filters.PHOTO | filters.TEXT) & ~filters.COMMAND,
                    sig_photo_received
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, sig_cancel)],
        per_message=False,
    )


def get_sig_static_handlers():
    return [
        CallbackQueryHandler(sig_view_handler,     pattern="^sig_view$"),
        CallbackQueryHandler(sig_set_text_handler, pattern="^sig_set_text$"),
        CallbackQueryHandler(sig_remove_handler,   pattern="^sig_remove$"),
        CallbackQueryHandler(sig_admin_handler,    pattern="^sig_admin$"),
    ]
