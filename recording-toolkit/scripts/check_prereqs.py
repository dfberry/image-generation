"""Environment prerequisites checker for desktop recording.

Validates the full environment before attempting a desktop recording.
Prints a summary table of ✅/❌ for each requirement.
Exits 0 if all pass, 1 if any fail.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add scripts dir to path so we can import detect_encoder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def detect_encoder_check():
    """Import and run detect_encoder from record_desktop."""
    from record_desktop import detect_encoder
    enc_name, _ = detect_encoder()
    return enc_name


def find_recording_config() -> str:
    """Walk up from CWD to find recording-config.json."""
    search = Path.cwd()
    for _ in range(10):
        candidate = search / "recording-toolkit" / "recording-config.json"
        if candidate.exists():
            return str(candidate)
        candidate = search / "recording-config.json"
        if candidate.exists():
            return str(candidate)
        parent = search.parent
        if parent == search:
            break
        search = parent
    return None


def main():
    checks = []

    def check(label, fn):
        try:
            result = fn()
            checks.append(("✅", label, result or "ok"))
        except Exception as e:
            checks.append(("❌", label, str(e)))

    # Python version
    check(
        "Python ≥ 3.10",
        lambda: (
            f"{sys.version_info.major}.{sys.version_info.minor}"
            if sys.version_info >= (3, 10)
            else (_ for _ in ()).throw(RuntimeError("requires 3.10+"))
        ),
    )

    # Python packages
    for pkg in ["pyautogui", "mss", "numpy", "cv2"]:
        check(
            f"pip: {pkg}",
            lambda p=pkg: (
                "installed"
                if importlib.util.find_spec(p)
                else (_ for _ in ()).throw(
                    ImportError(f"pip install {'opencv-python' if p == 'cv2' else p}")
                )
            ),
        )

    # FFmpeg on PATH
    check(
        "ffmpeg on PATH",
        lambda: (
            subprocess.check_output(
                ["ffmpeg", "-version"], stderr=subprocess.STDOUT
            )
            .decode(errors="replace")
            .splitlines()[0]
            if shutil.which("ffmpeg")
            else (_ for _ in ()).throw(
                FileNotFoundError("winget install ffmpeg")
            )
        ),
    )

    # FFmpeg encoder
    check("ffmpeg encoder (auto)", lambda: detect_encoder_check())

    # VS Code
    check(
        "VS Code (code) on PATH",
        lambda: (
            shutil.which("code")
            or (_ for _ in ()).throw(
                FileNotFoundError("winget install Microsoft.VisualStudioCode")
            )
        ),
    )

    # Copilot CLI
    check(
        "Copilot CLI (copilot) on PATH",
        lambda: (
            subprocess.check_output(
                ["copilot", "--version"], stderr=subprocess.STDOUT
            )
            .decode(errors="replace")
            .strip()
            if shutil.which("copilot")
            else (_ for _ in ()).throw(
                FileNotFoundError("npm install -g @github/copilot")
            )
        ),
    )

    # recording-config.json
    config_path = find_recording_config()
    check(
        "recording-config.json",
        lambda: config_path if config_path else (_ for _ in ()).throw(
            FileNotFoundError("not found (non-fatal)")
        ),
    )

    # Print summary table
    print(f"\n{'Status':<8} {'Check':<35} {'Detail'}")
    print("-" * 70)
    for status, label, detail in checks:
        # Truncate long detail lines
        detail_str = str(detail)[:60]
        print(f"{status:<8} {label:<35} {detail_str}")

    failed = [c for c in checks if c[0] == "❌"]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed.")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
