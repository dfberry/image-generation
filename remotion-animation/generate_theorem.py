"""Generate Pythagorean Theorem explainer video with TTS narration.

Bypasses LLM — uses a hand-crafted TSX component with step-by-step
geometric visualization and edge-tts narration.

Usage:
    cd remotion-animation
    python generate_theorem.py
"""

import sys
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).parent))

from remotion_gen.tts_providers import generate_narration
from remotion_gen.component_builder import write_component
from remotion_gen.renderer import render_video
from remotion_gen.config import QUALITY_PRESETS

# ── Narration text ──────────────────────────────────────────────────
NARRATION_TEXT = (
    "The Pythagorean Theorem states that for any right triangle, "
    "the square of the hypotenuse equals the sum of the squares "
    "of the other two sides. "
    "If we call the two shorter sides a and b, and the hypotenuse c, "
    "then a squared plus b squared equals c squared. "
    "Watch as we draw a square on each side of the triangle. "
    "The blue square has area a squared. "
    "The green square has area b squared. "
    "And the orange square on the hypotenuse has area c squared. "
    "Together, the two smaller squares have exactly the same area "
    "as the large square. "
    "This fundamental relationship has been known for thousands of years "
    "and remains one of the most important theorems in all of mathematics."
)

# ── TSX Component ───────────────────────────────────────────────────
COMPONENT_CODE = r'''import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  AbsoluteFill,
  Audio,
  staticFile,
} from "remotion";

const GeneratedScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // ── Helpers ──
  const fadeIn = (start: number, dur = 20) =>
    interpolate(frame, [start, start + dur], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  const springIn = (start: number) =>
    spring({
      frame: Math.max(0, frame - start),
      fps,
      config: { damping: 12, stiffness: 80 },
    });

  // ── Phase timing (30s @ 30fps = 900 frames) ──
  // Phase 1  (0–149):   Title
  // Phase 2  (120–299): Triangle appears
  // Phase 3  (270–449): Square on a (blue)
  // Phase 4  (420–599): Square on b (green)
  // Phase 5  (570–749): Square on c (orange)
  // Phase 6  (720–899): Conclusion equation

  // Title
  const titleOpacity = interpolate(
    frame,
    [0, 20, 120, 155],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const subtitleOpacity = fadeIn(40, 25);

  // Diagram
  const diagramOpacity = interpolate(
    frame,
    [120, 150],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const triScale = springIn(120);

  // Squares
  const sqAOpacity = fadeIn(270, 30);
  const sqBOpacity = fadeIn(420, 30);
  const sqCOpacity = fadeIn(570, 30);

  // Step annotations
  const annotAOpacity = fadeIn(300, 20);
  const annotBOpacity = fadeIn(450, 20);
  const annotCOpacity = fadeIn(600, 20);

  // Conclusion
  const conclusionOpacity = fadeIn(720, 35);
  const conclusionScale = springIn(720);

  // Subtle step label on the left
  const stepLabelA = fadeIn(270, 15);
  const stepLabelB = fadeIn(420, 15);
  const stepLabelC = fadeIn(570, 15);
  const stepLabelFinal = fadeIn(720, 15);

  // ── Geometry: 3-4-5 triangle (a=120, b=160, c=200 px) ──
  const cx = 480;
  const cy = 420;
  const ax = 480;
  const ay = 300;
  const bx = 640;
  const by = 420;

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(160deg, #0b0b2e 0%, #161650 40%, #1a1a5e 70%, #0d0d3a 100%)",
        fontFamily: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Narration audio */}
      <Audio src={staticFile('narration.mp3')} volume={1.0} />

      {/* ── Decorative grid (always visible, very faint) ── */}
      <svg
        width="1280"
        height="720"
        viewBox="0 0 1280 720"
        style={{ position: "absolute", opacity: 0.04 }}
      >
        {Array.from({ length: 26 }, (_, i) => (
          <line
            key={`v${i}`}
            x1={i * 50}
            y1={0}
            x2={i * 50}
            y2={720}
            stroke="white"
            strokeWidth={0.5}
          />
        ))}
        {Array.from({ length: 15 }, (_, i) => (
          <line
            key={`h${i}`}
            x1={0}
            y1={i * 50}
            x2={1280}
            y2={i * 50}
            stroke="white"
            strokeWidth={0.5}
          />
        ))}
      </svg>

      {/* ── Phase 1: Title ── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          opacity: titleOpacity,
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontSize: 58,
            fontWeight: 700,
            color: "#ffffff",
            textShadow: "0 0 40px rgba(100,150,255,0.4)",
            letterSpacing: 3,
          }}
        >
          The Pythagorean Theorem
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 300,
            color: "#7cb3ff",
            marginTop: 24,
            opacity: subtitleOpacity,
            letterSpacing: 6,
          }}
        >
          a&#178; + b&#178; = c&#178;
        </div>
      </div>

      {/* ── Phase 2–5: Diagram ── */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: diagramOpacity,
          transform: `scale(${triScale})`,
        }}
      >
        <svg
          width="1280"
          height="720"
          viewBox="0 0 1280 720"
          style={{ position: "absolute" }}
        >
          {/* Square on side a – BLUE (extends left from vertical side) */}
          <g opacity={sqAOpacity}>
            <rect
              x={cx - 120}
              y={ay}
              width={120}
              height={120}
              fill="rgba(66,165,245,0.2)"
              stroke="#42a5f5"
              strokeWidth={2}
            />
            <text
              x={cx - 60}
              y={ay + 65}
              fill="#42a5f5"
              fontSize={22}
              fontWeight="bold"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {"a\u00B2"}
            </text>
          </g>

          {/* Square on side b – GREEN (extends down from horizontal side) */}
          <g opacity={sqBOpacity}>
            <rect
              x={cx}
              y={cy}
              width={160}
              height={160}
              fill="rgba(76,175,80,0.2)"
              stroke="#4caf50"
              strokeWidth={2}
            />
            <text
              x={cx + 80}
              y={cy + 85}
              fill="#4caf50"
              fontSize={22}
              fontWeight="bold"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {"b\u00B2"}
            </text>
          </g>

          {/* Square on hypotenuse c – ORANGE (rotated square) */}
          <g opacity={sqCOpacity}>
            <polygon
              points={`${ax},${ay} ${bx},${by} ${bx + 120},${by - 160} ${ax + 120},${ay - 160}`}
              fill="rgba(255,152,0,0.2)"
              stroke="#ff9800"
              strokeWidth={2}
            />
            <text
              x={(ax + bx) / 2 + 60}
              y={(ay + by) / 2 - 80}
              fill="#ff9800"
              fontSize={22}
              fontWeight="bold"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {"c\u00B2"}
            </text>
          </g>

          {/* Triangle (always visible once diagram fades in) */}
          <polygon
            points={`${cx},${cy} ${ax},${ay} ${bx},${by}`}
            fill="rgba(255,255,255,0.06)"
            stroke="white"
            strokeWidth={3}
          />

          {/* Right-angle marker */}
          <path
            d={`M ${cx},${cy - 18} L ${cx + 18},${cy - 18} L ${cx + 18},${cy}`}
            fill="none"
            stroke="rgba(255,255,255,0.5)"
            strokeWidth={1.5}
          />

          {/* Side labels */}
          <text
            x={cx - 18}
            y={(ay + cy) / 2 + 5}
            fill="#42a5f5"
            fontSize={30}
            fontWeight="bold"
            textAnchor="end"
          >
            a
          </text>
          <text
            x={(cx + bx) / 2}
            y={cy + 35}
            fill="#4caf50"
            fontSize={30}
            fontWeight="bold"
            textAnchor="middle"
          >
            b
          </text>
          <text
            x={(ax + bx) / 2 + 18}
            y={(ay + by) / 2 - 12}
            fill="#ff9800"
            fontSize={30}
            fontWeight="bold"
            textAnchor="start"
          >
            c
          </text>
        </svg>
      </div>

      {/* ── Step annotations (right panel) ── */}
      <div style={{ position: "absolute", right: 60, top: 180, width: 420 }}>
        <div style={{ opacity: annotAOpacity, marginBottom: 24 }}>
          <div
            style={{
              fontSize: 22,
              color: "#42a5f5",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 16,
                height: 16,
                background: "#42a5f5",
                borderRadius: 3,
                flexShrink: 0,
              }}
            />
            {"Area of square on a = a\u00B2"}
          </div>
        </div>

        <div style={{ opacity: annotBOpacity, marginBottom: 24 }}>
          <div
            style={{
              fontSize: 22,
              color: "#4caf50",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 16,
                height: 16,
                background: "#4caf50",
                borderRadius: 3,
                flexShrink: 0,
              }}
            />
            {"Area of square on b = b\u00B2"}
          </div>
        </div>

        <div style={{ opacity: annotCOpacity, marginBottom: 24 }}>
          <div
            style={{
              fontSize: 22,
              color: "#ff9800",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 16,
                height: 16,
                background: "#ff9800",
                borderRadius: 3,
                flexShrink: 0,
              }}
            />
            {"Area of square on c = c\u00B2"}
          </div>
        </div>

        {/* Summary line */}
        <div
          style={{
            opacity: annotCOpacity,
            marginTop: 12,
            paddingTop: 16,
            borderTop: "1px solid rgba(255,255,255,0.15)",
          }}
        >
          <div style={{ fontSize: 20, color: "rgba(255,255,255,0.7)" }}>
            {"a\u00B2 + b\u00B2 = c\u00B2"}
          </div>
        </div>
      </div>

      {/* ── Step indicator (left edge) ── */}
      <div
        style={{
          position: "absolute",
          left: 40,
          bottom: 50,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.3)",
            opacity: stepLabelA,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {frame < 420 ? "Step 1 of 4" : ""}
        </div>
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.3)",
            opacity: stepLabelB,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {frame >= 420 && frame < 570 ? "Step 2 of 4" : ""}
        </div>
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.3)",
            opacity: stepLabelC,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {frame >= 570 && frame < 720 ? "Step 3 of 4" : ""}
        </div>
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.3)",
            opacity: stepLabelFinal,
            letterSpacing: 2,
            textTransform: "uppercase",
          }}
        >
          {frame >= 720 ? "Step 4 of 4" : ""}
        </div>
      </div>

      {/* ── Phase 6: Conclusion ── */}
      <div
        style={{
          position: "absolute",
          bottom: 50,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: conclusionOpacity,
          transform: `scale(${conclusionScale})`,
        }}
      >
        <div
          style={{
            fontSize: 42,
            fontWeight: 700,
            color: "#ffffff",
            background:
              "linear-gradient(135deg, rgba(66,165,245,0.15), rgba(255,152,0,0.15))",
            padding: "14px 48px",
            borderRadius: 12,
            border: "2px solid rgba(255,255,255,0.2)",
            letterSpacing: 5,
            textShadow: "0 0 20px rgba(100,150,255,0.3)",
          }}
        >
          {"a\u00B2 + b\u00B2 = c\u00B2"}
        </div>
        <div
          style={{
            fontSize: 18,
            color: "rgba(255,255,255,0.55)",
            marginTop: 14,
            letterSpacing: 1,
          }}
        >
          The two smaller squares together equal the large square
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default GeneratedScene;
'''


