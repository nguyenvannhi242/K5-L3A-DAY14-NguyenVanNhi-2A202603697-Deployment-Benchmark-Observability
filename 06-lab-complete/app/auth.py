"""Kiểm tra API key trước khi xử lý request."""

from secrets import compare_digest

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> str:
    expected = settings.agent_api_key
    if not api_key or not expected or not compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    return api_key
