import {AbsoluteFill, useCurrentFrame, useVideoConfig, spring} from 'remotion';

export default function ShapeRotate() {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  
  const rotation = spring({
    frame,
    fps,
    config: {
      damping: 100,
      stiffness: 200,
      mass: 0.5,
    },
  });
  
  const degrees = rotation * 360;
  
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1e1e1e',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          width: 200,
          height: 200,
          backgroundColor: '#ff6b6b',
          borderRadius: 20,
          transform: `rotate(${degrees}deg)`,
        }}
      />
    </AbsoluteFill>
  );
}
