from __future__ import annotations

import json
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field, ValidationError

from primer_ops.client_repo import ensure_client_repo
from primer_ops.config import get_output_base_dir


class LeadInput(BaseModel):
    company_name: str = Field(min_length=1)
    company_website: str = Field(default="")
    hq_country: str = Field(default="")
    industry: str = Field(default="")
    revenue_mln: float = Field(ge=0)
    primary_contact_name: str = Field(default="")
    primary_contact_role: str = Field(default="")
    deal_notes: str = Field(default="")


_FIELD_LABELS = {
    "company_name": "Company name",
    "company_website": "Company website (optional)",
    "hq_country": "HQ country (optional)",
    "industry": "Industry (optional)",
    "revenue_mln": "Revenue in EUR (mln)",
    "primary_contact_name": "Primary contact name (optional)",
    "primary_contact_role": "Primary contact role (optional)",
    "deal_notes": "Associated deal notes (optional)",
}


def prompt_str(label: str, required: bool = False) -> str:
    while True:
        val = input(f"{label}: ").strip()
        if required and not val:
            print("  -> Required field. Please enter a value.")
            continue
        return val


_PROMPT_MAX_RETRIES = 10


def prompt_float(label: str) -> float:
    for _ in range(_PROMPT_MAX_RETRIES):
        raw = input(f"{label} (number): ").strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            print("  -> Please enter a valid number (e.g., 75 or 75.5).")
    raise SystemExit(f"Too many invalid inputs for '{label}'. Exiting.")


def prompt_float_optional(label: str, default: float) -> float:
    for _ in range(_PROMPT_MAX_RETRIES):
        raw = input(f"{label} (number, press Enter to skip): ").strip().replace(",", ".")
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print("  -> Please enter a valid number (e.g., 75 or 75.5).")
    raise SystemExit(f"Too many invalid inputs for '{label}'. Exiting.")


def prompt_yes_no(label: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    for _ in range(_PROMPT_MAX_RETRIES):
        raw = input(f"{label} {suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("  -> Please answer y or n.")
    raise SystemExit(f"Too many invalid inputs for '{label}'. Exiting.")


def _resolve_output_path(lead_output: str | None, company_name: str) -> Path:
    if lead_output:
        return Path(lead_output)
    base_dir = get_output_base_dir()
    if base_dir is not None and company_name.strip():
        repo = ensure_client_repo(base_dir, company_name)
        return repo["lead_input_path"]
    return Path("lead_input.json")


def _save_lead(lead: LeadInput, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(lead.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSaved: {out_path}\n")


def _missing_hubspot_fields(lead: LeadInput) -> list[str]:
    data = lead.model_dump()
    missing_fields: list[str] = []
    for field_name in _FIELD_LABELS:
        value = data[field_name]
        if field_name == "revenue_mln":
            # HubSpot fetch normalizes missing annualrevenue to 0.0.
            if value == 0:
                missing_fields.append(field_name)
            continue
        if isinstance(value, str) and not value.strip():
            missing_fields.append(field_name)
    return missing_fields


def _complete_missing_hubspot_fields(lead: LeadInput) -> LeadInput:
    missing_fields = _missing_hubspot_fields(lead)
    if not missing_fields:
        return lead

    print("HubSpot left some fields empty or unavailable:")
    for field_name in missing_fields:
        print(f"  - {_FIELD_LABELS[field_name]}")

    if not prompt_yes_no("Do you want to fill them now?", default=True):
        return lead

    print()
    data = lead.model_dump()
    for field_name in missing_fields:
        label = _FIELD_LABELS[field_name]
        if field_name == "company_name":
            data[field_name] = prompt_str(label, required=True)
        elif field_name == "revenue_mln":
            data[field_name] = prompt_float_optional(label, default=data[field_name])
        else:
            data[field_name] = prompt_str(label, required=False)

    return LeadInput(**data)


def run_create_input_from_hubspot(
    query: str,
    lead_output: str | None = None,
) -> None:
    from primer_ops.hubspot_client import fetch_lead_from_hubspot

    env_path = find_dotenv(usecwd=True)
    load_dotenv(env_path, override=True)

    print(f"\nFetching from HubSpot: {query}\n")
    lead = fetch_lead_from_hubspot(query)

    print("Lead data fetched from HubSpot:")
    for key, value in lead.model_dump().items():
        print(f"  {key}: {value}")

    lead = _complete_missing_hubspot_fields(lead)

    print("\nFinal lead data:")
    for key, value in lead.model_dump().items():
        print(f"  {key}: {value}")

    out_path = _resolve_output_path(lead_output, lead.company_name)
    _save_lead(lead, out_path)


def run_create_input(
    lead_output: str | None = None, company_name: str | None = None
) -> None:
    env_path = find_dotenv(usecwd=True)
    load_dotenv(env_path, override=True)

    print("\n=== Lead Input Wizard ===\n")

    data = {
        "company_name": prompt_str("Company name", required=True),
        "company_website": prompt_str("Company website (optional)", required=False),
        "hq_country": prompt_str("HQ country (optional)", required=False),
        "industry": prompt_str("Industry (optional)", required=False),
        "revenue_mln": prompt_float("Revenue in EUR (mln)"),
        "primary_contact_name": prompt_str(
            "Primary contact name (optional)", required=False
        ),
        "primary_contact_role": prompt_str(
            "Primary contact role (optional)", required=False
        ),
        "deal_notes": prompt_str("Associated deal notes (optional)", required=False),
    }

    try:
        lead = LeadInput(**data)
    except ValidationError as e:
        print("\nValidation error:\n")
        print(e)
        raise SystemExit(1)

    out_path = _resolve_output_path(lead_output, lead.company_name if not company_name else company_name)
    print(f"Lead input path: {out_path}\n")
    _save_lead(lead, out_path)
