"""
regen_pdfs_handler.py — /regenerate_pdfs command for Bot_Manager

Scans Leave_Log and Memo_Log for approved rows with an empty Drive link,
generates the PDF for each, uploads to Drive, and saves the link back
to the sheet.  Run once to backfill all old requests.
"""

import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from config import get_sheet, TAB_USER_REGISTRY, TAB_LEAVE_LOG, TAB_MEMO_LOG
from drive_utils import upload_to_drive


# ── helpers ──────────────────────────────────────────────────────────────────

def _emp_db():
    """Return {Emp_Code: record_dict} from Employee_DB."""
    out = {}
    for r in get_sheet("Employee_DB").get_all_records():
        ec = str(r.get("Emp_Code", "")).strip()
        if ec:
            out[ec] = r
    return out


def _get_role(tid: str) -> str:
    for i, r in enumerate(get_sheet(TAB_USER_REGISTRY).get_all_values()):
        if i == 0:
            continue
        if r[1].strip() == tid:
            return r[3] if len(r) > 3 else ""
    return ""


# ── Leave_Log regeneration ────────────────────────────────────────────────────

_STAGE_PAIRS = [(9, 10), (11, 12), (13, 14)]   # 0-indexed (status_col, date_col)
_STAGE_ROLES = {0: "Direct Manager", 1: "HR Manager", 2: "Director"}


def _regen_leave_row(row: list, emp_db: dict):
    """Return (pdf_bytes, filename) for a Leave_Log row, or (None, None)."""
    from pdf_generator import generate_leave_pdf

    rid  = row[0].strip()
    ec   = row[1].strip()
    lt   = row[2].strip()
    emp  = emp_db.get(ec, {})

    # Build approval chain from sheet data (no live signatures — backfill)
    chain = []
    for idx, (sc, dc) in enumerate(_STAGE_PAIRS):
        status = row[sc].strip() if sc < len(row) else ""
        date   = row[dc].strip() if dc < len(row) else ""
        if status and status not in ("", "Pending", "Skipped", "NA"):
            chain.append({
                "role":      _STAGE_ROLES.get(idx, f"Stage {idx}"),
                "status":    status,
                "date":      date,
                "name":      "",
                "sig_bytes": None,
                "sig_text":  None,
            })

    if not chain:
        chain = [{"role": "Manager", "status": "Approved", "date": "",
                  "name": "", "sig_bytes": None, "sig_text": None}]

    cert_data = {
        "request_id":    rid,
        "full_name":     emp.get("Full_Name", ec),
        "emp_code":      ec,
        "department":    emp.get("Department", ""),
        "leave_type":    lt,
        "start_date":    row[3]  if len(row) > 3  else "",
        "end_date":      row[4]  if len(row) > 4  else "",
        "working_days":  row[5]  if len(row) > 5  else "",
        "reason":        row[8]  if len(row) > 8  else "",
        "submitted_at":  row[21] if len(row) > 21 else "",
        "final_status":  "Approved",
        "approval_chain": chain,
    }

    pdf_bytes = generate_leave_pdf(cert_data)
    lt_label  = lt.lower().replace("_", "-")
    start_cl  = (row[3] if len(row) > 3 else "").replace("/", "-")
    filename  = f"{ec}-{lt_label}-{rid}-{start_cl}.pdf"
    return pdf_bytes, filename


# ── Memo_Log regeneration ─────────────────────────────────────────────────────

def _regen_memo_row(row: list, emp_db: dict):
    """Return (pdf_bytes, filename) for a Memo_Log row, or (None, None)."""
    from memo_handler import generate_memo_pdf

    memo_id = row[0].strip()
    ec      = row[2].strip()
    emp     = emp_db.get(ec, {})

    body_text = row[8] if len(row) > 8 else ""
    language  = row[5] if len(row) > 5 else "EN"
    body_ru, body_en = "", ""
    if "[RU]:" in body_text and "[EN]:" in body_text:
        parts   = body_text.split("\n\n[EN]:")
        body_ru = parts[0].replace("[RU]: ", "").strip()
        body_en = parts[1].strip() if len(parts) > 1 else ""
    elif language == "RU":
        body_ru = body_text
    else:
        body_en = body_text

    memo_data = {
        "memo_id":         memo_id,
        "sz_number":       row[9]  if len(row) > 9  else memo_id,
        "date":            row[1][:10] if len(row) > 1 else "",
        "emp_code":        ec,
        "emp_name":        emp.get("Full_Name", ec),
        "job_title":       emp.get("Job_Title", ""),
        "job_title_ru":    emp.get("Job_Title", ""),
        "department":      emp.get("Department", ""),
        "language":        language,
        "topic":           row[6]  if len(row) > 6  else "",
        "topic_category":  row[7]  if len(row) > 7  else "",
        "body_ru":         body_ru,
        "body_en":         body_en,
        "director_name":   "",
        "submitter_name":  emp.get("Full_Name", ec),
        "submitter_date":  row[1][:10] if len(row) > 1 else "",
        "hr_staff_name":   "",
        "hr_staff_date":   row[13] if len(row) > 13 else "",
        "hr_manager_name": "",
        "hr_manager_date": row[16] if len(row) > 16 else "",
        "director_date":   "",
        "final_status":    "Director_Approved",
    }

    pdf_bytes = generate_memo_pdf(memo_data, {})
    sz_num    = memo_data["sz_number"].replace("/", "-").replace(" ", "_")
    filename  = f"{sz_num}_APPROVED.pdf"
    return pdf_bytes, filename


