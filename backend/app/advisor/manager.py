"""Advisor manager — orchestrates the Claude conversation with streaming and tool use."""

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.advisor.system_prompt import build_context_snapshot, build_system_prompt
from app.advisor.tools import TOOL_DEFINITIONS, TOOL_EXECUTORS
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOOL_ROUNDS = 10  # Safety limit on tool-use loops


class AdvisorManager:
    def __init__(self, db: AsyncSession, api_key: str, model: str = DEFAULT_MODEL):
        self.db = db
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        user_message: str,
        conversation_id: str | None = None,
        page_context: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message and yield SSE events.

        Event format:
          event: text\ndata: {"text": "..."}\n\n
          event: tool_use\ndata: {"tool": "...", "input": {...}}\n\n
          event: done\ndata: {"conversation_id": "..."}\n\n
          event: error\ndata: {"error": "..."}\n\n
        """
        # Load or create conversation
        conversation = await self._load_or_create(conversation_id)

        # Build system prompt with live financial context
        snapshot = await build_context_snapshot(self.db)
        conversation.context_snapshot = snapshot
        system_prompt = build_system_prompt(snapshot, page_context)

        # Append user message
        conversation.messages.append({"role": "user", "content": user_message})

        # Auto-title from first user message
        if conversation.title is None:
            conversation.title = user_message[:80]

        # Build messages for Claude (exclude internal tool metadata)
        api_messages = self._build_api_messages(conversation.messages)

        total_input = 0
        total_output = 0

        try:
            # Tool-use loop: Claude may call tools, get results, then respond (or call more tools)
            for _round in range(MAX_TOOL_ROUNDS):
                assistant_content = []
                text_buffer = ""

                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=api_messages,
                    tools=TOOL_DEFINITIONS,
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_start":
                            if event.content_block.type == "text":
                                text_buffer = ""
                            elif event.content_block.type == "tool_use":
                                # Signal that a tool call is starting
                                yield self._sse("tool_use", {
                                    "tool": event.content_block.name,
                                    "id": event.content_block.id,
                                })
                        elif event.type == "content_block_delta":
                            if event.delta.type == "text_delta":
                                text_buffer += event.delta.text
                                yield self._sse("text", {"text": event.delta.text})

                    # Get the final message for tool use handling
                    response = await stream.get_final_message()

                # Track tokens
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

                # Collect all content blocks from the response
                assistant_content = []
                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({
                            "type": "text",
                            "text": block.text,
                        })
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                # Save assistant message
                conversation.messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                })

                # Check if we need to execute tools
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if not tool_uses:
                    # No tool calls — we're done
                    break

                # Execute tools and collect results
                tool_results = []
                for tool_use in tool_uses:
                    result = await self._execute_tool(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result),
                    })

                # Save tool results as a user message (Anthropic format)
                conversation.messages.append({
                    "role": "user",
                    "content": tool_results,
                })

                # Rebuild API messages for next round
                api_messages = self._build_api_messages(conversation.messages)

        except Exception:
            logger.exception("Advisor chat error")
            yield self._sse("error", {"error": "Internal server error"})
            return
        finally:
            # Always save conversation state + token counts
            conversation.total_input_tokens += total_input
            conversation.total_output_tokens += total_output
            # Force SQLAlchemy to detect the JSONB mutation
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(conversation, "messages")
            flag_modified(conversation, "context_snapshot")
            await self.db.commit()

        yield self._sse("done", {"conversation_id": str(conversation.id)})

    async def _load_or_create(self, conversation_id: str | None) -> Conversation:
        """Load existing conversation or create a new one."""
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == uuid.UUID(conversation_id))
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        conv = Conversation(model=self.model, messages=[])
        self.db.add(conv)
        await self.db.flush()  # Get the generated ID
        return conv

    def _build_api_messages(self, messages: list[dict]) -> list[dict]:
        """Convert stored messages to Anthropic API format."""
        api_messages = []
        for msg in messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return api_messages

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """Execute a tool and return the result."""
        executor = TOOL_EXECUTORS.get(tool_name)
        if not executor:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = await executor(self.db, tool_input)
            return result
        except Exception:
            logger.exception("Tool execution error: %s", tool_name)
            return {"error": f"Tool '{tool_name}' failed."}

    @staticmethod
    def _sse(event: str, data: dict) -> str:
        """Format a Server-Sent Event."""
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
