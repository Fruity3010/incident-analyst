from datetime import date

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from app import db
from app.core import config
from app.schemas import CrimeType, Language, ReportDetail, ReportFilters, ReportOut
from app.services import extraction

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=ReportDetail, status_code=201)
async def create_report(text: str | None = Form(None), file: UploadFile | None = None):
    if file and file.filename:
        limit = config.MAX_UPLOAD_MB * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"File is larger than {config.MAX_UPLOAD_MB} MB.")
        content, source = extraction.read_upload(file.filename, data), file.filename
    elif text and text.strip():
        content, source = text, None
    else:
        raise HTTPException(400, "Paste some text or upload a .txt/.pdf file.")
    return await run_in_threadpool(extraction.ingest, content, source)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(
    crime_type: CrimeType | None = None,
    country: str | None = None,
    language: Language | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(200, ge=1, le=500),
):
    filters = ReportFilters(crime_type=crime_type, country=country or None, language=language, date_from=date_from, date_to=date_to)
    with db.session() as s:
        return db.search_reports(s, filters, limit=limit)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def read_report(report_id: int):
    with db.session() as s:
        report = db.get_report(s, report_id)
    if not report:
        raise HTTPException(404, "Report not found.")
    return report


@router.get("/stats")
def stats():
    with db.session() as s:
        return {group: [{"key": key, "count": n} for key, n in db.count_by(s, group)] for group in ("crime_type", "country", "language")}
