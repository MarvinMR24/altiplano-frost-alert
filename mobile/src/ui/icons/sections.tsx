import { Circle, Line, Path } from 'react-native-svg';

import { Frame, type IconProps } from './frame';

export function MapIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4Zm0 0v14m6-12v14" />
    </Frame>
  );
}

export function LayersIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="m12 3 9 4.8-9 4.8-9-4.8L12 3Z" />
      <Path d="m4.5 12.5 7.5 4 7.5-4" />
      <Path d="m4.5 16.5 7.5 4 7.5-4" />
    </Frame>
  );
}

export function BellIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M6.5 9.5a5.5 5.5 0 0 1 11 0c0 4.5 1.8 5.8 1.8 5.8H4.7s1.8-1.3 1.8-5.8" />
      <Path d="M10 19a2.2 2.2 0 0 0 4 0" />
    </Frame>
  );
}

export function HistoryIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <Path d="M3.5 3.8v4.7h4.7" />
      <Path d="M12 8v4.2l3 1.8" />
    </Frame>
  );
}

export function ProfileIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={12} cy={12} r={8.7} />
      <Circle cx={12} cy={9.8} r={2.9} />
      <Path d="M6.8 18.4c.9-2.7 2.9-4 5.2-4s4.3 1.3 5.2 4" />
    </Frame>
  );
}

export function SettingsIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Line x1={3.5} y1={6.5} x2={14} y2={6.5} />
      <Line x1={3.5} y1={12} x2={8.5} y2={12} />
      <Line x1={15.5} y1={12} x2={20.5} y2={12} />
      <Line x1={3.5} y1={17.5} x2={12} y2={17.5} />
      <Circle cx={17} cy={6.5} r={2.2} />
      <Circle cx={12} cy={12} r={2.2} />
      <Circle cx={15} cy={17.5} r={2.2} />
    </Frame>
  );
}

export function PlusIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 5v14M5 12h14" />
    </Frame>
  );
}

export function SproutIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 20.5v-8" />
      <Path d="M12 12.5c0-3.8 2.8-6.5 7.5-6.5 0 4-2.8 6.5-7.5 6.5Z" />
      <Path d="M12 14.5c0-3-2.2-5-5.8-5 0 3.2 2.2 5 5.8 5Z" />
      <Path d="M8 20.5h8" />
    </Frame>
  );
}

export function HouseIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="m3.5 11 8.5-7 8.5 7" />
      <Path d="M5.5 9.8V20h13V9.8" />
      <Path d="M10 20v-4.5h4V20" />
    </Frame>
  );
}

export function SpeakerIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4v-5Z" />
      <Path d="M15.5 9a4.2 4.2 0 0 1 0 6M18 6.5a7.8 7.8 0 0 1 0 11" />
    </Frame>
  );
}

export function StopIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7 6.5h10a.5.5 0 0 1 .5.5v10a.5.5 0 0 1-.5.5H7a.5.5 0 0 1-.5-.5V7a.5.5 0 0 1 .5-.5Z" />
    </Frame>
  );
}

export function PinIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z" />
      <Circle cx={12} cy={10} r={2.4} />
    </Frame>
  );
}

export function LocateIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={12} cy={12} r={6.5} />
      <Circle cx={12} cy={12} r={2} />
      <Path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3" />
    </Frame>
  );
}
