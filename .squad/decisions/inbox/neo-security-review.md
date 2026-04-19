# D6: Security Review — Neo (Tester)

**Date:** 2026-07-26
**Scope:** Full codebase security audit (Dimension D6, Phase 3)
**Status:** Complete — READ-ONLY review, no source files modified

**Files reviewed:** generate.py, generate_blog_images.sh, .github/workflows/tests.yml, .github/workflows/sync-squad-labels.yml, .github/workflows/squad-triage.yml, .github/workflows/squad-issue-assign.yml, .github/workflows/squad-heartbeat.yml, CODEOWNERS, .gitignore, requirements.txt, requirements-dev.txt, batch_blog_images.json, batch_blog_images_v2.json, batch_session_storage.json

---

## Findings (10)

### D6-001 — HuggingFace model IDs not pinned to revision
**Severity:** MEDIUM
**File:** generate.py:142-146, generate.py:165-170
**Dimension:** D6
**Description:** Both `stabilityai/stable-diffusion-xl-base-1.0` and `stabilityai/stable-diffusion-xl-refiner-1.0` are loaded via `DiffusionPipeline.from_pretrained()` without a `revision=` parameter. This means the code always pulls the latest version from the `main` branch of the HuggingFace repo. If the upstream model is modified (accidentally or maliciously), downstream builds silently change behavior. Supply-chain risk.
**Evidence:**
```python
pipe = DiffusionPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=dtype,
    use_safetensors=True,
    ...
)
```
**Recommendation:** Pin both model IDs to a specific commit SHA via `revision="<commit-sha>"`. Document the pinned revision in a comment or config file. Update intentionally when needed.

---

### D6-002 — Batch-file output path allows directory traversal
**Severity:** HIGH
**File:** generate.py:249-253, generate.py:328, generate.py:372-373
**Dimension:** D6
**Description:** The `--batch-file` JSON `"output"` field is used verbatim as the file write path with no sanitization. An attacker-crafted JSON file could write to arbitrary paths (e.g., `"output": "../../.bashrc"` or `"output": "/etc/cron.d/evil"`). The existing batch JSON files already demonstrate this — they write to absolute paths outside the project directory (e.g., `C:\Users\diberry\project-dfb\dfberry.github.io\...`).
**Evidence:**
```python
# generate.py:328
image.save(output_path)

# batch_blog_images.json line 6:
"output": "C:\\Users\\diberry\\project-dfb\\dfberry.github.io\\website\\blog\\media\\..."
```
**Recommendation:** Either (a) validate that output paths resolve within an allowed directory (e.g., `outputs/`), or (b) at minimum, document the trust model — that batch JSON files are trusted input. Option (a) is safer for any multi-user or CI context.

---

### D6-003 — Arbitrary scheduler class instantiation via getattr(diffusers, ...)
**Severity:** MEDIUM
**File:** generate.py:202-214
**Dimension:** D6
**Description:** The `--scheduler` CLI argument is used with `getattr(diffusers, scheduler_name)` to dynamically instantiate any attribute from the `diffusers` module. While the `SUPPORTED_SCHEDULERS` list exists for documentation, it is NOT used as a whitelist — the validation only checks `hasattr(diffusers, scheduler_name)`. A user could pass any diffusers class name, potentially triggering unexpected behavior.
**Evidence:**
```python
def apply_scheduler(pipeline, scheduler_name: str):
    if not hasattr(diffusers, scheduler_name):
        raise ValueError(...)
    scheduler_cls = getattr(diffusers, scheduler_name)  # No whitelist check
    ...
    pipeline.scheduler = scheduler_cls.from_config(config)
```
**Recommendation:** Validate `scheduler_name` against `SUPPORTED_SCHEDULERS` explicitly: `if scheduler_name not in SUPPORTED_SCHEDULERS: raise ValueError(...)`. The list already exists — use it as the gatekeeper.

---

### D6-004 — LoRA model loading from arbitrary paths
**Severity:** MEDIUM
**File:** generate.py:217-223
**Dimension:** D6
**Description:** The `--lora` argument accepts an arbitrary HuggingFace model ID or local filesystem path. `pipeline.load_lora_weights(lora)` will download from HuggingFace or load from local disk with no validation. A malicious LoRA weight file could alter model behavior. No revision pinning is possible through this interface.
**Evidence:**
```python
def apply_lora(pipeline, lora: str | None, lora_weight: float = 0.8):
    if lora is None:
        return
    pipeline.load_lora_weights(lora)  # Arbitrary path or HF model ID
```
**Recommendation:** Document the trust boundary for LoRA loading. Consider restricting to a known-safe list of LoRA IDs or local paths, or at least warn the user when loading from untrusted sources.

---

### D6-005 — Safety checker explicitly disabled
**Severity:** LOW
**File:** generate.py:148, generate.py:173
**Dimension:** D6
**Description:** The NSFW safety checker is explicitly set to `None` on both base and refiner pipelines. While this is a deliberate choice for an art generation tool, it removes the content-safety guardrail. Anyone with access to this tool can generate unrestricted content.
**Evidence:**
```python
pipe.safety_checker = None
```
**Recommendation:** Acknowledge this as a deliberate decision. If the tool is ever shared publicly or used in a team context, consider making the safety checker opt-out (default on, `--no-safety-check` flag) rather than always-off.

---

