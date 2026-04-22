# Documentation Index

Welcome to the **image-generation** project documentation. This repository contains **four complementary media generation tools**, each designed for specific use cases:

- 🎨 **image-generation** — AI-powered static image creation (SDXL)
- 🎬 **manim-animation** — Mathematical animations (Python + Manim)
- 🎞️ **remotion-animation** — Web-based video animations (React/TypeScript)
- 📊 **mermaid-diagrams** — Diagram rendering from Mermaid syntax

---

## Project Comparison Matrix

| Feature | image-generation | manim-animation | remotion-animation | mermaid-diagrams |
|---------|------------------|-----------------|-------------------|------------------|
| **Output Type** | Static PNG (1024×1024) | MP4 Video (5–30s) | MP4 Video (5–30s) | PNG/SVG/PDF |
| **LLM Required** | No | Yes (OpenAI/Ollama/Azure) | Yes (OpenAI/Ollama/Azure) | No |
| **Audio Support** | No | No | No | No |
| **Video Output** | No | Yes | Yes | No |
| **Static Images** | Yes | No | No | Yes |
| **Diagrams** | No | No | No | Yes |
| **Duration Limits** | N/A | 5–30 seconds | 5–30 seconds | N/A |
| **Web UI** | No | No | No | No |
| **CLI Only** | Yes | Yes | Yes | Yes |
| **Model/Style** | SDXL Base + Refiner (tropical) | Manim Community | Remotion React | Mermaid.js |
| **Setup Difficulty** | Medium (GPU needed) | Medium (LaTeX + FFmpeg) | Medium (Node.js) | Low (mmdc CLI) |
| **Primary Use Case** | Blog illustrations | Teaching/visualization | Web animations | Documentation diagrams |

---

## Quick Decision Tree: "What Do You Want to Create?"

```
START
  ├─ Static image (single output)?
  │  ├─ Blog-style illustration with tropical aesthetic?
  │  │  └─→ Use: image-generation ✓
  │  └─ Diagram/flowchart/ER model?
  │     └─→ Use: mermaid-diagrams ✓
  │
  ├─ Video/Animation (moving content)?
  │  ├─ Mathematical animations (graphs, equations, data viz)?
  │  │  └─→ Use: manim-animation ✓
  │  └─ Web-based animations (React components, creative effects)?
  │     └─→ Use: remotion-animation ✓
  │
  └─ Not sure?
     └─→ See tool descriptions below
```

---

## Navigation: All 28 Documentation Files

### 🎨 image-generation (SDXL Blog Illustrations)

Static image generation using SDXL for tropical magical-realism illustrations.

| Document | Purpose |
|----------|---------|
| [**user-guide.md**](image-generation/user-guide.md) | CLI flags, quick start, batch generation, prompt writing rules |
| [**architecture.md**](image-generation/architecture.md) | Pipeline flow, components, device selection (GPU/CPU), memory management |
| [**development.md**](image-generation/development.md) | Local setup, testing with pytest, code structure, contributing |
| [**installation.md**](image-generation/installation.md) | Prerequisites, venv setup, pip dependencies, GPU/CPU notes |
| [**testing.md**](image-generation/testing.md) | Test framework, running tests, coverage, adding new tests |
| [**troubleshooting.md**](image-generation/troubleshooting.md) | OOM errors, slow rendering, reproducibility, security notes |
| [**limitations-and-roadmap.md**](image-generation/limitations-and-roadmap.md) | What's NOT supported (animation, audio, inpainting), future features |

### 🎬 manim-animation (Mathematical Animations)

LLM-powered mathematical animation generation using Manim Community Edition.

| Document | Purpose |
|----------|---------|
| [**user-guide.md**](manim-animation/user-guide.md) | CLI flags, prompts, quality presets, duration limits, output options |
| [**architecture.md**](manim-animation/architecture.md) | LLM integration, prompt engineering, AST validation, rendering pipeline |
| [**development.md**](manim-animation/development.md) | Local setup, code structure, contributing, testing LLM output |
| [**installation.md**](manim-animation/installation.md) | Prerequisites (Python, Manim, LaTeX, FFmpeg), provider setup (Ollama/OpenAI/Azure) |
| [**testing.md**](manim-animation/testing.md) | Test structure, validation tests, rendering tests, mocking LLMs |
| [**troubleshooting.md**](manim-animation/troubleshooting.md) | FFmpeg/LaTeX not found, LLM errors, forbidden imports/functions, AST validation failures |
| [**limitations-and-roadmap.md**](manim-animation/limitations-and-roadmap.md) | No audio, no multi-scene, no 3D, no real-time preview, future phases |

