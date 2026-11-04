import { Circle, Line, Path, Rect } from 'react-native-svg';

import { colors } from '../theme';
import { Frame, type IconProps } from './frame';

export function MailIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Rect x={3} y={5} width={18} height={14} rx={2} />
      <Path d="m3.5 7 8.5 6 8.5-6" />
    </Frame>
  );
}

export function LockIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Rect x={4.5} y={10.5} width={15} height={9.5} rx={2} />
      <Path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
      <Circle cx={12} cy={15.5} r={1} fill={p.color ?? colors.ink} stroke="none" />
    </Frame>
  );
}

export function EyeIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
      <Circle cx={12} cy={12} r={3} />
    </Frame>
  );
}

export function EyeOffIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M4 4.5 20 19.5" />
      <Path d="M9.9 5.9A9.5 9.5 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-3 3.8M6 7.5A16 16 0 0 1 2.5 12S6 18.5 12 18.5c1 0 2-.2 2.8-.5" />
      <Path d="M9.5 9.8a3 3 0 0 0 4.1 4.1" />
    </Frame>
  );
}

export function UserIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={12} cy={8} r={3.8} />
      <Path d="M4.5 20.5c.8-3.8 3.8-5.8 7.5-5.8s6.7 2 7.5 5.8" />
    </Frame>
  );
}

export function PhoneIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M5.5 3.5h3.6l1.7 4.8-2.3 1.7a12.5 12.5 0 0 0 6 6l1.7-2.3 4.8 1.7v3.6a2 2 0 0 1-2 2A16.5 16.5 0 0 1 3.5 5.5a2 2 0 0 1 2-2Z" />
    </Frame>
  );
}

export function CheckIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="m4.5 12.5 5 5L19.5 7" />
    </Frame>
  );
}

export function CheckCircleIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={12} cy={12} r={8.7} />
      <Path d="m8.3 12.3 2.5 2.5 5-5.6" />
    </Frame>
  );
}

export function AlertIcon(p: IconProps) {
  const color = p.color ?? colors.ink;
  return (
    <Frame {...p}>
      <Path d="M12 3.5 2.8 19.5h18.4L12 3.5Z" />
      <Line x1={12} y1={9.5} x2={12} y2={13.8} />
      <Circle cx={12} cy={16.6} r={1} fill={color} stroke="none" />
    </Frame>
  );
}

export function InfoIcon(p: IconProps) {
  const color = p.color ?? colors.ink;
  return (
    <Frame {...p}>
      <Circle cx={12} cy={12} r={8.7} />
      <Line x1={12} y1={11} x2={12} y2={16} />
      <Circle cx={12} cy={8} r={1} fill={color} stroke="none" />
    </Frame>
  );
}

export function ArrowLeftIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M19 12H5m0 0 6-6m-6 6 6 6" />
    </Frame>
  );
}

export function ArrowRightIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M5 12h14m0 0-6-6m6 6-6 6" />
    </Frame>
  );
}

export function ChevronDownIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="m6 9.5 6 6 6-6" />
    </Frame>
  );
}

export function ChevronRightIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="m9.5 6 6 6-6 6" />
    </Frame>
  );
}

export function CloseIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M6 6l12 12M18 6 6 18" />
    </Frame>
  );
}

export function EditIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M4 20l1-4L16.6 4.4a2.05 2.05 0 0 1 2.9 2.9L8 19l-4 1Z" />
      <Path d="M14.5 6.5l3 3" />
    </Frame>
  );
}

export function SearchIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={11} cy={11} r={6.8} />
      <Line x1={15.8} y1={15.8} x2={20.5} y2={20.5} />
    </Frame>
  );
}

export function CalendarIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Rect x={3.5} y={5} width={17} height={15.5} rx={2} />
      <Line x1={3.5} y1={9.8} x2={20.5} y2={9.8} />
      <Line x1={8} y1={3} x2={8} y2={6.8} />
      <Line x1={16} y1={3} x2={16} y2={6.8} />
    </Frame>
  );
}

export function GlobeIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Circle cx={12} cy={12} r={8.7} />
      <Path d="M3.3 12h17.4" />
      <Path d="M12 3.3c2.4 2.4 3.7 5.5 3.7 8.7s-1.3 6.3-3.7 8.7c-2.4-2.4-3.7-5.5-3.7-8.7S9.6 5.7 12 3.3Z" />
    </Frame>
  );
}

export function LogoutIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M14.5 4.5h3a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-3" />
      <Path d="m10 8.5 3.5 3.5-3.5 3.5M13.5 12H3.5" />
    </Frame>
  );
}

export function TrashIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M4 7h16M9.5 7V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2M6.5 7l.9 13h9.2l.9-13" />
      <Line x1={10} y1={11} x2={10} y2={17} />
      <Line x1={14} y1={11} x2={14} y2={17} />
    </Frame>
  );
}

export function ShieldIcon(p: IconProps) {
  return (
    <Frame {...p}>
      <Path d="M12 3l7 2.8v6.1c0 4.3-2.9 7.2-7 8.6-4.1-1.4-7-4.3-7-8.6V5.8L12 3Z" />
      <Path d="m9.2 11.8 2 2 3.7-4" />
    </Frame>
  );
}
