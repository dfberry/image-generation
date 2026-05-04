---
name: "image-gen-pr-workflow"
description: "PR creation, validation, and merge workflow for image-generation repo including full team review process"
domain: "pr-workflow, code-review, testing"
confidence: "high"
source: "earned (session with PR #103)"
tools:
  - name: "gh pr create"
    description: "Create pull request from current branch"
    when: "After pushing branch and before validation"
  - name: "gh pr merge"
    description: "Merge and squash PR with branch deletion"
    when: "After all reviewers approve"
  - name: "python -m pytest"
    description: "Run Python test suite"
    when: "Before pushing and after making changes"
  - name: "task (Squad agents)"
    description: "Spawn specialized reviewers for PR validation"
    when: "After PR creation, for validation and fixing"
---

## Context

This skill captures the complete PR workflow for the image-generation repository, including branch creation, commit conventions, full team review orchestration, and merge procedures. It was learned from PR #103 which added text redaction functionality.

The workflow emphasizes:
- Safety first (branch from origin, never local main)
- Parallel reviews by specialized agents
- Clear approval gates before merge
- Test-driven validation

## Patterns

### PR Creation

**Branch Creation:**
```bash
# Always branch from origin/main, never local main
git checkout -b squad/{issue-number}-{kebab-case-slug} origin/main

# For non-issue work:
git checkout -b squad/{feature-slug} origin/main
```

**Why:** Local main may contain unpushed commits that bloat the PR diff.

**Commit Message Convention:**
```
feat(image-generation): add new feature
fix(redact_text): resolve RGBA conversion bug
test(redact_text): add Unicode character tests
docs(redact_text): update README with new flags
```

Pattern: `{type}({scope}): {description}`

**Required Co-author:**
```
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

Always include this trailer in commit messages.

**Push and Create PR:**
```bash
git push origin {branch-name}
gh pr create --title "feat: {description}" --body "{details}"
```

### PR Validation — Full Team Review

**Critical:** Spawn all relevant reviewers **in parallel**, not sequentially. This is faster and ensures independent perspectives.

**Review Team:**

1. **🏗️ Morpheus (Lead)** — `.squad/agents/morpheus/charter.md`
   - Architecture decisions
   - Security concerns (ReDoS, input validation)
   - Code quality and conventions
   - Cross-cutting concerns
   - Dependency choices

2. **🎨 Niobe (Image Specialist)** — `.squad/agents/niobe/charter.md`
   - OCR approach and accuracy
   - Image quality preservation
   - Color handling (RGBA, RGB, JPEG)
   - Resolution and bounds
   - Font rendering and fallback

3. **💬 Switch (Prompt/LLM Engineer)** — `.squad/agents/switch/charter.md`
   - CLI UX and flag naming
   - Help text clarity
   - Example quality in epilog
   - Error message actionability
   - Logging levels

4. **🧪 Neo (Tester)** — `.squad/agents/neo/charter.md`
   - Test coverage completeness
   - Edge case identification
   - Assertion quality and specificity
   - Mock realism
   - Missing test scenarios

**Spawning Pattern:**
```bash
# Spawn all reviewers in parallel
task agent_type: general-purpose, name: morpheus-review, prompt: "Review PR #{number}..."
task agent_type: general-purpose, name: niobe-review, prompt: "Review PR #{number}..."
task agent_type: general-purpose, name: switch-review, prompt: "Review PR #{number}..."
task agent_type: general-purpose, name: neo-review, prompt: "Review PR #{number}..."
```

**Review Verdict:**
Each reviewer must give a clear verdict:
- ✅ **APPROVE** — No blocking issues
- ⚠️ **REQUEST CHANGES** — Blocking issues found (with specific findings)

**On REQUEST CHANGES:**
1. Spawn the **appropriate agent** (not the reviewer) to fix findings
2. Example: If Niobe flags image quality issues, spawn Trinity (backend dev) to fix
3. Never ask the reviewer to fix their own findings

**Re-review After Fixes:**
After fixes are pushed, re-run the same reviewers who requested changes to verify their specific concerns were addressed.

**Merge Gate:**
Merge only when:
- All reviewers approve, OR
- User explicitly overrides with rationale

### Test Validation

**Before Pushing:**
```bash
cd image-generation
python -m pytest tests/test_redact_text.py -v
```

All tests must pass before pushing changes.

**Test Output Structure:**
```
image-generation/
  test-outputs/          # Gitignored
    demos/               # Before/after pairs for visual validation
      input-*.png
      output-*.png
    unit-tests/          # Expected to be blank/error outputs
      *.png
```

**After Making Changes:**
Re-run tests to ensure no regressions.

### PR Merge

**Command:**
```bash
gh pr merge {number} --squash --delete-branch
```

This squashes all commits, deletes the branch, and closes the PR.

## Examples

### Complete PR Flow (PR #103)

```bash
# 1. Create branch
git checkout -b squad/103-redact-text origin/main

