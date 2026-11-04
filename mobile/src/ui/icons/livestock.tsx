import { Circle, Path } from 'react-native-svg';

import { colors } from '../theme';
import { Frame, type IconProps } from './frame';

function Eye({ x, y, color }: { x: number; y: number; color?: string }) {
  return <Circle cx={x} cy={y} r={0.8} fill={color ?? colors.ink} stroke="none" />;
}

// Side silhouettes facing left, four legs each. Llama: long neck, tall ears. Alpaca: short neck,
// round head, fluffy topknot.
export function LlamaIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M9.5 12h7a2.5 2.5 0 0 1 0 5h-7a2.5 2.5 0 0 1 0-5Z" />
      <Path d="M7.4 13.2V6.6L4.8 6.3a.9.9 0 0 1-.1-1.7l3-1h1.6a.8.8 0 0 1 .8.8V12" />
      <Path d="M8 3.6 7.6 1.6M9.5 3.7l.3-2" />
      <Path d="M8.5 17v3M10.5 17v3M15.5 17v3M17.5 17v3" />
      <Path d="M19 13.3l1.2-1.3" />
      <Eye x={8.2} y={5.1} color={p.color} />
    </Frame>
  );
}

export function AlpacaIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7.5 20v-4.5M16.5 20v-4.5" />
      <Path d="M6 15.5h12v-1.2a3.2 3.2 0 0 0-3.2-3.2H9.2A3.2 3.2 0 0 0 6 14.3v1.2Z" />
      <Path d="M9.5 11V6.5" />
      <Circle cx={9.5} cy={5} r={1.9} />
      <Path d="M7.9 3.6 7.4 2.4M9.5 3.1V2M11.1 3.6l.5-1.2" />
      <Eye x={9} y={5.2} color={p.color} />
    </Frame>
  );
}

export function SheepIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7.5 20v-3.5M16.5 20v-3.5" />
      <Path d="M5.5 14.5a2.3 2.3 0 0 1 .5-4.5 2.6 2.6 0 0 1 1.7-2.8 2.6 2.6 0 0 1 3-1.2 2.6 2.6 0 0 1 3.4-.4 2.6 2.6 0 0 1 3.1 1.3 2.4 2.4 0 0 1 1.3 3.7 2.3 2.3 0 0 1-1 4H5.5Z" />
      <Path d="M4.5 16.5 3.5 18.5h2l1-2" />
      <Eye x={4.6} y={16.8} color={p.color} />
    </Frame>
  );
}

export function CowIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7.5 9h9.5a2.5 2.5 0 0 1 2.5 2.5V15a1 1 0 0 1-1 1H8.5" />
      <Path d="M7.5 9 4.6 9.4 3 13.4l2.1 1L7 12.6 8.5 16" />
      <Path d="M4.9 9.4 3.9 7.4M6.9 9.1l.4-1.9" />
      <Path d="M9 16v4M11.5 16v4M15.5 16v4M18 16v4" />
      <Path d="M19.5 11.5l1.3 3.8" />
      <Path d="M12.5 9v2a1.6 1.6 0 0 0 3.2 0V9" />
      <Eye x={5.3} y={11} color={p.color} />
    </Frame>
  );
}

export function PigIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7 20v-3M17 20v-3" />
      <Path d="M12 8.5c4.4 0 7.5 2.2 7.5 5s-3.1 4.5-7.5 4.5S5 16.2 5 14.5l-1.5-.5 1-2.5C6 9.8 8.8 8.5 12 8.5Z" />
      <Path d="M5 14.5 3.5 14l1-2.5" />
      <Path d="M8 8.7 8.6 6.5 10.4 8" />
      <Eye x={6.6} y={12.4} color={p.color} />
      <Path d="M19.5 12.5c1 0 1.5.7 1.2 1.5-.2.7-1.2.8-1.7.3" />
    </Frame>
  );
}

export function ChickenIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M10 20v-2.5M14 20v-2.5" />
      <Path d="M12 9.5c3.4 0 6 2.4 6 5.2s-2.6 3.3-6 3.3-6-1.4-6-4.2c0-1.5.7-2.7 1.8-3.5" />
      <Circle cx={7.2} cy={7.4} r={2.2} />
      <Path d="M5 7.4 3.2 6.6 5 5.4" />
      <Path d="M6.4 5.4c-.3-1 .2-2 1-2.4.2 1 .7 1.4 1.4 1.6.5-1 1.4-1.4 2.2-1.4-.2 1-.6 1.8-1.4 2.4" />
      <Eye x={7} y={7.2} color={p.color} />
      <Path d="M18 13.5l2.5-1.5-.8 2.5 1.8.4-2.3 1.3" />
    </Frame>
  );
}

export function GuineaPigIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 9.5c4.6 0 8 2.6 8 5.5s-3.4 4.5-8 4.5-7.5-2-7.5-5 2.9-5 7.5-5Z" />
      <Path d="M6.5 10.5 6 8l1.8.8" />
      <Eye x={7.4} y={13.4} color={p.color} />
      <Path d="M5 16.5h2" />
    </Frame>
  );
}

export function FishIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M3.5 12c2.6-3.4 6-5 9.5-5 3 0 5.2 1.2 6.5 2.6L21.5 7v10l-2-2.6c-1.3 1.4-3.5 2.6-6.5 2.6-3.5 0-6.9-1.6-9.5-5Z" />
      <Path d="M13 7.5c.8 1.4.8 7.6 0 9" />
      <Eye x={6.4} y={11.4} color={p.color} />
    </Frame>
  );
}

export function BeeIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M8 14.5c-2 0-3.5-1.6-3.5-3.5S6 7.5 8 7.5h6c3 0 5.5 1.4 5.5 3.5S17 14.5 14 14.5H8Z" />
      <Path d="M10.5 7.5v7M14 7.7v6.6" />
      <Path d="M19.5 11 21.5 9.5 21 12.5l.5 3-2-1.5" />
      <Path d="M9 7.5C8 5 8.5 3.2 10 2.5c1.6 1 1.8 3 1 5M14.5 7.3c.6-2.3 2-3.6 3.6-3.8.8 1.6.1 3.5-1.6 4.7" />
    </Frame>
  );
}

export function HorseIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M9.5 11h7a2.5 2.5 0 0 1 0 5h-7a2.5 2.5 0 0 1 0-5Z" />
      <Path d="M8.6 11.2 6.6 5 3.6 8l-.4 1.3 1.1.6 2-1.1L7.4 13" />
      <Path d="M6.6 5l.3-1.8M6.9 5.6l2.6 5.4" />
      <Path d="M8.5 16v4M10.5 16v4M15.5 16v4M17.5 16v4" />
      <Path d="M19 12.3c1.6.4 2.2 2.6 1.6 5.2" />
      <Eye x={5.4} y={7.1} color={p.color} />
    </Frame>
  );
}
