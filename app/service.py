"""Orchestration: validate input -> AI interpretation -> eSchool search -> explain."""
from typing import Callable, Optional

from . import eschool_client, interpreter, rag
from .matcher import explain
from .schemas import AssistantResponse, School, SearchCriteria

MAX_REQUEST_LENGTH = 1000


def handle(
    request: str,
    interpret_fn: Optional[Callable[[str], SearchCriteria]] = None,
    search_fn: Optional[Callable[[SearchCriteria], tuple[str, list[School]]]] = None,
    normalize_fn: Optional[Callable[[SearchCriteria], SearchCriteria]] = None,
) -> AssistantResponse:
    interpret_fn = interpret_fn or interpreter.interpret
    search_fn = search_fn or eschool_client.search
    normalize_fn = normalize_fn or rag.normalize_criteria

    request = (request or "").strip()
    if not request:
        return AssistantResponse(
            status="error", message="Please describe the kind of school you are looking for."
        )
    if len(request) > MAX_REQUEST_LENGTH:
        return AssistantResponse(
            status="error",
            message=f"Request is too long (max {MAX_REQUEST_LENGTH} characters). Please shorten it.",
        )

    try:
        criteria = interpret_fn(request)
    except interpreter.InterpretationError as exc:
        return AssistantResponse(status="error", message=str(exc))

    # Ask instead of guessing when the request is too vague to search.
    if criteria.clarification_question or not criteria.specified():
        question = criteria.clarification_question or (
            "Could you tell me more, such as the location, school level, budget per term, "
            "or whether you want a girls', boys' or mixed school?"
        )
        return AssistantResponse(status="needs_clarification", message=question, criteria=criteria)

    # Snap location/division to the exact values the site's form accepts (no-op if unknown).
    normalization_note = None
    try:
        criteria = normalize_fn(criteria)
    except Exception as exc:
        normalization_note = (
            f"Could not normalize the location filters ({exc}); searched using the "
            "original wording."
        )

    gaps = eschool_client.not_filterable(criteria)
    notes: list[str] = []
    if normalization_note:
        notes.append(normalization_note)
    if gaps:
        notes.append(
            "The eSchool search cannot filter on: " + ", ".join(gaps)
            + ". These are checked against each school's visible listing where possible."
        )
    if criteria.unsupported:
        notes.append("Not searchable: " + "; ".join(criteria.unsupported) + ".")
    note = " ".join(notes)

    try:
        url, schools = search_fn(criteria)
    except eschool_client.EschoolError as exc:
        return AssistantResponse(
            status="error",
            message=f"{exc}. Please try again shortly.",
            criteria=criteria,
            not_filterable_on_site=gaps,
        )

    if not schools:
        return AssistantResponse(
            status="no_results",
            message=(note + " " if note else "")
            + "No schools matched these criteria. Try widening the fee range, "
            "removing the area/division, or searching a nearby location.",
            criteria=criteria,
            search_url=url,
            not_filterable_on_site=gaps,
        )

    return AssistantResponse(
        status="ok",
        message=(note + " " if note else "") + f"Found {len(schools)} school(s).",
        criteria=criteria,
        search_url=url,
        not_filterable_on_site=gaps,
        results=[explain(criteria, s) for s in schools],
    )