import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';

export default function GeneratedScene() {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();

  const scale = 60;
  const a = 3 * scale;
  const b = 4 * scale;
  const cx = width / 2 - 60;
  const cy = height / 2 + 40;

  const triDraw = interpolate(frame, [0, fps * 1.5], [0, 1], {extrapolateRight: 'clamp'});
  const sqAOpacity = interpolate(frame, [fps * 1.5, fps * 2.5], [0, 1], {extrapolateRight: 'clamp'});
  const sqBOpacity = interpolate(frame, [fps * 2.5, fps * 3.5], [0, 1], {extrapolateRight: 'clamp'});
  const sqCOpacity = interpolate(frame, [fps * 3.5, fps * 4.5], [0, 1], {extrapolateRight: 'clamp'});
  const eqOpacity = interpolate(frame, [fps * 4.5, fps * 5], [0, 1], {extrapolateRight: 'clamp'});
  const eqScale = interpolate(frame, [fps * 4.5, fps * 5.5], [0.6, 1], {extrapolateRight: 'clamp'});

  const Ax = cx;
  const Ay = cy;
  const Bx = cx + b;
  const By = cy;
  const Cx = cx;
  const Cy = cy - a;

  const c = Math.sqrt(a * a + b * b);

  const triPath = `M ${Ax} ${Ay} L ${Bx} ${By} L ${Cx} ${Cy} Z`;

  const markerSize = 18;
  const rightAngle = `M ${Ax + markerSize} ${Ay} L ${Ax + markerSize} ${Ay - markerSize} L ${Ax} ${Ay - markerSize}`;

  const dx = (Bx - Cx) / c;
  const dy = (By - Cy) / c;
  const px = -dy;
  const py = dx;
  const P1x = Cx + px * c;
  const P1y = Cy + py * c;
  const P2x = Bx + px * c;
  const P2y = By + py * c;
  const sqCPath = `M ${Cx} ${Cy} L ${Bx} ${By} L ${P2x} ${P2y} L ${P1x} ${P1y} Z`;
  const cLabelX = (Cx + Bx + P1x + P2x) / 4 - 10;
  const cLabelY = (Cy + By + P1y + P2y) / 4 + 8;

  return (
    <AbsoluteFill style={{backgroundColor: '#0d1117', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{position: 'absolute', top: 40, width: '100%', textAlign: 'center'}}>
        <span style={{color: '#58a6ff', fontSize: 36, fontFamily: 'monospace', fontWeight: 700, letterSpacing: 2}}>
          Pythagorean Theorem
        </span>
      </div>

      <svg width={width} height={height} style={{position: 'absolute', top: 0, left: 0}}>
        <path d={triPath} fill="rgba(56,139,253,0.08)" stroke="#58a6ff" strokeWidth={3}
          strokeDasharray={`${triDraw * 1200}`} strokeDashoffset={0} fillOpacity={triDraw} />

        <path d={rightAngle} fill="none" stroke="#8b949e" strokeWidth={2} opacity={triDraw} />

        <text x={Ax - 30} y={(Ay + Cy) / 2 + 5} fill="#f0883e" fontSize={28}
          fontFamily="monospace" fontWeight={700} opacity={triDraw}>a</text>
        <text x={(Ax + Bx) / 2 - 5} y={Ay + 35} fill="#3fb950" fontSize={28}
          fontFamily="monospace" fontWeight={700} opacity={triDraw}>b</text>
        <text x={(Bx + Cx) / 2 + 15} y={(By + Cy) / 2 - 5} fill="#bc8cff" fontSize={28}
          fontFamily="monospace" fontWeight={700} opacity={triDraw}>c</text>

        <rect x={Ax - a} y={Cy} width={a} height={a}
          fill="rgba(240,136,62,0.15)" stroke="#f0883e" strokeWidth={2} opacity={sqAOpacity} />
        <text x={Ax - a / 2 - 10} y={(Cy + Ay) / 2 + 8} fill="#f0883e" fontSize={22}
          fontFamily="monospace" fontWeight={700} opacity={sqAOpacity}>{"a\u00B2"}</text>

        <rect x={Ax} y={Ay} width={b} height={b}
          fill="rgba(63,185,80,0.15)" stroke="#3fb950" strokeWidth={2} opacity={sqBOpacity} />
        <text x={Ax + b / 2 - 10} y={Ay + b / 2 + 8} fill="#3fb950" fontSize={22}
          fontFamily="monospace" fontWeight={700} opacity={sqBOpacity}>{"b\u00B2"}</text>

        <path d={sqCPath} fill="rgba(188,140,255,0.15)" stroke="#bc8cff" strokeWidth={2} opacity={sqCOpacity} />
        <text x={cLabelX} y={cLabelY} fill="#bc8cff" fontSize={22}
          fontFamily="monospace" fontWeight={700} opacity={sqCOpacity}>{"c\u00B2"}</text>
      </svg>

      <div style={{
        position: 'absolute', bottom: 60, width: '100%', textAlign: 'center',
        opacity: eqOpacity, transform: `scale(${eqScale})`,
      }}>
        <span style={{color: '#f0883e', fontSize: 52, fontFamily: 'monospace', fontWeight: 700}}>{"a\u00B2"}</span>
        <span style={{color: '#c9d1d9', fontSize: 52, fontFamily: 'monospace', fontWeight: 700}}>{" + "}</span>
        <span style={{color: '#3fb950', fontSize: 52, fontFamily: 'monospace', fontWeight: 700}}>{"b\u00B2"}</span>
        <span style={{color: '#c9d1d9', fontSize: 52, fontFamily: 'monospace', fontWeight: 700}}>{" = "}</span>
        <span style={{color: '#bc8cff', fontSize: 52, fontFamily: 'monospace', fontWeight: 700}}>{"c\u00B2"}</span>
      </div>
    </AbsoluteFill>
  );
}
