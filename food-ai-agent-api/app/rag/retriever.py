"""Hybrid retriever - BM25 keyword + pgvector semantic search with RRF fusion."""
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.rag.embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    id: UUID
    content: str
    metadata: dict = field(default_factory=dict)
    score: float = 0.0
    source: str = ""  # "keyword", "vector", "fused"


class HybridRetriever:
    """Hybrid search combining BM25 keyword search and pgvector cosine similarity."""

    def __init__(self, db: AsyncSession, embedder: Embedder | None = None):
        self.db = db
        self.embedder = embedder or Embedder()
        self.rrf_k = 60  # RRF smoothing constant
        self.keyword_weight = settings.rag_keyword_weight  # 0.3
        self.vector_weight = settings.rag_vector_weight    # 0.7

    async def search(
        self,
        query: str,
        doc_types: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.rag_top_k

        # Generate query embedding
        query_embedding = await self.embedder.embed_single(query)

        # Parallel search
        keyword_results = await self._keyword_search(query, doc_types)
        vector_results = await self._vector_search(query_embedding, doc_types)

        # RRF Fusion
        fused = self._rrf_fusion(keyword_results, vector_results)

        # Return top-k with adjacent chunks
        top_chunks = fused[:top_k]
        enriched = await self._enrich_with_adjacent(top_chunks)
        return enriched

    async def _keyword_search(
        self, query: str, doc_types: list[str] | None = None, limit: int = 20
    ) -> list[tuple[UUID, str, dict, float]]:
        """BM25 keyword search using PostgreSQL Full-Text Search."""
        type_filter = ""
        params: dict = {"query": query, "limit": limit}
        if doc_types:
            type_filter = "AND doc_type = ANY(:doc_types)"
            params["doc_types"] = doc_types

        sql = sql_text(f"""
            SELECT id, content, metadata,
                   ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', :query)) AS rank
            FROM recipe_documents
            WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
            {type_filter}
            ORDER BY rank DESC
            LIMIT :limit
        """)
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        return [(row[0], row[1], row[2] or {}, float(row[3])) for row in rows]

    async def _vector_search(
        self, embedding: list[float], doc_types: list[str] | None = None, limit: int = 20
    ) -> list[tuple[UUID, str, dict, float]]:
        """Vector cosine similarity search using pgvector."""
        type_filter = ""
        params: dict = {"embedding": str(embedding), "limit": limit}
        if doc_types:
            type_filter = "AND doc_type = ANY(:doc_types)"
            params["doc_types"] = doc_types

        sql = sql_text(f"""
            SELECT id, content, metadata,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM recipe_documents
            WHERE embedding IS NOT NULL
            {type_filter}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)
        result = await self.db.execute(sql, params)
        rows = result.fetchall()
        return [(row[0], row[1], row[2] or {}, float(row[3])) for row in rows]

    def _rrf_fusion(
        self,
        keyword_results: list[tuple[UUID, str, dict, float]],
        vector_results: list[tuple[UUID, str, dict, float]],
    ) -> list[RetrievedChunk]:
        """Reciprocal Rank Fusion: score(d) = sum(1/(k + rank_i))."""
        scores: dict[UUID, float] = {}
        content_map: dict[UUID, tuple[str, dict]] = {}

        # Keyword scores (weight=0.3)
        for rank, (doc_id, content, metadata, _) in enumerate(keyword_results):
            rrf_score = self.keyword_weight * (1.0 / (self.rrf_k + rank + 1))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            content_map[doc_id] = (content, metadata)

        # Vector scores (weight=0.7)
        for rank, (doc_id, content, metadata, _) in enumerate(vector_results):
            rrf_score = self.vector_weight * (1.0 / (self.rrf_k + rank + 1))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            content_map[doc_id] = (content, metadata)

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            RetrievedChunk(
                id=doc_id,
                content=content_map[doc_id][0],
                metadata=content_map[doc_id][1],
                score=scores[doc_id],
                source="fused",
            )
            for doc_id in sorted_ids
        ]

    async def _enrich_with_adjacent(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Include adjacent chunks from the same document for better context."""
        if not chunks:
            return chunks

        enriched = []
        for chunk in chunks:
            chunk_index = chunk.metadata.get("chunk_index")
            recipe_id = chunk.metadata.get("recipe_id")
            doc_type = chunk.metadata.get("doc_type")

            if chunk_index is not None and recipe_id:
                # Fetch prev/next chunk from same document
                sql = sql_text("""
                    SELECT content FROM recipe_documents
                    WHERE recipe_id = :recipe_id
                      AND doc_type = :doc_type
                      AND metadata->>'chunk_index' IN (:prev_idx, :next_idx)
                    ORDER BY metadata->>'chunk_index'
                """)
                try:
                    result = await self.db.execute(sql, {
                        "recipe_id": str(recipe_id),
                        "doc_type": doc_type,
                        "prev_idx": str(chunk_index - 1),
                        "next_idx": str(chunk_index + 1),
                    })
                    adjacent_rows = result.fetchall()
                    if adjacent_rows:
                        adjacent_text = "\n...\n".join(r[0] for r in adjacent_rows)
                        chunk.content = f"{chunk.content}\n\n[Adjacent context]\n{adjacent_text}"
                except Exception:
                    pass  # Adjacent enrichment is best-effort

            enriched.append(chunk)
        return enriched
