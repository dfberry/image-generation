← [Back to Documentation Index](../README.md)

# Troubleshooting Guide — mermaid-diagrams

This guide covers common issues and solutions when using the mermaid-diagrams package.

## Installation & Setup Issues

### `MmcdNotFoundError`: mmdc binary not found

**Error Message:**
```
MermaidError: 'mmdc' not found. Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli
```

**When it occurs:** During diagram rendering (not at initialization). The `MermaidGenerator` constructor does *not* check for mmdc availability; the error is raised only when `_run_mmdc()` calls `subprocess.run()` and encounters a `FileNotFoundError`.

**Solutions:**

1. **Install mermaid-cli globally:**
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   ```

2. **Verify the installation:**
   ```bash
   which mmdc  # macOS/Linux
   where mmdc  # Windows
   mmdc --version
   ```

3. **If mmdc is installed but not found:**
   - Ensure your npm global bin directory is in your `PATH`.
   - On macOS/Linux:
     ```bash
     npm config get prefix
     # Should be something like /usr/local/bin or /opt/homebrew/bin
     echo $PATH | grep -o '<prefix>/bin'
     ```
   - On Windows, npm installs to `%APPDATA%\npm`. Verify this folder is in your `PATH`:
     ```cmd
     echo %PATH%
     ```

4. **Specify a custom mmdc binary path:**
   ```python
   gen = MermaidGenerator(mmdc_binary="/usr/local/bin/mmdc")
   ```

---

### Node.js not installed (required by mmdc)

**Symptoms:**
- `npm` command not found
- `npm install -g @mermaid-js/mermaid-cli` fails with "npm: command not found"

**Solutions:**

1. **Install Node.js:**
   - Download from [nodejs.org](https://nodejs.org/) (LTS or Current)
   - Includes npm automatically
   - Verify installation:
     ```bash
     node --version
     npm --version
     ```

2. **Use a version manager** (recommended for multiple projects):
   - **nvm** (macOS/Linux): https://github.com/nvm-sh/nvm
   - **nvm-windows**: https://github.com/coreybutler/nvm-windows
   - **fnm**: https://github.com/Schniz/fnm

---

### npm install fails when installing mermaid-cli

**Common failure scenarios:**

#### Missing build tools
```
error: unable to find the specified base path
npm ERR! fatal error
```

**On macOS/Linux:**
```bash
# Install Xcode Command Line Tools
xcode-select --install

# or on Linux
sudo apt-get install build-essential python3-dev
```

**On Windows:**
```cmd
# Install Python and Visual C++ build tools
npm install --global windows-build-tools
```

#### Permission denied
```
npm ERR! code EACCES
npm ERR! errno -13
npm ERR! syscall mkdir
```

**Solutions:**
- Avoid `sudo npm install`. Instead, fix npm permissions:
  ```bash
  mkdir ~/.npm-global
  npm config set prefix '~/.npm-global'
  export PATH=~/.npm-global/bin:$PATH
  npm install -g @mermaid-js/mermaid-cli
  ```

- Or use a Node version manager (nvm/fnm), which handles permissions automatically.

#### Disk space or network issues
```
npm ERR! code ENOSPC
npm ERR! errno -28
npm ERR! syscall open
npm ERR! ENOSPC: no space left on device
```

- Free up disk space
- Check internet connection (npm may need to download from registry)
- Try a different npm registry:
  ```bash
  npm config set registry https://registry.npmjs.org/
  npm install -g @mermaid-js/mermaid-cli
  ```

---

## Mermaid Syntax Errors

### `MermaidSyntaxError`: Invalid Mermaid syntax

**Error Message:**
```
MermaidError: Missing diagram type declaration. First line must start with one of: ...
Got: '<your_first_line>'
```

**When it occurs:** When calling `from_syntax()` or `from_template()` with invalid syntax. The validator checks that:
1. Syntax is not empty or whitespace-only
2. The first non-comment, non-empty line starts with a recognized diagram type

**Common mistakes:**

1. **Missing diagram type declaration:**
   ```python
   # ❌ WRONG
   gen.from_syntax("A --> B")
   
   # ✅ CORRECT
   gen.from_syntax("flowchart TD\n    A --> B")
   ```

2. **Using incorrect diagram type keyword:**
   ```python
   # ❌ WRONG (flowchart vs graph - both are valid, but this one is wrong)
   gen.from_syntax("flow TD\n    A --> B")
   
   # ✅ CORRECT
   gen.from_syntax("flowchart TD\n    A --> B")
   ```

3. **Entire diagram is comments:**
   ```python
   # ❌ WRONG
   gen.from_syntax("%%% This is all comment\n%% flowchart TD")
   
   # ✅ CORRECT
   gen.from_syntax("flowchart TD\n    %% Comment here\n    A --> B")
   ```

**Valid diagram types:**
- `flowchart`, `graph` — flowcharts
- `sequenceDiagram` — sequence diagrams
- `classDiagram` — class diagrams
- `erDiagram` — entity-relationship diagrams
- `stateDiagram` — state machines
- `gantt` — Gantt charts
- `pie` — pie charts
- `gitgraph` — git graphs
- `journey` — user journey diagrams
- `mindmap` — mind maps
- `timeline` — timelines
- `quadrantChart` — quadrant charts
- `sankey` — Sankey diagrams
- `xychart` — XY charts
- `block` — block diagrams
- `packet` — packet diagrams
- `architecture` — architecture diagrams
- `kanban` — kanban boards

**Solution:** Review your diagram syntax against the [Mermaid documentation](https://mermaid.js.org/).

---

### `MermaidSyntaxError`: Empty syntax

**Error Message:**
```
MermaidError: Mermaid syntax cannot be empty
```

**When it occurs:** When passing an empty string or whitespace-only string to `from_syntax()`.

**Solutions:**
```python
# ❌ WRONG
gen.from_syntax("")
gen.from_syntax("   \n\n   ")

