---
name: "doc-accuracy-check"
description: "Cross-reference documentation claims against code implementation"
domain: "documentation"
confidence: "high"
source: "earned — developed by Morpheus (Lead) during D5 documentation accuracy review"
---

## Context

Use this skill when reviewing documentation PRs, auditing docs for accuracy, or after code changes that may have made docs stale. The methodology systematically cross-references every factual claim in documentation against the actual codebase, catching drift that accumulates as code evolves faster than docs.

This skill applies whenever:
- A PR changes CLI defaults, function signatures, or behavior
- Someone reports "the docs say X but the code does Y"
- A new release is being prepared
- Documentation hasn't been reviewed in >2 weeks

## Patterns

### CLI Defaults Verification

Compare every default value in documentation against `parse_args()` in `generate.py`:

```python
# Source of truth: generate.py parse_args()
parser.add_argument("--steps", type=_positive_int, default=22)
parser.add_argument("--guidance", type=_non_negative_float, default=6.5)
# ... etc for all 16 arguments
```

Check these documentation locations for each flag:
1. `README.md` Options table
2. `docs/feature-specification.md` §4.1 CLI Arguments
3. `docs/blog-image-generation-skill.md` usage examples
4. `generate_blog_images.sh` inline comments

### Test Count Verification

```bash
# Get actual test count
grep -r "def test_" tests/ | wc -l

# Compare against claims in:
# - README.md (test section)
# - CONTRIBUTING.md (testing section)
# - Any CI badges or status messages
```

### File Reference Verification

For every file path mentioned in documentation, verify it exists:

```bash
# Extract all file paths from a doc
grep -oE '[a-zA-Z_/]+\.(py|sh|md|txt|json|yml|yaml|toml)' README.md | sort -u

# Check each one exists
for f in $(grep -oE '[a-zA-Z_/]+\.(py|sh|md|txt|json|yml|yaml|toml)' README.md | sort -u); do
  test -f "$f" || echo "MISSING: $f"
done
```

### Version Claim Verification

Check all version claims against actual configuration:

| Claim Location | What to Verify | Source of Truth |
|---------------|----------------|-----------------|
| Python version | "Python 3.x" | `ruff.toml` target-version, CI matrix |
| Dependency versions | Version ranges | `requirements.txt` |
| torch compatibility | CUDA/MPS support claims | Code device detection logic |

### Path Portability Check

Flag any hardcoded OS-specific paths:

```
# Bad: macOS-specific
/Users/username/projects/image-generation/

# Bad: Linux-specific
/home/username/venv/bin/python

# Good: relative or variable
./outputs/
$(VENV)/bin/python  # (still Unix-only but at least parameterized)
```

### Documentation Claim Categories

Organize findings by claim type:

| Category | Priority | Examples |
|----------|----------|---------|
| **Behavioral claims** | CRITICAL | "Default steps is 40" (wrong — it's 22) |
| **Completeness** | CRITICAL | Options table missing 7 of 16 flags |
| **Counts/metrics** | HIGH | "22 tests" (actual: 170) |
| **File references** | HIGH | Points to `test_generate.py` (doesn't exist) |
| **Version claims** | MEDIUM | "Python 3.14" (should be 3.10+) |
| **Path portability** | LOW | Hardcoded macOS user paths |

### Cross-Reference Matrix

Build a matrix mapping each doc file to its code dependencies:

| Doc File | Depends On | Check |
|----------|-----------|-------|
| README.md Options table | `generate.py` parse_args() | All defaults match |
| README.md test section | `tests/` directory | Test count matches |
| CONTRIBUTING.md | `tests/`, `Makefile` | File refs exist, commands work |
| feature-specification.md | `generate.py` all functions | FR-xxx requirements implemented |
| design.md | `generate.py` architecture | Architecture claims accurate |
| blog-image-generation-skill.md | `generate.py`, env | Python version, paths correct |

## Examples

### Finding format for doc accuracy issues

```markdown
### DOC-01 — README: --steps default is wrong
**Severity:** CRITICAL
**File:** README.md:47 (Options table)
**Dimension:** D5
**Description:** README says `--steps` default is `40`. Code uses `22`.
**Evidence:**
- Doc: `| --steps INT | 40 | Inference steps |`
- Code: `parser.add_argument("--steps", ..., default=22, ...)` (generate.py:77)
**Recommendation:** Change `40` → `22` in the Options table.
```

### Batch verification script

```bash
# Quick smoke test: extract README defaults, compare to code
echo "=== README defaults ==="
grep -E '^\|.*\|.*\|' README.md | grep -E '\-\-'

echo "=== Code defaults ==="
grep 'default=' generate.py | grep add_argument
```

## Anti-Patterns

- **Trusting docs without verification:** Never assume documentation is correct. Always verify against code, even for "obvious" claims like version numbers.
- **Checking only README:** All 6 documentation files can drift independently. Check them all.
- **Fixing docs without fixing code:** If docs say one thing and code says another, verify which is the *intended* behavior before deciding which to change.
- **Ignoring internal docs:** `.squad/agents/*/history.md` files also contain factual claims (flag names, file paths) that can go stale.
- **One-time audit mentality:** Doc accuracy should be checked on every PR that changes CLI behavior, defaults, or test counts. Integrate into the review checklist.
