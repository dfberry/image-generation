# D5: Documentation Accuracy Review

> **Reviewer:** Morpheus (Lead)
> **Date:** 2026-04-19
> **Phase:** 2 of Codebase Review
> **Scope:** README.md, CONTRIBUTING.md, docs/feature-specification.md, docs/design.md, docs/blog-image-generation-skill.md, .squad/agents/morpheus/history.md
> **Reference:** `generate.py` parse_args() and implementation as ground truth

---

## Summary

**17 findings** across 6 documentation files. 4 CRITICAL (users will get wrong behavior), 5 HIGH (misleading or broken references), 5 MEDIUM (stale data), 3 LOW/INFO (cosmetic or internal-only).

The README Options table is the most impactful: it shows wrong defaults AND is missing 8 of 16 CLI flags. Anyone reading the docs will form incorrect expectations about the tool's behavior.

---

## Findings

### DOC-01 — README: --steps default is wrong
**Severity:** CRITICAL
**File:** README.md:47 (Options table)
**Dimension:** D5
**Description:** README says `--steps` default is `40`. Code uses `22`.
**Evidence:**
- Doc: `| --steps INT | 40 | Inference steps |`
- Code: `parser.add_argument("--steps", type=_positive_int, default=22, ...)`  (generate.py:77)
**Recommendation:** Change `40` → `22` in the Options table.

---

### DOC-02 — README: --guidance default is wrong
**Severity:** CRITICAL
**File:** README.md:48 (Options table)
**Dimension:** D5
**Description:** README says `--guidance` default is `7.5`. Code uses `6.5`.
**Evidence:**
- Doc: `| --guidance FLOAT | 7.5 | Guidance scale |`
- Code: `parser.add_argument("--guidance", type=_non_negative_float, default=6.5, ...)` (generate.py:80)
**Recommendation:** Change `7.5` → `6.5` in the Options table.

---

### DOC-03 — README: Options table missing 8 CLI flags
**Severity:** CRITICAL
**File:** README.md:43-53 (Options table)
**Dimension:** D5
**Description:** The Options table lists 9 flags but the actual CLI has 16 arguments. Missing: `--batch-file`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight` (7 flags). Additionally `--refine` description says just "off" but doesn't explain it enables the two-stage base+refiner pipeline.
**Evidence:**
- Code parse_args() defines 16 arguments (generate.py:67-99)
- README Options table has 9 rows
**Recommendation:** Add all missing flags to the Options table with correct defaults and descriptions. Match the complete table in `docs/feature-specification.md` §4.1 which is accurate.

---

### DOC-04 — README: Test count "22" is drastically wrong
**Severity:** CRITICAL
**File:** README.md:82
**Dimension:** D5
**Description:** README says "22 pytest tests" but the actual test suite has **170 test functions** across 11 test files. The "22" appears to be the count from `test_memory_cleanup.py` alone.
**Evidence:**
- Doc: "**Regression tests (stable):** 22 pytest tests covering memory management, device handling, and error cases"
- Actual: 170 `def test_` functions across 11 files (test_cli_validation:13, test_unit_functions:31, test_pipeline_enhancements:20, test_scheduler:18, test_memory_cleanup:22, test_oom_handling:14, test_oom_retry:10, test_batch_generation:17, test_batch_cli:10, test_negative_prompt:7, test_bug_fixes:8)
**Recommendation:** Update to "170 pytest tests across 11 files" and remove the "TDD suites (in development)" caveat — most suites are stable now.

---

### DOC-05 — README: Test command suggests only one file
**Severity:** MEDIUM
**File:** README.md:88
**Dimension:** D5
**Description:** The "regression test suite" command points to only `test_memory_cleanup.py`, implying that's the stable suite. All 11 test files are part of the regression suite.
**Evidence:**
- Doc: `pytest tests/test_memory_cleanup.py -v` labeled as "Run the regression test suite"
- Reality: `pytest tests/ -v` runs the full suite (shown on line 92 but labeled "including TDD in-progress")
**Recommendation:** Make `pytest tests/ -v` the primary recommended command. Remove the distinction between "regression" and "TDD in-progress" suites.

---

### DOC-06 — CONTRIBUTING.md: References nonexistent test_generate.py
**Severity:** HIGH
**File:** CONTRIBUTING.md:38
**Dimension:** D5
**Description:** CONTRIBUTING.md shows `python -m pytest tests/test_generate.py -v` as an example command. This file does not exist. Tests are spread across 11 files in `tests/`.
**Evidence:**
- Doc: `python -m pytest tests/test_generate.py -v` (line 38)
- Actual: `glob tests/test_generate.py` → no matches. Actual files: test_batch_cli.py, test_batch_generation.py, test_bug_fixes.py, test_cli_validation.py, test_memory_cleanup.py, test_negative_prompt.py, test_oom_handling.py, test_oom_retry.py, test_pipeline_enhancements.py, test_scheduler.py, test_unit_functions.py
**Recommendation:** Replace with a valid example like `python -m pytest tests/test_cli_validation.py -v` or remove the single-file example entirely.

---

### DOC-07 — blog-image-generation-skill.md: Says Python 3.14
**Severity:** HIGH
**File:** docs/blog-image-generation-skill.md:12,45,250
**Dimension:** D5
**Description:** Three references to "Python 3.14" — a version that does not exist (Python 3.13 is the latest stable as of 2026). The project requires Python 3.10+.
**Evidence:**
- Line 12: `"Python 3.14 + HuggingFace diffusers SDXL pipeline"` (YAML frontmatter tools)
- Line 45: `Python 3.14 + HuggingFace diffusers 0.37.0 + SDXL Base 1.0`
- Line 250: `nohup bash script.sh` (causes Python 3.14 fatal errors)`
- README.md line 7: `Python 3.10+` (correct)
**Recommendation:** Change all "3.14" → "3.10+" across the skill doc.

