from datetime import date
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app import db, llm
from app.schemas import CrimeType, Language, ReportFilters

NOTHING_FOUND = "No reports matched these filters."
LANGUAGE_NAMES = {"en": "English", "fr": "French", "es": "Spanish", "ar": "Arabic"}


def _ref(r: db.Report) -> str:
    return f"[Report #{r.id}] {r.title}"


def _line(r: db.Report) -> str:
    countries = ", ".join(sorted({loc.country for loc in r.locations})) or "unknown"
    return f"{_ref(r)} | {r.crime_type} | language: {r.original_language} | date: {r.incident_date or 'unknown'} | countries: {countries}"


@tool
def search_reports(
    crime_type: CrimeType | None = None,
    country: str | None = None,
    language: Language | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    """Find saved incident reports. All filters are optional and can be combined.

    country: English country name, e.g. "Nigeria". For a region, list its countries
    in ONE call, comma-separated, e.g. "Nigeria, Ghana, Senegal". language: original language code.
    date_from / date_to: YYYY-MM-DD, compared with the incident date.
    """
    filters = ReportFilters(crime_type=crime_type, country=country, language=language, date_from=date_from, date_to=date_to)
    with db.session() as s:
        reports = db.search_reports(s, filters)
    if not reports:
        return NOTHING_FOUND
    return f"Found {len(reports)} report(s):\n" + "\n".join(_line(r) for r in reports)


@tool
def get_report(report_id: int) -> str:
    """Get the full details of one report by its id."""
    with db.session() as s:
        r = db.get_report(s, report_id)
    if not r:
        return f"There is no report with id {report_id}."
    locations = "; ".join(f"{loc.city + ', ' if loc.city else ''}{loc.country}" for loc in r.locations) or "none"
    amounts = "; ".join(f"{a['value']:,.0f} {a['currency']} ({a['context']})" for a in r.amounts) or "none"
    return "\n".join(
        [
            _line(r),
            f"Summary: {r.summary}",
            f"Locations: {locations}",
            f"People: {', '.join(r.people) or 'none'}",
            f"Organisations: {', '.join(r.organisations) or 'none'}",
            f"Amounts: {amounts}",
            f"Extraction confidence: {r.confidence:.2f}",
            f"English text:\n{r.english_text[:3000]}",
        ]
    )


@tool
def summarize_reports(
    report_ids: list[int] | None = None,
    crime_type: CrimeType | None = None,
    country: str | None = None,
    language: Language | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    """Write one combined summary of several reports.

    Pass report_ids, or filters (same as search_reports) to choose the reports. At most 10 are used.
    """
    with db.session() as s:
        if report_ids:
            reports = db.get_reports(s, report_ids)
        else:
            filters = ReportFilters(crime_type=crime_type, country=country, language=language, date_from=date_from, date_to=date_to)
            reports = db.search_reports(s, filters, limit=10)
    if not reports:
        return NOTHING_FOUND
    reports = reports[:10]
    corpus = "\n\n".join(f"{_line(r)}\n{r.english_text[:1500]}" for r in reports)
    summary = llm.get_provider().generate(
        "You summarise incident reports for an analyst. Write one short paragraph covering common patterns, "
        "then one bullet per report. Cite each report as [Report #id]. Use only the reports given.",
        corpus,
    )
    return f"{summary}\n\nReports used: " + "; ".join(_ref(r) for r in reports)


@tool
def stats(group_by: Literal["crime_type", "country", "language"]) -> str:
    """Count saved reports grouped by crime_type, country or language."""
    with db.session() as s:
        rows = db.count_by(s, group_by)
    if not rows:
        return "There are no reports yet."
    return f"Reports by {group_by}:\n" + "\n".join(f"- {key}: {n}" for key, n in rows)


@tool
def translate(text: str, target_language: Literal["en", "fr", "es", "ar"]) -> str:
    """Translate text into English, French, Spanish or Arabic. Keep [Report #id] references unchanged."""
    return llm.get_provider().generate(
        f"Translate the user's text into {LANGUAGE_NAMES[target_language]}. "
        "Keep [Report #id] references, names and numbers unchanged. Return only the translation.",
        text,
    )


@tool
def remember_preference(preference: str, config: RunnableConfig) -> str:
    """Save a lasting preference or fact about the user, e.g. "Always answer in French" or
    "Focuses on West Africa". Only use this when the user asks you to remember something.
    """
    user_id = config["configurable"]["user_id"]
    with db.session() as s:
        db.add_preference(s, user_id, preference)
    return f"Saved to long-term memory: {preference}"


ALL_TOOLS = [search_reports, get_report, summarize_reports, stats, translate, remember_preference]
