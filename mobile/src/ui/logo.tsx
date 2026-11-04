import Svg, { Circle, ClipPath, Defs, G, Line, LinearGradient, Path, RadialGradient, Rect, Stop } from 'react-native-svg';

import { colors } from './theme';

// FrostWatch mark: a clear, cold Altiplano night over a snowy range, the moment radiation
// frost forms. Same paths as mobile/assets/logo.svg (full), logo-mono.svg (mono).
// variant "mark" is the simplified artwork for tiny sizes (no stars or plain lines).

const ARM = 'M11 0H48 M27 0l11-11M27 0l11 11';
const HEX = 'M8 0L4 6.9L-4 6.9L-8 0L-4-6.9L4-6.9Z';
const MOON = 'M390.7 104.5A30 30 0 1 0 423.7 62.5A27 27 0 0 1 390.7 104.5Z';
const MASSIF = 'M40 340 L130 245 L170 205 L230 252 L300 150 L370 230 L415 200 L480 340 Z';
const RIDGE =
  'M-4 268 L36 246 L64 258 L104 240 L140 254 L182 236 L222 252 L262 238 L302 252 L342 236 L382 250 L422 237 L462 251 L516 240 L516 330 L-4 330 Z';
const FOOTHILLS =
  'M-4 470 Q50 438 120 448 Q190 458 270 440 Q350 422 430 442 Q480 452 516 444 L516 516 L-4 516 Z';

const STARS: [number, number, number, number][] = [
  [40, 60, 3, 0.9],
  [90, 40, 2, 0.6],
  [150, 80, 2.5, 0.8],
  [210, 45, 3, 1],
  [265, 70, 2, 0.55],
  [330, 50, 2.5, 0.85],
  [370, 120, 2, 0.6],
  [300, 120, 3, 0.9],
  [120, 140, 2, 0.65],
  [60, 170, 2.5, 0.75],
  [200, 150, 2, 0.6],
  [350, 170, 2.4, 0.8],
];

function Snowflake({ x, y, color, width }: { x: number; y: number; color: string; width: number }) {
  return (
    <G transform={`translate(${x} ${y})`} stroke={color} strokeWidth={width} strokeLinecap="round" fill="none">
      {[0, 60, 120, 180, 240, 300].map((r) => (
        <G key={r} transform={`rotate(${r})`}>
          <Path d={ARM} />
        </G>
      ))}
      <Path d={HEX} strokeWidth={5} strokeLinejoin="round" />
    </G>
  );
}

export function LogoMark({ size = 40 }: { size?: number }) {
  return <Logo size={size} variant="full" />;
}

export function Logo({
  size = 64,
  variant = 'full',
  color = colors.navy,
}: {
  size?: number;
  variant?: 'full' | 'mark' | 'mono';
  color?: string;
}) {
  if (variant === 'mono') {
    return (
      <Svg width={size} height={size} viewBox="0 0 512 512" accessibilityLabel="FrostWatch logo">
        <Path d={MOON} fill={color} />
        <Path d={MASSIF} fill={color} />
        <Snowflake x={128} y={372} color={color} width={7} />
      </Svg>
    );
  }
  const detail = variant === 'full';
  return (
    <Svg width={size} height={size} viewBox="0 0 512 512" accessibilityLabel="FrostWatch logo">
      <Defs>
        <LinearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={colors.navyDeep} />
          <Stop offset="1" stopColor={colors.navy} />
        </LinearGradient>
        <RadialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
          <Stop offset="0" stopColor={colors.beige} stopOpacity={0.15} />
          <Stop offset="1" stopColor={colors.beige} stopOpacity={0} />
        </RadialGradient>
        <LinearGradient id="plain" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={colors.sand} />
          <Stop offset="1" stopColor={colors.plainEnd} />
        </LinearGradient>
        <ClipPath id="clip">
          <Rect x="0" y="0" width={512} height={512} rx={112} />
        </ClipPath>
      </Defs>
      <Rect x="0" y="0" width={512} height={512} rx={112} fill="url(#sky)" />
      <G clipPath="url(#clip)">
        {detail ? (
          <G fill={colors.beige}>
            {STARS.map(([cx, cy, r, o], i) => (
              <Circle key={i} cx={cx} cy={cy} r={r} opacity={o} />
            ))}
            <Path d="M245 85Q245 95 255 95Q245 95 245 105Q245 95 235 95Q245 95 245 85Z" opacity={0.95} />
            <Path d="M95 98Q95 105 102 105Q95 105 95 112Q95 105 88 105Q95 105 95 98Z" opacity={0.9} />
          </G>
        ) : null}
        <Circle cx={418} cy={92} r={58} fill="url(#halo)" />
        <Path d={MOON} fill={colors.beige} />
        <Rect x={0} y={300} width={512} height={150} fill="url(#plain)" />
        {detail ? (
          <G stroke={colors.plainLine} strokeWidth={2.5} strokeLinecap="round">
            <Line x1={170} y1={356} x2={342} y2={356} />
            <Line x1={200} y1={374} x2={312} y2={374} />
            <Line x1={228} y1={392} x2={284} y2={392} />
          </G>
        ) : null}
        {detail ? (
          <Line x1={36} y1={408} x2={72} y2={408} stroke={colors.iceBlue} strokeWidth={3} strokeLinecap="round" />
        ) : null}
        <Path d={RIDGE} fill={colors.ridge} opacity={0.6} />
        <Path d={MASSIF} fill={colors.navyLight} />
        <G fill={colors.beige}>
          <Path d="M170 205 L186 224 L180 221 L176 231 L170 224 L164 233 L160 223 L154 226 Z" />
          <Path d="M300 150 L320 176 L313 172 L308 184 L301 176 L295 187 L290 177 L283 181 Z" />
          <Path d="M415 200 L430 218 L424 215 L420 224 L414 217 L408 225 L404 216 L398 219 Z" />
        </G>
        <G fill={colors.iceBlue}>
          <Path d="M168 207 L156 222 L164 224 Z" />
          <Path d="M298 152 L282 178 L292 180 Z" />
          <Path d="M413 202 L400 217 L408 219 Z" />
        </G>
        <Path d={FOOTHILLS} fill={colors.navyDeep} />
        <Snowflake x={128} y={372} color={colors.beige} width={7} />
        {detail ? (
          <G stroke={colors.beige} strokeLinecap="round" fill="none">
            <G strokeWidth={3}>
              <Line x1={357} y1={190} x2={379} y2={190} />
              <Line x1={362.5} y1={180.5} x2={373.5} y2={199.5} />
              <Line x1={362.5} y1={199.5} x2={373.5} y2={180.5} />
            </G>
            <G strokeWidth={2.5}>
              <Line x1={235} y1={205} x2={251} y2={205} />
              <Line x1={239} y1={198.1} x2={247} y2={211.9} />
              <Line x1={239} y1={211.9} x2={247} y2={198.1} />
            </G>
          </G>
        ) : null}
        <Circle cx={300} cy={148} r={5.5} fill={colors.red} />
      </G>
    </Svg>
  );
}
