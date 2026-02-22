from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from primer_ops.client_repo import ensure_client_repo, sanitize_folder_name
from primer_ops.primer import (
    _safe_write_text_multi,
    resolve_lead_input_path,
    resolve_output_dir,
    resolve_output_targets,
)


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


def test_client_repo_output_targets_and_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp) / "base"
        base_dir.mkdir(parents=True, exist_ok=True)

        original_base = os.environ.get("OUTPUT_BASE_DIR")
        original_dir = os.environ.get("OUTPUT_DIR")
        try:
            _set_env("OUTPUT_BASE_DIR", str(base_dir))
            _set_env("OUTPUT_DIR", None)

            lead = {"company_name": "Acme Corp"}
            targets = resolve_output_targets(None, lead)

            repo_root = targets["repo_root"]
            latest_dir = targets["latest_dir"]
            run_dir = targets["run_dir"]

            assert repo_root == base_dir / "Acme Corp"
            assert (repo_root / "_dossier").exists()
            assert latest_dir.exists()
            assert run_dir.exists()

            primer_content = "OK"
            _safe_write_text_multi(
                [latest_dir / "primer.md", run_dir / "primer.md"], primer_content
            )
            assert (latest_dir / "primer.md").read_text(encoding="utf-8") == primer_content
            assert (run_dir / "primer.md").read_text(encoding="utf-8") == primer_content
        finally:
            _set_env("OUTPUT_BASE_DIR", original_base)
            _set_env("OUTPUT_DIR", original_dir)


def test_output_dir_override_skips_client_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp) / "base"
        base_dir.mkdir(parents=True, exist_ok=True)
        override_dir = Path(tmp) / "override"

        original_base = os.environ.get("OUTPUT_BASE_DIR")
        original_dir = os.environ.get("OUTPUT_DIR")
        try:
            _set_env("OUTPUT_BASE_DIR", str(base_dir))
            _set_env("OUTPUT_DIR", None)

            lead = {"company_name": "Acme Corp"}
            targets = resolve_output_targets(str(override_dir), lead)

            assert targets["repo_root"] is None
            assert override_dir.exists()
            assert not (base_dir / "Acme Corp").exists()

            primer_content = "OK"
            _safe_write_text_multi(
                [targets["output_dir"] / "primer.md"], primer_content
            )
            assert (override_dir / "primer.md").read_text(encoding="utf-8") == primer_content
            assert not (base_dir / "Acme Corp" / "latest" / "primer.md").exists()
        finally:
            _set_env("OUTPUT_BASE_DIR", original_base)
            _set_env("OUTPUT_DIR", original_dir)


def test_lead_override_skips_client_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp) / "base"
        base_dir.mkdir(parents=True, exist_ok=True)
        override_dir = Path(tmp) / "lead_override"

        original_base = os.environ.get("OUTPUT_BASE_DIR")
        original_dir = os.environ.get("OUTPUT_DIR")
        try:
            _set_env("OUTPUT_BASE_DIR", str(base_dir))
            _set_env("OUTPUT_DIR", None)

            lead = {"company_name": "Acme Corp", "client_output_dir": str(override_dir)}
            targets = resolve_output_targets(None, lead)

            assert targets["repo_root"] is None
            assert override_dir.exists()
            assert not (base_dir / "Acme Corp").exists()
        finally:
            _set_env("OUTPUT_BASE_DIR", original_base)
            _set_env("OUTPUT_DIR", original_dir)


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
    test_client_repo_output_targets_and_writes()
    test_output_dir_override_skips_client_repo()
    test_lead_override_skips_client_repo()
    test_lead_input_resolution_independent_from_output_dir()
    print("OK")


if __name__ == "__main__":
    main()
