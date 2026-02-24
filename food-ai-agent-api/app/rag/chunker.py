"""Text chunker - splits documents into overlapping chunks for embedding."""
import re
from dataclasses import dataclass, field

from app.rag.loader import RawDocument


@dataclass
class Chunk:
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class TextChunker:
    """RecursiveCharacterTextSplitter-style chunker optimized for Korean text."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n## ",    # Markdown H2
            "\n### ",   # Markdown H3
            "\n\n",     # Paragraph
            "\n",       # Line
            ". ",       # Sentence (English)
            "다. ",     # Sentence (Korean - 합니다, 입니다)
            "요. ",     # Sentence (Korean - 해요)
            " ",        # Word
        ]

    def chunk(self, documents: list[RawDocument]) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        for doc in documents:
            texts = self._recursive_split(doc.content, self.separators)
            merged = self._merge_with_overlap(texts)
            for idx, text in enumerate(merged):
                all_chunks.append(Chunk(
                    content=text,
                    chunk_index=idx,
                    metadata={**doc.metadata, "chunk_index": idx},
                ))
        return all_chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Split text recursively using ordered separators."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Find the best separator that exists in the text
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                result = []
                for part in parts:
                    part_with_sep = part if part == parts[0] else sep + part
                    if len(part_with_sep) <= self.chunk_size:
                        result.append(part_with_sep)
                    else:
                        # Recurse with remaining separators
                        remaining_seps = separators[separators.index(sep) + 1:]
                        if remaining_seps:
                            result.extend(self._recursive_split(part_with_sep, remaining_seps))
                        else:
                            # Force split by character
                            result.extend(self._force_split(part_with_sep))
                return [r for r in result if r.strip()]

        return self._force_split(text)

    def _force_split(self, text: str) -> list[str]:
        """Last resort: split by chunk_size characters."""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i:i + self.chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        return chunks

    def _merge_with_overlap(self, texts: list[str]) -> list[str]:
        """Merge small chunks and add overlap between chunks."""
        if not texts:
            return []

        merged: list[str] = []
        current = ""

        for text in texts:
            if len(current) + len(text) <= self.chunk_size:
                current = (current + text) if current else text
            else:
                if current:
                    merged.append(current.strip())
                current = text

        if current.strip():
            merged.append(current.strip())

        # Add overlap
        if self.chunk_overlap <= 0 or len(merged) <= 1:
            return merged

        overlapped = [merged[0]]
        for i in range(1, len(merged)):
            prev = merged[i - 1]
            overlap_text = prev[-self.chunk_overlap:] if len(prev) > self.chunk_overlap else prev
            overlapped.append(overlap_text + merged[i])

        return overlapped
