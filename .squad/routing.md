# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|---------|
| Architecture, decisions, scope | Morpheus | What to build, trade-offs, structural choices |
| Python implementation | Trinity | generate.py changes, new CLI flags, pipeline tweaks |
| Shell scripts | Trinity | generate_blog_images.sh, regen_*.sh, new batch scripts |
| Prompt engineering | Trinity | New prompts, prompt library updates, style guide changes |
| Output structure | Trinity | Naming conventions, output directory changes |
| Test design & test code | Neo | pytest tests, edge case specs, validation |
| Prompt validation | Neo | Does this prompt produce the intended output? |
| Quality review | Neo | Image output quality assessment, regression checks |
| Code review | Morpheus | Review PRs, check quality, suggest improvements |
| Async issue work (bugs, tests, small features) | @copilot 🤖 | Well-defined tasks matching capability profile |
| Session logging | Scribe | Automatic — never needs routing |
| Work queue monitoring | Ralph | Automatic — activated on request |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Morpheus |
| `squad:morpheus` | Lead picks up issue | Morpheus |
| `squad:trinity` | Backend picks up issue | Trinity |
| `squad:neo` | Tester picks up issue | Neo |
| `squad:copilot` | Assign to @copilot for autonomous work (if enabled) | @copilot 🤖 |

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If a feature is being built, spawn Neo to write test cases simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. Morpheus handles all `squad` (base label) triage.
