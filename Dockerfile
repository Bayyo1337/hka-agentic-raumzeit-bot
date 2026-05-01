FROM python:3.11-slim

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies zuerst (Layer-Caching) – uv.lock für reproduzierbare Builds
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Assets und Source
COPY assets/ assets/
COPY src/ src/
COPY scripts/setup/generate_maps.py scripts/setup/generate_maps.py

# Karten beim Build generieren (benötigt assets/HKA_Lageplan_A4.pdf)
RUN uv run python scripts/setup/generate_maps.py

# .env wird zur Laufzeit per Volume oder ENV-Vars gesetzt
ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "python", "-m", "src.bot"]
