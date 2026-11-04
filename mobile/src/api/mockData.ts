// MOCK DATA. Every number here is arbitrary and exists only to exercise the UI offline.
// It is not model output and must never be presented as a result.

import { circlePolygon } from '@/geo';
import { levelFromProbability } from '@/ui/theme';
import type { Cell, CoverageResponse, Driver, ModelCard, Observed } from './types';

export const MOCK_DATA_SOURCE = 'MOCK DATA (shaped like ERA5-Land reanalysis, Copernicus CDS)';
export const MOCK_MODEL_VERSION = 'mock-0';
export const COVERAGE_RADIUS_KM = 30;

interface MockCellBase {
  point_id: string;
  name: string;
  lat: number;
  lon: number;
  elevation_m: number;
}

export const MOCK_CELLS: MockCellBase[] = [
  { point_id: 'el_alto', name: 'El Alto', lat: -16.5, lon: -68.2, elevation_m: 4050 },
  { point_id: 'oruro', name: 'Oruro', lat: -18.0, lon: -67.1, elevation_m: 3710 },
  { point_id: 'patacamaya', name: 'Patacamaya', lat: -17.2, lon: -67.9, elevation_m: 3790 },
  { point_id: 'calamarca', name: 'Calamarca', lat: -17.0, lon: -68.1, elevation_m: 3990 },
  { point_id: 'caracollo', name: 'Caracollo', lat: -17.6, lon: -67.2, elevation_m: 3780 },
  { point_id: 'corocoro', name: 'Corocoro', lat: -17.2, lon: -69.1, elevation_m: 4010 },
  { point_id: 'charana', name: 'Charaña', lat: -17.6, lon: -69.4, elevation_m: 4060 },
  { point_id: 'huanuni', name: 'Huanuni', lat: -18.3, lon: -66.8, elevation_m: 3950 },
];

export const MOCK_NIGHTS = ['2025-07-12', '2025-07-13', '2025-07-14', '2025-07-15'];

// Arbitrary probabilities per night (rows) and cell (columns, MOCK_CELLS order),
// spread over the four levels.
const MOCK_PROBABILITIES: number[][] = [
  [0.22, 0.41, 0.55, 0.63, 0.35, 0.78, 0.86, 0.48],
  [0.18, 0.33, 0.47, 0.58, 0.29, 0.71, 0.82, 0.52],
  [0.12, 0.26, 0.38, 0.44, 0.21, 0.62, 0.74, 0.36],
  [0.27, 0.52, 0.68, 0.73, 0.45, 0.88, 0.93, 0.61],
];

const RELIABILITY_BINS: { range: [number, number]; observed_rate: number; n: number }[] = [
  { range: [0, 0.3], observed_rate: 0.08, n: 1200 },
  { range: [0.3, 0.5], observed_rate: 0.36, n: 410 },
  { range: [0.5, 0.7], observed_rate: 0.58, n: 300 },
  { range: [0.7, 1], observed_rate: 0.81, n: 260 },
];

function reliabilityFor(p: number) {
  return RELIABILITY_BINS.find((b) => p >= b.range[0] && p < b.range[1]) ?? RELIABILITY_BINS[3];
}

function driversFor(p: number): Driver[] {
  return [
    { feature: 'dewpoint_depression_c', effect: 'up', weight: round2(0.3 + p * 0.5) },
    { feature: 'tcc_pct', effect: p > 0.4 ? 'up' : 'down', weight: round2(0.2 + p * 0.3) },
    { feature: 'wind_ms', effect: 'down', weight: round2(0.15 + (1 - p) * 0.2) },
  ];
}

function conditionsFor(p: number, elevation: number) {
  return {
    t2m_c: round1(9 - p * 7 - (elevation - 3700) / 300),
    d2m_c: round1(-6 - p * 8),
    rh_pct: Math.round(45 - p * 25),
    wind_ms: round1(4 - p * 2.5),
    tcc_pct: Math.round(60 - p * 55),
  };
}

