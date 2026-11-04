import type { ReactNode } from 'react';
import Svg from 'react-native-svg';

import { colors } from '../theme';

export interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
}

// Shared outline style: 24x24 viewBox, rounded caps and joins.
export function Frame({
  size = 24,
  color = colors.ink,
  strokeWidth = 1.75,
  children,
}: IconProps & { children: ReactNode }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </Svg>
  );
}
