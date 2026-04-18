# Decision: PR #15 Blocker Fixes & Joel Test Score Revision

**Author:** Morpheus (Lead)  
**Date:** 2025-07-22  
**Context:** Neo's review of PR #15 (squad/joel-test-improvements) flagged 2 blockers and several concerns.

## Fixes Applied

### 🔴 BLOCKER: Makefile CRLF → LF
- Converted Makefile to LF line endings via PowerShell byte-level write.
- Added `Makefile text eol=lf` to `.gitattributes` so git enforces LF on checkout.

### 🔴 BLOCKER: batch_observability_blog.json removed
- `git rm` removed the file. It contained hardcoded `C:\Users\diberry\...` paths and was never part of Joel Test scope.

### 🟡 CI shell quoting
- `.github/workflows/tests.yml` line 26: `pip install ruff>=0.4.0` → `pip install 'ruff>=0.4.0'` to prevent bash `>=` redirect.

### 🟡 CI uses requirements-dev.txt
- Test job now runs `pip install -r requirements-dev.txt` instead of manually listing packages. Torch CPU install kept separate for its special index URL.

### 🟡 ruff.toml clarified
- Ruff doesn't support `line-length` under `[format]`. Kept `line-length = 120` at top level (controls formatter width) with an inline comment clarifying that lint rule E501 is separately ignored. The contradiction is resolved — intent is now explicit.

## Joel Test Score Revision

Neo correctly challenged the 10/12 claim. Honest reassessment:

| # | Criterion | Verdict |
|---|-----------|---------|
| 1 | Source control | ✅ Yes |
| 2 | One-step build | ✅ Yes (Makefile, after CRLF fix) |
| 3 | Daily builds | ✅ Yes (CI on push/PR) |
| 4 | Bug database | ✅ Yes (GitHub Issues) |
| 5 | Fix bugs before new code | ✅ Yes (process commitment) |
| 6 | Up-to-date schedule | ❌ No — spec ≠ schedule |
| 7 | Spec | ✅ Yes (prompts/examples.md) |
| 8 | Quiet working conditions | ➖ N/A (solo/AI project) |
| 9 | Best tools money can buy | ✅ Yes |
| 10 | Testers | ✅ Yes (Neo + pytest) |
| 11 | Code samples in interviews | ➖ N/A |
| 12 | Hallway usability testing | ❌ No — no user testing process |

**Revised score: 9/12** (counting N/A items as pass, #6 and #12 as fail).

The PR description should be updated to reflect 9/12 before merge.

## Reviewer Gate Note

Per Reviewer Rejection Protocol, Trinity (original author) was locked out of fixing these artifacts. Morpheus applied all fixes as Lead.
