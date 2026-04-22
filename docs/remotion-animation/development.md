← [Back to Documentation Index](../README.md)

# remotion-animation — Developer Guide

## Dual-Stack Repository Structure

This package is a hybrid Python + Node.js project:

```
remotion-animation/
├── remotion_gen/              Python package (CLI + orchestration)
│   ├── __init__.py
│   ├── cli.py                 CLI entry point, generate_video()
│   ├── llm_client.py          LLM API wrapper (Ollama/OpenAI/Azure)
│   ├── component_builder.py   TSX validation, import injection, writer
│   ├── renderer.py            Subprocess wrapper for Remotion CLI
│   ├── config.py              Quality presets, provider temps, constants
│   ├── errors.py              Exception hierarchy
│   ├── image_handler.py       Image validation, copy, LLM context
│   └── demo_template.py       Pre-built demo TSX template
├── remotion-project/          Node.js Remotion sub-project
│   ├── src/
│   │   ├── index.ts           registerRoot(Root)
│   │   ├── Root.tsx            Composition registry
│   │   ├── GeneratedScene.tsx  Runtime slot (overwritten each run)
│   │   └── templates/          Reference TSX examples
│   ├── public/                 Static assets (images copied here)
│   ├── package.json            Dependencies (Remotion, React, TS)
│   └── tsconfig.json
├── tests/                     Python test suite (209+ tests)
├── outputs/                   Generated videos + debug files
├── pyproject.toml             Python build config + tool settings
├── requirements.txt           Runtime deps (openai>=1.0.0)
└── requirements-dev.txt       Dev deps (pytest, ruff)
```

## Coding Conventions

### Python (remotion_gen/)

