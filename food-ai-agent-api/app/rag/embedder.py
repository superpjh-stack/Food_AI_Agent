"""Embedding generator using OpenAI text-embedding-3-small."""
import asyncio
import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    """Generate embeddings via OpenAI API with batch processing."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.batch_size = 100

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimension,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in batches of 100."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                        dimensions=self.dimension,
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(f"Embedding failed after {max_retries} retries: {e}")
                        raise
                    wait_time = 2 ** retry_count
                    logger.warning(f"Embedding retry {retry_count}/{max_retries}, waiting {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)

        return all_embeddings
