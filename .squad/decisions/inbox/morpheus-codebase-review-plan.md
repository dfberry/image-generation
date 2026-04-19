# Codebase Review Plan — image-generation

**By:** Morpheus (Lead)
**Date:** 2026-04-19
**Status:** Ready for execution

---

## 1. Codebase Inventory

Before defining review dimensions, here's the current state of what we're reviewing:

| Asset | Size | Description |
|-------|------|-------------|
| `generate.py` | 461 lines, 16 functions, 1 class | Monolithic CLI: parsing, device mgmt, model loading, inference, batch, OOM retry |
| `tests/` (11 files) | ~2,700 lines, **170 tests** | Mock-based, no GPU. conftest.py provides shared fixtures |
| `generate_blog_images.sh` | 57 lines | Batch script: builds JSON, calls `--batch-file`, cleans up |
| `prompts/examples.md` | ~25 KB | Master prompt library and style guide |
| `docs/` (3 files) | ~60 KB combined | design.md, feature-specification.md, blog-image-generation-skill.md |
| `requirements.txt` | 7 deps | diffusers, transformers, accelerate, safetensors, invisible-watermark, torch, Pillow |
| `requirements-dev.txt` | 3 deps | pytest, ruff, pytest-cov |
| `ruff.toml` | 10 lines | E/F/W/I rules, line-length 120, py310 target |
| `Makefile` | 36 lines | setup, install, test, lint, format, clean |
| `.github/workflows/tests.yml` | 57 lines | workflow_dispatch + labeled PR trigger, lint → test matrix |
| `README.md` | 108 lines | Setup, usage, options, memory model, testing |
| `CONTRIBUTING.md` | 116 lines | Dev setup, PR process, project structure |
| `CODEOWNERS` | 13 lines | All paths → @dfberry |

---

## 2. Review Dimensions

Seven dimensions, each with clear scope and acceptance criteria.

### D1: Code Quality & Architecture
**What:** Structural integrity of generate.py, function responsibility, coupling, naming, error handling patterns, adherence to ruff rules.
**Key questions:**
- Is the monolith still sustainable or is it time to extract modules?
- Are there function responsibilities that have grown beyond their original scope?
- Is the error handling hierarchy (OOMError → generate_with_retry → batch_generate) clean?
- Are there any dead code paths or unreachable branches?
- Does the code pass `ruff check .` cleanly?

### D2: SDXL Pipeline & GPU Safety
**What:** Correctness of the diffusers pipeline usage, memory management, device handling, scheduler/LoRA application, performance optimizations.
**Key questions:**
- Are all GPU memory flush points correct and complete?
- Is the try/finally cleanup truly leak-proof across all device paths (CUDA/MPS/CPU)?
- Is the torch.compile usage safe and properly guarded?
- Are the model loading parameters (dtype, variant, safety_checker) correct for each device?
- Is the 80/20 base/refiner split optimal?
- Does `enable_model_cpu_offload()` interact safely with the generator device binding?

### D3: Test Coverage & Quality
**What:** Coverage completeness, test quality, fixture hygiene, assertion correctness, edge case coverage.
**Key questions:**
- What functions/branches in generate.py have ZERO test coverage?
- Are test assertions robust (no silent tuple assertions, no `assert True`)?
- Do tests actually verify behavior or just confirm mocks were called?
- Is the conftest.py fixture set sufficient and DRY?
- Are there missing edge cases (e.g., batch with 1 item, seed=0, width=64)?
- Is pytest-cov actually being used? What's the measured line coverage?

### D4: Prompt Library & Style Consistency
**What:** Quality, consistency, and completeness of the prompt library and style guide.
**Key questions:**
- Do all prompts follow the documented style structure?
- Are the anti-text/anti-representation guardrails consistently applied?
- Are there prompts that violate the style guide's own rules?
- Is the color palette (magenta, teal, emerald, gold, coral, amber) consistently referenced?
- Are prompt lengths within the recommended 15-25 word detail range?

