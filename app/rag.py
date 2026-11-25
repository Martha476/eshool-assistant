"""Retrieval-augmented grounding for the interpreter.

This is deliberately NOT a school dataset (the brief forbids one). The knowledge
base holds reference material only:

  knowledge/glossary.json        Uganda education terms, class names, fee shorthand,
                                 Kampala divisions, admission wording
  knowledge/eschool_options.json The exact option values of eSchool's own search form
                                 (location / county / gender), exported by inspect_site.py

Two uses:
  1. retrieve()            picks the few glossary entries relevant to a request and the
                           interpreter adds them to the prompt as reference notes.
  2. normalize_criteria()  snaps extracted filters onto exact values the site's form
                           accepts (deterministic, no AI).

Retrieval is a small TF-IDF keyword scorer. The glossary has a handful of entries, so a
vector database would add dependencies without improving quality.
"""
from __future__ import annotations

import difflib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .schemas import SearchCriteria

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
GLOSSARY_PATH = KNOWLEDGE_DIR / "glossary.json"
OPTIONS_PATH = KNOWLEDGE_DIR / "eschool_options.json"

KEYWORD_PHRASE_BONUS = 3.0


@dataclass(frozen=True)
class Entry:
    id: str
    title: str
    text: str
    keywords: tuple[str, ...] = ()


STOPWORDS = frozenset(
    "a an and are as at be by for from i in is it me my of on or our please the to we with you your".split()
)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _content_tokens(text: str) -> list[str]:
    """Tokens that can carry meaning for retrieval: no stopwords, no single letters."""
    return [t for t in _tokens(text) if len(t) > 1 and t not in STOPWORDS]


def load_entries(path: Optional[Path] = None) -> list[Entry]:
    """Load glossary entries. Missing or malformed files yield [], never an exception."""
    path = Path(path) if path else GLOSSARY_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []

    entries: list[Entry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title, text = item.get("title"), item.get("text")
        if not isinstance(title, str) or not isinstance(text, str) or not title or not text:
            continue
        keywords = item.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []
        entries.append(
            Entry(
                id=str(item.get("id") or title),
                title=title,
                text=text,
                keywords=tuple(k for k in keywords if isinstance(k, str)),
            )
        )
    return entries


def retrieve(query: str, k: int = 3, entries: Optional[list[Entry]] = None) -> list[Entry]:
    """Return up to k entries relevant to the query, best first. [] if nothing matches."""
    entries = load_entries() if entries is None else entries
    query_tokens = set(_content_tokens(query))
    if not entries or not query_tokens or k <= 0:
        return []

    strong_sets = []  # title + keyword tokens: the strongest evidence an entry is relevant
    docs = []
    for e in entries:
        strong = set(_content_tokens(e.title)) | {t for kw in e.keywords for t in _content_tokens(kw)}
        strong_sets.append(strong)
        docs.append(set(_content_tokens(e.text)) | strong)

    n = len(entries)
    df: dict[str, int] = {}
    for d in docs:
        for t in d:
            df[t] = df.get(t, 0) + 1

    lowered_query = " ".join(_tokens(query))
    scored: list[tuple[float, int, Entry]] = []
    for idx, e in enumerate(entries):
        strong = strong_sets[idx]
        score = 0.0
        for t in query_tokens & docs[idx]:
            idf = math.log((n + 1) / (df[t] + 1)) + 1
            score += idf * (2.0 if t in strong else 1.0)
        for kw in e.keywords:
            phrase = " ".join(_tokens(kw))
            if phrase and re.search(rf"\b{re.escape(phrase)}\b", lowered_query):
                score += KEYWORD_PHRASE_BONUS
        # Require at least one strong signal so incidental body words never retrieve anything.
        if score > 0 and (query_tokens & strong):
            scored.append((score, -idx, e))

    scored.sort(reverse=True)
    return [e for _, _, e in scored[:k]]


def format_context(entries: list[Entry]) -> str:
    if not entries:
        return ""
    return "\n".join(f"- {e.title}: {e.text}" for e in entries)


# --------------------------------------------------------------------------- options

def load_options(path: Optional[Path] = None) -> dict[str, list[str]]:
    """Option values exported from the real eSchool form. {} if unavailable."""
    path = Path(path) if path else OPTIONS_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: [v for v in values if isinstance(v, str) and v.strip()]
        for key, values in raw.items()
        if isinstance(values, list) and not key.startswith("_")
    }


def options_context(options: dict[str, list[str]]) -> str:
    """Prompt text listing valid site values so the model can choose them exactly."""
    lines = []
    for field in (
        "location", "county", "level", "admission_status", "boarding",
        "curriculum", "facility", "affiliation",
    ):
        values = options.get(field) or []
        if values:
            lines.append(f"- Valid {field} values on eSchool: " + "; ".join(values[:200]))
    return "\n".join(lines)


def canonicalize(value: Optional[str], valid: list[str], cutoff: float = 0.8) -> Optional[str]:
    """Map a free-text value onto one of the site's valid option values.

    Order: exact (case-insensitive) -> a single option containing the text -> close spelling.
    Ambiguous or unknown values are returned unchanged rather than guessed.
    """
    if not value or not valid:
        return value
    norm = " ".join(_tokens(value))
    by_norm = {" ".join(_tokens(v)): v for v in valid}

    if norm in by_norm:
        return by_norm[norm]

    contains = [orig for n, orig in by_norm.items() if norm and re.search(rf"\b{re.escape(norm)}\b", n)]
    if len(contains) == 1:
        return contains[0]
    if len(contains) > 1:
        return value  # ambiguous: keep what the parent said

    close = difflib.get_close_matches(norm, list(by_norm), n=2, cutoff=cutoff)
    if len(close) == 1 or (len(close) == 2 and
                           difflib.SequenceMatcher(None, norm, close[0]).ratio()
                           - difflib.SequenceMatcher(None, norm, close[1]).ratio() > 0.05):
        return by_norm[close[0]]
    return value


def normalize_criteria(
    criteria: SearchCriteria, options: Optional[dict[str, list[str]]] = None
) -> SearchCriteria:
    """Return criteria with location/county snapped to the site's real option values."""
    options = load_options() if options is None else options
    updates = {}
    for field in (
        "location", "county", "level", "curriculum", "facility", "affiliation",
    ):
        current = getattr(criteria, field)
        fixed = canonicalize(current, options.get(field, []))
        if fixed != current:
            updates[field] = fixed
    return criteria.model_copy(update=updates) if updates else criteria
