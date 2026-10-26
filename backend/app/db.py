"""Database: SQLAlchemy tables plus every query the app runs.

All queries are fixed Python code with bound parameters. The LLM only ever
supplies filter *values* (validated by Pydantic first). It never writes SQL.
"""

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from app import config
from app.schemas import IncidentExtraction, ReportFilters

if not config.IS_POSTGRES:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(config.DATABASE_URL)


def now() -> datetime:
    return datetime.now(timezone.utc)


# Different spellings of the same country, mapped to the one name we store.
# Without this, a search for "Ivory Coast" misses a report saved as "Côte d'Ivoire".
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


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    original_language: Mapped[str] = mapped_column(String(8), index=True)
    crime_type: Mapped[str] = mapped_column(String(40), index=True)
    incident_date: Mapped[date | None] = mapped_column(Date, index=True)
    confidence: Mapped[float] = mapped_column(Float)
    original_text: Mapped[str] = mapped_column(Text)
    english_text: Mapped[str] = mapped_column(Text)
    # Lists we only display, never filter on, are stored as JSON
    people: Mapped[list] = mapped_column(JSON, default=list)
    organisations: Mapped[list] = mapped_column(JSON, default=list)
    amounts: Mapped[list] = mapped_column(JSON, default=list)
    source_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    # Locations get their own table because we filter and group by country
    locations: Mapped[list["ReportLocation"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class ReportLocation(Base):
    __tablename__ = "report_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100))


class Preference(Base):
    """Long-term memory: facts and preferences a user asked the agent to remember."""

    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def init_db() -> None:
    """Create tables if they don't exist (simple alternative to migrations for a demo)."""
    Base.metadata.create_all(engine)


def session() -> Session:
    return Session(engine, expire_on_commit=False)


# ---------- reports ----------


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
    """Filter reports. Each filter adds a WHERE clause with a bound parameter."""
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
        # "Nigeria, Ghana" matches reports in either country (case-insensitive, aliases resolved)
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
    """Counts per crime type, country or language, biggest first."""
    if group_by == "country":
        # A report is counted once per distinct country it mentions
        column = ReportLocation.country
        n = func.count(func.distinct(ReportLocation.report_id)).label("n")
    elif group_by in ("crime_type", "language"):
        column = Report.crime_type if group_by == "crime_type" else Report.original_language
        n = func.count(Report.id).label("n")
    else:
        raise ValueError(f"Can't group by {group_by!r}")
    q = select(column, n).group_by(column).order_by(n.desc(), column)
    return [(key, count) for key, count in db.execute(q)]


# ---------- long-term memory ----------


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