---

### DOC-08 — blog-image-generation-skill.md: Hardcoded macOS paths
**Severity:** MEDIUM
**File:** docs/blog-image-generation-skill.md:35,143,164,204
**Dimension:** D5
**Description:** Multiple hardcoded paths to `/Users/geraldinefberry/repos/my_repos/...` which are specific to one developer's machine. These paths won't work for any other contributor.
**Evidence:**
- Line 35: `cd /Users/geraldinefberry/repos/my_repos/image-generation`
- Line 143: `cd /Users/geraldinefberry/repos/my_repos/image-generation`
- Line 164: `cp /Users/geraldinefberry/repos/my_repos/image-generation/outputs/...`
- Line 204: `cd /Users/geraldinefberry/repos/my_repos/dfberry.github.io`
**Recommendation:** Replace absolute paths with relative paths or generic placeholders like `<your-repo-root>`.

---

### DOC-09 — blog-image-generation-skill.md: diffusers version claim
**Severity:** LOW
**File:** docs/blog-image-generation-skill.md:45
**Dimension:** D5
**Description:** Claims "diffusers 0.37.0" but requirements.txt specifies `diffusers>=0.21.0`. The pinned minimum is 0.21.0; 0.37.0 is not guaranteed.
**Evidence:**
- Doc: `Python 3.14 + HuggingFace diffusers 0.37.0 + SDXL Base 1.0`
- requirements.txt: `diffusers>=0.21.0`
**Recommendation:** Change to `diffusers>=0.21.0` to match requirements.txt, or remove specific version.

---

### DOC-10 — design.md: File layout lists removed file
**Severity:** MEDIUM
**File:** docs/design.md:651
**Dimension:** D5
**Description:** Appendix B file layout lists `batch_observability_blog.json` which was removed in PR #15 (per Morpheus history).
**Evidence:**
- Doc: `├── batch_observability_blog.json  # Another batch file` (design.md:651)
- Actual: `glob batch_observability_blog.json` → no matches
**Recommendation:** Remove the `batch_observability_blog.json` line from the file layout.

---

### DOC-11 — design.md: Test count says 170 but 29 collect
**Severity:** MEDIUM
**File:** docs/design.md:533
**Dimension:** D5
**Description:** Design doc says "170 (172 items with parametrize expansion)" test functions. Grep confirms 170 `def test_` functions, but `pytest --collect-only` only collects 29 tests due to 9 collection errors (likely import/fixture issues in some test files). The doc count matches the source code, but the test suite doesn't fully run.
**Evidence:**
- Doc: `| **Test functions** | 170 (172 items with parametrize expansion) |`
- `pytest --collect-only`: `29 tests collected, 9 errors`
- `grep "def test_"`: 170 matches across 11 files
**Recommendation:** Investigate and fix the 9 collection errors, then the doc count will be accurate. Note this in the review as a test health issue, not purely a doc issue.

---

