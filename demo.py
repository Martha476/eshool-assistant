"""Generate DEMO.md with the three required example requests.

Live mode (needs OPENAI_API_KEY, hits the real eSchool site):
    python demo.py

Offline mode (no key, no network). The AI step is replaced by hard-coded
criteria and eSchool by synthetic fixture pages, so ONLY the pipeline
(validation, URL building, parsing, matching, error handling) is exercised:
    python demo.py --offline
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from app.cli import render
from app.eschool_client import parse_results
from app.schemas import SearchCriteria
from app.service import handle

EXAMPLES = [
    (
        "1. Clearly specified request",
        "I'm looking for a girls' boarding school in Kampala, preferably around Central "
        "Division, charging no more than UGX 1 million per term and currently admitting "
        "Senior One students.",
        SearchCriteria(
            location="Kampala", county="Kampala Central Division", gender="girls",
            boarding="boarding", max_fees=1_000_000, admitting_now=True,
            admission_class="Senior One",
        ),
    ),
    (
        "2. Missing / ambiguous information",
        "I want a good school for my child.",
        SearchCriteria(
            clarification_question="Which area are you looking in, which class is your child "
            "joining, and what is your budget per term?"
        ),
    ),
    (
        "3. Request with no suitable results",
        "A mixed school in Kampala charging no more than UGX 50,000 per term.",
        SearchCriteria(location="Kampala", gender="mixed", max_fees=50_000),
    ),
]

FIXTURES = Path(__file__).parent / "tests" / "fixtures"


def offline_search(c: SearchCriteria):
    """Stand-in for the live site: filters the synthetic fixture like a server would."""
    from app.eschool_client import build_url

    schools = parse_results((FIXTURES / "results_page.html").read_text(encoding="utf-8"))
    if c.max_fees is not None:
        schools = [s for s in schools if s.fees is None or s.fees <= c.max_fees]
    if c.gender:
        schools = [s for s in schools if s.gender and c.gender in s.gender.lower()]
    return build_url(c), schools


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    offline = "--offline" in sys.argv
    out = ["# Demonstration", ""]
    if offline:
        out += [
            "> **Offline run.** The AI step is replaced by hard-coded criteria and eSchool by "
            "synthetic fixture pages, so this shows the pipeline behaviour only. "
            "Run `python demo.py` with an API key for live output.",
            "",
        ]
    for title, request, fixed in EXAMPLES:
        kwargs = {"interpret_fn": (lambda t, f=fixed: f), "search_fn": offline_search} if offline else {}
        response = handle(request, **kwargs)
        out += [f"## {title}", "", f"**Request:** {request}", "", "```", render(response), "```", ""]
    Path("DEMO.md").write_text("\n".join(out), encoding="utf-8")
    print("Wrote DEMO.md")


if __name__ == "__main__":
    main()