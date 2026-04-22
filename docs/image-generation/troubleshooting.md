← [Back to Documentation Index](../README.md)

# Troubleshooting Guide — image-generation

Comprehensive guide to common issues and their solutions.

## GPU & Device Issues

### Out of GPU Memory (OOM)

**Symptom:**
```
RuntimeError: CUDA out of memory. Tried to allocate X GiB...
```
or
```
RuntimeError: ... out of memory ...
```

**What's happening:** The SDXL base model (7GB) + refiner (6GB) + intermediate tensors exceed your GPU VRAM.

**Solutions (in order of preference):**

1. **Let the automatic retry system work first**
   - The tool automatically retries on OOM, halving steps each time (up to 2 retries)
   - Watch for `OOM: retrying with X steps` in the logs
   - If retries exhaust, you'll see: `Out of GPU memory after 2 retries. Last attempt used X steps.`

2. **Reduce steps manually**
   ```bash
   # Default is 22 steps. Try 15:
   python generate.py --prompt "..." --steps 15
   
   # For very constrained GPUs (4GB VRAM):
   python generate.py --prompt "..." --steps 8
   ```

3. **Disable the refiner**
   ```bash
   # Refiner doubles memory usage. Remove --refine:
   python generate.py --prompt "..." --steps 22
   # (Without --refine, only base model loads)
   ```

4. **Reduce image resolution**
   ```bash
   # Default is 1024×1024. Try 768×768:
   python generate.py --prompt "..." --width 768 --height 768
   ```

5. **Switch to CPU mode**
   ```bash
   # No GPU required, but expect 20–30+ minutes per image
   python generate.py --prompt "..." --cpu
   ```

6. **Close other GPU applications**
   - Close browser tabs, Discord, other ML tasks
   - Reboot to clear GPU memory cache if OOM persists

**Device-specific guidance:**
- **NVIDIA 4GB VRAM:** Use `--steps 8` or `--cpu`
- **NVIDIA 6GB VRAM:** Use `--steps 15`, no `--refine`
- **NVIDIA 8GB VRAM:** Standard settings work (22 steps, optional refine)
- **Apple Silicon:** Generally sufficient; OOM rare but use `--steps 15` if needed

---

### CUDA Not Detected (Falls Back to CPU)

**Symptom:**
```
WARNING: No GPU detected — falling back to CPU (slow)
```

**Diagnosis:**
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

**Solutions:**

1. **Install CUDA-enabled PyTorch**
   ```bash
   # CUDA 12.1 (most common for recent GPUs)
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   
   # CUDA 11.8 (older systems)
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   
   # Verify
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Check NVIDIA driver**
   ```bash
   nvidia-smi
   ```
   If this fails, update your NVIDIA driver from [nvidia.com/Download](https://www.nvidia.com/Download/index.aspx).

3. **Verify CUDA toolkit installation**
   ```bash
   nvcc --version
   ```
   If missing, install from [developer.nvidia.com/cuda-toolkit](https://developer.nvidia.com/cuda-toolkit).

4. **Force CPU mode intentionally**
   ```bash
   python generate.py --prompt "..." --cpu
   ```

---

### Apple Silicon (MPS) Not Available

**Symptom:**
```
INFO: No GPU detected — falling back to CPU (slow)
```
on a Mac with Apple Silicon.

**Solutions:**

1. **Ensure Python is ARM-native**
   ```bash
   python -c "import platform; print(platform.machine())"
   # Should print: arm64
   # If x86_64, you're using Rosetta 2 emulation — reinstall Python from python.org
   ```

2. **Install arm64-native dependencies**
   ```bash
   # Deactivate venv, remove it, and recreate with arm64 Python:
   deactivate
   rm -rf venv
   /opt/homebrew/bin/python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Verify MPS is available**
   ```bash
   python -c "
   import torch
   if hasattr(torch.backends, 'mps'):
       print('MPS available:', torch.backends.mps.is_available())
   else:
       print('MPS not available (older PyTorch)')
   "
   ```

4. **Use `--cpu` as a fallback**
   ```bash
   python generate.py --prompt "..." --cpu
   ```

---

### First Generation Takes 30+ Seconds (Longer Than Usual)

**Symptom:** First image takes 40+ seconds on CUDA (vs. 2–5 min on subsequent images), but not always.

**What's happening:** `torch.compile` warm-up phase on CUDA GPUs. Compiles the UNet once per session (~30s one-time cost).

**This is normal and expected.** Subsequent images in the same process are faster.

