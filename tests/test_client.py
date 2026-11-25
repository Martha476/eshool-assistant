from pathlib import Path

import httpx
import pytest
import respx

from app.eschool_client import (
    BASE_URL,
    EschoolError,
    build_url,
    not_filterable,
    parse_results,
    search,
)
from app.schemas import SearchCriteria

FIX = Path(__file__).parent / "fixtures"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_build_url_matches_example_format():
    c = SearchCriteria(location="Kampala", county="Kampala Central Division", gender="mixed")
    url = build_url(c)
    assert url.startswith(BASE_URL + "?")
    assert "location=KAMPALA" in url
    assert "county=KAMPALA+CENTRAL+DIVISION" in url
    assert "min_fees=&max_fees=" in url
    assert "gender=mixed" in url


def test_build_url_includes_fees():
    assert "max_fees=1000000" in build_url(SearchCriteria(max_fees=1_000_000))


def test_not_filterable_lists_unsupported_site_filters():
    c = SearchCriteria(location="Kampala", boarding="boarding", admission_class="Senior One")
    assert not_filterable(c) == ["admission_class"]


def test_build_url_maps_supported_public_form_filters():
    c = SearchCriteria(
        school_name="Greenhill", level="Secondary", boarding="boarding",
        admitting_now=True, curriculum="UNEB", facility="Library",
        affiliation="Catholic Founded",
    )
    url = build_url(c)
    assert "q=Greenhill" in url
    assert "levels%5B%5D=Secondary" in url
    assert "accomadation=Boarding" in url
    assert "admission_status=open" in url
    assert "curriculums%5B%5D=UNEB" in url
    assert "facilities%5B%5D=Library" in url
    assert "religions%5B%5D=Catholic+Founded" in url


def test_parse_results_reads_cards():
    schools = parse_results(read("results_page.html"))
    assert [s.name for s in schools] == [
        "Example Girls Boarding School",
        "Sample Mixed Day School",
        "Demo Girls College",
    ]
    first = schools[0]
    assert first.fees == 900_000
    assert first.url == "https://eschool.ug/find-schools/example-girls-boarding"
    assert first.admission_status == "Admitting Senior One"


def test_parse_current_public_card_markup():
    html = """
    <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3">
      <div class="col"><article class="card">
        <div class="card-img-top"><span class="text-success">Admissions Open</span></div>
        <div class="card-body">
          <span class="badge">Secondary</span>
          <div class="text-warning">4.8</div>
          <h3><a href="https://eschool.ug/find-schools?slug=demo">Demo School</a></h3>
          <span class="text-truncate">Kampala</span>
        </div>
      </article></div>
    </div>
    """
    schools = parse_results(html)
    assert len(schools) == 1
    assert schools[0].name == "Demo School"
    assert schools[0].location == "Kampala"
    assert schools[0].level == "Secondary"
    assert schools[0].admission_status == "Admissions Open"
    assert schools[0].rating == "4.8"


def test_missing_fields_stay_none():
    second = parse_results(read("results_page.html"))[1]
    assert second.boarding is None and second.admission_status is None


def test_empty_results_page_returns_empty_list():
    assert parse_results(read("empty_page.html")) == []


def test_current_public_empty_results_message_returns_empty_list():
    html = """
    <div class="row">
      <div class="col-12 py-3">
        <h4>Can't find the school you're looking for?</h4>
        <p>We couldn't find any schools matching your criteria. Try adjusting your filters.</p>
      </div>
    </div>
    """
    assert parse_results(html) == []


def test_unexpected_page_raises():
    with pytest.raises(EschoolError, match="Unexpected response format"):
        parse_results(read("unexpected_page.html"))


@respx.mock
def test_search_success():
    respx.get(BASE_URL).mock(return_value=httpx.Response(200, text=read("results_page.html")))
    url, schools = search(SearchCriteria(location="Kampala"))
    assert "location=KAMPALA" in url and len(schools) == 3


@respx.mock
def test_search_http_error_raises():
    respx.get(BASE_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(EschoolError, match="request failed"):
        search(SearchCriteria(location="Kampala"))


@respx.mock
def test_search_timeout_raises():
    respx.get(BASE_URL).mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(EschoolError):
        search(SearchCriteria(location="Kampala"))