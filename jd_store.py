"""
ROIN WORLD FZE — JD Storage Layer
===================================
All Google Sheets CRUD for JD_Drafts tab + Google Drive upload.
"""

import json, re, os
from datetime import datetime
from config import get_sheet, WORKBOOK
import gspread

TAB_JD = "JD_Drafts"

# Column numbers (1-based)
C_ID      = 1;  C_EMP     = 2;  C_EMPNAME = 3;  C_CREATOR  = 4
C_STATUS  = 5;  C_TITLE   = 6;  C_SUMMARY = 7;  C_TASKS    = 8
C_QUALS   = 9;  C_WRKCON  = 10; C_HREDITS = 11; C_HREDITOR = 12
C_DIRNOTE = 13; C_REJRSN  = 14; C_CREATED = 15; C_UPDATED  = 16
C_PDFLINK = 17

HEADERS = [
    "JD_ID", "Emp_Code", "Emp_Name", "Creator_Code", "Status",
    "Job_Title", "Summary", "Tasks_JSON", "Qualifications", "Working_Conditions",
    "HR_Edits_JSON", "HR_Editor_Code", "Director_Notes", "Rejection_Reason",
    "Created_At", "Updated_At", "PDF_Drive_Link",
]

# Status constants
S_PENDING_HR  = "Pending_HR"
S_PENDING_MGR = "Pending_Manager"   # HR edited → manager must review
S_PENDING_DIR = "Pending_Director"
S_APPROVED    = "Approved"
S_REJECTED    = "Rejected"


def _ws():
    try:
        return get_sheet(TAB_JD)
    except gspread.exceptions.WorksheetNotFound:
        ws = WORKBOOK.add_worksheet(title=TAB_JD, rows=500, cols=20)
        ws.append_row(HEADERS)
        return ws


def _gen_id():
    return f"JD-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _row_to_dict(row: list) -> dict:
    def g(i): return row[i] if len(row) > i else ""
    try:    tasks = json.loads(g(C_TASKS - 1)) if g(C_TASKS - 1) else []
    except: tasks = []
    try:    hr_edits = json.loads(g(C_HREDITS - 1)) if g(C_HREDITS - 1) else {}
    except: hr_edits = {}
    return {
        "jd_id":              g(C_ID - 1),
        "emp_code":           g(C_EMP - 1),
        "emp_name":           g(C_EMPNAME - 1),
        "creator_code":       g(C_CREATOR - 1),
        "status":             g(C_STATUS - 1),
        "job_title":          g(C_TITLE - 1),
        "summary":            g(C_SUMMARY - 1),
        "tasks":              tasks,
        "qualifications":     g(C_QUALS - 1),
        "working_conditions": g(C_WRKCON - 1),
        "hr_edits":           hr_edits,
        "hr_editor":          g(C_HREDITOR - 1),
        "director_notes":     g(C_DIRNOTE - 1),
        "rejection_reason":   g(C_REJRSN - 1),
        "created_at":         g(C_CREATED - 1),
        "updated_at":         g(C_UPDATED - 1),
        "pdf_link":           g(C_PDFLINK - 1),
    }


def _find(ws, jd_id: str):
    for i, row in enumerate(ws.get_all_values()):
        if i == 0: continue
        if row[0].strip() == jd_id:
            return i + 1, row
    return None, None


# ── Public API ─────────────────────────────────────────────────────────────────

def create_jd(data: dict) -> str:
    """Insert new JD draft. Returns JD_ID."""
    ws = _ws()
    jd_id = _gen_id()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    ws.append_row([
        jd_id,
        data.get("emp_code", ""),
        data.get("emp_name", ""),
        data.get("creator_code", ""),
        S_PENDING_HR,
        data.get("job_title", ""),
        data.get("summary", ""),
        json.dumps(data.get("tasks", []), ensure_ascii=False),
        data.get("qualifications", ""),
        data.get("working_conditions", ""),
        "", "", "", "",          # hr_edits, hr_editor, director_notes, rejection_reason
        now, now, "",            # created_at, updated_at, pdf_link
    ])
    return jd_id


