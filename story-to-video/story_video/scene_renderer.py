"""Scene renderer orchestrator - routes scenes to appropriate renderers."""

from pathlib import Path
from typing import Literal

from .models import RenderResult, Scene
from .renderers import ImageRenderer, ManimRenderer, RemotionRenderer


class SceneRendererOrchestrator:
    """Routes scenes to the appropriate renderer based on visual style."""

    def __init__(
        self,
        output_dir: Path,
        quality: str = "medium",
        provider: str = "ollama",
        model: str = "llama3.2",
    ):
        self.output_dir = output_dir
        self.quality = quality
        self.provider = provider
        self.model = model
        
        # Initialize renderers
        self.image_renderer = ImageRenderer(output_dir, quality)
        self.remotion_renderer = RemotionRenderer(output_dir, quality, provider, model)
        self.manim_renderer = ManimRenderer(output_dir, quality)

    def render_scene(self, scene: Scene) -> RenderResult:
        """Route scene to the appropriate renderer and render it."""
        if scene.visual_style == "image":
            return self.image_renderer.render(scene)
        elif scene.visual_style == "remotion":
            return self.remotion_renderer.render(scene)
        elif scene.visual_style == "manim":
            return self.manim_renderer.render(scene)
        else:
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=Path(""),
                duration=0.0,
                renderer=scene.visual_style,
                success=False,
                error=f"Unknown visual style: {scene.visual_style}",
            )

    def check_availability(self) -> dict[str, tuple[bool, str]]:
        """Check which renderers are available."""
        return {
            "image": self.image_renderer.is_available(),
            "remotion": self.remotion_renderer.is_available(),
            "manim": self.manim_renderer.is_available(),
        }
