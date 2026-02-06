from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from primer_ops.client_repo import ensure_client_repo, sanitize_folder_name
from primer_ops.primer import resolve_lead_input_path, resolve_output_dir


def _set_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def test_sanitize_folder_name() -> None:
    assert sanitize_folder_name('Acme<>:"/\\|?*  Corp') == "Acme Corp"
    assert sanitize_folder_name("Foo . ") == "Foo"
    assert sanitize_folder_name("Bar...") == "Bar"
    assert sanitize_folder_name("  Mega   Corp  ") == "Mega Corp"


def test_ensure_client_repo_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        repo = ensure_client_repo(base_dir, "Acme<>:\"/\\|?*  Corp")
        assert repo["repo_root"].exists()
        assert repo["dossier_dir"].exists()
        assert repo["latest_dir"].exists()
        assert repo["runs_dir"].exists()
        assert repo["lead_input_path"].parent == repo["dossier_dir"]


def test_lead_input_resolution_independent_from_output_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        lead_path = tmp_path / "lead_input.json"
        lead_path.write_text(json.dumps({"company_name": "Acme"}), encoding="utf-8")

        original = os.environ.get("LEAD_INPUT_PATH")
        try:
            _set_env("LEAD_INPUT_PATH", None)
            assert resolve_lead_input_path(None) == Path("lead_input.json")

            _set_env("LEAD_INPUT_PATH", str(lead_path))
            assert resolve_lead_input_path(None) == lead_path

            override_path = tmp_path / "override" / "lead.json"
            assert resolve_lead_input_path(str(override_path)) == override_path

            override_output = tmp_path / "output_override"
            lead = {"company_name": "Acme"}
            assert resolve_output_dir(str(override_output), lead) == override_output
            assert resolve_lead_input_path(None) == lead_path
        finally:
            _set_env("LEAD_INPUT_PATH", original)


def main() -> None:
    test_sanitize_folder_name()
    test_ensure_client_repo_paths()
    test_lead_input_resolution_independent_from_output_dir()
    print("OK")


if __name__ == "__main__":
    main()
