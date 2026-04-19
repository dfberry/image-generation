# Implementation Plan — Issues #17–#62

> **Author:** Morpheus (Lead)
> **Date:** 2026-07-26
> **Status:** Ready for execution
> **Scope:** 46 GitHub issues from codebase review (7 P0, 10 P1, 13 P2, 16 P3)

---

## Strategy

Two key insights shape this plan:

1. **Move the unblocking P1 (#32, lazy imports) into Batch 1.** It has zero dependencies and unblocks #27 (stale test patches). Without this, P1 needs 3 batches. With it, all P0+P1 completes in 2 batches.

2. **Batch by agent, not by issue number.** Each agent gets one PR per batch. Multiple small issues go in a single PR when they touch related files or share a theme. This minimizes merge conflicts and review overhead.

**Governance:** Per the TDD directive in `decisions.md`, all code changes require test-first approach on a PR branch with team sign-off. Doc-only PRs are exempt from TDD but still need review.

---

## Batch 1 — P0 + Unblocking P1 (No Dependencies)

> **Goal:** Fix all user-facing documentation lies, close the security hole, fix the public API device bug, and unblock test collection for Batch 2.
>
> **All 4 PRs run in parallel. Zero cross-PR dependencies.**

### PR-A — Doc Fixes Batch (Morpheus)

| Field | Value |
|-------|-------|
| **Issues** | #17 (README defaults + missing flags), #19 (README test count 22→170), #21 (Python 3.14→3.10+ in skill doc) |
| **Branch** | `squad/17-readme-doc-fixes` |
| **Files** | `README.md`, `docs/blog-image-generation-skill.md` |
| **Effort** | S (all three are text-only fixes) |
| **TDD** | Exempt (doc-only) |
| **Rationale** | Rule 4 — doc fixes batched into one PR. All three fix incorrect information that every user sees. Single source of truth: `docs/feature-specification.md` §4.1 for CLI defaults and flags. |

**Acceptance criteria:**
- [ ] README Options table shows correct defaults: `--steps 22`, `--guidance 6.5`, `--width 1024`, `--height 1024`
- [ ] All 16 CLI flags documented in README Options table
- [ ] README states 170 tests across 11 files (not "22 tests")
- [ ] Skill doc says Python 3.10+ (not 3.14)

---

### PR-B — Security + Device Fix (Trinity)

| Field | Value |
|-------|-------|
| **Issues** | #20 (directory traversal path sanitization), #23 (batch_generate default device → auto-detect) |
| **Branch** | `squad/20-security-and-device-fix` |
| **Files** | `generate.py` |
| **Effort** | S + S |
| **TDD** | Required — write tests for path traversal rejection and device auto-detection before fixing |
| **Rationale** | Both are small `generate.py` changes. #20 is security-critical (P0-04). #23 is a one-line API defect (P0-07). Grouping avoids two back-to-back PRs touching the same file. |

**Acceptance criteria:**
- [ ] `batch_generate()` rejects output paths containing `..` or absolute paths outside project root
- [ ] `batch_generate()` defaults to `detect_device()` result, not hardcoded `"mps"`
- [ ] Tests prove traversal paths like `../../etc/passwd` are rejected
- [ ] Tests prove device auto-detection works on CPU (the CI environment)

**Implementation notes for Trinity:**
- For #20: Validate `output` field in each batch item. Reject if `os.path.isabs(output)` or `".." in Path(output).parts`. Raise `ValueError` with clear message.
- For #23: Change default parameter from `device="mps"` to `device=None`, then `device = device or detect_device()` at function entry.

---

### PR-C — Prompt Fixes (Switch)

| Field | Value |
|-------|-------|
| **Issues** | #18 (sync shell script prompts with canonical library), #22 (rewrite figure prompts for silhouette compliance) |
| **Branch** | `squad/18-prompt-sync-and-figures` |
| **Files** | `generate_blog_images.sh`, `prompts/examples.md`, potentially `batch_blog_images.json` |
| **Effort** | S + M |
| **TDD** | Exempt (prompt content, not code logic) |
| **Rationale** | Rule 5 — prompt fixes batched by agent. Both address Theme A (stale satellite files) and Theme D (figure style violations). |

**Acceptance criteria:**
- [ ] All 5 shell script prompts include `magical realism` style anchor and `no text, no lettering` guard
- [ ] Shell script prompts match canonical versions in `prompts/examples.md`
- [ ] Prompts 03, 04 and variations V04, V05 use silhouette/backlighting for human figures
- [ ] No visible arm/hand action verbs in figure prompts (no "gesturing", "crossing", "leaning", "passing")

---

### PR-D — Lazy Imports for Test Collection (Neo)

| Field | Value |
|-------|-------|
| **Issues** | #32 (P1-09 — move module-level `import diffusers` to lazy/deferred) |
| **Branch** | `squad/32-lazy-diffusers-import` |
| **Files** | `generate.py` |
| **Effort** | M |
| **TDD** | Required — verify all 11 test modules collect without diffusers installed |
| **Rationale** | **Critical path item.** Moving this from Batch 2 to Batch 1 saves an entire batch cycle. #27 (stale test patches) and #31 (mock specs) both need test collection to work first. Currently 9/11 test files fail to collect without the GPU stack. |

**Acceptance criteria:**
- [ ] `generate.py` does not import `diffusers` or `torch` at module level
- [ ] All imports moved inside the functions that use them
- [ ] All 170 existing tests still pass
- [ ] `pytest --collect-only tests/` succeeds in CI (CPU-only, no diffusers)

**Implementation notes for Neo:**
- Move `import diffusers`, `import torch`, `from diffusers import ...` from module top to inside `generate()`, `batch_generate()`, and `detect_device()`.
- Keep `import argparse`, `import os`, `import json`, `from pathlib import Path` at top (stdlib, always available).
- The `SUPPORTED_SCHEDULERS` list at module level will need to become a function or lazy constant.

**Merge order note:** PR-D touches `generate.py`. PR-B also touches `generate.py`. If both land in Batch 1, **merge PR-B first** (smaller, surgical changes), then PR-D (larger refactor that may need rebase). Alert Trinity and Neo to coordinate.

---

## Batch 2 — Remaining P1 (All Batch 1 Dependencies Satisfied)

> **Goal:** Complete all P1 items. Security → validation → overrides chain is now unblocked. Test patches can proceed because lazy imports landed.
>
> **All 4 PRs run in parallel. Each depends only on Batch 1 completion.**

### PR-E — Input Validation Hardening (Trinity)

| Field | Value |
|-------|-------|
| **Issues** | #24 (scheduler whitelist), #29 (batch schema validation), #30 (per-item overrides) |
| **Branch** | `squad/24-input-validation-hardening` |
| **Files** | `generate.py` |
| **Effort** | S + S + S |
| **TDD** | Required |
| **Depends on** | PR-B (#20 path sanitization) and PR-D (#32 lazy imports) from Batch 1 |
| **Rationale** | These three form a natural group: all harden `batch_generate()` input handling. #29 depends on #20 (Rule 2). #30 depends on #23 (Rule 3). Scheduler whitelist (#24) is same trust boundary. |

**Acceptance criteria:**
- [ ] `--scheduler` values validated against `SUPPORTED_SCHEDULERS` list; unknown names raise `ValueError`
- [ ] Batch JSON entries validated for required keys (`prompt`, `output`) and correct types before processing
- [ ] `refiner_steps` and `scheduler` overridable per-item in batch JSON (consistent with existing `lora`/`lora_weight` overrides)
- [ ] Malformed batch JSON produces clear error message, not `KeyError` stack trace

---

### PR-F — Internal Doc + Path Fixes (Morpheus)

| Field | Value |
|-------|-------|
| **Issues** | #25 (CONTRIBUTING.md test file ref), #26 (history.md flag names + file refs), #33 (hardcoded macOS paths in skill doc) |
| **Branch** | `squad/25-internal-doc-fixes` |
| **Files** | `CONTRIBUTING.md`, `.squad/agents/morpheus/history.md` (or project history), `docs/blog-image-generation-skill.md` |
| **Effort** | S + S + S |
| **TDD** | Exempt (doc-only) |
| **Depends on** | PR-A (Batch 1) to avoid merge conflicts on overlapping doc files |
| **Rationale** | All three fix internal documentation that misleads contributors or agents. Batched for same reason as PR-A. |

**Acceptance criteria:**
- [ ] CONTRIBUTING.md references correct test file path (not nonexistent `tests/test_generate.py`)
- [ ] history.md uses correct flag names: `--refine` not `--refiner`, `--cpu` not `--device`
- [ ] history.md doesn't reference nonexistent `regen_fix.sh`
- [ ] Skill doc uses generic paths, not `/Users/diberry/...` macOS paths

---

### PR-G — Test Patch Fixes + Mock Specs (Neo)

| Field | Value |
|-------|-------|
| **Issues** | #27 (fix stale test patches in test_batch_generation.py), #31 (add `spec=` to critical mocks) |
| **Branch** | `squad/27-fix-test-patches-and-mocks` |
| **Files** | `tests/test_batch_generation.py`, potentially other test files |
| **Effort** | S + M |
| **TDD** | N/A (these ARE test fixes) |
| **Depends on** | PR-D (#32 lazy imports) from Batch 1 — tests must collect first |
| **Rationale** | Rule 1 — #32 (lazy imports) must come before #27 (stale patches). Both #27 and #31 improve test reliability and are naturally co-located in test files. |

**Acceptance criteria:**
- [ ] `test_batch_generation.py` patches `generate_with_retry` (not `generate.generate`)
- [ ] All 17 affected tests actually exercise the batch code path
- [ ] Critical mocks use `spec=` parameter (at minimum: pipeline mocks, scheduler mocks, batch_generate mocks)
- [ ] No mock attribute typos pass silently (verified by intentional typo → test failure)

---

### PR-H — Pen-and-Ink Aesthetic Decision (Switch)

| Field | Value |
|-------|-------|
| **Issues** | #28 (document or integrate pen-and-ink batch file aesthetic) |
| **Branch** | `squad/28-pen-and-ink-aesthetic` |
| **Files** | `batch_blog_images.json`, `batch_blog_images_v2.json`, `prompts/examples.md` |
| **Effort** | M |
| **TDD** | Exempt (prompt/doc content) |
| **Depends on** | PR-C (Batch 1) to avoid prompt file conflicts |
| **Rationale** | This is a **squad decision candidate** (see synthesis §6). Switch should propose one of: (a) add pen-and-ink as official alternative style in style guide, (b) migrate batch files to canonical tropical aesthetic, or (c) remove batch files. Write decision to `.squad/decisions/inbox/`. |

**Acceptance criteria:**
- [ ] Decision documented in `.squad/decisions/inbox/switch-pen-and-ink-decision.md`
- [ ] Batch files either aligned with decision or removed
- [ ] If kept: pen-and-ink style rules documented in `prompts/examples.md`
- [ ] If removed: batch files deleted, README updated

---

## Batch 1–2 Summary

```
Batch 1 (parallel)          Batch 2 (parallel, after Batch 1)
┌─────────────────────┐     ┌────────────────────────────────┐
│ PR-A Morpheus       │     │ PR-E Trinity                   │
│ #17+#19+#21 docs    │────→│ #24+#29+#30 validation         │
│                     │     │ (depends on PR-B, PR-D)        │
│ PR-B Trinity        │──┐  │                                │
│ #20+#23 security    │  │  │ PR-F Morpheus                  │
│                     │  ├─→│ #25+#26+#33 internal docs      │
│ PR-C Switch         │  │  │ (depends on PR-A)              │
│ #18+#22 prompts     │──┤  │                                │
│                     │  │  │ PR-G Neo                       │
│ PR-D Neo            │  ├─→│ #27+#31 test fixes             │
│ #32 lazy imports    │──┘  │ (depends on PR-D)              │
│                     │     │                                │
│                     │     │ PR-H Switch                    │
│                     │     │ #28 pen-and-ink                 │
│                     │     │ (depends on PR-C)              │
└─────────────────────┘     └────────────────────────────────┘

Issues resolved: 7 P0 + 10 P1 = 17 issues in 2 batches, 8 PRs
```

---

## Batch 3 — P2 (Next Sprint)

> **Goal:** Quality, consistency, and coverage improvements. All items are independent of each other. Run all PRs in parallel.
>
> **Depends on:** Batches 1–2 complete (especially lazy imports and helper extraction assumptions).

### PR-I — CI Improvements (Trinity)

| Field | Value |
|-------|-------|
| **Issues** | #34 (add `--cov` to CI pytest), #41 (document CI actor allowlist maintenance) |
| **Branch** | `squad/34-ci-coverage-and-docs` |
| **Files** | `.github/workflows/tests.yml`, `CONTRIBUTING.md` or `docs/` |
| **Effort** | S + S |

### PR-J — Doc Quality Pass (Morpheus)

| Field | Value |
|-------|-------|
| **Issues** | #37 (fix skill doc example prompts — anchor + figure violations), #45 (remove stale file from design.md layout) |
| **Branch** | `squad/37-doc-quality-pass` |
| **Files** | `docs/blog-image-generation-skill.md`, `docs/design.md` |
| **Effort** | M + S |

### PR-K — Test Coverage Expansion (Neo)

| Field | Value |
|-------|-------|
| **Issues** | #43 (unit tests for `_positive_int()` and `_non_negative_float()`), #44 (tests for `--seed`, `--output`, `--refine`, `--refiner-steps`) |
| **Branch** | `squad/43-validator-and-cli-tests` |
| **Files** | `tests/test_cli.py` or new test files |
| **Effort** | S + S |

### PR-L — Prompt Quality Fixes (Switch)

| Field | Value |
|-------|-------|
| **Issues** | #35 (style anchor "aesthetic"→"style"), #36 (add missing palette colors to V01, V03), #38 (standardize negative prompts across batch files) |
| **Branch** | `squad/35-prompt-quality-fixes` |
| **Files** | `prompts/examples.md`, `batch_blog_images.json`, `batch_blog_images_v2.json` |
| **Effort** | S + S + S |

### PR-M — Safety Checker Comment (Niobe)

| Field | Value |
|-------|-------|
| **Issues** | #42 (add comment explaining `safety_checker = None` in generate.py) |
| **Branch** | `squad/42-safety-checker-comment` |
| **Files** | `generate.py` |
| **Effort** | S |

### Batch 3 Overflow — Trinity Large Items (Sequential After PR-I)

These are larger Trinity items that should be **separate PRs**, done after PR-I:

| PR | Issue | Branch | Effort | Notes |
|----|-------|--------|--------|-------|
| PR-N | #39 — Extract `generate()` helpers | `squad/39-extract-helpers` | M | Significant refactor. Break `generate()` into `load_base()`, `run_inference()`, `run_refiner()` helpers. TDD required. |
| PR-O | #40 — Makefile cross-platform | `squad/40-makefile-cross-platform` | M | Either add PowerShell equivalents or document Makefile as Linux/macOS only. |
| PR-P | #46 — Pin HuggingFace model revisions | `squad/46-pin-model-revisions` | S | Add `revision=` SHA to all `from_pretrained()` calls. Research current stable SHAs first. |

**Recommended order:** PR-I → PR-N → PR-P → PR-O (coverage first, then refactor under coverage, then pin models, then tooling).

---

## Batch 4 — P3 (Backlog)

> **Goal:** Polish, consistency, and hardening. All items are independent (Rule 6). No ordering constraints. Execute as capacity allows.

### Agent Groupings

**Trinity (8 issues) — 3 PRs:**

| PR | Issues | Branch | Theme |
|----|--------|--------|-------|
| PR-Q | #47 (logging module), #48 (hoist shared code), #49 (simplify guards) | `squad/47-code-quality-cleanup` | Code quality — all touch `generate.py` internals |
| PR-R | #53 (python vs python3), #54 (requirements.lock) | `squad/53-build-hygiene` | Build/tooling hygiene |
| PR-S | #56 (SHA-pin Actions), #57 (LoRA trust docs), #59 (PAT scope docs) | `squad/56-supply-chain-and-docs` | Supply chain + security docs |

**Neo (3 issues) — 1 PR:**

| PR | Issues | Branch | Theme |
|----|--------|--------|-------|
| PR-T | #55 (remaining test coverage), #61 (remove commented lines), #62 (pytest.fail) | `squad/55-test-hygiene` | Test cleanup + coverage gaps |

**Switch (1 issue) — 1 PR:**

| PR | Issues | Branch | Theme |
|----|--------|--------|-------|
| PR-U | #60 (skill doc style anchor variant) | `squad/60-skill-doc-anchor` | Prompt/doc polish |

**Niobe (4 issues) — 1 PR:**

| PR | Issues | Branch | Theme |
|----|--------|--------|-------|
| PR-V | #50 (cuda cache guard), #51 (mps hasattr), #52 (torch.compile fullgraph), #58 (safety_checker docs) | `squad/50-pipeline-consistency` | Pipeline style consistency — all touch `generate.py` torch/device patterns |

---

## Execution Timeline

```
Week 1:  Batch 1 — 4 PRs parallel (P0 + #32)
         Merge order: PR-A, PR-C, PR-B, PR-D (PR-B before PR-D for generate.py)

Week 2:  Batch 2 — 4 PRs parallel (remaining P1)
         All Batch 1 merged before starting

Week 3:  Batch 3 — 5 PRs parallel + 3 sequential Trinity items (P2)

Week 4+: Batch 4 — 6 PRs as capacity allows (P3 backlog)
```

## Risk Register

| Risk | Mitigation |
|------|------------|
| **PR-B and PR-D both touch `generate.py` in Batch 1** | Merge PR-B first (surgical 2-line changes). Neo rebases PR-D after. |
| **Lazy import refactor (#32) breaks existing tests** | Neo runs full `pytest tests/ -v` in PR-D CI. If failures, fix in same PR. |
| **Pen-and-ink decision (#28) stalls** | Switch writes decision doc. If no user input in 3 days, default to "migrate to canonical style." |
| **Trinity's P2 refactor (#39) creates merge conflicts for P3** | Merge #39 before any P3 Trinity PRs. P3 is backlog — no urgency. |
| **GitHub Actions minutes budget** | All CI is `workflow_dispatch` only. Don't auto-trigger on PR. Manual trigger after review. |

## PR Count Summary

| Batch | PRs | Issues | Priority |
|-------|-----|--------|----------|
| 1 | 4 | 8 (7 P0 + 1 P1) | P0 + unblock |
| 2 | 4 | 9 (9 P1) | P1 |
| 3 | 5 + 3 | 13 (13 P2) | P2 |
| 4 | 6 | 16 (16 P3) | P3 |
| **Total** | **22** | **46** | — |

---

## Decision Required

**Pen-and-ink aesthetic (#28):** Switch needs a squad decision before PR-H can merge. Three options:

1. **Adopt** — Add pen-and-ink as an official alternative style in `prompts/examples.md`. Keep batch files.
2. **Migrate** — Rewrite batch file prompts to use canonical tropical magical-realism aesthetic.
3. **Remove** — Delete `batch_blog_images.json` and `_v2.json` as experimental artifacts.

Recommend: **Option 2 (Migrate)** unless dfberry explicitly wants the pen-and-ink style. The batch files are the only consumer of this aesthetic, and it's undocumented. Migrating preserves the batch infrastructure while eliminating style drift.

---

*This plan resolves all 46 issues in 4 batches with 22 PRs across 5 agents. P0+P1 (17 issues, highest impact) complete in 2 parallel batches. Estimated calendar time for P0+P1: 2 weeks assuming daily review cycles.*
