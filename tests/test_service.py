from app import service
from app.eschool_client import EschoolError
from app.interpreter import InterpretationError
from app.schemas import School, SearchCriteria


def fake_search(schools):
    return lambda c: ("https://example.test/search", schools)


def boom(exc):
    def _raise(*a, **k):
        raise exc

    return _raise


def test_happy_path_returns_results_with_reasons():
    criteria = SearchCriteria(location="Kampala", gender="girls", max_fees=1_000_000)
    school = School(name="A", location="Kampala", gender="Girls", fees=900_000)
    r = service.handle("req", interpret_fn=lambda t: criteria, search_fn=fake_search([school]))
    assert r.status == "ok"
    assert r.results[0].matched
    assert r.search_url


def test_clarification_question_skips_search():
    called = []
    r = service.handle(
        "a good school",
        interpret_fn=lambda t: SearchCriteria(clarification_question="Which district?"),
        search_fn=lambda c: called.append(1),
    )
    assert r.status == "needs_clarification" and r.message == "Which district?"
    assert not called


def test_no_criteria_at_all_asks_for_more():
    called = []
    r = service.handle("hello", interpret_fn=lambda t: SearchCriteria(),
                       search_fn=lambda c: called.append(1))
    assert r.status == "needs_clarification" and not called


def test_unsupported_filters_are_disclosed():
    c = SearchCriteria(
        location="Kampala", admission_class="Senior One", unsupported=["strong sports"]
    )
    r = service.handle("x", interpret_fn=lambda t: c,
                       search_fn=fake_search([School(name="A", boarding="Boarding")]))
    assert r.not_filterable_on_site == ["admission_class"]
    assert "strong sports" in r.message and "admission_class" in r.message


def test_no_results():
    r = service.handle("x", interpret_fn=lambda t: SearchCriteria(location="Gulu"),
                       search_fn=fake_search([]))
    assert r.status == "no_results" and "widening" in r.message


def test_site_failure_reported_not_raised():
    r = service.handle("x", interpret_fn=lambda t: SearchCriteria(location="Gulu"),
                       search_fn=boom(EschoolError("eSchool request failed: 500")))
    assert r.status == "error" and "500" in r.message and r.criteria


def test_ai_failure_reported_not_raised():
    r = service.handle("x", interpret_fn=boom(InterpretationError("AI service failed")))
    assert r.status == "error"


def test_empty_input_rejected():
    assert service.handle("   ").status == "error"
    assert service.handle(None).status == "error"


def test_overlong_input_rejected():
    assert service.handle("a" * (service.MAX_REQUEST_LENGTH + 1)).status == "error"


def test_normalization_runs_before_search():
    seen = {}

    def normalize(c):
        return c.model_copy(update={"county": "KAMPALA NAKAWA DIVISION"})

    def search(c):
        seen["county"] = c.county
        return "u", []

    r = service.handle("x", interpret_fn=lambda t: SearchCriteria(county="Nakawa"),
                       search_fn=search, normalize_fn=normalize)
    assert seen["county"] == "KAMPALA NAKAWA DIVISION"
    assert r.criteria.county == "KAMPALA NAKAWA DIVISION"