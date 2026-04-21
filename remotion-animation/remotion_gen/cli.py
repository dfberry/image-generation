"""CLI entry point for remotion-gen."""

import argparse
import sys
from pathlib import Path

from remotion_gen.component_builder import write_component
from remotion_gen.config import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_PROVIDER,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    QUALITY_PRESETS,
)
from remotion_gen.errors import LLMError, RemotionGenError, RenderError, ValidationError
from remotion_gen.llm_client import generate_component
from remotion_gen.renderer import render_video


def generate_video(
    prompt: str,
    output: str,
    quality: str = "medium",
    duration: int = DEFAULT_DURATION_SECONDS,
    provider: str = DEFAULT_PROVIDER,
    model: str = None,
    debug: bool = False,
) -> Path:
    """Generate video from prompt.

    Args:
        prompt: Animation description
        output: Output video path
        quality: Quality preset (low/medium/high)
        duration: Video duration in seconds
        provider: LLM provider ("ollama", "openai", or "azure")
        model: Optional model name override
        debug: Save intermediate component code

    Returns:
        Path to generated video

    Raises:
        RemotionGenError: If generation fails
    """
    # Resolve paths
    repo_root = Path(__file__).parent.parent
    project_root = repo_root / "remotion-project"
    output_path = Path(output).resolve()

    if not project_root.exists():
        raise RemotionGenError(f"Remotion project not found: {project_root}")

    # Get quality preset
    preset = QUALITY_PRESETS[quality]
    duration_frames = duration * preset.fps

    print(
        f"Generating {duration}s video at "
        f"{preset.resolution_name} {preset.fps}fps..."
    )

    # Step 1: Generate component with LLM
    print(f"→ Calling {provider} LLM to generate component...")
    try:
        component_code = generate_component(
            prompt, duration, preset.fps, provider=provider, model=model
        )
    except LLMError as e:
        print(f"✗ LLM generation failed: {e}", file=sys.stderr)
        raise

    # Step 2: Write component to project
    print("→ Writing component to Remotion project...")
    try:
        write_component(component_code, project_root, debug)
        if debug:
            debug_path = repo_root / "outputs" / "GeneratedScene.debug.tsx"
            print(f"  Debug: Component saved to {debug_path}")
    except ValidationError as e:
        print(f"✗ Component validation failed: {e}", file=sys.stderr)
        raise

    # Step 3: Render video
    print("→ Rendering video with Remotion...")
    try:
        result_path = render_video(project_root, output_path, preset, duration_frames)
    except RenderError as e:
        print(f"✗ Rendering failed: {e}", file=sys.stderr)
        raise

    print(f"✓ Video generated: {result_path}")
    return result_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate animated videos from text prompts using Remotion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  remotion-gen --prompt "A blue circle rotating 360 degrees" --output circle.mp4
  remotion-gen --prompt "Text fading in and out" \
    --quality high --duration 10 --output fade.mp4
  remotion-gen --prompt "Multiple shapes bouncing" --debug --output bounce.mp4
  remotion-gen --prompt "Sine wave" --provider openai --output sine.mp4

Environment variables:
  OLLAMA_HOST                 Ollama endpoint (default: http://localhost:11434)
  OPENAI_API_KEY              OpenAI API key (for --provider openai)
  AZURE_OPENAI_KEY            Azure OpenAI API key (for --provider azure)
  AZURE_OPENAI_ENDPOINT       Azure OpenAI endpoint URL
  AZURE_OPENAI_DEPLOYMENT     Azure OpenAI deployment name
        """,
    )

    parser.add_argument(
        "--prompt",
        required=True,
        help="Animation description (what you want to see)",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output video path (e.g., video.mp4)",
    )

    parser.add_argument(
        "--quality",
        choices=["low", "medium", "high"],
        default="medium",
        help="Video quality: low (480p 15fps), medium (720p 30fps), high (1080p 60fps)",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=DEFAULT_DURATION_SECONDS,
        help=(
            f"Video duration in seconds"
            f" ({MIN_DURATION_SECONDS}-{MAX_DURATION_SECONDS})"
        ),
    )

    parser.add_argument(
        "--provider",
        type=str,
        choices=["ollama", "openai", "azure"],
        default=DEFAULT_PROVIDER,
        help="LLM provider (default: ollama for local inference)",
    )

    parser.add_argument(
        "--model",
        type=str,
        help=(
            "Override default LLM model"
            " (default: llama3 for Ollama, gpt-4 for OpenAI)"
        ),
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save intermediate component code to outputs/ for inspection",
    )

    args = parser.parse_args()

    # Validate duration
    if args.duration < MIN_DURATION_SECONDS or args.duration > MAX_DURATION_SECONDS:
        parser.error(
            (
            f"Duration must be between {MIN_DURATION_SECONDS}"
            f" and {MAX_DURATION_SECONDS} seconds"
        )
        )

    try:
        generate_video(
            prompt=args.prompt,
            output=args.output,
            quality=args.quality,
            duration=args.duration,
            provider=args.provider,
            model=args.model,
            debug=args.debug,
        )
        return 0
    except RemotionGenError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
