.DEFAULT_GOAL := all

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: all setup install install-dev test lint format clean

all: setup lint test

setup: $(VENV)/bin/activate install-dev

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
