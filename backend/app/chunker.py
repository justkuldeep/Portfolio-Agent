"""Parse the knowledge-base markdown into chunks.

Rules (see the header comment in the KB file):
- one "## " heading = one chunk
- the HTML comment under the heading holds metadata and is NOT embedded
- the heading is prepended to the text so the subject travels with the chunk
"""
import re
from dataclasses import dataclass
from pathlib import Path

META_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.S)
# Trailing "---" separators or a "# " top-level heading (e.g. "# FAQ") end a chunk.
TAIL_RE = re.compile(r"(?m)^(?:---\s*|# .*)$")
METADATA_KEYS = ("type", "project", "topic", "status", "time_sensitive")


@dataclass
class Chunk:
    id: str
    title: str
    body: str
    metadata: dict

    @property
    def text(self) -> str:
        """Text that is embedded and later shown to the LLM."""
        return f"{self.title}\n\n{self.body}"


def _parse_metadata(raw: str) -> dict:
    meta = {}
    for part in raw.split("|"):
        if ":" in part:
            key, value = part.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta


def load_chunks(path: Path) -> list[Chunk]:
    content = Path(path).read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## ", content)[1:]  # drop the preamble
    chunks: list[Chunk] = []
    seen: set[str] = set()

    for section in sections:
        title, _, rest = section.partition("\n")
        title = title.strip()

        match = META_RE.search(rest)
        if not match:
            raise ValueError(f"Chunk '{title}' has no metadata comment")
        meta = _parse_metadata(match.group(1))
        chunk_id = meta.get("id")
        if not chunk_id:
            raise ValueError(f"Chunk '{title}' has no id in its metadata")
        if chunk_id in seen:
            raise ValueError(f"Duplicate chunk id: {chunk_id}")
        seen.add(chunk_id)

        body = META_RE.sub("", rest, count=1)
        body = TAIL_RE.split(body)[0].strip()
        if not body:
            raise ValueError(f"Chunk '{chunk_id}' is empty")

        # Chroma metadata values must be str/int/float/bool (no None).
        metadata = {"id": chunk_id, "title": title}
        metadata.update({k: meta.get(k, "") for k in METADATA_KEYS})
        chunks.append(Chunk(id=chunk_id, title=title, body=body, metadata=metadata))

    return chunks
