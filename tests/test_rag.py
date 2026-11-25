import json

from app import rag
from app.schemas import SearchCriteria

COUNTIES = [
    "KAMPALA CENTRAL DIVISION",
    "KAMPALA NAKAWA DIVISION",
    "KAMPALA RUBAGA DIVISION",
]


# --- loading ------------------------------------------------------------------------------

def test_real_glossary_loads_and_is_well_formed():
    entries = rag.load_entries()
    assert len(entries) >= 6
    for e in entries:
        assert e.id and e.title and e.text


def test_missing_file_returns_empty(tmp_path):
    assert rag.load_entries(tmp_path / "nope.json") == []


def test_malformed_json_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert rag.load_entries(p) == []


def test_non_list_json_returns_empty(tmp_path):
    p = tmp_path / "obj.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert rag.load_entries(p) == []


def test_malformed_entries_are_skipped(tmp_path):
    p = tmp_path / "mixed.json"
    p.write_text(json.dumps([
        {"title": "Good", "text": "ok", "keywords": ["k"]},
        {"title": "No text"},
        "not a dict",
        {"title": "", "text": "empty title"},
        {"title": "Bad keywords", "text": "t", "keywords": "oops"},
    ]), encoding="utf-8")
    assert [e.title for e in rag.load_entries(p)] == ["Good", "Bad keywords"]


# --- retrieval ----------------------------------------------------------------------------

def titles(query, **kw):
    return [e.title for e in rag.retrieve(query, **kw)]


def test_senior_one_retrieves_class_names_first():
    assert titles("Senior One admission")[0] == "Class names and abbreviations"


def test_abbreviation_s1_is_understood():
    assert "Class names and abbreviations" in titles("any S1 places?")


def test_division_name_retrieves_kampala_entry():
    assert titles("somewhere in Nakawa")[0] == "Kampala divisions and nearby districts"


def test_fee_shorthand_retrieves_fee_entry():
    assert titles("budget of 800k per term")[0] == "Fees, terms and currency shorthand"


def test_admission_wording_retrieves_status_entry():
    assert "Admission status wording" in titles("a school with vacancies right now")


def test_boarding_query():
    assert titles("boarding school")[0] == "Boarding and day schools"


def test_unrelated_query_returns_nothing():
    assert rag.retrieve("quantum chromodynamics lecture notes") == []


def test_filler_words_alone_return_nothing():
    assert rag.retrieve("the a of and to is it") == []


def test_empty_and_blank_queries_return_nothing():
    assert rag.retrieve("") == [] and rag.retrieve("   ") == []


def test_k_limits_results_and_zero_k_returns_nothing():
    assert len(rag.retrieve("girls boarding school in Kampala fees S1", k=2)) <= 2
    assert rag.retrieve("girls boarding", k=0) == []


def test_no_entries_returns_nothing():
    assert rag.retrieve("anything", entries=[]) == []


def test_multi_topic_request_retrieves_several_entries():
    got = titles("girls boarding school in Nakawa, S1, under 1 million per term", k=5)
    assert "School gender categories" in got
    assert "Boarding and day schools" in got
    assert "Kampala divisions and nearby districts" in got


def test_retrieval_is_deterministic():
    q = "girls boarding school in Kampala fees S1"
    assert titles(q) == titles(q)


def test_format_context():
    assert rag.format_context([]) == ""
    text = rag.format_context(rag.retrieve("boarding", k=1))
    assert text.startswith("- Boarding and day schools:")


def test_glossary_never_contains_school_listings():
    """The brief forbids building a school dataset; the knowledge base must stay reference-only."""
    blob = " ".join(e.text + e.title for e in rag.load_entries()).lower()
    for marker in ("school fees are ugx", "tel:", "p.o. box", "www."):
        assert marker not in blob


# --- options & canonicalization ----------------------------------------------------------

def test_options_missing_file_is_empty(tmp_path):
    assert rag.load_options(tmp_path / "none.json") == {}


def test_options_bad_json_is_empty(tmp_path):
    p = tmp_path / "o.json"
    p.write_text("[[[", encoding="utf-8")
    assert rag.load_options(p) == {}


def test_options_ignore_comment_keys_and_blank_values(tmp_path):
    p = tmp_path / "o.json"
    p.write_text(json.dumps({"_comment": ["x"], "county": ["A", " ", 5, "B"]}), encoding="utf-8")
    assert rag.load_options(p) == {"county": ["A", "B"]}


def test_shipped_options_file_loads():
    opts = rag.load_options()
    assert set(opts) >= {"location", "county", "gender"}


def test_canonicalize_exact_case_insensitive():
    assert rag.canonicalize("kampala central division", COUNTIES) == "KAMPALA CENTRAL DIVISION"


def test_canonicalize_partial_name_resolves_when_unique():
    assert rag.canonicalize("Nakawa", COUNTIES) == "KAMPALA NAKAWA DIVISION"
    assert rag.canonicalize("Central Division", COUNTIES) == "KAMPALA CENTRAL DIVISION"


def test_canonicalize_close_spelling():
    assert rag.canonicalize("Kampala Rubaga Divison", COUNTIES) == "KAMPALA RUBAGA DIVISION"


def test_canonicalize_ambiguous_keeps_original():
    assert rag.canonicalize("Kampala", COUNTIES) == "Kampala"


def test_canonicalize_unknown_keeps_original():
    assert rag.canonicalize("Gulu", COUNTIES) == "Gulu"


def test_canonicalize_none_or_no_options_is_passthrough():
    assert rag.canonicalize(None, COUNTIES) is None
    assert rag.canonicalize("Nakawa", []) == "Nakawa"


def test_normalize_criteria_updates_only_changed_fields():
    c = SearchCriteria(county="nakawa", max_fees=900_000)
    out = rag.normalize_criteria(c, {"county": COUNTIES})
    assert out.county == "KAMPALA NAKAWA DIVISION"
    assert out.max_fees == 900_000 and out.location is None
    assert c.county == "nakawa"  # original untouched


def test_normalize_criteria_without_options_returns_same_object():
    c = SearchCriteria(location="Kampala")
    assert rag.normalize_criteria(c, {}) is c


def test_options_context_lists_valid_values():
    text = rag.options_context({
        "county": COUNTIES[:2], "level": ["Secondary"], "gender": ["girls"],
    })
    assert "KAMPALA CENTRAL DIVISION" in text and "Secondary" in text and "gender" not in text
    assert rag.options_context({}) == ""