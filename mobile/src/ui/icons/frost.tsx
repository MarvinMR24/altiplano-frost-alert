import { Circle, Path } from 'react-native-svg';

import { Frame, type IconProps } from './frame';

export function SnowflakeIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 2.5v19M4.2 7.5l15.6 9M19.8 7.5l-15.6 9" />
      <Path d="M12 5.5 9.8 4.2M12 5.5l2.2-1.3M12 18.5l-2.2 1.3M12 18.5l2.2 1.3" />
      <Path d="M6.6 6.6 5 7.2M6.6 6.6l.4-1.9M17.4 17.4l1.6-.6m-1.6.6-.4 1.9" />
      <Path d="M17.4 6.6l1.6.6m-1.6-.6.4-1.9M6.6 17.4 5 16.8m1.6.6-.4 1.9" />
    </Frame>
  );
}

export function ThermometerLowIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M10 5a2 2 0 0 1 4 0v8.6a4.3 4.3 0 1 1-4 0V5Z" />
      <Path d="M6.5 15.5h3M5.5 18.5h2" />
      <Circle cx={12} cy={17.8} r={1.6} />
    </Frame>
  );
}

export function MoonStarsIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M20 14.5A8 8 0 1 1 9.5 4a6.3 6.3 0 0 0 10.5 10.5Z" />
      <Path d="M18.5 3.5v3M17 5h3" />
      <Path d="M6.5 5v2M5.5 6h2" />
    </Frame>
  );
}

export function CloudIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M7 18.5a4 4 0 0 1-.6-7.95A5.5 5.5 0 0 1 17.2 12 3.4 3.4 0 0 1 17 18.5H7Z" />
    </Frame>
  );
}

export function WindIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M9.6 4.3A2 2 0 1 1 11 8H3" />
      <Path d="M12.4 19.7A2 2 0 1 0 14 16H3" />
      <Path d="M19.7 7.8A2.5 2.5 0 1 1 19.5 12H3" />
    </Frame>
  );
}

export function DropletIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 3.5s6 6.6 6 10.7a6 6 0 0 1-12 0C6 10.1 12 3.5 12 3.5Z" />
    </Frame>
  );
}

export function MountainIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M3 20 9 8.5l3.8 6 2.4-3.3L21 20H3Z" />
      <Path d="M9 8.5 7.6 11M9 8.5l1.5 2.4" />
    </Frame>
  );
}

export function SunriseIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 9.5V3.5m0 0L9.5 6M12 3.5 14.5 6" />
      <Path d="M5 10.5l1.2 1.2M19 10.5l-1.2 1.2" />
      <Path d="M17 17.5a5 5 0 0 0-10 0" />
      <Path d="M3.5 17.5h17M8 21h8" />
    </Frame>
  );
}
