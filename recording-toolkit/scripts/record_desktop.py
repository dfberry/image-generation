"""Desktop screen recording engine — capture + encode via FFmpeg pipe.

CRITICAL IMPORT ORDER:
  1. ctypes DPI call MUST happen before any other imports
  2. mss MUST be imported before pyautogui

This prevents Windows DPI scaling from producing incorrect frame dimensions.
"""

import ctypes
# Set DPI awareness BEFORE importing display-dependent libraries
try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass  # Not on Windows — no DPI fix needed

import mss  # noqa: E402 — must import before pyautogui
import pyautogui  # noqa: E402

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty, Full

import numpy

logger = logging.getLogger("record_desktop")


def find_config() -> dict:
    """Walk up from CWD to find recording-config.json."""
    search = Path.cwd()
    for _ in range(10):
        candidate = search / "recording-toolkit" / "recording-config.json"
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
        candidate = search / "recording-config.json"
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
        parent = search.parent
        if parent == search:
            break
        search = parent
    return {}


def detect_encoder(force: str = None) -> tuple:
    """Probe GPU encoders in priority order, fall back to CPU.

    Returns (encoder_name, extra_flags_list).
    Probe order: h264_nvenc → h264_amf → h264_qsv → libx264
    """
    if force and force != "auto":
        # User explicitly chose an encoder — trust them
        encoder_flags = {
            "h264_nvenc": ["-preset", "p4", "-cq", "23"],
            "h264_amf": ["-quality", "speed", "-qp_i", "23"],
            "h264_qsv": ["-preset", "fast", "-global_quality", "23"],
            "libx264": ["-preset", "ultrafast", "-crf", "23"],
        }
        flags = encoder_flags.get(force, ["-preset", "ultrafast", "-crf", "23"])
        return force, flags

    candidates = [
        ("h264_nvenc", ["-preset", "p4", "-cq", "23"]),
        ("h264_amf", ["-quality", "speed", "-qp_i", "23"]),
        ("h264_qsv", ["-preset", "fast", "-global_quality", "23"]),
        ("libx264", ["-preset", "ultrafast", "-crf", "23"]),
    ]
    for encoder, flags in candidates:
        try:
            probe = subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "nullsrc=s=1280x720:d=1",
                    "-vcodec", encoder, "-t", "1", "-f", "null", os.devnull,
                ],
                capture_output=True,
                timeout=10,
            )
            if probe.returncode == 0:
                print(f"[record_desktop] Using encoder: {encoder}", file=sys.stderr)
                return encoder, flags
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    raise RuntimeError(
        "No supported H.264 encoder found. Install FFmpeg with libx264:\n"
        "  winget install ffmpeg"
    )


def capture_thread(queue: Queue, region: dict, fps: int, stop_event: threading.Event,
                   verbose: bool = False, stats: dict = None):
    """Capture frames at drift-compensated intervals and push to queue.

    Uses fixed-interval timing: next_frame = start + (frame_count / fps)
    This prevents cumulative drift from naive sleep(1/fps).
    """
    with mss.mss() as sct:
        start = time.perf_counter()
        frame_count = 0
        dropped = 0
        while not stop_event.is_set():
            next_frame_time = start + (frame_count / fps)
            lag = next_frame_time - time.perf_counter()
            if lag > 0:
                time.sleep(lag)

            frame = numpy.array(sct.grab(region))
            try:
                queue.put(frame, block=True, timeout=0.5)
            except (Full,):
                dropped += 1  # Queue full — drop frame rather than block forever

            frame_count += 1

            if verbose and frame_count % fps == 0:
                elapsed = time.perf_counter() - start
                logger.debug(f"[capture] {frame_count} frames in {elapsed:.1f}s (dropped: {dropped})")

        elapsed = time.perf_counter() - start
        if stats is not None:
            stats["frame_count"] = frame_count
            stats["elapsed"] = elapsed
        logger.debug(
            f"[capture] done: {frame_count} frames in {elapsed:.1f}s, dropped: {dropped}"
        )


def encode_thread(queue: Queue, ffmpeg_proc: subprocess.Popen, stop_event: threading.Event):
    """Read frames from queue and write raw BGRA bytes to FFmpeg stdin.

    Drains the queue after stop_event is set to ensure all captured frames are encoded.
    """
    while not stop_event.is_set() or not queue.empty():
        try:
            frame = queue.get(timeout=1.0)
        except Empty:
            continue
        try:
            ffmpeg_proc.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError):
            # FFmpeg crashed — signal stop
            print("[record_desktop] FFmpeg pipe broken — stopping", file=sys.stderr)
            stop_event.set()
            break


