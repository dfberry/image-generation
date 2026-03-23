#!/usr/bin/env python3
"""
Stable Diffusion XL image generation script.
Uses SDXL Base 1.0 with optional refiner for high-quality output.

Model: stabilityai/stable-diffusion-xl-base-1.0
License: CreativeML Open RAIL++-M
"""

import argparse
import gc
import os
from datetime import datetime

import torch
from diffusers import DiffusionPipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate images with Stable Diffusion XL",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--steps", type=int, default=40, help="Number of inference steps")
    parser.add_argument("--guidance", type=float, default=7.5, help="Guidance scale (CFG)")
    parser.add_argument("--width", type=int, default=1024, help="Image width in pixels")
    parser.add_argument("--height", type=int, default=1024, help="Image height in pixels")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--refine", action="store_true", help="Use base + refiner pipeline (higher quality)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode (slow, no GPU required)")
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


def load_base(device: str) -> DiffusionPipeline:
    """Load SDXL base model."""
    print("📥 Loading SDXL base model (first run downloads ~7GB)...")
    dtype = get_dtype(device)
    pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=dtype,
        use_safetensors=True,
        # fp16 variant available for CUDA and MPS
        variant="fp16" if device in ("cuda", "mps") else None,
    )
    if device in ("cpu", "mps"):
        # CPU offload reduces VRAM pressure; MPS benefits too
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(device)

    # torch.compile gives ~20-30% speedup on CUDA with torch >= 2.0
    if device == "cuda" and hasattr(torch, "compile"):
        print("⚡ Compiling UNet with torch.compile (one-time, ~30s)...")
        pipe.unet = torch.compile(pipe.unet, mode="reduce-overhead", fullgraph=True)

    return pipe


def load_refiner(text_encoder_2, vae, device: str) -> DiffusionPipeline:
    """Load SDXL refiner, sharing text encoder and VAE from base."""
    print("📥 Loading SDXL refiner model...")
    dtype = get_dtype(device)
    refiner = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-refiner-1.0",
        # Share components with base to save VRAM
        text_encoder_2=text_encoder_2,
        vae=vae,
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device in ("cuda", "mps") else None,
    )
    if device in ("cpu", "mps"):
        refiner.enable_model_cpu_offload()
    else:
        refiner.to(device)
    return refiner


def generate(args) -> str:
    """Run image generation and save to output path."""
    device = get_device(args.cpu)

    # Set up generator for reproducible output
    generator = None
    if args.seed is not None:
        generator = torch.Generator(device=device).manual_seed(args.seed)
        print(f"🌱 Seed: {args.seed}")

    # Resolve output path
    output_path = args.output
    if output_path is None:
        os.makedirs("outputs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"outputs/image_{timestamp}.png"

    # Base+refiner split: 80% of steps on base, 20% on refiner
    high_noise_frac = 0.8

    if args.refine:
        print(f"🎨 Running base + refiner pipeline ({args.steps} steps total)...")
        base = load_base(device)

        # Stage 1: base model produces latents
        latents = base(
            prompt=args.prompt,
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
        del base
        if device == "mps":
            torch.mps.empty_cache()
        gc.collect()

        # Stage 2: refiner polishes latents
        refiner = load_refiner(text_encoder_2, vae, device)
        image = refiner(
            prompt=args.prompt,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            denoising_start=high_noise_frac,
            image=latents,
            generator=generator,
        ).images[0]
        del latents, refiner
        if device == "mps":
            torch.mps.empty_cache()
        gc.collect()
    else:
        print(f"🎨 Running base model ({args.steps} steps)...")
        base = load_base(device)
        image = base(
            prompt=args.prompt,
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            width=args.width,
            height=args.height,
            generator=generator,
        ).images[0]
        del base
        if device == "mps":
            torch.mps.empty_cache()
        gc.collect()

    image.save(output_path)
    print(f"✅ Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    args = parse_args()
    generate(args)
