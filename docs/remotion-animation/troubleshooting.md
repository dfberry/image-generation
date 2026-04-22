← [Back to Documentation Index](../README.md)

# Troubleshooting Guide

This guide covers common errors and how to resolve them when using `remotion-gen`.

---

## Node.js & npm Issues

### Error: "Node.js not found" or "node: command not found"

**Root Cause:** Node.js is not installed or not in your system PATH.

**Solution:**
1. Install Node.js 18+ from [nodejs.org](https://nodejs.org/)
2. Choose the **LTS version** (18.x or later)
3. After installation, verify:
   ```bash
   node --version    # Should be v18.0.0 or higher
   npm --version     # Should be 8.0.0 or higher
   ```
4. On Windows, restart your terminal after installing Node.js for PATH changes to take effect.

---

### Error: "npm not found" or "npm: command not found"

**Root Cause:** npm is not installed or not in PATH. This is usually bundled with Node.js.

**Solution:**
1. Reinstall Node.js from [nodejs.org](https://nodejs.org/) — npm is included in the installer.
2. Verify npm is in your PATH:
   ```bash
   npm --version
   ```
3. If installed but still not found, try adding Node.js to your PATH manually (system-dependent — see OS documentation).

---

### Error: "npx command not found"

**Root Cause:** npx (npm's package runner) is not available, even though npm is installed.

**Solution:**
1. Verify npm version is 5.2.0+:
   ```bash
   npm --version
   ```
2. If npm is older, update it:
   ```bash
   npm install -g npm@latest
   ```
3. On Windows, npx is installed as `npx.cmd` — the system should auto-detect it. If not, restart your terminal.
4. Manually verify the npx path:
   ```bash
   which npx        # macOS/Linux
   where npx        # Windows (PowerShell)
   ```

---

## Dependencies Not Installed

### Error: "Dependencies not installed. Run: npm install"

**Root Cause:** The Remotion project's `node_modules/` folder is missing or incomplete.

**Solution:**
```bash
cd remotion-animation/remotion-project
npm install
cd ..
```

This installs all required packages:
- `remotion` (4.0.450)
- `@remotion/cli` (4.0.450)
- `react` (18.2.0)
- `react-dom` (18.2.0)
- TypeScript and type definitions

**Still failing?** Try a clean install:
```bash
cd remotion-project
rm -rf node_modules package-lock.json  # or delete manually on Windows
npm install
```

---

## LLM (Ollama, OpenAI, Azure OpenAI)

### Error: "[connection] Cannot reach ollama API" or "Connection refused"

**Root Cause:** Ollama is not running or listening on the expected host/port.

**Solution (Ollama):**
1. Start Ollama:
   ```bash
   ollama serve
   ```
   This starts Ollama on `http://localhost:11434` (default).

2. In a **separate terminal**, verify it's running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
   You should see a JSON response with available models.

3. If you're running Ollama on a different machine, set the host:
   ```bash
   export OLLAMA_HOST="http://my-remote-machine:11434"
   remotion-gen --prompt "..."
   ```

---

### Error: "Model not found" or "No such file or directory" (Ollama)

**Root Cause:** The model specified hasn't been downloaded yet.

**Solution:**
1. List available models:
   ```bash
   ollama list
   ```

2. Pull the model (default is `llama3`):
   ```bash
   ollama pull llama3
   ```

3. Other popular models:
   ```bash
   ollama pull llama2
   ollama pull mistral
   ollama pull neural-chat
   ```

4. To use a specific model with remotion-gen:
   ```bash
   remotion-gen --prompt "..." --model mistral
   ```

**Note:** First-time pulls can take 5–30 minutes depending on model size and internet speed.

---

### Error: "[auth] Authentication failed for openai" or "Invalid API key"

**Root Cause:** OpenAI API key is missing or invalid.

**Solution:**
1. Get your API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Verify it's set:
   ```bash
   echo $OPENAI_API_KEY        # macOS/Linux
   echo $env:OPENAI_API_KEY    # Windows PowerShell
   ```
4. Try again:
   ```bash
   remotion-gen --prompt "..." --provider openai
   ```

---

### Error: "Azure OpenAI requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT"

**Root Cause:** One or more required Azure OpenAI environment variables are not set.

**Solution:**
1. Set all three variables:
   ```bash
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   export AZURE_OPENAI_KEY="your-key"
   export AZURE_OPENAI_DEPLOYMENT="gpt-4"  # or your deployment name
   ```

2. Verify all three are set:
   ```bash
   echo $AZURE_OPENAI_ENDPOINT
   echo $AZURE_OPENAI_KEY
   echo $AZURE_OPENAI_DEPLOYMENT
   ```

3. Get these values from your Azure portal:
   - **Endpoint:** Your Azure OpenAI resource's endpoint URL
   - **Key:** Found under "Keys and Endpoint" in the Azure portal
   - **Deployment:** The name of your deployed model (e.g., `gpt-4`, `gpt-4-turbo`)

---

### Error: "[rate_limit] Rate limited by openai (retryable)"

**Root Cause:** You've exceeded your OpenAI rate limit.

**Solution:**
1. Wait a few minutes and retry.
2. Check your OpenAI account usage: [platform.openai.com/account/usage](https://platform.openai.com/account/usage)
3. Consider upgrading your plan or switching to Ollama (local, no rate limits).

---

## LLM Generation & Component Validation

### Error: "LLM returned no choices" or "LLM returned empty response"

**Root Cause:** The LLM API responded but with an empty or malformed result.

**Solution:**
1. Verify your API credentials (see [LLM API key issues](#error-auth-authentication-failed-for-openai-or-invalid-api-key) above).
2. For Ollama, check if the model finished loading:
   ```bash
   ollama list
   ```
3. Try a simpler prompt:
   ```bash
   remotion-gen --prompt "A blue circle" --output test.mp4
   ```
4. Enable debug mode to see the generated code:
   ```bash
   remotion-gen --prompt "..." --debug --output test.mp4
   ```
   Check `outputs/GeneratedScene.debug.tsx` to see what the LLM produced.

---

### Error: "Generated TSX has structural syntax errors"

**Root Cause:** The LLM generated code with mismatched brackets, unclosed tags, or other syntax issues.

**Common issues:**
- Unclosed JSX tags: `<div>` without `</div>`
- Mismatched brackets in `interpolate()` or `spring()` calls
- Extra commas or parentheses
- Invalid JSX expressions

**Solution:**
1. Look at the debug output:
   ```bash
   remotion-gen --prompt "..." --debug --output test.mp4
   ```
   Check `outputs/GeneratedScene.debug.tsx` for syntax problems.

2. Simplify your prompt — complex requests are more likely to produce invalid code:
   - Instead of: "A rotating 3D cube with color gradients and spring animation"
   - Try: "A blue square rotating 360 degrees"

3. Use a different provider/model:
   ```bash
   # If using Ollama (llama3), try a different model
   remotion-gen --prompt "..." --model mistral --output test.mp4
   
   # Or switch to OpenAI (more reliable, but requires API key)
   remotion-gen --prompt "..." --provider openai --output test.mp4
   ```

4. The system prompt instructs the LLM to self-correct on retry. You can also manually edit `outputs/GeneratedScene.debug.tsx` and test rendering:
   ```bash
   cd remotion-project
   npx remotion render src/index.ts GeneratedScene ../outputs/manual.mp4
   ```

---

### Error: "Component must import from 'remotion' package"

**Root Cause:** The generated TSX code doesn't have a `from 'remotion'` import.

**Solution:**
1. This usually indicates the LLM generated incomplete or malformed code.
2. Try the same prompt with a different model or provider (see above).
3. Use `--debug` to inspect the generated code.

---

### Error: "Component must have a default export"

**Root Cause:** The generated code is missing `export default`.

**Solution:**
1. The LLM should generate this automatically. Try again or use a different model.
2. For manual editing, the component structure must be:
   ```tsx
   export default function GeneratedScene() {
     // ... component body
   }
   ```

---

### Error: "Component must be named GeneratedScene"

**Root Cause:** The LLM generated a component with a different name.

**Solution:**
1. The system prompt enforces this, but smaller models (llama3 8B) sometimes ignore it.
2. Switch to a more capable model:
   ```bash
   remotion-gen --prompt "..." --model llama2 --output test.mp4
   ```
3. Or use OpenAI/Azure.

---

### Error: "Dangerous import detected: 'fs' is not allowed"

**Root Cause:** The LLM generated code that imports a Node.js module, which is a security risk in browser/Remotion execution.

**Solution:**
1. This is intentionally blocked for security. Only Remotion and React imports are allowed.
2. Try a different provider or model — some LLMs are better at following import restrictions.
3. Simplify your prompt to avoid LLM confusion about what's available.

**Common blocked modules:**
- `fs`, `fs/promises` (file system)
- `child_process`, `http`, `https` (system interaction)
- `path`, `os`, `crypto`, `net` (Node.js built-ins)

---

### Error: "Failed to inject required Remotion import 'interpolate'"

**Root Cause:** The code builder tried to auto-fix missing imports but couldn't modify the import statement.

**Solution:**
1. The generated code structure is unusual. Try a different model.
2. Use `--debug` to inspect the generated code and see what went wrong.
3. For Ollama, try a different model:
   ```bash
   remotion-gen --prompt "..." --model neural-chat --output test.mp4
   ```

---

## Image Validation

### Error: "Image file not found" or "Image path is not a file"

**Root Cause:** The `--image` path doesn't exist or points to a directory.

**Solution:**
1. Verify the file exists:
   ```bash
   ls -la /path/to/image.png    # macOS/Linux
   dir C:\path\to\image.png     # Windows
   ```
2. Use an absolute path or relative path from your current directory:
   ```bash
   remotion-gen --prompt "..." --image ./screenshot.png --output test.mp4
   remotion-gen --prompt "..." --image /home/user/images/logo.png --output test.mp4
   ```

---

### Error: "Symlinks are not allowed for security"

**Root Cause:** The `--image` path is a symbolic link.

**Solution:**
1. Copy the file instead:
   ```bash
   cp /path/to/symlink /path/to/real/file.png
   remotion-gen --prompt "..." --image /path/to/real/file.png --output test.mp4
   ```
2. Or use `--image-policy warn` to proceed anyway (not recommended):
   ```bash
   remotion-gen --prompt "..." --image /symlink/path --image-policy warn --output test.mp4
   ```

---

### Error: "Unsupported image extension '.gif'" or similar

**Root Cause:** The image format is not supported.

**Allowed formats:** `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.svg`

**Solution:**
1. Convert the image to a supported format using an image tool:
   ```bash
   # macOS/Linux example using ImageMagick
   convert image.bmp image.png
   ```
2. Or use `--image-policy warn` to skip validation (may cause issues later):
   ```bash
   remotion-gen --prompt "..." --image image.bmp --image-policy warn --output test.mp4
   ```

---

### Error: "Image too large (200.5 MB). Max: 100 MB"

**Root Cause:** The image file exceeds the 100 MB size limit.

**Solution:**
1. Compress or resize the image using ImageMagick, Pillow, or your image editor:
   ```bash
   # ImageMagick
   convert large.png -resize 50% smaller.png
   
   # Pillow (Python)
   python -c "from PIL import Image; img = Image.open('large.png'); img.resize((1920, 1080)).save('smaller.png')"
   ```
2. Or use `--image-policy warn` to proceed (not recommended):
   ```bash
   remotion-gen --prompt "..." --image huge.png --image-policy warn --output test.mp4
   ```

---

### Error: "staticFile() references 'image_xyz.png' but only 'image_abc.png' is allowed"

**Root Cause:** The LLM-generated code referenced a different image file than the one provided.

**Solution:**
1. This is a security measure to prevent accessing unauthorized files.
2. The LLM should use the provided image. Try:
   ```bash
   remotion-gen --prompt "Include the provided image prominently" \
     --image myimage.png \
     --image-description "A logo showing our company mascot" \
     --output test.mp4
   ```
3. If still failing, use a different model or provider.

---

## Remotion Rendering

### Error: "Remotion render failed: Unable to parse module"

**Root Cause:** The generated TypeScript component has syntax errors that TypeScript compiler caught.

**Solution:**
1. Enable debug mode to see the generated component:
   ```bash
   remotion-gen --prompt "..." --debug --output test.mp4
   ```
2. Check `outputs/GeneratedScene.debug.tsx` for errors.
3. Common issues:
   - Missing semicolons
   - Unclosed braces or parentheses
   - Invalid JSX syntax
4. Try a simpler prompt or different model.

---

### Error: "Render completed but output not found"

**Root Cause:** Remotion render completed with exit code 0, but the MP4 file wasn't created.

**Solution:**
1. Verify the output directory is writable:
   ```bash
   touch /path/to/outputs/test.mp4    # Should succeed
   ```
2. Try writing to a different directory:
   ```bash
   remotion-gen --prompt "..." --output ~/videos/test.mp4
   ```
3. Check disk space:
   ```bash
   df -h      # macOS/Linux
   dir        # Windows
   ```
4. Disable FFmpeg caching:
   ```bash
   export REMOTION_CACHING=false
   remotion-gen --prompt "..." --output test.mp4
   ```

---

### Error: "No such file or directory: node_modules/.bin/ffmpeg" or similar

**Root Cause:** Remotion's dependencies (including FFmpeg wrapper) are not installed.

**Solution:**
```bash
cd remotion-project
npm install
cd ..
remotion-gen --prompt "..." --output test.mp4
```

---

## Windows-Specific Issues

### Error: Backticks or special characters in PowerShell commands

**Root Cause:** PowerShell interprets backticks (`) as escape characters in unquoted strings.

**Example (fails):**
```powershell
remotion-gen --prompt "A circle `rotating` quickly" --output test.mp4
```

**Solution 1: Single quotes** (recommended for Windows)
```powershell
remotion-gen --prompt 'A circle rotating quickly' --output test.mp4
```

**Solution 2: Escape backticks**
```powershell
remotion-gen --prompt "A circle ``rotating`` quickly" --output test.mp4
```

**Solution 3: Use Python script to avoid PowerShell parsing**
Create `generate.py`:
```python
import subprocess
from remotion_gen.cli import generate_video

generate_video(
    prompt="A circle with backticks `like this` and TSX code",
    output="test.mp4"
)
```
Then run:
```powershell
python generate.py
```

---

### Error: Path separators or "Invalid path" on Windows

**Root Cause:** Windows uses backslashes `\` in paths, which can confuse some shells.

**Solution:**
1. Use forward slashes (Windows PowerShell accepts these):
   ```powershell
   remotion-gen --prompt "..." --image ./screenshots/logo.png --output ./videos/test.mp4
   ```
2. Or double-escape backslashes in command-line args:
   ```powershell
   remotion-gen --prompt "..." --image "C:\\Users\\Name\\logo.png" --output "C:\\Users\\Name\\videos\\test.mp4"
   ```

---

## Output Directory Permissions

### Error: "Failed to write component" or "Permission denied" when writing output

**Root Cause:** The output directory doesn't exist or you don't have write permissions.

**Solution:**
1. Verify the output directory exists and is writable:
   ```bash
   mkdir -p outputs
   touch outputs/test.mp4    # Should succeed
   ```
2. Try writing to a different location:
   ```bash
   remotion-gen --prompt "..." --output ~/Desktop/test.mp4
   ```
3. Check file permissions:
   ```bash
   ls -la outputs    # macOS/Linux
   icacls outputs    # Windows
   ```

---

## React Version Mismatches

### Error: "React version mismatch" or "Multiple instances of React"

**Root Cause:** The project has conflicting React versions (18.2.0 is pinned in package.json).

**Solution:**
1. Clean and reinstall dependencies:
   ```bash
   cd remotion-project
   rm -rf node_modules package-lock.json
   npm install
   cd ..
   remotion-gen --prompt "..." --output test.mp4
   ```
2. If still failing, check for duplicate React installations:
   ```bash
   npm ls react
   npm ls react-dom
   ```
3. Verify package.json enforces React 18.2.0 (it should).

---

## Quality Preset Issues

### Error: "Invalid quality preset" or unrecognized quality option

**Root Cause:** You specified an invalid quality value.

**Solution:**
Use one of these three presets:
- `low`: 854×480 @ 15fps (smallest, fastest)
- `medium`: 1280×720 @ 30fps (default, balanced)
- `high`: 1920×1080 @ 60fps (largest, slowest)

Example:
```bash
remotion-gen --prompt "..." --quality high --output test.mp4
```

---

## Duration Out of Range

### Error: "Duration must be between 5 and 30 seconds"

**Root Cause:** You specified a duration outside the allowed 5–30 second range.

**Solution:**
1. Clamp your duration to 5–30 seconds:
   ```bash
   remotion-gen --prompt "..." --duration 10 --output test.mp4    # ✓ Valid
   remotion-gen --prompt "..." --duration 2 --output test.mp4     # ✗ Too short
   remotion-gen --prompt "..." --duration 60 --output test.mp4    # ✗ Too long
   ```
2. The range is intentional — shorter videos render faster and avoid memory issues. Phase 1 will support longer videos.

---

## Unexpected Errors

### Error: "Unexpected error" or generic exception

**Root Cause:** An error not covered by specific handlers was raised.

**Solution:**
1. Enable debug output:
   ```bash
   remotion-gen --prompt "..." --debug --output test.mp4
   ```
2. Check `outputs/GeneratedScene.debug.tsx` to see the generated component.
3. Inspect the full error message in your terminal.
4. Try a different prompt, provider, or model.
5. Open an issue on GitHub with:
   - Your command line
   - The error message (full traceback if possible)
   - The debug TSX file (if generated successfully)

---

## Getting Help

If you're stuck:

1. **Check the [main README](../README.md)** for setup and basic usage.
2. **Review this guide** for your specific error message.
3. **Try a simpler prompt** — complex requests are more likely to fail.
4. **Switch providers or models** — different LLMs produce different results.
5. **Use `--debug`** to inspect intermediate outputs.
6. **Check GitHub issues** in the `image-generation` repo for similar problems.

---

## Summary

| Issue | Quick Fix |
|-------|-----------|
| Node.js/npm not found | Install from [nodejs.org](https://nodejs.org/) |
| Dependencies missing | `cd remotion-project && npm install && cd ..` |
| Ollama not running | `ollama serve` (in a separate terminal) |
| Model not downloaded | `ollama pull llama3` |
| API key missing | `export OPENAI_API_KEY="sk-..."` |
| Invalid TSX generated | Try `--debug`, switch model/provider, or simplify prompt |
| Windows backtick issues | Use single quotes: `'A circle rotating'` |
| Permission denied | Check output directory exists and is writable |
| Invalid duration | Use 5–30 seconds |

