# Copilot Instructions — image-generation

This repository uses **Squad**, an AI team framework. Every Copilot session in this repo should load the Squad system and work with the team.

## Load Squad on Every Session

1. **Read `.squad/team.md`** — current team roster, member roles, project context.
2. **Read `.squad/routing.md`** — how work gets assigned and who owns what.
3. **Read `.squad/decisions.md`** — architectural and process decisions the team has made.
4. **Check `.squad/identity/now.md`** — what the team was last focused on.

## Team

This project has three AI agents:

| Agent | Role | Charter |
|-------|------|---------|
| Morpheus | 🏗️ Lead | `.squad/agents/morpheus/charter.md` |
| Trinity | 🔧 Backend Dev | `.squad/agents/trinity/charter.md` |
| Neo | 🧪 Tester | `.squad/agents/neo/charter.md` |
| Scribe | 📋 Session Logger | `.squad/agents/scribe/charter.md` |

When you are directed to work as a specific agent, read their charter and history before starting.

## Project Context

This is a multi-tool media generation repo. Each tool lives in its own subfolder.

### image-generation/

Python CLI tool that uses Stable Diffusion XL (SDXL) to generate blog post illustrations with a tropical magical-realism aesthetic.

**Key files:**
- `image-generation/generate.py` — main CLI (--steps, --guidance, --seed, --width, --height, --refiner, --device)
- `image-generation/generate_blog_images.sh` — batch generation script (5 blog images, seeds 42–46)
- `image-generation/prompts/examples.md` — master prompt library and style guide
- `image-generation/outputs/` — generated 1024×1024 PNG images
- `image-generation/requirements.txt` — Python dependencies (diffusers, transformers, torch, Pillow)

**Stack:** Python 3.10+, diffusers, transformers, torch, Pillow. GPU-first (CUDA/MPS/CPU fallback).

### mermaid-diagrams/

(Planned) Diagram generation from text descriptions.

## Making Decisions

If you make a decision that affects other team members, write it to:
```
.squad/decisions/inbox/copilot-{brief-slug}.md
```
Scribe will merge it into the shared decisions ledger.

## Branch Naming (for issue work)

```
squad/{issue-number}-{kebab-case-slug}
```

## Squad Coordinator

The Squad coordinator is defined in `.github/agents/squad.agent.md`. Start a session with Squad to get full team orchestration.
