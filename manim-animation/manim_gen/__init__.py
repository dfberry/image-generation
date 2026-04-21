"""Manim Animation Generator - Python API"""

from manim_gen.cli import main
from manim_gen.config import Config, QualityPreset
from manim_gen.errors import LLMError, RenderError, ValidationError
from manim_gen.llm_client import LLMClient
from manim_gen.renderer import render_scene
from manim_gen.scene_builder import build_scene

__all__ = [
    "main",
    "Config",
    "QualityPreset",
    "LLMError",
    "RenderError",
    "ValidationError",
    "LLMClient",
    "render_scene",
    "build_scene",
]
