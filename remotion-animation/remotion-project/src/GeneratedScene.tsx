import {
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

  // Spring animation for the name
  const nameSpring = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });

  // Fade/slide for the timestamp (starts at 0.5s)
  const timestampDelay = Math.round(fps * 0.5);
  const timestampOpacity = interpolate(
    frame,
    [timestampDelay, timestampDelay + 15],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const timestampSlide = interpolate(
    frame,
    [timestampDelay, timestampDelay + 15],
    [20, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // "Generated with Remotion" fades in at 3s, name fades out at 5s
  const outroStart = Math.round(fps * 5);
  const outroOpacity = interpolate(
    frame,
    [outroStart, outroStart + 20],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const nameOutOpacity = interpolate(
    frame,
    [outroStart, outroStart + 20],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "'Segoe UI', Arial, sans-serif",
      }}
    >
      {/* Name + timestamp card */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: nameOutOpacity,
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 700,
            color: "white",
            transform: `scale(${nameSpring})`,
            letterSpacing: 2,
          }}
        >
          Dina Berry
        </div>
        <div
          style={{
            fontSize: 28,
            color: "rgba(255,255,255,0.75)",
            marginTop: 16,
            opacity: timestampOpacity,
            transform: `translateY(${timestampSlide}px)`,
          }}
        >
          April 22, 2026 at 10:38 AM PDT
        </div>
      </div>

      {/* Outro text */}
      <div
        style={{
          position: "absolute",
          bottom: "15%",
          fontSize: 24,
          color: "rgba(255,255,255,0.6)",
          opacity: outroOpacity,
          letterSpacing: 1,
        }}
      >
        Generated with Remotion
      </div>

      {/* TTS narration */}
      <Audio src={staticFile('narration.mp3')} volume={1.0} />
    </AbsoluteFill>
  );
};

export default GeneratedScene;