# ✅ CORRECT
gen.from_syntax("flowchart TD\n    A --> B")
```

---

## Template Errors

### Template not found

**Error Message:**
```
ValueError: Template '<name>' not found
```

**When it occurs:** When calling `from_template()` with a template name that does not exist in the registry.

**Solutions:**

1. **List available templates:**
   ```bash
   mermaid-diagram --list-templates
   ```

2. **Use correct template names:**
   ```python
   from mermaidgen import default_registry
   
   # See all available templates
   for t in default_registry.list_available():
       print(f"{t['name']}: {t['description']}")
   ```

3. **Built-in templates:**
   - `flowchart_simple` — linear top-down flowchart
   - `sequence_api` — API sequence diagram
   - `class_inheritance` — class inheritance diagram
   - `er_database` — entity-relationship diagram

---

### Template parameter validation failures

**Error Message:**
```
ValueError: 'steps' must be a list with at least 2 items
ValueError: 'participants' must be a non-empty list of strings
ValueError: 'parent' is required
```

**When it occurs:** When required parameters are missing or invalid for a template.

**flowchart_simple template:**
- Requires `steps`: list of at least 2 strings
  ```python
  # ❌ WRONG
  gen.from_template("flowchart_simple", params={})
  gen.from_template("flowchart_simple", params={"steps": ["Only one"]})
  
  # ✅ CORRECT
  gen.from_template("flowchart_simple", params={"steps": ["Start", "Process", "End"]})
  ```

**sequence_api template:**
- Requires `participants`: non-empty list of strings
- Requires `messages`: non-empty list of `(from, to, label)` tuples
  ```python
  # ✅ CORRECT
  gen.from_template("sequence_api", params={
      "participants": ["Client", "Server"],
      "messages": [("Client", "Server", "GET /api")]
  })
  ```

**class_inheritance template:**
- Requires `parent`: string (class name)
- Requires `children`: non-empty list of strings
  ```python
  # ✅ CORRECT
  gen.from_template("class_inheritance", params={
      "parent": "Animal",
      "children": ["Dog", "Cat"]
  })
  ```

**er_database template:**
- Requires `entities`: non-empty list of dicts with `name` and `attributes` keys
  ```python
  # ✅ CORRECT
  gen.from_template("er_database", params={
      "entities": [
          {"name": "User", "attributes": ["id", "name"]},
          {"name": "Post", "attributes": ["id", "title"]}
      ]
  })
  ```

---

## Output Issues

### Output format not supported

**Error Message:**
```
Error: argument --format: invalid choice: '<fmt>' (choose from 'png', 'svg', 'pdf')
```

**When it occurs:** When specifying an unsupported output format via CLI.

**Supported formats:**
- `png` — portable network graphics (default)
- `svg` — scalable vector graphics
- `pdf` — portable document format

**Solutions:**
```bash
# ✅ CORRECT
mermaid-diagram --syntax "flowchart TD\n    A --> B" --format png
mermaid-diagram --syntax "flowchart TD\n    A --> B" --format svg
mermaid-diagram --file diagram.mmd --format pdf
```

---

### Output directory permissions

**Error Message:**
```
PermissionError: [Errno 13] Permission denied: '<path>'
OSError: [Errno 20] Not a directory: '<path>'
```

**When it occurs:** When the output directory cannot be created or written to.

**Solutions:**

1. **Ensure output directory exists:**
   ```python
   import os
   output_dir = "my_outputs"
   os.makedirs(output_dir, exist_ok=True)
   gen = MermaidGenerator(output_dir=output_dir)
   ```

2. **Check directory permissions:**
   ```bash
   # macOS/Linux
   ls -ld <directory>  # Check if you have write permission (w flag)
   chmod u+w <directory>  # Add write permission if needed
   ```

3. **Use an absolute path:**
   ```python
   import os
   from pathlib import Path
   
   output_dir = Path.home() / "mermaid_output"
   output_dir.mkdir(exist_ok=True)
   gen = MermaidGenerator(output_dir=str(output_dir))
   ```

---

## Subprocess & Rendering Issues

### Subprocess timeout

**Error Message:**
```
RenderError: mmdc timed out after 30s
```

**When it occurs:** When `mmdc` takes longer than 30 seconds to render a diagram. This can happen with very complex diagrams or slow systems.

**Default timeout:** 30 seconds (set in `config.py` as `SUBPROCESS_TIMEOUT`)

**Solutions:**

1. **Simplify your diagram:**
   - Reduce the number of nodes/edges
   - Break large diagrams into multiple smaller diagrams

2. **Increase timeout** (if modifying code):
   ```python
   from mermaidgen.generator import MermaidGenerator
   from mermaidgen import config
   
   # Temporarily increase timeout
   old_timeout = config.SUBPROCESS_TIMEOUT
   config.SUBPROCESS_TIMEOUT = 60  # 60 seconds
   gen = MermaidGenerator()
   result = gen.from_syntax(my_diagram)
   config.SUBPROCESS_TIMEOUT = old_timeout
   ```

3. **Check system resources:**
   - Free up RAM/CPU
   - Close other applications
   - Run on a faster machine

---

### Chromium/Puppeteer issues (mmdc uses headless browser)

**Error Message:**
```
RenderError: mmdc failed (exit 1): Error: Failed to launch chrome!
RenderError: mmdc failed (exit 1): Timeout waiting for browser instance to start
```

**When it occurs:** `mmdc` uses a headless Chromium browser to render diagrams. Browser launch failures can occur due to:
- Missing system dependencies
- Insufficient sandbox permissions
- GPU rendering conflicts

**Solutions:**

1. **On Linux, install required dependencies:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y \
       libgtk-3-0 \
       libgbm-dev \
       libxss-dev \
       libasound2 \
       libnspr4 \
       libnss3

   # Alpine
   apk add --no-cache \
       chromium \
       nss \
       freetype \
       harfbuzz \
       ca-certificates \
       ttf-freefont
   ```