### D5: Documentation Accuracy
**What:** README, CONTRIBUTING, docs/, and feature-specification.md — are they accurate against the actual codebase?
**Key questions:**
- Does the README Options table match the actual CLI defaults? (e.g., README says `--steps` default 40, code says 22)
- Does the test count in README match reality? (README says 22, actual is 170)
- Does CONTRIBUTING.md reference correct test commands?
- Does docs/feature-specification.md match the actual code behavior?
- Does docs/blog-image-generation-skill.md reference correct paths and Python version? (says Python 3.14)
- Are there hardcoded paths (macOS user-specific) in docs?

### D6: Security & Supply Chain
**What:** Dependency security, secrets exposure, input validation, shell script safety.
**Key questions:**
- Are dependency version floors high enough to avoid known CVEs?
- Is there any path traversal risk in `--output` or `--batch-file`?
- Does `generate_blog_images.sh` use `set -euo pipefail` correctly?
- Is `json.load()` called safely (file handling, error handling)?
- Are there any hardcoded credentials or API keys anywhere?
- Is the CI workflow properly scoped (permissions, actor allowlists)?

### D7: CI/DevOps & Build System
**What:** CI workflow correctness, Makefile targets, dev tooling, release readiness.
**Key questions:**
- Does the CI workflow actually match what developers run locally?
- Is the Makefile usable on Windows? (uses Unix paths like `$(VENV)/bin/python`)
- Does CI run the full 170-test suite or just 22 (regression)?
- Is pytest-cov configured to generate coverage reports?
- Are there missing CI steps (e.g., format check, type check)?

---

## 3. Agent Assignments

### Phase 1 — Parallel Independent Reviews

These five reviews have no dependencies and can run simultaneously.

| Agent | Dimension | Scope | Deliverable |
|-------|-----------|-------|-------------|
| **Trinity** | D1: Code Quality | `generate.py`, `Makefile`, `ruff.toml` | Code quality findings with severity ratings |
| **Niobe** | D2: Pipeline & GPU | `generate.py` (load_base, load_refiner, generate, _apply_performance_opts, apply_scheduler, apply_lora) | Pipeline correctness report + memory safety audit |
| **Neo** | D3: Test Coverage | All 11 test files, `conftest.py`, `requirements-dev.txt` | Coverage gap analysis + test quality report |
| **Switch** | D4: Prompts | `prompts/examples.md`, `docs/blog-image-generation-skill.md` | Prompt audit with per-prompt pass/fail |
| **Trinity** | D7: CI/DevOps | `.github/workflows/tests.yml`, `Makefile`, `requirements*.txt` | CI/DevOps findings (can combine with D1 in one session) |

### Phase 2 — Documentation Review (after Phase 1)

Depends on Phase 1 findings to know what's actually true about the code.

| Agent | Dimension | Scope | Deliverable |
|-------|-----------|-------|-------------|
| **Morpheus** | D5: Documentation | `README.md`, `CONTRIBUTING.md`, `docs/feature-specification.md`, `docs/design.md`, `docs/blog-image-generation-skill.md` | Documentation accuracy report: each claim verified against code |

### Phase 3 — Security Review (after Phase 1)

Depends on Trinity's code quality review and Niobe's pipeline review to avoid duplicate findings.

| Agent | Dimension | Scope | Deliverable |
|-------|-----------|-------|-------------|
| **Neo** | D6: Security | `generate.py`, `generate_blog_images.sh`, `.github/workflows/tests.yml`, `requirements.txt` | Security checklist with pass/fail per item |

### Phase 4 — Synthesis (after all phases)

| Agent | Task | Deliverable |
|-------|------|-------------|
| **Morpheus** | Cross-cutting synthesis | Unified findings report with prioritized action items |
| **Scribe** | Logging | Session log capturing all findings and decisions |

---

## 4. Review Checklists

### 4.1 Trinity — Code Quality Checklist (D1 + D7)

