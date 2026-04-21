import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: 'clamp',
  });
  
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1a1a2e',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <h1
        style={{
          color: '#eee',
          fontSize: 80,
          opacity,
          fontFamily: 'sans-serif',
        }}
      >
        Hello Remotion
      </h1>
    </AbsoluteFill>
  );
}
