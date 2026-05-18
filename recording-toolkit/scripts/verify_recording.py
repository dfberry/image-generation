"""verify_recording.py — Check if a recorded MP4 contains meaningful visual content.

Checks:
  1. Too short  — duration under --min-duration (default: 5s)
  2. All blank  — average pixel value below --threshold (default: 15/255) across all samples
  3. Frozen     — all sampled frames near-identical via pixel diff (--similarity-threshold)

Exits 0 on PASS, 1 on FAIL.
"""

import argparse
import json
import os
import sys

try:
    import cv2
    import numpy as np
except ImportError:
    print("Error: opencv-python is required. Install: pip install opencv-python", file=sys.stderr)
    sys.exit(1)


def sample_frames(cap: cv2.VideoCapture, n_samples: int):
    """Sample N frames evenly distributed across the video.

    Returns (frames, total_frames, fps, width, height, duration).
    frames is a list of (frame_index, ndarray).
    """
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps

    if total_frames <= 0:
        return [], total_frames, fps, width, height, duration

    count = min(n_samples, total_frames)
    step = total_frames / count
    positions = [int(i * step) for i in range(count)]

    frames = []
    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if ret:
            frames.append((pos, frame))

    return frames, total_frames, fps, width, height, duration


def frame_intensities(frames: list) -> list:
    """Return list of (frame_idx, avg_pixel) for each sampled frame."""
    results = []
    for pos, frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg = float(np.mean(gray))
        results.append((pos, avg))
    return results


def count_unique_frames(frames: list, similarity_threshold: float) -> tuple:
    """Count unique frames using sequential pixel-diff comparison.

    Two adjacent frames are considered identical when their normalised mean
    absolute difference produces similarity >= similarity_threshold.

    Returns (unique_count, duplicate_pairs).
    duplicate_pairs is a list of (prev_idx, curr_idx, similarity).
    """
    if len(frames) < 2:
        return len(frames), []

    unique_count = 1
    duplicate_pairs = []
    prev_gray = cv2.cvtColor(frames[0][1], cv2.COLOR_BGR2GRAY).astype(np.float32)

    for i in range(1, len(frames)):
        curr_gray = cv2.cvtColor(frames[i][1], cv2.COLOR_BGR2GRAY).astype(np.float32)
        norm_diff = np.abs(prev_gray - curr_gray).mean() / 255.0
        similarity = 1.0 - norm_diff

        if similarity >= similarity_threshold:
            duplicate_pairs.append((frames[i - 1][0], frames[i][0], round(similarity, 4)))
        else:
            unique_count += 1

        prev_gray = curr_gray

    return unique_count, duplicate_pairs


def verify(
    video_path: str,
    n_samples: int = 10,
    blank_threshold: float = 15.0,
    similarity_threshold: float = 0.98,
    min_duration: float = 5.0,
    verbose: bool = False,
) -> dict:
    """Run all verification checks on a video file.

    Returns a result dict with a top-level 'pass' boolean.
    """
    if not os.path.isfile(video_path):
        return {
            "pass": False,
            "file": video_path,
            "error": f"File not found: {video_path}",
            "failures": ["file_not_found"],
            "warnings": [],
        }

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "pass": False,
            "file": video_path,
            "error": f"Cannot open video: {video_path}",
            "failures": ["cannot_open"],
            "warnings": [],
        }

    try:
        frames, total_frames, fps, width, height, duration = sample_frames(cap, n_samples)
    finally:
        cap.release()

    failures = []
    warnings = []

    # --- Check 1: Too short ---
    if duration < min_duration:
        failures.append(
            f"too_short: {duration:.1f}s is under the {min_duration}s minimum"
        )

    # --- Check 2: All blank/black ---
    intensities = frame_intensities(frames)
    blank = [(pos, avg) for pos, avg in intensities if avg < blank_threshold]
    blank_pct = (len(blank) / len(frames) * 100) if frames else 100.0

    if len(blank) == len(frames) and frames:
        failures.append(
            f"all_blank: all {len(frames)} sampled frames have avg pixel < {blank_threshold}"
        )
    elif blank_pct >= 50:
        warnings.append(
            f"{blank_pct:.0f}% of sampled frames appear blank (avg pixel < {blank_threshold})"
        )

    # --- Check 3: Frozen/static ---
    unique_count, duplicate_pairs = count_unique_frames(frames, similarity_threshold)
    frozen_pct = ((len(frames) - unique_count) / len(frames) * 100) if frames else 100.0

    if unique_count <= 1 and len(frames) > 1:
        failures.append(
            f"frozen: all {len(frames)} sampled frames are near-identical "
            f"(similarity >= {similarity_threshold})"
        )
    elif frozen_pct >= 50:
        warnings.append(
            f"{frozen_pct:.0f}% of sampled frames appear identical "
            f"(similarity >= {similarity_threshold})"
        )

    result = {
        "pass": len(failures) == 0,
        "file": video_path,
        "duration_seconds": round(duration, 2),
        "total_frames": total_frames,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 2),
        "samples_taken": len(frames),
        "unique_frames_in_sample": unique_count,
        "failures": failures,
        "warnings": warnings,
    }

    if verbose:
        result["frame_intensities"] = [
            {"frame": pos, "avg_pixel": round(avg, 2)}
            for pos, avg in intensities
        ]

    return result


def print_result(result: dict, blank_threshold: float) -> None:
    """Pretty-print a verification result to stdout."""
    verdict = "PASS" if result["pass"] else "FAIL"
    print(f"[verify] {verdict}: {result.get('file', '?')}")

    if "error" in result:
        print(f"  error: {result['error']}")
        return

    print(f"  Duration:    {result['duration_seconds']}s")
    print(f"  Frames:      {result['total_frames']} total, {result['samples_taken']} sampled")
    print(f"  Resolution:  {result['resolution']} @ {result['fps']} fps")
    print(f"  Unique frames in sample: {result['unique_frames_in_sample']}/{result['samples_taken']}")

    for failure in result.get("failures", []):
        print(f"  \u274c FAIL: {failure}")

    for warning in result.get("warnings", []):
        print(f"  \u26a0\ufe0f  WARN: {warning}")

    if "frame_intensities" in result:
        print("\n  Per-frame intensities:")
        for fi in result["frame_intensities"]:
            status = "blank" if fi["avg_pixel"] < blank_threshold else "ok"
            print(f"    frame {fi['frame']:6d}: avg={fi['avg_pixel']:6.1f}  [{status}]")


def main():
    parser = argparse.ArgumentParser(
        description="Verify a recorded MP4 contains meaningful visual content."
    )
    parser.add_argument("video", help="Path to MP4 video file")
    parser.add_argument(
        "-n", "--samples", type=int, default=10,
        help="Number of frames to sample evenly across the video (default: 10)",
    )
    parser.add_argument(
        "--threshold", type=float, default=15.0,
        help="Avg pixel threshold for blank detection, 0-255 (default: 15)",
    )
    parser.add_argument(
        "--similarity-threshold", type=float, default=0.98,
        help="Similarity threshold for frozen detection, 0-1 (default: 0.98)",
    )
    parser.add_argument(
        "--min-duration", type=float, default=5.0,
        help="Minimum acceptable video duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-frame pixel intensity details",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON (for CI integration)",
    )

    args = parser.parse_args()

    result = verify(
        video_path=args.video,
        n_samples=args.samples,
        blank_threshold=args.threshold,
        similarity_threshold=args.similarity_threshold,
        min_duration=args.min_duration,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_result(result, blank_threshold=args.threshold)

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