**generate.py structure:**
- [ ] Count function responsibilities — is any function doing > 2 things?
- [ ] Check for code duplication between base-only and refiner paths in `generate()`
- [ ] Verify all `getattr()` calls have sensible defaults
- [ ] Check if `batch_generate()` properly forwards ALL CLI args
- [ ] Verify `main()` handles both `--prompt` and `--batch-file` correctly
- [ ] Run `ruff check .` — report any violations
- [ ] Check for any `print()` statements that should be `logging`
- [ ] Verify error messages are actionable

**CI/DevOps:**
- [ ] Does `tests.yml` install correct dependencies?
- [ ] Does the actor allowlist include all maintainers?
- [ ] Is the Makefile cross-platform? (Unix shell vs Windows)
- [ ] Does CI run lint before test? (yes — `needs: lint`)
- [ ] Is there a coverage report step? (missing?)
- [ ] Are GitHub Actions pinned to SHA or major version?

### 4.2 Niobe — Pipeline & GPU Checklist (D2)

- [ ] Verify `get_device()` detection order: CUDA → MPS → CPU
- [ ] Check `get_dtype()` returns correct dtype for each device
- [ ] Verify `load_base()` uses correct variant per device
- [ ] Verify `safety_checker = None` is intentional and documented
- [ ] Check `enable_model_cpu_offload()` is only called on MPS
- [ ] Verify `torch.compile` guard: CUDA-only, hasattr check
- [ ] Check xFormers fallback chain: xFormers → attention_slicing
- [ ] Verify scheduler config preservation in `apply_scheduler()`
- [ ] Check Karras sigmas applied only for DPMSolverMultistepScheduler
- [ ] Verify LoRA loading: null check, weight application, adapter naming
- [ ] Audit all 5 memory flush points: pre-flight, mid-refine, between-batch, finally, dynamo
- [ ] Verify latents CPU transfer in refiner path
- [ ] Check generator device binding: CPU for cpu/mps, cuda for cuda
- [ ] Verify OOM detection covers both CUDA and MPS error patterns

### 4.3 Neo — Test Coverage Checklist (D3)

**Coverage gaps — verify tests exist for:**
- [ ] `parse_args()` — all 16 CLI flags
- [ ] `_positive_int()`, `_non_negative_float()`, `_dimension()` — edge cases
- [ ] `validate_dimensions()` — valid and invalid inputs
- [ ] `get_device()` — all 4 paths (force_cpu, cuda, mps, fallback)
- [ ] `get_dtype()` — each device
- [ ] `load_base()` — each device path (cuda, mps, cpu)
- [ ] `load_refiner()` — shared components, each device
- [ ] `apply_scheduler()` — valid, invalid, Karras config
- [ ] `apply_lora()` — None, valid ID, weight setting
- [ ] `generate()` — base path, refiner path, seed handling, output path
- [ ] `generate_with_retry()` — 0 retries, 1 retry, exhausted, non-OOM
- [ ] `batch_generate()` — empty list, single item, multi item, error isolation
- [ ] `main()` — prompt mode, batch mode, file not found, invalid JSON

**Test quality:**
- [ ] Grep for `mock.assert_called(), "msg"` pattern (silent tuple bug)
- [ ] Verify no tests use `assert True` or `assert False` unconditionally
- [ ] Check all MagicMock specs match actual function signatures
- [ ] Run `pytest --co -q` to list all test names — check for naming consistency
- [ ] Run `pytest-cov` and report line coverage percentage

### 4.4 Switch — Prompt Audit Checklist (D4)

- [ ] Does every prompt start with style anchor ("Latin American folk art" or "magical realism")?
- [ ] Does every prompt mention >= 3 palette colors?
- [ ] Do prompts with human figures use silhouette/backlighting technique?
- [ ] Do prompts with signage/text include "no letters or text" guard?
- [ ] Are prompt lengths within 15-25 word detail range?
- [ ] Is the style guide internally consistent (no contradictory guidance)?
- [ ] Are the anti-pattern examples still relevant?

### 4.5 Morpheus — Documentation Accuracy Checklist (D5)

