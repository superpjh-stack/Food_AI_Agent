"""RAG pipeline orchestration - ingest documents and retrieve context."""
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.orm.recipe import RecipeDocument
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.loader import DocumentLoader
from app.rag.retriever import HybridRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Retrieved context ready to inject into system prompt."""
    chunks: list[RetrievedChunk] = field(default_factory=list)
    formatted_text: str = ""
    total_tokens_estimate: int = 0

    def to_prompt_section(self) -> str:
        if not self.chunks:
            return "[검색된 내부 문서 없음]"
        return self.formatted_text


class RAGPipeline:
    """Orchestrates document ingestion and context retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.loader = DocumentLoader()
        self.chunker = TextChunker(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        )
        self.embedder = Embedder()
        self.retriever = HybridRetriever(db, self.embedder)

    async def ingest_document(
        self,
        file_path: str,
        doc_type: str,
        recipe_id: UUID | None = None,
        title: str | None = None,
    ) -> int:
        """Load, chunk, embed, and store a document. Returns number of chunks stored."""
        # 1. Load
        docs = await self.loader.load(file_path, doc_type=doc_type)
        if not docs:
            logger.warning(f"No content extracted from {file_path}")
            return 0

        # 2. Chunk
        chunks = self.chunker.chunk(docs)
        if not chunks:
            return 0

        # 3. Embed
        texts = [c.content for c in chunks]
        embeddings = await self.embedder.embed_batch(texts)

        # 4. Store - delete existing chunks for same doc first (re-index)
        if recipe_id:
            existing = await self.db.execute(
                select(RecipeDocument).where(
                    RecipeDocument.recipe_id == recipe_id,
                    RecipeDocument.doc_type == doc_type,
                )
            )
            for row in existing.scalars().all():
                await self.db.delete(row)

        doc_title = title or docs[0].metadata.get("title", "Untitled")

        for chunk, embedding in zip(chunks, embeddings):
            record = RecipeDocument(
                recipe_id=recipe_id,
                doc_type=doc_type,
                title=doc_title,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                metadata_={
                    "source_file": chunk.metadata.get("source_file"),
                    "doc_type": doc_type,
                    "recipe_id": str(recipe_id) if recipe_id else None,
                    "chunk_index": chunk.chunk_index,
                },
                embedding=embedding,
            )
            self.db.add(record)

        await self.db.flush()
        logger.info(f"Ingested {len(chunks)} chunks from {file_path} (doc_type={doc_type})")
        return len(chunks)

    async def retrieve(
        self,
        query: str,
        doc_types: list[str] | None = None,
        top_k: int | None = None,
    ) -> RAGContext:
        """Retrieve relevant context for a query."""
        chunks = await self.retriever.search(query, doc_types=doc_types, top_k=top_k)

        formatted = self._format_context(chunks)
        token_estimate = len(formatted) // 3  # rough estimate: ~3 chars per token for Korean

        return RAGContext(
            chunks=chunks,
            formatted_text=formatted,
            total_tokens_estimate=token_estimate,
        )

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        """Format retrieved chunks into a prompt-ready string."""
        if not chunks:
            return ""

        sections = []
        for i, chunk in enumerate(chunks, 1):
            title = chunk.metadata.get("title", "Unknown")
            doc_type = chunk.metadata.get("doc_type", "document")
            source_file = chunk.metadata.get("source_file", "")
            header = f"--- 검색 결과 {i}: {title} (유형: {doc_type}"
            if source_file:
                header += f", 출처: {source_file}"
            header += f", 관련도: {chunk.score:.4f}) ---"
            sections.append(f"{header}\n{chunk.content}")

        return "\n\n".join(sections)
