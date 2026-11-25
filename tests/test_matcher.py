from app.matcher import explain
from app.schemas import School, SearchCriteria


def test_fees_within_budget_matches():
    r = explain(SearchCriteria(max_fees=1_000_000), School(name="X", fees=900_000))
    assert any("900,000" in m for m in r.matched) and not r.unverified


def test_missing_fees_is_unverified_never_matched():
    r = explain(SearchCriteria(max_fees=1_000_000), School(name="X", fees=None))
    assert "fees not listed" in r.unverified
    assert not r.matched


def test_fees_over_budget_not_claimed_as_match():
    r = explain(SearchCriteria(max_fees=1_000_000), School(name="X", fees=1_800_000))
    assert not r.matched
    assert any("exceed" in u for u in r.unverified)


def test_gender_match_and_mismatch():
    c = SearchCriteria(gender="girls")
    assert explain(c, School(name="A", gender="Girls")).matched == ["Girls school"]
    assert explain(c, School(name="B", gender="Mixed")).unverified


def test_admitting_now_variants():
    c = SearchCriteria(admitting_now=True)
    assert explain(c, School(name="A", admission_status="Admitting Senior One")).matched
    assert explain(c, School(name="B", admission_status="Admissions closed")).unverified
    assert explain(c, School(name="C")).unverified == ["admission status not listed"]


def test_admission_class_only_matched_when_mentioned():
    c = SearchCriteria(admission_class="Senior One")
    assert explain(c, School(name="A", text="Admitting Senior One")).matched
    assert explain(c, School(name="B", text="Nothing relevant")).unverified


def test_boarding_status():
    c = SearchCriteria(boarding="boarding")
    assert explain(c, School(name="A", boarding="Boarding")).matched
    assert explain(c, School(name="B")).unverified


def test_both_boarding_requires_both_options():
    c = SearchCriteria(boarding="both")
    assert explain(c, School(name="A", boarding="Day & Boarding")).matched
    assert explain(c, School(name="B", boarding="Boarding")).unverified


def test_closed_admission_request_is_checked():
    c = SearchCriteria(admitting_now=False)
    assert explain(c, School(name="A", admission_status="Admissions closed")).matched
    assert explain(c, School(name="B", admission_status="Admissions Open")).unverified


def test_unlisted_search_filter_details_are_not_claimed():
    c = SearchCriteria(facility="Library", curriculum="UNEB")
    r = explain(c, School(name="A", text="Kampala"))
    assert r.matched == []
    assert "facility 'Library' not confirmed on the listing" in r.unverified
    assert "curriculum 'UNEB' not confirmed on the listing" in r.unverified