2. **Disable GPU rendering** (if running headless or in a container):
   - This is handled by mmdc automatically, but if you have issues:
   ```bash
   # Set environment variable
   export PUPPETEER_ARGS="--no-sandbox --disable-gpu"
   mermaid-diagram --syntax "flowchart TD\n    A --> B"
   ```

3. **Check Puppeteer cache:**
   ```bash
   # mmdc ships with Puppeteer, which downloads Chromium
   # Clear cache and reinstall if corrupted
   npm cache clean --force
   npm install -g @mermaid-js/mermaid-cli
   ```

4. **Run with `--no-sandbox` flag** (less secure, use carefully):
   ```bash
   PUPPETEER_ARGS="--no-sandbox" mermaid-diagram --file diagram.mmd
   ```

---

### Large diagram rendering failures

**Error Message:**
```
RenderError: mmdc failed (exit 1): <Chrome/Puppeteer error>
MemoryError or similar resource exhaustion
```

**When it occurs:** When rendering very large or complex diagrams that exceed browser memory limits.

**Solutions:**

1. **Break diagrams into smaller parts:**
   ```python
   # Instead of one massive diagram
   # Create multiple focused diagrams
   gen.from_syntax(part1_syntax, output_filename="diagram_part1.png")
   gen.from_syntax(part2_syntax, output_filename="diagram_part2.png")
   gen.from_syntax(part3_syntax, output_filename="diagram_part3.png")
   ```

