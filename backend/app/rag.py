from . import gemini
from .config import get_settings
from .prompts import system_prompt, user_message


def _retrieval_query(question: str, history: list[dict]) -> str:
    """Short follow-ups ("what about SAISA?") borrow the previous user turn."""
    if history and len(question.split()) < 8:
        previous = [m["content"] for m in history if m["role"] == "user"]
        if previous:
            return f"{previous[-1]} {question}"
    return question


def retrieve(collection, question: str, history: list[dict], k: int | None = None) -> list[dict]:
    k = k or get_settings().top_k
    query = _retrieval_query(question, history)
    vector = gemini.embed([query], "RETRIEVAL_QUERY")[0]
    res = collection.query(
        query_embeddings=[vector],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "id": meta["id"],
            "title": meta["title"],
            "text": doc,
            "distance": dist,
            "metadata": meta,
        }
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


def _clean_history(history: list[dict]) -> list[dict]:
    history = history[-get_settings().max_history_messages :]
    while history and history[0]["role"] != "user":  # Gemini expects a user turn first
        history = history[1:]
    return history


def answer(collection, question: str, history: list[dict]) -> dict:
    history = _clean_history(history)
    passages = retrieve(collection, question, history)
    text = gemini.generate(system_prompt(), history, user_message(question, passages))
    return {
        "answer": text or "Sorry, I couldn't generate an answer. Please try again.",
        "sources": [{"id": p["id"], "title": p["title"]} for p in passages],
    }