### 🎞️ remotion-animation (Web-Based Animations)

LLM-powered video animation generation using Remotion (React components).

| Document | Purpose |
|----------|---------|
| [**user-guide.md**](remotion-animation/user-guide.md) | CLI setup, prompt writing, duration settings, component generation, compilation |
| [**architecture.md**](remotion-animation/architecture.md) | LLM-to-TSX generation, Remotion API, component structure, rendering flow |
| [**development.md**](remotion-animation/development.md) | Node.js setup, local development, debugging generated TSX, contributing |
| [**installation.md**](remotion-animation/installation.md) | Node.js/npm requirements, Remotion setup, LLM provider configuration |
| [**testing.md**](remotion-animation/testing.md) | Component testing, rendering tests, LLM output validation, snapshot tests |
| [**troubleshooting.md**](remotion-animation/troubleshooting.md) | Rendering failures, LLM errors, TypeScript issues, memory problems |
| [**limitations-and-roadmap.md**](remotion-animation/limitations-and-roadmap.md) | No audio, no multi-scene, no 3D, no real-time preview, future roadmap |

### 📊 mermaid-diagrams (Diagram Rendering)

Batch diagram rendering from Mermaid syntax (no LLM involved).

| Document | Purpose |
|----------|---------|
| [**user-guide.md**](mermaid-diagrams/user-guide.md) | CLI usage, input methods (syntax, files, templates), output formats (PNG/SVG/PDF) |
| [**architecture.md**](mermaid-diagrams/architecture.md) | mmdc integration, template registry, rendering pipeline, format handling |
| [**development.md**](mermaid-diagrams/development.md) | Local setup, code structure, template creation, contributing custom templates |
| [**installation.md**](mermaid-diagrams/installation.md) | Prerequisites (mmdc binary), Python dependencies, platform-specific setup |
| [**testing.md**](mermaid-diagrams/testing.md) | Test structure, rendering tests, format validation, template tests |
| [**troubleshooting.md**](mermaid-diagrams/troubleshooting.md) | mmdc not found, rendering failures, format issues, syntax validation errors |
| [**limitations-and-roadmap.md**](mermaid-diagrams/limitations-and-roadmap.md) | No LLM, no interactivity, no theming, no animation, future opportunities |

---

## Getting Started

### I want to generate a blog illustration

Start with [**image-generation/user-guide.md**](image-generation/user-guide.md):
```bash
python generate.py --prompt "Latin American folk art style, magical realism illustration of ..."
```

### I want to create a mathematical animation

Start with [**manim-animation/user-guide.md**](manim-animation/user-guide.md):
```bash
manim-gen --prompt "Animate a rotating cube in 3D space"
```

### I want to create a web-based animation

Start with [**remotion-animation/user-guide.md**](remotion-animation/user-guide.md):
```bash
remotion-gen --prompt "Blue circles bouncing around the screen"
```

### I want to render a diagram

Start with [**mermaid-diagrams/user-guide.md**](mermaid-diagrams/user-guide.md):
```bash
mermaid-diagram --syntax "flowchart TD\n    A --> B --> C"
```

---

## Common Tasks

### Setup & Installation

- **image-generation:** [Installation guide](image-generation/installation.md)
- **manim-animation:** [Installation guide](manim-animation/installation.md) + [LLM provider setup](manim-animation/installation.md)
- **remotion-animation:** [Installation guide](remotion-animation/installation.md) + [LLM provider setup](remotion-animation/installation.md)
- **mermaid-diagrams:** [Installation guide](mermaid-diagrams/installation.md)

### Architecture & Design

- [image-generation architecture](image-generation/architecture.md)
- [manim-animation architecture](manim-animation/architecture.md)
- [remotion-animation architecture](remotion-animation/architecture.md)
- [mermaid-diagrams architecture](mermaid-diagrams/architecture.md)

### Development & Contributing

- [image-generation development](image-generation/development.md)
- [manim-animation development](manim-animation/development.md)
- [remotion-animation development](remotion-animation/development.md)
- [mermaid-diagrams development](mermaid-diagrams/development.md)

### Testing

