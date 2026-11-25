"""Production AI agent cho Part 6."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StringConstraints
from redis.exceptions import RedisError

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "lvl": record.levelname,
            "event": record.getMessage(),
        }
        for field in ("environment", "method", "path", "status", "ms", "error_type"):
            if field in record.__dict__:
                payload[field] = record.__dict__[field]
        return json.dumps(payload)


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("startup", extra={"environment": settings.environment})
    try:
        yield
    finally:
        r.close()
        logger.info("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    user_id: str | None = None


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:
        logger.error("request_failed", extra={"error_type": type(error).__name__})
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})

    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": getattr(request.scope.get("route"), "path", None),
            "status": response.status_code,
            "ms": round((perf_counter() - started) * 1000, 2),
        },
    )
    return response


@app.exception_handler(RedisError)
async def redis_unavailable(_: Request, exc: RedisError) -> JSONResponse:
    logger.warning("redis_unavailable", extra={"error_type": type(exc).__name__})
    return JSONResponse(status_code=503, content={"detail": "Redis unavailable"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}


@app.post("/ask")
def ask(body: AskRequest, api_key: Annotated[str, Depends(verify_api_key)]):
    check_rate_limit(api_key)
    check_budget()
    answer = llm_ask(body.question)

    # Mock LLM không trả token usage, dùng cùng cách ước tính như ví dụ Part 4.
    input_tokens = len(body.question.split()) * 2
    output_tokens = len(answer.split()) * 2
    record_cost(input_tokens, output_tokens)
    return {"question": body.question, "answer": answer}
