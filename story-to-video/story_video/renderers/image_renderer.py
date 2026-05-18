"""Image renderer with Ken Burns effect and text overlay."""

import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..image_generators import ImageGeneratorBase, get_image_generator
from ..models import RenderResult, Scene
from .base import BaseRenderer

logger = logging.getLogger(__name__)


class ImageRenderer(BaseRenderer):
    """Renders static images with Ken Burns motion and text overlay."""

    DEFAULT_STYLE_ANCHOR = (
        "Latin American folk art style, magical realism illustration, "
        "warm luminous lighting, no text"
    )

    def __init__(
        self,
        output_dir: Path,
        quality: str = "medium",
        image_gen_path: Optional[Path] = None,
        style_anchor: Optional[str] = None,
        image_generator: Optional[ImageGeneratorBase] = None,
    ):
        """Initialize ImageRenderer.

        Args:
            output_dir: Directory for rendered video output files.
            quality: Render quality preset (low/medium/high).
            image_gen_path: Deprecated — use image_generator instead.
            style_anchor: Style prompt suffix appended to every scene prompt
                for visual consistency across scenes. Defaults to Latin American
                folk art / magical realism aesthetic.
            image_generator: Pluggable image generation backend. Defaults to
                local SDXL if not provided.
        """
        super().__init__(output_dir, quality)
        self.image_generator = image_generator or get_image_generator("local")
        self.style_anchor = style_anchor or self.DEFAULT_STYLE_ANCHOR
        self.temp_dir = output_dir / "temp_images"
        self.temp_dir.mkdir(exist_ok=True)

    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if ffmpeg and the image generator are available."""
        if not shutil.which("ffmpeg"):
            return False, "ffmpeg not found in PATH"

        gen_ok, gen_reason = self.image_generator.is_available()
        if not gen_ok:
            return False, f"Image generator '{self.image_generator.name}' not available: {gen_reason}"

        return True, None

    def render(self, scene: Scene) -> RenderResult:
        """Generate still image, then apply Ken Burns effect and text overlay."""
        try:
            # Step 1: Generate still image
            image_path = self._generate_image(scene)
            
            # Step 2: Apply Ken Burns effect and text overlay
            video_path = self._create_video_from_image(scene, image_path)
            
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=video_path,
                duration=float(scene.duration),
                renderer="image",
                success=True,
            )
        except Exception as e:
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=Path(""),
                duration=0.0,
                renderer="image",
                success=False,
                error=str(e),
            )

    def _build_sdxl_prompt(self, scene: Scene) -> str:
        """Build an enhanced SDXL prompt with story elements and framing hints."""
        # Extract action verbs and objects from narration
        base_prompt = scene.prompt

        # Add framing hint based on scene position
        scene_num = scene.scene_number
        if scene_num == 1:
            framing = "wide establishing shot"
        elif scene_num <= 3:
            framing = "medium shot"
        else:
            framing = "close-up detail shot"

        # Style anchor for consistent aesthetic (configurable)
        style_anchor = self.style_anchor

        return f"{base_prompt}, {framing}, {style_anchor}"

    def _generate_image(self, scene: Scene) -> Path:
        """Delegate image generation to the pluggable backend."""
        output_dir = self.temp_dir / f"scene_{scene.scene_number:03d}"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"scene_{scene.scene_number:03d}.png"

        enhanced_prompt = self._build_sdxl_prompt(scene)

        logger.debug(f"Generating image via {self.image_generator.name}: scene {scene.scene_number}")
        return self.image_generator.generate(enhanced_prompt, output_file)

    def _create_video_from_image(self, scene: Scene, image_path: Path) -> Path:
        """Apply Ken Burns effect and text overlay using ffmpeg."""
        output_path = self._get_output_path(scene)
        duration = scene.duration
        
        # Ken Burns effect: slow zoom and pan
        
        # Text overlay (escape special chars for ffmpeg drawtext filter).
        # Since we use subprocess.run with a list (no shell), we only need
        # ffmpeg filter-level escaping, not shell escaping.
        narration = (scene.narration
            .replace("\\", "\\\\\\\\")
            .replace("'", "\\\\'")
            .replace(":", "\\\\:")
            .replace(",", "\\,")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("%", "%%")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace("\n", " "))
        
        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", str(image_path),
            "-vf",
            f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"zoompan=z='min(1+0.002*on,1.2)':d={duration*30}:s=1920x1080:fps=30,"
            f"drawtext=text='{narration}':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=h-80:"
            f"box=1:boxcolor=black@0.7:boxborderw=10",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-y",
            str(output_path),
        ]
        
        logger.debug(f"Running ffmpeg Ken Burns: scene {scene.scene_number}, duration={duration}s")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        logger.debug(f"ffmpeg exited with code {result.returncode}")
        
        if result.returncode != 0:
            raise RuntimeError(f"Video creation failed: {result.stderr}")
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Output video is empty")
        
        return output_path