Linted with **ruff**. Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
```

- **E** — pycodestyle errors
- **F** — pyflakes
- **I** — isort (import sorting)
- **N** — pep8-naming
- **W** — pycodestyle warnings
- **E501** is globally ignored (line length). `llm_client.py` has additional per-file E501 ignore for long TSX prompt strings.

Run the linter:

```bash
cd remotion-animation
ruff check .
```

### TypeScript/Node.js (remotion-project/)

- TypeScript 5.5.4 with strict config
- React 18.2.0 (pinned — Remotion 4.0.450 requires this exact version)
- Inline styles only — no CSS modules, styled-components, or className usage
- All Remotion components import from `'remotion'` only

## How to Add a New LLM Provider

1. **Update `_create_client()` in `llm_client.py`** — Add a new `if provider == "your_provider":` block that returns an OpenAI-compatible client and default model name. All providers use the OpenAI SDK's chat completions API.

2. **Add default model** — Add entry to `DEFAULT_MODELS` dict:
   ```python
   DEFAULT_MODELS = {
       "ollama": "llama3",
       "openai": "gpt-4",
       "your_provider": "model-name",
   }
   ```

3. **Set temperature** — Add entry to `PROVIDER_TEMPERATURES` in `config.py`:
   ```python
   PROVIDER_TEMPERATURES = {
       "ollama": 0.4,
       "openai": 0.7,
       "azure": 0.7,
       "your_provider": 0.7,
   }
   ```

4. **Register CLI choice** — Add to the `--provider` choices list in `cli.py`:
   ```python
   parser.add_argument(
       "--provider",
       choices=["ollama", "openai", "azure", "your_provider"],
       ...
   )
   ```

5. **Add tests** — Add `_create_client("your_provider")` tests to `tests/test_llm_client.py` covering success and missing-credentials cases.

6. **Document env vars** — Add environment variable requirements to the CLI epilog in `cli.py` and to the installation docs.

## How to Add New Templates

Templates live in `remotion-project/src/templates/`. They are reference implementations, not used at runtime.

1. Create a new `.tsx` file in `templates/`:
   ```tsx
   // remotion-project/src/templates/MyAnimation.tsx
   import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

   export default function MyAnimation() {
     const frame = useCurrentFrame();
     const {fps, durationInFrames} = useVideoConfig();
     // ... animation logic
     return (
       <AbsoluteFill style={{backgroundColor: '#000'}}>
         {/* ... */}
       </AbsoluteFill>
     );
   }
   ```

2. Follow the same conventions the system prompt enforces:
   - Name as `export default function`
   - Import only from `'remotion'`
   - Use inline styles
   - Use `{extrapolateRight: 'clamp'}` on all `interpolate()` calls
   - Destructure `fps` and `durationInFrames` from `useVideoConfig()`

## How Component Injection Works

The core mechanism is file overwrite:

1. `GeneratedScene.tsx` in `remotion-project/src/` is the **runtime slot** — it gets overwritten on every generation.
2. `Root.tsx` imports `GeneratedScene` and registers it as a `<Composition>`:
   ```tsx
   import GeneratedScene from './GeneratedScene';
   // ...
   <Composition id="GeneratedScene" component={GeneratedScene} ... />
   ```
3. When `npx remotion render` runs, it picks up the freshly-written `GeneratedScene.tsx`.
4. Props (`durationInFrames`, `fps`, `width`, `height`) are passed via `--props` JSON and read by `Root.tsx` via `getInputProps()`.

## How to Extend TSX Validation

### Adding new dangerous imports

Edit `DANGEROUS_IMPORTS` frozenset in `component_builder.py`:

```python
DANGEROUS_IMPORTS = frozenset([
    "fs", "node:fs", "fs/promises", ...
    "your_new_module",       # add here
    "node:your_new_module",  # add node: variant
])
```

If the module has subpath exports, also add to `_DANGEROUS_PREFIXES`.

### Adding new Remotion symbol auto-imports

Edit `_REMOTION_HOOKS` list in `component_builder.py`:

```python
_REMOTION_HOOKS = [
    "useCurrentFrame", "useVideoConfig", "spring", "interpolate",
    "Sequence", "AbsoluteFill", "Img", "staticFile", ...
    "YourNewSymbol",  # add here
]
```

### Adding new JSX tag closure checks

Edit the tag list in `validate_tsx_syntax()`:

```python
for tag in ["AbsoluteFill", "Sequence", "div", "Img", "YourTag"]:
```

### Adding new image security checks

Add patterns to `validate_image_paths()` in `component_builder.py`. Follow the existing pattern of regex-based detection with `ValidationError` raises.

## Branch Naming

For issue-linked work:

```
squad/{issue-number}-{kebab-case-slug}
```

Example: `squad/92-import-injection`

## PR Workflow

1. Create feature branch from `main`
2. Make changes, run `ruff check .` and `python -m pytest tests/ -q`
3. Commit with descriptive message
4. Open PR — Neo reviews test coverage, Morpheus reviews architecture
5. If you made a team-relevant decision, write to `.squad/decisions/inbox/`

## Dependency Management

### Python

- **Runtime deps** in `requirements.txt` and `pyproject.toml [project.dependencies]`:
  - `openai>=1.0.0` — OpenAI SDK (used for all providers via compatible API)

- **Dev deps** in `requirements-dev.txt` and `pyproject.toml [project.optional-dependencies.dev]`:
  - `pytest>=7.0.0`
  - `ruff>=0.1.0`

- Install for development:
  ```bash
  pip install -e .
  pip install -r requirements-dev.txt
  ```

### Node.js

Key pinned versions in `remotion-project/package.json`:

| Package | Version | Notes |
|---------|---------|-------|
| remotion | 4.0.450 | Core rendering engine |
| @remotion/cli | 4.0.450 | CLI for render commands |
| @remotion/player | 4.0.450 | Player component |
| react | 18.2.0 | **Pinned** — Remotion 4.x requires this exact version |
| react-dom | 18.2.0 | **Pinned** — matches React |
| typescript | 5.5.4 | TypeScript compiler |
| @types/react | 18.2.0 | React type definitions |

The `package.json` also includes `overrides` to enforce consistent Remotion sub-package versions across the dependency tree.

Install:

```bash
cd remotion-project
npm install
```
