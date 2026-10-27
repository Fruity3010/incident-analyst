from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Preference, Report, ReportLocation
from app.schemas import IncidentExtraction, ReportFilters

COUNTRY_ALIASES = {
    "ivory coast": "Côte d'Ivoire",
    "cote d'ivoire": "Côte d'Ivoire",
    "côte d'ivoire": "Côte d'Ivoire",
    "usa": "United States",
    "us": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "uae": "United Arab Emirates",
    "drc": "Democratic Republic of the Congo",
    "dr congo": "Democratic Republic of the Congo",
    "the gambia": "Gambia",
    "cape verde": "Cabo Verde",
}


def canonical_country(name: str) -> str:
    name = name.strip()
    return COUNTRY_ALIASES.get(name.lower(), name)


def save_report(db: Session, extraction: IncidentExtraction, original_text: str, english_text: str, source_name: str | None) -> Report:
    report = Report(
        title=extraction.title,
        summary=extraction.summary,
        original_language=extraction.original_language,
        crime_type=extraction.crime_type.value,
        incident_date=extraction.incident_date,
        confidence=extraction.confidence,
        original_text=original_text,
        english_text=english_text,
        people=extraction.people,
        organisations=extraction.organisations,
        amounts=[a.model_dump() for a in extraction.amounts],
        source_name=source_name,
        locations=[ReportLocation(country=canonical_country(loc.country), city=loc.city) for loc in extraction.locations],
    )
    db.add(report)
    db.commit()
    return report


def search_reports(db: Session, filters: ReportFilters, limit: int = 50) -> list[Report]:
    q = select(Report)
    if filters.crime_type:
        q = q.where(Report.crime_type == filters.crime_type.value)
    if filters.language:
        q = q.where(Report.original_language == filters.language)
    if filters.date_from:
        q = q.where(Report.incident_date >= filters.date_from)
    if filters.date_to:
        q = q.where(Report.incident_date <= filters.date_to)
    if filters.country:
        wanted = {canonical_country(c).lower() for c in filters.country.split(",") if c.strip()}
        in_country = select(ReportLocation.report_id).where(func.lower(ReportLocation.country).in_(wanted))
        q = q.where(Report.id.in_(in_country))
    q = q.order_by(Report.incident_date.desc().nulls_last(), Report.id.desc()).limit(limit)
    return list(db.scalars(q))


def get_report(db: Session, report_id: int) -> Report | None:
    return db.get(Report, report_id)


def get_reports(db: Session, ids: list[int]) -> list[Report]:
    return list(db.scalars(select(Report).where(Report.id.in_(ids)).order_by(Report.id)))


def count_by(db: Session, group_by: str) -> list[tuple[str, int]]:
    if group_by == "country":
        column = ReportLocation.country
        n = func.count(func.distinct(ReportLocation.report_id)).label("n")
    elif group_by in ("crime_type", "language"):
        column = Report.crime_type if group_by == "crime_type" else Report.original_language
        n = func.count(Report.id).label("n")
    else:
        raise ValueError(f"Can't group by {group_by!r}")
    q = select(column, n).group_by(column).order_by(n.desc(), column)
    return [(key, count) for key, count in db.execute(q)]


def list_preferences(db: Session, user_id: str) -> list[Preference]:
    return list(db.scalars(select(Preference).where(Preference.user_id == user_id).order_by(Preference.id)))


def add_preference(db: Session, user_id: str, text: str) -> Preference:
    pref = Preference(user_id=user_id, text=text.strip())
    db.add(pref)
    db.commit()
    return pref


def delete_preference(db: Session, user_id: str, pref_id: int) -> bool:
    pref = db.get(Preference, pref_id)
    if not pref or pref.user_id != user_id:
        return False
    db.delete(pref)
    db.commit()
    return True
