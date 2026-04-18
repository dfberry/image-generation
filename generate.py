#!/usr/bin/env python3
"""
Stable Diffusion XL image generation script.
Uses SDXL Base 1.0 with optional refiner for high-quality output.

Model: stabilityai/stable-diffusion-xl-base-1.0
License: CreativeML Open RAIL++-M
"""

import argparse
import gc
import json
import os
import sys
from datetime import datetime
from types import SimpleNamespace

import diffusers
import torch
from diffusers import DiffusionPipeline


class OOMError(RuntimeError):
    """Raised when GPU/MPS runs out of memory during generation."""
    pass


def _positive_int(value):
    """Argparse type: positive integer (> 0)."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {value}")
    return ivalue


def _non_negative_float(value):
    """Argparse type: non-negative float (>= 0)."""
    fvalue = float(value)
    if fvalue < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return fvalue


def _dimension(value):
    """Argparse type: image dimension in pixels (>= 64, divisible by 8)."""
    ivalue = int(value)
    if ivalue < 64:
        raise argparse.ArgumentTypeError(f"must be >= 64, got {value}")
    if ivalue % 8 != 0:
        nearest = ((ivalue + 7) // 8) * 8
        raise argparse.ArgumentTypeError(
            f"must be divisible by 8, got {value} (nearest valid: {nearest})"
        )
    return ivalue


def validate_dimensions(width: int, height: int):
    """Runtime guard: width and height must be divisible by 8."""
    for name, val in [("width", width), ("height", height)]:
        if val % 8 != 0:
            nearest = ((val + 7) // 8) * 8
            raise ValueError(
                f"{name} must be divisible by 8, got {val} (nearest valid: {nearest})"
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate images with Stable Diffusion XL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Text prompt for image generation")
    group.add_argument("--batch-file", dest="batch_file", metavar="PATH",
                       help="JSON file with list of prompt dicts for batch generation")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--steps", type=_positive_int, default=22, help="Number of base inference steps (> 0)")
    parser.add_argument("--refiner-steps", type=_positive_int, default=10, dest="refiner_steps",
                        help="Number of refiner inference steps (> 0)")
    parser.add_argument("--guidance", type=_non_negative_float, default=6.5, help="Guidance scale (>= 0)")
    parser.add_argument("--refiner-guidance", type=_non_negative_float, default=5.0, dest="refiner_guidance",
                        help="Guidance scale for refiner (independent from base)")
    parser.add_argument("--scheduler", type=str, default="DPMSolverMultistepScheduler",
                        help="Scheduler class name from diffusers")
    parser.add_argument("--width", type=_dimension, default=1024, help="Image width in pixels (>= 64)")
    parser.add_argument("--height", type=_dimension, default=1024, help="Image height in pixels (>= 64)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument(
        "--negative-prompt",
        default="blurry, bad quality, worst quality, low resolution, text, watermark, signature, deformed, ugly, duplicate, morbid",
        help="Negative prompt to steer generation away from undesired features",
    )
    parser.add_argument("--refine", action="store_true", help="Use base + refiner pipeline (higher quality)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode (slow, no GPU required)")
    parser.add_argument("--lora", type=str, default=None,
                        help="LoRA model ID or path to load (e.g. joachim_s/aether-watercolor-and-ink-sdxl)")
    parser.add_argument("--lora-weight", type=_non_negative_float, default=0.8, dest="lora_weight",
                        help="LoRA adapter weight (0.0–1.0)")
    return parser.parse_args()


def get_device(force_cpu: bool) -> str:
    """Detect best available device."""
    if force_cpu:
        return "cpu"
    if torch.cuda.is_available():
        print("✅ CUDA GPU detected")
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print("✅ Apple Silicon (MPS) detected")
        return "mps"
    print("⚠️  No GPU detected — falling back to CPU (slow)")
    return "cpu"


def get_dtype(device: str):
    """Float16 on GPU, float32 on CPU."""
    return torch.float16 if device in ("cuda", "mps") else torch.float32


def _apply_performance_opts(pipe, device: str):
    """Apply torch.compile and memory-efficient attention optimizations."""
    # torch.compile gives ~1.5-2× speedup on CUDA with torch >= 2.0
    if device == "cuda" and hasattr(torch, "compile"):
        print("⚡ Compiling UNet with torch.compile (one-time, ~30s)...")
        pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)

    # Memory-efficient attention: prefer xFormers, fall back to attention slicing
    if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pipe.enable_attention_slicing()
    else:
        pipe.enable_attention_slicing()


def load_base(device: str) -> DiffusionPipeline:
    """Load SDXL base model."""
    print("📥 Loading SDXL base model (first run downloads ~7GB)...")
    dtype = get_dtype(device)
    pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device in ("cuda", "mps") else None,
    )
    pipe.safety_checker = None

    if device == "mps":
        pipe.enable_model_cpu_offload()
    elif device == "cpu":
        pipe.to("cpu")
    else:
        pipe.to(device)

    _apply_performance_opts(pipe, device)
    return pipe


def load_refiner(text_encoder_2, vae, device: str) -> DiffusionPipeline:
    """Load SDXL refiner, sharing text encoder and VAE from base."""
    print("📥 Loading SDXL refiner model...")
    dtype = get_dtype(device)
    refiner = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-refiner-1.0",
        text_encoder_2=text_encoder_2,
        vae=vae,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device in ("cuda", "mps") else None,
    )
    refiner.safety_checker = None

    if device == "mps":
        refiner.enable_model_cpu_offload()
    elif device == "cpu":
        refiner.to("cpu")
    else:
        refiner.to(device)

    _apply_performance_opts(refiner, device)
    return refiner


SUPPORTED_SCHEDULERS = [
    "DPMSolverMultistepScheduler",
    "EulerDiscreteScheduler",
    "EulerAncestralDiscreteScheduler",
    "DDIMScheduler",
    "LMSDiscreteScheduler",
    "PNDMScheduler",
    "UniPCMultistepScheduler",
    "HeunDiscreteScheduler",
    "KDPM2DiscreteScheduler",
    "DEISMultistepScheduler",
]


def apply_scheduler(pipeline, scheduler_name: str):
    """Override the pipeline's scheduler by name, using its existing config."""
    if not hasattr(diffusers, scheduler_name):
        raise ValueError(
            f"Unknown scheduler: {scheduler_name}. "
            f"Available: {', '.join(SUPPORTED_SCHEDULERS)}"
        )
    scheduler_cls = getattr(diffusers, scheduler_name)
    config = getattr(pipeline.scheduler, 'config', {})
    if not isinstance(config, dict):
        config = {}
    # Karras sigmas improve quality with DPM++ solvers
    if scheduler_name == "DPMSolverMultistepScheduler":
        config["use_karras_sigmas"] = True
    pipeline.scheduler = scheduler_cls.from_config(config)


