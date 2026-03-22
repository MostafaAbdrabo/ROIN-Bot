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
