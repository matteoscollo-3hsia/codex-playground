from __future__ import annotations

import json

from primer_ops.lead_input import LeadInput, run_create_input_from_hubspot


def test_run_create_input_from_hubspot_skips_completion_when_no_fields_missing(
    tmp_path, monkeypatch
) -> None:
    lead = LeadInput(
        company_name="Acme Corp",
        company_website="https://acme.example",
        hq_country="Italy",
        industry="Food",
        revenue_mln=125.0,
        primary_contact_name="Jane Doe",
        primary_contact_role="CEO",
        deal_notes="Deal note from HubSpot",
    )

    monkeypatch.setattr(
        "primer_ops.hubspot_client.fetch_lead_from_hubspot",
        lambda query: lead,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": (_ for _ in ()).throw(AssertionError("input should not be called")),
    )

    out_path = tmp_path / "lead_input.json"
    run_create_input_from_hubspot("Acme", lead_output=str(out_path))

    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved == lead.model_dump()


def test_run_create_input_from_hubspot_completes_missing_fields(
    tmp_path, monkeypatch
) -> None:
    lead = LeadInput(
        company_name="Acme Corp",
        company_website="",
        hq_country="",
        industry="Food",
        revenue_mln=0.0,
        primary_contact_name="",
        primary_contact_role="",
        deal_notes="",
    )
    answers = iter(
        [
            "y",
            "https://acme.example",
            "Italy",
            "125.5",
            "Jane Doe",
            "CEO",
            "Deal note from HubSpot",
        ]
    )

    monkeypatch.setattr(
        "primer_ops.hubspot_client.fetch_lead_from_hubspot",
        lambda query: lead,
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    out_path = tmp_path / "lead_input.json"
    run_create_input_from_hubspot("Acme", lead_output=str(out_path))

    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["company_name"] == "Acme Corp"
    assert saved["company_website"] == "https://acme.example"
    assert saved["hq_country"] == "Italy"
    assert saved["industry"] == "Food"
    assert saved["revenue_mln"] == 125.5
    assert saved["primary_contact_name"] == "Jane Doe"
    assert saved["primary_contact_role"] == "CEO"
    assert saved["deal_notes"] == "Deal note from HubSpot"