- [ ] README `--steps` default: code says 22, README says 40 → **MISMATCH**
- [ ] README `--guidance` default: code says 6.5, README says 7.5 → **MISMATCH**
- [ ] README test count: says 22 regression, actual total is 170 → **STALE**
- [ ] README Options table: missing `--batch-file`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight`
- [ ] CONTRIBUTING.md references `tests/test_generate.py` which doesn't exist → **STALE**
- [ ] blog-image-generation-skill.md says "Python 3.14" → **INCORRECT** (project targets 3.10+)
- [ ] blog-image-generation-skill.md has hardcoded macOS paths → **NON-PORTABLE**
- [ ] feature-specification.md — verify all FR-xxx requirements against code
- [ ] design.md — verify architecture claims against actual structure

### 4.6 Neo — Security Checklist (D6)

- [ ] `--output` path: any path traversal or overwrite risk?
- [ ] `--batch-file` JSON loading: does it validate structure before processing?
- [ ] `json.load()`: file handle properly closed? (yes — `with open`)
- [ ] Shell script: `set -euo pipefail` present? (yes)
- [ ] Shell script: any variable injection risks? (check `$BATCH_FILE`)
- [ ] CI: `permissions: {}` (minimal permissions — good)
- [ ] CI: actor allowlist only `diberry` and `dfberry`
- [ ] Dependencies: any known CVEs in current version ranges?
- [ ] No `.env` files or secrets in repository
- [ ] `safety_checker = None` — is disabling NSFW filter documented and intentional?

---

## 5. Proposed Skills

Three reusable skills that would benefit future reviews and ongoing development.

### Skill 1: `codebase-review`

```
.squad/skills/codebase-review/SKILL.md
```

**Purpose:** Standardized code review checklist for this project. Teaches agents what to look for in generate.py changes.

**Content:**
- Memory management verification (5 flush points)
- Device path coverage (CUDA/MPS/CPU)
- Error handling hierarchy (OOMError chain)
- CLI argument forwarding to batch_generate
- Test-first requirement per TDD directive
- Ruff compliance check

### Skill 2: `test-coverage-audit`

```
.squad/skills/test-coverage-audit/SKILL.md
```

**Purpose:** Systematic test gap analysis. Teaches agents how to assess and report on test coverage.

**Content:**
- Function-level coverage mapping technique
- Test quality patterns (assertion correctness, mock verification)
- Anti-patterns (silent tuple assertions, unconditional asserts)
- pytest-cov usage and interpretation
- Coverage threshold expectations (target: 90%+ line coverage)

### Skill 3: `doc-accuracy-check`

```
.squad/skills/doc-accuracy-check/SKILL.md
```

**Purpose:** Documentation verification against code. Teaches agents to cross-reference docs with implementation.

**Content:**
- CLI flag defaults: compare argparse defaults to README/docs tables
- Test counts: compare actual test count to documented claims
- File references: verify all mentioned paths exist
- Version claims: verify Python version, dependency versions
- Path portability: flag hardcoded OS-specific paths

---

## 6. Review Artifacts

Each reviewer produces a structured findings document.

### Finding Format

```markdown
### [FINDING-ID] — Title

**Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
**File:** path/to/file.py:L42-L55
**Dimension:** D1–D7
**Description:** What's wrong
**Evidence:** Code snippet or test output
**Recommendation:** What to do
```

### Deliverable Per Agent

| Agent | Output File | Format |
|-------|-------------|--------|
| Trinity | `.squad/decisions/inbox/trinity-code-quality-review.md` | Findings list (D1 + D7) |
| Niobe | `.squad/decisions/inbox/niobe-pipeline-review.md` | Findings list (D2) |
| Neo | `.squad/decisions/inbox/neo-test-coverage-audit.md` | Coverage table + findings (D3), then security checklist (D6) |
| Switch | `.squad/decisions/inbox/switch-prompt-audit.md` | Per-prompt pass/fail table (D4) |
| Morpheus | `.squad/decisions/inbox/morpheus-doc-accuracy-review.md` | Claim verification table (D5) |

### Synthesis Report

After all phases, Morpheus produces:

```
.squad/decisions/inbox/morpheus-codebase-review-synthesis.md
```

Contains:
- Severity summary table (count by severity across all dimensions)
- Top 10 prioritized action items
- Cross-cutting themes
- Recommendations for next sprint
- Updated Joel Test score impact

---

## 7. Execution Plan

### Orchestration Sequence

```
Phase 1 (Parallel)     Phase 2        Phase 3        Phase 4
┌──────────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Trinity: D1+D7   │   │          │   │          │   │          │
│ Niobe:   D2      │──▶│ Morpheus │──▶│ Neo: D6  │──▶│ Morpheus │
│ Neo:     D3      │   │ D5       │   │ Security │   │ Synthesis│
│ Switch:  D4      │   │ Docs     │   │          │   │ Scribe   │
└──────────────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Gate Criteria

