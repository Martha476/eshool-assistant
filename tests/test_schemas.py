import pytest
from pydantic import ValidationError

from app.schemas import SearchCriteria


def test_unspecified_fields_are_none():
    c = SearchCriteria()
    assert c.specified() == {}


def test_specified_returns_only_stated_fields():
    c = SearchCriteria(location="Kampala", max_fees=1_000_000)
    assert c.specified() == {"location": "Kampala", "max_fees": 1_000_000}


def test_min_greater_than_max_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(min_fees=2_000_000, max_fees=1_000_000)


def test_negative_fees_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(max_fees=-5)


def test_invalid_gender_rejected():
    with pytest.raises(ValidationError):
        SearchCriteria(gender="robots")