def apply_lora(pipeline, lora: str | None, lora_weight: float = 0.8):
    """Load LoRA weights into the pipeline if specified."""
    if lora is None:
        return
    print(f"🎨 Loading LoRA: {lora} (weight={lora_weight})")
    pipeline.load_lora_weights(lora)
    pipeline.set_adapters(["default"], adapter_weights=[lora_weight])


def generate(args) -> str:
    """Run image generation and save to output path."""
    validate_dimensions(args.width, args.height)
    device = get_device(args.cpu)

    # Fix 3: Pre-flight flush — reclaim any GPU memory from a prior generate()
    # call before loading new pipelines. Reduces OOM risk in back-to-back runs.
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

    # Set up generator for reproducible output
    generator = None
    if args.seed is not None:
        # Fix C: cpu_offload routes layers to CPU for "cpu"/"mps" devices,
        # so bind the generator to CPU to avoid a device mismatch.
        generator_device = "cpu" if device in ("cpu", "mps") else device
        generator = torch.Generator(device=generator_device).manual_seed(args.seed)
        print(f"🌱 Seed: {args.seed}")

    # Resolve output path
    output_path = args.output
    if output_path is None:
        os.makedirs("outputs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"outputs/image_{timestamp}.png"

    # Base+refiner split: 80% of steps on base, 20% on refiner
    high_noise_frac = 0.8

    base = refiner = latents = text_encoder_2 = vae = image = None
    try:
        if args.refine:
            print(f"🎨 Running base + refiner pipeline ({args.steps} steps total)...")
            base = load_base(device)

            # Apply chosen scheduler to base pipeline
            apply_scheduler(base, args.scheduler)
            apply_lora(base, getattr(args, 'lora', None), getattr(args, 'lora_weight', 0.8))

            # Stage 1: base model produces latents
            latents = base(
                prompt=args.prompt,
                negative_prompt=args.negative_prompt,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                width=args.width,
                height=args.height,
                denoising_end=high_noise_frac,
                output_type="latent",
                generator=generator,
            ).images

            # Extract shared components before freeing base from GPU
            text_encoder_2 = base.text_encoder_2
            vae = base.vae

            # Fix 1: Move latents to CPU before the cache flush window so that
            # the GPU-resident tensor doesn't pin VRAM while empty_cache() runs.
            if device in ("cuda", "mps"):
                latents = latents.cpu()

            del base
            base = None
            if device == "mps":
                torch.mps.empty_cache()
            if device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

            refiner = load_refiner(text_encoder_2, vae, device)
            image = refiner(
                prompt=args.prompt,
                negative_prompt=args.negative_prompt,
                num_inference_steps=getattr(args, 'refiner_steps', 10),
                guidance_scale=args.refiner_guidance,
                denoising_start=high_noise_frac,
                # Move latents back to device for refiner inference.
                image=latents.to(device) if device in ("cuda", "mps") else latents,
                generator=generator,
            ).images[0]
        else:
            print(f"🎨 Running base model ({args.steps} steps)...")
            base = load_base(device)

            # Apply chosen scheduler to base pipeline
            apply_scheduler(base, args.scheduler)
            apply_lora(base, getattr(args, 'lora', None), getattr(args, 'lora_weight', 0.8))

            image = base(
                prompt=args.prompt,
                negative_prompt=args.negative_prompt,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                width=args.width,
                height=args.height,
                generator=generator,
            ).images[0]

        if image is not None:
            image.save(output_path)
            print(f"✅ Saved: {output_path}")
    except Exception as exc:
        _is_cuda_oom = (
            hasattr(torch.cuda, "OutOfMemoryError")
            and isinstance(exc, torch.cuda.OutOfMemoryError)
        )
        _is_mps_oom = isinstance(exc, RuntimeError) and "out of memory" in str(exc).lower()
        if _is_cuda_oom or _is_mps_oom:
            raise OOMError(
                "Out of GPU memory. Reduce steps with --steps or switch to CPU with --cpu."
            ) from exc
        raise
    finally:
        # Unconditional cleanup — runs on success, OOM, interrupt, or any exception.
        # base may already be None (freed mid-refine path) but del is safe on None.
        del base, refiner, latents, text_encoder_2, vae
        image = None
        gc.collect()
        torch.cuda.empty_cache()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        # Fix 2: torch.compile (used on CUDA in load_base) populates a process-global
        # dynamo cache that survives del base. Reset it to prevent accumulation across
        # repeated generate() calls. If torch.compile is added for other devices later,
        # broaden this guard accordingly.
        if device == "cuda" and hasattr(torch, "_dynamo"):
            torch._dynamo.reset()

    return output_path


def batch_generate(prompts: list[dict], device: str = "mps", args=None) -> list[dict]:
    """
    Generate images for a list of prompt dicts, flushing GPU memory between items.

    Each input dict: {"prompt": str, "output": str, "seed": int (optional)}
    Returns list of {"prompt": str, "output": str, "status": "ok"|"error", "error": str|None}

    When args is provided, CLI params (steps, guidance, width, height, refine,
    negative_prompt) are forwarded from it instead of using defaults.
    """
    results = []
    for i, item in enumerate(prompts):
        batch_args = SimpleNamespace(
            prompt=item["prompt"],
            output=item["output"],
            seed=item.get("seed"),
            steps=args.steps if args else 22,
            guidance=args.guidance if args else 6.5,
            refiner_guidance=args.refiner_guidance if args else 5.0,
            scheduler=args.scheduler if args else "DPMSolverMultistepScheduler",
            width=args.width if args else 1024,
            height=args.height if args else 1024,
            refine=args.refine if args else False,
            negative_prompt=item.get("negative_prompt", args.negative_prompt if args else ""),
            cpu=(device == "cpu"),
            lora=item.get("lora", getattr(args, 'lora', None)),
            lora_weight=item.get("lora_weight", getattr(args, 'lora_weight', 0.8)),
            refiner_steps=getattr(args, 'refiner_steps', 10),
        )
        try:
            output_path = generate_with_retry(batch_args)
            results.append({
                "prompt": item["prompt"],
                "output": output_path,
                "status": "ok",
                "error": None,
            })
        except Exception as exc:
            results.append({
                "prompt": item["prompt"],
                "output": item["output"],
                "status": "error",
                "error": str(exc),
            })

        # Flush GPU memory between items (not needed after the last item)
        if i < len(prompts) - 1:
            gc.collect()
            torch.cuda.empty_cache()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

    return results


def generate_with_retry(args, max_retries: int = 2) -> str:
    """
    Wraps generate(args) with OOM retry logic.
    - On OOMError: halves steps (floor at 1), prints warning, retries
    - Retries up to max_retries times (so up to max_retries+1 total calls)
    - If all retries exhausted: raises OOMError with message mentioning final steps count
    - Non-OOM exceptions: re-raised immediately, no retry
    - Does NOT mutate args.steps — uses a local copy for each attempt.
    """
    current_steps = args.steps
    for attempt in range(max_retries + 1):
        try:
            retry_args = SimpleNamespace(**vars(args))
            retry_args.steps = current_steps
            return generate(retry_args)
        except OOMError:
            if attempt == max_retries:
                raise OOMError(
                    f"Out of GPU memory after {max_retries} retries. Last attempt used {current_steps} steps."
                )
            current_steps = max(1, current_steps // 2)
            print(f"OOM: retrying with {current_steps} steps")


def main():
    args = parse_args()
    if hasattr(args, 'batch_file') and args.batch_file:
        try:
            with open(args.batch_file) as f:
                prompts = json.load(f)
        except FileNotFoundError:
            print(f"Error: batch file not found: {args.batch_file}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in batch file: {e}", file=sys.stderr)
            sys.exit(1)
        device = "cpu" if args.cpu else get_device(False)
        results = batch_generate(prompts, device=device, args=args)
        for r in results:
            status = r['status']
            print(f"[{status}] {r['prompt'][:50]} → {r.get('output', r.get('error', ''))}")
    else:
        generate_with_retry(args)


if __name__ == "__main__":
    main()
