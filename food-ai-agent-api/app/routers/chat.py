"""Chat router - AI agent SSE streaming endpoint."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.orm.conversation import Conversation
from app.models.orm.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    site_id: UUID
    conversation_id: UUID | None = None


@router.post("")
async def send_message(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send message to AI agent with SSE streaming response."""
    # Verify site access
    if (
        current_user.role not in ("ADM", "OPS")
        and body.site_id not in (current_user.site_ids or [])
    ):
        raise HTTPException(status_code=403, detail="No access to this site")

    orchestrator = AgentOrchestrator(db)

    async def event_stream():
        async for event in orchestrator.run(
            message=body.message,
            user=current_user,
            site_id=body.site_id,
            conversation_id=body.conversation_id,
        ):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_active == True)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    conversations = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(c.id),
                "title": c.title,
                "context_type": c.context_type,
                "message_count": len(c.messages) if c.messages else 0,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation detail."""
    conv = (await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "success": True,
        "data": {
            "id": str(conv.id),
            "title": conv.title,
            "context_type": conv.context_type,
            "messages": conv.messages or [],
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        },
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a conversation."""
    conv = (await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.is_active = False
    await db.flush()

    return {"success": True, "data": {"deleted": True}}
