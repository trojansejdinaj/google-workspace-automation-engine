.PHONY: help sync format fmt lint type test check

help:
	@echo "Targets:"
	@echo "  make sync    - install deps via uv"
	@echo "  make format  - format with ruff"
	@echo "  make fmt     - alias for make format"
	@echo "  make lint    - lint with ruff"
	@echo "  make type    - typecheck with mypy"
	@echo "  make test    - run pytest"
	@echo "  make check   - run format+lint+type+test"

sync:
	uv sync

format:
	uv run ruff format .

fmt: format

lint:
	uv run ruff check .

type:
	uv run mypy .

test:
	uv run pytest

check: format lint type test
