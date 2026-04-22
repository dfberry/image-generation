← [Back to Documentation Index](../README.md)

# Limitations and Roadmap — mermaid-diagrams

This document describes what mermaid-diagrams does **not** do and outlines future opportunities for enhancement.

## Current Limitations

### No LLM/AI integration

Unlike sister tools in this project (`manim-animation` and `remotion-animation`), **mermaid-diagrams does not use AI** to generate diagram syntax from natural language descriptions.

- **What you get:** Render Mermaid diagrams from structured syntax (DSL) or templated code
- **What you don't get:** "Generate a flowchart from a natural language description like 'User logs in, system validates credentials, either shows dashboard or error page'"

**Rationale:** Mermaid already has a mature DSL. Adding LLM generation would require:
- Fine-tuning or prompt engineering for diagram quality
- Validation layer (output must be syntactically valid)
- Fallback handling when LLM produces invalid syntax
- Significant additional complexity

**Workaround:** Use ChatGPT or Claude to write the Mermaid syntax, then use this tool to render it.

---

### No interactive diagrams

Output is **always static**: PNG, SVG, or PDF files.

- **What you get:** High-quality rendered images suitable for documentation, reports, presentations
- **What you don't get:** Interactive features like clickable nodes, collapsible sections, hover tooltips, zoom/pan

**Rationale:** Static rendering is the primary use case. Interactive diagrams would require:
- Exporting to HTML/JavaScript (not just raster images)
- Embedding Mermaid.js runtime
- Browser runtime dependency
- Significant scope expansion

**Workaround:** For interactive diagrams, embed Mermaid.js directly in your web app and pass the DSL to the browser renderer.

---

### No real-time editing/preview

This tool operates in **batch mode only**.

- **What you get:** CLI or Python API to generate diagrams from files/code
- **What you don't get:** Live editor where you type and see the diagram update in real time

**Rationale:** Building a UI/editor is outside the project scope. The focus is on programmatic generation.

