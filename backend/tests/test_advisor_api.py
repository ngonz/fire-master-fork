import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.advisor.manager import AdvisorManager
from app.api.advisor import _safe_chat_stream
from app.schemas.advisor import ChatRequest

SENSITIVE_ERROR_MESSAGE = "traceback: sensitive details"


class _SuccessfulManager:
    def __init__(self):
        self.calls = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        yield 'event: text\ndata: {"text":"hello"}\n\n'
        yield 'event: done\ndata: {"conversation_id":"123"}\n\n'


class _FailingManager:
    async def chat(self, **kwargs):
        if False:  # pragma: no cover
            yield ""
        raise RuntimeError(SENSITIVE_ERROR_MESSAGE)


@pytest.mark.asyncio
async def test_safe_chat_stream_passthrough_events():
    manager = _SuccessfulManager()
    request = ChatRequest(
        message="Hello",
        conversation_id="conv-id",
        page_context="dashboard",
        model="sonnet",
    )

    events = [event async for event in _safe_chat_stream(manager, request)]

    assert events == [
        'event: text\ndata: {"text":"hello"}\n\n',
        'event: done\ndata: {"conversation_id":"123"}\n\n',
    ]
    assert manager.calls == [
        {
            "user_message": "Hello",
            "conversation_id": "conv-id",
            "page_context": "dashboard",
        }
    ]


@pytest.mark.asyncio
async def test_safe_chat_stream_masks_exception_details():
    request = ChatRequest(message="Hello")

    events = [event async for event in _safe_chat_stream(_FailingManager(), request)]

    assert len(events) == 1
    assert events[0] == 'event: error\ndata: {"error": "Internal server error"}\n\n'
    assert "traceback" not in events[0]


class _FailingStream:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise RuntimeError(SENSITIVE_ERROR_MESSAGE)


@pytest.mark.asyncio
async def test_advisor_manager_masks_exception_details(monkeypatch):
    conversation = SimpleNamespace(
        id=uuid.uuid4(),
        messages=[],
        title=None,
        context_snapshot={},
        total_input_tokens=0,
        total_output_tokens=0,
    )
    db = SimpleNamespace(commit=AsyncMock())
    manager = AdvisorManager.__new__(AdvisorManager)
    manager.db = db
    manager.model = "claude-sonnet-4-20250514"
    manager.client = SimpleNamespace(
        messages=SimpleNamespace(stream=lambda **kwargs: _FailingStream())
    )
    manager._load_or_create = AsyncMock(return_value=conversation)

    monkeypatch.setattr("app.advisor.manager.build_context_snapshot", AsyncMock(return_value={}))
    monkeypatch.setattr("app.advisor.manager.build_system_prompt", lambda *_: "system")
    monkeypatch.setattr("sqlalchemy.orm.attributes.flag_modified", lambda *_: None)

    events = [event async for event in manager.chat(user_message="Hello")]

    assert events == ['event: error\ndata: {"error": "Internal server error"}\n\n']
    assert "traceback" not in events[0]
