#!/usr/bin/env python3
"""simple_config.py — User-friendly CLI wrapper for generate.py.

Translates plain-English quality/style/size terms into SDXL parameters,
then delegates to generate.py via subprocess.run.

Usage:
  python simple_config.py "a sunset over mountains" --preset quick-draft --seed 42
  python simple_config.py --prompt "a developer at a desk" --preset production \\
    --style watercolor --size blog-hero --output hero.png
  python simple_config.py --preset standard --dry-run
  python simple_config.py --preset production --style watercolor --batch-file jobs.json
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

from presets import (
    MODIFIERS,
    PRESETS,
    PROMPT_TEMPLATES,
    SIZES,
    STYLES,
    apply_modifier,
    apply_style_tokens,
    check_guidance_warning,
    check_vague_colors,
    estimate_tokens,
    resolve_preset,
)

_GENERATE_PY = Path(__file__).parent / "generate.py"
_DEFAULT_PRESET = "standard"
_DEFAULT_NEGATIVE_PROMPT = (
    "text, letters, words, no text, no letters, no words, no writing, "
    "watermark, signature, blurry, low quality, distorted"
)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simple_config.py",
        description=(
            "User-friendly wrapper for generate.py.\n"
            "Translates plain-English terms (preset/style/size) to SDXL parameters."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Quick draft
  python simple_config.py "a glowing tropical garden" --preset quick-draft --seed 42

  # Production watercolor blog hero
  python simple_config.py --prompt "a developer at a desk, warm light, no text" \\
    --preset production --style watercolor --size blog-hero --output outputs/hero.png --cpu

  # Dry run to preview resolved parameters
  python simple_config.py --preset production --style watercolor --dry-run

  # Batch processing
  python simple_config.py --preset production --style watercolor --batch-file jobs.json --dry-run
""",
    )

    # Prompt: positional (convenience) or named --prompt (canonical)
    parser.add_argument(
        "pos_prompt",
        nargs="?",
        default=None,
        metavar="PROMPT",
        help="Text prompt (positional shorthand; use --prompt for named form)",
    )
    parser.add_argument(
        "--prompt",
        dest="named_prompt",
        default=None,
        metavar="TEXT",
        help="Text prompt for image generation",
    )

    # Quality / preset
    parser.add_argument(
        "--preset",
        "--quality",
        dest="preset",
        default=_DEFAULT_PRESET,
        choices=list(PRESETS),
        metavar="PRESET",
        help=f"Quality preset: {', '.join(PRESETS)} (default: {_DEFAULT_PRESET})",
    )

    # Modifiers (repeatable)
    parser.add_argument(
        "--modifier",
        action="append",
        dest="modifiers",
        default=None,
        metavar="MODIFIER",
        help=(
            "Adjust parameters on top of preset (repeatable). "
            f"Choices: {', '.join(sorted(MODIFIERS))}"
        ),
    )

    # Style
    parser.add_argument(
        "--style",
        default=None,
        choices=list(STYLES) + ["none"],
        metavar="STYLE",
        help=f"Style preset: {', '.join(STYLES)}, none",
    )
    parser.add_argument(
        "--no-default-style",
        action="store_true",
        dest="no_default_style",
        help="Suppress folk-art default style tokens (same as --style none)",
    )

    # Size
    parser.add_argument(
        "--size",
        default=None,
        choices=list(SIZES),
        metavar="SIZE",
        help=f"Image size preset: {', '.join(SIZES)}",
    )

    # Passthrough args forwarded to generate.py
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode (slow, no GPU required)")
    parser.add_argument(
        "--model",
        default=None,
        choices=["creative", "precise", "balanced"],
        help="Model override (overrides any modifier-applied model)",
    )
    parser.add_argument(
        "--negative-prompt",
        dest="negative_prompt",
        default=None,
        help="Negative prompt override",
    )
    parser.add_argument(
        "--lora",
        default=None,
        help="LoRA model ID — overrides the style's default LoRA",
    )
    parser.add_argument(
        "--lora-weight",
        type=float,
        dest="lora_weight",
        default=None,
        help="LoRA adapter weight (default: 0.8)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Image width override in pixels (must be divisible by 8)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Image height override in pixels (must be divisible by 8)",
    )

    # simple_config.py control flags
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print resolved generate.py command without executing",
    )
    parser.add_argument(
        "--assist",
        "--prompt-help",
        action="store_true",
        dest="assist",
        help="Pre-flight prompt engineering assistance (token check, style preview, suggestions)",
    )
    parser.add_argument(
        "--template",
        default=None,
        choices=list(PROMPT_TEMPLATES),
        help="Prompt scaffold template (requires --assist)",
    )
    parser.add_argument(
        "--batch-file",
        dest="batch_file",
        default=None,
        metavar="PATH",
        help="JSON file with array of generation jobs",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------


def _effective_prompt(args: argparse.Namespace) -> str:
    """Return the final user-supplied prompt text (before style injection)."""
    return args.named_prompt if args.named_prompt is not None else (args.pos_prompt or "")


def resolve_base_params(args: argparse.Namespace) -> dict:
    """Resolve preset + modifiers + size + passthrough args (no style tokens yet).

    Style token injection is done separately so batch jobs can each get their
    own prompt with shared style applied.
    """
    params = resolve_preset(args.preset)

    for mod_name in args.modifiers or []:
        if mod_name not in MODIFIERS:
            print(
                f"[simple_config] ❌ Unknown modifier '{mod_name}'. "
                f"Available: {', '.join(sorted(MODIFIERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        apply_modifier(params, mod_name)

    # Print any guidance warnings after all modifiers are applied
    for warning in check_guidance_warning(params):
        print(warning, file=sys.stderr)

    # CLI --model takes highest priority over modifier-applied model
    if args.model:
        params["model"] = args.model

    # Size resolution
    params["width"] = 1024
    params["height"] = 1024
    if args.size:
        params.update(SIZES[args.size])
    if args.width is not None:
        params["width"] = args.width
    if args.height is not None:
        params["height"] = args.height

    # Passthrough args
    params["seed"] = args.seed
    params["output"] = args.output
    params["cpu"] = args.cpu
    params["negative_prompt"] = args.negative_prompt

    return params


def apply_prompt_and_style(
    base_params: dict,
    prompt: str,
    style: str | None,
    no_default_style: bool,
    lora_override: str | None,
    lora_weight_override: float | None,
) -> dict:
    """Apply style tokens to prompt and set LoRA params. Returns a new param dict."""
    params = dict(base_params)

    effective_style = None if (style is None or style.lower() == "none") else style
    no_default = no_default_style or (style is not None and style.lower() == "none")

    final_prompt, style_lora, style_lora_weight, passthrough_style = apply_style_tokens(
        prompt,
        effective_style,
        no_default_style=no_default,
    )
    params["prompt"] = final_prompt

    # LoRA: explicit CLI --lora takes highest priority over style default
    if lora_override:
        params["lora"] = lora_override
        params["lora_weight"] = lora_weight_override if lora_weight_override is not None else 0.8
    elif style_lora:
        params["lora"] = style_lora
        params["lora_weight"] = style_lora_weight if style_lora_weight is not None else 0.8
    else:
        params["lora"] = None
        params["lora_weight"] = 0.8

    if passthrough_style:
        params["style_passthrough"] = passthrough_style

    return params


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------


def build_generate_cmd(params: dict) -> list[str]:
    """Convert a resolved params dict to a generate.py CLI arg list.

    Omits args that match generate.py defaults to keep the command concise.
    """
    cmd = [sys.executable, str(_GENERATE_PY)]

    if params.get("prompt"):
        cmd += ["--prompt", params["prompt"]]

    # Core inference params (always include steps + guidance)
    cmd += ["--steps", str(params["steps"])]
    cmd += ["--guidance", str(params["guidance"])]

    if params.get("refine"):
        cmd.append("--refine")

    # Omit --refiner-steps if it matches generate.py default (10)
    refiner_steps = params.get("refiner_steps", 10)
    if refiner_steps != 10:
        cmd += ["--refiner-steps", str(refiner_steps)]

    # Omit --refiner-guidance if it matches generate.py default (5.0)
    refiner_guidance = params.get("refiner_guidance", 5.0)
    if refiner_guidance != 5.0:
        cmd += ["--refiner-guidance", str(refiner_guidance)]

    # LoRA
    if params.get("lora"):
        cmd += ["--lora", params["lora"]]
        cmd += ["--lora-weight", str(params.get("lora_weight", 0.8))]

    # Passthrough style (for styles like oil-painting, sketch, anime)
    if params.get("style_passthrough"):
        cmd += ["--style", params["style_passthrough"]]

    # Dimensions — omit if square (1024×1024, the generate.py defaults)
    width = params.get("width", 1024)
    height = params.get("height", 1024)
    if width != 1024 or height != 1024:
        cmd += ["--width", str(width), "--height", str(height)]

    # Model override (only if set — None means use generate.py default)
    if params.get("model"):
        cmd += ["--model", params["model"]]

    # Scheduler (only if non-default)
    scheduler = params.get("scheduler", "DPMSolverMultistepScheduler")
    if scheduler != "DPMSolverMultistepScheduler":
        cmd += ["--scheduler", scheduler]

    # Passthrough args
    if params.get("seed") is not None:
        cmd += ["--seed", str(params["seed"])]
    if params.get("output"):
        cmd += ["--output", params["output"]]
    if params.get("negative_prompt"):
        cmd += ["--negative-prompt", params["negative_prompt"]]
    if params.get("cpu"):
        cmd.append("--cpu")

    return cmd


# ---------------------------------------------------------------------------
# Prompt assist
# ---------------------------------------------------------------------------

_LIGHTING_WORDS = frozenset(
    "light lighting morning afternoon evening sunset sunrise glow bright dark shadow dusk dawn".split()
)


def run_assist(params: dict, args: argparse.Namespace) -> dict:
    """Run prompt engineering checks; modifies params['prompt'] as needed.

    Interactive when a TTY is detected; applies silent safe defaults otherwise.
    (See OQ-7, OQ-10 in prd-wrapper-core.md.)
    """
    is_interactive = sys.stdin.isatty()
    prompt = params.get("prompt", "")
    raw_prompt = _effective_prompt(args)

    # Template handling (--assist --template)
    if args.template and not raw_prompt:
        scaffold = PROMPT_TEMPLATES[args.template]
        print(f"\n[assist] Prompt template ({args.template}):\n  {scaffold}")
        if is_interactive:
            resp = input("  → Use this as your starting prompt? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                params["prompt"] = scaffold
                prompt = scaffold
        return params

    if not prompt:
        return params

    # "no text" enforcement
    if "no text" not in prompt.lower():
        if is_interactive:
            print('\n[assist] "no text" rule not detected in your prompt.')
            resp = input('  Suggestion: append ", no text". → Apply? [Y/n]: ').strip().lower()
            if resp in ("", "y", "yes"):
                params["prompt"] = prompt.rstrip(" ,") + ", no text"
                prompt = params["prompt"]
        else:
            params["prompt"] = prompt.rstrip(" ,") + ", no text"
            prompt = params["prompt"]

    # Negative prompt auto-add
    if not params.get("negative_prompt"):
        if is_interactive:
            print(f'\n[assist] Negative prompt will be applied automatically:\n  "{_DEFAULT_NEGATIVE_PROMPT}"')
            resp = input("  → Accept? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT
        else:
            params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT

    # Token count check
    token_count = estimate_tokens(prompt)
    print(f"\n[assist] Token check: {token_count} / 77 CLIP limit. ", end="")
    if token_count < 60:
        print("✅ OK.")
    elif token_count < 77:
        print(f"⚠️  {token_count} tokens — consider trimming to under 60.")
        if is_interactive:
            input("  → Press Enter to continue... ")
    else:
        print(f"❌ {token_count} tokens — prompt will be truncated by SDXL's text encoder.")
        if is_interactive:
            resp = input("  → Proceed anyway? [y/N]: ").strip().lower()
            if resp not in ("y", "yes"):
                sys.exit(1)

    # Color specificity suggestion
    vague = check_vague_colors(raw_prompt)
    if vague:
        print(f"\n[assist] Vague color words detected: {', '.join(vague)}")
        print("  Suggestion: use specifics like 'bright cobalt blue', 'deep crimson red', etc.")

    # Scene expansion suggestion
    raw_words = raw_prompt.split()
    has_lighting = any(w.lower() in _LIGHTING_WORDS for w in raw_words)
    if len(raw_words) < 8 and not has_lighting:
        suggestion = raw_prompt.rstrip(" ,") + ", warm afternoon light"
        print('\n[assist] Scene suggestion: minimal prompt detected (no lighting cues).')
        print(f'  Suggested expansion: "{suggestion}"')
        if is_interactive:
            resp = input("  → Use suggestion? [Y/n]: ").strip().lower()
            if resp in ("", "y", "yes"):
                # params["prompt"] already has style tokens prepended; just extend it
                params["prompt"] = params["prompt"].rstrip(" ,") + ", warm afternoon light"

    return params


# ---------------------------------------------------------------------------
# Single-image execution
# ---------------------------------------------------------------------------


def run_single(args: argparse.Namespace) -> int:
    """Resolve params for a single image and invoke (or dry-run) generate.py."""
    prompt = _effective_prompt(args)

    if not prompt and not args.dry_run:
        print(
            "[simple_config] ❌ --prompt is required for image generation. "
            "Use --dry-run to preview without a prompt.",
            file=sys.stderr,
        )
        return 1

    base = resolve_base_params(args)
    params = apply_prompt_and_style(
        base,
        prompt,
        args.style,
        args.no_default_style,
        args.lora,
        args.lora_weight,
    )

    if args.assist:
        params = run_assist(params, args)

    cmd = build_generate_cmd(params)
    cmd_str = " ".join(shlex.quote(c) for c in cmd)
    print(f"[simple_config] Resolved command:\n  {cmd_str}\n")

    if args.dry_run:
        print("[dry-run] 0 generate.py calls made.")
        return 0

    result = subprocess.run(cmd, cwd=Path(__file__).parent, timeout=3600)
    return result.returncode


# ---------------------------------------------------------------------------
# Batch-file execution
# ---------------------------------------------------------------------------


def run_batch(args: argparse.Namespace) -> int:
    """Process a JSON batch file of generation jobs."""
    batch_path = Path(args.batch_file)
    if not batch_path.is_absolute():
        # Resolve relative paths from the current working directory
        batch_path = Path.cwd() / batch_path

    if not batch_path.exists():
        print(f"[simple_config] ❌ Batch file not found: {args.batch_file}", file=sys.stderr)
        return 1

    try:
        jobs = json.loads(batch_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[simple_config] ❌ Invalid JSON in batch file: {exc}", file=sys.stderr)
        return 1

    if not isinstance(jobs, list):
        print("[simple_config] ❌ Batch file must contain a JSON array of job objects.", file=sys.stderr)
        return 1

    base = resolve_base_params(args)
    total = len(jobs)
    failures: list[int] = []

    for i, job in enumerate(jobs, 1):
        if not isinstance(job, dict):
            print(f"[simple_config] ❌ Job {i}/{total} is not a dict — skipping.", file=sys.stderr)
            failures.append(i)
            continue

        job_prompt = job.get("prompt", "")
        if not job_prompt:
            print(f"[simple_config] ❌ Job {i}/{total} has no 'prompt' field — skipping.", file=sys.stderr)
            failures.append(i)
            continue

        params = apply_prompt_and_style(
            base,
            job_prompt,
            args.style,
            args.no_default_style,
            args.lora,
            args.lora_weight,
        )

        # Apply per-job field overrides with type validation
        _JOB_FIELD_TYPES: dict[str, type | tuple] = {
            "seed": int,
            "output": str,
            "steps": int,
            "guidance": (int, float),
            "width": int,
            "height": int,
            "model": str,
        }
        _MODEL_CHOICES = frozenset({"creative", "precise", "balanced"})
        job_valid = True
        for field, expected_type in _JOB_FIELD_TYPES.items():
            if field not in job:
                continue
            value = job[field]
            if not isinstance(value, expected_type):
                print(
                    f"[simple_config] ❌ Job {i}/{total}: field '{field}' must be "
                    f"{expected_type if isinstance(expected_type, type) else '/'.join(t.__name__ for t in expected_type)}"
                    f", got {type(value).__name__} — skipping job.",
                    file=sys.stderr,
                )
                job_valid = False
                break
            if field == "model" and value not in _MODEL_CHOICES:
                print(
                    f"[simple_config] ❌ Job {i}/{total}: field 'model' must be one of "
                    f"{sorted(_MODEL_CHOICES)}, got '{value}' — skipping job.",
                    file=sys.stderr,
                )
                job_valid = False
                break
            params[field] = value
        if not job_valid:
            failures.append(i)
            continue

        # --assist runs in non-interactive (silent safe-defaults) mode for batch
        if args.assist:
            if "no text" not in params.get("prompt", "").lower():
                params["prompt"] = params.get("prompt", "").rstrip(" ,") + ", no text"
            if not params.get("negative_prompt"):
                params["negative_prompt"] = _DEFAULT_NEGATIVE_PROMPT

        cmd = build_generate_cmd(params)
        cmd_str = " ".join(shlex.quote(c) for c in cmd)
        print(f"[job {i}/{total}] {cmd_str}")

        if not args.dry_run:
            result = subprocess.run(cmd, cwd=Path(__file__).parent, timeout=3600)
            if result.returncode != 0:
                failures.append(i)

    if args.dry_run:
        print(f"[dry-run] {total} jobs resolved. 0 generate.py calls made.")
        return 0

    if failures:
        print(f"\n[simple_config] ⚠️  {len(failures)}/{total} jobs failed: {failures}")
        return 1

    print(f"\n[simple_config] ✅ {total}/{total} jobs completed.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.batch_file:
        return run_batch(args)
    return run_single(args)


if __name__ == "__main__":
    sys.exit(main())

