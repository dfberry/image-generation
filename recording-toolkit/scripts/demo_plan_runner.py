"""Plan-driven desktop automation runner — reads JSON plans and drives VS Code + Copilot CLI.

Reads a plan with "type": "desktop", starts record_desktop.py in a background thread,
executes automation steps in sequence, then signals recording to stop.

SECURITY WARNING: Plans can execute arbitrary shell commands. Only run plans from
trusted sources. Do not include PII or secrets in plan files or output paths.
"""

import argparse
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pyautogui

# Import the recording engine from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import record_desktop  # noqa: E402


def find_config(config_path: str = None) -> dict:
    """Load recording-config.json from explicit path or auto-discover."""
    if config_path:
        with open(config_path) as f:
            return json.load(f)
    return record_desktop.find_config()


def preflight_checks(plan: dict, dry_run: bool = False) -> bool:
    """Run pre-flight checks before starting automation.

    Verifies VS Code and Copilot CLI are available.
    In dry-run mode, prints warnings but does not exit.
    """
    issues = []

    # Check VS Code
    if not shutil.which("code"):
        msg = "VS Code (code) not on PATH. Install: winget install Microsoft.VisualStudioCode"
        if dry_run:
            print(f"[warning] {msg}")
        else:
            issues.append(msg)

    # Check Copilot CLI
    copilot_path = shutil.which("copilot")
    if not copilot_path:
        msg = "Copilot CLI (copilot) not on PATH. Install: npm install -g @github/copilot"
        if dry_run:
            print(f"[warning] {msg}")
        else:
            issues.append(msg)

    # Check FFmpeg (needed for recording)
    if not shutil.which("ffmpeg"):
        msg = "FFmpeg not on PATH. Install: winget install ffmpeg"
        if dry_run:
            print(f"[warning] {msg}")
        else:
            issues.append(msg)

    if issues:
        print("Pre-flight check failed:", file=sys.stderr)
        for issue in issues:
            print(f"  ❌ {issue}", file=sys.stderr)
        return False

    return True


def run_step(step: dict, step_log: bool = False):
    """Execute a single automation step.

    Dispatches on step["action"] and sleeps for step.get("wait", 0) after.
    """
    action = step["action"]
    wait = step.get("wait", 0)

    if step_log:
        print(f"  [step] {action}: {step}")

    if action == "launch":
        # Start an application via subprocess
        program = step["program"]
        args = step.get("args", [])
        try:
            subprocess.Popen([program] + args)
        except FileNotFoundError:
            raise RuntimeError(f"Cannot launch '{program}' — not found on PATH")

    elif action == "hotkey":
        # Send a key combination (e.g., ["ctrl", "`"])
        pyautogui.hotkey(*step["keys"])

    elif action == "type":
        # Type text character-by-character with interval delay
        interval = step.get("interval", 0.04)
        pyautogui.typewrite(step["text"], interval=interval)

    elif action == "press":
        # Press a single key (e.g., "enter", "tab")
        pyautogui.press(step["key"])

    elif action == "click":
        # Left-click at screen coordinates
        pyautogui.click(step["x"], step["y"])

    elif action == "right_click":
        # Right-click at screen coordinates
        pyautogui.click(step["x"], step["y"], button='right')

    elif action == "move":
        # Move mouse to coordinates
        duration = step.get("duration", 0.5)
        pyautogui.moveTo(step["x"], step["y"], duration=duration)

    elif action == "scroll":
        # Scroll wheel at coordinates
        pyautogui.scroll(step["clicks"], x=step["x"], y=step["y"])

    elif action == "pause":
        # No-op — wait handles the delay
        pass

    elif action == "screenshot":
        # Save a checkpoint screenshot (debug aid)
        filename = step.get("filename", f"checkpoint-{int(time.time())}.png")
        # Validate screenshot path stays local
        resolved_screenshot = pathlib.Path(filename).resolve()
        cwd = pathlib.Path.cwd().resolve()
        try:
            resolved_screenshot.relative_to(cwd)
        except ValueError:
            print(f"Error: screenshot path '{filename}' escapes working directory", file=sys.stderr)
            return
        screenshot = pyautogui.screenshot()
        screenshot.save(str(resolved_screenshot))
        if step_log:
            print(f"    [screenshot] saved: {filename}")

    else:
        print(f"[warning] Unknown action: {action}", file=sys.stderr)

    # Post-action wait
    if wait > 0:
        time.sleep(wait)


def build_output_path(plan: dict, output_dir: str = None) -> str:
    """Build output MP4 path from plan name + timestamp."""
    name = plan.get("name", "recording")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    subdir = plan.get("output", {}).get("subdir", "desktop")
    base_dir = output_dir or os.path.join("recordings", subdir)
    resolved = pathlib.Path(base_dir).resolve()
    safe_root = pathlib.Path("recordings").resolve()
    try:
        resolved.relative_to(safe_root)
    except ValueError:
        sys.exit(f"Error: output directory '{base_dir}' escapes recordings/ directory")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, f"{name}-{timestamp}.mp4")


