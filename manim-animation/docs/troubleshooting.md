# Troubleshooting Guide for Manim Animation Generator

This guide covers common errors, their causes, and solutions. Exit codes are documented in the CLI.

## Exit Codes

- **0** — Success
- **1** — LLM error (API failure, missing credentials, connection issues)
- **2** — Validation error (generated code failed safety/syntax checks)
- **3** — Render error (Manim/FFmpeg failure)
- **4** — Unexpected/internal error
- **5** — Image validation error (bad path, format, size, permissions)

---

## FFmpeg Not Found

### Error Message
```
FFmpeg not found. Install FFmpeg: https://docs.manim.community/en/stable/installation.html
```

Or from Manim's output:
```
No such file or directory: ffmpeg
```

### Why It Happens
Manim Community Edition requires FFmpeg for video encoding (MP4 output). The `manim` CLI checks your system PATH for the `ffmpeg` command. If it's not installed or not in your PATH, render fails.

### Solution

**macOS** (using Homebrew):
```bash
brew install ffmpeg
# Verify: ffmpeg -version
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
# Verify: ffmpeg -version
```

**Windows**:
1. Download from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add the bin folder to your system PATH:
   - Right-click "This PC" → Properties → Advanced System Settings
   - Environment Variables → Edit PATH → Add `C:\ffmpeg\bin`
4. Restart terminal and verify: `ffmpeg -version`

---

## LaTeX Not Found

### Error Message
```
LaTeX not found. Install LaTeX to use MathTex
```

Or from Manim:
```
pdflatex not found in PATH
```

### Why It Happens
LaTeX is only required for `MathTex` objects — complex mathematical equations. If your prompt uses simple text or basic math (e.g., `Circle()`, `Text("hello")`), LaTeX is not needed.

- **MathTex required**: "Write the Pythagorean theorem: a² + b² = c²" (generates MathTex)
- **LaTeX not required**: "A blue circle rotates" (uses only basic Manim objects and Text)

### Solution

**Do NOT render prompts with complex equations** — LaTeX support is optional:
- Rephrase to avoid equations: "Show a right triangle with sides labeled a, b, c" (using Text)
- Or install LaTeX:

**macOS**:
```bash
brew install --cask mactex  # ~3GB, includes full LaTeX suite
```

**Ubuntu**:
```bash
sudo apt install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```

**Windows**:
Download and install from https://www.latex-project.org/get/

After installing LaTeX, restart your terminal and try again.

---

## Ollama Not Running or Model Not Pulled

### Error Message
```
LLM Error: [connection] Cannot reach ollama API (retryable)
```

Or:
```
LLM Error: [connection] Failed to connect to http://localhost:11434
```

### Why It Happens
When using `--provider ollama` (default), the tool expects a local Ollama service running on `http://localhost:11434`. If Ollama isn't running or the model isn't pulled, the LLM call fails.

### Solution

1. **Start Ollama**:
   ```bash
   # macOS/Linux
   ollama serve
   
   # Windows (if Ollama is installed)
   # Usually runs as a background service; restart it if needed
   ```

2. **Pull a model** (in another terminal while Ollama runs):
   ```bash
   # Default model (recommended)
   ollama pull llama3
   
   # Other options (faster but lower quality)
   ollama pull llama2
   ollama pull mistral
   ```

3. **Verify Ollama is responsive**:
   ```bash
   curl -X POST http://localhost:11434/api/generate -d '{"model":"llama3","prompt":"hello"}'
   ```

4. **Use a custom Ollama host** (if running on a different machine):
   ```bash
   export OLLAMA_HOST="http://my-server:11434"
   manim-gen --prompt "Your prompt"
   ```

---

## OpenAI/Azure API Key Missing or Invalid

### Error Message
```
LLM Error: [auth] Authentication failed: Unauthorized
```

Or:
```
LLM Error: OpenAI requires OPENAI_API_KEY environment variable
```

Or for Azure:
```
LLM Error: Azure OpenAI requires AZURE_OPENAI_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT
```

### Why It Happens
- **OpenAI**: API key not set or invalid/expired
- **Azure**: Missing one or more required environment variables

### Solution