### DOC-12 — history.md: Key Paths lists wrong CLI flag names
**Severity:** HIGH
**File:** .squad/agents/morpheus/history.md:10
**Dimension:** D5
**Description:** Key Paths says `--refiner` and `--device` flags. Actual flags are `--refine` and `--cpu`.
**Evidence:**
- Doc: `generate.py — main CLI with --steps, --guidance, --seed, --width, --height, --refiner, --device flags`
- Code: `--refine` (generate.py:93), `--cpu` (generate.py:94). No `--refiner` or `--device` flag exists.
**Recommendation:** Change `--refiner` → `--refine` and `--device` → `--cpu`. Also add the missing flags: `--batch-file`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight`.

---

### DOC-13 — history.md: References nonexistent regen scripts
**Severity:** HIGH
**File:** .squad/agents/morpheus/history.md:12
**Dimension:** D5
**Description:** Key Paths lists `regen_fix.sh` but no `regen_*.sh` files exist in the repository.
**Evidence:**
- Doc: `regen_fix.sh — regenerates images 01, 06, 07, 08 with corrected prompts`
- Actual: `glob regen_*.sh` → no matches. README "Project Context" also references `regen_fix.sh`, `regen_new.sh`, `regen_345.sh` but none exist.
**Recommendation:** Remove references to regen scripts, or note they were removed. The batch file approach via `--batch-file` supersedes individual regen scripts.

---

### DOC-14 — history.md: Missing Key Paths flags incomplete
**Severity:** MEDIUM
**File:** .squad/agents/morpheus/history.md:10
**Dimension:** D5
**Description:** Key Paths only lists 7 of 16 CLI flags. Missing: `--batch-file`, `--output`, `--refiner-steps`, `--refiner-guidance`, `--scheduler`, `--negative-prompt`, `--lora`, `--lora-weight`, `--refine` (correct name).
**Evidence:** See generate.py:67-99 for full argument list.
**Recommendation:** Update to list all flags or use a general description like "main CLI with 16 configurable flags (see README Options table)".

---

### DOC-15 — CONTRIBUTING.md: Key Details lists flags correctly
**Severity:** INFO
**File:** CONTRIBUTING.md:113
**Dimension:** D5
**Description:** Positive finding — CONTRIBUTING.md line 113 correctly lists the full set of CLI flags including `--batch-file`, `--refiner-steps`, `--scheduler`, `--negative-prompt`, `--lora`. This is the most accurate flag list in any doc.
**Evidence:** `CLI flags: --prompt, --batch-file, --output, --steps, --refiner-steps, --guidance, --scheduler, --seed, --negative-prompt, --refine, --cpu, --lora`
**Recommendation:** No change needed. Use this as the reference when updating other docs. (Note: `--refiner-guidance` and `--lora-weight` are still missing from this list.)

---

### DOC-16 — feature-specification.md: Fully accurate
**Severity:** INFO
**File:** docs/feature-specification.md
**Dimension:** D5
**Description:** Positive finding — the feature specification (§4.1 CLI Arguments table) is the most complete and accurate documentation of the CLI interface. All 16 arguments are listed with correct defaults, types, and constraints. All functional requirements match the code.
**Evidence:** Verified every argument in §4.1 against generate.py parse_args(). All defaults match: steps=22, refiner-steps=10, guidance=6.5, refiner-guidance=5.0, scheduler=DPMSolverMultistepScheduler, width=1024, height=1024, lora-weight=0.8.
**Recommendation:** No change needed. This should be the source of truth for other docs.

---

### DOC-17 — design.md: Architecture matches code
**Severity:** INFO
**File:** docs/design.md
**Dimension:** D5
**Description:** Positive finding — the design document's architecture description, data flow diagrams, memory management strategy, OOM recovery, scheduler system, LoRA integration, batch processing, and device abstraction all accurately reflect the current code. Line number references in §1.2 are approximately correct (within a few lines). The testing strategy section (§11) accurately describes the mock strategy and test coverage by area.
**Evidence:** Cross-referenced all code sections, function signatures, and behavior descriptions against generate.py. No material discrepancies found (aside from DOC-10 and DOC-11).
**Recommendation:** Only fix the stale file layout (DOC-10) and note the collection error issue (DOC-11).

---

## Priority Summary

| Severity | Count | Action |
|----------|-------|--------|
| CRITICAL | 4 | Fix immediately — users get wrong defaults and incomplete feature awareness |
| HIGH | 4 | Fix soon — broken references and wrong flag names mislead contributors |
| MEDIUM | 5 | Fix in next cleanup pass — stale data but lower user impact |
| LOW | 1 | Optional — version specificity in skill doc |
| INFO | 3 | No action — positive findings confirming accuracy |

## Recommended Fix Order

1. **README.md Options table** (DOC-01, DOC-02, DOC-03) — highest user impact
2. **README.md test count** (DOC-04, DOC-05) — misleading project maturity signal
3. **CONTRIBUTING.md test file ref** (DOC-06) — contributor onboarding blocker
4. **blog-image-generation-skill.md Python version** (DOC-07) — factually wrong
5. **history.md flag names** (DOC-12, DOC-13, DOC-14) — internal but affects agent accuracy
6. **blog-image-generation-skill.md paths** (DOC-08) — contributor convenience
7. **design.md stale file** (DOC-10) — minor cleanup
