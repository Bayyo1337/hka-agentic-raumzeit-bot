.PHONY: run check reset lint clean test-e2e

run:
	@echo "🧹 Bereinige Cache..."
	@find src scripts -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "🔄 Synchronisiere Abhängigkeiten..."
	@uv sync --quiet
	@uv run python -c "import telegram, pydantic_settings, httpx, litellm" 2>/dev/null || \
		(echo "Venv korrupt – wird neu aufgebaut..." && rm -rf .venv && uv sync)
	@echo "🚀 Starte Raumzeit Bot..."
	@uv run python -m src.bot

check:
	uv run python scripts/check.py

test-e2e:
	PYTHONPATH=. uv run pytest tests/test_e2e.py -v

reset:
	@echo "Gesprächshistorie wird nicht persistent gespeichert – einfach Bot neu starten."

lint:
	uv run ruff check src/ scripts/

clean:
	find src scripts -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
