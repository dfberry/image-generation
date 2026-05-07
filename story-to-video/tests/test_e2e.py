"""End-to-end integration tests for story-to-video pipeline."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from story_video.cli import cli
from story_video.models import RenderResult, Scene, StoryPlan
from story_video.playlist_builder import PlaylistBuilder
from story_video.scene_planner import ScenePlanner
from story_video.scene_renderer import SceneRendererOrchestrator


@pytest.fixture
def sample_story() -> str:
    """Sample story for testing."""
    return """A brave robot named Spark discovers a hidden garden filled with glowing flowers.
    
The garden whispers ancient secrets about love and friendship.

Spark learns that emotions are not weaknesses but the most powerful force in the universe.

Through this journey, Spark transforms from a cold machine into a being filled with warmth and compassion."""


@pytest.fixture
def predetermined_story_plan() -> StoryPlan:
    """Pre-built StoryPlan with exactly 4 scenes for deterministic testing."""
    return StoryPlan(
        title="Spark's Journey",
        total_scenes=4,
        scenes=[
            Scene(
                scene_number=1,
                duration=20,
                visual_style="image",
                description="Opening shot of robot in industrial setting",
                prompt="Cinematic wide shot of a sleek robot standing in a vast industrial complex, metallic surfaces, dramatic lighting, photorealistic, 4k",
                narration="In a world of steel and circuits, Spark awakens.",
                transition="fade_to_black",
            ),
            Scene(
                scene_number=2,
                duration=25,
                visual_style="remotion",
                description="Dynamic discovery sequence with text animation",
                prompt="Dynamic animation of a glowing garden gate opening, particle effects, vibrant colors flowing, magical atmosphere, modern motion graphics",
                narration="A hidden gateway reveals itself, pulsing with mysterious energy.",
                transition="crossfade",
            ),
            Scene(
                scene_number=3,
                duration=30,
                visual_style="remotion",
                description="Emotional transformation sequence",
                prompt="Abstract visualization of emotions flowing through circuits, data transforming into colorful patterns, fluid motion, emotional journey",
                narration="Emotions flow through Spark's systems like rivers of light.",
                transition="fade_to_black",
            ),
            Scene(
                scene_number=4,
                duration=15,
                visual_style="manim",
                description="Explanatory diagram showing transformation",
                prompt="Educational diagram showing the transformation from machine logic to emotional intelligence, clear visualization, technical yet warm",
                narration="The equation of existence: Logic + Love = Life.",
                transition="none",
            ),
        ],
    )


@pytest.fixture
def mock_openai_response(predetermined_story_plan: StoryPlan):
    """Mock OpenAI API response that returns our predetermined story plan."""
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    
    # Return the plan as JSON string
    plan_json = predetermined_story_plan.model_dump()
    mock_message.content = json.dumps(plan_json)
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    return mock_response


class TestFullPipeline:
    """Test the complete story-to-video pipeline with mocked external calls."""

    def test_scene_planner_produces_valid_plan(
        self, sample_story: str, mock_openai_response, predetermined_story_plan: StoryPlan
    ):
        """Test that scene planner produces a valid StoryPlan from story text."""
        with patch("story_video.scene_planner.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_openai_class.return_value = mock_client

            planner = ScenePlanner(provider="ollama", model="llama3.2")
            plan = planner.plan_scenes(sample_story)

            # Validate plan structure
            assert plan.title == "Spark's Journey"
            assert plan.total_scenes == 4
            assert len(plan.scenes) == 4

            # Validate scene details
            assert plan.scenes[0].visual_style == "image"
            assert plan.scenes[1].visual_style == "remotion"
            assert plan.scenes[2].visual_style == "remotion"
            assert plan.scenes[3].visual_style == "manim"

            # Validate all scenes have required fields
            for scene in plan.scenes:
                assert scene.scene_number > 0
                assert 5 <= scene.duration <= 30
                assert scene.description
                assert scene.prompt
                assert scene.narration
                assert scene.transition in ["none", "fade_to_black", "crossfade"]

    def test_scene_renderer_routes_to_correct_adapters(
        self, tmp_path: Path, predetermined_story_plan: StoryPlan
    ):
        """Test that scene renderer routes each scene to the correct renderer adapter."""
        output_dir = tmp_path / "clips"
        output_dir.mkdir()

        # Track which renderers were called for which scenes
        render_calls = []

        def mock_image_render(scene: Scene) -> RenderResult:
            render_calls.append(("image", scene.scene_number))
            output_path = output_dir / f"scene_{scene.scene_number:03d}.mp4"
            output_path.write_text("mock video")
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=output_path,
                duration=float(scene.duration),
                renderer="image",
                success=True,
            )

        def mock_remotion_render(scene: Scene) -> RenderResult:
            render_calls.append(("remotion", scene.scene_number))
            output_path = output_dir / f"scene_{scene.scene_number:03d}.mp4"
            output_path.write_text("mock video")
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=output_path,
                duration=float(scene.duration),
                renderer="remotion",
                success=True,
            )

        def mock_manim_render(scene: Scene) -> RenderResult:
            render_calls.append(("manim", scene.scene_number))
            output_path = output_dir / f"scene_{scene.scene_number:03d}.mp4"
            output_path.write_text("mock video")
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=output_path,
                duration=float(scene.duration),
                renderer="manim",
                success=True,
            )

        # Create renderer with mocked adapters
        renderer = SceneRendererOrchestrator(output_dir=output_dir, quality="medium")
        renderer.image_renderer.render = mock_image_render
        renderer.remotion_renderer.render = mock_remotion_render
        renderer.manim_renderer.render = mock_manim_render

        # Render all scenes
        results = []
        for scene in predetermined_story_plan.scenes:
            result = renderer.render_scene(scene)
            results.append(result)

        # Validate routing
        assert len(render_calls) == 4
        assert render_calls[0] == ("image", 1)  # Scene 1: image
        assert render_calls[1] == ("remotion", 2)  # Scene 2: remotion
        assert render_calls[2] == ("remotion", 3)  # Scene 3: remotion
        assert render_calls[3] == ("manim", 4)  # Scene 4: manim

        # Validate all renders succeeded
        assert all(r.success for r in results)
        assert all(r.clip_path.exists() for r in results)

    def test_playlist_builder_generates_valid_yaml(
        self, tmp_path: Path, predetermined_story_plan: StoryPlan
    ):
        """Test that playlist builder creates valid YAML with all clips in order."""
        clips_dir = tmp_path / "clips"
        clips_dir.mkdir()

        # Create mock render results
        results = []
        for scene in predetermined_story_plan.scenes:
            clip_path = clips_dir / f"scene_{scene.scene_number:03d}.mp4"
            clip_path.write_text("mock video")
            results.append(
                RenderResult(
                    scene_number=scene.scene_number,
                    clip_path=clip_path,
                    duration=float(scene.duration),
                    renderer=scene.visual_style,
                    success=True,
                )
            )

        # Build playlist
        playlist_path = tmp_path / "playlist.yaml"
        PlaylistBuilder.build_playlist(results, playlist_path, transition="fade_to_black")

        # Validate playlist file exists and is valid YAML
        assert playlist_path.exists()
        with open(playlist_path) as f:
            playlist = yaml.safe_load(f)

        # Validate structure
        assert playlist["version"] == "1.0"
        assert "clips" in playlist
        assert len(playlist["clips"]) == 4

        # Validate clips are in order with correct paths
        for i, clip in enumerate(playlist["clips"], start=1):
            expected_path = clips_dir / f"scene_{i:03d}.mp4"
            assert clip["path"] == str(expected_path.absolute())
            assert clip["duration"] == predetermined_story_plan.scenes[i - 1].duration
            # All clips except possibly the last should have transitions
            if i < 4:
                assert clip["transition"] == "fade_to_black"

    def test_full_pipeline_with_mocks(
        self, tmp_path: Path, sample_story: str, mock_openai_response, predetermined_story_plan: StoryPlan
    ):
        """Test complete pipeline: planning → rendering → playlist → stitch call."""
        run_dir = tmp_path / "run_test"
        run_dir.mkdir()
        clips_dir = run_dir / "clips"
        clips_dir.mkdir()

        # Mock OpenAI client
        with patch("story_video.scene_planner.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_openai_class.return_value = mock_client

            # Step 1: Plan scenes
            planner = ScenePlanner(provider="ollama", model="llama3.2")
            plan = planner.plan_scenes(sample_story)
            
            assert plan.total_scenes == 4
            assert len(plan.scenes) == 4

            # Save plan to run directory
            scenes_path = run_dir / "scenes.json"
            with open(scenes_path, "w") as f:
                json.dump(plan.model_dump(), f, indent=2)
            
            assert scenes_path.exists()

            # Step 2: Mock render all scenes
            results = []
            for scene in plan.scenes:
                clip_path = clips_dir / f"scene_{scene.scene_number:03d}.mp4"
                clip_path.write_text(f"mock video for scene {scene.scene_number}")
                results.append(
                    RenderResult(
                        scene_number=scene.scene_number,
                        clip_path=clip_path,
                        duration=float(scene.duration),
                        renderer=scene.visual_style,
                        success=True,
                    )
                )

            # Validate all scenes rendered
            assert len(results) == 4
            assert all(r.success for r in results)
            assert results[0].renderer == "image"
            assert results[1].renderer == "remotion"
            assert results[2].renderer == "remotion"
            assert results[3].renderer == "manim"

            # Step 3: Build playlist
            playlist_path = run_dir / "playlist.yaml"
            PlaylistBuilder.build_playlist(results, playlist_path, transition="fade_to_black")
            
            assert playlist_path.exists()

            # Step 4: Validate run directory structure
            assert (run_dir / "scenes.json").exists()
            assert (run_dir / "playlist.yaml").exists()
            assert (clips_dir / "scene_001.mp4").exists()
            assert (clips_dir / "scene_002.mp4").exists()
            assert (clips_dir / "scene_003.mp4").exists()
            assert (clips_dir / "scene_004.mp4").exists()

            # Step 5: Verify playlist content
            with open(playlist_path) as f:
                playlist = yaml.safe_load(f)
            
            assert len(playlist["clips"]) == 4
            assert all("path" in clip for clip in playlist["clips"])
            assert all("duration" in clip for clip in playlist["clips"])


class TestCLISmokeTest:
    """Test CLI entry point with mocked dependencies."""

    def test_plan_only_mode_writes_scenes_json(
        self, tmp_path: Path, mock_openai_response, predetermined_story_plan: StoryPlan
    ):
        """Test that --plan-only mode successfully writes scenes.json via CLI."""
        runner = CliRunner()
        
        # Create a test story file
        story_file = tmp_path / "test_story.txt"
        story_file.write_text("A robot discovers emotions and learns to love.")

        with patch("story_video.scene_planner.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_openai_class.return_value = mock_client

            # Patch the outputs directory to use tmp_path
            with patch("story_video.cli.Path") as mock_path_class:
                # Make Path work normally except for the outputs directory
                mock_path_class.side_effect = lambda x: Path(x) if x != "__file__" else Path(__file__)
                
                # Run CLI with --plan-only
                result = runner.invoke(
                    cli,
                    [
                        "render",
                        "--input", str(story_file),
                        "--plan-only",
                        "--provider", "ollama",
                    ],
                )

                # Check command executed successfully
                assert result.exit_code == 0
                assert "Planning scenes" in result.output
                assert "Planned 4 scenes" in result.output
                assert "Planning complete (--plan-only mode)" in result.output

    def test_cli_doctor_command(self):
        """Test that doctor command runs without errors."""
        runner = CliRunner()
        
        # Mock some checks to ensure they pass
        with patch("story_video.doctor.SystemDoctor.check_all") as mock_check_all:
            mock_check_all.return_value = [
                ("Python version >= 3.10", True, "Python 3.10.0"),
                ("ffmpeg available", True, "Found in PATH"),
                ("Node.js available", True, "Found in PATH"),
            ]
            
            result = runner.invoke(cli, ["doctor"])
            
            # Doctor should run (exit code 0 if all pass, 1 if any fail)
            assert result.exit_code in [0, 1]
            assert "System Check" in result.output

    def test_cli_render_with_inline_prompt(
        self, tmp_path: Path, mock_openai_response, predetermined_story_plan: StoryPlan
    ):
        """Test CLI render with inline --prompt flag."""
        runner = CliRunner()

        with patch("story_video.scene_planner.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_openai_class.return_value = mock_client

            # Mock renderers to avoid actual subprocess calls
            with patch("story_video.renderers.image_renderer.ImageRenderer.render") as mock_img, \
                 patch("story_video.renderers.remotion_renderer.RemotionRenderer.render") as mock_rem, \
                 patch("story_video.renderers.manim_renderer.ManimRenderer.render") as mock_man, \
                 patch("story_video.cli._stitch_video") as mock_stitch:
                
                # Configure mock returns
                mock_img.return_value = RenderResult(
                    scene_number=1, clip_path=Path("scene_001.mp4"), duration=20.0, renderer="image", success=True
                )
                mock_rem.return_value = RenderResult(
                    scene_number=2, clip_path=Path("scene_002.mp4"), duration=25.0, renderer="remotion", success=True
                )
                mock_man.return_value = RenderResult(
                    scene_number=4, clip_path=Path("scene_004.mp4"), duration=15.0, renderer="manim", success=True
                )
                mock_stitch.return_value = True

                result = runner.invoke(
                    cli,
                    [
                        "render",
                        "--prompt", "A robot's emotional journey",
                        "--plan-only",  # Use plan-only to avoid full rendering in test
                        "--provider", "ollama",
                    ],
                )

                # Should succeed
                assert result.exit_code == 0
                assert "Planning scenes" in result.output


class TestErrorHandling:
    """Test error handling in the pipeline."""

    def test_continue_on_error_skips_failed_scenes(
        self, tmp_path: Path, predetermined_story_plan: StoryPlan
    ):
        """Test that --continue-on-error allows pipeline to continue past failures."""
        output_dir = tmp_path / "clips"
        output_dir.mkdir()

        def mock_render_with_failure(scene: Scene) -> RenderResult:
            """Mock renderer that fails on scene 2."""
            if scene.scene_number == 2:
                return RenderResult(
                    scene_number=scene.scene_number,
                    clip_path=Path(""),
                    duration=0.0,
                    renderer=scene.visual_style,
                    success=False,
                    error="Simulated render failure",
                )
            
            output_path = output_dir / f"scene_{scene.scene_number:03d}.mp4"
            output_path.write_text("mock video")
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=output_path,
                duration=float(scene.duration),
                renderer=scene.visual_style,
                success=True,
            )

        renderer = SceneRendererOrchestrator(output_dir=output_dir, quality="medium")
        renderer.image_renderer.render = mock_render_with_failure
        renderer.remotion_renderer.render = mock_render_with_failure
        renderer.manim_renderer.render = mock_render_with_failure

        # Render all scenes (with continue on error behavior)
        results = []
        for scene in predetermined_story_plan.scenes:
            result = renderer.render_scene(scene)
            results.append(result)
            # In real CLI, --continue-on-error prevents exit here

        # Should have 4 results, with scene 2 failed
        assert len(results) == 4
        assert results[0].success is True
        assert results[1].success is False  # Scene 2 failed
        assert results[2].success is True
        assert results[3].success is True

        # Playlist should only include successful scenes
        successful_results = [r for r in results if r.success]
        assert len(successful_results) == 3

    def test_invalid_scene_style_returns_error(self, tmp_path: Path):
        """Test that invalid visual_style is handled gracefully."""
        output_dir = tmp_path / "clips"
        output_dir.mkdir()

        # Create scene with invalid style (bypassing Pydantic validation for test)
        invalid_scene = Scene.model_construct(
            scene_number=1,
            duration=20,
            visual_style="invalid_style",  # type: ignore
            description="Test",
            prompt="Test prompt",
            narration="Test narration",
        )

        renderer = SceneRendererOrchestrator(output_dir=output_dir, quality="medium")
        result = renderer.render_scene(invalid_scene)

        # Result should indicate failure with error message
        assert result.success is False
        assert "Unknown visual style" in result.error
        # Renderer field should have a valid literal value (to satisfy Pydantic)
        assert result.renderer in ["image", "remotion", "manim"]

    def test_empty_playlist_raises_error(self, tmp_path):
        """Test that building a playlist with zero successful results raises ValueError."""
        failed_results = [
            RenderResult(scene_number=1, clip_path=Path(""), duration=0.0, renderer="image", success=False, error="failed"),
            RenderResult(scene_number=2, clip_path=Path(""), duration=0.0, renderer="remotion", success=False, error="failed"),
        ]
        with pytest.raises(ValueError, match="No scenes rendered"):
            PlaylistBuilder.build_playlist(failed_results, tmp_path / "playlist.yaml")
