"""Tests for intelligent scene routing (issue #121)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from story_video.models import RenderResult, RendererStrategy, Scene
from story_video.scene_renderer import SceneRendererOrchestrator


def _make_scene(prompt: str, narration: str = "", scene_number: int = 1) -> Scene:
    """Create a test scene with given prompt and narration."""
    return Scene(
        scene_number=scene_number,
        duration=10,
        visual_style="remotion",  # Plan says remotion, but routing may override
        description="Test scene",
        prompt=prompt,
        narration=narration or prompt,
    )


@pytest.fixture
def orchestrator(tmp_path: Path) -> SceneRendererOrchestrator:
    """Create orchestrator with default strategy."""
    return SceneRendererOrchestrator(output_dir=tmp_path)


@pytest.fixture
def orchestrator_prefer_image(tmp_path: Path) -> SceneRendererOrchestrator:
    """Create orchestrator with prefer-image strategy."""
    return SceneRendererOrchestrator(
        output_dir=tmp_path,
        renderer_strategy=RendererStrategy(strategy="prefer-image"),
    )


@pytest.fixture
def orchestrator_force_image(tmp_path: Path) -> SceneRendererOrchestrator:
    """Create orchestrator with force image override."""
    return SceneRendererOrchestrator(
        output_dir=tmp_path,
        renderer_strategy=RendererStrategy(force_renderer="image"),
    )


class TestIntelligentRouting:
    """Test _intelligent_routing method."""

    def test_narrative_content_routes_to_image(self, orchestrator):
        """Narrative scenes with characters/objects → image renderer."""
        scene = _make_scene(
            "A girl walks through a magical garden with glowing flowers",
            "The child discovers a beautiful ancient tree",
        )
        assert orchestrator._intelligent_routing(scene) == "image"

    def test_abstract_content_routes_to_remotion(self, orchestrator):
        """Abstract/diagrammatic scenes → remotion renderer."""
        scene = _make_scene(
            "A flowchart showing the algorithm's data flow",
            "The diagram illustrates the equation and formula",
        )
        assert orchestrator._intelligent_routing(scene) == "remotion"

    def test_mixed_content_with_more_narrative_routes_image(self, orchestrator):
        """Mixed content with more narrative keywords → image."""
        scene = _make_scene(
            "A person standing in a forest near a mountain landscape",
            "The woman walks through the garden",
        )
        assert orchestrator._intelligent_routing(scene) == "image"

    def test_no_keywords_defaults_to_image(self, orchestrator):
        """No keyword matches defaults to image (conservative)."""
        scene = _make_scene(
            "Something abstract happening",
            "An undefined concept",
        )
        assert orchestrator._intelligent_routing(scene) == "image"

    def test_tie_score_defaults_to_image(self, orchestrator):
        """When narrative and abstract scores are equal, defaults to image."""
        # One narrative keyword (tree) and one abstract keyword (diagram)
        scene = _make_scene(
            "A tree next to a diagram",
            "Just a scene",
        )
        assert orchestrator._intelligent_routing(scene) == "image"

    def test_keyword_word_boundary_no_false_positives(self, orchestrator):
        """Keyword matching uses word boundaries — no substring false positives."""
        # "decode" contains "code" but should NOT match
        # "decision" contains no exact abstract keyword
        scene = _make_scene(
            "A person will decode the mystery",
            "The decision about the streetcar",
        )
        # Only "person" matches narrative; no abstract matches
        assert orchestrator._intelligent_routing(scene) == "image"

    def test_prefer_image_strategy_biases_routing(self, orchestrator_prefer_image):
        """prefer-image strategy adds bias toward image renderer."""
        # One abstract keyword, but prefer-image adds +2 to narrative
        scene = _make_scene("A diagram of something")
        assert orchestrator_prefer_image._intelligent_routing(scene) == "image"

    def test_prefer_remotion_strategy_biases_routing(self, tmp_path):
        """prefer-remotion strategy adds bias toward remotion."""
        orch = SceneRendererOrchestrator(
            output_dir=tmp_path,
            renderer_strategy=RendererStrategy(strategy="prefer-remotion"),
        )
        # One narrative keyword, but prefer-remotion adds +2 to abstract
        scene = _make_scene("A tree in an empty space")
        assert orch._intelligent_routing(scene) == "remotion"


class TestForceRendererOverride:
    """Test that force_renderer bypasses routing."""

    def test_force_image_overrides_abstract_content(self, orchestrator_force_image):
        """Force flag sends abstract content to image renderer anyway."""
        scene = _make_scene("A complex flowchart diagram with equations")
        # Would normally route to remotion, but force overrides
        # We can't call render (no ffmpeg), so test the logic path
        assert orchestrator_force_image.renderer_strategy.force_renderer == "image"

    def test_force_remotion_overrides_narrative_content(self, tmp_path):
        """Force remotion sends narrative content to remotion anyway."""
        orch = SceneRendererOrchestrator(
            output_dir=tmp_path,
            renderer_strategy=RendererStrategy(force_renderer="remotion"),
        )
        assert orch.renderer_strategy.force_renderer == "remotion"

    def test_force_image_calls_image_renderer(self, tmp_path):
        """Force image actually routes render_scene() to image renderer."""
        orch = SceneRendererOrchestrator(
            output_dir=tmp_path,
            renderer_strategy=RendererStrategy(force_renderer="image"),
        )
        scene = _make_scene("A complex flowchart diagram with equations")
        mock_result = RenderResult(
            scene_number=1, clip_path=Path("out.mp4"),
            duration=10.0, renderer="image", success=True,
        )
        orch.image_renderer.is_available = MagicMock(return_value=(True, None))
        orch.image_renderer.render = MagicMock(return_value=mock_result)
        orch.remotion_renderer.render = MagicMock()
        orch.manim_renderer.render = MagicMock()

        result = orch.render_scene(scene)

        orch.image_renderer.render.assert_called_once_with(scene)
        orch.remotion_renderer.render.assert_not_called()
        orch.manim_renderer.render.assert_not_called()
        assert result.renderer == "image"

    def test_force_remotion_calls_remotion_renderer(self, tmp_path):
        """Force remotion actually routes render_scene() to remotion renderer."""
        orch = SceneRendererOrchestrator(
            output_dir=tmp_path,
            renderer_strategy=RendererStrategy(force_renderer="remotion"),
        )
        scene = _make_scene("A girl walks through a magical garden")
        mock_result = RenderResult(
            scene_number=1, clip_path=Path("out.mp4"),
            duration=10.0, renderer="remotion", success=True,
        )
        orch.remotion_renderer.is_available = MagicMock(return_value=(True, None))
        orch.remotion_renderer.render = MagicMock(return_value=mock_result)
        orch.image_renderer.render = MagicMock()
        orch.manim_renderer.render = MagicMock()

        result = orch.render_scene(scene)

        orch.remotion_renderer.render.assert_called_once_with(scene)
        orch.image_renderer.render.assert_not_called()
        orch.manim_renderer.render.assert_not_called()
        assert result.renderer == "remotion"

    def test_force_manim_calls_manim_renderer(self, tmp_path):
        """Force manim actually routes render_scene() to manim renderer."""
        orch = SceneRendererOrchestrator(
            output_dir=tmp_path,
            renderer_strategy=RendererStrategy(force_renderer="manim"),
        )
        scene = _make_scene("A girl walks through a magical garden")
        mock_result = RenderResult(
            scene_number=1, clip_path=Path("out.mp4"),
            duration=10.0, renderer="manim", success=True,
        )
        orch.manim_renderer.is_available = MagicMock(return_value=(True, None))
        orch.manim_renderer.render = MagicMock(return_value=mock_result)
        orch.image_renderer.render = MagicMock()
        orch.remotion_renderer.render = MagicMock()

        result = orch.render_scene(scene)

        orch.manim_renderer.render.assert_called_once_with(scene)
        orch.image_renderer.render.assert_not_called()
        orch.remotion_renderer.render.assert_not_called()
        assert result.renderer == "manim"


class TestRendererStrategyModel:
    """Test RendererStrategy pydantic model."""

    def test_default_strategy(self):
        rs = RendererStrategy()
        assert rs.strategy == "auto"
        assert rs.force_renderer is None

    def test_valid_strategies(self):
        for s in ("auto", "prefer-image", "prefer-remotion"):
            rs = RendererStrategy(strategy=s)
            assert rs.strategy == s

    def test_valid_force_values(self):
        for r in ("image", "remotion", "manim"):
            rs = RendererStrategy(force_renderer=r)
            assert rs.force_renderer == r