function observedFor(p: number, index: number): Observed {
  // Deterministic mock outcome; includes a miss and a false alarm on purpose.
  const frost = (p >= 0.5) !== (index % 5 === 3);
  return { frost, tmin_c: round1(frost ? -2 - p * 6 : 1.5 + (1 - p) * 3) };
}

export function mockCellsFor(night: string): Cell[] {
  const nightIndex = Math.max(0, MOCK_NIGHTS.indexOf(night));
  const isLatest = nightIndex === MOCK_NIGHTS.length - 1;
  return MOCK_CELLS.map((base, i) => {
    const p = MOCK_PROBABILITIES[nightIndex][i];
    const cell: Cell = {
      ...base,
      probability: p,
      level: levelFromProbability(p),
      top_drivers: driversFor(p),
      conditions_1800: conditionsFor(p, base.elevation_m),
      historical_reliability: reliabilityFor(p),
    };
    if (!isLatest) cell.observed = observedFor(p, i + nightIndex);
    return cell;
  });
}

export function mockCoverage(): CoverageResponse {
  return {
    type: 'FeatureCollection',
    features: MOCK_CELLS.map((c) => ({
      type: 'Feature',
      geometry: circlePolygon({ latitude: c.lat, longitude: c.lon }, COVERAGE_RADIUS_KM, 48),
      properties: { point_id: c.point_id, name: c.name },
    })),
    meta: { radius_km: COVERAGE_RADIUS_KM },
  };
}

export const MOCK_MODEL_CARD: ModelCard = {
  model_version: MOCK_MODEL_VERSION,
  trained_years: [0, 0],
  n_cells: MOCK_CELLS.length,
  metrics: {
    validation: {
      pr_auc: 0.5, f2: 0.5, precision: 0.5, recall: 0.5, f1: 0.5,
      roc_auc: 0.5, brier: 0.25, accuracy: 0.5, majority_accuracy: 0.5,
    },
    test: {
      pr_auc: 0.5, f2: 0.5, precision: 0.5, recall: 0.5, f1: 0.5,
      roc_auc: 0.5, brier: 0.25, accuracy: 0.5, majority_accuracy: 0.5,
    },
  },
  limitations: [
    'MOCK DATA: these values are placeholders, not real model metrics.',
    'Labels come from the same ERA5-Land reanalysis used for the features.',
    'Reanalysis is published a few days late, so there is no live forecast.',
  ],
};

export const MOCK_EXPLANATION_TEXT: Record<
  'es' | 'en',
  { headline: (name: string) => string; why: string; actions: string[]; caveats: string[]; summary: string }
> = {
  es: {
    headline: (name) => `Riesgo de helada en ${name} (simulado)`,
    why: 'Aire seco y cielo despejado al atardecer favorecen el enfriamiento nocturno. Texto simulado.',
    actions: [
      'Cubrir cultivos sensibles antes del anochecer.',
      'Resguardar el ganado joven en corrales protegidos.',
      'Proteger tuberías de agua expuestas.',
    ],
    caveats: [
      'DATOS SIMULADOS. No es una predicción real.',
      'Datos de reanálisis ERA5-Land, no un pronóstico en vivo.',
    ],
    summary: 'Modelo simulado mock-0. Las métricas reales aparecerán cuando el modelo esté entrenado.',
  },
  en: {
    headline: (name) => `Frost risk in ${name} (mock)`,
    why: 'Dry air and clear skies at dusk favor night cooling. Mock text.',
    actions: [
      'Cover sensitive crops before dusk.',
      'Keep young livestock in sheltered pens.',
      'Protect exposed water pipes.',
    ],
    caveats: ['MOCK DATA. Not a real prediction.', 'ERA5-Land reanalysis data, not a live forecast.'],
    summary: 'Mock model mock-0. Real metrics will appear once the model is trained.',
  },
};

function round1(x: number): number {
  return Math.round(x * 10) / 10;
}

function round2(x: number): number {
  return Math.round(x * 100) / 100;
}
