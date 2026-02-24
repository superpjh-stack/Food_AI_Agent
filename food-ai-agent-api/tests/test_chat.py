"""Integration tests for chat endpoints with mocked Anthropic client."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from tests.conftest import ADMIN_ID, SITE_ID

pytestmark = pytest.mark.asyncio


def _mock_content_block(text: str):
    """Create a mock text content block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _mock_anthropic_response(text: str, stop_reason: str = "end_turn"):
    """Create a mock Anthropic messages.create response."""
    response = MagicMock()
    response.content = [_mock_content_block(text)]
    response.stop_reason = stop_reason
    return response


@patch("app.agents.orchestrator.AsyncAnthropic")
@patch("app.agents.orchestrator.RAGPipeline")
@patch("app.agents.orchestrator.IntentRouter")
async def test_chat_sse_stream(
    mock_intent_cls, mock_rag_cls, mock_anthropic_cls,
    client: AsyncClient, admin_headers,
):
    """POST /chat returns SSE stream with text_delta and done events."""
    # Mock IntentRouter
    mock_router = MagicMock()
    mock_intent = MagicMock()
    mock_intent.intent = "menu_query"
    mock_intent.agent = "menu"
    mock_intent.confidence = 0.9
    mock_router.classify = AsyncMock(return_value=mock_intent)
    mock_router.rewrite_query = AsyncMock(return_value="이번 주 식단 알려줘")
    mock_intent_cls.return_value = mock_router

    # Mock RAGPipeline
    mock_rag = MagicMock()
    mock_rag_context = MagicMock()
    mock_rag_context.chunks = []
    mock_rag_context.to_prompt_section = MagicMock(return_value="")
    mock_rag.retrieve = AsyncMock(return_value=mock_rag_context)
    mock_rag_cls.return_value = mock_rag

    # Mock Anthropic client
    mock_client = MagicMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_anthropic_response("이번 주 식단은 다음과 같습니다.")
    )
    mock_anthropic_cls.return_value = mock_client

    resp = await client.post("/api/v1/chat", json={
        "message": "이번 주 식단 알려줘",
        "site_id": str(SITE_ID),
    }, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    # Parse SSE events
    events = []
    for line in resp.text.strip().split("\n\n"):
        if line.startswith("data: "):
            event_data = json.loads(line.removeprefix("data: "))
            events.append(event_data)

    # Should have at least text_delta and done events
    event_types = [e["type"] for e in events]
    assert "text_delta" in event_types
    assert "done" in event_types


async def test_chat_no_site_access(client: AsyncClient, kit_headers):
    """Chat with inaccessible site returns 403."""
    fake_site = "99999999-0000-0000-0000-000000000099"
    resp = await client.post("/api/v1/chat", json={
        "message": "test",
        "site_id": fake_site,
    }, headers=kit_headers)
    assert resp.status_code == 403


async def test_list_conversations(client: AsyncClient, admin_headers):
    """GET /conversations returns conversation list."""
    resp = await client.get("/api/v1/chat/conversations", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


async def test_get_conversation_not_found(client: AsyncClient, admin_headers):
    """GET /conversations/{id} returns 404 for non-existent."""
    fake_id = "00000000-0000-0000-0000-999999999999"
    resp = await client.get(f"/api/v1/chat/conversations/{fake_id}", headers=admin_headers)
    assert resp.status_code == 404


async def test_chat_no_auth(client: AsyncClient):
    """POST /chat without auth returns 401."""
    resp = await client.post("/api/v1/chat", json={
        "message": "hello",
        "site_id": str(SITE_ID),
    })
    assert resp.status_code == 401
