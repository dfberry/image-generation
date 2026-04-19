.DEFAULT_GOAL := all

VENV := venv

# Detect OS and set path separators
ifeq ($(OS),Windows_NT)
    PYTHON := $(VENV)\Scripts\python
    PIP := $(VENV)\Scripts\pip
    ACTIVATE := $(VENV)\Scripts\activate.bat
else
    PYTHON := $(VENV)/bin/python
    PIP := $(VENV)/bin/pip
    ACTIVATE := $(VENV)/bin/activate
endif

.PHONY: all setup install install-dev test lint format clean

all: setup lint test

setup: $(ACTIVATE) install-dev

$(ACTIVATE):
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
ifeq ($(OS),Windows_NT)
	if exist __pycache__ rmdir /s /q __pycache__
	if exist .pytest_cache rmdir /s /q .pytest_cache
	if exist .ruff_cache rmdir /s /q .ruff_cache
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
else
	rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
endif
