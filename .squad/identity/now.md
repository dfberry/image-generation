---
updated_at: 2026-04-21
focus_area: Image support for both animation packages complete and merged
active_issues: []
---

# What We're Focused On

Image/screenshot input support for Manim and Remotion animation packages is complete and merged to main. Both implementations feature secure image handling, AST-based validation, workspace isolation, and LLM context injection. Tests passing: Manim 67/67, Remotion 63/64.

## Image Support Delivery Complete (2026-04-21)

- **PRs:** #88 (Manim), #89 (Remotion)
- **Merge Type:** Squash-merged to main
- **Worktrees:** Cleaned up after merge
- **Tests:** Manim 67/67 passing, Remotion 63/64 passing
- **Architecture:** Separate `image_handler.py` per package, consistent CLI API, policy-based strictness

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
