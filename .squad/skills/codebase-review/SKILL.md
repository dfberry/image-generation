---
name: "codebase-review"
description: "7-dimension structured codebase review framework for image-generation"
domain: "code-review"
confidence: "high"
source: "earned — designed and executed by Morpheus (Lead) with full Squad team"
---

## Context

Use this skill when performing a comprehensive code review of the image-generation project, or when reviewing PRs that touch multiple dimensions (code quality, pipeline, tests, prompts, docs, security, CI). The framework ensures nothing is missed by decomposing the review into 7 orthogonal dimensions with explicit checklists and phase gates.

This skill is also useful as a template when designing reviews for other Python CLI + ML pipeline projects.

## Patterns

### 7-Dimension Review Framework

Every thorough review covers these 7 dimensions:

| Dimension | Scope | Key Questions |
|-----------|-------|---------------|
| D1: Code Quality & Architecture | `generate.py`, linting, structure | Function responsibility, dead code, error hierarchy, ruff compliance |
| D2: SDXL Pipeline & GPU Safety | Model loading, inference, memory | 5 flush points, device paths (CUDA/MPS/CPU), scheduler/LoRA safety |
| D3: Test Coverage & Quality | `tests/`, `conftest.py` | Coverage gaps, assertion correctness, mock quality, collection barriers |
| D4: Prompt Library & Style | `prompts/examples.md`, style guide | Style anchors, palette colors, silhouette compliance, anti-text guards |
| D5: Documentation Accuracy | README, CONTRIBUTING, docs/ | CLI defaults vs code, test counts, file references, version claims |
| D6: Security & Supply Chain | All files | Path traversal, input validation, dependency CVEs, CI permissions |
| D7: CI/DevOps & Build System | workflows, Makefile, requirements | CI/local parity, cross-platform, coverage reporting, action pinning |

### Phase Gate Execution

Reviews execute in 4 phases with gate conditions:

```
Phase 1 (Parallel)     Phase 2        Phase 3        Phase 4
┌──────────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ D1+D7 Code/CI    │   │          │   │          │   │          │
│ D2   Pipeline    │──▶│ D5 Docs  │──▶│ D6 Sec   │──▶│ Synthesis│
│ D3   Tests       │   │          │   │          │   │          │
│ D4   Prompts     │   │          │   │          │   │          │
└──────────────────┘   └──────────┘   └──────────┘   └──────────┘
```

- **G1:** Phase 2 waits for Phase 1 (doc review needs code truth from D1/D2)
- **G2:** Phase 3 waits for Phase 2 (security review avoids duplicating D1/D2 findings)
- **G3:** Phase 4 synthesis waits for all findings

### Finding Format

Every finding uses this structure:

```markdown
### [FINDING-ID] — Title
**Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
**File:** path/to/file.py:L42-L55
**Dimension:** D1–D7
**Description:** What's wrong
**Evidence:** Code snippet or test output
**Recommendation:** What to do
```

### Agent Assignment (Squad)

| Agent | Dimensions | Why |
|-------|-----------|-----|
| Trinity | D1 + D7 | Backend dev knows code structure and CI |
| Niobe | D2 | Image specialist understands SDXL pipeline |
| Neo | D3 + D6 | Tester owns coverage; security is test-adjacent |
| Switch | D4 | Prompt engineer owns style consistency |
| Morpheus | D5 + Synthesis | Lead cross-references docs against code truth |

### Severity Classification

| Severity | Criteria |
|----------|----------|
| CRITICAL | Users get wrong behavior, security vulnerability, data loss risk |
| HIGH | Misleading docs, broken references, significant gaps |
| MEDIUM | Stale data, missing coverage, non-portable code |
| LOW | Cosmetic, internal-only, minor inconsistencies |
| INFO | Observations, positive findings, future improvements |

### Synthesis Report Structure

The Phase 4 synthesis must include:
1. Executive summary with overall grade
2. Cross-cutting themes (patterns that span multiple dimensions)
3. Prioritized action items (P0 = must fix, P1 = should fix, P2 = improve, P3 = nice-to-have)
4. Positive findings (what's working well)
5. Metrics dashboard (findings by severity, dimension, effort)

## Examples

### Launching Phase 1 (parallel agents)

```
# Spawn 4 agents simultaneously — each reads their charter + checklist
Trinity → D1+D7: generate.py structure, ruff, Makefile, CI workflow
Niobe  → D2:    load_base, load_refiner, generate, memory flush points
Neo    → D3:    all 11 test files, conftest.py, coverage gaps
Switch → D4:    prompts/examples.md, style guide compliance
```

### Cross-cutting theme identification

Look for findings that appear across multiple dimensions:
- **Stale satellites:** Prompts (D4) + docs (D5) + scripts (D7) all drift from source of truth
- **Input validation:** Code (D1) + security (D6) both flag unvalidated inputs
- **Test barriers:** Tests (D3) + CI (D7) both blocked by module-level imports

## Anti-Patterns

- **Single-pass review:** Don't try to review everything in one pass — the phase gates exist because later phases depend on earlier findings.
- **Skipping dimensions:** Even if the code "looks fine," run all 7 dimensions. D5 (docs) almost always finds issues invisible to code-only review.
- **Severity inflation:** Not everything is CRITICAL. Reserve CRITICAL for user-facing incorrect behavior or security vulnerabilities.
- **Ignoring positive findings:** Document what's working well — it prevents future regressions and acknowledges good engineering.
- **Duplicate findings:** Phase 3 (security) should explicitly exclude issues already found in Phase 1 — check prior findings before filing.
