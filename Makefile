.PHONY: run check reset lint clean

run:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	uv sync --quiet
	uv run python -m src.bot

check:
	uv run python scripts/check.py

reset:
	@echo "Gesprächshistorie wird nicht persistent gespeichert – einfach Bot neu starten."

lint:
	uv run ruff check src/ scripts/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