**To verify:**
```bash
# Run two images back-to-back
python generate.py --prompt "image 1" --seed 1
python generate.py --prompt "image 2" --seed 2
# Second command will be faster
```

---

## Model Download & Disk Space

### Insufficient Disk Space

**Symptom:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**

1. **Check available disk space**
   ```bash
   # Linux/macOS
   df -h
   
   # Windows
   dir C:
   ```

2. **Free up space**
   - SDXL Base: ~7GB
   - SDXL Refiner: ~6GB (only needed with `--refine`)
   - Total: ~13GB if using both

3. **Change cache directory (optional)**
   ```bash
   # Use a different disk with more space
   export HF_HOME=/path/to/larger/disk/.cache/huggingface
   python generate.py --prompt "..."
   ```

### Model Download Fails

**Symptom:**
```
HTTPError: 401 Client Error: Unauthorized
```
or
```
ConnectionError: Connection aborted
```

**Solutions:**

1. **Accept Hugging Face model license**
   - Visit [huggingface.co/stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
   - Click "Agree and access repository"
   - Login to Hugging Face if prompted

2. **Use a Hugging Face API token (if behind proxy)**
   ```bash
   huggingface-cli login
   # Enter your API token from https://huggingface.co/settings/tokens
   ```

3. **Retry with a stable connection**
   ```bash
   # If behind a proxy or on flaky Wi-Fi, enable retry:
   export HF_HUB_ENABLE_HF_TRANSFER=1
   pip install hf-transfer  # Install helper
   python generate.py --prompt "..."
   ```

4. **Pre-download models manually (if offline after first run)**
   ```bash
   # Once models are cached in ~/.cache/huggingface/, tool works offline
   # On the first machine:
   python generate.py --prompt "test" --steps 1  # Download models
   
   # Then transfer ~/.cache/huggingface/ to target machine
   # Tool will use cached models (no internet needed)
   ```

---

## torch.compile Errors

### CUDA Compilation Failed

**Symptom:**
```
RuntimeError: Compilation failed ...
```
or
```
triton.compiler.CompilationError: ...
```

**What's happening:** `torch.compile` with `fullgraph=True` was attempted, but SDXL's UNet has dynamic control flow.

**Solution:** The current code uses `fullgraph=False` (safe default). If you modified the code, revert it:

```python
# In generate.py, _apply_performance_opts():
pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead")
# ✓ Correct: fullgraph=False is the default, or omit it entirely

# ✗ Do NOT use:
# pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)
```

---

## Batch Generation Failures

### Batch File Not Found

**Symptom:**
```
Error: Batch file not found: /path/to/batch.json
```

**Solutions:**

1. **Check file path**
   ```bash
   ls -la /path/to/batch.json  # or dir on Windows
   ```

2. **Use absolute path or relative from cwd**
   ```bash
   # From image-generation/ directory:
   python generate.py --batch-file ./batch_prompts.json
   
   # Or absolute:
   python generate.py --batch-file /full/path/to/batch_prompts.json
   ```

### Invalid JSON in Batch File

**Symptom:**
```
Error: Invalid JSON in batch file: Expecting value: line 1 column 1
```

**Solutions:**

1. **Validate JSON syntax**
   ```bash
   python -m json.tool batch_prompts.json > /dev/null
   # If no error, JSON is valid
   ```

2. **Common mistakes**
   - Missing commas between array elements:
     ```json
     [
       {"prompt": "...", "output": "1.png"}  // ✗ Missing comma
       {"prompt": "...", "output": "2.png"}
     ]
     ```
   - Trailing comma in last element (invalid in JSON):
     ```json
     [
       {"prompt": "...", "output": "1.png"},
     ]  // ✗ Trailing comma
     ```

3. **Use a JSON validator**
   - Online: [jsonlint.com](https://www.jsonlint.com)
   - VSCode: Install "JSON" extension, errors appear inline

### Missing Required Keys in Batch Item

**Symptom:**
```
Batch item 0: missing required key 'prompt'
```

**Solutions:**

1. **Ensure each batch item has `prompt` and `output`**
   ```json
   [
     {
       "prompt": "Latin American folk art style, magical realism illustration of ..., no text",
       "output": "outputs/01.png"
     }
   ]
   ```

2. **Optional keys:** `seed`, `negative_prompt`, `scheduler`, `refiner_steps`, `lora`, `lora_weight`

### Batch Job Partially Failed

**Symptom:**
```
[error] Latin American folk art ... → ValueError: ...
[ok] Latin American folk art ... → outputs/01.png
```

**Expected behavior:** `batch_generate()` continues processing remaining items if one fails. Check the output log for per-item status.

**To isolate the failed item:**
```bash
# Run with verbose logging
python generate.py --batch-file batch_prompts.json 2>&1 | grep "\[error\]"
```

---

## Scheduler Compatibility Issues

### Unsupported Scheduler Name

**Symptom:**
```
ValueError: 'MyScheduler' is not a supported scheduler. Valid options: DPMSolverMultistepScheduler, ...
```

**Solutions:**

1. **Use a supported scheduler**
   ```bash
   python generate.py --prompt "..." --scheduler DPMSolverMultistepScheduler
   ```

2. **List of supported schedulers**
   ```
   DPMSolverMultistepScheduler (default)
   EulerDiscreteScheduler
   EulerAncestralDiscreteScheduler
   DDIMScheduler
   LMSDiscreteScheduler
   PNDMScheduler
   UniPCMultistepScheduler
   HeunDiscreteScheduler
   KDPM2DiscreteScheduler
   DEISMultistepScheduler
   ```

### Scheduler Not Available in diffusers

**Symptom:**
```
ValueError: Unknown scheduler: MyScheduler
```

**Solution:** Upgrade diffusers
```bash
pip install --upgrade diffusers
```

---

## LoRA Loading Problems

### LoRA Model Not Found

**Symptom:**
```
OSError: Model ID does not contain a file_name value ...
```

**Solutions:**

1. **Use a valid Hugging Face LoRA ID**
   ```bash
   # Valid format: username/model-name
   python generate.py --prompt "..." --lora "joachim_s/aether-watercolor-and-ink-sdxl"
   ```

2. **Or use a local file path**
   ```bash
   python generate.py --prompt "..." --lora "./my_lora_model"
   ```

3. **Find LoRAs on Hugging Face**
   - Search [huggingface.co](https://huggingface.co) for "SDXL LoRA"
   - Verify the repo has SDXL-compatible weights

### LoRA Weight Out of Range

**Symptom:**
```
ArgumentTypeError: must be >= 0, got 1.5
```

**Solution:** LoRA weight must be 0.0–1.0
```bash
# ✓ Correct
python generate.py --prompt "..." --lora "model" --lora-weight 0.8

# ✗ Wrong
python generate.py --prompt "..." --lora "model" --lora-weight 1.5
```

---

## Memory Cleanup Failures

### Memory Leaks in Long-Running Sessions

**Symptom:** Multiple generations in a session use increasing amounts of GPU memory.

**What's happening:** Pipelines or tensors from prior generations weren't fully freed.

**Solutions:**

1. **Batch generation already handles this**
   - `batch_generate()` flushes GPU memory between items automatically
   - Use `--batch-file` for multiple images

2. **For single-image generation, restart Python**
   ```bash
   # Each invocation starts a fresh process
   python generate.py --prompt "image 1"
   python generate.py --prompt "image 2"  # Fresh process, no leak
   ```

3. **If running in a script, ensure cleanup**
   - The `generate()` function has a `finally` block that cleans up unconditionally
   - Check for `del`, `gc.collect()`, and `empty_cache()` calls

---

## Pip Install Issues

### Incompatible Torch Version

**Symptom:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**Solution:**

1. **Reinstall torch for your device**
   ```bash
   pip uninstall torch -y
   
   # For NVIDIA CUDA 12.1:
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   
   # For NVIDIA CUDA 11.8:
   pip install torch --index-url https://download.pytorch.org/whl/cu118
   
   # For CPU only:
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   
   # For Apple Silicon (arm64):
   pip install torch  # Default PyTorch handles this
   ```

2. **Verify installation**
   ```bash
   python -c "import torch; print(torch.__version__)"
   ```

### Platform-Specific Wheel Issues

**Symptom:**
```
ERROR: No matching distribution found for torch ...
```

**Solutions:**

1. **On Apple Silicon with Intel Python (Rosetta 2)**
   - Install arm64-native Python from [python.org](https://www.python.org/downloads/macos/)

2. **On Linux ARM (e.g., Raspberry Pi, NVIDIA Jetson)**
   - Use PyTorch's official ARM wheels:
     ```bash
     # For Jetson (CUDA):
     pip install torch --index-url https://download.pytorch.org/whl/cu121
     
     # For generic ARM:
     pip install torch  # May need to build from source
     ```

3. **Check Python version**
   ```bash
   python --version
   # Must be 3.10 or higher
   ```

---

## Permission Errors on Output Directory

### Cannot Write to `outputs/` Directory

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: 'outputs/image_XXX.png'
```

**Solutions:**

1. **Check directory permissions**
   ```bash
   ls -la outputs/
   ```

2. **Make directory writable**
   ```bash
   chmod 755 outputs/  # Add write permission
   ```

3. **Use a different output path**
   ```bash
   python generate.py --prompt "..." --output /tmp/my_image.png
   ```

4. **On Windows, check ACL**
   - Right-click folder → Properties → Security → Edit permissions

### Output Directory Doesn't Exist

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'outputs/...'
```

**Solution:** The tool creates `outputs/` automatically, but if using a custom path:
```bash
mkdir -p outputs
python generate.py --prompt "..." --output outputs/my_image.png
```

---

## Dimension Validation Errors

### Image Width/Height Not Divisible by 8

**Symptom:**
```
ArgumentTypeError: must be divisible by 8, got 1000 (nearest valid: 1000)
```

**Solution:** Dimensions must be ≥64 and divisible by 8

```bash
# ✗ Wrong (1000 ÷ 8 = 125 remainder)
python generate.py --prompt "..." --width 1000 --height 1000

# ✓ Correct
python generate.py --prompt "..." --width 1024 --height 1024  # 1024 ÷ 8 = 128
python generate.py --prompt "..." --width 512 --height 512    # 512 ÷ 8 = 64
python generate.py --prompt "..." --width 768 --height 768    # 768 ÷ 8 = 96
```

### Dimension Too Small

**Symptom:**
```
ArgumentTypeError: must be >= 64, got 32
```

**Solution:** Minimum dimension is 64 pixels
```bash
python generate.py --prompt "..." --width 512 --height 512  # ✓ Valid
```

---

## Environment Variable Issues

### Model Cache Not Found

**Symptom:**
```
Model not found at ~/.cache/huggingface/...
```

**Solutions:**

1. **Set custom cache directory**
   ```bash
   export HF_HOME=/path/to/cache
   python generate.py --prompt "..."
   ```

2. **Or use TORCH_HOME for PyTorch cache**
   ```bash
   export TORCH_HOME=/path/to/torch/cache
   python generate.py --prompt "..."
   ```

3. **Verify cache directory is writable**
   ```bash
   ls -la ~/.cache/huggingface/
   chmod 755 ~/.cache/huggingface/
   ```

### GPU Visibility Issues

**Symptom:** Only one GPU used, but multiple are available.

**Solution:**
```bash
# Restrict to GPU 0 only
export CUDA_VISIBLE_DEVICES=0
python generate.py --prompt "..."

# Or use GPUs 0 and 1
export CUDA_VISIBLE_DEVICES=0,1
python generate.py --prompt "..."
```

---

## Slow First Generation (Torch.compile Warm-up)

**Expected behavior on CUDA:** First image takes ~30s longer due to `torch.compile` JIT compilation.

**Breakdown:**
- Model loading: ~5–10s
- torch.compile UNet: ~20–30s
- Generation: ~2–5 min
- **Total first image: ~3–6 min**

**Subsequent images:** ~2–5 min (compilation is cached)

**Why:** Compiling the UNet to GPU machine code once per session provides 1.5–2× speedup on subsequent generations. The cost is amortized over multiple images.

**To minimize warm-up time:**
- Run batch jobs with `--batch-file` (one process, multiple images)
- Or accept slower first image in single-image workflows

---

## Output Path Security Checks

### Path Traversal Blocked

**Symptom:**
```
ValueError: Directory traversal blocked: 'outputs/../../../etc/passwd' contains '..'
```

**Explanation:** Output paths cannot contain `..` (security restriction).

**Solutions:**

1. **Use relative paths only**
   ```bash
   python generate.py --prompt "..." --output outputs/my_image.png  # ✓
   ```

2. **Do not use absolute paths**
   ```bash
   # ✗ Not allowed
   python generate.py --prompt "..." --output /etc/image.png
   
   # ✓ Allowed (relative)
   python generate.py --prompt "..." --output ./outputs/image.png
   ```

---

## Additional Help

- **Documentation:** See `docs/image-generation/`
- **Source code:** `generate.py` (well-commented, includes error handling)
- **Tests:** `tests/` (170+ tests show expected behavior)
- **Issue tracker:** [GitHub Issues](https://github.com/dfberry/image-generation/issues)

For reproducible bug reports, include:
```bash
python --version
python -c "import torch; print('torch:', torch.__version__)"
python -c "import diffusers; print('diffusers:', diffusers.__version__)"
nvidia-smi  # or equivalent GPU info
# Full command and error output
python generate.py --prompt "..." 2>&1
```
