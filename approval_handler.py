"""
ROIN WORLD FZE — Approval Handler v9
======================================
List-based navigation:
  Pending Approvals → Category → List of requests → Open one → Approve/Reject → Back to list
"""

import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from config import get_sheet

REJECTION_REASON = 200

CHAINS = {"MGR_HR_DIR": ["manager", "hr", "director"], "MGR_HR": ["manager", "hr"]}
STAGE_COLUMNS = {0: (10, 11), 1: (12, 13), 2: (14, 15)}
ROLE_LABELS = {"manager": "Direct Manager", "hr": "HR Manager", "director": "Director", "bm": "Bot Manager"}
ROLE_PREFIX = {"manager": "mgr", "hr": "hr", "director": "dir", "bm": "bm"}
TYPE_EMOJI = {
    "Paid": "🏖", "Sick": "🤒", "Emergency": "🚨", "Unpaid": "📋",
    "Business_Trip": "🚗", "Missing_Punch": "🖐",
    "Early_Departure": "🚪", "Overtime_Planned": "⏰", "Overtime_Emergency": "🚨",
}

def bm(): return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")
def bc(): return InlineKeyboardButton("↩️ Categories", callback_data="menu_pending_approvals")


class SheetCache:
    def __init__(self):
        self.employee_db = self.user_registry = self.leave_log_raw = None
    def load_all(self):
        self.employee_db = get_sheet("Employee_DB").get_all_records()
        self.user_registry = get_sheet("User_Registry").get_all_values()
        self.leave_log_raw = get_sheet("Leave_Log").get_all_values()
    def get_employee(self, ec):
        for r in self.employee_db:
            if str(r.get("Emp_Code", "")) == str(ec):
                return {"full_name": r.get("Full_Name", "Unknown"), "department": r.get("Department", "Unknown"),
                        "manager_code": str(r.get("Manager_Code", "")),
                        "approval_chain": str(r.get("Approval_Chain", "MGR_HR")).strip()}
        return None
    def get_emp_code_by_tid(self, tid):
        for i, r in enumerate(self.user_registry):
            if i == 0: continue
            if r[1].strip() == str(tid):
                return r[0].strip(), r[3].strip() if len(r) > 3 else ""
        return None, None


