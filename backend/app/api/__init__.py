from fastapi import APIRouter

from app.api import chat, health, memory, reports

router = APIRouter(prefix="/api")
for module in (health, reports, chat, memory):
    router.include_router(module.router)