def main():
    repo_root = Path(__file__).parent
    project_root = repo_root / "remotion-project"
    output_dir = repo_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (output_dir / "theorem_explained.mp4").resolve()

    print("=" * 60)
    print("Pythagorean Theorem Explainer — Video Generator")
    print("=" * 60)

    # ── Step 1: Generate TTS narration ──
    print("\n→ Step 1: Generating TTS narration (edge-tts, en-US-JennyNeural)...")
    narration_path = generate_narration(
        NARRATION_TEXT,
        provider_name="edge-tts",
        voice="en-US-JennyNeural",
        output_dir=project_root / "public",
    )
    print(f"  ✓ Narration saved: {narration_path}")
    print(f"  Size: {narration_path.stat().st_size / 1024:.1f} KB")

    # ── Step 2: Write TSX component ──
    print("\n→ Step 2: Writing Remotion component...")
    component_path = write_component(
        COMPONENT_CODE,
        project_root,
        debug=True,
        audio_filenames=["narration.mp3"],
    )
    print(f"  ✓ Component written: {component_path}")

    # ── Step 3: Render video ──
    preset = QUALITY_PRESETS["medium"]  # 720p 30fps
    duration_seconds = 30
    duration_frames = duration_seconds * preset.fps

    print(f"\n→ Step 3: Rendering {duration_seconds}s video at "
          f"{preset.resolution_name} {preset.fps}fps ({duration_frames} frames)...")
    result_path = render_video(project_root, output_path, preset, duration_frames)

    print(f"\n{'=' * 60}")
    print(f"✓ Video generated: {result_path}")
    print(f"  Size: {result_path.stat().st_size / (1024 * 1024):.1f} MB")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