**OpenAI**:
1. Get your API key from https://platform.openai.com/api-keys
2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."  # Replace with your actual key
   manim-gen --prompt "Your prompt" --provider openai
   ```
3. Verify the key is set:
   ```bash
   echo $OPENAI_API_KEY  # Should print your key
   ```

**Azure OpenAI**:
1. Get credentials from your Azure OpenAI resource:
   - API key: From "Keys and endpoints" in Azure Portal
   - Endpoint: Your resource's base URL
   - Deployment name: From "Model deployments" → your deployment
2. Set environment variables:
   ```bash
   export AZURE_OPENAI_KEY="your-key"
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
   export AZURE_OPENAI_DEPLOYMENT="gpt-4"
   manim-gen --prompt "Your prompt" --provider azure
   ```
3. Verify all three are set:
   ```bash
   echo $AZURE_OPENAI_KEY $AZURE_OPENAI_ENDPOINT $AZURE_OPENAI_DEPLOYMENT
   ```

**Troubleshooting**:
- Verify the key is correct (no extra spaces or quotes)
- Check API key is active (not revoked or expired)
- For OpenAI, ensure account has credits
- For Azure, confirm deployment exists and is running

---

## LLM Rate Limited

### Error Message
```
LLM Error: [rate_limit] Rate limited by openai (retryable)
```

### Why It Happens
You've exceeded the API provider's rate limits for your account/tier.

### Solution
- **OpenAI**: Upgrade your account tier or wait for the rate limit window to reset (usually 1 minute)
- **Azure**: Check your deployment's quotas in Azure Portal; increase if needed
- **Ollama**: Rate limiting is rare with local inference; if it happens, your machine may be overloaded

For repeated rate limiting, consider:
- Using lower quality (less compute-intensive)
- Spacing out requests
- Upgrading your API tier

---

## Generated Code Has Syntax Error

### Error Message
```
Validation Error: Generated code has syntax error: invalid syntax on line X
```

### Why It Happens
The LLM generated Python code with syntax errors — malformed class definitions, indentation issues, unclosed strings, etc. This is more likely with:
- Very complex prompts
- Ambiguous English descriptions
- LLM models with lower capability

### Solution

1. **Use `--debug` to inspect the code**:
   ```bash
   manim-gen --prompt "Your prompt" --debug
   ```
   This saves the generated code to `outputs/video_YYYYMMDD_HHMMSS_scene.py` for inspection.

2. **Rephrase the prompt to be more specific**:
   - ✗ Bad: "Visualize something cool"
   - ✓ Good: "Create a blue circle that rotates 360 degrees, then transforms into a red square"

3. **Break complex ideas into simpler parts**:
   - ✗ Bad: "Animate a 3D rotating cube with perspective and shadows while text fades in and out"
   - ✓ Good: "A white cube rotates slowly. Text below says 'Cube Rotation'"

4. **Try a different LLM model** (if not using OpenAI):
   ```bash
   manim-gen --prompt "Your prompt" --model mistral
   ```

5. **Share the error with the team** if the prompt is reasonable but the LLM consistently fails.

---

## Forbidden Import or Function Call Detected

### Error Message
```
Validation Error: Forbidden import: os. Only {'manim', 'math', 'numpy'} are allowed.
```

Or:
```
Validation Error: Forbidden function call: exec
```

### Why It Happens
For security, generated code is restricted to safe imports and function calls:
- **Allowed imports**: `manim`, `math`, `numpy`
- **Blocked imports**: `os`, `sys`, `requests`, `pickle`, file I/O libraries, etc.
- **Blocked calls**: `open()`, `exec()`, `eval()`, `__import__()`, `getattr()`, `setattr()`, etc.

This prevents the LLM from generating code that reads/writes files, imports malware, or executes arbitrary code.

### Solution

The LLM generated unsafe code. Try rephrasing:
- ✗ Bad: "Read an image from disk and show it"
- ✓ Good: Use the `--image` argument instead

**To include images in your animation**:
```bash
manim-gen \
  --prompt "Show this photo with animations" \
  --image /path/to/photo.png \
  --image-descriptions "A landscape photo"
```

The tool automatically handles image copying and passes filenames to the LLM safely.

**If you need to access files**:
- This tool does not support file I/O in generated animations
- Pre-process your data outside the generator and pass results to the prompt

---

## AST Validation Failure (Invalid Scene Class or Structure)

### Error Message
```
Validation Error: Generated code must contain a class named 'GeneratedScene'
```

Or:
```
Validation Error: GeneratedScene class must inherit from Scene
```

### Why It Happens
The generated code doesn't meet Manim's requirements:
- Missing `GeneratedScene` class
- Class doesn't inherit from `Scene`
- Missing `construct()` method

The LLM should generate code matching this structure:
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Animations go here
        self.play(...)
```

### Solution

1. **Use `--debug` to inspect the generated code**
2. **Rephrase more explicitly**:
   - ✗ Bad: "Animate a circle"
   - ✓ Good: "Create a blue circle and make it spin. Use Manim Scene class with construct() method"

3. **Try a different model** (if using Ollama):
   ```bash
   ollama pull llama3  # Or try mistral, neural-chat
   ```

---

## Manim Render Subprocess Failed

### Error Message
```
Render Error: Manim render failed: [stderr from manim]
```

Common Manim errors:
- `ModuleNotFoundError: No module named 'manim'`
- `Command 'manim' not found`
- `LaTeX not found`
- Various animation runtime errors

