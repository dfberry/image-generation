"""Manim animation renderer adapter."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..config import RENDER_TIMEOUT_MANIM
from ..models import RenderResult, Scene
from .base import BaseRenderer


class ManimRenderer(BaseRenderer):
    """Renders explanatory animations using manim-animation tool."""

    def __init__(self, output_dir: Path, quality: str = "medium"):
        super().__init__(output_dir, quality)
        self.manim_path = self._find_manim()

    def _find_manim(self) -> Optional[Path]:
        """Find manim tool (check sibling directory)."""
        # Check if manim is in PATH
        if shutil.which("manim"):
            return Path("manim")
        
        # Check sibling directory
        repo_root = Path(__file__).parent.parent.parent.parent
        sibling_path = repo_root / "manim-animation"
        if sibling_path.exists():
            return sibling_path
        
        return None

    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if manim is available."""
        if not self.manim_path:
            return False, "manim not found in PATH or sibling directory"
        return True, None

    def render(self, scene: Scene) -> RenderResult:
        """Render scene using manim.
        
        Note: This is a placeholder implementation. In practice, you would need
        to generate a Manim scene script from the prompt and then render it.
        """
        try:
            output_path = self._get_output_path(scene)
            
            # TODO: Implement actual Manim scene generation from prompt
            # For now, create a placeholder video
            self._create_placeholder_video(scene, output_path)
            
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=output_path,
                duration=float(scene.duration),
                renderer="manim",
                success=True,
            )
        except Exception as e:
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=Path(""),
                duration=0.0,
                renderer="manim",
                success=False,
                error=str(e),
            )

    def _create_placeholder_video(self, scene: Scene, output_path: Path):
        """Create a placeholder video with text (until Manim integration is complete)."""
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"color=c=blue:s=1920x1080:d={scene.duration}",
            "-vf",
            f"drawtext=text='Manim Scene {scene.scene_number}\\n{scene.description}':fontsize=40:"
            f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-pix_fmt", "yuv420p",
            "-y",
            str(output_path),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_MANIM,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Placeholder video creation failed: {result.stderr}")
