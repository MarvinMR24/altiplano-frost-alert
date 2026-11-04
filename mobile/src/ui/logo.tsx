import Svg, { Circle, Defs, G, Mask, Path, Rect } from 'react-native-svg';

import { colors } from './theme';

// FrostWatch mark: a map pin (your place) holding a snowy Altiplano peak, a frost
// snowflake and a red dot for the alert. Same paths as mobile/assets/logo.svg (full) and
// logo-mono.svg (mono); `node scripts/check-logo.mjs` checks they stay in sync.

const PIN = 'M256 448 C256 448 116 300 116 206 A140 140 0 0 1 396 206 C396 300 256 448 256 448 Z';
const MOUNTAINS = 'M150 262 L214 186 L244 220 L286 160 L362 262 Z';
const SNOWCAP = 'M286 160 L312 196 L298 190 L286 204 L274 190 L262 196 Z';
const FLAKE = 'M0 -28V28M-24 -14L24 14M-24 14L24 -14';

export function LogoMark({ size = 40 }: { size?: number }) {
  return <Logo size={size} variant="full" />;
}

export function Logo({
  size = 64,
  variant = 'full',
  color = colors.navy,
}: {
  size?: number;
  // "mark" drops the rounded background, for places that already have one.
  variant?: 'full' | 'mark' | 'mono';
  color?: string;
}) {
  if (variant === 'mono') {
    return (
      // One color: the mountains, snowflake and dot are cut out of the pin.
      <Svg width={size} height={size} viewBox="0 0 512 512" accessibilityLabel="FrostWatch">
        <Defs>
          <Mask id="cut">
            <Rect width={512} height={512} fill={colors.white} />
            <Path d={MOUNTAINS} fill={colors.black} />
            <Circle cx={256} cy={300} r={12} fill={colors.black} />
            <G transform="translate(256 110)" stroke={colors.black} strokeLinecap="round" fill="none">
              <Path d={FLAKE} strokeWidth={9} />
            </G>
          </Mask>
        </Defs>
        <Path d={PIN} fill={color} mask="url(#cut)" />
      </Svg>
    );
  }
  return (
    <Svg width={size} height={size} viewBox="0 0 512 512" accessibilityLabel="FrostWatch">
      {variant === 'full' ? <Rect width={512} height={512} rx={112} fill={colors.beige} /> : null}
      <Path d={PIN} fill={colors.navy} />
      <Path d={MOUNTAINS} fill={colors.logoMountain} />
      <Path d={SNOWCAP} fill={colors.beige} />
      <G transform="translate(256 110)" stroke={colors.beige} strokeLinecap="round" fill="none">
        <Path d={FLAKE} strokeWidth={9} />
      </G>
      <Circle cx={256} cy={300} r={12} fill={colors.red} />
    </Svg>
  );
}
