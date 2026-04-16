SDXL TEXT-TO-IMAGE SETUP (DIFFUSERS)

This document contains a complete, reproducible setup for generating a pen-and-ink + watercolor illustration using Stable Diffusion XL with diffusers.

============================================================
1. PYTHON DEPENDENCIES
============================================================

Required versions (known working):

- diffusers >= 0.21.0
- transformers >= 4.30.0
- accelerate >= 0.24.0
- safetensors >= 0.3.0
- invisible-watermark >= 0.2.0
- torch >= 2.1.0
- Pillow >= 10.0.0

============================================================
2. MODELS (RECOMMENDED)
============================================================

Base model:
- stabilityai/stable-diffusion-xl-base-1.0

Refiner (strongly recommended):
- stabilityai/stable-diffusion-xl-refiner-1.0

Optional style LoRA (watercolor + ink):
- Aether Watercolor & Ink (SDXL LoRA)
  Trigger words: "watercolor ink sketch"
  Suggested weight: 0.7–0.9

Optional composition control:
- xinsir/controlnet-scribble-sdxl-1.0

============================================================
3. PROMPT (LAYOUT-FIRST, SDXL FRIENDLY)
============================================================

POSITIVE PROMPT:

Two lighthouses at dusk, wide landscape view of Bellingham Bay.
Left lighthouse on the left shore in the foreground, tall and prominent,
shining a wide, scattered lighthouse beam across the water.
Right lighthouse on the right shore in the distance, smaller in scale,
shining a narrow, focused beam.
The two beams aim toward each other but do not touch,
leaving a visible gap of dark water between them.

Pacific Northwest shoreline with evergreen tree silhouettes on both sides.
Calm bay water, low dusk sky.

Pen and ink line art with a light watercolor wash on white paper.
Clean ink outlines, minimal shading, airy negative space.
Limited color palette only: slate blue water and light beams,
warm sage green trees, charcoal black ink lines.
No text.


NEGATIVE PROMPT:

single lighthouse, extra lighthouse,
buildings, houses, city skyline,
boats, people,
text, letters, signage,
monochrome, grayscale, black and white,
photorealistic, digital painting, oil painting,
thick brush strokes, heavy paint, high saturation

============================================================
4. DIFFUSERS CODE: BASE + REFINER
============================================================

import torch
from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLRefinerPipeline
)

# Device

device = "cuda"

# Load base pipeline
base = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16",
).to(device)

# OPTIONAL: load watercolor / ink LoRA
# base.load_lora_weights("joachim_s/aether-watercolor-and-ink-sdxl", weight=0.8)

# Load refiner pipeline
refiner = StableDiffusionXLRefinerPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-refiner-1.0",
    torch_dtype=torch.float16,
    variant="fp16",
).to(device)

prompt = """
<Paste POSITIVE PROMPT here>
"""

negative_prompt = """
<Paste NEGATIVE PROMPT here>
"""

# Step 1: Base model (structure)
image_latents = base(
    prompt=prompt,
    negative_prompt=negative_prompt,
    width=1200,
    height=630,
    num_inference_steps=40,
    guidance_scale=6.5,
    output_type="latent",
).images

# Step 2: Refiner (detail + ink quality)
final_image = refiner(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=20,
    guidance_scale=6.5,
    image=image_latents,
).images[0]

final_image.save("bellingham-bay-two-lighthouses.png")

============================================================
5. OPTIONAL: CONTROLNET SCRIBBLE (COMPOSITION LOCK)
============================================================

Use this if SDXL collapses to a single lighthouse.
Provide a simple doodle with two towers and two beams.

from diffusers import ControlNetModel

controlnet = ControlNetModel.from_pretrained(
    "xinsir/controlnet-scribble-sdxl-1.0",
    torch_dtype=torch.float16,
).to(device)

base = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    controlnet=controlnet,
    torch_dtype=torch.float16,
    variant="fp16",
).to(device)

============================================================
6. TUNING NOTES
============================================================

- guidance_scale: 6–7 works best for layout + style balance
- Always include a negative prompt to prevent grayscale collapse
- Use Base for layout, Refiner for line quality
- Prefer explicit spatial language (left/right/foreground/distance)
- Avoid hex color codes; name colors instead

============================================================
END OF FILE
