# Decision: Branch Reorg — recording-toolkit/desktop-capture-v2

**Date:** 2026-05-18  
**Author:** Trinity (Backend Dev)  
**Status:** Executed

## What happened

Local `main` had 1 unpushed commit (`c4873aa` — "feat: add vscode-copilot-chat desktop test plan and smoke test runner") and two uncommitted modifications that belonged on a feature branch, not main.

## Action taken

1. Stashed dirty changes (`recording-toolkit/scripts/record_desktop.py`, `recording-toolkit/scripts/demo_plan_runner.py`)
2. Created `recording-toolkit/desktop-capture-v2` from local main (capturing `c4873aa`)
3. Popped stash onto feature branch
4. Hard-reset `main` to `origin/main` — `main` now clean and in sync
5. Recovered stash modifications via dropped stash SHA (`743e7c8f`) after git checkout carried them to main during branch switch

## Recovery note

`git checkout main` after stash pop silently carried working-tree modifications to main before the hard reset could run. Recovery used the unreferenced stash object (`git checkout <sha> -- <files>`). This is safe — dropped stash objects persist until GC.

## Final state

| Branch | HEAD | Dirty changes |
|--------|------|---------------|
| `main` | `9bdf0e5` == `origin/main` | none |
| `recording-toolkit/desktop-capture-v2` | `c4873aa` | `record_desktop.py`, `demo_plan_runner.py` modified (unstaged) |

Untracked test outputs (`checkpoint-*.png`, `recording-toolkit/recordings/`, `recordings/test/`) untouched — not committed, not deleted.

## Recommendation

Add `recordings/test/` and `checkpoint-*.png` to `.gitignore` to prevent accidental staging.
