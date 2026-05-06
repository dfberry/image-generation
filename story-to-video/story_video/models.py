"""Pydantic models for story-to-video data structures."""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class RenderResult(BaseModel):
    """Result of rendering a single scene."""

    scene_number: int
    clip_path: Path
    duration: float
    renderer: Literal["image", "remotion", "manim"]
    success: bool
    error: Optional[str] = None


class RunManifest(BaseModel):
    """Complete manifest of a story-to-video run."""

    run_id: str
    created_at: str
    story_source: str
    plan: StoryPlan
    results: list[RenderResult] = []
    final_output: Optional[Path] = None
    status: Literal["planning", "rendering", "stitching", "complete", "failed"]
