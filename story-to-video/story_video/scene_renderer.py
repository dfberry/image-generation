"""Scene renderer orchestrator - routes scenes to appropriate renderers."""

import logging
import re
from pathlib import Path
from typing import Literal, Optional

from .models import RenderResult, RendererStrategy, Scene
from .renderers import ImageRenderer, ManimRenderer, RemotionRenderer

logger = logging.getLogger(__name__)

# Keywords that signal narrative/visual content → image renderer
NARRATIVE_KEYWORDS = frozenset([
    "character", "person", "people", "animal", "cat", "dog", "bird", "fish",
    "tree", "flower", "garden", "house", "landscape", "forest", "mountain",
    "ocean", "river", "sky", "sun", "moon", "star", "village", "city",
    "woman", "man", "child", "boy", "girl", "family", "friend",
    "walk", "run", "fly", "swim", "dance", "sing", "paint",
    "magical", "glowing", "colorful", "beautiful", "ancient", "mysterious",
])

# Keywords that signal abstract/diagrammatic content → remotion renderer
ABSTRACT_KEYWORDS = frozenset([
    "diagram", "chart", "graph", "equation", "formula", "geometric",
    "theorem", "proof", "algorithm", "data", "statistics", "table",
    "flowchart", "architecture", "schematic", "blueprint", "wireframe",
    "code", "syntax", "terminal", "console", "matrix", "vector",
])


class SceneRendererOrchestrator:
    """Routes scenes to the appropriate renderer based on visual style."""

    def __init__(
        self,
        output_dir: Path,
        quality: str = "medium",
        provider: str = "ollama",
        model: str = "llama3.2",
        renderer_strategy: Optional[RendererStrategy] = None,
    ):
        self.output_dir = output_dir
        self.quality = quality
        self.provider = provider
        self.model = model
        self.renderer_strategy = renderer_strategy or RendererStrategy()
        
        # Initialize renderers
        self.image_renderer = ImageRenderer(output_dir, quality)
        self.remotion_renderer = RemotionRenderer(output_dir, quality, provider, model)
        self.manim_renderer = ManimRenderer(output_dir, quality)

    def _intelligent_routing(self, scene: Scene) -> str:
        """Analyze scene content and route to the best renderer.
        
        Scores narrative vs abstract keywords in prompt+narration.
        Default bias: image renderer (better results for stories).
        """
        text = f"{scene.prompt} {scene.narration}".lower()

        narrative_score = sum(1 for kw in NARRATIVE_KEYWORDS if re.search(r'\b' + kw + r'\b', text))
        abstract_score = sum(1 for kw in ABSTRACT_KEYWORDS if re.search(r'\b' + kw + r'\b', text))

        # Apply strategy bias
        strategy = self.renderer_strategy.strategy
        if strategy == "prefer-image":
            narrative_score += 2
        elif strategy == "prefer-remotion":
            abstract_score += 2

        # Default to image when tied or no signals
        if abstract_score > narrative_score:
            result = "remotion"
        else:
            result = "image"

        logger.debug(
            f"Scene {scene.scene_number}: narrative={narrative_score}, "
            f"abstract={abstract_score} → {result}"
        )
        return result

    def render_scene(self, scene: Scene) -> RenderResult:
        """Route scene to the appropriate renderer and render it."""
        if self.renderer_strategy.force_renderer:
            effective_style = self.renderer_strategy.force_renderer
        else:
            effective_style = self._intelligent_routing(scene)

        if effective_style == "image":
            return self.image_renderer.render(scene)
        elif effective_style == "remotion":
            return self.remotion_renderer.render(scene)
        elif effective_style == "manim":
            return self.manim_renderer.render(scene)
        else:
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=Path(""),
                duration=0.0,
                renderer="image",
                success=False,
                error=f"Unknown visual style: {effective_style}",
            )

    def check_availability(self) -> dict[str, tuple[bool, str]]:
        """Check which renderers are available."""
        return {
            "image": self.image_renderer.is_available(),
            "remotion": self.remotion_renderer.is_available(),
            "manim": self.manim_renderer.is_available(),
        }
