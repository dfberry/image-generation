← [Back to Documentation Index](../README.md)

# remotion-animation — Architecture

## Overview

**remotion-gen** is a hybrid Python + Node.js pipeline that converts natural language prompts into animated MP4 videos. A Python CLI orchestrates an LLM call, validates the generated code, and delegates rendering to a Node.js Remotion sub-project.

```
User Prompt
    │
    ▼
┌──────────────────────────────────────────────┐
│  Python CLI  (remotion_gen/cli.py)            │
│  • Parses flags, resolves paths               │
│  • Coordinates pipeline steps                 │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  Image Handler  (image_handler.py)  [opt]     │
│  • Validates image (ext, size, symlink)        │
│  • Copies to remotion-project/public/          │
│  • Generates LLM context for image usage       │
└──────────┬───────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│  LLM Client  (llm_client.py)                  │
│  • Calls Ollama / OpenAI / Azure OpenAI        │
│  • System prompt enforces Remotion conventions │
│  • Extracts TSX from markdown fences           │
│  • Validates syntax, retries on errors         │
└──────────┬───────────────────────────────────┘
           │  raw TSX code
           ▼
┌──────────────────────────────────────────────┐
│  Component Builder  (component_builder.py)    │
│  • Import injection (ensure_remotion_imports)  │
│  • Image import injection (Img, staticFile)    │
│  • TSX syntax validation (brackets, tags)      │
│  • Dangerous import rejection (security)       │
│  • Structural validation (remotion, export)     │
│  • Writes GeneratedScene.tsx to project         │
└──────────┬───────────────────────────────────┘
           │  validated TSX written to disk
           ▼
┌──────────────────────────────────────────────┐
│  Renderer  (renderer.py)                      │
│  • Checks prerequisites (node, npm, npx)       │
│  • Runs: npx remotion render src/index.ts      │
│  • Passes --width, --height, --fps, --props    │
│  • Returns path to rendered MP4                │
└──────────┬───────────────────────────────────┘
           │
           ▼
       output.mp4
```

## Module Breakdown

## Module Breakdown

### cli.py — Entry Point

- **`generate_video()`** — Programmatic entry point. Accepts prompt, output path, quality, duration, provider, model, debug, image options, and optional pre-built component code. Orchestrates the full pipeline: image handling → LLM generation → component writing → rendering.
- **`main()`** — CLI entry point registered as `remotion-gen` console script. Parses `argparse` arguments and calls `generate_video()`. Handles `--demo` mode (bypasses LLM with pre-built template).

### audio_handler.py — Audio Pipeline

- **`validate_audio_path()`** — Checks symlinks, existence, format (`.wav`, `.mp3`, `.ogg`), size (≤100MB). Policy modes: `strict`, `warn`, `ignore`.
- **`copy_audio_to_public()`** — Copies audio to `remotion-project/public/` with UUID-based safe filename.
- **`generate_audio_context()`** — Builds LLM prompt context explaining `<Audio>` component usage for narration, music, and sound effects.

### tts_providers.py — Text-to-Speech

- **`EdgeTTSProvider.generate()`** — Generates speech from text using edge-tts (free, no API key). Outputs MP3 natively.
- **`get_tts_provider()`** — Factory returning TTS provider by name. Phase 0 supports `edge-tts` only.
- **`generate_narration()`** — High-level API: text → MP3 file path. Uses default voice if not specified.

### llm_client.py — LLM Integration

- **Lazy OpenAI import** — `from openai import OpenAI` happens inside `_create_client()`, not at module level. The module can be imported without the `openai` package installed.
- **`_create_client(provider)`** — Factory returning an OpenAI-compatible client + model name for `ollama`, `openai`, or `azure` providers.
- **`_call_llm()`** — Single API call wrapper. Uses `SYSTEM_PROMPT` with strict Remotion coding rules.
- **`_extract_code_block()`** — Strips markdown fences from LLM responses.
- **`generate_component()`** — High-level function with retry loop. Calls `_call_llm()`, validates TSX syntax with `validate_tsx_syntax()`, and retries up to `max_retries` times by feeding errors back to the model.
- **`PROVIDER_TEMPERATURES`** from config controls sampling temperature per provider (0.4 for Ollama, 0.7 for OpenAI/Azure).

### component_builder.py — Validation & Writing

- **Import injection** — `ensure_remotion_imports()` scans for used Remotion symbols (`useCurrentFrame`, `interpolate`, `spring`, `Img`, `staticFile`, etc.) and adds missing ones to the import statement. Post-injection validation confirms each symbol was successfully injected.
- **Image import injection** — `inject_image_imports()` adds `Img`, `staticFile`, and an `imageSrc` constant when an image file is provided.
- **TSX syntax validation** — `validate_tsx_syntax()` checks bracket/paren/brace balance and JSX tag closure. Returns a list of errors (empty = valid).
- **Security validation** — `validate_imports()` blocks 30+ dangerous Node.js built-in modules (`fs`, `child_process`, `http`, `net`, `os`, `crypto`, `vm`, `worker_threads`, etc.) via import, require(), and bare import patterns.
- **Component structure validation** — `validate_component()` verifies: remotion import present, `export default` present, `GeneratedScene` name used, `return` statement exists.
- **`write_component()`** — Full pipeline: image injection → import injection → syntax check → structural validation → write to `remotion-project/src/GeneratedScene.tsx`. Optionally saves debug copy to `outputs/GeneratedScene.debug.tsx`.

