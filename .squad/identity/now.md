---
updated_at: 2026-04-19
focus_area: Multi-tool repo structure complete; PR #84 pending merge
active_issues: []
---

# What We're Focused On

Repo restructured into multi-tool layout (PR #84, squad-approved). Image generation lives in `image-generation/` subfolder. Empty `mermaid-diagrams/` created for future diagram tool. CI, CODEOWNERS, .gitignore, doc paths all updated.

## Restructure Complete (2026-04-19)

- **Branch:** `squad/repo-restructure-subfolders`
- **PR:** #84 (labeled squad-approved)
- **Layout:** `image-generation/` (active), `mermaid-diagrams/` (planned), shared infra at root
- **CI:** `working-directory: image-generation` for lint, install, test steps
- **Tests:** 161 pass, zero new failures; conftest.py sys.path fix for imports
- **Commits:** 387283b (Trinity — restructure), 6f4fd49 (Coordinator — doc path fixes)

## Prior Review Summary (2026-04-19)

- **Overall grade:** B- (pipeline A-, code quality B+, docs D+, prompts C+)
- **Findings:** 5 CRITICAL, 7 HIGH, 22 MEDIUM, 12 LOW, 12 INFO
- **Top P0 items:** README defaults wrong, shell script prompts stale, batch path traversal, Python version wrong in skill doc, figure prompts need silhouette rewrite, batch_generate() default device hardcoded to "mps"
- **Synthesis report:** `.squad/decisions/inbox/morpheus-codebase-review-synthesis.md`
- **Reviewers:** Trinity (D1+D7), Niobe (D2), Neo (D3+D6), Switch (D4), Morpheus (D5 + synthesis)
