"""Preflight system checks for story-to-video."""

import shutil
import sys
from pathlib import Path
from typing import List, Tuple

from .config import DEFAULT_PROVIDER, OLLAMA_BASE_URL
from .tool_locator import find_tool, find_tool_file


class SystemDoctor:
    """Performs preflight checks for all dependencies."""

    @staticmethod
    def check_all() -> List[Tuple[str, bool, str]]:
        """Run all checks and return results."""
        checks = [
            ("Python version >= 3.10", *SystemDoctor._check_python_version()),
            ("ffmpeg available", *SystemDoctor._check_ffmpeg()),
            ("Node.js available", *SystemDoctor._check_nodejs()),
            ("remotion-gen available", *SystemDoctor._check_remotion()),
            ("stitch-video available", *SystemDoctor._check_stitcher()),
            ("image-generation available", *SystemDoctor._check_image_gen()),
            ("LLM provider configured", *SystemDoctor._check_llm_provider()),
            ("Output directory writable", *SystemDoctor._check_output_dir()),
        ]
        return checks

    @staticmethod
    def _check_python_version() -> Tuple[bool, str]:
        """Check Python version."""
        version = sys.version_info
        if version >= (3, 10):
            return True, f"Python {version.major}.{version.minor}.{version.micro}"
        return False, f"Python {version.major}.{version.minor} (need >= 3.10)"

    @staticmethod
    def _check_ffmpeg() -> Tuple[bool, str]:
        """Check if ffmpeg is in PATH."""
        if shutil.which("ffmpeg"):
            return True, "Found in PATH"
        return False, "Not found in PATH"

    @staticmethod
    def _check_nodejs() -> Tuple[bool, str]:
        """Check if Node.js is available."""
        if shutil.which("node"):
            return True, "Found in PATH"
        return False, "Not found (needed for Remotion)"

    @staticmethod
    def _check_remotion() -> Tuple[bool, str]:
        """Check if remotion-gen is available."""
        result = find_tool("remotion-gen", sibling_path="remotion-animation")
        if result:
            return True, f"Found: {result}"
        return False, "Not found in PATH or sibling directory"

    @staticmethod
    def _check_stitcher() -> Tuple[bool, str]:
        """Check if stitch-video is available."""
        result = find_tool("stitch-video", sibling_path="video-stitcher")
        if result:
            return True, f"Found: {result}"
        return False, "Not found in PATH or sibling directory"

    @staticmethod
    def _check_image_gen() -> Tuple[bool, str]:
        """Check if image-generation is available."""
        result = find_tool_file("image-generation/generate.py")
        if result:
            return True, f"Found: {result}"
        return False, "Not found in sibling directory"

    @staticmethod
    def _check_llm_provider() -> Tuple[bool, str]:
        """Check if LLM provider is configured."""
        import os
        
        if DEFAULT_PROVIDER == "ollama":
            # Try to connect to Ollama
            try:
                import requests
                response = requests.get(f"{OLLAMA_BASE_URL.replace('/v1', '')}/api/tags", timeout=2)
                if response.status_code == 200:
                    return True, "Ollama running"
            except Exception:
                return False, "Ollama not running or not accessible"
        
        elif DEFAULT_PROVIDER == "openai":
            if os.getenv("OPENAI_API_KEY"):
                return True, "OpenAI API key set"
            return False, "OPENAI_API_KEY not set"
        
        elif DEFAULT_PROVIDER == "azure":
            if os.getenv("AZURE_OPENAI_API_KEY"):
                return True, "Azure OpenAI API key set"
            return False, "AZURE_OPENAI_API_KEY not set"
        
        return True, "No check needed"

    @staticmethod
    def _check_output_dir() -> Tuple[bool, str]:
        """Check if output directory is writable."""
        output_dir = Path(__file__).parent.parent / "outputs"
        try:
            output_dir.mkdir(exist_ok=True)
            test_file = output_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            return True, str(output_dir)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def print_report(checks: List[Tuple[str, bool, str]]):
        """Print a formatted report of checks."""
        print("\n🏥 Story-to-Video System Check\n")
        print("=" * 70)
        
        all_pass = True
        for name, passed, detail in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {name:<35} {detail}")
            if not passed:
                all_pass = False
        
        print("=" * 70)
        
        if all_pass:
            print("\n✨ All checks passed! Ready to create videos.\n")
        else:
            print("\n⚠️  Some checks failed. Install missing dependencies.\n")
        
        return all_pass
