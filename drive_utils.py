"""
ROIN WORLD FZE — Google Drive Upload Utility
=============================================
Uploads PDF bytes to a Drive folder via Google Apps Script and returns a
browser-viewable link.

Usage:
    from drive_utils import upload_to_drive
    url = upload_to_drive(pdf_bytes, "MEMO-2026-0001.pdf", "memo_drafts")
    # url is a https://drive.google.com/... link, or None on failure.

Folder keys are defined in config.DRIVE_FOLDERS.
"""

import base64
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbxKtTNn_1TRofVi_QUGoF6aMOVJdmzs4LyMksvaIVg2j_lzadK0VJ-vrUwM0ss72FEIpA/exec"
)


def upload_to_drive(pdf_bytes: bytes, filename: str, folder_key: str) -> str | None:
    """
    Upload pdf_bytes to the Drive folder identified by folder_key.

    Args:
        pdf_bytes:  Raw PDF bytes to upload.
        filename:   Filename to use in Drive (e.g. "MEMO-2026-0001_draft.pdf").
        folder_key: Key from config.DRIVE_FOLDERS (e.g. "drafts", "approved").

    Returns:
        file URL (str) on success, or None if upload failed.
    """
    from config import DRIVE_FOLDERS
    folder_id = DRIVE_FOLDERS.get(folder_key, DRIVE_FOLDERS.get("drafts", ""))
    if not folder_id:
        logger.info("Drive folder not configured for '%s' — skipping upload of %s", folder_key, filename)
        return None
    try:
        payload = json.dumps({
            "folder_id": folder_id,
            "filename": filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
        }).encode("utf-8")
        req = urllib.request.Request(
            APPS_SCRIPT_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        response = opener.open(req, timeout=30)
        result = json.loads(response.read().decode("utf-8"))
        if result.get("success"):
            link = result.get("file_url", "")
            logger.info("Uploaded %s to Drive (%s): %s", filename, folder_key, link)
            return link if link else None
        logger.error("Drive upload error for %s: %s", filename, result.get("error"))
        return None
    except Exception as e:
        logger.error("Drive upload failed for %s: %s", filename, e)
        return None


def upload_to_drive_by_id(pdf_bytes: bytes, filename: str, folder_id: str) -> str | None:
    """Upload pdf_bytes directly to a Drive folder by its ID (not a key)."""
    if not folder_id:
        return None
    try:
        payload = json.dumps({
            "folder_id": folder_id,
            "filename": filename,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
        }).encode("utf-8")
        req = urllib.request.Request(
            APPS_SCRIPT_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        response = opener.open(req, timeout=30)
        result = json.loads(response.read().decode("utf-8"))
        if result.get("success"):
            return result.get("file_url", "") or None
        return None
    except Exception as e:
        logger.error("Drive upload (by ID) failed for %s: %s", filename, e)
        return None


def _call_apps_script(payload_dict: dict) -> dict | None:
    """Send a JSON payload to the Apps Script and return the parsed response."""
    try:
        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(
            APPS_SCRIPT_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
        response = opener.open(req, timeout=30)
        return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        logger.error("Apps Script call failed: %s", e)
        return None


def get_or_create_employee_folder(emp_code, full_name) -> str | None:
    """Return the Drive folder ID for an employee. Creates the folder if needed."""
    from config import get_sheet, EMPLOYEE_FOLDERS_PARENT
    try:
        ws = get_sheet("Employee_DB")
        headers = ws.row_values(1)
        link_col = None
        code_col = None
        for i, h in enumerate(headers):
            if h.strip() == "Drive_Folder_Link":
                link_col = i + 1
            if h.strip() == "Emp_Code":
                code_col = i + 1
        if not link_col or not code_col:
            logger.error("Employee_DB missing Drive_Folder_Link or Emp_Code column")
            return None

        all_rows = ws.get_all_values()
        target_row = None
        for idx, row in enumerate(all_rows):
            if idx == 0:
                continue
            if row[code_col - 1].strip() == str(emp_code).strip():
                target_row = idx + 1
                existing_link = row[link_col - 1].strip() if len(row) >= link_col else ""
                if existing_link:
                    import re
                    m = re.search(r'/folders/([a-zA-Z0-9_-]+)', existing_link)
                    if m:
                        return m.group(1)
                break

        if target_row is None:
            logger.error("Employee %s not found in Employee_DB", emp_code)
            return None

        folder_name = f"{emp_code}_{full_name}"
        result = _call_apps_script({
            "action": "create_folder",
            "parent_id": EMPLOYEE_FOLDERS_PARENT,
            "folder_name": folder_name,
        })
        if result and result.get("success"):
            folder_id = result.get("folder_id", "")
            folder_url = result.get("folder_url", f"https://drive.google.com/drive/folders/{folder_id}")
            ws.update_cell(target_row, link_col, folder_url)
            logger.info("Created employee folder for %s: %s", emp_code, folder_url)
            return folder_id
        logger.error("Failed to create folder for %s: %s", emp_code, result)
        return None
    except Exception as e:
        logger.error("get_or_create_employee_folder error for %s: %s", emp_code, e)
        return None


def upload_and_archive(pdf_bytes: bytes, filename: str, dept_folder_key: str,
                       emp_code: str = "", emp_name: str = "") -> str | None:
    """Upload PDF to department folder AND employee personal folder."""
    dept_url = upload_to_drive(pdf_bytes, filename, dept_folder_key)
    if emp_code:
        try:
            emp_folder_id = get_or_create_employee_folder(emp_code, emp_name)
            if emp_folder_id:
                upload_to_drive_by_id(pdf_bytes, filename, emp_folder_id)
        except Exception as e:
            logger.error("Employee archive failed for %s: %s", emp_code, e)
    return dept_url


def make_pdf_filename(doc_type: str, request_id: str, emp_code: str,
                      reference_date=None) -> str:
    """Generate standardised PDF filename: PREFIX_ID_CODE_MM-YYYY.pdf"""
    from config import FILENAME_PREFIXES
    from datetime import datetime
    prefix = FILENAME_PREFIXES.get(doc_type, doc_type.upper())
    if reference_date is None:
        reference_date = datetime.now()
    if isinstance(reference_date, str):
        parts = reference_date.split("/")
        mm = parts[1] if len(parts) >= 2 else datetime.now().strftime("%m")
        yyyy = parts[2] if len(parts) >= 3 else datetime.now().strftime("%Y")
    else:
        mm = reference_date.strftime("%m")
        yyyy = reference_date.strftime("%Y")
    return f"{prefix}_{request_id}_{emp_code}_{mm}-{yyyy}.pdf"


def download_pdf_from_drive(file_url: str) -> bytes | None:
    """Download a PDF from Drive by extracting the file ID from a URL."""
    import re, io
    patterns = [r'/file/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
    file_id = None
    for p in patterns:
        m = re.search(p, str(file_url))
        if m:
            file_id = m.group(1)
            break
    if not file_id:
        return None
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        from config import _creds
        service = build('drive', 'v3', credentials=_creds)
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        logger.error("Drive download failed for %s: %s", file_url, e)
        return None
