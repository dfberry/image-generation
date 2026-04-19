# Security Documentation

## LoRA Weights Trust Boundary

**LoRA (Low-Rank Adaptation) weights are untrusted code execution contexts.**

When loading LoRA adapters via the `--lora` flag, PyTorch's `load()` function deserializes arbitrary Python objects from the weight files. This **can execute arbitrary code** on your machine during deserialization.

### Risk Summary

- **Attack Vector:** A malicious `.safetensors` or `.pth` file containing embedded Python objects
- **Execution Context:** Code runs with the same privileges as the image-generation process
- **Scope:** Affects any LoRA weights from untrusted sources

### Best Practices

#### ✅ DO:
- **Only load LoRA weights from trusted sources** (official model repositories, vetted providers)
- **Verify file integrity** using checksums or signatures when available
- **Inspect `.pth` file contents** before loading (use `torch.load(..., weights_only=True)` where possible)
- **Use `.safetensors` format** when available (safer serialization format)
- **Run image generation in isolated environments** (containers, virtual machines) when processing untrusted workflows

#### ❌ DON'T:
- **Load arbitrary `.pth` files** from unknown sources
- **Assume `.safetensors` is unhackable** — check the source and metadata
- **Run untrusted LoRA workflows** with elevated privileges or sensitive credentials

### Technical Details

The image-generation pipeline loads LoRA weights using PyTorch's `load()` function:

```python
# UNSAFE: Code can execute during deserialization
lora_weights = torch.load(lora_path)  # Remote code execution possible here
```

### Mitigation Strategies

For production workflows handling LoRA weights:

1. **Use allowlists** — maintain a curated list of approved model sources
2. **Container isolation** — run in Docker/Kubernetes with limited capabilities
3. **Code review** — validate LoRA sources before adding to batch files
4. **Monitoring** — log all LoRA loads and their sources for audit trails
5. **Future work** — consider pre-validating weights with static analysis tools

### Related Issues

- Issue #57 — Document LoRA trust boundary (this document)
- Issue #58 — Document safety_checker=None decision (below)

---

## `safety_checker=None` — Deliberate Decision

In `generate.py`, both `load_base()` and `load_refiner()` set
`pipe.safety_checker = None` on the loaded pipeline.

### Why this is NOT disabling safety

The SDXL Base 1.0 (`stabilityai/stable-diffusion-xl-base-1.0`) and its
companion refiner **do not ship a safety-checker module**. Unlike earlier
Stable Diffusion 1.x / 2.x checkpoints, the SDXL architecture was released
without a bundled NSFW classifier.

Setting `safety_checker = None` therefore:

- **Prevents an attribute-lookup error** that would otherwise occur when
  diffusers tries to invoke a checker that does not exist.
- **Does not remove a working filter** — there is nothing to remove.
- **Is the documented practice** in the diffusers library for SDXL pipelines.

### Where to look

| Location | Purpose |
|---|---|
| `generate.py → load_base()` | Sets `pipe.safety_checker = None` on the base pipeline |
| `generate.py → load_refiner()` | Sets `refiner.safety_checker = None` on the refiner pipeline |

Both call sites include inline comments explaining the rationale
(added in PR #75).

### If a safety classifier is needed

If you later need content filtering, consider:

1. **External classifier** — run a separate NSFW/content-policy model on the
   output image *after* generation (e.g., `CompVis/stable-diffusion-safety-checker`
   or a custom classifier).
2. **Prompt-level filtering** — validate prompts against a blocklist before they
   reach the pipeline.
3. **Wait for upstream support** — if Stability AI or the diffusers project adds
   a native SDXL safety checker, integrate it by removing the `= None` lines and
   letting the default behaviour take over.

---

**Last updated:** 2025-07-17
