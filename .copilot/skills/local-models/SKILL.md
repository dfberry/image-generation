---
name: local-models
description: Documents locally available AI models via Ollama and how to use them with project tools
confidence: medium
---
# Local Models

## Provider

- **Provider:** Ollama
- **Endpoint:** `http://localhost:11434`

## Available Models

| Model | Size | Best For |
|-------|------|----------|
| `qwen2.5-coder:32b` | 19 GB | Code generation, structured JSON output, scene planning |
| `llama3:latest` | 4.7 GB | General purpose text generation |

## Common Gotcha

⚠️ **`llama3.2` is NOT installed.** The story-video tool defaults to `llama3.2`, which will fail. Always pass an explicit `--model` flag.

## Usage with story-video

The story-video tool uses Ollama for both scene planning (text) and SDXL image generation (via `generate.py`).

### Recommended: Scene Planning

Use `qwen2.5-coder:32b` for scene planning — it produces better structured JSON output:

```bash
story-video --model qwen2.5-coder:32b
```

### General Purpose

Use `llama3:latest` for general text tasks:

```bash
story-video --model llama3:latest
```

## Adding New Models

To add a model locally:

```bash
ollama pull <model-name>
```

Update this skill file when models are added or removed so agents stay in sync.
