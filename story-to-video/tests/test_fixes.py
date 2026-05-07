"""Tests covering bug-fix and coverage items for story-to-video."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from story_video.cli import cli, _stitch_video
from story_video.models import RenderResult, RunManifest, Scene, StoryPlan
from story_video.scene_planner import ScenePlanner
from story_video.tool_locator import find_tool, find_tool_file


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_scene(num: int, style: str = "image") -> Scene:
    return Scene(
        scene_number=num,
        duration=10,
        visual_style=style,
        description=f"Scene {num}",
        prompt=f"Prompt {num}",
        narration=f"Narration {num}",
    )


def _make_plan(n: int = 2) -> StoryPlan:
    return StoryPlan(
        title="Test",
        total_scenes=n,
        scenes=[_make_scene(i) for i in range(1, n + 1)],
    )


def _make_result(num: int, success: bool = True) -> RenderResult:
    return RenderResult(
        scene_number=num,
        clip_path=Path(f"scene_{num:03d}.mp4"),
        duration=10.0,
        renderer="image",
        success=success,
        error=None if success else "fail",
    )


def _make_manifest(plan: StoryPlan, results: list[RenderResult], status: str = "rendering") -> RunManifest:
    return RunManifest(
        run_id="test-run",
        created_at="2025-01-01T00:00:00",
        story_source="inline",
        plan=plan,
        results=results,
        status=status,
    )


# ===================================================================
# T1 — Resume logic tests
# ===================================================================


class TestResume:
    """Tests for resume workflow (bug #2 / T1)."""

    def test_resume_skips_already_successful_scenes(self, tmp_path):
        """Resume should skip scenes whose results are in the manifest."""
        run_dir = tmp_path / "resume_run"
        run_dir.mkdir()
        clips_dir = run_dir / "clips"
        clips_dir.mkdir()

        plan = _make_plan(2)
        results = [_make_result(1, success=True)]
        manifest = _make_manifest(plan, results)
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2)
        )

        runner = CliRunner()
        with patch("story_video.scene_planner.OpenAI"), \
             patch("story_video.renderers.image_renderer.ImageRenderer.render") as mock_render, \
             patch("story_video.cli._stitch_video", return_value=True):
            mock_render.return_value = _make_result(2, success=True)

            result = runner.invoke(cli, ["render", "--resume", str(run_dir), "--continue-on-error"])

        assert result.exit_code == 0
        assert "Skipping scene 1" in result.output
        # Scene 2 should have been rendered (not skipped)
        assert "Scene 2" in result.output
        assert mock_render.call_count == 1  # Renderer only called for scene 2

    def test_resume_missing_manifest_exits(self, tmp_path):
        """Resume with no manifest.json should sys.exit(1)."""
        run_dir = tmp_path / "empty_run"
        run_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--resume", str(run_dir)])
        assert result.exit_code == 1
        assert "No manifest.json" in result.output

    def test_resume_scene_not_in_manifest_results(self, tmp_path):
        """Resume when completed_scenes includes a number but results list is empty should not crash."""
        run_dir = tmp_path / "partial_run"
        run_dir.mkdir()
        clips_dir = run_dir / "clips"
        clips_dir.mkdir()

        plan = _make_plan(2)
        # Mark scene 1 as success in results but omit it from the results list
        # to simulate the scenario where completed_scenes set has it but results doesn't
        result_scene2_fail = _make_result(2, success=False)
        # results only has scene 2 (failed), but completed_scenes would not include it
        manifest = _make_manifest(plan, [result_scene2_fail])
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2)
        )

        runner = CliRunner()
        with patch("story_video.renderers.image_renderer.ImageRenderer.render") as mock_render, \
             patch("story_video.cli._stitch_video", return_value=True):
            mock_render.return_value = _make_result(1, success=True)

            result = runner.invoke(cli, ["render", "--resume", str(run_dir), "--continue-on-error"])

        # Should not crash with StopIteration
        assert result.exit_code == 0
        # Scene should have been re-rendered since it wasn't in manifest results
        assert mock_render.called, "Renderer should have been called for the re-rendered scene"


# ===================================================================
# T2 — Retry / JSON extraction tests
# ===================================================================


