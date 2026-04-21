#!/usr/bin/env python3
"""Manim Animation Generator CLI"""

import argparse
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from manim_gen.config import Config, QualityPreset
from manim_gen.errors import (
    ImageValidationError,
    LLMError,
    RenderError,
    ValidationError,
)
from manim_gen.image_handler import copy_images_to_workspace, generate_image_context
from manim_gen.llm_client import LLMClient
from manim_gen.renderer import render_scene
from manim_gen.scene_builder import build_scene

logger = logging.getLogger(__name__)

def setup_logging(debug: bool = False) -> None:
    """Configure logging"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate animated videos using AI and Manim",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  manim-gen --prompt "A blue circle morphs into a red square" --output circle.mp4
  manim-gen --prompt "Pythagorean theorem visualization" --quality high --duration 15
  manim-gen --prompt "Show sine wave animation" --debug --provider azure

Environment variables:
  OPENAI_API_KEY              OpenAI API key (for --provider openai)
  AZURE_OPENAI_KEY            Azure OpenAI API key (for --provider azure)
  AZURE_OPENAI_ENDPOINT       Azure OpenAI endpoint URL
  AZURE_OPENAI_DEPLOYMENT     Azure OpenAI deployment name
        """,
    )

    parser.add_argument(
        "--prompt",
        required=True,
        help="Description of the animation to generate",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output video path (default: outputs/video_YYYYMMDD_HHMMSS.mp4)",
    )

    parser.add_argument(
        "--quality",
        type=str,
        choices=["low", "medium", "high"],
        default="medium",
        help="Video quality preset (default: medium)",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Target duration in seconds (5-30, default: 10)",
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["ollama", "openai", "azure"],
        default="ollama",
        help="LLM provider (default: ollama for local inference)",
    )

    parser.add_argument(
        "--model",
        type=str,
        help="Override default LLM model (default: llama3 for Ollama, gpt-4 for OpenAI)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and save intermediate scene code",
    )

    # Image input arguments
    parser.add_argument(
        "--image",
        type=Path,
        nargs="*",
        help="Image file(s) to include in the animation",
    )

    parser.add_argument(
        "--image-descriptions",
        type=str,
        help="Descriptions of the images for LLM context",
    )

    parser.add_argument(
        "--image-policy",
        type=str,
        choices=["strict", "warn", "ignore"],
        default="strict",
        help="Image validation policy (default: strict)",
    )

    return parser.parse_args()

def generate_video(
    prompt: str,
    output: Path,
    quality: QualityPreset,
    duration: int,
    provider: str = "openai",
    model: str = None,
    debug: bool = False,
    images: Optional[List[Path]] = None,
    image_descriptions: Optional[str] = None,
    image_policy: str = "strict",
) -> Path:
    """Main video generation pipeline

    Args:
        prompt: User's animation description
        output: Output video path
        quality: Quality preset
        duration: Target duration in seconds
        provider: LLM provider ("ollama", "openai", or "azure")
        model: Optional model override
        debug: Save intermediate files
        images: Optional list of image file paths to include
        image_descriptions: Optional descriptions for images
        image_policy: Image validation policy

    Returns:
        Path to generated video

    Raises:
        LLMError: If LLM call fails
        ValidationError: If generated code is invalid
        RenderError: If Manim render fails
        ImageValidationError: If image validation fails (strict mode)
    """
    logger.info(f"Starting video generation for prompt: {prompt}")

    image_context = None
    image_copies = {}

    # Step 1: Generate scene code via LLM
    logger.info(f"Calling {provider} LLM to generate scene code")
    client = LLMClient(provider=provider)

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Handle images if provided
        if images:
            logger.info(f"Processing {len(images)} image(s) with policy={image_policy}")
            image_copies = copy_images_to_workspace(images, workspace, image_policy)
            workspace_paths = list(image_copies.values())
            image_context = generate_image_context(
                workspace_paths, custom_descriptions=image_descriptions
            )
            logger.info(f"Copied {len(image_copies)} image(s) to workspace")

        llm_output = client.generate_scene_code(
            prompt, duration, model=model, image_context=image_context
        )

        # Step 2: Build and validate scene
        scene_file = workspace / "scene.py"
        logger.info("Building and validating scene")

        image_filenames = {p.name for p in image_copies.values()} if image_copies else None
        code, scene_path = build_scene(llm_output, scene_file, image_filenames)

        # Save debug copy if requested
        if debug:
            debug_path = output.parent / f"{output.stem}_scene.py"
            debug_path.write_text(code, encoding="utf-8")
            logger.info(f"Debug: Scene code saved to {debug_path}")

        # Step 3: Render with Manim
        logger.info("Rendering video with Manim")
        assets_dir = workspace if image_copies else None
        video_path = render_scene(scene_path, output, quality, assets_dir=assets_dir)

    logger.info(f"Video generation complete: {video_path}")
    return video_path

def main() -> int:
    """CLI entry point"""
    args = parse_args()
    setup_logging(args.debug)

    try:
        # Build config
        config = Config(
            quality=QualityPreset[args.quality.upper()],
            duration=args.duration,
            debug=args.debug,
            provider=args.provider,
        )

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.output_dir / f"video_{timestamp}.mp4"

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate video
        result = generate_video(
            prompt=args.prompt,
            output=output_path,
            quality=config.quality,
            duration=config.duration,
            provider=args.provider,
            model=args.model,
            debug=args.debug,
            images=args.image,
            image_descriptions=args.image_descriptions,
            image_policy=args.image_policy,
        )

        print(f"\n✓ Video generated successfully: {result}")
        print(f"  Quality: {config.quality.name} ({config.quality.height}p @ {config.quality.fps}fps)")
        print(f"  Duration: ~{config.duration}s")
        return 0

    except ImageValidationError as e:
        logger.error(f"Image validation error: {e}")
        print(f"\n✗ Image Error: {e}", file=sys.stderr)
        print("  Check image paths, formats, and sizes", file=sys.stderr)
        return 5

    except LLMError as e:
        logger.error(f"LLM error: {e}")
        print(f"\n✗ LLM Error: {e}", file=sys.stderr)
        print("  Check API credentials and network connection", file=sys.stderr)
        return 1

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        print(f"\n✗ Validation Error: {e}", file=sys.stderr)
        print("  Generated code failed safety/syntax checks", file=sys.stderr)
        return 2

    except RenderError as e:
        logger.error(f"Render error: {e}")
        print(f"\n✗ Render Error: {e}", file=sys.stderr)
        print("  Check that Manim and FFmpeg are installed correctly", file=sys.stderr)
        return 3

    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n✗ Unexpected Error: {e}", file=sys.stderr)
        return 4

if __name__ == "__main__":
    sys.exit(main())
