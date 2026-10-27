from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db
from app.api import router
from app.core import config
from app.llm import ProviderError
from app.services.extraction import ExtractionError


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Incident Report Analyst Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.exception_handler(ProviderError)
def provider_error_handler(_: Request, e: ProviderError):
    return JSONResponse(status_code=e.status, content={"detail": str(e)})


@app.exception_handler(ExtractionError)
def extraction_error_handler(_: Request, e: ExtractionError):
    return JSONResponse(status_code=422, content={"detail": str(e)})