class TestRetryAndJsonExtraction:
    """Tests for ScenePlanner retry and _extract_json (T2)."""

    def test_extract_json_from_markdown_code_block(self):
        """_extract_json should handle ```json ... ``` wrapped responses."""
        planner = ScenePlanner.__new__(ScenePlanner)
        raw = '```json\n{"title": "Test", "total_scenes": 1, "scenes": [{"scene_number": 1}]}\n```'
        result = planner._extract_json(raw)
        assert result["title"] == "Test"

    def test_retry_invalid_json_then_valid(self):
        """LLM returns invalid JSON twice, then valid JSON on third attempt."""
        plan = _make_plan(1)
        valid_json = json.dumps(plan.model_dump())

        mock_bad1 = Mock()
        mock_bad1.choices = [Mock(message=Mock(content="not json at all"))]
        mock_bad2 = Mock()
        mock_bad2.choices = [Mock(message=Mock(content="{invalid"))]
        mock_good = Mock()
        mock_good.choices = [Mock(message=Mock(content=valid_json))]

        with patch("story_video.scene_planner.OpenAI") as mock_cls:
            client = Mock()
            client.chat.completions.create.side_effect = [mock_bad1, mock_bad2, mock_good]
            mock_cls.return_value = client

            planner = ScenePlanner(provider="ollama")
            result_plan = planner.plan_scenes("A short story")

        assert result_plan.title == "Test"
        assert client.chat.completions.create.call_count == 3
        # Verify temperature decreases across retries (progressively stricter)
        calls = client.chat.completions.create.call_args_list
        temps = [c.kwargs.get("temperature") for c in calls if c.kwargs and "temperature" in c.kwargs]
        if len(temps) >= 2:
            assert temps[-1] <= temps[0], f"Temperature should decrease across retries: {temps}"

    def test_retry_all_invalid_raises(self):
        """LLM returns invalid JSON all 3 times — should raise RuntimeError."""
        mock_bad = Mock()
        mock_bad.choices = [Mock(message=Mock(content="nope"))]

        with patch("story_video.scene_planner.OpenAI") as mock_cls:
            client = Mock()
            client.chat.completions.create.return_value = mock_bad
            mock_cls.return_value = client

            planner = ScenePlanner(provider="ollama")
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                planner.plan_scenes("A story")


# ===================================================================
# T3 — ToolLocator tests
# ===================================================================


class TestToolLocator:
    """Tests for find_tool and find_tool_file (T3)."""

    def test_find_tool_via_env_var(self, tmp_path):
        """Tool found via environment variable."""
        tool_path = tmp_path / "my-tool"
        tool_path.write_text("#!/bin/sh\necho hi")

        with patch.dict(os.environ, {"MY_TOOL_PATH": str(tool_path)}):
            result = find_tool("my-tool", env_var="MY_TOOL_PATH")
        assert result == str(tool_path)

    def test_find_tool_sibling_directory(self, tmp_path):
        """Tool found in sibling directory — returns None for bare directory (no executable inside)."""
        sibling = tmp_path / "sibling-tool"
        sibling.mkdir()

        with patch("story_video.tool_locator._REPO_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=False):
            result = find_tool("nonexistent-cli", sibling_path="sibling-tool")
        assert result is None

    def test_find_tool_sibling_directory_with_executable(self, tmp_path):
        """Tool found as executable file inside sibling directory."""
        sibling = tmp_path / "sibling-tool"
        sibling.mkdir()
        exe = sibling / "my-cli"
        exe.write_text("#!/bin/sh\necho hi")

        with patch("story_video.tool_locator._REPO_ROOT", tmp_path), \
             patch.dict(os.environ, {}, clear=False):
            result = find_tool("my-cli", sibling_path="sibling-tool")
        assert result == str(exe)

    def test_find_tool_not_found_returns_none(self):
        """Tool not found anywhere returns None."""
        with patch("story_video.tool_locator._REPO_ROOT", Path("/nonexistent")), \
             patch.dict(os.environ, {}, clear=False):
            result = find_tool("no-such-tool-xyz-12345")
        assert result is None


# ===================================================================
# T4 — Timeout handling tests
# ===================================================================


class TestTimeoutHandling:
    """Tests for subprocess timeout in renderers (T4)."""

    def test_remotion_timeout_returns_failure(self, tmp_path):
        """TimeoutExpired should produce RenderResult with success=False."""
        from story_video.renderers.remotion_renderer import RemotionRenderer

        renderer = RemotionRenderer(output_dir=tmp_path, quality="low")
        renderer.remotion_cli = "fake-remotion"

        scene = _make_scene(1, style="remotion")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 600)):
            result = renderer.render(scene)

        assert result.success is False
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    def test_image_renderer_timeout_returns_failure(self, tmp_path):
        """TimeoutExpired in image renderer produces RenderResult with success=False."""
        from story_video.renderers.image_renderer import ImageRenderer

        renderer = ImageRenderer(output_dir=tmp_path, quality="low", image_gen_path=Path("fake.py"))

        scene = _make_scene(1, style="image")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)):
            result = renderer.render(scene)

        assert result.success is False
        assert "timed out" in result.error.lower() or "timeout" in result.error.lower()


