from __future__ import annotations

from pathlib import Path
import re

_INVALID_FOLDER_CHARS_RE = re.compile(r"[<>:\"/\\\\|?*]")
_MAX_FOLDER_NAME_LEN = 80


def sanitize_folder_name(name: str) -> str:
    if name is None:
        return ""
    cleaned = _INVALID_FOLDER_CHARS_RE.sub("", str(name))
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.rstrip(" .")
    if _MAX_FOLDER_NAME_LEN and len(cleaned) > _MAX_FOLDER_NAME_LEN:
        cleaned = cleaned[:_MAX_FOLDER_NAME_LEN].rstrip(" .")
    return cleaned


def ensure_client_repo(base_dir: Path, company_name: str) -> dict[str, Path]:
    folder_name = sanitize_folder_name(company_name) or "unknown_company"
    repo_root = base_dir / folder_name
    dossier_dir = repo_root / "_dossier"
    lead_input_path = dossier_dir / "lead_input.json"
    latest_dir = repo_root / "latest"
    runs_dir = repo_root / "runs"

    repo_root.mkdir(parents=True, exist_ok=True)
    dossier_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    return {
        "repo_root": repo_root,
        "dossier_dir": dossier_dir,
        "lead_input_path": lead_input_path,
        "latest_dir": latest_dir,
        "runs_dir": runs_dir,
    }
