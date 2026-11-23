"""Thin wrapper around the Gemini API (embeddings + generation)."""
from functools import lru_cache

from google import genai
from google.genai import types

from .config import get_settings

EMBED_BATCH = 50


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    """task_type: RETRIEVAL_DOCUMENT for chunks, RETRIEVAL_QUERY for questions."""
    s = get_settings()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        resp = _client().models.embed_content(
            model=s.embedding_model,
            contents=texts[i : i + EMBED_BATCH],
            config=types.EmbedContentConfig(
                task_type=task_type, output_dimensionality=s.embedding_dim
            ),
        )
        vectors.extend(e.values for e in resp.embeddings)
    return vectors


def generate(system: str, history: list[dict], user_message: str) -> str:
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in history
    ]
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )
    resp = _client().models.generate_content(
        model=get_settings().gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=1024,
        ),
    )
    return (resp.text or "").strip()
