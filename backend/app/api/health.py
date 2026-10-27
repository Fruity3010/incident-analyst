from fastapi import APIRouter

from app import llm
from app.core import config
from app.llm import ProviderError

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    try:
        provider = llm.get_provider()
        return {"status": "ok", "provider": provider.name, "model": provider.chat_model, "database": "postgresql" if config.IS_POSTGRES else "sqlite"}
    except ProviderError as e:
        return {"status": "error", "provider": config.LLM_PROVIDER, "model": None, "error": str(e)}