# 2. Make changes, commit with convention
git add image-generation/redact_text.py tests/test_redact_text.py
git commit -m "feat(image-generation): add text redaction with customizable replacement

- Add --redact-text and --replacement-text flags
- Support Unicode characters in redaction
- Convert RGBA to RGB for JPEG compatibility
- Add comprehensive test suite with edge cases

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# 3. Test before push
cd image-generation
python -m pytest tests/test_redact_text.py -v
# All tests pass ✓

# 4. Push and create PR
git push origin squad/103-redact-text
gh pr create --title "feat: Add text redaction to generated images" \
  --body "Closes #103. Adds --redact-text and --replacement-text flags..."

# 5. Spawn reviewers in parallel
# (Use task tool to spawn Morpheus, Niobe, Switch, Neo simultaneously)

# 6. Collect verdicts
# - Morpheus: REQUEST CHANGES (ReDoS concern on regex)
# - Niobe: REQUEST CHANGES (JPEG quality, double image load)
# - Switch: APPROVE
# - Neo: REQUEST CHANGES (weak assertions, missing Unicode test)

# 7. Fix findings
# Spawn Trinity to address Morpheus and Niobe findings
# Spawn Neo to address test quality findings

# 8. Re-review
# Re-run Morpheus, Niobe, Neo on updated PR
# All: APPROVE ✓

# 9. Merge
gh pr merge 103 --squash --delete-branch
```

### Review-Specific Findings

**Morpheus (Lead) — Common Findings:**
```python
# ❌ Bad: No validation on user regex input (ReDoS risk)
pattern = re.compile(args.redact_text)

# ✅ Good: Validate regex complexity
if len(args.redact_text) > 100:
    raise ValueError("Pattern too long")
```

**Niobe (Image) — Common Findings:**
```python
# ❌ Bad: JPEG save without quality param (degrades image)
image.save(output_path, format="JPEG")

# ✅ Good: Preserve quality
image.save(output_path, format="JPEG", quality=95)

# ❌ Bad: Double image load (inefficient)
img1 = Image.open(path)
img2 = Image.open(path)

# ✅ Good: Single load
img = Image.open(path)
```

**Switch (UX) — Common Findings:**
```python
# ❌ Bad: Help text doesn't mention related flags
parser.add_argument("--redact-text", help="Text to redact")

# ✅ Good: Cross-reference related flags
parser.add_argument("--redact-text", 
    help="Text to redact. Use with --replacement-text to customize replacement.")
```

**Neo (Tests) — Common Findings:**
```python
# ❌ Bad: Weak assertion
assert result is not None

# ✅ Good: Specific assertion
assert result == expected_blank_image

# ❌ Bad: Missing edge case
def test_redact_text():
    redact_text_from_image("input.png", "secret", "***", "output.png")

# ✅ Good: Edge cases covered
def test_redact_unicode():
    redact_text_from_image("input.png", "秘密", "***", "output.png")

def test_redact_case_insensitive():
    redact_text_from_image("input.png", "(?i)secret", "***", "output.png")
```

## Anti-Patterns

### Branch Creation
- ❌ **Branch from local main** — May include unpushed commits
- ❌ **Branch naming without squad/ prefix** — Inconsistent with conventions
- ❌ **Forget Co-authored-by trailer** — Loses attribution

### Review Process
- ❌ **Sequential reviews** — Wastes time, creates bottlenecks
- ❌ **Vague verdicts** — "Looks good" or "Some concerns" without APPROVE/REQUEST CHANGES
- ❌ **Asking reviewers to fix their findings** — Reviewers review, devs fix
- ❌ **Skip re-review after fixes** — Original concerns may not be addressed
- ❌ **Merge without all approvals** — Unless user explicitly overrides

### Testing
- ❌ **Skip tests before push** — Catches regressions too late
- ❌ **Weak assertions** — `is not None` or `in [0, 1]` don't validate correctness
- ❌ **Missing edge cases** — Unicode, case sensitivity, invalid input
- ❌ **Unrealistic mocks** — Don't represent production behavior

### Image Quality
- ❌ **JPEG save without quality param** — Degrades image quality
- ❌ **Double image loads** — Inefficient, slower processing
- ❌ **Forget RGBA→RGB conversion** — JPEG doesn't support RGBA, causes errors
- ❌ **Missing font fallback** — Renders as boxes when font unavailable

### Security
- ❌ **No regex validation** — ReDoS vulnerability on user input
- ❌ **Overly complex regex** — Hard to maintain, slow to execute
- ❌ **No input length limits** — Enables denial-of-service

### UX/CLI
- ❌ **Flags without related flag mentions** — User doesn't know about complementary options
- ❌ **Missing epilog examples** — User doesn't know how to use flags together
- ❌ **Generic error messages** — "Error processing image" (not actionable)
- ❌ **Wrong logging levels** — Info messages as warnings, debug as info