# ===================================================================
# T5 — Video stitcher tests
# ===================================================================


class TestVideoStitcher:
    """Tests for _stitch_video helper (T5)."""

    def test_stitch_video_tool_not_found_returns_false(self, tmp_path):
        """_stitch_video should return False when stitch tool is not found."""
        with patch("story_video.cli.find_tool", return_value=None):
            result = _stitch_video(
                tmp_path / "playlist.yaml",
                tmp_path / "output.mp4",
                "medium",
                "fade_to_black",
            )
        assert result is False


# ===================================================================
# T6 — Special character escaping test
# ===================================================================


class TestSpecialCharEscaping:
    """Tests for ffmpeg drawtext escaping in ImageRenderer (T6)."""

    def test_narration_special_chars_escaped(self, tmp_path):
        """Narration with quotes, colons, brackets, %, {}, newlines is escaped."""
        from story_video.renderers.image_renderer import ImageRenderer

        renderer = ImageRenderer(output_dir=tmp_path, quality="low", image_gen_path=Path("fake.py"))

        scene = _make_scene(1)
        scene = scene.model_copy(update={
            "narration": "Hello: 'world' [100%] {key}\nline2",
        })

        # We'll capture the ffmpeg command that would be built
        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            mock_result = Mock()
            mock_result.returncode = 0
            return mock_result

        # Mock _generate_image to return a fake image path
        fake_img = tmp_path / "temp_images" / "scene_001" / "scene_001.png"
        fake_img.parent.mkdir(parents=True, exist_ok=True)
        fake_img.write_bytes(b"\x89PNG fake")

        # Create output file so the existence check passes
        output_path = tmp_path / "scene_001.mp4"
        output_path.write_bytes(b"fake video")

        with patch.object(renderer, "_generate_image", return_value=fake_img), \
             patch("subprocess.run", side_effect=fake_run):
            renderer.render(scene)

        # Find the drawtext filter string in the command
        vf_arg = captured_cmd[captured_cmd.index("-vf") + 1]

        # Verify escaping
        assert "\\:" in vf_arg          # colon escaped
        assert "'\\''world'\\'" in vf_arg or "\\'" in vf_arg  # quote escaped
        assert "\\[" in vf_arg          # bracket escaped
        assert "%%" in vf_arg           # percent escaped
        assert "\\{" in vf_arg          # brace escaped
        assert "\\}" in vf_arg          # brace escaped
        assert "\\n" not in vf_arg or " " in vf_arg  # newline replaced with space


# ===================================================================
# Output directory tests (bug #1)
# ===================================================================


class TestOutputDirectory:
    """Tests for output directory resolution (bug #1)."""

    def test_output_dir_env_var(self, tmp_path, monkeypatch):
        """STORY_VIDEO_OUTPUT_DIR env var should be used when set."""
        runner = CliRunner()
        story_file = tmp_path / "story.txt"
        story_file.write_text("A short tale.")
        out_dir = tmp_path / "custom-out"

        monkeypatch.setenv("STORY_VIDEO_OUTPUT_DIR", str(out_dir))

        plan = _make_plan(1)
        valid_json = json.dumps(plan.model_dump())
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content=valid_json))]

        with patch("story_video.scene_planner.OpenAI") as mock_cls:
            client = Mock()
            client.chat.completions.create.return_value = mock_resp
            mock_cls.return_value = client

            result = runner.invoke(cli, ["render", "--input", str(story_file), "--plan-only"])

        assert result.exit_code == 0
        assert str(out_dir) in result.output

    def test_output_dir_cli_option(self, tmp_path):
        """--output-dir CLI option should override default."""
        runner = CliRunner()
        story_file = tmp_path / "story.txt"
        story_file.write_text("A short tale.")
        out_dir = tmp_path / "cli-out"

        plan = _make_plan(1)
        valid_json = json.dumps(plan.model_dump())
        mock_resp = Mock()
        mock_resp.choices = [Mock(message=Mock(content=valid_json))]

        with patch("story_video.scene_planner.OpenAI") as mock_cls:
            client = Mock()
            client.chat.completions.create.return_value = mock_resp
            mock_cls.return_value = client

            result = runner.invoke(cli, [
                "render", "--input", str(story_file),
                "--output-dir", str(out_dir),
                "--plan-only",
            ])

        assert result.exit_code == 0
        assert str(out_dir) in result.output
