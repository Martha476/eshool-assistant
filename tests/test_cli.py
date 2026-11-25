from app import cli
from app.schemas import AssistantResponse, MatchedSchool, School, SearchCriteria


def test_render_ok_shows_reasons_and_gaps():
    r = AssistantResponse(
        status="ok",
        message="Found 1 school(s).",
        criteria=SearchCriteria(location="Kampala"),
        search_url="https://eschool.ug/find-schools/search?location=KAMPALA",
        results=[
            MatchedSchool(
                school=School(
                    name="Example School", url="https://x.test/e", fees=900_000,
                    level="Secondary", admission_status="Admissions Open", rating="4.8",
                ),
                matched=["Girls school"],
                unverified=["admission status not listed"],
            )
        ],
    )
    out = cli.render(r)
    assert "[ok]" in out and "Example School" in out and "UGX 900,000" in out
    assert "+ Girls school" in out and "? admission status not listed" in out
    assert "Level: Secondary" in out
    assert "Admission status: Admissions Open" in out and "Rating: 4.8" in out
    assert "Search URL:" in out


def test_render_missing_fees_says_not_listed():
    r = AssistantResponse(status="ok", results=[MatchedSchool(school=School(name="A"))])
    assert "Fees: not listed" in cli.render(r)


def test_render_zero_fees_as_listed():
    r = AssistantResponse(
        status="ok", results=[MatchedSchool(school=School(name="A", fees=0))]
    )
    assert "Fees: UGX 0" in cli.render(r)


def test_render_clarification_and_error():
    assert "[needs_clarification] Which area?" in cli.render(
        AssistantResponse(status="needs_clarification", message="Which area?")
    )
    assert "[error] boom" in cli.render(AssistantResponse(status="error", message="boom"))


def test_main_uses_argv_and_prints(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["cli", "girls", "school"])
    seen = {}
    monkeypatch.setattr(
        cli, "handle", lambda text: seen.setdefault("t", text) and AssistantResponse(status="error", message="stub")
    )
    cli.main()
    assert seen["t"] == "girls school"
    assert "[error] stub" in capsys.readouterr().out