| Gate | Required Before | Condition |
|------|----------------|-----------|
| G1 | Phase 2 starts | All Phase 1 agents have submitted findings |
| G2 | Phase 3 starts | Morpheus doc review complete (may surface code issues) |
| G3 | Phase 4 starts | All findings submitted from all phases |

### Coordinator Instructions

1. **Launch Phase 1:** Dispatch Trinity, Niobe, Neo, Switch simultaneously with their checklists above. Each agent reads their charter + history before starting.

2. **Gate G1:** Verify all four `.squad/decisions/inbox/*-review.md` files exist.

3. **Launch Phase 2:** Morpheus reads Phase 1 findings, then reviews documentation accuracy using the D5 checklist. Key advantage: Phase 1 findings tell Morpheus what the code *actually* does, so doc claims can be verified.

4. **Gate G2:** Verify `morpheus-doc-accuracy-review.md` exists.

5. **Launch Phase 3:** Neo reads Trinity's code quality findings and Niobe's pipeline findings, then runs the security checklist (D6). Key advantage: avoids duplicating issues already surfaced in D1/D2.

6. **Gate G3:** Verify all 6 deliverables exist.

7. **Launch Phase 4:** Morpheus synthesizes all findings. Scribe logs the session.

### Known Issues to Pre-Seed

These are issues I already spotted during this analysis that reviewers should confirm:

| # | Expected Finding | Dimension | Severity |
|---|-----------------|-----------|----------|
| 1 | README `--steps` default says 40, code says 22 | D5 | HIGH |
| 2 | README `--guidance` default says 6.5 in code, 7.5 in README | D5 | HIGH |
| 3 | README Options table missing 7 CLI flags | D5 | HIGH |
| 4 | README says 22 tests, actual count is 170 | D5 | MEDIUM |
| 5 | CONTRIBUTING.md references nonexistent `test_generate.py` | D5 | MEDIUM |
| 6 | blog-image-generation-skill.md says Python 3.14 | D5 | MEDIUM |
| 7 | blog-image-generation-skill.md has hardcoded macOS paths | D5 | LOW |
| 8 | Makefile uses Unix paths, won't work on Windows | D7 | MEDIUM |
| 9 | `safety_checker = None` undocumented rationale | D2 | LOW |
| 10 | pytest-cov in requirements-dev.txt but no coverage config | D3/D7 | MEDIUM |

### Estimated Effort

| Phase | Agents | Estimated Time | Notes |
|-------|--------|---------------|-------|
| Phase 1 | 4 parallel | ~5 min each | Independent, no blocking |
| Phase 2 | 1 (Morpheus) | ~5 min | Reads Phase 1 outputs |
| Phase 3 | 1 (Neo) | ~3 min | Focused security pass |
| Phase 4 | 2 (Morpheus + Scribe) | ~5 min | Synthesis + logging |
| **Total wall clock** | — | **~18 min** | Phases 2-4 sequential |

---

## 8. Success Criteria

The review is complete when:

1. ✅ All 7 dimensions have been reviewed
2. ✅ Every finding has severity, file reference, and recommendation
3. ✅ A synthesis report with prioritized action items exists
4. ✅ No CRITICAL findings remain unacknowledged
5. ✅ The review is logged in `.squad/log/` by Scribe
6. ✅ Actionable items are filed as GitHub Issues (or documented for filing)
