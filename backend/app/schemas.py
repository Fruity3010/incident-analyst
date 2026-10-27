from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrimeType(StrEnum):
    ransomware = "ransomware"
    phishing = "phishing"
    online_fraud = "online_fraud"
    business_email_compromise = "business_email_compromise"
    data_breach = "data_breach"
    money_laundering = "money_laundering"
    human_trafficking = "human_trafficking"
    drug_trafficking = "drug_trafficking"
    other = "other"


Language = Literal["en", "fr", "es", "ar", "other"]


class Location(BaseModel):
    country: str = Field(description="Country name in English, e.g. 'Nigeria'")
    city: str | None = Field(default=None, description="City in English, or null if not mentioned")


class Amount(BaseModel):
    value: float = Field(description="The number only, e.g. 2500000")
    currency: str = Field(description="ISO currency code, e.g. USD, EUR, NGN")
    context: str = Field(description="What the amount refers to, in a few words")


class Translation(BaseModel):
    """Step 1 of the analysis: detect the language and translate."""

    original_language: Language = Field(description="ISO 639-1 code of the original text")
    english_text: str = Field(description="Full English translation, or an empty string if the text is already English")


class IncidentExtraction(BaseModel):
    """Step 2 of the analysis: structured fields extracted from the English text."""

    title: str = Field(min_length=3, max_length=200, description="Short headline for the incident, in English")
    summary: str = Field(min_length=10, description="2-3 sentence summary in English")
    original_language: Language
    crime_type: CrimeType
    people: list[str] = Field(default_factory=list, description="Names of people mentioned")
    organisations: list[str] = Field(default_factory=list, description="Companies, agencies, groups mentioned")
    locations: list[Location] = Field(default_factory=list)
    incident_date: date | None = Field(default=None, description="When the incident happened, YYYY-MM-DD, or null if unknown")
    amounts: list[Amount] = Field(default_factory=list, description="Money amounts mentioned")
    confidence: float = Field(ge=0, le=1, description="How confident you are in this extraction, 0 to 1")

    @field_validator("crime_type", mode="before")
    @classmethod
    def normalise_crime_type(cls, v):
        return v.strip().lower().replace(" ", "_").replace("-", "_") if isinstance(v, str) else v


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str
    original_language: str
    crime_type: str
    incident_date: date | None
    confidence: float
    source_name: str | None
    created_at: datetime
    locations: list[Location]


class ReportDetail(ReportOut):
    original_text: str
    english_text: str
    people: list[str]
    organisations: list[str]
    amounts: list[Amount]


class ReportFilters(BaseModel):
    crime_type: CrimeType | None = None
    country: str | None = None
    language: Language | None = None
    date_from: date | None = None
    date_to: date | None = None


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)
