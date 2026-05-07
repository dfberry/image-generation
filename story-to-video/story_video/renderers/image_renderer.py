"""Image renderer with Ken Burns effect and text overlay."""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..config import RENDER_TIMEOUT_IMAGE
from ..models import RenderResult, Scene
from ..tool_locator import find_tool_file
from .base import BaseRenderer


class ImageRenderer(BaseRenderer):
    """Renders static images with Ken Burns motion and text overlay."""

    DEFAULT_STYLE_ANCHOR = (
        "Latin American folk art style, magical realism illustration, "
        "warm luminous lighting, no text"
    )

    def __init__(self, output_dir: Path, quality: str = "medium", image_gen_path: Optional[Path] = None, style_anchor: Optional[str] = None):
        super().__init__(output_dir, quality)
        self.image_gen_path = image_gen_path or self._find_image_gen()
        self.style_anchor = style_anchor or self.DEFAULT_STYLE_ANCHOR
        self.temp_dir = output_dir / "temp_images"
        self.temp_dir.mkdir(exist_ok=True)

    def _find_image_gen(self) -> Optional[Path]:
        """Find image-generation tool (check env var, then sibling directory)."""
        return find_tool_file("image-generation/generate.py", env_var="IMAGE_GEN_PATH")

    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if ffmpeg and image-generation are available."""
        if not shutil.which("ffmpeg"):
            return False, "ffmpeg not found in PATH"
        
        if not self.image_gen_path or not self.image_gen_path.exists():
            return False, "image-generation tool not found"
        
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
        """Call image-generation to create a still image."""
        output_dir = self.temp_dir / f"scene_{scene.scene_number:03d}"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"scene_{scene.scene_number:03d}.png"

        enhanced_prompt = self._build_sdxl_prompt(scene)
        
        cmd = [
            sys.executable,
            str(self.image_gen_path),
            "--prompt", enhanced_prompt,
            "--output", str(output_file),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RENDER_TIMEOUT_IMAGE,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Image generation failed: {result.stderr}")
        
        if output_file.exists():
            if output_file.stat().st_size == 0:
                raise RuntimeError(f"Image generation produced 0-byte file: {output_file}")
            return output_file

        raise RuntimeError(f"Expected output {output_file} not found after image generation")

    def _create_video_from_image(self, scene: Scene, image_path: Path) -> Path:
        """Apply Ken Burns effect and text overlay using ffmpeg."""
        output_path = self._get_output_path(scene)
        duration = scene.duration
        
        # Ken Burns effect: slow zoom and pan
        
        # Text overlay (escape special chars for ffmpeg drawtext)
        narration = (scene.narration
            .replace("\\", "\\\\")
            .replace("'", "'\\''")
            .replace(":", "\\:")
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
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Video creation failed: {result.stderr}")
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Output video is empty")
        
        return output_path
