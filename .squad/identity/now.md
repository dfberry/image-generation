---
updated_at: 2026-04-19
focus_area: Repo restructure into multi-tool layout
active_issues: []
---

# What We're Focused On

Repo restructured into multi-tool layout. Image generation moved to `image-generation/` subfolder. Empty `mermaid-diagrams/` created for future diagram tool. CI, CODEOWNERS, .gitignore updated for new paths.

## Restructure (2026-04-19)

- **Branch:** `squad/repo-restructure-subfolders`
- **Layout:** `image-generation/` (active), `mermaid-diagrams/` (planned), shared infra at root
- **CI:** Updated `working-directory: image-generation` for lint, install, test steps
- **Tests:** conftest.py updated with sys.path insert for cross-directory imports

## Review Summary (2026-04-19)

- **Overall grade:** B- (pipeline A-, code quality B+, docs D+, prompts C+)
- **Findings:** 5 CRITICAL, 7 HIGH, 22 MEDIUM, 12 LOW, 12 INFO
- **Top P0 items:** README defaults wrong, shell script prompts stale, batch path traversal, Python version wrong in skill doc, figure prompts need silhouette rewrite, batch_generate() default device hardcoded to "mps"
- **Synthesis report:** `.squad/decisions/inbox/morpheus-codebase-review-synthesis.md`
- **Reviewers:** Trinity (D1+D7), Niobe (D2), Neo (D3+D6), Switch (D4), Morpheus (D5 + synthesis)