2. **Simplify diagram structure:**
   - Reduce node count (>500 nodes often causes issues)
   - Reduce edge count
   - Use fewer nested levels

3. **Increase system resources:**
   - Run on a machine with more RAM/CPU
   - Close other applications
   - Increase swap space (if applicable)

4. **Use a different format:**
   - SVG output is sometimes lighter than PNG
   - Try `--format svg` instead of `--format png`

---

## Python Version Compatibility

### Python version too old

**Error Message:**
```
error: Python 3.10+ required
ModuleNotFoundError: No module named 'mermaidgen'
```

**When it occurs:** When using Python < 3.10. The package requires Python 3.10+ for syntax features (e.g., union types with `|`, match statements).

**Check your Python version:**
```bash
python --version
python3 --version
```

**Solutions:**

1. **Upgrade Python:**
   - Download from [python.org](https://www.python.org/downloads/)
   - Or use a version manager (pyenv, conda, etc.)

2. **Use a virtual environment with the correct Python:**
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate  # Windows
   pip install -e .
   ```

3. **Verify installation:**
   ```bash
   python -c "import mermaidgen; print(mermaidgen.__version__)"
   ```

---

## CLI Argument Errors

### Multiple input sources specified

**Error Message:**
```
Error: argument group: not allowed with argument...
```

**When it occurs:** When specifying more than one input source (--syntax, --file, --template, --list-templates together).

**Solutions:**
```bash
# ❌ WRONG — multiple input sources
mermaid-diagram --syntax "flowchart TD\n    A --> B" --file diagram.mmd

# ✅ CORRECT — choose one
mermaid-diagram --syntax "flowchart TD\n    A --> B"
mermaid-diagram --file diagram.mmd
mermaid-diagram --template flowchart_simple --param steps="Start,End"
```

### No input source specified

**Error Message:**
```
usage: mermaid-diagram [-h] [--syntax SYNTAX] ...
```

**When it occurs:** When running `mermaid-diagram` with no arguments or no input source.

**Solutions:**
```bash
# Provide an input source
mermaid-diagram --syntax "flowchart TD\n    A --> B"
mermaid-diagram --file diagram.mmd
mermaid-diagram --template flowchart_simple --param steps="Start,Process,End"

# Or list templates
mermaid-diagram --list-templates
```

### Template parameter parsing error

**Error Message:**
```
Error: --param must be KEY=VALUE, got: '<param>'
```

**When it occurs:** When --param arguments are not in KEY=VALUE format.

**Solutions:**
```bash
# ❌ WRONG
mermaid-diagram --template flowchart_simple --param "steps: Start, End"

# ✅ CORRECT
mermaid-diagram --template flowchart_simple --param steps="Start,End"

# For multiple values (comma-separated)
mermaid-diagram --template sequence_api \
  --param participants="Client,Server,Database" \
  --param messages="Client,Server,Request|Server,Database,Query|Database,Server,Result"
```

---

## Getting Help

1. **Check error messages carefully** — they often include specific guidance
2. **Verify mmdc is installed and in PATH:**
   ```bash
   mmdc --version
   ```
3. **Enable debug output** (if adding custom code):
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```
4. **Test with a simple diagram first:**
   ```bash
   mermaid-diagram --syntax "flowchart TD\n    A[Start]\n    B[End]\n    A --> B"
   ```
5. **Review the source code:**
   - Error classes: `mermaidgen/errors.py`
   - Generator: `mermaidgen/generator.py`
   - Validators: `mermaidgen/validators.py`
