FROM python:3.11-slim AS builder

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd --system agent && useradd --system --gid agent --create-home agent

WORKDIR /app
ENV PYTHONUSERBASE=/home/agent/.local \
    PATH=/home/agent/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /root/.local /home/agent/.local
COPY app/ app/
COPY utils/ utils/

USER agent
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + (os.getenv('PORT') or '8000') + '/health', timeout=2)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${AGENT_WORKERS:-1}"]
