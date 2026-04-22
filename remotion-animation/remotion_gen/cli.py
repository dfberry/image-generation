"""CLI entry point for remotion-gen."""

import argparse
import sys
from pathlib import Path

from remotion_gen.component_builder import write_component
from remotion_gen.config import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_MUSIC_VOLUME,
    DEFAULT_NARRATION_VOLUME,
    DEFAULT_PROVIDER,
    DEFAULT_TTS_PROVIDER,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    QUALITY_PRESETS,
)
from remotion_gen.errors import (
    AudioValidationError,
    ImageValidationError,
    LLMError,
    RemotionGenError,
    RenderError,
    TTSError,
    ValidationError,
)
from remotion_gen.audio_handler import (
    copy_audio_to_public,
    generate_audio_context,
)
from remotion_gen.image_handler import copy_image_to_public, generate_image_context
from remotion_gen.llm_client import generate_component
from remotion_gen.renderer import render_video
from remotion_gen.tts_providers import generate_narration


def generate_video(
    prompt: str,
    output: str,
    quality: str = "medium",
    duration: int = DEFAULT_DURATION_SECONDS,
    provider: str = DEFAULT_PROVIDER,
    model: str = None,
    debug: bool = False,
    image_path: str = None,
    image_description: str = None,
    image_policy: str = "strict",
    component_code: str = None,
    narration_text: str = None,
    narration_file: str = None,
    background_music: str = None,
    sound_effects: list[str] = None,
    tts_provider: str = DEFAULT_TTS_PROVIDER,
    voice: str = None,
    music_volume: float = DEFAULT_MUSIC_VOLUME,
    narration_volume: float = DEFAULT_NARRATION_VOLUME,
    audio_policy: str = "strict",
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
        image_path: Optional path to an image file to include
        image_description: Optional description of the image for LLM context
        image_policy: Image validation policy ("strict", "warn", "ignore")
        component_code: Pre-built TSX code (skips LLM generation when set)
        narration_text: Inline text for TTS narration
        narration_file: Text file containing narration
        background_music: MP3/WAV file for background music
        sound_effects: One or more SFX audio files
        tts_provider: TTS engine ("edge-tts" or "openai")
        voice: Voice name (e.g. "en-US-GuyNeural", "alloy")
        music_volume: Background music volume 0.0–1.0
        narration_volume: Narration volume 0.0–1.0
        audio_policy: Audio file validation policy ("strict", "warn", "ignore")

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

    if component_code is None:
        # Step 0: Handle image input
        image_context = None
        image_filename = None
        if image_path:
            print(f"→ Processing image: {image_path}")
            try:
                image_filename = copy_image_to_public(
                    image_path, project_root, image_policy
                )
                image_context = generate_image_context(
                    image_filename, image_description
                )
                print(f"  Image copied as: {image_filename}")
            except ImageValidationError as e:
                print(f"✗ Image validation failed: {e}", file=sys.stderr)
                raise

        # Step 0b: Handle audio input
        audio_context = None
        audio_filenames = []
        audio_files = {}

        # Handle narration (TTS or file)
        if narration_text or narration_file:
            print("→ Processing narration...")
            try:
                # Get narration text from file if needed
                if narration_file:
                    narration_path = Path(narration_file)
                    if not narration_path.exists():
                        raise AudioValidationError(
                            f"Narration file not found: {narration_file}"
                        )
                    narration_text = narration_path.read_text(encoding="utf-8")

                # Validate narration text (Morpheus P1 condition #1)
                if not narration_text or not narration_text.strip():
                    raise TTSError("Narration text cannot be empty or whitespace-only")

                # Generate TTS audio
                print(f"  Generating TTS with {tts_provider}...")
                narration_mp3 = generate_narration(
                    narration_text,
                    provider_name=tts_provider,
                    voice=voice,
                    output_dir=project_root / "public",
                )
                narration_filename = narration_mp3.name
                audio_files["narration"] = narration_filename
                audio_filenames.append(narration_filename)
                print(f"  Narration generated: {narration_filename}")
            except (AudioValidationError, TTSError) as e:
                print(f"✗ Narration processing failed: {e}", file=sys.stderr)
                raise

        # Handle background music
        if background_music:
            print(f"→ Processing background music: {background_music}")
            try:
                music_filename = copy_audio_to_public(
                    background_music, project_root, audio_policy, prefix="music"
                )
                audio_files["music"] = music_filename
                audio_filenames.append(music_filename)
                print(f"  Music copied as: {music_filename}")
            except AudioValidationError as e:
                print(f"✗ Music validation failed: {e}", file=sys.stderr)
                raise

        # Handle sound effects
        if sound_effects:
            print(f"→ Processing {len(sound_effects)} sound effect(s)...")
            try:
                for i, sfx_path in enumerate(sound_effects):
                    sfx_filename = copy_audio_to_public(
                        sfx_path, project_root, audio_policy, prefix=f"sfx_{i}"
                    )
                    audio_files[f"sfx_{i}"] = sfx_filename
                    audio_filenames.append(sfx_filename)
                    print(f"  SFX {i} copied as: {sfx_filename}")
            except AudioValidationError as e:
                print(f"✗ SFX validation failed: {e}", file=sys.stderr)
                raise

        # Generate audio context for LLM
        if audio_files:
            audio_context = generate_audio_context(
                audio_files, music_volume, narration_volume
            )

        # Step 1: Generate component with LLM
        print(f"→ Calling {provider} LLM to generate component...")
        try:
            component_code = generate_component(
                prompt,
                duration,
                preset.fps,
                provider=provider,
                model=model,
                image_context=image_context,
                audio_context=audio_context,
            )
        except LLMError as e:
            print(f"✗ LLM generation failed: {e}", file=sys.stderr)
            raise

        image_filename_for_write = image_filename
    else:
        image_filename_for_write = None
        audio_filenames = []

    # Step 2: Write component to project
    print("→ Writing component to Remotion project...")
    try:
        write_component(
            component_code,
            project_root,
            debug,
            image_filename=image_filename_for_write,
            audio_filenames=audio_filenames if audio_filenames else None,
        )
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
        required=False,
        default=None,
        help="Animation description (what you want to see)",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate a personalized demo title card (no --prompt needed, bypasses LLM)",
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

    parser.add_argument(
        "--image",
        type=str,
        help="Path to an image or screenshot to include in the animation",
    )

    parser.add_argument(
        "--image-description",
        type=str,
        help="Optional description of the image for better LLM context",
    )

    parser.add_argument(
        "--image-policy",
        type=str,
        choices=["strict", "warn", "ignore"],
        default="strict",
        help="Image validation policy (default: strict)",
    )

    # Audio flags
    parser.add_argument(
        "--narration-text",
        type=str,
        help="Inline text for TTS narration",
    )

    parser.add_argument(
        "--narration-file",
        type=str,
        help="Text file containing narration",
    )

    parser.add_argument(
        "--background-music",
        type=str,
        help="MP3/WAV file for background music",
    )

    parser.add_argument(
        "--sound-effects",
        type=str,
        nargs="+",
        help="One or more SFX audio files",
    )

    parser.add_argument(
        "--tts-provider",
        type=str,
        choices=["edge-tts", "openai"],
        default=DEFAULT_TTS_PROVIDER,
        help=f"TTS engine (default: {DEFAULT_TTS_PROVIDER})",
    )

    parser.add_argument(
        "--voice",
        type=str,
        help="Voice name (e.g. 'en-US-GuyNeural', 'alloy')",
    )

    parser.add_argument(
        "--music-volume",
        type=float,
        default=DEFAULT_MUSIC_VOLUME,
        help=f"Background music volume 0.0-1.0 (default: {DEFAULT_MUSIC_VOLUME})",
    )

    parser.add_argument(
        "--narration-volume",
        type=float,
        default=DEFAULT_NARRATION_VOLUME,
        help=f"Narration volume 0.0-1.0 (default: {DEFAULT_NARRATION_VOLUME})",
    )

    parser.add_argument(
        "--audio-policy",
        type=str,
        choices=["strict", "warn", "ignore"],
        default="strict",
        help="Audio file validation policy (default: strict)",
    )

    args = parser.parse_args()

    # Mutual exclusion: narration-text and narration-file
    if args.narration_text and args.narration_file:
        parser.error("--narration-text and --narration-file cannot both be set")

    # Volume range validation
    if not (0.0 <= args.music_volume <= 1.0):
        parser.error("--music-volume must be between 0.0 and 1.0")
    if not (0.0 <= args.narration_volume <= 1.0):
        parser.error("--narration-volume must be between 0.0 and 1.0")

    # Validate duration
    if args.duration < MIN_DURATION_SECONDS or args.duration > MAX_DURATION_SECONDS:
        parser.error(
            (
            f"Duration must be between {MIN_DURATION_SECONDS}"
            f" and {MAX_DURATION_SECONDS} seconds"
        )
        )

    # Handle --demo mode: bypass LLM with pre-built template
    if args.demo:
        from datetime import datetime  # noqa: I001

        from remotion_gen.demo_template import get_demo_component

        now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        demo_code = get_demo_component(now)

        print("🎬 Demo mode: writing pre-built title card (bypassing LLM)")
        try:
            generate_video(
                prompt="demo",
                output=args.output,
                quality=args.quality,
                duration=args.duration,
                debug=args.debug,
                component_code=demo_code,
            )
            return 0
        except RemotionGenError as e:
            print(f"\nError: {e}", file=sys.stderr)
            return 1

    if not args.prompt:
        print("✗ Error: --prompt is required (or use --demo)", file=sys.stderr)
        return 1

    try:
        generate_video(
            prompt=args.prompt,
            output=args.output,
            quality=args.quality,
            duration=args.duration,
            provider=args.provider,
            model=args.model,
            debug=args.debug,
            image_path=args.image,
            image_description=args.image_description,
            image_policy=args.image_policy,
            narration_text=args.narration_text,
            narration_file=args.narration_file,
            background_music=args.background_music,
            sound_effects=args.sound_effects,
            tts_provider=args.tts_provider,
            voice=args.voice,
            music_volume=args.music_volume,
            narration_volume=args.narration_volume,
            audio_policy=args.audio_policy,
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
