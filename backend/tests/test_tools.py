from datetime import date

import pytest
from pydantic import ValidationError

from app import db, tools
from app.schemas import ReportFilters
from tests.conftest import add_report


@pytest.fixture
def reports():
    return {
        "lagos": add_report("Ransomware hits Lagos hospital", "ransomware", "en", "Nigeria", "Lagos", date(2025, 3, 1)),
        "abuja": add_report("Phishing wave in Abuja", "phishing", "en", "Nigeria", "Abuja", date(2024, 11, 5)),
        "dakar": add_report("Arnaque en ligne à Dakar", "online_fraud", "fr", "Senegal", "Dakar", date(2025, 6, 10)),
        "madrid": add_report("Ransomware en Madrid", "ransomware", "es", "Spain", "Madrid", None),
    }


def ids(filters: ReportFilters) -> set[int]:
    with db.session() as s:
        return {r.id for r in db.search_reports(s, filters)}


def test_filters_by_each_field(reports):
    assert ids(ReportFilters(crime_type="ransomware")) == {reports["lagos"], reports["madrid"]}
    assert ids(ReportFilters(country="nigeria")) == {reports["lagos"], reports["abuja"]}
    assert ids(ReportFilters(language="fr")) == {reports["dakar"]}
    assert ids(ReportFilters(date_from=date(2025, 1, 1))) == {reports["lagos"], reports["dakar"]}
    assert ids(ReportFilters(date_to=date(2024, 12, 31))) == {reports["abuja"]}


def test_country_list_and_aliases(reports):
    assert ids(ReportFilters(country="Senegal, Spain")) == {reports["dakar"], reports["madrid"]}
    abidjan = add_report("Phishing in Abidjan", "phishing", "fr", "Ivory Coast", "Abidjan")
    assert ids(ReportFilters(country="Côte d'Ivoire")) == {abidjan}
    assert ids(ReportFilters(country="ivory coast")) == {abidjan}


def test_filters_combine_with_and(reports):
    assert ids(ReportFilters(crime_type="ransomware", country="Nigeria", date_from=date(2025, 1, 1))) == {reports["lagos"]}
    assert ids(ReportFilters(crime_type="phishing", country="Spain")) == set()


def test_injection_attempt_is_just_a_value(reports):
    assert ids(ReportFilters(country="Nigeria' OR '1'='1")) == set()
    assert len(ids(ReportFilters())) == 4


def test_invalid_filter_values_are_rejected():
    with pytest.raises(ValidationError):
        ReportFilters(crime_type="DROP TABLE reports")
    with pytest.raises(ValidationError):
        ReportFilters(date_from="last tuesday")


def test_search_reports_tool_lists_ids_and_says_when_empty(reports):
    out = tools.search_reports.invoke({"crime_type": "ransomware", "country": "Nigeria"})
    assert f"[Report #{reports['lagos']}] Ransomware hits Lagos hospital" in out
    assert "Madrid" not in out
    assert tools.search_reports.invoke({"country": "Japan"}) == tools.NOTHING_FOUND


def test_search_reports_tool_validates_llm_arguments(reports):
    with pytest.raises(ValidationError):
        tools.search_reports.invoke({"crime_type": "shoplifting"})


def test_get_report_tool(reports):
    out = tools.get_report.invoke({"report_id": reports["dakar"]})
    assert "Arnaque en ligne à Dakar" in out and "Dakar, Senegal" in out and "English text" in out
    assert "no report with id 999" in tools.get_report.invoke({"report_id": 999})


def test_summarize_reports_tool_by_ids_and_filters(reports, fake):
    fake.text_reply = "Two ransomware incidents."
    out = tools.summarize_reports.invoke({"report_ids": [reports["lagos"], reports["madrid"]]})
    assert out.startswith("Two ransomware incidents.")
    assert f"[Report #{reports['madrid']}]" in out
    assert "English text of Ransomware hits Lagos hospital" in fake.prompts[-1]

    out = tools.summarize_reports.invoke({"language": "fr"})
    assert f"[Report #{reports['dakar']}]" in out and "Lagos" not in out.split("Reports used:")[1]
    assert tools.summarize_reports.invoke({"country": "Japan"}) == tools.NOTHING_FOUND


def test_stats_tool(reports):
    assert "- ransomware: 2" in tools.stats.invoke({"group_by": "crime_type"})
    assert "- Nigeria: 2" in tools.stats.invoke({"group_by": "country"})
    assert "- en: 2" in tools.stats.invoke({"group_by": "language"})


def test_stats_tool_with_no_reports():
    assert tools.stats.invoke({"group_by": "country"}) == "There are no reports yet."


def test_translate_tool(fake):
    fake.text_reply = "Bonjour"
    assert tools.translate.invoke({"text": "Hello", "target_language": "fr"}) == "Bonjour"
    with pytest.raises(ValidationError):
        tools.translate.invoke({"text": "Hello", "target_language": "klingon"})


def test_remember_preference_tool_uses_user_from_config():
    out = tools.remember_preference.invoke({"preference": "Always answer in French"}, config={"configurable": {"user_id": "alice"}})
    assert "Always answer in French" in out
    with db.session() as s:
        assert [p.text for p in db.list_preferences(s, "alice")] == ["Always answer in French"]
        assert db.list_preferences(s, "bob") == []


def test_seed_data_is_valid_and_searchable():
    import seed

    assert seed.seed() == 8
    assert seed.seed() == 0
    assert "- ar: 2" in tools.stats.invoke({"group_by": "language"})
    assert "Casablanca" in tools.search_reports.invoke({"country": "Morocco", "language": "ar"})
