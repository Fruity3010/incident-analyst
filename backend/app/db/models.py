from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(timezone.utc)


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
    people: Mapped[list] = mapped_column(JSON, default=list)
    organisations: Mapped[list] = mapped_column(JSON, default=list)
    amounts: Mapped[list] = mapped_column(JSON, default=list)
    source_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    locations: Mapped[list["ReportLocation"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class ReportLocation(Base):
    __tablename__ = "report_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    city: Mapped[str | None] = mapped_column(String(100))


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    text: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
