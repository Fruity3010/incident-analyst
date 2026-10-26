"""Structured extraction: validation, the retry-once rule, and saving."""

import json

import pytest
from pydantic import ValidationError

from app import db, extraction
from app.schemas import IncidentExtraction, ReportFilters

ARTICLE = "Les autorités de Dakar ont démantelé un réseau d'escroquerie en ligne visant des retraités en mars 2025."

TRANSLATION = json.dumps({"original_language": "fr", "english_text": "Dakar authorities dismantled an online scam network targeting retirees in March 2025."})

VALID = json.dumps(
    {
        "title": "Online scam network dismantled in Dakar",
        "summary": "Police in Dakar dismantled an online scam network that targeted retirees.",
        "original_language": "en",
        "crime_type": "Online Fraud",
        "people": [],
        "organisations": ["Dakar Police"],
        "locations": [{"country": "Senegal", "city": "Dakar"}],
        "incident_date": "2025-03-01",
        "amounts": [{"value": 45000000, "currency": "XOF", "context": "victim losses"}],
        "confidence": 0.8,
    }
)


def test_valid_extraction_is_saved_with_translation(fake):
    fake.json_replies = [TRANSLATION, VALID]
    report = extraction.ingest(ARTICLE, "article.txt")

    with db.session() as s:
        saved = db.get_report(s, report.id)
    assert saved.crime_type == "online_fraud"  # normalised by the validator
    assert saved.original_language == "fr"  # taken from step 1, not step 2
    assert saved.english_text.startswith("Dakar authorities")
    assert saved.original_text == ARTICLE
    assert [(l.country, l.city) for l in saved.locations] == [("Senegal", "Dakar")]
    assert saved.amounts[0]["currency"] == "XOF"


def test_invalid_output_is_retried_once_with_the_errors(fake):
    bad = json.dumps({**json.loads(VALID), "confidence": 7})
    fake.json_replies = [TRANSLATION, bad, VALID]
    report = extraction.ingest(ARTICLE)

    assert report.confidence == 0.8
    assert "Validation errors" in fake.prompts[-1]


def test_invalid_output_twice_raises(fake):
    bad = json.dumps({**json.loads(VALID), "crime_type": "jaywalking"})
    fake.json_replies = [TRANSLATION, bad, bad]
    with pytest.raises(extraction.ExtractionError):
        extraction.ingest(ARTICLE)
    with db.session() as s:
        assert db.search_reports(s, ReportFilters()) == []


def test_english_text_is_kept_when_no_translation_needed(fake):
    english = "Police in Lagos arrested three suspects linked to a ransomware attack on a hospital in 2025."
    fake.json_replies = [json.dumps({"original_language": "en", "english_text": ""}), VALID]
    report = extraction.ingest(english)
    assert report.english_text == english
    assert report.original_language == "en"


def test_schema_rejects_missing_and_out_of_range_fields():
    data = json.loads(VALID)
    with pytest.raises(ValidationError):
        IncidentExtraction.model_validate({**data, "title": ""})
    with pytest.raises(ValidationError):
        IncidentExtraction.model_validate({**data, "incident_date": "sometime in spring"})
    with pytest.raises(ValidationError):
        IncidentExtraction.model_validate({k: v for k, v in data.items() if k != "crime_type"})


def test_json_in_code_fences_is_accepted(fake):
    fake.json_replies = [TRANSLATION, f"```json\n{VALID}\n```"]
    assert extraction.ingest(ARTICLE).title.startswith("Online scam")


def test_short_text_and_bad_uploads_are_rejected():
    with pytest.raises(extraction.ExtractionError):
        extraction.analyse("too short")
    with pytest.raises(extraction.ExtractionError):
        extraction.read_upload("photo.png", b"...")
    assert extraction.read_upload("a.txt", "héllo".encode()) == "héllo"
