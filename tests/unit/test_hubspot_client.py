from __future__ import annotations

from primer_ops.hubspot_client import fetch_lead_from_hubspot


def test_fetch_lead_from_hubspot_uses_associated_notes_from_selected_deal(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "primer_ops.hubspot_client.search_companies",
        lambda query: [
            {
                "id": "company-1",
                "properties": {
                    "name": "Acme Corp",
                    "website": "https://acme.example",
                    "country": "Italy",
                    "industry": "food",
                    "annualrevenue": "125500000",
                },
            }
        ],
    )
    monkeypatch.setattr(
        "primer_ops.hubspot_client.get_associated_contacts",
        lambda company_id: [
            {
                "id": "contact-1",
                "properties": {
                    "firstname": "Jane",
                    "lastname": "Doe",
                    "jobtitle": "CEO",
                },
            }
        ],
    )

    def fake_get_associated_deal_ids(object_type: str, object_id: str) -> list[str]:
        mapping = {
            ("companies", "company-1"): ["deal-1", "deal-2"],
            ("contacts", "contact-1"): ["deal-2"],
        }
        return mapping.get((object_type, object_id), [])

    def fake_get_deal(deal_id: str) -> dict | None:
        deals = {
            "deal-1": {
                "id": "deal-1",
                "properties": {
                    "dealname": "Old deal",
                    "hs_lastmodifieddate": "2024-01-01T00:00:00Z",
                },
            },
            "deal-2": {
                "id": "deal-2",
                "properties": {
                    "dealname": "Current deal",
                    "hs_lastmodifieddate": "2025-01-01T00:00:00Z",
                },
            },
        }
        return deals.get(deal_id)

    def fake_get_associated_note_ids(deal_id: str) -> list[str]:
        mapping = {
            "deal-1": ["note-1"],
            "deal-2": ["note-2", "note-3"],
        }
        return mapping.get(deal_id, [])

    def fake_get_note(note_id: str) -> dict | None:
        notes = {
            "note-1": {
                "id": "note-1",
                "properties": {
                    "hs_note_body": "Old fallback note",
                    "hs_timestamp": "2024-01-01T00:00:00Z",
                },
            },
            "note-2": {
                "id": "note-2",
                "properties": {
                    "hs_note_body": "Latest deal note",
                    "hs_timestamp": "2025-02-01T00:00:00Z",
                },
            },
            "note-3": {
                "id": "note-3",
                "properties": {
                    "hs_note_body": "Earlier deal note",
                    "hs_timestamp": "2025-01-15T00:00:00Z",
                },
            },
        }
        return notes.get(note_id)

    monkeypatch.setattr(
        "primer_ops.hubspot_client.get_associated_deal_ids",
        fake_get_associated_deal_ids,
    )
    monkeypatch.setattr("primer_ops.hubspot_client.get_deal", fake_get_deal)
    monkeypatch.setattr(
        "primer_ops.hubspot_client.get_associated_note_ids",
        fake_get_associated_note_ids,
    )
    monkeypatch.setattr("primer_ops.hubspot_client.get_note", fake_get_note)

    lead = fetch_lead_from_hubspot("Acme")

    assert lead.company_name == "Acme Corp"
    assert lead.primary_contact_name == "Jane Doe"
    assert lead.primary_contact_role == "CEO"
    assert lead.revenue_mln == 125.5
    assert lead.deal_notes == "Latest deal note\n\nEarlier deal note"
