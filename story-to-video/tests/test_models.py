"""Tests for pydantic models."""

import pytest
from story_video.models import Scene, StoryPlan, RenderResult, RunManifest


def test_scene_creation():
    """Test Scene model validation."""
    scene = Scene(
        scene_number=1,
        duration=20,
        visual_style="image",
        description="Test scene",
        prompt="A beautiful landscape",
        narration="This is a test",
        transition="fade_to_black",
    )
    
    assert scene.scene_number == 1
    assert scene.duration == 20
    assert scene.visual_style == "image"


def test_scene_duration_validation():
    """Test duration constraints (5-30 seconds)."""
    with pytest.raises(ValueError):
        Scene(
            scene_number=1,
            duration=2,  # Too short
            visual_style="image",
            description="Test",
            prompt="Test",
            narration="Test",
        )
    
    with pytest.raises(ValueError):
        Scene(
            scene_number=1,
            duration=35,  # Too long
            visual_style="image",
            description="Test",
            prompt="Test",
            narration="Test",
        )


def test_story_plan_creation():
    """Test StoryPlan model."""
    scenes = [
        Scene(
            scene_number=1,
            visual_style="image",
            description="Scene 1",
            prompt="Prompt 1",
            narration="Narration 1",
        ),
        Scene(
            scene_number=2,
            visual_style="remotion",
            description="Scene 2",
            prompt="Prompt 2",
            narration="Narration 2",
        ),
    ]
    
    plan = StoryPlan(
        title="Test Story",
        total_scenes=2,
        scenes=scenes,
    )
    
    assert plan.title == "Test Story"
    assert plan.total_scenes == 2
    assert len(plan.scenes) == 2


def test_render_result():
    """Test RenderResult model."""
    from pathlib import Path
    
    result = RenderResult(
        scene_number=1,
        clip_path=Path("/tmp/scene_001.mp4"),
        duration=20.0,
        renderer="image",
        success=True,
    )
    
    assert result.success is True
    assert result.error is None
    
    failed_result = RenderResult(
        scene_number=2,
        clip_path=Path(""),
        duration=0.0,
        renderer="remotion",
        success=False,
        error="Rendering failed",
    )
    
    assert failed_result.success is False
    assert failed_result.error == "Rendering failed"


def test_story_plan_scene_count_mismatch():
    """Test that total_scenes must match len(scenes)."""
    scene = Scene(
        scene_number=1,
        visual_style="image",
        description="Test",
        prompt="Test",
        narration="Test",
    )
    with pytest.raises(ValueError, match="total_scenes"):
        StoryPlan(title="Test", total_scenes=3, scenes=[scene])


def test_story_plan_non_sequential_scenes():
    """Test that scene numbers must be sequential 1..N."""
    scenes = [
        Scene(scene_number=1, visual_style="image", description="S1", prompt="P1", narration="N1"),
        Scene(scene_number=3, visual_style="image", description="S2", prompt="P2", narration="N2"),
    ]
    with pytest.raises(ValueError, match="sequential"):
        StoryPlan(title="Test", total_scenes=2, scenes=scenes)


def test_story_plan_duplicate_scene_numbers():
    """Test that duplicate scene numbers are rejected."""
    scenes = [
        Scene(scene_number=1, visual_style="image", description="S1", prompt="P1", narration="N1"),
        Scene(scene_number=1, visual_style="image", description="S2", prompt="P2", narration="N2"),
    ]
    with pytest.raises(ValueError, match="sequential"):
        StoryPlan(title="Test", total_scenes=2, scenes=scenes)
