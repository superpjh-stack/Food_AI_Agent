"""Agent Orchestrator - ReAct agentic loop with Claude Tool Use and SSE streaming."""
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import UUID

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent_router import IntentRouter, UserContext, IntentResult
from app.agents.prompts.system import build_system_prompt
from app.agents.tools.registry import get_tools_for_agent, get_tool_names_for_agent
from app.config import settings
from app.models.orm.audit_log import AuditLog
from app.models.orm.conversation import Conversation
from app.models.orm.site import Site
from app.models.orm.user import User
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# Domain-specific RAG doc_type filters
AGENT_DOC_TYPES = {
    "menu": ["recipe", "sop"],
    "recipe": ["recipe", "sop"],
    "haccp": ["haccp_guide"],
    "general": ["recipe", "sop", "haccp_guide", "policy"],
}


class AgentOrchestrator:
    """ReAct agent loop: Intent → RAG → Claude (streaming + tool calls) → Response."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.intent_router = IntentRouter()
        self.rag = RAGPipeline(db)
        self.max_iterations = 10

    async def run(
        self,
        message: str,
        user: User,
        site_id: UUID,
        conversation_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """Execute the agentic loop, yielding SSE events."""

        # 1. Load site
        site = (await self.db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
        if not site:
            yield self._sse("text_delta", content="현장 정보를 찾을 수 없습니다.")
            yield self._sse("done")
            return

        # 2. Intent classification
        context = UserContext(
            user_role=user.role,
            site_name=site.name,
            site_id=str(site_id),
        )
        intent = await self.intent_router.classify(message, context)
        logger.info(f"Intent: {intent.intent} (confidence={intent.confidence}, agent={intent.agent})")

        # 3. Query rewrite for RAG
        search_query = await self.intent_router.rewrite_query(message, intent.intent, context)

        # 4. RAG Retrieve (domain-specific)
        doc_types = AGENT_DOC_TYPES.get(intent.agent, ["recipe", "sop"])
        rag_context = await self.rag.retrieve(search_query, doc_types=doc_types)

        # 5. Build system prompt
        system_prompt = build_system_prompt(
            agent_type=intent.agent,
            user_role=user.role,
            user_name=user.name,
            site_name=site.name,
            site_type=site.type,
            site_capacity=site.capacity,
            rag_context=rag_context.to_prompt_section(),
        )

        # 6. Load conversation history
        conversation_history = await self._load_history(conversation_id)

        # 7. Build messages
        messages = [
            *conversation_history[-20:],  # sliding window: last 10 turns
            {"role": "user", "content": message},
        ]

        # 8. Get tools for this agent
        tools = get_tools_for_agent(intent.agent)
        allowed_tool_names = get_tool_names_for_agent(intent.agent)

        # 9. ReAct Loop
        full_response_text = ""
        tool_results_log = []

        for iteration in range(self.max_iterations):
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                temperature=0.3,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )

            # Process response content blocks
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    full_response_text += block.text
                    yield self._sse("text_delta", content=block.text)
                    assistant_content.append({"type": "text", "text": block.text})

                elif block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Security: verify tool is allowed for this agent
                    if tool_name not in allowed_tool_names:
                        logger.warning(f"Tool {tool_name} not allowed for agent {intent.agent}")
                        continue

                    yield self._sse("tool_call", name=tool_name, status="started")
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": tool_name,
                        "input": tool_input,
                    })

                    # Execute tool
                    try:
                        result = await self._execute_tool(tool_name, tool_input, user, site_id)
                        tool_results_log.append({"tool": tool_name, "input": tool_input, "result": result})
                        yield self._sse("tool_result", name=tool_name, data=result)
                    except Exception as e:
                        logger.error(f"Tool execution error ({tool_name}): {e}")
                        result = {"error": str(e)}
                        yield self._sse("tool_result", name=tool_name, data={"error": str(e)})

                    # Add tool result to messages for next iteration
                    messages.append({"role": "assistant", "content": assistant_content})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }],
                    })
                    assistant_content = []

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Extract citations from RAG context
                citations = self._extract_citations(rag_context)
                if citations:
                    yield self._sse("citations", sources=citations)
                yield self._sse("done")
                break
            elif response.stop_reason != "tool_use":
                # Unexpected stop, end gracefully
                yield self._sse("done")
                break
        else:
            # Max iterations exceeded
            yield self._sse("text_delta", content="\n\n처리가 복잡하여 부분 결과를 제공합니다.")
            yield self._sse("done")

        # 10. Save conversation
        await self._save_conversation(
            user_id=user.id,
            site_id=site_id,
            conversation_id=conversation_id,
            user_message=message,
            assistant_response=full_response_text,
            context_type=intent.agent,
        )

        # 11. Audit log
        await self._log_audit(
            user=user,
            site_id=site_id,
            intent=intent,
            tool_results=tool_results_log,
            rag_chunks_used=len(rag_context.chunks),
        )

    async def _execute_tool(
        self, tool_name: str, tool_input: dict, user: User, site_id: UUID
    ) -> dict:
        """Route tool execution to the appropriate handler."""
        from app.agents.tools import menu_tools, recipe_tools, haccp_tools, dashboard_tools, work_order_tools

        # Inject site_id for multi-site isolation
        if "site_id" in tool_input:
            # Verify user has access to this site
            requested_site = UUID(tool_input["site_id"])
            if user.role not in ("ADM", "OPS") and requested_site not in (user.site_ids or []):
                return {"error": "No access to the requested site"}
        elif tool_name in ("generate_menu_plan", "generate_work_order", "generate_haccp_checklist",
                           "check_haccp_completion", "generate_audit_report", "query_dashboard"):
            tool_input["site_id"] = str(site_id)

        # Dispatch
        dispatch = {
            "generate_menu_plan": lambda: menu_tools.generate_menu_plan(self.db, created_by=user.id, **tool_input),
            "validate_nutrition": lambda: menu_tools.validate_nutrition(self.db, **tool_input),
            "tag_allergens": lambda: menu_tools.tag_allergens(self.db, **tool_input),
            "check_diversity": lambda: menu_tools.check_diversity(self.db, **tool_input),
            "search_recipes": lambda: recipe_tools.search_recipes(self.db, **tool_input),
            "scale_recipe": lambda: recipe_tools.scale_recipe(self.db, **tool_input),
            "generate_work_order": lambda: work_order_tools.generate_work_order(self.db, **tool_input),
            "generate_haccp_checklist": lambda: haccp_tools.generate_haccp_checklist(
                self.db, date_str=tool_input.pop("date", ""), **tool_input
            ),
            "check_haccp_completion": lambda: haccp_tools.check_haccp_completion(
                self.db, date_str=tool_input.pop("date", ""), **tool_input
            ),
            "generate_audit_report": lambda: haccp_tools.generate_audit_report(self.db, **tool_input),
            "query_dashboard": lambda: dashboard_tools.query_dashboard(
                self.db, date_str=tool_input.pop("date", None), **tool_input
            ),
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        return await handler()

    async def _load_history(self, conversation_id: UUID | None) -> list[dict]:
        """Load conversation history from DB."""
        if not conversation_id:
            return []
        conv = (await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )).scalar_one_or_none()
        if not conv or not conv.messages:
            return []
        return conv.messages

    async def _save_conversation(
        self,
        user_id: UUID,
        site_id: UUID,
        conversation_id: UUID | None,
        user_message: str,
        assistant_response: str,
        context_type: str,
    ):
        """Save or update conversation in DB."""
        now = datetime.now(timezone.utc).isoformat()
        new_messages = [
            {"role": "user", "content": user_message, "timestamp": now},
            {"role": "assistant", "content": assistant_response, "timestamp": now},
        ]

        if conversation_id:
            conv = (await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )).scalar_one_or_none()
            if conv:
                existing = conv.messages or []
                conv.messages = existing + new_messages
                conv.updated_at = datetime.now(timezone.utc)
                await self.db.flush()
                return

        # Create new conversation
        conv = Conversation(
            user_id=user_id,
            site_id=site_id,
            context_type=context_type,
            title=user_message[:100],
            messages=new_messages,
        )
        self.db.add(conv)
        await self.db.flush()

    async def _log_audit(
        self,
        user: User,
        site_id: UUID,
        intent: IntentResult,
        tool_results: list[dict],
        rag_chunks_used: int,
    ):
        """Record AI interaction in audit log."""
        log = AuditLog(
            user_id=user.id,
            site_id=site_id,
            action="ai_chat",
            entity_type="conversation",
            entity_id=user.id,  # placeholder
            ai_context={
                "intent": intent.intent,
                "agent": intent.agent,
                "confidence": intent.confidence,
                "tools_called": [tr["tool"] for tr in tool_results],
                "rag_chunks_used": rag_chunks_used,
                "model": settings.claude_model,
            },
        )
        self.db.add(log)
        await self.db.flush()

    @staticmethod
    def _extract_citations(rag_context) -> list[dict]:
        """Extract citation sources from RAG context."""
        if not rag_context or not rag_context.chunks:
            return []
        seen = set()
        citations = []
        for chunk in rag_context.chunks:
            title = chunk.metadata.get("title", "Unknown")
            doc_type = chunk.metadata.get("doc_type", "document")
            key = f"{title}:{doc_type}"
            if key not in seen:
                seen.add(key)
                citations.append({
                    "title": title,
                    "type": doc_type,
                    "source": chunk.metadata.get("source_file"),
                })
        return citations

    @staticmethod
    def _sse(event_type: str, **data) -> str:
        """Format an SSE event string."""
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