def get_employee_details(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code", "")) == str(ec):
            return {"full_name": r.get("Full_Name", "Unknown"), "department": r.get("Department", "Unknown"),
                    "manager_code": str(r.get("Manager_Code", "")),
                    "approval_chain": str(r.get("Approval_Chain", "MGR_HR")).strip()}
    return None

def get_telegram_id(ec):
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[0].strip() == str(ec).strip():
            t = r[1].strip() if len(r) > 1 else ""
            return t if t else None
    return None

def get_employee_name(ec):
    for r in get_sheet("Employee_DB").get_all_records():
        if str(r.get("Emp_Code", "")) == str(ec):
            return r.get("Full_Name", ec), r.get("Department", "Unknown")
    return ec, "Unknown"

def find_leave_request(rid):
    for i, r in enumerate(get_sheet("Leave_Log").get_all_values()):
        if i == 0: continue
        if r[0].strip() == rid.strip(): return i + 1, r
    return None, None

def update_leave_log(rn, cn, v):
    get_sheet("Leave_Log").update_cell(rn, cn, v)

def get_approval_chain(ec, lt, cache=None):
    # Early Departure and Overtime: always Manager → HR only (no Director)
    if lt in ("Early_Departure", "Overtime_Planned", "Overtime_Emergency"):
        return ["manager", "hr"]
    d = cache.get_employee(ec) if cache else get_employee_details(ec)
    if not d: return ["manager", "hr"]
    chain = list(CHAINS.get(d.get("approval_chain", "MGR_HR"), CHAINS["MGR_HR"]))
    return chain

def get_current_stage(rd):
    for i, ci in enumerate([9, 11, 13]):
        if ci < len(rd) and rd[ci].strip() == "Pending": return i
    return -1

async def send_sick_photos(bot, cid, pids, cap=""):
    if not pids: return
    try:
        await bot.send_photo(chat_id=cid, photo=pids[0], caption=f"📷 {cap}Sick note" if cap else "📷 Sick note")
        for p in pids[1:]: await bot.send_photo(chat_id=cid, photo=p)
    except: pass

def build_status_line(rd, chain):
    lines = []
    for i, role in enumerate(chain):
        sc = STAGE_COLUMNS[i][0] - 1; dc = STAGE_COLUMNS[i][1] - 1
        lb = ROLE_LABELS.get(role, role)
        if sc < len(rd):
            s = rd[sc].strip(); d = rd[dc].strip() if dc < len(rd) else ""
            if s == "Approved": lines.append(f"  ✅ {lb} ({d})")
            elif s == "Rejected": lines.append(f"  ❌ {lb} ({d})")
            elif s == "Pending": lines.append(f"  ⏳ {lb}")
    return "\n".join(lines)

def request_summary(rid, rd):
    lt = rd[2] if len(rd) > 2 else "?"
    return f"{TYPE_EMOJI.get(lt, '📋')} {rid} ({rd[3]} to {rd[4]}, {rd[5]} days)"


# no auto-notify
async def notify_first_approver(bot, rid, ec, lt, sd, ed, wd, reason, sub, sick=None):
    pass


def _users_by_role(role):
    """Return list of (emp_code, telegram_id) for users with the given role."""
    result = []
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if len(r) > 3 and r[3].strip() == role:
            ec  = r[0].strip()
            tid = r[1].strip() if len(r) > 1 else ""
            if ec: result.append((ec, tid))
    return result


# Leave types that get an official order (Распоряжение)
_RASPORYA_TYPES = {"Paid", "Sick", "Emergency", "Unpaid", "Business_Trip"}


async def _generate_and_save_stage_pdf(context, rn, rd, rid, ec, lt, chain, now):
    """
    Rule 5.10 — generate PDF with all approved sigs so far, upload to Drive,
    save to Leave_Log col 21 (PDF_Drive_Link).  Returns the Drive URL or None.
    """
    try:
        from pdf_generator import generate_leave_pdf
        from drive_utils import upload_to_drive as drive_upload
        from signature_handler import get_sig_bytes

        bot = context.bot
        emp_recs = get_sheet("Employee_DB").get_all_records()
        emp_data = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(ec)), {})
        emp_name = emp_data.get("Full_Name", ec)
        emp_dept = emp_data.get("Department", "")

        directors   = _users_by_role("Director")
        hr_managers = _users_by_role("HR_Manager")
        dir_ec = directors[0][0]   if directors   else None
        hr_ec  = hr_managers[0][0] if hr_managers else None

        dir_data = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(dir_ec)), {}) if dir_ec else {}
        hr_data  = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(hr_ec)), {})  if hr_ec  else {}

        approval_chain_data = []
        for i, role in enumerate(chain):
            sc, dc = STAGE_COLUMNS[i]
            status = rd[sc - 1].strip() if sc - 1 < len(rd) else ""
            date   = rd[dc - 1].strip() if dc - 1 < len(rd) else ""
            sb, st = None, None
            if status == "Approved":
                if role == "director" and dir_ec:
                    sb, st = await get_sig_bytes(bot, dir_ec)
                elif role == "hr" and hr_ec:
                    sb, st = await get_sig_bytes(bot, hr_ec)
                else:
                    mgr_code = str(emp_data.get("Manager_Code", "")).strip()
                    if mgr_code:
                        sb, st = await get_sig_bytes(bot, mgr_code)
            approval_chain_data.append({
                "role":      ROLE_LABELS.get(role, role),
                "status":    status if status in ("Approved", "Rejected", "NA") else "Pending",
                "date":      date,
                "name":      (emp_data.get("Manager_Code", "") if role == "manager"
                              else (hr_data.get("Full_Name", "") if role == "hr"
                                    else dir_data.get("Full_Name", ""))),
                "sig_bytes": sb,
                "sig_text":  st,
            })

        cert_data = {
            "request_id":    rid,
            "full_name":     emp_name,
            "emp_code":      ec,
            "department":    emp_dept,
            "leave_type":    lt,
            "start_date":    rd[3] if len(rd) > 3 else "",
            "end_date":      rd[4] if len(rd) > 4 else "",
            "working_days":  rd[5] if len(rd) > 5 else "",
            "reason":        rd[8] if len(rd) > 8 else "",
            "submitted_at":  rd[21] if len(rd) > 21 else "",
            "final_status":  "In Progress",
            "approval_chain": approval_chain_data,
        }
        pdf_bytes = generate_leave_pdf(cert_data)
        url = drive_upload(pdf_bytes, f"LeaveProgress_{rid}.pdf", "leave_approvals")
        if url:
            update_leave_log(rn, 21, url)
        return url
    except Exception as e:
        print(f"[stage_pdf] {rid}: {e}")
        return None


