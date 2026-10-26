"""All settings come from environment variables (loaded from backend/.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# Which provider to use: "gemini" (default) or "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")

# Ollama (local). The model must support tool calling, e.g. llama3.2 or qwen3.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")

# Database: PostgreSQL if DATABASE_URL is set, otherwise a local SQLite file
DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DATA_DIR / 'app.db'}"
IS_POSTGRES = DATABASE_URL.startswith("postgresql")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 10))
MAX_REPORT_CHARS = int(os.getenv("MAX_REPORT_CHARS", 20000))  # keeps prompts small

# Comma-separated list of frontend origins allowed by CORS
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
