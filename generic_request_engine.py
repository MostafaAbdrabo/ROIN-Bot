"""
ROIN WORLD FZE -- Generic Request Engine
==========================================
ONE engine that handles ALL standard request types.
Each request type is a config dict (see request_configs.py).

Covers the full lifecycle per REQUEST_FLOW_RULES.md:
  Submission -> Approval chain -> Assignment -> Completion -> PDF at every stage

Usage in bot.py:
    from generic_request_engine import build_all_request_handlers
    for h in build_all_request_handlers(): app.add_handler(h)
"""

import io, secrets
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ConversationHandler, CallbackQueryHandler,
                           MessageHandler, filters)
from config import get_sheet
from drive_utils import upload_to_drive

# ---------------------------------------------------------------------------
# Back-button helpers
# ---------------------------------------------------------------------------
def _bm():
    return InlineKeyboardButton("↩️ Main Menu", callback_data="back_to_menu")


# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------
def _get_emp_by_tid(tid):
    """Return dict with code, name, dept, role, mgr or None."""
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if r[1].strip() == str(tid):
                ec = r[0].strip()
                role = r[3].strip() if len(r) > 3 else "Employee"
                for j, e in enumerate(get_sheet("Employee_DB").get_all_values()):
                    if j == 0:
                        continue
                    if e[0].strip() == ec:
                        return {
                            "code": ec,
                            "name": e[1].strip() if len(e) > 1 else ec,
                            "dept": e[6].strip() if len(e) > 6 else "",
                            "title": e[7].strip() if len(e) > 7 else "",
                            "role": role,
                            "mgr": e[17].strip() if len(e) > 17 else "",
                        }
                return {"code": ec, "name": ec, "dept": "", "title": "", "role": role, "mgr": ""}
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
            if i == 0:
                continue
            if r[0].strip() == str(ec) and r[1].strip():
                return r[1].strip()
    except Exception:
        pass
    return None


def _users_by_role(role):
    out = []
    try:
        for i, r in enumerate(get_sheet("User_Registry").get_all_values()):
            if i == 0:
                continue
            if len(r) > 3 and r[3].strip() == role and r[1].strip():
                out.append((r[0].strip(), r[1].strip()))
    except Exception:
        pass
    return out


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _gen_id(tab_name, col_idx, prefix):
    """Generate next ID: PREFIX-YYYY-NNNN."""
    try:
        ids = get_sheet(tab_name).col_values(col_idx)
    except Exception:
        ids = []
    yr = datetime.now().strftime("%Y")
    px = f"{prefix}-{yr}-"
    mx = 0
    for v in ids:
        if str(v).startswith(px):
            try:
                mx = max(mx, int(str(v).split("-")[-1]))
            except Exception:
                pass
    return f"{px}{mx + 1:04d}"


def _find_row(tab_name, req_id):
    """Return (row_num_1based, row_values) or (None, None)."""
    try:
        rows = get_sheet(tab_name).get_all_values()
        for i, r in enumerate(rows):
            if i == 0:
                continue
            if r[0].strip() == str(req_id):
                return i + 1, r
    except Exception:
        pass
    return None, None


