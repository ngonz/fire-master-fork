import pytest

from app.api.advisor import _safe_chat_stream
from app.schemas.advisor import ChatRequest


class _SuccessfulManager:
    def __init__(self):
        self.calls = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        yield 'event: text\ndata: {"text":"hello"}\n\n'
        yield 'event: done\ndata: {"conversation_id":"123"}\n\n'


class _FailingManager:
    async def chat(self, **kwargs):
        raise RuntimeError("traceback: sensitive details")
        yield  # pragma: no cover


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
