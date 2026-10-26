import os
import tempfile

os.environ["DATABASE_URL"] = ""
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="incident-tests-")

from datetime import date

import pytest
from langchain_core.messages import AIMessage

from app import db
from app.llm.base import LLMProvider
from app.schemas import IncidentExtraction


class FakeProvider(LLMProvider):
    name = "fake"
    chat_model = "fake-model"

    def __init__(self):
        self.json_replies: list[str] = []
        self.chat_replies: list[AIMessage] = []
        self.text_reply = "Fake summary."
        self.prompts: list[str] = []
        self.chat_systems: list[str] = []

    def generate(self, system, prompt):
        self.prompts.append(prompt)
        return self.text_reply

    def generate_json(self, system, prompt, schema):
        self.prompts.append(prompt)
        return self.json_replies.pop(0)

    def chat(self, system, messages, tools, on_token=lambda _: None):
        self.chat_systems.append(system)
        reply = self.chat_replies.pop(0)
        for word in reply.content.split(" ") if reply.content else []:
            on_token(word + " ")
        return reply


@pytest.fixture(autouse=True)
def fresh_db():
    db.Base.metadata.drop_all(db.engine)
    db.init_db()


@pytest.fixture
def fake(monkeypatch) -> FakeProvider:
    provider = FakeProvider()
    monkeypatch.setattr("app.llm.get_provider", lambda: provider)
    return provider


def add_report(title="Ransomware hits hospital", crime_type="ransomware", language="en", country="Nigeria", city="Lagos", when=date(2025, 3, 1)) -> int:
    extraction = IncidentExtraction(
        title=title,
        summary=f"{title}. A fictional test report.",
        original_language=language,
        crime_type=crime_type,
        locations=[{"country": country, "city": city}],
        incident_date=when,
        confidence=0.9,
    )
    with db.session() as s:
        return db.save_report(s, extraction, f"Original text of {title}", f"English text of {title}", None).id
