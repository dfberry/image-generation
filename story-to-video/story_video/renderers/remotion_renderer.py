"""Remotion animation renderer adapter."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..config import RENDER_TIMEOUT_REMOTION
from ..models import RenderResult, Scene
from .base import BaseRenderer


class RemotionRenderer(BaseRenderer):
    """Renders dynamic animations using remotion-animation tool."""

    def __init__(
        self,
        output_dir: Path,
        quality: str = "medium",
        provider: str = "ollama",
        model: str = "llama3.2",
    ):
        super().__init__(output_dir, quality)
        self.provider = provider
        self.model = model
        self.remotion_cli = self._find_remotion_cli()

    def _find_remotion_cli(self) -> Optional[str]:
        """Find remotion-gen CLI (check PATH, then sibling directory)."""
        # Check PATH
        if shutil.which("remotion-gen"):
            return "remotion-gen"
        
        # Check sibling directory
        repo_root = Path(__file__).parent.parent.parent.parent
        sibling_path = repo_root / "remotion-animation"
        if sibling_path.exists():
            # Assume it's in the sibling's node_modules or has a CLI wrapper
            return str(sibling_path / "remotion-gen")
        
        return None

    def is_available(self) -> tuple[bool, Optional[str]]:
        """Check if remotion-gen CLI is available."""
        if not self.remotion_cli:
            return False, "remotion-gen not found in PATH or sibling directory"
        return True, None

    def render(self, scene: Scene) -> RenderResult:
        """Render scene using remotion-gen CLI."""
        try:
            output_path = self._get_output_path(scene)
            
            cmd = [
                self.remotion_cli,
                "--prompt", f"{scene.prompt}\n\nNarration: {scene.narration}",
                "--output", str(output_path),
                "--duration", str(scene.duration),
                "--quality", self.quality,
                "--provider", self.provider,
                "--model", self.model,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=RENDER_TIMEOUT_REMOTION,
                cwd=Path(self.remotion_cli).parent if "/" in self.remotion_cli or "\\" in self.remotion_cli else None,
                env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"},
            )
            
            # Check success by output file existence (remotion-gen may have non-fatal
            # encoding errors in stderr on Windows that don't prevent video creation)
            if output_path.exists() and output_path.stat().st_size > 0:
                return RenderResult(
                    scene_number=scene.scene_number,
                    clip_path=output_path,
                    duration=float(scene.duration),
                    renderer="remotion",
                    success=True,
                )
            
            if result.returncode != 0:
                stderr_text = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr or "")
                raise RuntimeError(f"Remotion rendering failed: {stderr_text}")
            
            raise RuntimeError("Output video is empty or missing")
        except Exception as e:
            return RenderResult(
                scene_number=scene.scene_number,
                clip_path=Path(""),
                duration=0.0,
                renderer="remotion",
                success=False,
                error=str(e),
            )