def resolve_capture_region(plan: dict, preset_settings: dict = None) -> dict:
    """Resolve the capture region from plan capture config."""
    capture = plan.get("capture", {})
    mode = capture.get("mode", "full")

    if mode == "region" and "region" in capture:
        r = capture["region"]
        return {"left": r[0], "top": r[1], "width": r[2], "height": r[3]}

    # Use resolution from plan > preset > default
    resolution = capture.get("resolution")
    if not resolution and preset_settings:
        resolution = preset_settings.get("resolution")
    if not resolution:
        resolution = [1920, 1080]

    return {"top": 0, "left": 0, "width": resolution[0], "height": resolution[1]}


def run_plan(plan_path: str, dry_run: bool = False, output_override: str = None,
             no_record: bool = False, config_path: str = None, preset_name: str = None,
             step_log: bool = False):
    """Execute a desktop recording plan end-to-end."""
    # Load plan
    with open(plan_path) as f:
        plan = json.load(f)

    # Validate type
    plan_type = plan.get("type", "terminal")
    if plan_type != "desktop":
        print(f'Error: This runner only handles "type": "desktop" plans.', file=sys.stderr)
        print(f'Got "type": "{plan_type}" in {plan_path}', file=sys.stderr)
        sys.exit(1)

    # Pre-flight checks
    if not preflight_checks(plan, dry_run=dry_run):
        sys.exit(1)

    # Load config and preset
    config = find_config(config_path)
    desktop_cfg = config.get("desktop", {})
    presets = desktop_cfg.get("presets", {})
    preset_settings = {}
    if preset_name:
        if preset_name not in presets:
            print(f"Error: preset '{preset_name}' not found.", file=sys.stderr)
            sys.exit(1)
        preset_settings = presets[preset_name]

    # Resolve capture settings
    capture = plan.get("capture", {})
    fps = capture.get("fps") or preset_settings.get("fps") or desktop_cfg.get("defaults", {}).get("fps", 30)
    region = resolve_capture_region(plan, preset_settings)

    # Run pre_record commands
    pre_record = plan.get("pre_record", {})
    for cmd in pre_record.get("commands", []):
        if dry_run:
            print(f"[dry-run] pre_record: {cmd}")
        else:
            if step_log:
                print(f"  [pre_record] {cmd}")
            subprocess.run(shlex.split(cmd), check=True)

    # Determine output path
    output_dir = desktop_cfg.get("defaults", {}).get("output_dir")
    output_path = output_override or build_output_path(plan, output_dir)

    if dry_run:
        print(f"\n[dry-run] Output: {output_path}")
        print(f"[dry-run] Region: {region}")
        print(f"[dry-run] FPS: {fps}")
        print(f"\n[dry-run] Steps ({len(plan.get('steps', []))}):")
        for i, step in enumerate(plan.get("steps", []), 1):
            print(f"  {i}. {step}")
        return

    # Start recording in background thread (unless --no-record)
    stop_event = threading.Event()
    record_thread = None
    if not no_record:
        encoder = preset_settings.get("encoder") or desktop_cfg.get("defaults", {}).get("encoder", "auto")
        record_thread = threading.Thread(
            target=record_desktop.record,
            args=(output_path, region, fps),
            kwargs={"stop_event": stop_event, "encoder": encoder},
        )
        record_thread.start()
        time.sleep(0.5)  # Brief pause to let FFmpeg initialize

    # Execute automation steps
    try:
        for step in plan.get("steps", []):
            run_step(step, step_log=step_log)
    except Exception as e:
        print(f"[error] Step failed: {e}", file=sys.stderr)
        stop_event.set()
        if record_thread:
            record_thread.join(timeout=10)
        sys.exit(1)

    # Signal stop and wait for encoding to finish
    stop_event.set()
    if record_thread:
        record_thread.join(timeout=30)
        print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Plan-driven desktop automation + recording runner."
    )
    parser.add_argument("plan", help="Path to desktop recording plan JSON")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    parser.add_argument("-o", "--output", default=None, help="Override output MP4 path")
    parser.add_argument("--no-record", action="store_true", help="Run automation without recording")
    parser.add_argument("-c", "--config", default=None, help="Path to recording-config.json")
    parser.add_argument("--preset", default=None, help="Override capture preset")
    parser.add_argument("--step-log", action="store_true", help="Print each step as it executes")

    args = parser.parse_args()

    if not os.path.isfile(args.plan):
        print(f"Error: Plan file not found: {args.plan}", file=sys.stderr)
        sys.exit(1)

    run_plan(
        plan_path=args.plan,
        dry_run=args.dry_run,
        output_override=args.output,
        no_record=args.no_record,
        config_path=args.config,
        preset_name=args.preset,
        step_log=args.step_log,
    )


if __name__ == "__main__":
    main()
