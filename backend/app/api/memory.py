from fastapi import APIRouter, HTTPException

from app import db
from app.core.config import DEMO_USER

router = APIRouter(tags=["memory"])


@router.get("/memory")
def list_memory():
    with db.session() as s:
        return [{"id": p.id, "text": p.text, "created_at": p.created_at} for p in db.list_preferences(s, DEMO_USER)]


@router.delete("/memory/{pref_id}", status_code=204)
def delete_memory(pref_id: int):
    with db.session() as s:
        if not db.delete_preference(s, DEMO_USER, pref_id):
            raise HTTPException(404, "Preference not found.")