### D6-006 — requirements.txt uses minimum version pins (>=), not exact pins
**Severity:** LOW
**File:** requirements.txt:1-7
**Dimension:** D6
**Description:** All dependencies use `>=` version constraints. This means `pip install` will pull the latest compatible version, which could introduce untested behavior or known CVEs. No `requirements.lock` or hash verification exists.
**Evidence:**
```
diffusers>=0.21.0
transformers>=4.30.0
accelerate>=0.24.0
safetensors>=0.3.0
invisible-watermark>=0.2.0
torch>=2.1.0
Pillow>=10.0.0
```
**Recommendation:** For reproducibility and supply-chain safety, add a `requirements.lock` (or `pip freeze > requirements.lock`) with pinned exact versions. Consider using `pip install --require-hashes` for CI builds.

---

### D6-007 — Batch JSON fields not validated before use
**Severity:** MEDIUM
**File:** generate.py:371-388
**Dimension:** D6
**Description:** In `batch_generate()`, JSON items are accessed with `item["prompt"]` and `item["output"]` with no schema validation. Missing or unexpected keys will raise a `KeyError` with a stack trace (information leak). Malformed JSON with extra keys (e.g., `"steps": -1`) could inject unexpected batch args via `item.get()` calls.
**Evidence:**
```python
batch_args = SimpleNamespace(
    prompt=item["prompt"],        # KeyError if missing
    output=item["output"],        # KeyError if missing
    seed=item.get("seed"),        # Attacker can inject
    negative_prompt=item.get("negative_prompt", ...),
    lora=item.get("lora", ...),   # Attacker can inject LoRA
    lora_weight=item.get("lora_weight", ...),
)
```
**Recommendation:** Add schema validation for batch JSON entries — require `prompt` and `output` as mandatory strings, validate `seed` as int, validate `lora` if present. Reject unknown keys or at minimum ignore them.

---

### D6-008 — GitHub Actions workflow uses `secrets.COPILOT_ASSIGN_TOKEN` with broad scope
**Severity:** LOW
**File:** .github/workflows/squad-issue-assign.yml:121
**Dimension:** D6
**Description:** The `squad-issue-assign.yml` workflow uses `secrets.COPILOT_ASSIGN_TOKEN` (a PAT) to assign the Copilot SWE agent. If this PAT has scopes broader than `issues:write` on this specific repo, it could be abused if the workflow is compromised. The heartbeat workflow also falls back between tokens: `${{ secrets.COPILOT_ASSIGN_TOKEN || secrets.GITHUB_TOKEN }}`.
**Evidence:**
```yaml
github-token: ${{ secrets.COPILOT_ASSIGN_TOKEN }}
# and in heartbeat:
github-token: ${{ secrets.COPILOT_ASSIGN_TOKEN || secrets.GITHUB_TOKEN }}
```
**Recommendation:** Ensure `COPILOT_ASSIGN_TOKEN` is a fine-grained PAT scoped to only `issues:write` on this repository. Document the required scopes in the repo README or CONTRIBUTING.md.

---

### D6-009 — No secrets detected in committed files
**Severity:** INFO
**File:** (all scanned files)
**Dimension:** D6
**Description:** Comprehensive scan of all `*.py`, `*.sh`, `*.json`, `*.md`, `*.yml` files found no hardcoded API keys, tokens, passwords, or secrets. The `.gitignore` correctly excludes `.env` files, model weights (`.bin`, `.safetensors`, `.ckpt`, `.pt`, `.pth`), and generated outputs. No `os.system()`, `subprocess`, `eval()`, `exec()`, or `pickle` usage detected in production code.
**Evidence:** Grep across all file types returned zero matches for secret patterns in production files. `.gitignore` covers common sensitive patterns.
**Recommendation:** None — this is a positive finding. Consider adding a pre-commit hook (e.g., `detect-secrets`) to maintain this posture.

---

### D6-010 — CI workflow has minimal permissions (positive finding)
**Severity:** INFO
**File:** .github/workflows/tests.yml:8
**Dimension:** D6
**Description:** The `tests.yml` workflow sets `permissions: {}` at the top level, which is the most restrictive setting (no permissions). This is a security best practice. The workflow also gates on specific actors (`diberry`, `dfberry`) and the `run-ci` label, preventing arbitrary PR authors from triggering CI. GitHub event data (`github.event.label.name`, `github.actor`) is used only in `if:` conditions, not interpolated into shell commands — no injection risk.
**Evidence:**
```yaml
permissions: {}
```
**Recommendation:** None — this is exemplary. Other workflows correctly scope permissions to `issues: write` and `contents: read` as needed.

---

## Summary

| Severity | Count | IDs |
|----------|-------|-----|
| CRITICAL | 0 | — |
| HIGH | 1 | D6-002 |
| MEDIUM | 4 | D6-001, D6-003, D6-004, D6-007 |
| LOW | 3 | D6-005, D6-006, D6-008 |
| INFO | 2 | D6-009, D6-010 |

**Top priority fix:** D6-002 (output path traversal in batch mode) — the only HIGH finding. The batch JSON `output` field can write to arbitrary filesystem paths with no validation.

**What was NOT tested:**
- Git history was not scanned for secrets (would require `git log` + regex, or a tool like `trufflehog`)
- Runtime behavior of `diffusers` model loading was not tested (would require a live environment)
- Network-level risks (HuggingFace download over HTTPS, no certificate pinning) were not assessed
- No CVE database lookup was performed against pinned dependency versions
