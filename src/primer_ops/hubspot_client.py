from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.hubapi.com"
_COMPANY_PROPS = ["name", "website", "domain", "country", "industry", "annualrevenue"]
_CONTACT_PROPS = ["firstname", "lastname", "jobtitle"]


def _headers() -> dict[str, str]:
    token = os.environ.get("HUBSPOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "HUBSPOT_TOKEN environment variable not set. "
            "Create a HubSpot Private App and set its token in .env."
        )
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def search_companies(query: str) -> list[dict]:
    """Search HubSpot companies by name (up to 10 results)."""
    url = f"{_BASE}/crm/v3/objects/companies/search"
    body = {"query": query, "properties": _COMPANY_PROPS, "limit": 10}
    response = httpx.post(url, json=body, headers=_headers(), timeout=15)
    response.raise_for_status()
    return response.json().get("results", [])


def get_associated_contacts(company_id: str) -> list[dict]:
    """Fetch contacts associated with a company (up to 3)."""
    url = f"{_BASE}/crm/v4/objects/companies/{company_id}/associations/contacts"
    response = httpx.get(url, headers=_headers(), timeout=15)
    if response.status_code == 404:
        return []
    response.raise_for_status()

    contacts: list[dict] = []
    for assoc in response.json().get("results", [])[:3]:
        contact_id = assoc["toObjectId"]
        c_resp = httpx.get(
            f"{_BASE}/crm/v3/objects/contacts/{contact_id}",
            params={"properties": ",".join(_CONTACT_PROPS)},
            headers=_headers(),
            timeout=15,
        )
        if c_resp.status_code == 200:
            contacts.append(c_resp.json())
    return contacts


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

    return LeadInput(
        company_name=(props.get("name") or "").strip(),
        company_website=website,
        hq_country=(props.get("country") or "").strip(),
        industry=industry,
        revenue_mln=_parse_revenue_mln(props.get("annualrevenue")),
        primary_contact_name=contact_name,
        primary_contact_role=contact_role,
    )
