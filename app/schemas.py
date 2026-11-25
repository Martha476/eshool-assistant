"""Data models shared across the application."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SearchCriteria(BaseModel):
    """Structured search criteria extracted from a parent's request.

    Every field is None unless the parent explicitly stated it, so
    "not specified" is always distinguishable from a real preference.
    """

    location: Optional[str] = Field(None, description="City/district, e.g. 'Kampala'")
    county: Optional[str] = Field(
        None, description="Administrative area/division, e.g. 'Kampala Central Division'"
    )
    min_fees: Optional[int] = Field(None, ge=0, description="Minimum fees per term in UGX")
    max_fees: Optional[int] = Field(None, ge=0, description="Maximum fees per term in UGX")
    gender: Optional[Literal["boys", "girls", "mixed"]] = Field(
        None, description="School category by gender intake"
    )
    boarding: Optional[Literal["boarding", "day", "both"]] = None
    level: Optional[str] = Field(None, description="e.g. 'nursery', 'primary', 'secondary'")
    admission_class: Optional[str] = Field(None, description="e.g. 'Senior One', 'Primary One'")
    admitting_now: Optional[bool] = Field(
        None, description="True for open admissions, false for closed admissions"
    )
    school_name: Optional[str] = Field(None, description="A named school to search for")
    curriculum: Optional[str] = Field(None, description="Curriculum or syllabus preference")
    facility: Optional[str] = Field(None, description="A requested school facility")
    affiliation: Optional[str] = Field(None, description="Religious or other school affiliation")
    unsupported: list[str] = Field(
        default_factory=list,
        description="Requirements that cannot be expressed as a filter, e.g. 'strong sports'",
    )
    clarification_question: Optional[str] = Field(
        None,
        description="One short question, set only if the request is too vague or contradictory to search",
    )

    @model_validator(mode="after")
    def _fees_consistent(self):
        if (
            self.min_fees is not None
            and self.max_fees is not None
            and self.min_fees > self.max_fees
        ):
            raise ValueError("min_fees cannot exceed max_fees")
        return self

    def specified(self) -> dict:
        """Only the criteria the parent actually stated."""
        data = self.model_dump(exclude={"unsupported", "clarification_question"})
        return {k: v for k, v in data.items() if v is not None}


class School(BaseModel):
    name: str
    url: Optional[str] = None
    location: Optional[str] = None
    level: Optional[str] = None
    gender: Optional[str] = None
    boarding: Optional[str] = None
    fees: Optional[int] = None  # None = not listed on the page
    admission_status: Optional[str] = None
    rating: Optional[str] = None
    text: str = ""  # full visible card text, used for conservative keyword checks


class MatchedSchool(BaseModel):
    school: School
    matched: list[str] = Field(default_factory=list)
    unverified: list[str] = Field(default_factory=list)


class AssistantResponse(BaseModel):
    status: Literal["ok", "needs_clarification", "no_results", "error"]
    message: str = ""
    criteria: Optional[SearchCriteria] = None
    search_url: Optional[str] = None
    not_filterable_on_site: list[str] = Field(default_factory=list)
    results: list[MatchedSchool] = Field(default_factory=list)