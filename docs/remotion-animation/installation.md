← [Back to Documentation Index](../README.md)

# remotion-animation — Installation Guide

## System Requirements

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.10+ | 3.10, 3.11, 3.12 tested |
| Node.js | 18+ | Required for Remotion rendering |
| npm | (bundled with Node.js) | Manages Remotion dependencies |
| OS | Windows, macOS, Linux | See platform notes below |

## Step-by-Step Installation

### 1. Install the Python package

```bash
cd remotion-animation
pip install -e .
```

This installs:
- `openai>=1.0.0` — OpenAI SDK (used for all LLM providers via compatible API)
- Registers `remotion-gen` as a CLI command

### 2. Install Node.js dependencies

```bash
cd remotion-project
npm install
cd ..
```

This installs Remotion 4.0.450, React 18.2.0, and TypeScript. The `node_modules/` folder is required — the renderer checks for it at runtime.

### 3. Set up an LLM provider

#### Option A: Ollama (default — local, free, no API key)

Ollama is the default provider. Install it, then pull a model:

**Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```

**Windows:**
Download from [ollama.com/download](https://ollama.com/download), then:
```powershell
ollama pull llama3
```

Ollama must be running when you use remotion-gen. Start it with:
```bash
ollama serve
```

Custom host (if Ollama runs on a different machine):
```bash
export OLLAMA_HOST="http://my-server:11434"
```

#### Option B: OpenAI (cloud)

```bash
export OPENAI_API_KEY="sk-..."
```

Use with `--provider openai`. Default model: `gpt-4`.

#### Option C: Azure OpenAI (cloud)

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

All three environment variables are required. Use with `--provider azure`.

## Verifying Installation

```bash
remotion-gen --help
```

Expected output:
```
usage: remotion-gen [-h] [--prompt PROMPT] [--demo] --output OUTPUT
                    [--quality {low,medium,high}] [--duration DURATION]
                    [--provider {ollama,openai,azure}] [--model MODEL]
                    [--debug] [--image IMAGE]
                    [--image-description IMAGE_DESCRIPTION]
                    [--image-policy {strict,warn,ignore}]
```

Quick smoke test with demo mode (no LLM required):
```bash
remotion-gen --demo --output demo.mp4
```

This uses a pre-built template to generate a title card video, confirming both Python and Node.js stacks work.

## Installing Dev Dependencies

For running tests and linting:

```bash
pip install -r requirements-dev.txt
```

Or via the optional extras:
```bash
pip install -e ".[dev]"
```

Verify:
```bash
python -m pytest tests/ -q    # Should show 209 passed (1 skipped on Windows)
ruff check .                   # Should show no errors
```

## Platform Notes

### Windows (PowerShell)

**TSX template backtick issue:** PowerShell interprets backtick (`` ` ``) as an escape character. If you're writing inline TSX with template literals in PowerShell commands, use Python script files instead of inline strings.

**Symlinks:** One test (`test_symlink_rejected_strict`) is automatically skipped on Windows because symlink creation requires elevated privileges. This does not affect functionality.

**npx resolution:** On Windows, npx is installed as `npx.cmd`. The renderer uses `shutil.which("npx")` which handles this automatically.

### macOS

No known issues. Both Intel and Apple Silicon work. If using Apple Silicon, ensure your Python and Node.js are both native ARM or both Rosetta — avoid mixing.

### Linux

No known issues. Standard package manager installations of Python and Node.js work.

## Troubleshooting Installation

### "remotion-gen: command not found"

The `pip install -e .` step registers the CLI. Ensure your Python scripts directory is on PATH:
```bash
pip install -e .
# or try:
python -m remotion_gen.cli --help
```

### "Node.js not found" or "npm not found"

Install Node.js 18+ from [nodejs.org](https://nodejs.org/). Verify:
```bash
node --version   # Should be v18+
npm --version
```

### "Dependencies not installed"

Run `npm install` inside the `remotion-project/` directory:
```bash
cd remotion-project
npm install
```

### "LLM API call failed" / connection errors

- **Ollama:** Ensure it's running (`ollama serve`) and the model is pulled (`ollama pull llama3`).
- **OpenAI:** Verify `OPENAI_API_KEY` is set and valid.
- **Azure:** Verify all three env vars (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`) are set.

### "npx command not found"

Ensure npm's global bin directory is on PATH. Reinstalling Node.js usually fixes this.

### "Failed to import openai library"

The `openai` package is required:
```bash
pip install openai>=1.0.0
```
