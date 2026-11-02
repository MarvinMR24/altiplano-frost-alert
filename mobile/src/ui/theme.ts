import type { Level } from '@/api/types';

export const colors = {
  background: '#F7F7F5',
  surface: '#FFFFFF',
  text: '#1C1C1E',
  muted: '#6B6B70',
  border: '#E2E2E0',
  primary: '#1F4E79',
  danger: '#B42318',
  mockBanner: '#6E2C8E',
  coverageFill: 'rgba(46, 160, 67, 0.15)',
  coverageStroke: 'rgba(46, 160, 67, 0.6)',
  aoiFill: 'rgba(37, 99, 235, 0.18)',
  aoiStroke: '#2563EB',
  drawStroke: '#111827',
};

// Amber to red by level. Risk is never shown in green.
export const levelColors: Record<Level, string> = {
  low: '#F2C94C',
  moderate: '#F2994A',
  high: '#E8590C',
  very_high: '#C92A2A',
};

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