- [image-generation testing](image-generation/testing.md)
- [manim-animation testing](manim-animation/testing.md)
- [remotion-animation testing](remotion-animation/testing.md)
- [mermaid-diagrams testing](mermaid-diagrams/testing.md)

### Troubleshooting

- [image-generation troubleshooting](image-generation/troubleshooting.md)
- [manim-animation troubleshooting](manim-animation/troubleshooting.md)
- [remotion-animation troubleshooting](remotion-animation/troubleshooting.md)
- [mermaid-diagrams troubleshooting](mermaid-diagrams/troubleshooting.md)

### Limitations & Future Roadmap

- [image-generation limitations](image-generation/limitations-and-roadmap.md)
- [manim-animation limitations](manim-animation/limitations-and-roadmap.md)
- [remotion-animation limitations](remotion-animation/limitations-and-roadmap.md)
- [mermaid-diagrams limitations](mermaid-diagrams/limitations-and-roadmap.md)

---

## Combining Tools

You can combine tools for powerful workflows:

**Example 1: Illustrated Blog Post**
1. Generate static illustrations → **image-generation**
2. Create animated diagrams → **mermaid-diagrams** + **manim-animation**
3. Render intro/outro animations → **remotion-animation**
4. Stitch together with FFmpeg

**Example 2: Educational Content**
1. Create mathematical animations → **manim-animation**
2. Add flowcharts/architecture diagrams → **mermaid-diagrams**
3. Generate hero/thumbnail images → **image-generation**

**Example 3: Interactive Documentation**
1. Static diagrams → **mermaid-diagrams** or **image-generation**
2. Data visualizations → **manim-animation**
3. Web animations → **remotion-animation**

---

## Tool Comparison Details

### When to Use Each Tool

**image-generation:**
- ✓ Blog post illustrations in tropical magical-realism style
- ✓ Batch generation of multiple images
- ✓ Reproducible outputs (seed control)
- ✗ Animation, video, diagrams, or general-purpose image generation

**manim-animation:**
- ✓ Mathematical visualizations (graphs, equations, data)
- ✓ Educational animations (proofs, processes)
- ✓ Procedurally generated content
- ✗ Realistic animation, long-form content (30s max), audio

**remotion-animation:**
- ✓ Web-based animations (React components)
- ✓ Creative motion graphics
- ✓ Interactive component-driven animation
- ✗ 3D animation, real-time preview, audio

**mermaid-diagrams:**
- ✓ Documentation diagrams (flowcharts, ER, sequence)
- ✓ Batch rendering from code/files
- ✓ Multiple output formats (PNG, SVG, PDF)
- ✗ Animation, LLM-powered generation, custom theming

---

## FAQ

**Q: Can I use multiple tools in one project?**  
A: Yes! Many projects use all four tools for complementary purposes. See "Combining Tools" above.

**Q: Which tool requires GPU?**  
A: image-generation (for SDXL, but CPU mode available). manim-animation and remotion-animation run on CPU fine.

**Q: Do I need an LLM API key?**  
A: Only for manim-animation and remotion-animation. image-generation and mermaid-diagrams don't use LLMs.

**Q: Which tool is fastest?**  
A: mermaid-diagrams (instant, no GPU). remotion-animation compiles in ~10–30s. image-generation and manim-animation take 2–30 min depending on settings.

**Q: Can I extend or customize the tools?**  
A: Yes! All tools support custom components/templates. See development guides for each tool.

**Q: How do I report bugs or request features?**  
A: Open an issue on GitHub or check the limitations document for each tool.

---

## Project Structure

```
image-generation/
├── docs/                          ← YOU ARE HERE
│   ├── README.md                  ← Main documentation index (this file)
│   ├── image-generation/          ← 7 docs
│   ├── manim-animation/           ← 7 docs
│   ├── remotion-animation/        ← 7 docs
│   └── mermaid-diagrams/          ← 7 docs
├── image-generation/              ← SDXL generation tool
├── manim-animation/               ← Manim animation tool
├── remotion-animation/            ← Remotion animation tool
└── mermaid-diagrams/              ← Mermaid diagram tool
```

Each tool is independent but documented together for easy cross-reference.

---

## Related Resources

- [GitHub Repository](https://github.com/dfberry/image-generation)
- [Project README](../README.md)
- [Contributing Guidelines](../CODEOWNERS)

---

**Last Updated:** April 2026  
**Documentation Version:** Phase 0 (MVP)
