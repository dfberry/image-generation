"""CLI entry point for story-to-video."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import DEFAULT_MODEL, DEFAULT_PROVIDER, DEFAULT_QUALITY, DEFAULT_SCENE_DURATION, DEFAULT_TRANSITION
from .doctor import SystemDoctor
from .models import RunManifest, StoryPlan
from .playlist_builder import PlaylistBuilder
from .scene_planner import ScenePlanner
from .scene_renderer import SceneRendererOrchestrator
from .tool_locator import find_tool


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(__version__)
def cli(ctx):
    """Story-to-Video: Orchestrate AI video generation from text stories."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("--input", "-i", type=click.Path(exists=True), help="Input story text file")
@click.option("--prompt", "-p", help="Inline story prompt")
@click.option("--scenes", type=click.Path(exists=True), help="Pre-structured scenes JSON (skip LLM planning)")
@click.option("--output", "-o", help="Output video filename")
@click.option("--quality", type=click.Choice(["low", "medium", "high"]), default=DEFAULT_QUALITY)
@click.option("--scene-duration", type=int, default=DEFAULT_SCENE_DURATION)
@click.option("--transition", type=click.Choice(["none", "fade_to_black", "crossfade"]), default=DEFAULT_TRANSITION)
@click.option("--provider", type=click.Choice(["ollama", "openai", "azure"]), default=DEFAULT_PROVIDER)
@click.option("--model", default=DEFAULT_MODEL)
@click.option("--style", help="Visual style hint (auto/cinematic/minimal/etc)")
@click.option("--plan-only", is_flag=True, help="Only plan scenes, don't render")
@click.option("--dry-run", is_flag=True, help="Show what would happen without rendering")
@click.option("--continue-on-error", is_flag=True, help="Continue if a scene fails to render")
@click.option("--resume", type=click.Path(exists=True), help="Resume a failed run")
def render(
    input: Optional[str],
    prompt: Optional[str],
    scenes: Optional[str],
    output: Optional[str],
    quality: str,
    scene_duration: int,
    transition: str,
    provider: str,
    model: str,
    style: Optional[str],
    plan_only: bool,
    dry_run: bool,
    continue_on_error: bool,
    resume: Optional[str],
):
    """Render a story into a video."""
    
    # Validate inputs
    if not input and not prompt and not scenes and not resume:
        click.echo("Error: Provide --input, --prompt, --scenes, or --resume", err=True)
        sys.exit(1)
    
    # Create run directory
    if resume:
        run_dir = Path(resume)
        click.echo(f"📂 Resuming run: {run_dir}")
    else:
        run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        run_dir = Path(__file__).parent.parent / "outputs" / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"📂 Created run directory: {run_dir}")
    
    try:
        # Load or create story plan
        if scenes:
            click.echo(f"📖 Loading scenes from {scenes}")
            with open(scenes) as f:
                plan = StoryPlan(**json.load(f))
        elif resume:
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                click.echo("Error: No manifest.json in resume directory", err=True)
                sys.exit(1)
            with open(manifest_path) as f:
                manifest = RunManifest(**json.load(f))
            plan = manifest.plan
            # Track previously successful scenes
            completed_scenes = {r.scene_number for r in manifest.results if r.success}
            click.echo(f"📖 Loaded plan: {plan.total_scenes} scenes ({len(completed_scenes)} already complete)")
        else:
            # Get story text
            if input:
                story = Path(input).read_text(encoding="utf-8")
                story_source = input
            else:
                story = prompt
                story_source = "inline"
            
            if not story or not story.strip():
                click.echo("Error: Story text is empty", err=True)
                sys.exit(1)
            
            # Save story to run directory
            (run_dir / "story.txt").write_text(story)
            
            # Plan scenes
            click.echo("🎬 Planning scenes...")
            planner = ScenePlanner(provider=provider, model=model, scene_duration=scene_duration)
            plan = planner.plan_scenes(story, style_hint=style)
            
            # Save plan
            plan_path = run_dir / "scenes.json"
            with open(plan_path, "w") as f:
                json.dump(plan.model_dump(), f, indent=2)
            click.echo(f"✅ Planned {plan.total_scenes} scenes → {plan_path}")
            
            # Initialize manifest
            manifest = RunManifest(
                run_id=run_dir.name,
                created_at=datetime.now().isoformat(),
                story_source=story_source,
                plan=plan,
                status="planning",
            )
        
        if plan_only:
            click.echo("✅ Planning complete (--plan-only mode)")
            return
        
        if dry_run:
            click.echo("\n🎥 Dry run - scenes to render:")
            for scene in plan.scenes:
                click.echo(f"  Scene {scene.scene_number}: {scene.visual_style} - {scene.description}")
            return
        
        # Render scenes
        click.echo(f"\n🎥 Rendering {plan.total_scenes} scenes...")
        clips_dir = run_dir / "clips"
        clips_dir.mkdir(exist_ok=True)
        
        renderer = SceneRendererOrchestrator(
            output_dir=clips_dir,
            quality=quality,
            provider=provider,
            model=model,
        )
        
        # Check renderer availability
        availability = renderer.check_availability()
        click.echo("\nRenderer availability:")
        for renderer_name, (available, msg) in availability.items():
            status = "✅" if available else "❌"
            click.echo(f"  {status} {renderer_name}: {msg or 'OK'}")
        
        results = []
        for scene in plan.scenes:
            # Skip already-rendered scenes on resume
            if resume and scene.scene_number in completed_scenes:
                existing = next(r for r in manifest.results if r.scene_number == scene.scene_number)
                results.append(existing)
                click.echo(f"\n⏭️  Skipping scene {scene.scene_number}/{plan.total_scenes} (already rendered)")
                continue

            click.echo(f"\n▶️  Scene {scene.scene_number}/{plan.total_scenes}: {scene.visual_style}")
            click.echo(f"    {scene.description}")
            
            result = renderer.render_scene(scene)
            results.append(result)
            
            if result.success:
                click.echo(f"    ✅ Rendered → {result.clip_path}")
            else:
                click.echo(f"    ❌ Failed: {result.error}")
                if not continue_on_error:
                    click.echo("\n❌ Aborting due to render failure (use --continue-on-error to skip)")
                    sys.exit(1)
        
        # Update manifest (preserve original metadata on resume)
        if not resume:
            manifest = RunManifest(
                run_id=run_dir.name,
                created_at=datetime.now().isoformat(),
                story_source=input or scenes or "inline",
                plan=plan,
                results=results,
                status="rendering",
            )
        else:
            manifest.results = results
            manifest.status = "rendering"
        
        # Build playlist
        click.echo("\n📝 Building playlist...")
        playlist_path = run_dir / "playlist.yaml"
        PlaylistBuilder.build_playlist(results, playlist_path, transition, scenes=plan.scenes)
        click.echo(f"✅ Playlist → {playlist_path}")
        
        # Stitch video
        click.echo("\n🎬 Stitching final video...")
        final_output = run_dir / (output or "final.mp4")
        stitch_result = _stitch_video(playlist_path, final_output, quality, transition)
        
        if stitch_result:
            manifest.final_output = final_output
            manifest.status = "complete"
            click.echo(f"\n✨ Video complete: {final_output}")
        else:
            manifest.status = "failed"
            click.echo("\n❌ Video stitching failed")
        
        # Save manifest
        manifest_path = run_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest.model_dump(mode="json"), f, indent=2)
        
        click.echo(f"\n📊 Run manifest: {manifest_path}")
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _stitch_video(playlist_path: Path, output_path: Path, quality: str, transition: str) -> bool:
    """Call video-stitcher to create final video."""
    import subprocess
    
    cmd = find_tool("stitch-video", env_var="STITCH_VIDEO_PATH", sibling_path="video-stitcher")
    if not cmd:
        click.echo("❌ stitch-video not found", err=True)
        return False
    
    try:
        result = subprocess.run(
            [
                cmd,
                "--playlist", str(playlist_path),
                "--output", str(output_path),
                "--quality", quality,
                "--transition", transition,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        
        return result.returncode == 0 and output_path.exists()
    except Exception as e:
        click.echo(f"❌ Stitching error: {e}", err=True)
        return False


@cli.command()
def doctor():
    """Run preflight system checks."""
    checks = SystemDoctor.check_all()
    all_pass = SystemDoctor.print_report(checks)
    sys.exit(0 if all_pass else 1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