async def _send_final_pdfs(context, rn, rd, rid, ec, lt, chain, now, bm_approver_ec=None):
    """
    Generate and send both PDFs after a request is fully approved.
    Called only for leave types that require a formal order.
    """
    try:
        from pdf_generator import generate_leave_pdf
        from order_generator import generate_leave_order, get_next_order_number
        from signature_handler import get_sig_bytes

        bot       = context.bot
        emp_recs  = get_sheet("Employee_DB").get_all_records()
        emp_data  = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(ec)), {})
        emp_name  = emp_data.get("Full_Name", ec)
        emp_dept  = emp_data.get("Department", "")

        # Find Director and HR Manager
        directors   = _users_by_role("Director")
        hr_managers = _users_by_role("HR_Manager")

        dir_ec   = directors[0][0]   if directors   else None
        hr_ec    = hr_managers[0][0] if hr_managers  else None
        dir_data = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(dir_ec)), {}) if dir_ec else {}
        hr_data  = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(hr_ec)), {})  if hr_ec  else {}
        hr_name  = hr_data.get("Full_Name", "HR Manager")

        # Download signatures
        dir_sig_bytes, dir_sig_text = (await get_sig_bytes(bot, dir_ec)) if dir_ec else (None, None)

        # Bot_Manager override: use BM's signature for all stages
        bm_name = None
        if bm_approver_ec:
            bm_sig_bytes, bm_sig_text = await get_sig_bytes(bot, bm_approver_ec)
            bm_emp = next((r for r in emp_recs if str(r.get("Emp_Code", "")) == str(bm_approver_ec)), {})
            bm_name = bm_emp.get("Full_Name", "Sokolov A.S.")
            dir_sig_bytes = bm_sig_bytes
            dir_sig_text  = bm_sig_text
            dir_data      = {"Full_Name": bm_name}

        # Build per-approver signature map for the approval cert
        sig_map = {}
        for i, role in enumerate(chain):
            sc, dc = STAGE_COLUMNS[i]
            status = rd[sc - 1].strip() if sc - 1 < len(rd) else ""
            if status != "Approved": continue
            if bm_approver_ec:
                sb, st = dir_sig_bytes, dir_sig_text
            elif role == "director" and dir_ec:
                sb, st = dir_sig_bytes, dir_sig_text
            elif role == "hr" and hr_ec:
                sb, st = await get_sig_bytes(bot, hr_ec)
            else:
                mgr_code = str(emp_data.get("Manager_Code", "")).strip()
                sb, st   = (await get_sig_bytes(bot, mgr_code)) if mgr_code else (None, None)
            sig_map[role] = (sb, st)

        # Build approval_chain list for pdf_generator
        approval_chain_data = []
        for i, role in enumerate(chain):
            sc, dc = STAGE_COLUMNS[i]
            status = rd[sc - 1].strip() if sc - 1 < len(rd) else "Approved"
            date   = rd[dc - 1].strip() if dc - 1 < len(rd) else now
            sb, st = sig_map.get(role, (None, None))
            approval_chain_data.append({
                "role":      ROLE_LABELS.get(role, role),
                "status":    status if status in ("Approved", "Rejected", "NA") else "Approved",
                "date":      date,
                "name":      bm_name if bm_approver_ec else (emp_name if i == 0 else (hr_name if role == "hr" else dir_data.get("Full_Name", ""))),
                "sig_bytes": sb,
                "sig_text":  st,
            })

        # Approval certificate
        cert_data = {
            "request_id":    rid,
            "full_name":     emp_name,
            "emp_code":      ec,
            "department":    emp_dept,
            "leave_type":    lt,
            "start_date":    rd[3] if len(rd) > 3 else "",
            "end_date":      rd[4] if len(rd) > 4 else "",
            "working_days":  rd[5] if len(rd) > 5 else "",
            "reason":        rd[8] if len(rd) > 8 else "",
            "submitted_at":  rd[21] if len(rd) > 21 else "",
            "final_status":  "Approved",
            "approval_chain": approval_chain_data,
        }
        cert_bytes = generate_leave_pdf(cert_data)

        # Официальный приказ only for main leave types
        order_bytes = None
        order_num   = None
        if lt in _RASPORYA_TYPES:
            order_num  = get_next_order_number()
            req_data   = {
                "request_id":   rid,
                "leave_type":   lt,
                "start_date":   rd[3] if len(rd) > 3 else "",
                "end_date":     rd[4] if len(rd) > 4 else "",
                "working_days": rd[5] if len(rd) > 5 else "",
                "reason":       rd[8] if len(rd) > 8 else "",
                "submitted_at": rd[21] if len(rd) > 21 else "",
            }
            order_bytes = generate_leave_order(
                req_data, emp_data, dir_data, hr_name,
                director_sig_bytes=dir_sig_bytes,
                director_sig_text=dir_sig_text,
                order_number=order_num,
            )
            # Save order number to Leave_Log col 23
            try:
                update_leave_log(rn, 23, order_num)
            except Exception:
                pass

        # Upload PDFs to Drive (approved → also archive to employee folder)
        from drive_utils import upload_and_archive
        from drive_utils import make_pdf_filename
        cert_fn  = make_pdf_filename(leave_type, rid, ec)
        cert_url = upload_and_archive(cert_bytes, cert_fn,
                                      "leave_approvals", emp_code=ec, emp_name=emp_name)
        order_fn = make_pdf_filename("rasporya", order_num, ec) if order_bytes else ""
        order_url = upload_and_archive(order_bytes, order_fn,
                                       "leave_orders", emp_code=ec, emp_name=emp_name) if order_bytes else None

        # Save Drive links back to Leave_Log so they appear in Requests menu
        if cert_url:
            try: update_leave_log(rn, 21, cert_url)
            except Exception: pass

        # Send to employee
        et = get_telegram_id(ec)
        if et:
            try:
                if cert_url:
                    await bot.send_message(chat_id=et,
                        text="✅ Your leave has been fully approved.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View Approval PDF", url=cert_url)]]))
                else:
                    await bot.send_document(chat_id=et,
                        document=io.BytesIO(cert_bytes),
                        filename=f"LeaveApproval_{rid}.pdf",
                        caption="Your leave has been fully approved.")
                if order_bytes:
                    if order_url:
                        await bot.send_message(chat_id=et,
                            text=f"📋 Official Leave Order: {order_num}",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View Order PDF", url=order_url)]]))
                    else:
                        await bot.send_document(chat_id=et,
                            document=io.BytesIO(order_bytes),
                            filename=f"LeaveOrder_{order_num}_{ec}.pdf",
                            caption=f"Official Leave Order: {order_num}")
            except Exception:
                pass

        # Send order link to all HR Managers
        if order_bytes:
            for _, hr_tid in hr_managers:
                if hr_tid:
                    try:
                        if order_url:
                            await bot.send_message(chat_id=hr_tid,
                                text=f"✅ Approved: {order_num} — {emp_name} ({lt})",
                                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 View Order PDF", url=order_url)]]))
                        else:
                            await bot.send_document(chat_id=hr_tid,
                                document=io.BytesIO(order_bytes),
                                filename=f"LeaveOrder_{order_num}_{ec}.pdf",
                                caption=f"Approved: {order_num} — {emp_name} ({lt})")
                    except Exception:
                        pass

    except Exception as pdf_err:
        print(f"[PDF] Error generating/sending approval PDFs: {pdf_err}")


ALL_REQUEST_TYPES = [
    "Sick", "Paid", "Emergency", "Unpaid", "Business_Trip",
    "Missing_Punch", "Early_Departure", "Overtime_Planned", "Overtime_Emergency",
]

def _get_my_pending(cache, my_code, my_role):
    role_map = {"Direct_Manager": "manager", "HR_Manager": "hr", "Director": "director"}
    grouped = {t: [] for t in ALL_REQUEST_TYPES}

    # Bot_Manager sees ALL pending requests at any stage
    if my_role == "Bot_Manager":
        for idx, row in enumerate(cache.leave_log_raw):
            if idx == 0 or len(row) < 16 or row[15].strip() != "Pending": continue
            ec, lt = row[1], row[2]
            chain = get_approval_chain(ec, lt, cache)
            if lt in ("Overtime_Planned","Overtime_Emergency") and len(row) > 13 and row[13].strip() == "Pending":
                chain = ["manager","hr","director"]
            stage = get_current_stage(row)
            if stage == -1: continue
            emp = cache.get_employee(ec)
            name = emp["full_name"] if emp else ec
            if lt in grouped: grouped[lt].append({"row": row, "name": name, "chain": chain})
        return grouped, "bm"

    mcr = role_map.get(my_role)
    if not mcr: return {}, mcr
    for idx, row in enumerate(cache.leave_log_raw):
        if idx == 0 or len(row) < 16 or row[15].strip() != "Pending": continue
        ec, lt = row[1], row[2]
        chain = get_approval_chain(ec, lt, cache)
        if lt in ("Overtime_Planned","Overtime_Emergency") and len(row) > 13 and row[13].strip() == "Pending":
            chain = ["manager","hr","director"]
        stage = get_current_stage(row)
        if stage == -1 or stage >= len(chain) or chain[stage] != mcr: continue
        if mcr == "manager":
            d = cache.get_employee(ec)
            if not d or str(d.get("manager_code", "")) != str(my_code): continue
        emp = cache.get_employee(ec)
        name = emp["full_name"] if emp else ec
        if lt in grouped: grouped[lt].append({"row": row, "name": name, "chain": chain})
    return grouped, mcr


# ══════════════════════════════════════════════════════════════════
#  PENDING APPROVALS — CATEGORIES
# ══════════════════════════════════════════════════════════════════
async def pending_approvals_handler(update, context):
    q = update.callback_query; await q.answer()
    await _cleanup_sick_photos(context, q.message.chat_id)
    await q.edit_message_text("⏳ Loading...")
    try:
        cache = SheetCache(); cache.load_all()
        my_code, my_role = cache.get_emp_code_by_tid(str(q.from_user.id))
        if not my_code or my_role not in ("Direct_Manager", "HR_Manager", "Director", "Bot_Manager"):
            await q.edit_message_text("ℹ️ No approval permissions.", reply_markup=InlineKeyboardMarkup([[bm()]]))
            return
        grouped, _ = _get_my_pending(cache, my_code, my_role)
        total = sum(len(v) for v in grouped.values())
        if total == 0:
            await q.edit_message_text("✅ No pending approvals.", reply_markup=InlineKeyboardMarkup([[bm()]]))
            return
        kb = []
        category_display = [
            ("Sick","🤒 Sick Leave"),("Paid","🏖 Paid Leave"),
            ("Emergency","🚨 Emergency Leave"),("Unpaid","📋 Unpaid Leave"),
            ("Business_Trip","🚗 Business Trip"),
            ("Missing_Punch","🖐 Missing Punch"),
            ("Early_Departure","🚪 Early Departure"),
            ("Overtime_Planned","⏰ Planned Overtime"),
            ("Overtime_Emergency","🚨 Emergency Overtime"),
        ]
        for lt, label in category_display:
            c = len(grouped.get(lt, []))
            if c > 0:
                kb.append([InlineKeyboardButton(f"{label} ({c})", callback_data=f"pending_cat_{lt}")])
        kb.append([bm()])
        await q.edit_message_text(f"📋 Pending Approvals — {total} total\n\nSelect category:",
            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bm()]]))