# ── Command handler ───────────────────────────────────────────────────────────

async def regenerate_pdfs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /regenerate_pdfs — Bot_Manager only.

    For every approved Leave/Memo row that has no Drive link:
      1. Generate the PDF
      2. Upload to Drive
      3. Save the link back to the sheet
    """
    tid = str(update.effective_user.id)
    if _get_role(tid) != "Bot_Manager":
        await update.message.reply_text("⛔ Bot_Manager only.")
        return

    status_msg = await update.message.reply_text(
        "🔄 Scanning Leave_Log and Memo_Log for missing Drive links…"
    )

    emp_db = _emp_db()
    leave_done = leave_skip = leave_fail = 0
    memo_done  = memo_skip  = memo_fail  = 0

    # ── Leave_Log ─────────────────────────────────────────────────────────────
    try:
        ws_leave   = get_sheet(TAB_LEAVE_LOG)
        leave_rows = ws_leave.get_all_values()

        for rn, row in enumerate(leave_rows, start=1):
            if rn == 1:
                continue          # header
            if len(row) < 16:
                continue
            final  = row[15].strip()                          # col 16
            link   = row[20].strip() if len(row) > 20 else "" # col 21
            if final != "Approved" or link:
                leave_skip += 1
                continue

            try:
                pdf_bytes, filename = _regen_leave_row(row, emp_db)
                url = upload_to_drive(pdf_bytes, filename, "leave_approvals")
                if url:
                    ws_leave.update_cell(rn, 21, url)
                    leave_done += 1
                else:
                    leave_fail += 1
            except Exception as e:
                print(f"[regen] Leave row {rn} ({row[0]}): {e}")
                leave_fail += 1

            await asyncio.sleep(0.3)   # gentle rate-limiting

    except Exception as e:
        print(f"[regen] Leave_Log scan error: {e}")

    # Update progress
    try:
        await status_msg.edit_text(
            f"✅ Leave_Log done — {leave_done} uploaded, {leave_fail} failed\n"
            f"🔄 Scanning Memo_Log…"
        )
    except Exception:
        pass

    # ── Memo_Log ──────────────────────────────────────────────────────────────
    try:
        ws_memo   = get_sheet(TAB_MEMO_LOG)
        memo_rows = ws_memo.get_all_values()

        for rn, row in enumerate(memo_rows, start=1):
            if rn == 1:
                continue
            if len(row) < 21:
                continue
            final = row[20].strip()                           # col 21 = Final_Status
            link  = row[23].strip() if len(row) > 23 else "" # col 24 = Drive_Link
            if final != "Director_Approved" or link:
                memo_skip += 1
                continue

            try:
                pdf_bytes, filename = _regen_memo_row(row, emp_db)
                url = upload_to_drive(pdf_bytes, filename, "memo_approved")
                if url:
                    ws_memo.update_cell(rn, 24, url)
                    memo_done += 1
                else:
                    memo_fail += 1
            except Exception as e:
                print(f"[regen] Memo row {rn} ({row[0]}): {e}")
                memo_fail += 1

            await asyncio.sleep(0.3)

    except Exception as e:
        print(f"[regen] Memo_Log scan error: {e}")

    # ── Final report ──────────────────────────────────────────────────────────
    total = leave_done + memo_done
    try:
        await status_msg.edit_text(
            f"✅ Regeneration complete!\n\n"
            f"📋 Leave approvals:  {leave_done} uploaded,  {leave_fail} failed\n"
            f"📝 Memos:            {memo_done} uploaded,  {memo_fail} failed\n"
            f"─────────────────────\n"
            f"Total uploaded: {total}"
        )
    except Exception:
        await update.message.reply_text(
            f"✅ Done — {total} PDFs uploaded to Drive."
        )


def get_regen_handler():
    return CommandHandler("regenerate_pdfs", regenerate_pdfs_cmd)
