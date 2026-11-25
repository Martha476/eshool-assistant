"""Shared test doubles."""
import json
from pathlib import Path
from types import SimpleNamespace

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeClient:
    """Mimics the OpenAI chat-completions API and records every call."""

    def __init__(self, content=None, error=None):
        self._content, self._error = content, error
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=self._content))]
        )

    @property
    def last_user_message(self) -> str:
        return self.calls[-1]["messages"][-1]["content"]


def tool_block(payload: dict):
    return SimpleNamespace(
        type="function",
        function=SimpleNamespace(
            name="set_search_criteria",
            arguments=json.dumps(payload),
        ),
    )


def client_returning(payload: dict) -> FakeClient:
    return FakeClient([tool_block(payload)])