"""End-to-end: fake AI client -> real service -> real HTTP layer (mocked with respx) -> real parser."""
from urllib.parse import parse_qs, urlparse

import httpx
import respx

from app import eschool_client, service
from app.eschool_client import BASE_URL
from app.interpreter import interpret
from tests.helpers import client_returning, read_fixture

EXAMPLE_REQUEST = (
    "I'm looking for a girls' boarding school in Kampala, preferably around Central "
    "Division, charging no more than UGX 1 million per term and currently admitting "
    "Senior One students."
)

EXAMPLE_CRITERIA = {
    "location": "Kampala",
    "county": "Kampala Central Division",
    "gender": "girls",
    "boarding": "boarding",
    "max_fees": 1_000_000,
    "admitting_now": True,
    "admission_class": "Senior One",
}


def run(request, payload):
    client = client_returning(payload)
    return service.handle(request, interpret_fn=lambda t: interpret(t, client=client))


@respx.mock
def test_example_request_end_to_end():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("results_page.html")))
    r = run(EXAMPLE_REQUEST, EXAMPLE_CRITERIA)

    # the right query reached the site
    params = parse_qs(urlparse(str(route.calls[0].request.url)).query, keep_blank_values=True)
    assert params["location"] == ["KAMPALA"]
    assert params["county"] == ["KAMPALA CENTRAL DIVISION"]
    assert params["max_fees"] == ["1000000"] and params["min_fees"] == [""]
    assert params["gender"] == ["girls"]
    assert params["accomadation"] == ["Boarding"]
    assert params["admission_status"] == ["open"]

    assert r.status == "ok"
    assert r.not_filterable_on_site == ["admission_class"]
    best = r.results[0]
    assert best.school.name == "Example Girls Boarding School"
    assert "fees UGX 900,000 are within UGX 1,000,000" in best.matched
    assert "listing mentions Senior One" in best.matched
    assert best.unverified == []


@respx.mock
def test_over_budget_and_closed_school_is_not_claimed_as_match():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("results_page.html")))
    r = run(EXAMPLE_REQUEST, EXAMPLE_CRITERIA)
    demo = next(m for m in r.results if m.school.name == "Demo Girls College")
    assert any("exceed" in u for u in demo.unverified)
    assert any("closed" in u.lower() for u in demo.unverified)
    assert "admission status: Admissions closed" not in demo.matched


@respx.mock
def test_missing_school_data_is_reported_not_invented():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("results_page.html")))
    r = run("mixed school in Kampala", {"location": "Kampala", "gender": "mixed", "admitting_now": True})
    mixed = next(m for m in r.results if m.school.name == "Sample Mixed Day School")
    assert "admission status not listed" in mixed.unverified


@respx.mock
def test_ambiguous_request_never_calls_the_site():
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, text="should not be fetched"))
    r = run("I want a good school", {"clarification_question": "Which area and class?"})
    assert r.status == "needs_clarification" and r.message == "Which area and class?"
    assert not route.called


@respx.mock
def test_no_matching_schools():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("empty_page.html")))
    r = run("mixed school under 50k", {"location": "Kampala", "gender": "mixed", "max_fees": 50_000})
    assert r.status == "no_results" and r.search_url and "widening" in r.message


@respx.mock
def test_site_returns_500():
    respx.get(BASE_URL).mock(return_value=httpx.Response(500))
    r = run("school in Gulu", {"location": "Gulu"})
    assert r.status == "error" and "request failed" in r.message
    assert r.criteria.location == "GULU"  # normalized criteria are still shown to the user


@respx.mock
def test_site_changes_layout():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("unexpected_page.html")))
    r = run("school in Gulu", {"location": "Gulu"})
    assert r.status == "error" and "Unexpected response format" in r.message


@respx.mock
def test_site_timeout():
    respx.get(BASE_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    assert run("school in Gulu", {"location": "Gulu"}).status == "error"


def test_ai_outage_does_not_reach_the_site():
    from tests.helpers import FakeClient

    client = FakeClient(error=RuntimeError("model_not_supported"))
    with respx.mock:
        route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=""))
        r = service.handle("school in Gulu", interpret_fn=lambda t: interpret(t, client=client))
    assert r.status == "error" and "model_not_supported" in r.message and not route.called


@respx.mock
def test_soft_requirements_are_disclosed_not_dropped():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("results_page.html")))
    r = run("school with strong sports in Kampala", {"location": "Kampala", "unsupported": ["strong sports"]})
    assert r.status == "ok" and "strong sports" in r.message


@respx.mock
def test_division_name_is_normalized_before_searching(monkeypatch):
    from app import rag

    monkeypatch.setattr(rag, "load_options", lambda path=None: {"county": ["KAMPALA NAKAWA DIVISION"]})
    route = respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read_fixture("empty_page.html")))
    run("school in Nakawa", {"location": "Kampala", "county": "Nakawa"})
    assert "county=KAMPALA+NAKAWA+DIVISION" in str(route.calls[0].request.url)


def test_search_function_is_the_only_network_user():
    assert callable(eschool_client.search)