**Workaround:** Use [Mermaid Live Editor](https://mermaid.live/) for interactive editing, then export the `.mmd` file and use this tool for batch rendering.

---

### No web UI

This is a **command-line and Python API tool only**.

- **What you get:** `mermaid-diagram` CLI and `MermaidGenerator` Python class
- **What you don't get:** Web dashboard, REST API, or GUI application

**Rationale:** Keeping the tool lightweight and self-contained. Web UI would require:
- Web framework (Flask, FastAPI, etc.)
- Frontend (React, Vue, etc.)
- Deployment infrastructure
- Authentication/authorization (if multi-user)

**Workaround:** Wrap this tool in a Flask/FastAPI app if you need HTTP endpoints or a web UI.

---

### Only 4 built-in templates

The package ships with 4 concrete templates:

1. **flowchart_simple** — Linear top-down flowchart from a list of steps
2. **sequence_api** — Sequence diagram for API interactions (client → server → database)
3. **class_inheritance** — Class diagram showing parent-child relationships
4. **er_database** — Entity-relationship diagram with entities and attributes

These templates cover common patterns but are **not exhaustive**.

- **What you get:** Quick generation of these 4 diagram types without writing Mermaid syntax
- **What you don't get:** Templates for pie charts, Gantt charts, state machines, etc.

**Rationale:** Extensibility. You can create custom templates by:
1. Subclassing `MermaidTemplate`
2. Implementing `render(**kwargs) -> str`
3. Registering with `default_registry.register(my_template)`

**Example:** Create a custom template for swimlane flowcharts
```python
from mermaidgen.templates import MermaidTemplate, default_registry

class SwimlaneTemplate(MermaidTemplate):
    name = "swimlane"
    description = "Swimlane flowchart with roles/actors"
    
    def render(self, **kwargs):
        # Your swimlane rendering logic
        return "flowchart TD\n    ..."

default_registry.register(SwimlaneTemplate())
```

---

### No custom theming

Output uses **mmdc (mermaid-cli) default theme**.

- **What you get:** Clean, professional diagrams with standard Mermaid styling
- **What you don't get:** Custom colors, fonts, spacing, or theme configuration

**Rationale:** Theme support would require:
- Theme file format (JSON, YAML, CSS, etc.)
- Configuration parsing
- Passing theme to mmdc (which may or may not support it depending on version)

**Workaround:** 
1. Generate SVG output (`--format svg`)
2. Post-process the SVG with custom CSS or sed/regex
3. Or modify the generated SVG directly in Inkscape or a text editor

---

### No diagram-to-code reverse engineering

This tool is **unidirectional**: syntax → diagram only.

- **What you get:** Render diagrams from Mermaid code
- **What you don't get:** Convert a PNG/SVG image back to editable Mermaid syntax

**Rationale:** Reverse engineering would require OCR, shape detection, and relationship inference — a separate project with low ROI.

**Workaround:** Keep your `.mmd` source files under version control and use them as the source of truth.

---

### No version comparison / diff visualization

Cannot compare two diagrams and highlight differences.

- **What you get:** Render individual diagrams
- **What you don't get:** Side-by-side comparison, diff highlighting, change detection

**Rationale:** Diagram diffing is a specialized problem. This tool focuses on rendering.

**Workaround:** 
1. Render both diagram versions as PNG/SVG
2. Use a visual diff tool (e.g., ImageMagick `compare`, Photoshop)
3. Or write a custom diff layer if you need programmatic comparison

---

### No automatic layout optimization

Diagrams are rendered as-is; no algorithmic tweaking of node positions.

- **What you get:** Mermaid's built-in layout engine (Daigre-D3, ELK, etc.)
- **What you don't get:** Custom force-directed layout, hierarchical layout tuning, or overlap elimination

**Rationale:** Mermaid handles layout; this tool just calls it. Overriding layout would require:
- Understanding Mermaid's layout engine
- Modifying SVG node positions post-render
- Testing across diagram types

**Workaround:** If layout is unsatisfactory, consider:
1. Reordering nodes in your Mermaid syntax
2. Using Mermaid's built-in layout directives (if available for your diagram type)
3. Post-processing SVG with custom layout logic

---

### No animation/video output

Output is **always static images**.

- **What you get:** PNG, SVG, PDF — suitable for static documents and presentations
- **What you don't get:** Animated GIF, MP4, WebM, or other video formats

**Rationale:** Animation requires:
- Frame sequence generation
- Timing/easing logic
- Video encoding (ffmpeg integration)
- Significant added complexity

For animated diagrams, see the **`manim-animation`** tool in this project, which is purpose-built for procedural animation.

---

### No sound/audio

Diagrams do not produce audio output.

**Rationale:** Not applicable to diagrams. (Noted for consistency with other tools in the project.)

---

### No accessibility features

Output diagrams do not include automatic alt text, captions, or semantic markup.

- **What you get:** PNG, SVG, PDF files
- **What you don't get:** ARIA labels, alt text, accessibility metadata

**Rationale:** Adding accessibility would require:
- Semantic enrichment (tagging nodes/edges with meaning)
- Alt text generation (AI or manual template)
- Output format support (SVG can include alt text, but PNG cannot)

**Workaround:**
1. For SVG output: Add `<title>` and `<desc>` tags manually or with post-processing
2. For static documents: Write alt text in your document separately
3. Consider generating SVG and enhancing with accessibility attributes programmatically

---

### No batch processing from directory

Cannot automatically generate diagrams for all `.mmd` files in a directory.

- **What you get:** Process one file or one syntax string at a time
- **What you don't get:** `--input-dir <dir>` to batch-render all `.mmd` files

**Rationale:** Use shell scripting or Python loops instead for batch operations.

**Workaround:** Shell script to batch process:
```bash
#!/bin/bash
for file in diagrams/*.mmd; do
  output="outputs/$(basename "$file" .mmd).png"
  mermaid-diagram --file "$file" --output "$output"
done
```

Or Python loop:
```python
from pathlib import Path
from mermaidgen import MermaidGenerator

gen = MermaidGenerator(output_dir="outputs")
for mmd_file in Path("diagrams").glob("*.mmd"):
    syntax = mmd_file.read_text()
    output = f"outputs/{mmd_file.stem}.png"
    gen.from_syntax(syntax, output_filename=output)
```

---

## Future Opportunities

### 1. LLM integration (major feature)

**Opportunity:** Add optional AI-powered diagram generation from natural language.

**Example API:**
```python
gen = MermaidGenerator(use_ai=True, ai_model="gpt-4")
diagram = gen.from_prompt("A user logs in, validates credentials, and sees a dashboard")
```

**Scope:**
- Integrate with OpenAI, Anthropic, or Ollama
- Use few-shot prompts to guide syntax generation
- Validate output before rendering
- Fallback if LLM output is invalid

**Benefits:**
- Unify with `manim-animation` and `remotion-animation` AI capabilities
- Lower barrier to entry for non-technical users
- Attractive to documentation generators

**Challenges:**
- LLM cost and latency
- Quality control (syntax validation)
- Handling ambiguous prompts
- Keeping diagrams deterministic (optional seed?)

---

### 2. Custom template library

**Opportunity:** Expand built-in templates or provide a standard way to register domain-specific templates.

**Example templates:**
- Swimlane flowcharts (multiple actors)
- UML sequence diagrams (with alt/loop blocks)
- Architecture diagrams (cloud components)
- Data pipeline diagrams
- State machine (with guards/actions)
- Decision trees

**Implementation:**
```python
# Load templates from a registry or file
templates = TemplateRegistry.load_from_file("templates.yaml")
gen = MermaidGenerator(template_registry=templates)
```

**Benefits:**
- Reusable domain patterns
- Reduced boilerplate for users
- Community contributions

---

### 3. Theming and customization

**Opportunity:** Support custom themes and styling.

**Example:**
```python
gen = MermaidGenerator(theme="dark", theme_config={"primaryColor": "#ff0000"})
```

Or via CLI:
```bash
mermaid-diagram --syntax "..." --theme dark --theme-config primaryColor=#ff0000
```

**Implementation:**
- Detect mmdc theme support
- Pass theme JSON to mmdc
- Or post-process SVG with custom CSS

**Benefits:**
- Brand consistency (corporate colors)
- Dark mode support
- Better presentation customization

---

### 4. Diagram diffing and versioning

**Opportunity:** Compare two diagrams and visualize changes.

**Example API:**
```python
diff = gen.diff(diagram1_syntax, diagram2_syntax)
# Returns: nodes added, removed, modified; edges added, removed
diff.render()  # Side-by-side comparison image
```

**Implementation:**
- Parse both diagrams into abstract syntax trees (AST)
- Compute diff (added/removed/modified nodes and edges)
- Render side-by-side or highlight changes in output

**Benefits:**
- Version control integration
- Change tracking for documentation
- Audit trails for diagram evolution

---

### 5. REST API / Web service

**Opportunity:** Wrap the tool as a lightweight HTTP API.

**Example:**
```bash
# Start server
mermaid-diagram-server --port 8000

# Client request
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"syntax": "flowchart TD\n    A --> B", "format": "png"}'
```

**Implementation:**
- FastAPI or Flask wrapper
- OpenAPI/Swagger schema
- Docker image for deployment

**Benefits:**
- Integration with CI/CD pipelines
- Multi-user access (if deployed centrally)
- Language-agnostic (any HTTP client)

---

### 6. Output format extensions

**Opportunity:** Support additional output formats beyond PNG/SVG/PDF.

**Examples:**
- **WebP** — modern image format, smaller file sizes
- **JPEG** — lossy compression
- **GIF** — animated (if animation support is added)
- **Mermaid JSON** — AST representation for downstream tools
- **PlantUML output** — cross-format conversion

**Implementation:**
- Delegate to format libraries or post-processing
- Update CLI and API accordingly

**Benefits:**
- Flexibility in output delivery
- Format-specific optimizations (file size, quality)

---

### 7. Mermaid version pinning and updates

**Opportunity:** Allow users to specify mmdc/Mermaid version.

**Example:**
```python
gen = MermaidGenerator(mmdc_version="10.6.0")
# Or auto-detect and pin current version
```

**Scope:**
- Detect installed mmdc version
- Warn if version is very old
- Support version matrix in CI/CD

**Benefits:**
- Reproducible diagram rendering across environments
- Ability to upgrade mmdc deliberately
- Warning if system mmdc is outdated

---

### 8. Diagram validation and linting

**Opportunity:** Provide linting/validation before rendering.

**Example API:**
```python
issues = gen.lint("flowchart TD\n    A --> B\n    C --> D")
# Returns: unreachable node C, unused node D, etc.
```

**Scope:**
- Detect unreachable nodes
- Find unused variables
- Check for duplicate edge definitions
- Enforce naming conventions

**Benefits:**
- Catch diagram errors early
- Maintain diagram quality
- Educational (learning Mermaid best practices)

---

### 9. Documentation generation

**Opportunity:** Auto-generate documentation from diagrams (and vice versa).

**Example:**
```python
# Extract diagram metadata and generate markdown
doc = gen.to_markdown(diagram_syntax)
# Generates: title, description, node/edge definitions, etc.
```

**Scope:**
- Parse Mermaid syntax into structured format
- Generate human-readable descriptions
- Optionally generate diagrams from markdown specifications

**Benefits:**
- Bridge between code and documentation
- Automated API documentation generation
- Self-documenting diagrams

---

### 10. Integration with popular platforms

**Opportunity:** Native integration with documentation and diagramming platforms.

**Examples:**
- **Notion** — render diagrams in Notion pages
- **Obsidian** — plugin for diagram generation
- **Confluence** — macro for rendering diagrams
- **GitHub / GitLab** — automatic diagram rendering in markdown
- **Jupyter** — output diagrams in notebooks

**Implementation:**
- Plugin SDKs for each platform
- Embedding support for web-based platforms

**Benefits:**
- Seamless diagram inclusion in notes/docs
- Lower friction for users already in these tools

---

## Contributing Ideas

Have an idea for a feature? Consider:

1. **Scope:** Is it a small enhancement or a major architectural change?
2. **Complexity:** What dependencies would it introduce?
3. **Use case:** Who benefits and how?
4. **Alignment:** Does it fit the project's mission (batch-mode diagram rendering)?

Submit ideas as GitHub issues with:
- **Motivation:** Why is this useful?
- **Proposed API:** How would users interact with it?
- **Alternative approaches:** Any simpler alternatives?
- **Potential implementation:** Rough idea for how to build it

---

## Related Tools in This Project

For features not in mermaid-diagrams, consider these sibling tools:

- **`image-generation/`** — For AI-generated static images (blog illustrations with SDXL)
  - Tropical magical-realism aesthetic
  - Batch generation
  - Reproducible outputs via seed control
- **`manim-animation/`** — For animated mathematical visualizations
  - AI-powered script generation
  - Frame-by-frame animation
  - Mathematical rendering
- **`remotion-animation/`** — For web-based video and animation generation
  - React component-based animation
  - Rich media (video, audio, effects)
  - Export to MP4/WebM

Combining these tools can provide comprehensive diagramming, animation, and image generation capabilities for your documentation and presentations.
