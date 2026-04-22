← [Back to Documentation Index](../README.md)

# Manim Animation — Troubleshooting Guide

Common issues, error messages, and solutions for the manim-animation package.

---

## Quick Reference: Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (LLM, validation, or render failure) |
| 2 | CLI argument error |

---

## 1. FFmpeg Not Found

**Symptom:** Manim render fails with a subprocess error mentioning FFmpeg.

**Cause:** Manim Community Edition requires FFmpeg for video encoding.

**Solution:**

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows (via chocolatey)
choco install ffmpeg
```

Verify: `ffmpeg -version`

---

## 2. LaTeX Not Found

**Symptom:** `MathTex` objects fail to render.

**Cause:** `MathTex` requires a LaTeX installation. `Text` with Unicode superscripts works without it.

**Solution:**

```bash
# macOS
brew install --cask mactex-no-gui

# Ubuntu/Debian
sudo apt install texlive-full

# Windows
# Install MiKTeX from https://miktex.org/
```

**Workaround:** Use `Text("a² + b² = c²")` instead of `MathTex("a^2 + b^2 = c^2")` if LaTeX is unavailable.

---

## 3. Manim CLI Not Found

**Error:**
```
RenderError: manim CLI not found. Install with: pip install manim
Requires FFmpeg: https://docs.manim.community/en/stable/installation.html
```

**Cause:** The `manim` package is not installed or not on PATH.

**Solution:**
```bash
pip install manim
# Verify
manim --version
```

---

## 4. Ollama Not Running

**Error:**
```
LLMError: <connection error to http://localhost:11434>
```

**Cause:** Ollama server is not running or listening on a non-default port.

**Solution:**
```bash
# Start Ollama
ollama serve

# Pull required model
ollama pull llama3

# Verify
curl http://localhost:11434/api/tags
```

**Custom host:** Set `OLLAMA_HOST` environment variable if not using default port.

---

## 5. OpenAI / Azure API Key Issues

**Error (OpenAI):**
```
LLMError: OpenAI requires OPENAI_API_KEY environment variable
```

**Error (Azure):**
```
LLMError: Azure OpenAI requires AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT
```

**Solution:**
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Azure OpenAI (all three required)
export AZURE_OPENAI_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

---

## 6. Unknown LLM Provider

**Error:**
```
LLMError: Unknown provider 'xxx'. Use 'ollama', 'openai', or 'azure'.
```

**Cause:** Invalid `--provider` flag value.

**Solution:** Use one of: `ollama` (default), `openai`, or `azure`.

---

## 7. LLM Returns Invalid Code

**Error:**
```
ValidationError: No valid Python code block found in LLM output
```

**Cause:** The LLM response didn't contain a recognizable Python code block or a `class GeneratedScene`.

**Solutions:**
- Rephrase the prompt to be more specific
- Try a different model (`ollama pull codellama`)
- Use `--debug` to inspect the raw LLM output saved to the output directory
- Simpler prompts produce more reliable results

---

## 8. AST Validation — Forbidden Imports

**Error:**
```
ValidationError: Forbidden import: os. Only {'manim', 'math', 'numpy'} are allowed.
```

**Cause:** The LLM generated code that imports modules outside the security whitelist.

**Allowed imports:** `manim`, `math`, `numpy` only.

**Solution:** Rephrase the prompt. The security model blocks imports like `os`, `sys`, `subprocess`, `random`, etc. If the LLM keeps generating forbidden imports, simplify your prompt.

---

## 9. AST Validation — Forbidden Function Calls

**Error:**
```
ValidationError: Forbidden function call: exec
```

**Cause:** Generated code calls a dangerous built-in function.

**Blocked functions:** `open`, `exec`, `eval`, `__import__`, `compile`, `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `dir`, `breakpoint`, `input`

**Solution:** Rephrase the prompt. This is a security feature that cannot be disabled.

---

## 9a. AST Validation — Forbidden Names

**Error:**
```
ValidationError: Forbidden name referenced: __import__
```

**Cause:** Generated code references a dangerous built-in name. Even without calling the function, **referencing** these names is blocked by the AST validator.

**Forbidden names (never allowed):**
- `__import__` — Module loading
- `__builtins__` — Built-in namespace access
- `__loader__` — Module loader access
- `__spec__` — Module specification access

These names are dangerous because:
1. They grant access to Python internals
2. They can be used to bypass security restrictions
3. They pose a security risk in untrusted code environments