### renderer.py — Subprocess Wrapper

- **`check_prerequisites()`** — Verifies `node` and `npm` are on PATH.
- **`render_video()`** — Builds and runs `npx remotion render src/index.ts GeneratedScene <output> --codec=h264 --width=W --height=H --fps=F --props=JSON`. Checks for `node_modules/` existence. Returns output path on success, raises `RenderError` with stderr on failure.

### config.py — Configuration

- **`QualityPreset`** — Dataclass with `width`, `height`, `fps`, and a `resolution_name` property.
- **`QUALITY_PRESETS`** — `low` (854×480 15fps), `medium` (1280×720 30fps), `high` (1920×1080 60fps).
- **`PROVIDER_TEMPERATURES`** — `ollama: 0.4`, `openai: 0.7`, `azure: 0.7`. Lower temperature for local models reduces structural errors.
- **Duration constants** — `DEFAULT_DURATION_SECONDS = 5`, `MIN = 5`, `MAX = 30`.
- **`DEFAULT_PROVIDER = "ollama"`**.

### errors.py — Exception Hierarchy

```
RemotionGenError          Base exception (catch-all)
├── LLMError              Auth, rate limit, timeout, bad response
├── RenderError           npx/node not found, non-zero exit, missing output
├── ValidationError       Bracket mismatch, forbidden imports, structural
└── ImageValidationError  Bad paths, unsupported formats, symlinks, oversized
```

### image_handler.py — Image Pipeline

- **`validate_image_path()`** — Checks: symlink rejection, existence, is-file, extension (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.svg`), size (max 100 MB). Supports `strict`, `warn`, and `ignore` policies.
- **`copy_image_to_public()`** — Copies image to `remotion-project/public/` with a UUID-based safe filename (`image_<hex8>.<ext>`).
- **`generate_image_context()`** — Builds LLM prompt context explaining how to use `Img` and `staticFile()` for the copied image.

### demo_template.py — Pre-built Template

- **`get_demo_component(datetime_str)`** — Returns a complete `GeneratedScene` TSX component with a "Dina Berry" title card animation. Bypasses LLM entirely for `--demo` mode.

## Remotion Project Structure (Node.js)

```
remotion-project/
├── src/
│   ├── index.ts              Remotion entry: registerRoot(Root)
│   ├── Root.tsx               Composition registry — reads inputProps
│   │                          (durationInFrames, fps, width, height)
│   ├── GeneratedScene.tsx     Runtime slot — overwritten each generation
│   └── templates/
│       ├── TextFade.tsx       Example: text fade animation
│       └── ShapeRotate.tsx    Example: shape rotation animation
├── public/                    Static assets (user images copied here)
├── package.json               Remotion 4.0.450, React 18.2.0, TypeScript 5.5.4
└── tsconfig.json
```

**Root.tsx** acts as the composition registry. It imports `GeneratedScene` (the runtime slot) and registers it as a `<Composition>` with props from `getInputProps()` — this is how the Python CLI passes `durationInFrames`, `fps`, `width`, and `height` to the Remotion renderer.

**GeneratedScene.tsx** is the file that gets overwritten on every generation. The LLM generates this component, `component_builder.py` validates and writes it, then Remotion renders it.

**templates/** contains reference implementations that serve as examples for LLM prompting and developer reference. They are not used at runtime.

## Image Handling Pipeline

1. User provides `--image photo.png` (optionally `--image-description`)
2. `validate_image_path()` — checks symlinks, existence, extension, size
3. `copy_image_to_public()` — copies to `public/image_<uuid>.png`
4. `generate_image_context()` — builds LLM prompt explaining `Img`/`staticFile` usage
5. LLM generates TSX that uses `staticFile('image_<uuid>.png')`
6. `inject_image_imports()` — ensures `Img` and `staticFile` are imported
7. `validate_image_paths()` — blocks `file://`, path traversal, non-matching `staticFile()` refs

## Security Model

### TSX Validation (component_builder.py)

The component builder implements defense-in-depth against LLM-generated code executing arbitrary operations:

1. **Dangerous import blocking** — Rejects 30+ Node.js built-ins (`fs`, `child_process`, `http`, `net`, `os`, `crypto`, `vm`, `worker_threads`, etc.) via regex matching on `import ... from`, `import '...'`, and `require()` patterns. Includes `node:` prefixed variants and subpath imports (e.g., `fs/promises`).

2. **Image path validation** — Blocks `file://` URLs (case-insensitive + URL-encoded variants), `data:` URIs, path traversal (`../`, `..\`, URL-encoded `%2E%2E%2F`), non-matching `staticFile()` references, and dynamic `staticFile()` calls (template literals, variables, function calls).

3. **Structural validation** — Ensures generated code has a remotion import, `export default`, `GeneratedScene` name, and a `return` statement.

4. **Bracket validation** — Catches the most common LLM failure: mismatched brackets, parentheses, and braces. Also checks JSX tag closure for `AbsoluteFill`, `Sequence`, `div`, and `Img`.

5. **Import injection with verification** — After auto-injecting missing Remotion imports, verifies each injection succeeded. Raises `ValidationError` if injection fails (prevents silent corruption).