def build_ffmpeg_cmd(encoder: str, flags: list, output_path: str, width: int, height: int, fps: int) -> list:
    """Build the FFmpeg command for raw BGRA stdin pipe encoding."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgra",
        "-r", str(fps),
        "-i", "pipe:0",
        "-vcodec", encoder,
    ]
    cmd.extend(flags)
    cmd.extend([
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])
    return cmd


def record(output_path: str, region: dict, fps: int = 30, duration: float = None,
           stop_event: threading.Event = None, encoder: str = None, queue_size: int = 120,
           verbose: bool = False, ready_event: threading.Event = None):
    """Public API: capture screen region and encode to MP4.

    Args:
        output_path: Destination MP4 file path.
        region: mss monitor dict with top, left, width, height.
        fps: Frames per second.
        duration: Max seconds to record (None = until stop_event is set).
        stop_event: External threading.Event to signal stop.
        encoder: Force encoder name or None for auto-detect.
        queue_size: Frame buffer depth.
        verbose: Print per-second timing stats.
        ready_event: Optional threading.Event set after capture thread starts
            (after lead-in frames). Callers can wait on this instead of
            using a fixed sleep to ensure capture is genuinely active.
    """
    enc_name, enc_flags = detect_encoder(encoder)
    width = region["width"]
    height = region["height"]

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid region: width={width}, height={height} must be positive")
    if region["left"] < 0 or region["top"] < 0:
        raise ValueError(f"Invalid region: left={region['left']}, top={region['top']} must be non-negative")

    logger.info(f"[record] Starting: {output_path}, {width}x{height} @ {fps}fps, encoder={enc_name}")

    ffmpeg_cmd = build_ffmpeg_cmd(enc_name, enc_flags, output_path, width, height, fps)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # Drain FFmpeg stderr in a background thread to prevent buffer deadlock
    stderr_lines: list = []

    def _read_stderr():
        for raw_line in ffmpeg_proc.stderr:
            stderr_lines.append(raw_line.decode(errors="replace"))

    t_stderr = threading.Thread(target=_read_stderr, daemon=True)
    t_stderr.start()

    if stop_event is None:
        stop_event = threading.Event()

    # Lead-in: 3 seconds of black (BGRA) frames written directly to FFmpeg stdin
    lead_frames = fps * 3
    logger.info(f"[record] Writing {lead_frames} lead-in frames (3s black)")
    black_frame = numpy.zeros((height, width, 4), dtype=numpy.uint8)
    black_bytes = black_frame.tobytes()
    for _ in range(lead_frames):
        try:
            ffmpeg_proc.stdin.write(black_bytes)
        except (BrokenPipeError, OSError):
            break

    q = Queue(maxsize=queue_size)
    capture_stats: dict = {}

    t_capture = threading.Thread(
        target=capture_thread,
        args=(q, region, fps, stop_event, verbose),
        kwargs={"stats": capture_stats},
        daemon=True,
    )
    t_encode = threading.Thread(
        target=encode_thread,
        args=(q, ffmpeg_proc, stop_event),
        daemon=True,
    )

    logger.info("[record] Capture started")
    t_capture.start()
    t_encode.start()

    # Signal caller that capture is now actively running
    if ready_event is not None:
        ready_event.set()

    if duration:
        time.sleep(duration)
        stop_event.set()

    t_capture.join()
    elapsed = capture_stats.get("elapsed", 0.0)
    frame_count = capture_stats.get("frame_count", 0)
    logger.info(f"[record] Capture stopped after {elapsed:.1f}s, {frame_count} frames")

    # Signal encode thread to drain remaining queued frames and exit
    stop_event.set()
    t_encode.join()

    # Lead-out: 3 seconds of black frames
    lead_frames = fps * 3
    logger.info(f"[record] Writing {lead_frames} lead-out frames (3s black)")
    for _ in range(lead_frames):
        try:
            ffmpeg_proc.stdin.write(black_bytes)
        except (BrokenPipeError, OSError):
            break

    logger.info("[record] FFmpeg stdin closed, waiting for process...")
    try:
        ffmpeg_proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass  # Pipe already closed by FFmpeg crash — handled in encode_thread

    ffmpeg_proc.wait()
    t_stderr.join(timeout=5)

    stderr_text = "".join(stderr_lines)
    logger.info(f"[record] FFmpeg exited with code {ffmpeg_proc.returncode}")
    logger.info(f"[record] FFmpeg stderr: {stderr_text[-1000:]}")

    if ffmpeg_proc.returncode != 0:
        partial_path = output_path.replace(".mp4", f"-PARTIAL-{int(time.time())}.mp4")
        if os.path.exists(output_path):
            os.rename(output_path, partial_path)
        raise RuntimeError(f"FFmpeg failed with exit code {ffmpeg_proc.returncode}")

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0.0
    logger.info(f"[record] Done: {output_path} ({file_size_mb:.1f} MB)")


def resolve_region(region_str: str = None, resolution_str: str = None) -> dict:
    """Build an mss region dict from CLI args or defaults to primary monitor."""
    if region_str:
        parts = [int(x) for x in region_str.split(",")]
        if len(parts) != 4:
            raise ValueError("--region must be x,y,w,h (4 integers)")
        return {"top": parts[1], "left": parts[0], "width": parts[2], "height": parts[3]}

    if resolution_str:
        w, h = [int(x) for x in resolution_str.lower().split("x")]
        return {"top": 0, "left": 0, "width": w, "height": h}

    # Default: full primary monitor
    with mss.mss() as sct:
        mon = sct.monitors[1]  # Primary monitor (monitors[0] is "all")
        return {"top": mon["top"], "left": mon["left"], "width": mon["width"], "height": mon["height"]}


def main():
    parser = argparse.ArgumentParser(
        description="Desktop screen recording engine — capture + encode to MP4 via FFmpeg pipe."
    )
    parser.add_argument("-o", "--output", required=True, help="Output MP4 file path")
    parser.add_argument("-f", "--fps", type=int, default=None, help="Frames per second (default: 30)")
    parser.add_argument("-d", "--duration", type=float, default=None, help="Max recording duration in seconds")
    parser.add_argument("-r", "--region", default=None, help="Capture region: x,y,w,h")
    parser.add_argument("--resolution", default=None, help="Override capture size: WxH (e.g., 1280x720)")
    parser.add_argument("-e", "--encoder", default=None, help="Force encoder (h264_nvenc, h264_amf, h264_qsv, libx264)")
    parser.add_argument("-p", "--preset", default=None, help="Named preset from recording-config.json")
    parser.add_argument("-c", "--config", default=None, help="Path to recording-config.json")
    parser.add_argument("--queue-size", type=int, default=None, help="Frame queue buffer depth (default: 120)")
    parser.add_argument("--dry-run", action="store_true", help="Print FFmpeg command and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print per-frame timing stats")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )

    # Load config
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        config = find_config()

    desktop_cfg = config.get("desktop", {})
    defaults = desktop_cfg.get("defaults", {})
    presets = desktop_cfg.get("presets", {})

    # Apply preset (if specified)
    preset_settings = {}
    if args.preset:
        if args.preset not in presets:
            print(f"Error: preset '{args.preset}' not found. Available: {list(presets.keys())}", file=sys.stderr)
            sys.exit(1)
        preset_settings = presets[args.preset]

    # Resolve settings: CLI > preset > config defaults > built-in
    fps = args.fps or preset_settings.get("fps") or defaults.get("fps", 30)
    encoder = args.encoder or preset_settings.get("encoder") or defaults.get("encoder", "auto")
    queue_size = args.queue_size or defaults.get("queue_size", 120)

    # Resolve region/resolution
    if args.region:
        region = resolve_region(region_str=args.region)
    elif args.resolution:
        region = resolve_region(resolution_str=args.resolution)
    elif "resolution" in preset_settings:
        res = preset_settings["resolution"]
        region = {"top": 0, "left": 0, "width": res[0], "height": res[1]}
    elif "resolution" in defaults:
        res = defaults["resolution"]
        region = {"top": 0, "left": 0, "width": res[0], "height": res[1]}
    else:
        region = resolve_region()

    # Dry-run: print FFmpeg command and exit
    if args.dry_run:
        try:
            enc_name, enc_flags = detect_encoder(encoder)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        cmd = build_ffmpeg_cmd(enc_name, enc_flags, args.output, region["width"], region["height"], fps)
        print("[dry-run] FFmpeg command:")
        print(" ".join(cmd))
        print(f"\n[dry-run] Region: {region}")
        print(f"[dry-run] FPS: {fps}, Encoder: {enc_name}, Queue: {queue_size}")
        sys.exit(0)

    # Run recording
    stop_event = threading.Event()
    try:
        record(
            output_path=args.output,
            region=region,
            fps=fps,
            duration=args.duration,
            stop_event=stop_event,
            encoder=encoder,
            queue_size=queue_size,
            verbose=args.verbose,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        stop_event.set()
        print("\n[record_desktop] Interrupted — finalizing...", file=sys.stderr)


if __name__ == "__main__":
    main()
