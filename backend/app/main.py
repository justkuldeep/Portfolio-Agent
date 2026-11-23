import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from . import rag
from .config import get_settings
from .store import ensure_index

log = logging.getLogger("portfolio-rag")
settings = get_settings()


def client_ip(request: Request) -> str:
    # Behind Render/Vercel proxies the real IP is the first X-Forwarded-For entry.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.collection = ensure_index()
    log.info("Index ready: %s chunks", app.state.collection.count())
    yield


app = FastAPI(title="Kuldeep Soni Portfolio RAG API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1500)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=settings.max_question_chars)
    history: list[Message] = Field(default_factory=list, max_length=12)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be blank")
        return v


class Source(BaseModel):
    id: str
    title: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/health")
def health():
    return {"status": "ok", "chunks": app.state.collection.count()}


@app.post("/ask", response_model=AskResponse)
@limiter.limit(settings.rate_limit)
def ask(request: Request, body: AskRequest):
    try:
        return rag.answer(
            app.state.collection,
            body.question,
            [m.model_dump() for m in body.history],
        )
    except Exception:
        log.exception("ask failed")
        raise HTTPException(
            status_code=502,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        )
