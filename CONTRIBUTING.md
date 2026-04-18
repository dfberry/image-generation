# Contributing to image-generation

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Prerequisites

- **Python 3.10+**
- **Git**
- A virtual environment tool (`venv` is built in)
- **GPU not required** — the test suite uses mocks so you can develop on CPU-only machines

## Development Setup

```bash
# Clone the repository
git clone https://github.com/dfberry/image-generation.git
cd image-generation

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (includes test tools)
pip install -r requirements-dev.txt
```

## Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_generate.py -v

# Run with short output
python -m pytest tests/
```

All tests use mock-based infrastructure — no GPU or model downloads needed.

## Linting and Formatting

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors
ruff check --fix .

# Format code
ruff format .
```

**Code style rules:**
- Line length: 120 characters
- Linter/formatter: [ruff](https://docs.astral.sh/ruff/)

## Pull Request Process

1. **Branch from `main`** using the naming convention:
   ```
   squad/{issue-number}-{kebab-case-slug}
   ```
   Example: `squad/12-add-batch-retry`

2. **Write tests first** — this project follows TDD. New features and bug fixes need tests before implementation.

3. **Ensure all tests pass** before opening a PR:
   ```bash
   python -m pytest tests/ -v
   ```

4. **Ensure lint passes**:
   ```bash
   ruff check .
   ```

5. Open a PR against `main`. Include:
   - What changed and why
   - Issue number (e.g., "Closes #12")
   - Test results summary

## Reporting Issues

Use the GitHub issue templates:

- **[Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)** — for broken behavior, errors, or regressions
- **[Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)** — for new features or improvements

## Project Structure

```
image-generation/
├── generate.py                 # Main CLI — image generation pipeline
├── generate_blog_images.sh     # Batch script — generates 5 blog images
├── requirements.txt            # Python dependencies
├── tests/                      # pytest test suite (mock-based, no GPU needed)
├── prompts/                    # Prompt library and style guides
│   └── examples.md             # Master prompt library
├── outputs/                    # Generated PNG images (1024×1024)
├── .github/                    # CI workflows, issue templates
└── .squad/                     # AI team memory and decisions
```

## Key Details

- **Image pipeline:** Stable Diffusion XL (SDXL) via HuggingFace `diffusers`
- **CLI flags:** `--prompt`, `--batch-file`, `--output`, `--steps`, `--refiner-steps`, `--guidance`, `--scheduler`, `--seed`, `--negative-prompt`, `--refine`, `--cpu`, `--lora`
- **Device support:** CUDA → MPS → CPU (automatic fallback)
- **Aesthetic:** Tropical magical-realism (Latin American folk art palette)
