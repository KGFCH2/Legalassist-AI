import os
import re
import uuid
from pathlib import Path
from typing import Tuple
from config import Config

ATTACHMENTS_DIR = Path(Config.ATTACHMENTS_DIR)

# Ensure directory exists
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)


def safe_filename(name: str) -> str:
    name = name or "report"
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = name.strip(" .")
    return name[:180] if len(name) > 180 else name


def save_attachment(file_bytes: bytes, original_filename: str) -> Tuple[str, int]:
    """
    Save attachment bytes to the attachments directory.
    Returns (stored_path, size_bytes).
    """
    ext = Path(original_filename).suffix or ""
    if Config.ATTACHMENTS_RANDOMIZE_FILENAMES:
        stored_name = f"{uuid.uuid4().hex}{ext}"
    else:
        stored_name = safe_filename(original_filename)

    stored_path = ATTACHMENTS_DIR / stored_name

    # Write file
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    size = stored_path.stat().st_size
    return str(stored_path), size


def get_attachment_path(stored_path: str) -> str:
    """Return safe path for stored attachment, rejecting traversal attempts."""
    if not stored_path:
        return ""

    resolved = Path(stored_path).resolve()
    attachments_dir = Path(ATTACHMENTS_DIR).resolve()

    if ".." in stored_path or resolved.is_relative_to(attachments_dir) is False:
        return ""

    if not resolved.exists():
        return ""

    return str(resolved)
