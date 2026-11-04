import { Circle, Path } from 'react-native-svg';

import { colors } from '../theme';
import { Frame, type IconProps } from './frame';

function Dot({ x, y, color }: { x: number; y: number; color?: string }) {
  return <Circle cx={x} cy={y} r={0.9} fill={color ?? colors.ink} stroke="none" />;
}

export function TuberIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 4.5c3.8 0 6.8 3.3 6.8 7.5s-3 7.5-6.8 7.5-6.8-3.3-6.8-7.5S8.2 4.5 12 4.5Z" />
      <Dot x={10.4} y={10} color={p.color} />
      <Dot x={13.4} y={12} color={p.color} />
      <Dot x={11} y={14.6} color={p.color} />
    </Frame>
  );
}

export function GrainIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 20.5v-15" />
      <Path d="m12 5.5-3.2 2m3.2-2 3.2 2m-3.2 2.5-3.2 2m3.2-2 3.2 2m-3.2 2.5-3.2 2m3.2-2 3.2 2m-3.2 2.5-2.6 1.8M12 16.5l2.6 1.8" />
      <Path d="M12 5.5V2.5M10 6.5 9 3.5M14 6.5l1-3" />
    </Frame>
  );
}

export function LegumeIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M5 19C5 11.5 11 5.5 18.5 5.5c0 7.5-6 13.5-13.5 13.5Z" />
      <Path d="M18.5 5.5c.8-1 1.8-1.5 2.5-1.7" />
      <Dot x={10.4} y={14} color={p.color} />
      <Dot x={13.4} y={11} color={p.color} />
    </Frame>
  );
}

export function VegetableIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M5.5 18.5C5.5 11 11 5.5 19.5 4.5c-1 8.5-6.5 14-14 14Z" />
      <Path d="M5.5 18.5C9 14.5 13 10.5 17 7" />
    </Frame>
  );
}

export function ForageIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7 20.5c0-5 .8-8.5 2.8-11-.3 4-.6 7.5-1.2 11" />
      <Path d="M12 20.5V8.5" />
      <Path d="M12 20.5c.8-4.5 2.8-7.5 6-9-.8 3.5-2.2 6.5-4.4 9" />
      <Path d="M4.5 20.5h15" />
    </Frame>
  );
}

export function GreenhouseIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M2.5 20h19" />
      <Path d="M4 20v-6.5a8 7 0 0 1 16 0V20" />
      <Path d="M8.5 20v-8.2a3.5 5.4 0 0 1 7 0V20" />
      <Path d="M12 20v-2.6m0 0c0-1.2.8-2 2-2M12 17.4c0-1-.7-1.8-1.8-1.8" />
    </Frame>
  );
}
