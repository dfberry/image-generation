.PHONY: install test lint clean

install:
	pip install -e .
	pip install -r requirements-dev.txt
	@echo "Note: Also requires: npm install -g @mermaid-js/mermaid-cli"

test:
	python -m pytest tests/ -v --tb=short

lint:
	ruff check .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf outputs/*.png outputs/*.svg outputs/*.pdf
