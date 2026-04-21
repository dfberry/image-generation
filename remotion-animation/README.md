# remotion-animation

Generate animated videos from text prompts using Remotion and LLMs.

This is a Phase 0 Proof of Concept: Python CLI → LLM → TSX component → Remotion render → MP4.

## What This Does

**remotion-gen** is a CLI tool that turns natural language descriptions into animated videos. You describe what you want to see, a local LLM (via Ollama) generates a Remotion React component, and Remotion renders it to MP4.

Architecture: Python CLI orchestrator wraps a Node.js/Remotion project (same pattern as `mermaid-diagrams` uses `mmdc` subprocess).

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm ([install from nodejs.org](https://nodejs.org/))
- **Ollama** (default, local inference — no API key needed)
  - Install: `curl -fsSL https://ollama.com/install.sh | sh`
  - Windows: [Download from ollama.com](https://ollama.com/download)

## Installation

### 1. Install Python package
```bash
cd remotion-animation
pip install -e .
```

### 2. Install Node.js dependencies
```bash
cd remotion-project
npm install
cd ..
```

### 3. Set up LLM

**Option A: Ollama (default — local, no API key)**
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3
```

**Option B: OpenAI (cloud)**
```bash
export OPENAI_API_KEY="sk-..."
```

**Option C: Azure OpenAI (cloud)**
```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

## Quick Start

### Example 1: Simple rotation (uses Ollama by default)
```bash
remotion-gen --prompt "A blue circle rotating 360 degrees" --output circle.mp4
```

### Example 2: Text animation with specific model
```bash
remotion-gen --prompt "Text saying 'Hello World' fading in and out" --model codellama --quality high --duration 10 --output fade.mp4
```

### Example 3: Using OpenAI instead
```bash
remotion-gen --prompt "Multiple colorful squares bouncing around" --provider openai --output bounce.mp4
```

### Example 4: Debug mode
```bash
remotion-gen --prompt "Multiple colorful squares bouncing around" --debug --output bounce.mp4
```

The `--debug` flag saves the LLM-generated TSX component to `outputs/GeneratedScene.debug.tsx` for inspection.

## How It Works

1. **CLI (`remotion_gen/cli.py`)** accepts `--prompt`, `--output`, `--quality`, `--duration`, `--provider`, `--model`, `--debug`
2. **LLM Client (`llm_client.py`)** calls Ollama/OpenAI/Azure OpenAI to generate a valid Remotion React component
3. **Component Builder (`component_builder.py`)** validates the TSX code and writes it to `remotion-project/src/GeneratedScene.tsx`
4. **Renderer (`renderer.py`)** invokes `npx remotion render` to produce the MP4

## Quality Presets

- `low`: 480p @ 15fps
- `medium`: 720p @ 30fps (default)
- `high`: 1080p @ 60fps

## Phase 0 Limitations

- **5-30 second videos only** (enforced by CLI)
- **No audio** (video-only)
- **Single-scene compositions** (no multi-scene sequencing)
- **2D animations only** (no Three.js integration)
- **Happy path focus** (basic error handling, no advanced retry logic)
- **Hardcoded few-shot examples** in LLM system prompt

## File Structure

```
remotion-animation/
├── remotion_gen/              # Python package
│   ├── cli.py                 # CLI entry point
│   ├── config.py              # Quality presets
│   ├── errors.py              # Custom exceptions
│   ├── llm_client.py          # OpenAI/Azure OpenAI wrapper
│   ├── component_builder.py   # TSX validator & writer
│   └── renderer.py            # Remotion CLI wrapper
├── remotion-project/          # Node.js Remotion project
│   ├── src/
│   │   ├── index.ts           # Remotion entry point
│   │   ├── Root.tsx            # Composition registry
│   │   ├── GeneratedScene.tsx  # LLM-generated component (runtime)
│   │   └── templates/
│   │       ├── TextFade.tsx    # Example: text fade animation
│   │       └── ShapeRotate.tsx # Example: shape rotation
│   ├── package.json
│   └── tsconfig.json
├── outputs/                   # Generated MP4s (gitignored)
├── tests/                     # Test suite (Neo owns this)
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Development

Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests (when Neo writes them):
```bash
pytest
```

Lint:
```bash
ruff check .
```

## Troubleshooting

### "Node.js not found"
Install Node.js from https://nodejs.org/

### "Dependencies not installed"
Run: `cd remotion-project && npm install`

### "No API key found" / "LLM API call failed"
- For Ollama (default): ensure Ollama is running (`ollama serve`) and model is pulled (`ollama pull llama3`)
- For OpenAI: set `OPENAI_API_KEY`
- For Azure: set Azure OpenAI environment variables
- Custom Ollama host: `export OLLAMA_HOST="http://my-server:11434"`

### Render fails with "npx command not found"
Ensure npm is in your PATH after installing Node.js

## License

Part of the `image-generation` multi-tool repository.
