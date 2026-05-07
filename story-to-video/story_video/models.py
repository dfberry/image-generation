"""Pydantic models for story-to-video data structures."""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Scene(BaseModel):
    """Represents a single scene in the story."""

    scene_number: int
    duration: int = Field(default=30, ge=5, le=30)
    visual_style: Literal["image", "remotion", "manim"]
    description: str
    prompt: str
    narration: str
    transition: Literal["none", "fade_to_black", "crossfade"] = "fade_to_black"


class StoryPlan(BaseModel):
    """Complete story plan with all scenes."""

    title: str
    total_scenes: int
    scenes: list[Scene]

    @model_validator(mode="after")
    def validate_scenes(self) -> "StoryPlan":
        if len(self.scenes) != self.total_scenes:
            raise ValueError(f"total_scenes ({self.total_scenes}) != len(scenes) ({len(self.scenes)})")
        numbers = [s.scene_number for s in self.scenes]
        expected = list(range(1, self.total_scenes + 1))
        if sorted(numbers) != expected:
            raise ValueError(f"Scene numbers must be sequential 1..{self.total_scenes}, got {numbers}")
        return self


class RenderResult(BaseModel):
    """Result of rendering a single scene."""

    scene_number: int
    clip_path: Path
    duration: float
    renderer: Literal["image", "remotion", "manim"]
    success: bool
    error: Optional[str] = None


class RendererStrategy(BaseModel):
    """Configuration for intelligent scene routing."""

    strategy: Literal["auto", "prefer-image", "prefer-remotion"] = "auto"
    force_renderer: Optional[Literal["image", "remotion", "manim"]] = None


class RunManifest(BaseModel):
    """Complete manifest of a story-to-video run."""

    run_id: str
    created_at: str
    story_source: str
    plan: StoryPlan
    results: list[RenderResult] = []
    final_output: Optional[Path] = None
    status: Literal["planning", "rendering", "stitching", "complete", "failed"]
