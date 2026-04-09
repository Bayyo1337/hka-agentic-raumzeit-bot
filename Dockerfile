FROM python:3.11-slim

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies zuerst (Layer-Caching)
COPY pyproject.toml .
RUN uv sync --no-dev

# Source
COPY src/ src/

# .env wird zur Laufzeit per Volume oder ENV-Vars gesetzt
ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "src.bot"]