# ══════════════════════════════════════════════════════════════════
#  PENDING — CATEGORY → LIST OF REQUESTS
# ══════════════════════════════════════════════════════════════════
async def pending_category_handler(update, context):
    q = update.callback_query; await q.answer()
    # Clean up sick photos when navigating away from a request
    await _cleanup_sick_photos(context, q.message.chat_id)
    lt = q.data.replace("pending_cat_", "")
    await q.edit_message_text(f"⏳ Loading {lt}...")
    try:
        cache = SheetCache(); cache.load_all()
        my_code, my_role = cache.get_emp_code_by_tid(str(q.from_user.id))
        grouped, mcr = _get_my_pending(cache, my_code, my_role)
        reqs = grouped.get(lt, [])
        if not reqs:
            await q.edit_message_text(f"✅ No pending {lt} requests.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
            return
        em = TYPE_EMOJI.get(lt, "📋")
        type_label = lt.replace("_"," ")
        kb = []
        for req in reqs:
            r = req["row"]; rid = r[0]
            sub = r[21].strip() if len(r) > 21 else ""
            # For single-day requests (ED, OT, MP) show just date; for leave show range
            if lt in ("Early_Departure","Overtime_Planned","Overtime_Emergency","Missing_Punch"):
                label = f"{req['name']} — {r[3]}"
            else:
                label = f"{req['name']} — {r[3]} to {r[4]} ({r[5]}d)"
            kb.append([InlineKeyboardButton(f"{em} {label}", callback_data=f"pview_{rid}")])
        kb.append([bc(), bm()])
        await q.edit_message_text(f"{em} {type_label} — {len(reqs)} pending\n\nSelect to review:",
            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))