### Why It Happens
The Manim CLI can't find the `manim` command, or Manim encounters an error while rendering the scene.

### Solution

**Reinstall Manim**:
```bash
pip install -U manim
# Verify: manim --version
```

**Check for corrupted environment**:
```bash
# In the manim-animation directory
pip install -r requirements.txt
```

**If specific Manim error appears in logs**:
- Review Manim's error message carefully
- Check your generated code (`--debug`) for invalid object references
- Try simplifying your prompt

---

## Scene Class Not Found in Generated Code

### Error Message (at render time)
```
Render Error: Manim render failed: cannot find class GeneratedScene
```

### Why It Happens
The generated code compiled successfully but doesn't contain a `GeneratedScene` class. This can happen if:
- The LLM put the class definition outside the file
- The class is defined in a comment or string
- The code extraction regex failed

### Solution

1. **Use `--debug` and inspect the generated `.py` file**:
   - Look for the `class GeneratedScene(Scene):` line
   - If missing, the code extraction failed

2. **Enable more verbose logging**:
   ```bash
   manim-gen --debug --prompt "Your prompt" 2>&1 | grep -i "extracting\|validating"
   ```

3. **Report the issue** if the prompt is reasonable but the extraction consistently fails.

---

## Quality Preset Issues

### Error Message
```
Validation Error: Quality must be 'low', 'medium', or 'high'
```

### Why It Happens
Invalid `--quality` argument.

### Solution
Use valid values only:
```bash
manim-gen --prompt "..." --quality low     # 480p, 15fps
manim-gen --prompt "..." --quality medium  # 720p, 30fps (default)
manim-gen --prompt "..." --quality high    # 1080p, 60fps
```

---

## Duration Out of Range

### Error Message
```
ValueError: Duration must be between 5 and 30 seconds
```

### Why It Happens
`--duration` argument is outside the valid range [5, 30].

### Solution
Use a duration between 5 and 30 seconds:
```bash
manim-gen --prompt "..." --duration 5   # Shortest
manim-gen --prompt "..." --duration 10  # Default (recommended)
manim-gen --prompt "..." --duration 30  # Longest
```

Why the limit?
- **5 seconds minimum**: Animations need time to render and play meaningfully
- **30 seconds maximum**: Prevents excessive compute time and simplifies LLM prompt design

---

## Output Directory Permissions

### Error Message
```
PermissionError: [Errno 13] Permission denied: '/path/to/outputs/'
```

Or:
```
OSError: [Errno 28] No space left on device
```

### Why It Happens
- Output directory doesn't have write permissions
- Disk is full
- Parent directory is missing

### Solution

**Check permissions**:
```bash
ls -ld outputs/  # Check if directory is writable
chmod 755 outputs/  # Fix permissions if needed
```

**Use a different output directory** (if no permissions to default):
```bash
mkdir -p /tmp/my_videos  # Create writable location
manim-gen --prompt "..." --output /tmp/my_videos/video.mp4
```

**Check disk space**:
```bash
df -h  # Show disk usage
# Videos are typically 5-50 MB depending on quality/duration
```

---

## Python Version Compatibility

### Error Message
```
python: No module named manim_gen
```

Or:
```
SyntaxError: invalid syntax
```

### Why It Happens
Tool requires Python 3.10+. Older versions don't support certain syntax (e.g., `|` union types, match statements).

### Solution

**Check your Python version**:
```bash
python --version  # Must be 3.10.0 or higher
```

**If you have multiple Python versions** (macOS/Linux):
```bash
python3.10 --version
python3.11 --version

# Use the right one for the venv or to install
python3.10 -m pip install -e .
python3.10 -m manim_gen.cli --prompt "..."
```

**Upgrade Python**:
- Visit https://www.python.org/downloads/
- Or use a package manager (brew, apt, etc.)
- Or use pyenv to manage multiple versions

---

## pip Install Conflicts with Manim Dependencies

### Error Message
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

Or:
```
Conflicting requirements: numpy 1.20.0 required, but numpy 2.0.0 already installed
```

### Why It Happens
Manim has complex dependencies (numpy, scipy, Pillow, pydub, pygments, etc.). Conflicts arise when:
- Another package requires an incompatible version
- Your environment is partially broken
- You're upgrading conflicting packages

### Solution

**Start fresh** (recommended):
```bash
# Remove old environment
rm -rf venv/

# Create new environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Verify
manim --version
```

**If that doesn't work**, install Manim directly and update:
```bash
pip install --upgrade manim
```

**As a last resort**, file a dependency issue on GitHub with:
- Python version
- Your pip and pip dependencies (`pip list`)
- Full error message

---

## LLM Generating Invalid/Unsafe Scene Code

### Error Message
```
Validation Error: Forbidden attribute call: getattr
```

Or various syntax/structure errors (see AST Validation above).