def get_jd(jd_id: str) -> dict | None:
    ws = _ws()
    _, row = _find(ws, jd_id)
    return _row_to_dict(row) if row else None


def update_jd(jd_id: str, status: str = None, **fields):
    """Update status and/or specific fields."""
    col_map = {
        "job_title": C_TITLE,   "summary": C_SUMMARY,     "tasks": C_TASKS,
        "qualifications": C_QUALS, "working_conditions": C_WRKCON,
        "hr_edits": C_HREDITS,  "hr_editor": C_HREDITOR,
        "director_notes": C_DIRNOTE, "rejection_reason": C_REJRSN,
        "pdf_link": C_PDFLINK,
    }
    ws = _ws()
    ri, _ = _find(ws, jd_id)
    if not ri: return
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    if status:
        ws.update_cell(ri, C_STATUS, status)
    ws.update_cell(ri, C_UPDATED, now)
    for key, val in fields.items():
        col = col_map.get(key)
        if col:
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            ws.update_cell(ri, col, val)


def get_jds_by_status(*statuses) -> list:
    ws = _ws()
    return [_row_to_dict(row)
            for i, row in enumerate(ws.get_all_values())
            if i > 0 and row[0].strip() and row[C_STATUS - 1].strip() in statuses]


def get_jds_by_creator(creator_code: str, *statuses) -> list:
    ws = _ws()
    result = []
    for i, row in enumerate(ws.get_all_values()):
        if i == 0: continue
        if not row[0].strip(): continue
        if row[C_CREATOR - 1].strip() != str(creator_code): continue
        if statuses and row[C_STATUS - 1].strip() not in statuses: continue
        result.append(_row_to_dict(row))
    return result


def merge_jd(jd: dict) -> dict:
    """Return final merged data: HR edits override manager's originals."""
    hr = jd.get("hr_edits", {})
    return {
        "emp_code":           jd["emp_code"],
        "full_name":          jd["emp_name"],
        "job_title":          hr.get("job_title") or jd["job_title"],
        "department":         jd.get("department", ""),
        "manager_name":       jd.get("manager_name", ""),
        "location":           jd.get("location", "El Dabaa Nuclear Power Plant Site, Matrouh"),
        "employment_type":    jd.get("employment_type", "Full-Time"),
        "grade":              jd.get("grade", ""),
        "summary":            hr.get("summary") or jd["summary"],
        "tasks":              hr.get("tasks") or jd["tasks"],
        "qualifications":     hr.get("qualifications") or jd["qualifications"],
        "working_conditions": hr.get("working_conditions") or jd["working_conditions"],
        "created_by":         jd.get("created_by", "HR Department"),
        "created_at":         jd.get("created_at", ""),
    }


# ── Google Drive upload (via Apps Script — same as leave requests) ─────────────

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec"


def _folder_id(link: str) -> str | None:
    if "/folders/" in str(link):
        return str(link).split("/folders/")[-1].split("?")[0].split("/")[0]
    return None


def upload_to_drive(folder_link: str, pdf_bytes: bytes, filename: str) -> str:
    """Upload PDF via Apps Script middleman. Returns file URL. Raises on failure."""
    import base64, urllib.request, json as _json, urllib.request as ur
    fid = _folder_id(folder_link)
    if not fid:
        raise ValueError(f"Cannot extract folder ID from Drive link: {folder_link!r}")
    payload = _json.dumps({
        "folder_id": fid,
        "filename": filename,
        "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
    }).encode("utf-8")
    req = ur.Request(APPS_SCRIPT_URL, data=payload,
                     headers={"Content-Type": "application/json"}, method="POST")
    opener = ur.build_opener(ur.HTTPRedirectHandler)
    response = opener.open(req, timeout=30)
    result = _json.loads(response.read().decode("utf-8"))
    if result.get("success"):
        return result.get("file_url", "")
    raise RuntimeError(f"Apps Script error: {result.get('error', result)}")
