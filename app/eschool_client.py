"""Everything that knows about the eSchool website lives in this file.

If the real site's filters or HTML differ from the defaults below, only
SUPPORTED_FILTERS, build_params() and SELECTORS need to change.
Run `python inspect_site.py` to list the real form fields.
"""
import re
from typing import Optional
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from .schemas import School, SearchCriteria

BASE_URL = "https://eschool.ug/find-schools/search"
USER_AGENT = "eschool-assistant/0.1 (take-home assessment prototype)"

# Public GET filters confirmed in the live search form. Some of these use
# array-style query keys even though this prototype sends one requested value.
SUPPORTED_FILTERS = {
    "location", "county", "min_fees", "max_fees", "gender", "boarding",
    "level", "admitting_now", "school_name", "curriculum", "facility", "affiliation",
}

# Support the synthetic fixtures and the current public listing-card markup.
SELECTORS = {
    "results_container": (
        "#results, .results, [data-results], "
        ".row.row-cols-1.row-cols-sm-2.row-cols-lg-3"
    ),
    "card": ".school-card, article.card",
    "name": ".school-name, h3 a",
    "gender": ".school-gender",
    "boarding": ".school-boarding",
    "fees": ".school-fees",
    "level": ".school-level, .card-body .badge",
    "rating": ".school-rating, .card-body .text-warning",
    "location": ".school-location, .text-truncate",
    "admission": ".school-admission, .card-img-top .text-success",
}


class EschoolError(Exception):
    """The search request failed or the response was not understood."""


def build_params(c: SearchCriteria) -> dict:
    params = {
        "location": (c.location or "").upper(),
        "county": (c.county or "").upper(),
        "min_fees": "" if c.min_fees is None else c.min_fees,
        "max_fees": "" if c.max_fees is None else c.max_fees,
        "gender": c.gender or "",
    }
    if c.school_name:
        params["q"] = c.school_name
    if c.level:
        params["levels[]"] = c.level
    if c.boarding:
        params["accomadation"] = {
            "boarding": "Boarding",
            "day": "Day",
            "both": "Day & Boarding",
        }[c.boarding]
    if c.admitting_now is not None:
        params["admission_status"] = "open" if c.admitting_now else "closed"
    if c.curriculum:
        params["curriculums[]"] = c.curriculum
    if c.facility:
        params["facilities[]"] = c.facility
    if c.affiliation:
        params["religions[]"] = c.affiliation
    return params


def build_url(c: SearchCriteria) -> str:
    return f"{BASE_URL}?{urlencode(build_params(c))}"


def not_filterable(c: SearchCriteria) -> list[str]:
    """Specified criteria the site search cannot apply."""
    return sorted(k for k in c.specified() if k not in SUPPORTED_FILTERS)


def _text(node, selector: str) -> Optional[str]:
    el = node.select_one(selector)
    if not el:
        return None
    value = el.get_text(" ", strip=True)
    return value or None


def _fees(raw: Optional[str]) -> Optional[int]:
    """'UGX 900,000 per term' -> 900000. Returns None if no number is present."""
    if not raw:
        return None
    match = re.search(r"\d[\d,\.]*", raw)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group(0).split(".")[0])
    return int(digits) if digits else None


def parse_results(html: str) -> list[School]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(SELECTORS["card"])
    if not cards:
        # An empty-but-valid results page still has the container.
        # No container at all means the page structure is not what we expect.
        if soup.select_one(SELECTORS["results_container"]) is None:
            raise EschoolError("Unexpected response format: results section not found")
        return []

    schools: list[School] = []
    for card in cards:
        name = _text(card, SELECTORS["name"])
        if not name:
            continue  # skip malformed cards rather than inventing a name
        link = card.select_one("a[href]")
        href = link["href"] if link else None
        if href and href.startswith("/"):
            href = "https://eschool.ug" + href
        schools.append(
            School(
                name=name,
                url=href,
                location=_text(card, SELECTORS["location"]),
                level=_text(card, SELECTORS["level"]),
                gender=_text(card, SELECTORS["gender"]),
                boarding=_text(card, SELECTORS["boarding"]),
                fees=_fees(_text(card, SELECTORS["fees"])),
                admission_status=_text(card, SELECTORS["admission"]),
                rating=_text(card, SELECTORS["rating"]),
                text=card.get_text(" ", strip=True),
            )
        )
    return schools


def search(
    criteria: SearchCriteria, http: Optional[httpx.Client] = None
) -> tuple[str, list[School]]:
    """Run the search on eSchool. Returns (url_used, schools)."""
    url = build_url(criteria)
    owns_client = http is None
    http = http or httpx.Client(timeout=15, follow_redirects=True)
    try:
        response = http.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EschoolError(f"eSchool request failed: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    try:
        return url, parse_results(response.text)
    except EschoolError:
        raise
    except Exception as exc:
        raise EschoolError(f"Could not parse eSchool response: {exc}") from exc
