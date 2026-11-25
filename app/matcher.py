"""Deterministic 'why does this school match?' logic.

No AI here: explanations are built only from fields actually present on
the school. If a requested attribute cannot be confirmed, it is listed
under `unverified` instead of being claimed as a match.
"""
from .schemas import MatchedSchool, School, SearchCriteria


def _contains(haystack: str | None, needle: str | None) -> bool:
    return bool(haystack and needle and needle.lower() in haystack.lower())


def explain(c: SearchCriteria, s: School) -> MatchedSchool:
    matched: list[str] = []
    unverified: list[str] = []

    if c.location:
        if _contains(s.location, c.location) or _contains(s.text, c.location):
            matched.append(f"located in {c.location.title()}")
        else:
            unverified.append(f"location '{c.location}' not confirmed on the listing")

    if c.county:
        if _contains(s.location, c.county) or _contains(s.text, c.county):
            matched.append(f"in {c.county.title()}")
        else:
            unverified.append(f"area '{c.county}' not confirmed on the listing")

    if c.gender:
        if s.gender is None:
            unverified.append(f"school category (wanted {c.gender}) not listed")
        elif c.gender.lower() in s.gender.lower():
            matched.append(f"{s.gender} school")
        else:
            unverified.append(f"listed as '{s.gender}', wanted {c.gender}")

    if c.max_fees is not None:
        if s.fees is None:
            unverified.append("fees not listed")
        elif s.fees <= c.max_fees:
            matched.append(f"fees UGX {s.fees:,} are within UGX {c.max_fees:,}")
        else:
            unverified.append(f"fees UGX {s.fees:,} exceed UGX {c.max_fees:,}")

    if c.min_fees is not None:
        if s.fees is None:
            if "fees not listed" not in unverified:
                unverified.append("fees not listed")
        elif s.fees >= c.min_fees:
            matched.append(f"fees UGX {s.fees:,} are at least UGX {c.min_fees:,}")
        else:
            unverified.append(f"fees UGX {s.fees:,} are below UGX {c.min_fees:,}")

    if c.boarding:
        source = s.boarding or ""
        if not source:
            unverified.append(f"boarding/day status (wanted {c.boarding}) not listed")
        elif (
            c.boarding == "both"
            and any(value in source.lower() for value in ("both", "day & boarding", "day and boarding"))
        ) or (c.boarding != "both" and c.boarding in source.lower()):
            matched.append(f"{source}")
        else:
            unverified.append(f"listed as '{source}', wanted {c.boarding}")

    if c.admitting_now is not None:
        status = (s.admission_status or "").lower()
        if not status:
            unverified.append("admission status not listed")
        elif c.admitting_now and any(w in status for w in ("closed", "not admitting", "full")):
            unverified.append(f"admission status is '{s.admission_status}'")
        elif not c.admitting_now and any(w in status for w in ("open", "admitting", "accepting")):
            unverified.append(f"admission status is '{s.admission_status}'")
        elif c.admitting_now and any(w in status for w in ("open", "admitting", "accepting")):
            matched.append(f"admission status: {s.admission_status}")
        elif not c.admitting_now and any(w in status for w in ("closed", "not admitting", "full")):
            matched.append(f"admission status: {s.admission_status}")
        else:
            unverified.append(f"admission status unclear: '{s.admission_status}'")

    if c.school_name:
        if _contains(s.name, c.school_name):
            matched.append(f"school name includes {c.school_name}")
        else:
            unverified.append(f"school name '{c.school_name}' not confirmed")

    if c.admission_class:
        if _contains(s.text, c.admission_class):
            matched.append(f"listing mentions {c.admission_class}")
        else:
            unverified.append(f"admission to {c.admission_class} not confirmed on the listing")

    if c.level:
        if _contains(s.text, c.level):
            matched.append(f"listing mentions {c.level} level")
        else:
            unverified.append(f"{c.level} level not confirmed on the listing")

    for value, label in (
        (c.curriculum, "curriculum"),
        (c.facility, "facility"),
        (c.affiliation, "affiliation"),
    ):
        if value:
            if _contains(s.text, value):
                matched.append(f"listing mentions {value}")
            else:
                unverified.append(f"{label} '{value}' not confirmed on the listing")

    return MatchedSchool(school=s, matched=matched, unverified=unverified)