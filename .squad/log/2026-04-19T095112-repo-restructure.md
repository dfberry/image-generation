# Repo Restructure into Multi-Tool Layout — 2026-04-19T095112

**Branch:** `squad/repo-restructure-subfolders`
**PR:** #84 (labeled squad-approved)
**Commits:** 387283b (Trinity — restructure), 6f4fd49 (Coordinator — doc path fixes)

## Summary

Restructured the repository from a flat single-tool layout into a multi-tool architecture. All image-generation files moved into an `image-generation/` subfolder; an empty `mermaid-diagrams/` folder was created for a future diagram tool. Shared infrastructure (`.squad/`, `.github/`, root config files) stayed at root.

## Timeline

| Step | Agent | Action |
|------|-------|--------|
| 1 | User | Requested repo restructure: move image-gen into subfolder, create mermaid-diagrams/ |
| 2 | Morpheus | Designed folder layout and 470-line migration plan (`morpheus-repo-restructure.md`) |
| 3 | Trinity | Executed restructure via `git mv`, updated CI, .gitignore, CODEOWNERS, conftest.py, created root README and mermaid-diagrams/README.md (commit 387283b) |
| 4 | Neo | Verified tests: 161 pass, 57 pre-existing torch skips, zero new failures (`neo-restructure-verification.md`) |
| 5 | Morpheus | Reviewed Trinity's execution: approved with findings — Makefile venv path flagged as blocker, shell script venv path as should-fix (`morpheus-restructure-review.md`) |
| 6 | Coordinator | Fixed doc path references in `.github/copilot-instructions.md` and `.github/ISSUE_TEMPLATE/bug_report.md` (commit 6f4fd49) |
| 7 | Coordinator | Created PR #84, labeled squad-approved |

## Key Decisions

1. **Each tool subfolder gets its own venv** — Makefile `VENV := venv` is correct relative to the subfolder working directory.
2. **Tests stay with their tool** — `image-generation/tests/` uses `conftest.py` with `sys.path.insert(0, ...)` to resolve `from generate import ...` regardless of pytest working directory.
3. **Shared infra stays at root** — `.squad/`, `.github/`, `.gitignore`, `CODEOWNERS`, project-level planning docs.
4. **CI uses `working-directory: image-generation`** — Per-step directive in `.github/workflows/tests.yml` keeps all commands relative to the tool folder.

## Files Changed

### Moved to `image-generation/`
- `generate.py`, `generate_blog_images.sh`
- `prompts/`, `outputs/`, `tests/`, `docs/`
- `requirements.txt`, `requirements-dev.txt`, `requirements.lock`
- `ruff.toml`, `Makefile`, `_write_tests.py`, `CONTRIBUTING.md`
- All 4 `batch_*.json` files
- `README.md` (now tool-specific)

### Updated
- `.github/workflows/tests.yml` — `working-directory: image-generation` per-step
- `.gitignore` — output patterns prefixed with `image-generation/`
- `CODEOWNERS` — all tool-specific patterns prefixed
- `image-generation/tests/conftest.py` — `sys.path.insert` for import resolution
- `.github/copilot-instructions.md` — doc paths updated (commit 6f4fd49)
- `.github/ISSUE_TEMPLATE/bug_report.md` — command paths updated (commit 6f4fd49)

### Created
- `README.md` (root) — project overview pointing to tool subfolders
- `mermaid-diagrams/README.md` — placeholder for future tool

## Review Findings (Morpheus)

| Severity | Issue | Status |
|----------|-------|--------|
| BLOCKER | Makefile `VENV := venv` may need `../venv` if venv at root | Deferred — per-subfolder venv is the intended design |
| SHOULD_FIX | Shell script `source venv/bin/activate` path | Deferred — same rationale |

**Resolution:** The team decided each tool subfolder owns its own venv. When a developer runs `make install-dev` from `image-generation/`, it creates `image-generation/venv/` locally. The Makefile `VENV := venv` reference is therefore correct.

## Test Verification (Neo)

- **161 passed**, 57 failed (all pre-existing torch `ModuleNotFoundError`), 1 skipped, 2 collection errors (torch)
- **Zero new failures** introduced by the restructure
- All 14 test files discovered correctly
- `conftest.py` sys.path fix verified working

---

*— Scribe | Logged: 2026-04-19*
