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

### Reproducible Builds

For reproducible builds in CI/CD environments, use `requirements.lock` which pins all dependencies to exact versions:

```bash
pip install -r requirements.lock
```

See [`requirements.lock`](requirements.lock) for the complete pinned dependency list.

## Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run a specific test file (example)
python -m pytest tests/test_cli_validation.py -v

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

## CI Actor Allowlist

The CI workflow (`.github/workflows/tests.yml`) restricts who can trigger test runs
to a known set of GitHub usernames. The check uses `github.actor` against a JSON list:

```yaml
contains(fromJSON('["diberry","dfberry"]'), github.actor)
```

### Adding a new contributor to the allowlist

1. Open `.github/workflows/tests.yml`.
2. Find the `if:` condition on the `lint` job.
3. Add the new GitHub username to the JSON array — for example, change
   `'["diberry","dfberry"]'` to `'["diberry","dfberry","new-user"]'`.
4. The username must appear in **both** `contains()` calls in that condition
   (one for `workflow_dispatch`, one for `pull_request`).
5. Commit the change to `main` (or include it in a PR that an existing
   allowlisted contributor can merge).

> **Why an allowlist?** The workflow has no `permissions:` grants beyond the
> default, but restricting the actor list prevents CI resource usage from
> unknown forks or accounts.

## GitHub Token Scopes and Permissions

### Workflow Token Requirements

This repository uses GitHub Actions with the following permission models:

#### `.github/workflows/tests.yml` — Run Tests
- **Permissions:** `{}` (empty/minimal)
- **Actions Used:** `actions/checkout`, `actions/setup-python`
- **Purpose:** Linting and unit tests on PR/manual dispatch
- **Note:** Minimal permissions are intentional — no external writes are needed

#### `.github/workflows/squad-issue-assign.yml` — Squad Issue Assign
- **Permissions:**
  - `issues: write` — to create comments and assign issues
  - `contents: read` — to read `.squad/team.md`
- **Actions Used:** `actions/checkout`, `actions/github-script`
- **Special Token:** `COPILOT_ASSIGN_TOKEN` (when assigning `@copilot` agent)
  - Scope: `repo` (full repository access)
  - Used for: Assigning the GitHub Copilot SWE agent to issues
  - Storage: GitHub Actions Secret (repo-level)
  - **Note:** This is a Personal Access Token (PAT) and should be created with minimal scopes

#### `.github/workflows/squad-triage.yml` — Squad Triage
- **Permissions:**
  - `issues: write` — to create comments and add labels
  - `contents: read` — to read `.squad/team.md` and routing rules
- **Actions Used:** `actions/checkout`, `actions/github-script`
- **Purpose:** Automated issue routing based on capability matching

#### `.github/workflows/sync-squad-labels.yml`
- **Actions Used:** `actions/checkout`
- **Purpose:** Sync squad member labels and metadata

#### `.github/workflows/squad-heartbeat.yml`
- **Actions Used:** `actions/checkout`
- **Purpose:** Periodic health check for squad workflow infrastructure

### Setting up `COPILOT_ASSIGN_TOKEN`

If you need to enable `@copilot` agent assignment:

1. Generate a Personal Access Token (PAT) from your GitHub account
2. Recommended scopes:
   - `repo` — full repository access (required for agent assignment)
3. Store as a GitHub Actions Secret named `COPILOT_ASSIGN_TOKEN` at the repository level
4. The secret will be available to workflows that explicitly request it via `github-token`

**Security Note:** This token should be rotated periodically and created with the minimum necessary scopes for the agent to function.

## Key Details

- **Image pipeline:** Stable Diffusion XL (SDXL) via HuggingFace `diffusers`
- **CLI flags:** `--prompt`, `--batch-file`, `--output`, `--steps`, `--refiner-steps`, `--guidance`, `--scheduler`, `--seed`, `--negative-prompt`, `--refine`, `--cpu`, `--lora`
- **Device support:** CUDA → MPS → CPU (automatic fallback)
- **Aesthetic:** Tropical magical-realism (Latin American folk art palette)
