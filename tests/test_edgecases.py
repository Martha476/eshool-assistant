"""Input-validation and robustness edge cases."""
import pytest

from app import service
from app.eschool_client import _fees, parse_results
from app.schemas import School, SearchCriteria


def never(*_a, **_k):
    raise AssertionError("must not be called")


@pytest.mark.parametrize("bad", ["", "   ", "\n\t", None])
def test_blank_input_rejected_without_calling_ai(bad):
    r = service.handle(bad, interpret_fn=never, search_fn=never)
    assert r.status == "error" and "describe" in r.message.lower()


def test_exactly_max_length_is_accepted():
    r = service.handle(
        "a" * service.MAX_REQUEST_LENGTH,
        interpret_fn=lambda t: SearchCriteria(clarification_question="Where?"),
        search_fn=never,
    )
    assert r.status == "needs_clarification"


def test_one_over_max_length_is_rejected_without_calling_ai():
    r = service.handle("a" * (service.MAX_REQUEST_LENGTH + 1), interpret_fn=never, search_fn=never)
    assert r.status == "error" and "too long" in r.message


def test_unicode_and_emoji_request_is_passed_through():
    seen = {}

    def interp(t):
        seen["t"] = t
        return SearchCriteria(location="Kampala")

    service.handle("Ssomero ery'abawala e Kampala 🏫 – ≤ 1m", interpret_fn=interp,
                   search_fn=lambda c: ("u", []))
    assert "🏫" in seen["t"]


def test_whitespace_is_trimmed_before_interpretation():
    seen = {}
    service.handle("  school in Gulu \n", interpret_fn=lambda t: seen.setdefault("t", t) and SearchCriteria(location="Gulu"),
                   search_fn=lambda c: ("u", []))
    assert seen["t"] == "school in Gulu"


def test_only_unsupported_requirements_asks_for_clarification():
    c = SearchCriteria(unsupported=["strong sports"])
    r = service.handle("a school with strong sports", interpret_fn=lambda t: c, search_fn=never)
    assert r.status == "needs_clarification"


def test_normalizer_crash_does_not_break_search():
    def broken(_):
        raise RuntimeError("bad options file")

    r = service.handle("school in Gulu", interpret_fn=lambda t: SearchCriteria(location="Gulu"),
                       search_fn=lambda c: ("u", [School(name="A")]), normalize_fn=broken)
    assert r.status == "ok"


def test_many_results_are_all_returned_with_explanations():
    schools = [School(name=f"School {i}", fees=100_000 + i) for i in range(50)]
    r = service.handle("x", interpret_fn=lambda t: SearchCriteria(max_fees=1_000_000),
                       search_fn=lambda c: ("u", schools))
    assert r.status == "ok" and len(r.results) == 50 and all(m.matched for m in r.results)


# --- fee parsing ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("UGX 900,000 per term", 900_000),
    ("UGX 1,250,000", 1_250_000),
    ("900000", 900_000),
    ("Fees: 450,000/=", 450_000),
    ("UGX 1,200,000.00", 1_200_000),
    ("Contact school", None),
    ("", None),
    (None, None),
])
def test_fee_parsing(raw, expected):
    assert _fees(raw) == expected


# --- HTML parsing robustness ---------------------------------------------------------------

def card(inner):
    return f'<div id="results"><div class="school-card">{inner}</div></div>'


def test_card_without_a_name_is_skipped_not_invented():
    html = '<div id="results"><div class="school-card"><span class="school-fees">UGX 1</span></div></div>'
    assert parse_results(html) == []


def test_malformed_html_does_not_crash():
    html = '<div id="results"><div class="school-card"><span class="school-name">Broken School'
    assert [s.name for s in parse_results(html)] == ["Broken School"]


def test_absolute_links_are_kept_and_relative_links_resolved():
    rel = parse_results(card('<a href="/s/a"><span class="school-name">A</span></a>'))[0]
    absolute = parse_results(card('<a href="https://other.test/s"><span class="school-name">B</span></a>'))[0]
    assert rel.url == "https://eschool.ug/s/a" and absolute.url == "https://other.test/s"


def test_html_in_names_is_reduced_to_text():
    s = parse_results(card('<span class="school-name"><b>Bold</b> <script>alert(1)</script>School</span>'))[0]
    assert "<b>" not in s.name


def test_card_text_is_captured_for_conservative_keyword_checks():
    s = parse_results(card('<span class="school-name">A</span><p>Admitting Senior One and Senior Two</p>'))[0]
    assert "Senior One" in s.text