# ══════════════════════════════════════════════════════════════════
#  PENDING — VIEW SINGLE REQUEST DETAIL (photos auto-show for sick)
# ══════════════════════════════════════════════════════════════════
async def _cleanup_sick_photos(context, cid):
    """Delete any previously shown sick note photos from this chat."""
    key = f"sick_msg_ids_{cid}"
    msg_ids = context.bot_data.get(key, [])
    for mid in msg_ids:
        try: await context.bot.delete_message(chat_id=cid, message_id=mid)
        except: pass
    context.bot_data.pop(key, None)


async def pending_view_handler(update, context):
    q = update.callback_query; await q.answer()
    rid = q.data.replace("pview_", "")
    cid = q.message.chat_id

    # Clean up any photos from a previously viewed request
    await _cleanup_sick_photos(context, cid)

    try:
        cache = SheetCache(); cache.load_all()
        my_code, my_role = cache.get_emp_code_by_tid(str(q.from_user.id))
        role_map = {"Direct_Manager": "manager", "HR_Manager": "hr", "Director": "director", "Bot_Manager": "bm"}
        mcr = role_map.get(my_role, "manager")
        px = ROLE_PREFIX.get(mcr, "mgr")

        rd = None
        for i, r in enumerate(cache.leave_log_raw):
            if i == 0: continue
            if r[0].strip() == rid: rd = r; break
        if not rd:
            await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
            return

        ec = rd[1]; lt = rd[2]
        emp = cache.get_employee(ec)
        name = emp["full_name"] if emp else ec
        dept = emp["department"] if emp else "?"
        chain = get_approval_chain(ec, lt, cache)
        st = build_status_line(rd, chain)
        sub = rd[21].strip() if len(rd) > 21 else "-"
        em = TYPE_EMOJI.get(lt, "📋")
        back_cat = InlineKeyboardButton(f"↩️ Back to {lt} List", callback_data=f"pending_cat_{lt}")

        # Send sick photos BEFORE the detail message (they appear above)
        if lt == "Sick":
            sp = context.bot_data.get(f"sick_photos_{rid}", [])
            if sp:
                sent_ids = []
                for i, pid in enumerate(sp):
                    try:
                        cap = f"📷 Sick note {i+1}/{len(sp)} - {rid}" if i == 0 else ""
                        m = await context.bot.send_photo(chat_id=cid, photo=pid, caption=cap)
                        sent_ids.append(m.message_id)
                    except: pass
                context.bot_data[f"sick_msg_ids_{cid}"] = sent_ids

        # Build type-specific detail line
        if lt in ("Early_Departure",):
            hrs = rd[6].strip() if len(rd) > 6 and rd[6] else "?"
            lv_time = rd[7].strip() if len(rd) > 7 and rd[7] else "?"
            detail = f"⏰ Leaving at: {lv_time} ({hrs} hrs early)\n"
        elif lt in ("Overtime_Planned","Overtime_Emergency"):
            hrs = rd[6].strip() if len(rd) > 6 and rd[6] else "?"
            rate = rd[17].strip() if len(rd) > 17 and rd[17] else "1.5"
            equiv = rd[18].strip() if len(rd) > 18 and rd[18] else "?"
            detail = f"⏰ OT: {hrs} hrs × {rate} = {equiv} hrs\n"
        elif lt == "Missing_Punch":
            detail = ""
        else:
            detail = f"📅 {rd[3]} to {rd[4]} ({rd[5]} days)\n"

        # Smart leave context (Phase 4B) — only for leave types, not OT/ED/MP
        smart_ctx = ""
        if lt in ("Paid", "Sick", "Emergency", "Unpaid", "Business_Trip"):
            try:
                from manager_handler import get_smart_leave_context
                smart_ctx = get_smart_leave_context(ec, rd[3], rd[5])
                if smart_ctx: smart_ctx = f"\n{'─'*28}\n📊 Context:\n{smart_ctx}\n"
            except Exception:
                pass

        msg = (f"{em} {lt.replace('_',' ')} Request\n{'─' * 28}\n"
               f"👤 {name} ({ec})\n🏢 {dept}\n"
               f"{'📅 Date: ' + rd[3] + chr(10) if lt in ('Early_Departure','Overtime_Planned','Overtime_Emergency','Missing_Punch') else ''}"
               f"{detail}"
               f"💬 {rd[8]}\n🕐 Submitted: {sub}\n🔖 {rid}\n\n"
               f"Status:\n{st}\n"
               f"{smart_ctx}")

        # Drive link — always show current PDF before approving (Rule 5.10)
        drive_link = rd[20].strip() if len(rd) > 20 else ""

        kb = []
        if drive_link:
            kb.append([InlineKeyboardButton("📄 View Current PDF", url=drive_link)])
        kb.append([InlineKeyboardButton("✅ Approve", callback_data=f"{px}_approve_{rid}"),
                   InlineKeyboardButton("❌ Reject", callback_data=f"{px}_reject_{rid}")])
        kb.append([back_cat, bm()])

        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await q.edit_message_text(f"❌ {e}", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))


