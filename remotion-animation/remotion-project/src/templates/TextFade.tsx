import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function TextFade() {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  
  const fadeInEnd = 30;
  const fadeOutStart = durationInFrames - 30;
  
  const opacity = interpolate(
    frame,
    [0, fadeInEnd, fadeOutStart, durationInFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );
  
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#0f0f23',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          color: '#61dafb',
          fontSize: 100,
          fontFamily: 'sans-serif',
          fontWeight: 'bold',
          opacity,
        }}
      >
        Remotion
      </div>
    </AbsoluteFill>
  );
}
