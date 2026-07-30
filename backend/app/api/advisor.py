"""Advisor API routes — streaming chat with Claude + conversation management."""

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.manager import AdvisorManager
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.conversation import Conversation
from app.schemas.advisor import (
    ChatRequest,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
)

router = APIRouter(prefix="/api/advisor", tags=["advisor"])
logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _safe_chat_stream(
    manager: AdvisorManager,
    request: ChatRequest,
) -> AsyncGenerator[str, None]:
    """Stream advisor events while preventing exception detail leakage."""
    try:
        async for event in manager.chat(
            user_message=request.message,
            conversation_id=request.conversation_id,
            page_context=request.page_context,
        ):
            yield event
    except Exception:
        logger.exception("Advisor stream failed")
        yield _sse("error", {"error": "Internal server error"})


@router.post("/chat")
async def chat(
    request: ChatRequest,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not configured")

    ALLOWED_MODELS = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250515",
    }
    model = ALLOWED_MODELS.get(request.model or "sonnet", ALLOWED_MODELS["sonnet"])

    manager = AdvisorManager(db=db, api_key=settings.ANTHROPIC_API_KEY, model=model)

    return StreamingResponse(
        _safe_chat_stream(manager, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=c.id,
                title=c.title,
                model=c.model,
                message_count=len(c.messages),
                total_input_tokens=c.total_input_tokens,
                total_output_tokens=c.total_output_tokens,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        messages=conv.messages,
        context_snapshot=conv.context_snapshot,
        total_input_tokens=conv.total_input_tokens,
        total_output_tokens=conv.total_output_tokens,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    _user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return {"status": "deleted"}
