import type { Level } from '@/api/types';

export const colors = {
  navy: '#0F2A44',
  navyLight: '#1F4E79',
  navyDeep: '#0B1F33',
  beige: '#F4EDE1',
  sand: '#E7DAC4',
  ink: '#1B1F24',
  black: '#000000',
  red: '#B3261E',
  teal: '#2F7E6E',
  ridge: '#3A5068',
  iceBlue: '#9FB4C7',
  logoMountain: '#8FA9C2',
  plainLine: '#B49F76',
  plainEnd: '#D9CBAE',
  background: '#F4EDE1',
  surface: '#FBF7EE',
  text: '#1B1F24',
  muted: '#4A5560',
  border: '#D8CBB2',
  primary: '#0F2A44',
  primaryText: '#F4EDE1',
  danger: '#B3261E',
  dangerText: '#FFFFFF',
  mockBanner: '#0F2A44',
  white: '#FFFFFF',
  coverageFill: 'rgba(31, 78, 121, 0.22)',
  coverageStroke: 'rgba(15, 42, 68, 0.55)',
  aoiFill: 'rgba(31, 78, 121, 0.34)',
  // Light outline drawn under map strokes so shapes read on dark satellite imagery.
  mapHalo: '#F4EDE1',
  transparent: 'transparent',
  mapShadow: 'rgba(0, 0, 0, 0.35)',
  outsideText: '#7A848E',
  aoiStroke: '#0F2A44',
  drawStroke: '#0F2A44',
  drawInvalid: '#B3261E',
  headerBg: '#0F2A44',
  headerText: '#F4EDE1',
  tabActive: '#0F2A44',
  tabInactive: '#6B7683',
  tabBg: '#F4EDE1',
  cardShadow: 'rgba(15, 42, 68, 0.12)',
  backdrop: 'rgba(15, 42, 68, 0.45)',
  pinBorder: '#FFFFFF',
  navButtonBg: '#E7DAC4',
};

// Ordered low to very_high. Never green. Always paired with text and an icon.
export const levelColors: Record<Level, string> = {
  low: '#C9A227',
  moderate: '#C96A1B',
  high: '#A83226',
  very_high: '#6E1423',
};

// Text color on top of each level badge. Chosen for at least 4.5:1 contrast.
export const levelOnColors: Record<Level, string> = {
  low: '#1B1F24',
  moderate: '#1B1F24',
  high: '#FFFFFF',
  very_high: '#FFFFFF',
};

export const levelIcons = {
  low: 'moon-stars',
  moderate: 'cloud',
  high: 'snowflake',
  very_high: 'alert',
} as const;

export const LEVELS: Level[] = ['low', 'moderate', 'high', 'very_high'];

// Same cut points as docs/api_contract.md.
export function levelFromProbability(p: number): Level {
  if (p >= 0.7) return 'very_high';
  if (p >= 0.5) return 'high';
  if (p >= 0.3) return 'moderate';
  return 'low';
}

export function percent(p: number): number {
  return Math.round(p * 100);
}

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
export const radius = { sm: 8, md: 12, lg: 16 };
