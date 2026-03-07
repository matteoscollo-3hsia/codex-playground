from __future__ import annotations

import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.hubapi.com"
_COMPANY_PROPS = ["name", "website", "domain", "country", "industry", "annualrevenue"]
_CONTACT_PROPS = ["firstname", "lastname", "jobtitle"]
_DEAL_PROPS = ["dealname", "hs_lastmodifieddate"]
_NOTE_PROPS = ["hs_note_body", "hs_timestamp"]
_MAX_RETRIES = 4
_RETRY_BASE_SLEEP = 1.0  # seconds; doubles on each attempt (1s, 2s, 4s, 8s)


def _headers() -> dict[str, str]:
    token = os.environ.get("HUBSPOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "HUBSPOT_TOKEN environment variable not set. "
            "Create a HubSpot Private App and set its token in .env."
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """Execute an httpx request with exponential backoff on 429 rate-limit responses."""
    for attempt in range(_MAX_RETRIES + 1):
        response = httpx.request(method, url, **kwargs)
        if response.status_code != 429:
            return response
        retry_after = int(response.headers.get("Retry-After", _RETRY_BASE_SLEEP * (2**attempt)))
        logger.warning(
            "HubSpot rate limit hit (attempt %d/%d). Retrying in %ds.",
            attempt + 1,
            _MAX_RETRIES,
            retry_after,
        )
        time.sleep(retry_after)
    return response  # return last response to let caller handle it


def search_companies(query: str) -> list[dict]:
    """Search HubSpot companies by name (up to 10 results)."""
    url = f"{_BASE}/crm/v3/objects/companies/search"
    body = {"query": query, "properties": _COMPANY_PROPS, "limit": 10}
    response = _request_with_retry("POST", url, json=body, headers=_headers(), timeout=15)
    response.raise_for_status()
    return response.json().get("results", [])


def get_associated_contacts(company_id: str) -> list[dict]:
    """Fetch contacts associated with a company (up to 3)."""
    url = f"{_BASE}/crm/v4/objects/companies/{company_id}/associations/contacts"
    response = _request_with_retry("GET", url, headers=_headers(), timeout=15)
    if response.status_code == 404:
        return []
    response.raise_for_status()

    contacts: list[dict] = []
    for assoc in response.json().get("results", [])[:3]:
        contact_id = assoc["toObjectId"]
        c_resp = _request_with_retry(
            "GET",
            f"{_BASE}/crm/v3/objects/contacts/{contact_id}",
            params={"properties": ",".join(_CONTACT_PROPS)},
            headers=_headers(),
            timeout=15,
        )
        if c_resp.status_code == 200:
            contacts.append(c_resp.json())
    return contacts


def get_associated_deal_ids(object_type: str, object_id: str) -> list[str]:
    """Fetch deal IDs associated with a CRM object."""
    url = f"{_BASE}/crm/v4/objects/{object_type}/{object_id}/associations/deals"
    response = _request_with_retry("GET", url, headers=_headers(), timeout=15)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    deal_ids: list[str] = []
    for assoc in response.json().get("results", []):
        deal_id = assoc.get("toObjectId")
        if deal_id is not None:
            deal_ids.append(str(deal_id))
    return deal_ids


def get_deal(deal_id: str) -> dict | None:
    """Fetch a single deal with the properties needed for lead enrichment."""
    response = _request_with_retry(
        "GET",
        f"{_BASE}/crm/v3/objects/deals/{deal_id}",
        params={"properties": ",".join(_DEAL_PROPS)},
        headers=_headers(),
        timeout=15,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def get_associated_note_ids(deal_id: str) -> list[str]:
    """Fetch note IDs associated with a deal."""
    url = f"{_BASE}/crm/v4/objects/deals/{deal_id}/associations/notes"
    response = _request_with_retry("GET", url, headers=_headers(), timeout=15)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    note_ids: list[str] = []
    for assoc in response.json().get("results", []):
        note_id = assoc.get("toObjectId")
        if note_id is not None:
            note_ids.append(str(note_id))
    return note_ids


def get_note(note_id: str) -> dict | None:
    """Fetch a single HubSpot note."""
    response = _request_with_retry(
        "GET",
        f"{_BASE}/crm/v3/objects/notes/{note_id}",
        params={"properties": ",".join(_NOTE_PROPS)},
        headers=_headers(),
        timeout=15,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _parse_revenue_mln(raw: str | None) -> float:
    """Convert HubSpot annualrevenue (full number) to millions, rounded to 2dp."""
    if not raw:
        return 0.0
    try:
        return round(float(raw) / 1_000_000, 2)
    except ValueError:
        logger.warning("Could not parse annualrevenue value: %r", raw)
        return 0.0


def _primary_contact(contacts: list[dict]) -> tuple[str, str]:
    if not contacts:
        return "", ""
    props = contacts[0].get("properties", {})
    first = (props.get("firstname") or "").strip()
    last = (props.get("lastname") or "").strip()
    name = f"{first} {last}".strip()
    role = (props.get("jobtitle") or "").strip()
    return name, role


def _note_body(note: dict | None) -> str:
    if not note:
        return ""
    props = note.get("properties", {})
    return (props.get("hs_note_body") or "").strip()


def _note_sort_key(note: dict) -> tuple[str, str]:
    props = note.get("properties", {})
    timestamp = (props.get("hs_timestamp") or "").strip()
    note_id = str(note.get("id") or "")
    return timestamp, note_id


def _deal_notes_text(deal_id: str | None) -> str:
    if not deal_id:
        return ""

    notes: list[dict] = []
    seen_ids: set[str] = set()
    for note_id in get_associated_note_ids(deal_id):
        if note_id in seen_ids:
            continue
        seen_ids.add(note_id)
        note = get_note(note_id)
        if note is None or not _note_body(note):
            continue
        notes.append(note)

    if not notes:
        return ""

    sorted_notes = sorted(notes, key=_note_sort_key, reverse=True)
    return "\n\n".join(_note_body(note) for note in sorted_notes)


def _deal_sort_key(deal: dict) -> tuple[bool, str, str]:
    props = deal.get("properties", {})
    modified_at = (props.get("hs_lastmodifieddate") or "").strip()
    deal_name = (props.get("dealname") or "").strip()
    return bool(modified_at), modified_at, deal_name


def _best_deal_from_ids(deal_ids: list[str]) -> dict | None:
    deals: list[dict] = []
    seen_ids: set[str] = set()
    for deal_id in deal_ids:
        if deal_id in seen_ids:
            continue
        seen_ids.add(deal_id)
        deal = get_deal(deal_id)
        if deal is not None:
            deals.append(deal)
    if not deals:
        return None
    return max(deals, key=_deal_sort_key)


def _pick_associated_deal(company_id: str, contacts: list[dict]) -> tuple[dict | None, str]:
    company_deal_ids = get_associated_deal_ids("companies", company_id)
    if not company_deal_ids:
        return None, ""

    contact_ids = [str(contact.get("id")) for contact in contacts if contact.get("id")]
    prioritized_groups: list[list[str]] = []

    if contact_ids:
        primary_contact_deal_ids = set(
            get_associated_deal_ids("contacts", contact_ids[0])
        )
        primary_matches = [
            deal_id for deal_id in company_deal_ids if deal_id in primary_contact_deal_ids
        ]
        if primary_matches:
            prioritized_groups.append(primary_matches)

        other_contact_deal_ids: set[str] = set()
        for contact_id in contact_ids[1:]:
            other_contact_deal_ids.update(
                get_associated_deal_ids("contacts", contact_id)
            )
        other_matches = [
            deal_id
            for deal_id in company_deal_ids
            if deal_id in other_contact_deal_ids and deal_id not in primary_matches
        ]
        if other_matches:
            prioritized_groups.append(other_matches)

    prioritized_groups.append(company_deal_ids)

    best_fallback: tuple[dict, str] | None = None
    for deal_ids in prioritized_groups:
        deal = _best_deal_from_ids(deal_ids)
        if deal is None:
            continue
        notes_text = _deal_notes_text(str(deal.get("id") or ""))
        if best_fallback is None:
            best_fallback = deal, notes_text
        if notes_text:
            return deal, notes_text

    if best_fallback is None:
        return None, ""
    return best_fallback


def _pick_company(companies: list[dict], query: str) -> dict:
    """If multiple results, print a menu and let the user choose."""
    if len(companies) == 1:
        return companies[0]

    print(f"\nFound {len(companies)} companies matching '{query}':\n")
    for i, c in enumerate(companies, 1):
        props = c.get("properties", {})
        website = props.get("website") or props.get("domain") or ""
        country = props.get("country") or ""
        print(f"  [{i}] {props.get('name', '?')}  |  {website}  |  {country}")
    print()

    while True:
        raw = input(f"Select company [1-{len(companies)}]: ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(companies):
                return companies[idx]
        except ValueError:
            pass
        print("  -> Invalid selection.")


def fetch_lead_from_hubspot(query: str) -> "LeadInput":  # noqa: F821 — avoid circular import
    """Search HubSpot for *query* and return a populated LeadInput."""
    from primer_ops.lead_input import LeadInput  # local import to avoid circular dep

    logger.info("Searching HubSpot for: %s", query)
    companies = search_companies(query)
    if not companies:
        raise SystemExit(f"No HubSpot companies found matching '{query}'.")

    company = _pick_company(companies, query)
    company_id = company["id"]

    logger.info("Fetching contacts for company ID %s", company_id)
    contacts = get_associated_contacts(company_id)

    props = company.get("properties", {})
    website = (props.get("website") or props.get("domain") or "").strip()
    industry = (props.get("industry") or "").strip().title()
    contact_name, contact_role = _primary_contact(contacts)
    _, deal_notes = _pick_associated_deal(company_id, contacts)

    return LeadInput(
        company_name=(props.get("name") or "").strip(),
        company_website=website,
        hq_country=(props.get("country") or "").strip(),
        industry=industry,
        revenue_mln=_parse_revenue_mln(props.get("annualrevenue")),
        primary_contact_name=contact_name,
        primary_contact_role=contact_role,
        deal_notes=deal_notes,
    )