### Why It Happens
The LLM occasionally generates:
- Code that tries to bypass safety restrictions
- Syntactically invalid Python
- Code missing the required `GeneratedScene` class

Limitations of current LLM integration:
- No automatic retry on failures
- Happy path focus (not production-hardened)
- Output quality varies by model and prompt complexity

### Solution

1. **Rephrase your prompt** to be more explicit and less ambiguous
2. **Try a different LLM model** (if using Ollama):
   ```bash
   ollama pull llama3
   ollama pull mistral
   manim-gen --prompt "..." --model mistral
   ```
3. **Use a more capable model** (if cost allows):
   ```bash
   manim-gen --prompt "..." --provider openai
   ```
4. **Break complex prompts into simpler steps**
5. **Use `--debug` to inspect failed code** and report patterns to the team

---

## Manim Render Takes Very Long

### Error Message
No error — just waiting a long time.

### Why It Happens
Rendering times depend on:
- **Quality preset**: HIGH (1080p@60fps) is slowest
- **Animation complexity**: Many objects, transforms, and effects slow rendering
- **Duration**: Longer animations take longer to render
- **System performance**: Slower CPUs/GPUs render slower

Typical render times:
- Low quality, simple animation: 10-30 seconds
- Medium quality, moderate animation: 30-120 seconds
- High quality, complex animation: 2-10 minutes

### Solution

To speed up rendering:
1. **Use lower quality** (if acceptable):
   ```bash
   manim-gen --prompt "..." --quality low
   ```
2. **Reduce duration** (if animation can be shorter):
   ```bash
   manim-gen --prompt "..." --duration 8
   ```
3. **Simplify the prompt** (fewer objects and transformations)
4. **Use a more powerful machine** (GPU acceleration helps, but not always enabled by default)

---

## Output File Wasn't Created

### Error Message
```
Render Error: Manim media directory not created
```

Or:
```
Render Error: Manim completed but output video not found
```

### Why It Happens
Manim ran without errors but didn't produce the expected output file:
- Manim cached output from a previous run (now fixed with `--disable_caching`)
- Unusual file system state
- Permission issues in temp directory

### Solution

1. **Clear Manim cache**:
   ```bash
   rm -rf manim_gen/media/  # Remove cached renders
   rm -rf media/            # Remove local cache
   ```

2. **Try again**:
   ```bash
   manim-gen --prompt "Your prompt"
   ```

3. **Use `--debug` to inspect logs**:
   ```bash
   manim-gen --prompt "..." --debug 2>&1 | tail -20
   ```

---

## Image Validation Errors

### Error Message (Exit Code 5)
```
Image Error: Image not found: /path/to/image.png
```

Or:
```
Image Error: Unsupported image format '.svg'. Allowed: {'.png', '.jpg', ...}
```

Or:
```
Image Error: Image too large (150.5 MB). Max: 100 MB
```

### Supported Image Formats
- `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`
- **Not supported**: `.svg` (use SVGMobject in Manim instead, not ImageMobject)

### Why It Happens
- File doesn't exist or path is wrong
- File is a symlink (rejected for security)
- File format is unsupported or corrupted
- File is larger than 100 MB
- Insufficient permissions to read the file

### Solution

**Check the file**:
```bash
ls -lh /path/to/image.png  # Verify file exists and size
file /path/to/image.png     # Check format
```

**Use valid paths and formats**:
```bash
# ✓ Correct
manim-gen --prompt "..." --image ~/Desktop/photo.png

# ✗ Wrong
manim-gen --prompt "..." --image ~/Desktop/photo.svg  # SVG not supported
manim-gen --prompt "..." --image ~/Desktop/photo.HEIC  # HEIC not supported
```

**For large images**, resize first:
```bash
# Using ImageMagick or similar
convert large.png -resize 2000x2000 resized.png
manim-gen --prompt "..." --image resized.png
```

**For image validation policy**:
```bash
# Default (strict): fails on any invalid image
manim-gen --prompt "..." --image bad.png --image-policy strict

# Warn: logs warnings but continues
manim-gen --prompt "..." --image bad.png --image-policy warn

# Ignore: skips invalid images silently
manim-gen --prompt "..." --image bad.png --image-policy ignore
```

---

## General Tips for Troubleshooting

1. **Always use `--debug`** when debugging — it saves the generated Python code for inspection
2. **Check logs** carefully — error messages often contain the root cause
3. **Try simpler prompts first** — if basic animations work, your complex prompt has issues
4. **Test each component separately**:
   - Does Ollama work? `curl http://localhost:11434`
   - Does Manim work? `manim --version && ffmpeg -version`
   - Does the generator work? `manim-gen --prompt "A blue circle"`
5. **Report reproducible issues** to the team with:
   - Your prompt
   - Full error output (from `--debug`)
   - Your environment (Python version, OS, GPU/CPU)
   - The generated code (if available)