# ---------------------------------------------------------------------------
# Generic PDF generator
# ---------------------------------------------------------------------------
def _generate_request_pdf(cfg, row_data, headers, extra_sigs=None):
    """Generate a standard request PDF. Returns bytes."""
    from fpdf import FPDF
    import os

    def safe(text):
        if not text:
            return ""
        text = str(text)
        for old, new in {"\u2014": "-", "\u2013": "-", "\u2018": "'",
                         "\u2019": "'", "\u201c": '"', "\u201d": '"'}.items():
            text = text.replace(old, new)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    class ReqPDF(FPDF):
        def header(self):
            logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company_logo.png")
            if os.path.exists(logo):
                self.image(logo, x=85, y=8, w=25)
                self.ln(28)
            else:
                self.ln(10)
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 6, "ROIN WORLD FZE EGYPT BRANCH", new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_font("Helvetica", "", 8)
            self.cell(0, 5, "Building No 1, Gamal Abdel Nasser Street - El Dabaa - Matrouh",
                      new_x="LMARGIN", new_y="NEXT", align="C")
            self.cell(0, 5, "info.egypt@roinworld.com     www.roinworld.com",
                      new_x="LMARGIN", new_y="NEXT", align="C")
            self.line(15, self.get_y() + 2, 195, self.get_y() + 2)
            self.ln(5)
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 7, safe(cfg["name"].upper()), new_x="LMARGIN", new_y="NEXT", align="C")
            self.ln(3)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.cell(0, 4, "Generated by ROIN WORLD FZE HR System", align="C",
                      new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 4, f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C")

    pdf = ReqPDF()
    pdf.add_page()

    # Request info section
    pdf.set_fill_color(220, 230, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "  REQUEST DETAILS", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(1)

    # Show all fields from row_data matched with headers
    pdf.set_font("Helvetica", "", 9)
    for idx, hdr in enumerate(headers):
        if not hdr:
            continue
        val = row_data[idx] if idx < len(row_data) else ""
        if not val:
            continue
        # Skip long text fields in summary — show them separately
        if len(str(val)) > 200:
            continue
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(55, 6, f"  {safe(hdr)}:")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, safe(str(val)[:80]), new_x="LMARGIN", new_y="NEXT")

    # Approval chain section
    chain = cfg.get("chain", [])
    if chain:
        pdf.ln(3)
        pdf.set_fill_color(220, 230, 245)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "  APPROVAL CHAIN", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(1)

        for stage in chain:
            role_label = stage.get("label", stage["role"])
            # Find the status column in headers
            status_key = f"{stage['role']}_Status"
            date_key = f"{stage['role']}_Date"
            status = ""
            date = ""
            for hi, h in enumerate(headers):
                if h == status_key and hi < len(row_data):
                    status = row_data[hi]
                elif h == date_key and hi < len(row_data):
                    date = row_data[hi]

            icon = "[APPROVED]" if status == "Approved" else (
                   "[REJECTED]" if status == "Rejected" else (
                   "[N/A]" if status == "NA" else "[PENDING]"))
            pdf.set_font("Helvetica", "B", 9)
            line = f"  {icon}  {safe(role_label)}"
            if date:
                line += f"  --  {safe(date)}"
            pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

            # Add signature if approved and extra_sigs provided
            if status == "Approved" and extra_sigs:
                sig = extra_sigs.get(stage["role"])
                if sig:
                    sb, st = sig
                    if sb:
                        try:
                            img_io = io.BytesIO(sb)
                            pdf.image(img_io, x=pdf.l_margin + 10, y=pdf.get_y(), w=40, h=16)
                            pdf.ln(18)
                        except Exception:
                            if st:
                                pdf.set_font("Helvetica", "I", 8)
                                pdf.cell(0, 5, safe(f"  {st}"), new_x="LMARGIN", new_y="NEXT")
                    elif st:
                        pdf.set_font("Helvetica", "I", 8)
                        pdf.cell(0, 5, safe(f"  {st}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    # Final status
    final_status = ""
    for hi, h in enumerate(headers):
        if h == "Final_Status" and hi < len(row_data):
            final_status = row_data[hi]
    pdf.ln(3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    code = secrets.token_hex(4).upper()
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 5, f"Verification: {cfg['prefix']}-{code}  |  Status: {safe(final_status or 'Pending')}",
             align="C")

    out = io.BytesIO()
    pdf.output(out)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Build headers for a request type
# ---------------------------------------------------------------------------
def _build_headers(cfg):
    """Build the full list of column headers for a request type's sheet tab."""
    headers = ["Request_ID", "Date", "Emp_Code", "Full_Name", "Department"]
    for f in cfg.get("fields", []):
        headers.append(f["key"])
    for stage in cfg.get("chain", []):
        headers.append(f"{stage['role']}_Status")
        headers.append(f"{stage['role']}_Date")
    headers.extend(["Final_Status", "Rejection_Reason", "PDF_Drive_Link", "Created_At"])
    if cfg.get("assignment"):
        headers.extend(["Assigned_To", "Assigned_By", "Assigned_At", "Execution_Status",
                         "Completed_By", "Completed_At"])
        for f in cfg.get("completion_fields", []):
            headers.append(f["key"])
    return headers


# ---------------------------------------------------------------------------
# Ensure sheet tab exists
# ---------------------------------------------------------------------------
def _ensure_tab(cfg):
    """Create the sheet tab if it doesn't exist."""
    tab = cfg["tab"]
    try:
        get_sheet(tab)
    except Exception:
        try:
            from config import WORKBOOK
            headers = _build_headers(cfg)
            ws = WORKBOOK.add_worksheet(tab, rows=1000, cols=len(headers))
            ws.update('A1', [headers])
        except Exception as e:
            print(f"[generic_req] Could not create tab {tab}: {e}")


# ---------------------------------------------------------------------------
# CORE: Build handlers for ONE request type
# ---------------------------------------------------------------------------
def _build_handlers_for_type(cfg):
    """Return (conversation_handlers, static_handlers) for one request type."""
    prefix = cfg["prefix"].lower()
    tab = cfg["tab"]
    fields = cfg.get("fields", [])
    chain = cfg.get("chain", [])
    assignment = cfg.get("assignment")
    completion_fields = cfg.get("completion_fields", [])
    base_state = cfg.get("_base_state", 6000)
    ST_FORM = base_state
    ST_CONFIRM = base_state + 1
    ST_REJECT = base_state + 2
    ST_ASSIGN = base_state + 3
    ST_COMPLETE = base_state + 4
    ST_COMP_CONFIRM = base_state + 5
    back_cb = cfg.get("back_callback", "back_to_menu")

    def _back():
        return InlineKeyboardButton("↩️ Back", callback_data=back_cb)

    # ── SUBMISSION ─────────────────────────────────────────────────────
    async def start_request(update, context):
        q = update.callback_query
        await q.answer()
        emp = _get_emp_by_tid(q.from_user.id)
        if not emp:
            await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return ConversationHandler.END
        # Check role permission
        can_submit = cfg.get("can_submit", [])
        if can_submit and emp["role"] not in can_submit and emp["role"] != "Bot_Manager":
            await q.edit_message_text("You don't have permission to submit this request.",
                                      reply_markup=InlineKeyboardMarkup([[_back(), _bm()]]))
            return ConversationHandler.END

        context.user_data[f"{prefix}_emp"] = emp
        context.user_data[f"{prefix}_field_idx"] = 0
        context.user_data[f"{prefix}_data"] = {}
        return await _ask_next_field(q, context)

    async def _ask_next_field(q_or_msg, context, edit=True):
        idx = context.user_data.get(f"{prefix}_field_idx", 0)
        if idx >= len(fields):
            return await _show_summary(q_or_msg, context, edit)

        f = fields[idx]
        label = f.get("label", f["key"])
        ftype = f.get("type", "text")

        if ftype == "choice":
            options = f.get("options", [])
            kb = [[InlineKeyboardButton(opt, callback_data=f"gr_{prefix}_opt_{idx}_{i}")]
                  for i, opt in enumerate(options)]
            kb.append([_back(), _bm()])
            text = f"Step {idx + 1}/{len(fields)}: {label}"
            if edit and hasattr(q_or_msg, 'edit_message_text'):
                await q_or_msg.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
            else:
                target = q_or_msg if hasattr(q_or_msg, 'reply_text') else q_or_msg.message
                if hasattr(target, 'reply_text'):
                    await target.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            hint = ""
            if ftype == "number":
                hint = " (enter a number)"
            elif ftype == "date":
                hint = " (DD/MM/YYYY)"
            elif ftype == "photo":
                hint = " (send a photo)"
            text = f"Step {idx + 1}/{len(fields)}: {label}{hint}"
            kb = InlineKeyboardMarkup([[_back(), _bm()]])
            if edit and hasattr(q_or_msg, 'edit_message_text'):
                await q_or_msg.edit_message_text(text, reply_markup=kb)
            else:
                target = q_or_msg if hasattr(q_or_msg, 'reply_text') else q_or_msg
                await target.reply_text(text, reply_markup=kb)
        return ST_FORM

    async def handle_choice(update, context):
        q = update.callback_query
        await q.answer()
        # Parse: gr_{prefix}_opt_{field_idx}_{option_idx}
        parts = q.data.split("_")
        fidx = int(parts[-2])
        oidx = int(parts[-1])
        f = fields[fidx]
        val = f["options"][oidx]
        context.user_data[f"{prefix}_data"][f["key"]] = val
        context.user_data[f"{prefix}_field_idx"] = fidx + 1
        return await _ask_next_field(q, context)

    async def handle_text_input(update, context):
        idx = context.user_data.get(f"{prefix}_field_idx", 0)
        if idx >= len(fields):
            return ST_FORM
        f = fields[idx]
        ftype = f.get("type", "text")
        val = update.message.text.strip()

        # Validate
        if ftype == "number":
            try:
                float(val)
            except ValueError:
                await update.message.reply_text("Please enter a valid number:")
                return ST_FORM
        elif ftype == "date":
            if val.lower() not in ("today", "tomorrow"):
                try:
                    datetime.strptime(val, "%d/%m/%Y")
                except ValueError:
                    await update.message.reply_text("Please use DD/MM/YYYY format:")
                    return ST_FORM
            if val.lower() == "today":
                val = datetime.now().strftime("%d/%m/%Y")
            elif val.lower() == "tomorrow":
                from datetime import timedelta
                val = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")

        context.user_data[f"{prefix}_data"][f["key"]] = val
        context.user_data[f"{prefix}_field_idx"] = idx + 1
        return await _ask_next_field(update.message, context, edit=False)

    async def handle_photo_input(update, context):
        idx = context.user_data.get(f"{prefix}_field_idx", 0)
        if idx >= len(fields):
            return ST_FORM
        f = fields[idx]
        if update.message.photo:
            fid = update.message.photo[-1].file_id
        elif update.message.document:
            fid = update.message.document.file_id
        else:
            await update.message.reply_text("Please send a photo or file:")
            return ST_FORM
        context.user_data[f"{prefix}_data"][f["key"]] = fid
        context.user_data[f"{prefix}_field_idx"] = idx + 1
        return await _ask_next_field(update.message, context, edit=False)

    async def _show_summary(q_or_msg, context, edit=True):
        emp = context.user_data.get(f"{prefix}_emp", {})
        data = context.user_data.get(f"{prefix}_data", {})
        lines = [f"{cfg['name']}\n{'_' * 28}"]
        lines.append(f"By: {emp.get('name', '')} ({emp.get('code', '')})")
        for f in fields:
            val = data.get(f["key"], "")
            label = f.get("label", f["key"])
            display = str(val)[:60]
            lines.append(f"{label}: {display}")
        text = "\n".join(lines)
        kb = [
            [InlineKeyboardButton("Submit", callback_data=f"gr_{prefix}_cfm_yes"),
             InlineKeyboardButton("Cancel", callback_data=f"gr_{prefix}_cfm_no")],
            [_bm()],
        ]
        if edit and hasattr(q_or_msg, 'edit_message_text'):
            await q_or_msg.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q_or_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        return ST_CONFIRM

    async def handle_confirm(update, context):
        q = update.callback_query
        await q.answer()
        if q.data.endswith("_no"):
            await q.edit_message_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return ConversationHandler.END

        emp = context.user_data.get(f"{prefix}_emp", {})
        data = context.user_data.get(f"{prefix}_data", {})
        now_str = _now()

        _ensure_tab(cfg)
        try:
            req_id = _gen_id(tab, 1, cfg["prefix"])
        except Exception as e:
            await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return ConversationHandler.END

        headers = _build_headers(cfg)
        row = [""] * len(headers)
        # Standard columns
        for hi, h in enumerate(headers):
            if h == "Request_ID":
                row[hi] = req_id
            elif h == "Date":
                row[hi] = now_str
            elif h == "Emp_Code":
                row[hi] = emp.get("code", "")
            elif h == "Full_Name":
                row[hi] = ""  # VLOOKUP
            elif h == "Department":
                row[hi] = ""  # VLOOKUP
            elif h == "Created_At":
                row[hi] = now_str
            elif h == "Final_Status":
                row[hi] = "Pending"
            elif h == "Execution_Status":
                row[hi] = ""
            elif h.endswith("_Status"):
                row[hi] = "Pending"
            elif h in data:
                row[hi] = data[h]

        try:
            get_sheet(tab).append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            await q.edit_message_text(f"Error saving: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return ConversationHandler.END

        # Generate PDF
        pdf_url = None
        try:
            rn, rd = _find_row(tab, req_id)
            if rn:
                pdf_bytes = _generate_request_pdf(cfg, rd, headers)
                pdf_url = upload_to_drive(pdf_bytes, f"{req_id}_submitted.pdf", cfg.get("pending_folder", "in_process"))
                if pdf_url:
                    # Find PDF_Drive_Link column
                    for hi, h in enumerate(headers):
                        if h == "PDF_Drive_Link":
                            get_sheet(tab).update_cell(rn, hi + 1, pdf_url)
                            break
        except Exception as e:
            print(f"[generic_req] PDF error for {req_id}: {e}")

        kb = [[_bm()]]
        if pdf_url:
            kb.insert(0, [InlineKeyboardButton("View PDF", url=pdf_url)])
        await q.edit_message_text(
            f"Submitted!\nID: {req_id}\n{now_str}",
            reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    async def cancel_handler(update, context):
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        elif update.message:
            await update.message.reply_text("Cancelled.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
        return ConversationHandler.END

    # ── APPROVAL ───────────────────────────────────────────────────────
    async def show_pending(update, context):
        """Show pending requests for the current approval stage."""
        q = update.callback_query
        await q.answer()
        emp = _get_emp_by_tid(q.from_user.id)
        if not emp:
            await q.edit_message_text("Not registered.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return

        _ensure_tab(cfg)
        try:
            rows = get_sheet(tab).get_all_values()
        except Exception as e:
            await q.edit_message_text(f"Error: {e}", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return

        headers = rows[0] if rows else []
        pending = []
        for i, r in enumerate(rows):
            if i == 0:
                continue
            # Find which stage this request is at
            for si, stage in enumerate(chain):
                status_col = f"{stage['role']}_Status"
                try:
                    col_idx = headers.index(status_col)
                except ValueError:
                    continue
                if col_idx < len(r) and r[col_idx].strip() == "Pending":
                    # Check if previous stages are approved
                    all_prev_ok = True
                    for prev_si in range(si):
                        prev_status_col = f"{chain[prev_si]['role']}_Status"
                        try:
                            prev_col = headers.index(prev_status_col)
                            if prev_col < len(r) and r[prev_col].strip() != "Approved":
                                all_prev_ok = False
                        except ValueError:
                            pass
                    if all_prev_ok:
                        # Check role match (or Bot_Manager)
                        if emp["role"] == "Bot_Manager" or emp["role"] == stage["role"]:
                            pending.append((i + 1, r, si))
                    break

        if not pending:
            await q.edit_message_text(f"No pending {cfg['name']} requests.",
                                      reply_markup=InlineKeyboardMarkup([[_back(), _bm()]]))
            return

        kb = []
        for rn, r, si in pending[-15:]:
            rid = r[0]
            label = f"{rid} | Stage: {chain[si].get('label', chain[si]['role'])}"
            kb.append([InlineKeyboardButton(label, callback_data=f"gr_{prefix}_view_{rid}")])
        kb.append([_back(), _bm()])
        await q.edit_message_text(f"Pending {cfg['name']} ({len(pending)}):",
                                  reply_markup=InlineKeyboardMarkup(kb))

    async def view_request(update, context):
        q = update.callback_query
        await q.answer()
        req_id = q.data.replace(f"gr_{prefix}_view_", "")
        rn, rd = _find_row(tab, req_id)
        if not rd:
            await q.edit_message_text("Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return

        _ensure_tab(cfg)
        headers = get_sheet(tab).row_values(1)

        lines = [f"{cfg['name']} -- {req_id}\n{'_' * 28}"]
        for hi, h in enumerate(headers):
            if hi < len(rd) and rd[hi] and h not in ("PDF_Drive_Link", "Created_At"):
                val = rd[hi][:60] if len(rd[hi]) > 60 else rd[hi]
                lines.append(f"{h}: {val}")

        kb = []
        # PDF link
        for hi, h in enumerate(headers):
            if h == "PDF_Drive_Link" and hi < len(rd) and rd[hi]:
                kb.append([InlineKeyboardButton("View PDF", url=rd[hi])])
        # Approve / Reject
        kb.append([
            InlineKeyboardButton("Approve", callback_data=f"gr_{prefix}_apr_{req_id}"),
            InlineKeyboardButton("Reject", callback_data=f"gr_{prefix}_rej_{req_id}"),
        ])
        kb.append([_back(), _bm()])
        await q.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))

    async def handle_approve(update, context):
        q = update.callback_query
        await q.answer()
        req_id = q.data.replace(f"gr_{prefix}_apr_", "")
        emp = _get_emp_by_tid(q.from_user.id)
        rn, rd = _find_row(tab, req_id)
        if not rn:
            await q.edit_message_text("Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return

        _ensure_tab(cfg)
        headers = get_sheet(tab).row_values(1)
        now_str = _now()

        # Find current stage and approve
        approved_stage = None
        for si, stage in enumerate(chain):
            status_col = f"{stage['role']}_Status"
            date_col = f"{stage['role']}_Date"
            try:
                si_col = headers.index(status_col)
                di_col = headers.index(date_col)
            except ValueError:
                continue
            if si_col < len(rd) and rd[si_col].strip() == "Pending":
                # Check previous stages
                all_prev_ok = True
                for prev_si in range(si):
                    prev_sc = f"{chain[prev_si]['role']}_Status"
                    try:
                        pc = headers.index(prev_sc)
                        if pc < len(rd) and rd[pc].strip() != "Approved":
                            all_prev_ok = False
                    except ValueError:
                        pass
                if all_prev_ok:
                    get_sheet(tab).update_cell(rn, si_col + 1, "Approved")
                    get_sheet(tab).update_cell(rn, di_col + 1, now_str)
                    approved_stage = si
                break

        if approved_stage is None:
            await q.edit_message_text("Nothing to approve.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return

        # Check if all stages done -> Final_Status = Approved
        is_final = (approved_stage == len(chain) - 1)
        if is_final:
            try:
                fs_col = headers.index("Final_Status")
                get_sheet(tab).update_cell(rn, fs_col + 1, "Approved")
            except ValueError:
                pass

        # Regenerate PDF with updated data
        pdf_url = None
        try:
            _, rd_fresh = _find_row(tab, req_id)
            if rd_fresh:
                # Stale-proof: override current stage
                for hi, h in enumerate(headers):
                    if h == f"{chain[approved_stage]['role']}_Status":
                        rd_fresh[hi] = "Approved"
                    elif h == f"{chain[approved_stage]['role']}_Date":
                        rd_fresh[hi] = now_str
                    elif h == "Final_Status" and is_final:
                        rd_fresh[hi] = "Approved"

                sigs = {}
                try:
                    from signature_handler import get_sig_bytes
                    sb, st = await get_sig_bytes(context.bot, emp["code"] if emp else "")
                    sigs[chain[approved_stage]["role"]] = (sb, st)
                except Exception:
                    pass

                pdf_bytes = _generate_request_pdf(cfg, rd_fresh, headers, extra_sigs=sigs)
                folder = cfg.get("pending_folder", "in_process") if not is_final else cfg.get("approved_folder", cfg.get("pending_folder", "in_process"))
                if is_final:
                    from drive_utils import upload_and_archive
                    sub_ec = rd_fresh[headers.index("Emp_Code")].strip() if "Emp_Code" in headers else ""
                    pdf_url = upload_and_archive(pdf_bytes, f"{req_id}_stage{approved_stage}.pdf", folder,
                                                 emp_code=sub_ec)
                else:
                    pdf_url = upload_to_drive(pdf_bytes, f"{req_id}_stage{approved_stage}.pdf", folder)
                if pdf_url:
                    try:
                        pl_col = headers.index("PDF_Drive_Link")
                        get_sheet(tab).update_cell(rn, pl_col + 1, pdf_url)
                    except ValueError:
                        pass
        except Exception as e:
            print(f"[generic_req] approve PDF error: {e}")

        # Notify submitter
        try:
            ec_col = headers.index("Emp_Code")
            req_ec = rd[ec_col]
            req_tid = _get_tid_by_code(req_ec)
            if req_tid:
                stage_label = chain[approved_stage].get("label", chain[approved_stage]["role"])
                notif_kb = []
                if pdf_url:
                    notif_kb.append([InlineKeyboardButton("View PDF", url=pdf_url)])
                status_msg = "APPROVED" if is_final else f"approved by {stage_label}"
                await context.bot.send_message(
                    chat_id=req_tid,
                    text=f"Your {cfg['name']} {req_id} -- {status_msg}.",
                    reply_markup=InlineKeyboardMarkup(notif_kb) if notif_kb else None)
        except Exception:
            pass

        kb = [[_back(), _bm()]]
        if pdf_url:
            kb.insert(0, [InlineKeyboardButton("View PDF", url=pdf_url)])
        status_text = "FULLY APPROVED" if is_final else f"Stage {approved_stage + 1} approved"
        await q.edit_message_text(f"{req_id} -- {status_text} ({now_str})",
                                  reply_markup=InlineKeyboardMarkup(kb))

    async def start_reject(update, context):
        q = update.callback_query
        await q.answer()
        req_id = q.data.replace(f"gr_{prefix}_rej_", "")
        context.user_data[f"{prefix}_rej_id"] = req_id
        await q.edit_message_text(f"Rejecting {req_id}.\n\nType the rejection reason:")
        return ST_REJECT

    async def handle_reject_reason(update, context):
        reason = update.message.text.strip()
        if len(reason) < 3:
            await update.message.reply_text("Reason too short. Try again:")
            return ST_REJECT
        req_id = context.user_data.get(f"{prefix}_rej_id", "")
        rn, rd = _find_row(tab, req_id)
        if not rn:
            await update.message.reply_text("Not found.", reply_markup=InlineKeyboardMarkup([[_bm()]]))
            return ConversationHandler.END

        headers = get_sheet(tab).row_values(1)
        now_str = _now()

        # Find current pending stage and reject
        for si, stage in enumerate(chain):
            status_col = f"{stage['role']}_Status"
            date_col = f"{stage['role']}_Date"
            try:
                si_col = headers.index(status_col)
                di_col = headers.index(date_col)
            except ValueError:
                continue
            if si_col < len(rd) and rd[si_col].strip() == "Pending":
                get_sheet(tab).update_cell(rn, si_col + 1, "Rejected")
                get_sheet(tab).update_cell(rn, di_col + 1, now_str)
                break

        try:
            fs_col = headers.index("Final_Status")
            get_sheet(tab).update_cell(rn, fs_col + 1, "Rejected")
        except ValueError:
            pass
        try:
            rr_col = headers.index("Rejection_Reason")
            get_sheet(tab).update_cell(rn, rr_col + 1, reason)
        except ValueError:
            pass

        # Notify submitter
        try:
            ec_col = headers.index("Emp_Code")
            req_ec = rd[ec_col]
            req_tid = _get_tid_by_code(req_ec)
            if req_tid:
                await context.bot.send_message(
                    chat_id=req_tid,
                    text=f"Your {cfg['name']} {req_id} was REJECTED.\nReason: {reason}")
        except Exception:
            pass

        await update.message.reply_text(f"{req_id} rejected.",
                                        reply_markup=InlineKeyboardMarkup([[_back(), _bm()]]))
        return ConversationHandler.END

    # ── Build handler objects ──────────────────────────────────────────
    conv_handlers = []
    static_handlers = []

    # Submission conversation
    submit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_request, pattern=f"^gr_{prefix}_start$")],
        states={
            ST_FORM: [
                CallbackQueryHandler(handle_choice, pattern=f"^gr_{prefix}_opt_"),
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_photo_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input),
            ],
            ST_CONFIRM: [CallbackQueryHandler(handle_confirm, pattern=f"^gr_{prefix}_cfm_")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_handler, pattern="^back_to_menu$"),
        ],
        allow_reentry=True,
    )
    conv_handlers.append(submit_conv)

    # Rejection conversation
    reject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_reject, pattern=f"^gr_{prefix}_rej_")],
        states={
            ST_REJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reject_reason)],
        },
        fallbacks=[],
        allow_reentry=True,
    )
    conv_handlers.append(reject_conv)

    # Static handlers
    static_handlers.append(
        CallbackQueryHandler(show_pending, pattern=f"^gr_{prefix}_pending$"))
    static_handlers.append(
        CallbackQueryHandler(view_request, pattern=f"^gr_{prefix}_view_"))
    static_handlers.append(
        CallbackQueryHandler(handle_approve, pattern=f"^gr_{prefix}_apr_"))

    return conv_handlers, static_handlers, cfg


# ---------------------------------------------------------------------------
# PUBLIC: Build ALL request handlers from configs
# ---------------------------------------------------------------------------
def build_all_request_handlers():
    """Import configs, build handlers for each, return flat list."""
    from request_configs import ALL_REQUEST_TYPES

    all_conv = []
    all_static = []
    registry = []  # for menu building

    for i, cfg in enumerate(ALL_REQUEST_TYPES):
        cfg["_base_state"] = 6000 + (i * 10)
        convs, statics, c = _build_handlers_for_type(cfg)
        all_conv.extend(convs)
        all_static.extend(statics)
        registry.append(c)

    return all_conv + all_static


# Export for menu building
def get_request_registry():
    from request_configs import ALL_REQUEST_TYPES
    return ALL_REQUEST_TYPES