# ══════════════════════════════════════════════════════════════════
#  APPROVE — then back to category list
# ══════════════════════════════════════════════════════════════════
async def handle_approve(update, context, approver_role):
    q = update.callback_query; await q.answer()
    await _cleanup_sick_photos(context, q.message.chat_id)
    rid = q.data.split("_", 2)[2]; now = datetime.now().strftime("%d/%m/%Y %H:%M")

    rn, rd = find_leave_request(rid)
    if not rn:
        await q.edit_message_text(f"❌ Not found.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return

    ec, lt = rd[1], rd[2]; stage = get_current_stage(rd)
    if stage == -1:
        await q.edit_message_text("ℹ️ Already processed.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return
    chain = get_approval_chain(ec, lt)
    is_bm = (approver_role == "bm")
    if is_bm:
        effective_role = chain[stage] if stage < len(chain) else "manager"
    elif stage >= len(chain) or chain[stage] != approver_role:
        exp = ROLE_LABELS.get(chain[stage], "") if stage < len(chain) else ""
        await q.edit_message_text(f"ℹ️ Waiting for {exp}.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return
    else:
        effective_role = approver_role

    sm = request_summary(rid, rd)
    back_cat = InlineKeyboardButton(f"↩️ Back to {lt} List", callback_data=f"pending_cat_{lt}")

    # Bot_Manager: approve all remaining stages at once, no boundary checks
    if is_bm:
        for s in range(stage, len(chain)):
            sc2, dc2 = STAGE_COLUMNS[s]
            update_leave_log(rn, sc2, "Approved")
            update_leave_log(rn, dc2, now)
        for s in range(len(chain), 3):
            sc2, _ = STAGE_COLUMNS[s]
            update_leave_log(rn, sc2, "NA")
        update_leave_log(rn, 16, "Approved")
        bm_ec = None
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0: continue
            if r[1].strip() == str(q.from_user.id): bm_ec = r[0].strip(); break
        await q.edit_message_text(
            f"✅ {rid} FULLY APPROVED ({now})\n🎉 All stages approved!\nGenerating documents...",
            reply_markup=InlineKeyboardMarkup([[back_cat, bc(), bm()]]))
        et = get_telegram_id(ec)
        if et:
            try: await context.bot.send_message(chat_id=et, text=f"🎉 {sm}\nFully approved! ({now})\nDocuments will arrive shortly.")
            except: pass
        _, rd_fresh = find_leave_request(rid)
        await _send_final_pdfs(context, rn, rd_fresh or rd, rid, ec, lt, chain, now, bm_approver_ec=bm_ec)
        return

    sc, dc = STAGE_COLUMNS[stage]
    update_leave_log(rn, sc, "Approved"); update_leave_log(rn, dc, now)
    rl = ROLE_LABELS.get(effective_role); nxt = stage + 1
    if nxt < len(chain):
        nl = ROLE_LABELS.get(chain[nxt])
        # Rule 5.10 — generate stage PDF with current sigs, upload, save to col 21
        _, rd_int = find_leave_request(rid)
        stage_url = await _generate_and_save_stage_pdf(context, rn, rd_int or rd, rid, ec, lt, chain, now)
        await q.edit_message_text(f"✅ {rid} APPROVED ({now})\nForwarded to {nl}.",
            reply_markup=InlineKeyboardMarkup([[back_cat, bc(), bm()]]))
        et = get_telegram_id(ec)
        if et:
            try:
                emp_msg = f"✅ {sm}\nApproved by {rl} ({now}).\nWaiting for {nl}."
                emp_kb = [[InlineKeyboardButton("📄 View Current PDF", url=stage_url)]] if stage_url else []
                await context.bot.send_message(chat_id=et, text=emp_msg,
                    reply_markup=InlineKeyboardMarkup(emp_kb) if emp_kb else None)
            except: pass
    else:
        update_leave_log(rn, 16, "Approved")
        for i in range(nxt, 3):
            s, _ = STAGE_COLUMNS[i]
            if s - 1 < len(rd) and rd[s - 1].strip() in ("Pending", ""): update_leave_log(rn, s, "NA")
        await q.edit_message_text(f"✅ {rid} APPROVED ({now})\n🎉 FULLY APPROVED!\nGenerating documents...",
            reply_markup=InlineKeyboardMarkup([[back_cat, bc(), bm()]]))
        et = get_telegram_id(ec)
        if et:
            try: await context.bot.send_message(chat_id=et, text=f"🎉 {sm}\nFully approved! ({now})\nDocuments will arrive shortly.")
            except: pass
        _, rd_fresh = find_leave_request(rid)
        await _send_final_pdfs(context, rn, rd_fresh or rd, rid, ec, lt, chain, now)


# ══════════════════════════════════════════════════════════════════
#  REJECT
# ══════════════════════════════════════════════════════════════════
async def handle_reject(update, context, approver_role):
    q = update.callback_query; await q.answer()
    rid = q.data.split("_", 2)[2]
    rn, rd = find_leave_request(rid)
    if not rn:
        await q.edit_message_text("❌ Not found.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return
    stage = get_current_stage(rd)
    if stage == -1:
        await q.edit_message_text("ℹ️ Processed.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return
    chain = get_approval_chain(rd[1], rd[2])
    is_bm = (approver_role == "bm")
    effective_role = chain[stage] if (is_bm and stage < len(chain)) else approver_role
    if not is_bm and (stage >= len(chain) or chain[stage] != approver_role):
        await q.edit_message_text("ℹ️ Not your turn.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
        return
    context.user_data["rej_id"] = rid; context.user_data["rej_role"] = effective_role
    context.user_data["rej_stage"] = stage; context.user_data["rej_row"] = rd
    await q.edit_message_text(f"❌ Rejecting {rid}.\n\nType the reason:\n\nOr /cancel to go back.")
    return REJECTION_REASON

async def rejection_reason_received(update, context):
    reason = update.message.text.strip()
    if len(reason) < 3:
        await update.message.reply_text("⚠️ Too short."); return REJECTION_REASON
    rid = context.user_data.get("rej_id", ""); role = context.user_data.get("rej_role", "")
    stage = context.user_data.get("rej_stage", 0); rd = context.user_data.get("rej_row", [])
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rn, fresh = find_leave_request(rid)
    if not rn:
        await update.message.reply_text("❌ Not found."); return ConversationHandler.END
    if fresh: rd = fresh
    lt = rd[2] if len(rd) > 2 else "Paid"
    sc, dc = STAGE_COLUMNS[stage]
    update_leave_log(rn, sc, "Rejected"); update_leave_log(rn, dc, now)
    update_leave_log(rn, 16, "Rejected")
    rl = ROLE_LABELS.get(role, role); update_leave_log(rn, 17, f"{rl}: {reason}")
    sm = request_summary(rid, rd)
    back_cat = InlineKeyboardButton(f"↩️ Back to {lt} List", callback_data=f"pending_cat_{lt}")
    await update.message.reply_text(f"❌ {rid} rejected.\nReason: {reason}",
        reply_markup=InlineKeyboardMarkup([[back_cat, bc(), bm()]]))
    et = get_telegram_id(rd[1])
    if et:
        try: await context.bot.send_message(chat_id=et,
                text=f"❌ {sm}\nRejected by {rl} ({now}).\nReason: {reason}")
        except: pass
    return ConversationHandler.END

async def rejection_cancel(update, context):
    await update.message.reply_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[bc(), bm()]]))
    return ConversationHandler.END


# ── Back to menu ──
async def back_to_menu_handler(update, context):
    q = update.callback_query; await q.answer()
    await _cleanup_sick_photos(context, q.message.chat_id)
    tid = str(q.from_user.id); role = "Employee"
    for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
        if i == 0: continue
        if r[1].strip() == tid: role = r[3].strip() if len(r) > 3 else "Employee"; break
    from bot import build_inline_menu
    await q.edit_message_text("Choose an option:", reply_markup=build_inline_menu(role))


# ── Wrappers ──
async def mgr_approve(u, c): await handle_approve(u, c, "manager")
async def hr_approve(u, c): await handle_approve(u, c, "hr")
async def dir_approve(u, c): await handle_approve(u, c, "director")
async def bm_approve(u, c): await handle_approve(u, c, "bm")
async def mgr_reject(u, c): return await handle_reject(u, c, "manager")
async def hr_reject(u, c): return await handle_reject(u, c, "hr")
async def dir_reject(u, c): return await handle_reject(u, c, "director")
async def bm_reject(u, c): return await handle_reject(u, c, "bm")

def get_approval_handlers():
    def mk(p, f):
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(f, pattern=p)],
            states={REJECTION_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, rejection_reason_received)]},
            fallbacks=[MessageHandler(filters.COMMAND, rejection_cancel)], per_message=False)
    return [mk("^mgr_reject_", mgr_reject), mk("^hr_reject_", hr_reject), mk("^dir_reject_", dir_reject),
            mk("^bm_reject_", bm_reject),
            CallbackQueryHandler(mgr_approve, pattern="^mgr_approve_"),
            CallbackQueryHandler(hr_approve, pattern="^hr_approve_"),
            CallbackQueryHandler(dir_approve, pattern="^dir_approve_"),
            CallbackQueryHandler(bm_approve, pattern="^bm_approve_")]
