.PHONY: run check reset lint

run:
	uv run python -m src.bot

check:
	uv run python scripts/check.py

reset:
	@echo "Gesprächshistorie wird nicht persistent gespeichert – einfach Bot neu starten."

lint:
	uv run ruff check src/ scripts/