**Solution:** Rephrase the prompt to avoid any reference to these names. If the LLM keeps generating code with these references, try:
- Simplifying the prompt
- Using a more instruction-following model (e.g., GPT-4 vs Llama)
- Providing examples of safe code patterns

---

## 10. Syntax Errors in Generated Code

**Error:**
```
ValidationError: Generated code has syntax error: <details>
```

**Cause:** The LLM produced syntactically invalid Python.

**Solutions:**
- Try a more capable model (e.g., `gpt-4` via `--provider openai`)
- Simplify the prompt
- Use `--debug` to inspect the generated code

---

## 11. Scene Class Not Found

**Symptom:** Manim render fails because it can't find `GeneratedScene` in the file.

**Cause:** The LLM used a different class name (e.g., `MyScene` instead of `GeneratedScene`).

**Solution:** The renderer always looks for `GeneratedScene`. If the LLM doesn't follow the system prompt, try rephrasing or using a more instruction-following model.

---

## 12. Duration Out of Range

**Error:**
```
ValueError: Duration must be between 5 and 30 seconds
```

**Cause:** `--duration` value outside the 5–30 second range.

**Solution:** Use `--duration` between 5 and 30 (inclusive). Default is 10.

---

## 13. Invalid Quality Preset

**Error:**
```
KeyError: 'ULTRA'
```

**Cause:** Invalid `--quality` value.

**Valid values:**
| Preset | Resolution | FPS |
|--------|-----------|-----|
| `low` | 480p | 15 |
| `medium` | 720p | 30 |
| `high` | 1080p | 60 |

---

## 14. Image Validation Errors

**Error (not found):**
```
ImageValidationError: Image not found: /path/to/image.png
```

**Error (bad format):**
```
ImageValidationError: Unsupported image format '.svg'. Allowed: ['.bmp', '.gif', '.jpeg', '.jpg', '.png', '.tiff', '.tif', '.webp']
```

**Error (too large):**
```
ImageValidationError: Image exceeds 100 MB limit
```

**Error (symlink):**
```
ImageValidationError: Symlinks not allowed: /path/to/link.png
```

**Notes:**
- SVG is intentionally excluded — Manim uses `SVGMobject` for SVGs, not `ImageMobject`
- Maximum file size: 100 MB
- Symlinks are rejected before path resolution (security measure)
- Policy modes: `strict` (raise), `warn` (log), `ignore` (skip)

---

## 15. Manim Render Subprocess Failure

**Error:**
```
RenderError: Manim render failed (exit code X): <stderr output>
```

**Common causes:**
- Generated code uses deprecated Manim API
- Missing assets referenced in the scene
- Memory issues with complex scenes

**Debug steps:**
1. Run with `--debug` to save the generated `.py` file
2. Try rendering manually: `manim render <file.py> GeneratedScene -qm`
3. Check Manim version: `manim --version`

---

## 16. Output Directory Permissions

**Error:** `PermissionError` or `OSError` when writing output.

**Solution:**
```bash
# Check/fix permissions
mkdir -p outputs
chmod 755 outputs

# Or specify a writable directory
manim-gen --prompt "..." --output /tmp/my-video.mp4
```

---

## 17. Python Version Compatibility

**Requirement:** Python 3.10+

**Check:**
```bash
python --version
```

**Solution:** Use pyenv or conda to manage Python versions:
```bash
pyenv install 3.10.14
pyenv local 3.10.14
```

---

## 18. pip Dependency Conflicts

**Symptom:** Conflicting version requirements during `pip install`.

**Solution:**
```bash
# Clean virtual environment
python -m venv .venv --clear
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

---

## 19. Slow Rendering

**Cause:** High quality settings + complex scenes.

**Solutions:**
- Use `--quality low` for quick previews
- Reduce `--duration` while iterating
- Simplify the prompt (fewer objects/animations)
- Manim caching is disabled (`--disable_caching`) by design to avoid stale cache issues

---

## 20. General Debug Workflow

1. **Add `--debug`** to save intermediate files (LLM output, generated scene code)
2. **Check the generated `.py` file** in the output directory
3. **Try manual render:** `manim render scene.py GeneratedScene -qm`
4. **Check logs:** Logging uses `%(asctime)s [%(levelname)s] %(name)s: %(message)s` format
5. **Try a simpler prompt** to isolate whether the issue is prompt-dependent
6. **Try a different provider** (`--provider openai` vs `--provider ollama`)
