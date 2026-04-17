SDXL PERFORMANCE OPTIMIZATION (DIFFUSERS)

This document focuses on speeding up Stable Diffusion XL generation while preserving high image quality.
It assumes a Python + diffusers stack (no A1111 / no ComfyUI).

============================================================
1. WHY GENERATION IS SLOW
============================================================

Common causes of 10-minute SDXL generations:
- Default scheduler (DDIM / Euler)
- Excessive inference steps
- No PyTorch 2.x compilation
- No memory-efficient attention
- Base + Refiner both oversampled
- Safety checker enabled

SDXL is designed to be run with optimizations enabled.
A naive pipeline leaves significant performance untapped.

============================================================
2. BIGGEST SPEED WINS (DO THESE FIRST)
============================================================

------------------------------------------------------------
2.1 Use a Faster Scheduler (3–5× speedup)
------------------------------------------------------------

Replace the default scheduler with DPM++ (Karras sigmas):

from diffusers import DPMSolverMultistepScheduler

base.scheduler = DPMSolverMultistepScheduler.from_config(
    base.scheduler.config,
    use_karras_sigmas=True
)

refiner.scheduler = DPMSolverMultistepScheduler.from_config(
    refiner.scheduler.config,
    use_karras_sigmas=True
)

------------------------------------------------------------
2.2 Reduce Inference Steps (no quality loss)
------------------------------------------------------------

Recommended SDXL ranges for illustrative styles:

Base model:
- Old: 40–50 steps
- New: 20–24 steps

Refiner:
- Old: 20–30 steps
- New: 8–12 steps

Example:
num_inference_steps=22  # base
num_inference_steps=10  # refiner

Watercolor + ink styles do NOT benefit from high step counts.
Extra steps often add muddy noise instead of clarity.

------------------------------------------------------------
2.3 Enable PyTorch 2.x Compilation (1.5–2× speedup)
------------------------------------------------------------

Available because torch >= 2.1.0

base.unet = torch.compile(base.unet, mode="reduce-overhead")
refiner.unet = torch.compile(refiner.unet, mode="reduce-overhead")

NOTE:
- First run is slower (compile cost)
- Subsequent runs are significantly faster

------------------------------------------------------------
2.4 Enable Memory-Efficient Attention
------------------------------------------------------------

If xFormers is installed:

base.enable_xformers_memory_efficient_attention()
refiner.enable_xformers_memory_efficient_attention()

If not available, still enable slicing:

base.enable_attention_slicing()
refiner.enable_attention_slicing()

============================================================
3. EASY WINS (DON’T SKIP)
============================================================

------------------------------------------------------------
3.1 Disable Safety Checker
------------------------------------------------------------

Not needed for local generation:

base.safety_checker = None
refiner.safety_checker = None

------------------------------------------------------------
3.2 Avoid CPU Offload
------------------------------------------------------------

DO NOT enable:
- enable_model_cpu_offload()

CPU/GPU swaps drastically slow SDXL.
Keep everything on GPU.

------------------------------------------------------------
3.3 Always Pass LATENTS to Refiner
------------------------------------------------------------

Correct:
output_type="latent"

Incorrect:
- Decoding to image, then re-encoding

Latent handoff saves time and preserves detail.

============================================================
4. RECOMMENDED FAST + HIGH-QUALITY CONFIGURATION
============================================================

This configuration typically reduces generation time
from ~10 minutes to ~60–90 seconds on a modern GPU.

from diffusers import DPMSolverMultistepScheduler

base.scheduler = DPMSolverMultistepScheduler.from_config(
    base.scheduler.config,
    use_karras_sigmas=True
)
refiner.scheduler = DPMSolverMultistepScheduler.from_config(
    refiner.scheduler.config,
    use_karras_sigmas=True
)

base.unet = torch.compile(base.unet, mode="reduce-overhead")
refiner.unet = torch.compile(refiner.unet, mode="reduce-overhead")

base.enable_xformers_memory_efficient_attention()
refiner.enable_xformers_memory_efficient_attention()

base.safety_checker = None
refiner.safety_checker = None

# Base generation
image_latents = base(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=1200,
    height=630,
    num_inference_steps=22,
    guidance_scale=6.5,
    output_type="latent",
).images

# Refiner pass
final_image = refiner(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=10,
    guidance_scale=6.5,
    image=image_latents,
).images[0]

============================================================
5. OPTIONAL: EXTREME SPEED MODES
============================================================

------------------------------------------------------------
5.1 SDXL Lightning / Turbo Models
------------------------------------------------------------

Characteristics:
- 3–6 steps total
- Near-instant generation (5–15 seconds)
- ~90–95% quality for illustration styles

Best used for:
- Rapid iteration
- Concept exploration

Later switch back to full SDXL for final hero renders.

------------------------------------------------------------
5.2 ControlNet Without Killing Performance
------------------------------------------------------------

If using ControlNet scribble:
- Use scribble only (not depth)
- Control strength: 0.6–0.75
- Fewer base steps (20 range)

ControlNet mainly influences early denoising steps.

============================================================
6. REALISTIC PERFORMANCE EXPECTATIONS
============================================================

Approximate times (modern GPU):

- Naive SDXL: ~10 minutes
- Optimized scheduler + steps: 2–3 minutes
- + torch.compile: ~60–90 seconds
- Lightning models: 5–15 seconds

============================================================
7. KEY TAKEAWAYS
============================================================

- SDXL expects scheduler + step tuning
- High steps do not equal high quality
- PyTorch 2.x compilation is a major unlock
- Separate fast iteration from final render passes

============================================================
END OF FILE
