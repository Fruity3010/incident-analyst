from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core import config
from app.db.models import Base

if not config.IS_POSTGRES:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(config.DATABASE_URL)


def init_db() -> None:
    Base.metadata.create_all(engine)


def session() -> Session:
    return Session(engine, expire_on_commit=False)
