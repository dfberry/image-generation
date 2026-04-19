# Multi-Tool Media Generation Suite

This repository contains multiple media generation tools powered by AI models.

## Tools

| Tool | Description | Status |
|------|-------------|--------|
| [image-generation/](image-generation/) | Stable Diffusion XL image generation with batch processing | ✅ Active |
| [mermaid-diagrams/](mermaid-diagrams/) | Diagram generation from text | 🔜 Planned |

## Getting Started

See the README in each tool's folder for setup and usage instructions.

## Development

- **CI:** GitHub Actions runs lint + tests on PRs labeled `run-ci`
- **Team docs:** `.squad/agents/` for team member charters, `.squad/decisions.md` for architecture decisions
- **Contributing:** See [image-generation/CONTRIBUTING.md](image-generation/CONTRIBUTING.md)

## License

- Model weights: [CreativeML Open RAIL++-M License](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md)
- Code: MIT
