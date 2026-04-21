"""Pre-built TSX demo template that bypasses LLM generation.

This produces a reliable, polished "Dina Berry" title card animation
without depending on llama3 to generate valid TSX.
"""


def get_demo_component(datetime_str: str) -> str:
    """Return a complete GeneratedScene TSX component with the given timestamp.

    Args:
        datetime_str: Formatted date/time string to embed in the video.

    Returns:
        Valid TSX source for a GeneratedScene component.
    """
    return f'''import React from "react";
import {{
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  AbsoluteFill,
  Sequence,
}} from "remotion";

const GeneratedScene: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{ fps }} = useVideoConfig();

  // Spring animation for the name
  const nameSpring = spring({{
    frame,
    fps,
    config: {{ damping: 12, stiffness: 80 }},
  }});

  // Fade/slide for the timestamp (starts at 0.5s)
  const timestampDelay = Math.round(fps * 0.5);
  const timestampOpacity = interpolate(
    frame,
    [timestampDelay, timestampDelay + 15],
    [0, 1],
    {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }}
  );
  const timestampSlide = interpolate(
    frame,
    [timestampDelay, timestampDelay + 15],
    [20, 0],
    {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }}
  );

  // "Generated with Remotion" fades in at 3s, name fades out
  const outroStart = Math.round(fps * 3);
  const outroOpacity = interpolate(
    frame,
    [outroStart, outroStart + 20],
    [0, 1],
    {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }}
  );
  const nameOutOpacity = interpolate(
    frame,
    [outroStart, outroStart + 20],
    [1, 0],
    {{ extrapolateLeft: "clamp", extrapolateRight: "clamp" }}
  );

  return (
    <AbsoluteFill
      style={{{{
        background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "'Segoe UI', Arial, sans-serif",
      }}}}
    >
      {{/* Name + timestamp card */}}
      <div
        style={{{{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: nameOutOpacity,
        }}}}
      >
        <div
          style={{{{
            fontSize: 72,
            fontWeight: 700,
            color: "white",
            transform: `scale(${{nameSpring}})`,
            letterSpacing: 2,
          }}}}
        >
          Dina Berry
        </div>
        <div
          style={{{{
            fontSize: 28,
            color: "rgba(255,255,255,0.75)",
            marginTop: 16,
            opacity: timestampOpacity,
            transform: `translateY(${{timestampSlide}}px)`,
          }}}}
        >
          {datetime_str}
        </div>
      </div>

      {{/* Outro text */}}
      <div
        style={{{{
          position: "absolute",
          bottom: "15%",
          fontSize: 24,
          color: "rgba(255,255,255,0.6)",
          opacity: outroOpacity,
          letterSpacing: 1,
        }}}}
      >
        Generated with Remotion
      </div>
    </AbsoluteFill>
  );
}};

export default GeneratedScene;
'''
