import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const opacity = interpolate(frame, [0, 240], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{backgroundColor: `linear-gradient(to bottom, #ff69b4, #33ccff)`}}>
      <Sequence from={frame} durationInFrames={240}>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <h1
            style={{
              color: '#fff',
              fontSize: 80,
              opacity,
              transform: `scale(${interpolate(frame, [0, 240], [0.8, 1], {extrapolateRight: 'clamp'})})`
            }}
          >
            April 22, 2026
            <br />
            10:00 AM PDT
          </h1>
        </div>
      </Sequence>
      <Audio src={staticFile('narration.mp3')} volume={1.0} />
    </AbsoluteFill>
  );
}