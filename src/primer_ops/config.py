from __future__ import annotations

import os
from pathlib import Path

OUTPUT_BASE_DIR_ENV = "OUTPUT_BASE_DIR"
LEAD_INPUT_PATH_ENV = "LEAD_INPUT_PATH"
INCLUDE_HEADINGS_ENV = "INCLUDE_HEADINGS"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_DEEP_RESEARCH_MODEL_ENV = "OPENAI_DEEP_RESEARCH_MODEL"

_DEFAULT_BASE_MODEL = "gpt-5.2"
_DEFAULT_DEEP_MODEL = "o4-mini-deep-research"


def _get_env_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return Path(value)


def get_output_base_dir() -> Path | None:
    return _get_env_path(OUTPUT_BASE_DIR_ENV)


def get_lead_input_path() -> Path | None:
    return _get_env_path(LEAD_INPUT_PATH_ENV)


def get_base_model() -> str:
    return os.getenv(OPENAI_MODEL_ENV, "").strip() or _DEFAULT_BASE_MODEL


def get_deep_model() -> str:
    return os.getenv(OPENAI_DEEP_RESEARCH_MODEL_ENV, "").strip() or _DEFAULT_DEEP_MODEL


def get_include_headings(default: bool = False) -> bool:
    value = os.getenv(INCLUDE_HEADINGS_ENV, "").strip()
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}
