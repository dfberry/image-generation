---
name: image-gen-pr-workflow
description: "Orchestrate PR reviews for image-generation repo. Spawn parallel team reviews (Lead, Image Specialist, UX, Tester), enforce branch/commit conventions, gate merges on approval. USE FOR: 'review PR', 'validate PR', 'create PR', 'merge PR', 'PR workflow'. DO NOT USE FOR: issue triage, backlog management, general code questions, feature planning, documentation updates."
---

**WORKFLOW SKILL** — Full PR lifecycle orchestration for image-generation repo. INVOKES: squad agents (Morpheus, Niobe, Switch, Neo), git, gh CLI.

## Branch & Commit

**Branch:** `squad/{slug}` from `origin/main` (never local main)  
**Commit:** `type(scope): message` + Co-authored-by trailer  
**Test:** `python -m pytest` before push

## Create PR

```bash
git push origin {branch}
gh pr create --title "type: description" --body "details"
```

## Review (Parallel)

Spawn 4 reviewers simultaneously:
- **Morpheus (Lead):** architecture, security, quality
- **Niobe (Image):** OCR, image quality, color handling
- **Switch (UX):** CLI flags, help text, error messages
- **Neo (Tester):** coverage, edge cases, assertions

Each gives: ✅ **APPROVE** or ⚠️ **REQUEST CHANGES**

**Fix cycle:** Spawn dev agent (not reviewer) to address findings → re-review

**Merge gate:** All approve OR user override

## Merge

```bash
gh pr merge {number} --squash --delete-branch
```

## References

Detailed checklists and examples:
- [Reviewer Checklists](references/reviewer-checklists.md) — what each reviewer checks
- [Common Findings](references/common-findings.md) — typical issues by reviewer
