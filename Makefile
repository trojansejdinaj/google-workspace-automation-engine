.PHONY: help sync format lint type test check

help:
	@echo "Targets:"
	@echo "  make sync    - install deps via uv"
	@echo "  make format  - format with ruff"
	@echo "  make lint    - lint with ruff"
	@echo "  make type    - typecheck with mypy"
	@echo "  make test    - run pytest"
	@echo "  make check   - run format+lint+type+test"

sync:
	uv sync

format:
	uv run ruff format .

lint:
	uv run ruff check .

type:
	uv run mypy .

test:
	uv run pytest

check: format lint type test
