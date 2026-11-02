import type { CoverageResponse, PolygonGeometry, Position } from '@/api/types';

export interface LatLng {
  latitude: number;
  longitude: number;
}

const EARTH_RADIUS_KM = 6371;

export function haversineKm(a: LatLng, b: LatLng): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h));
}

// Closed ring of `vertices` points approximating a circle (good enough at 30 km).
export function circlePolygon(center: LatLng, radiusKm: number, vertices = 48): PolygonGeometry {
  const ring: Position[] = [];
  const latRad = (center.latitude * Math.PI) / 180;
  for (let i = 0; i < vertices; i++) {
    const angle = (2 * Math.PI * i) / vertices;
    const dLat = (radiusKm / EARTH_RADIUS_KM) * Math.cos(angle) * (180 / Math.PI);
    const dLon =
      ((radiusKm / EARTH_RADIUS_KM) * Math.sin(angle) * (180 / Math.PI)) / Math.cos(latRad);
    ring.push([round6(center.longitude + dLon), round6(center.latitude + dLat)]);
  }
  ring.push(ring[0]);
  return { type: 'Polygon', coordinates: [ring] };
}

function round6(x: number): number {
  return Math.round(x * 1e6) / 1e6;
}

// Ray casting on a GeoJSON ring ([lon, lat]).
export function pointInRing(point: LatLng, ring: Position[]): boolean {
  const x = point.longitude;
  const y = point.latitude;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

export function pointInCoverage(point: LatLng, coverage: CoverageResponse): boolean {
  return coverage.features.some((f) => pointInRing(point, f.geometry.coordinates[0]));
}

// Area-weighted centroid of a simple polygon; falls back to the vertex mean when degenerate.
export function centroid(points: LatLng[]): LatLng {
  let area = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    const cross = a.longitude * b.latitude - b.longitude * a.latitude;
    area += cross;
    cx += (a.longitude + b.longitude) * cross;
    cy += (a.latitude + b.latitude) * cross;
  }
  if (Math.abs(area) < 1e-12) {
    const n = points.length || 1;
    return {
      latitude: points.reduce((s, p) => s + p.latitude, 0) / n,
      longitude: points.reduce((s, p) => s + p.longitude, 0) / n,
    };
  }
  area /= 2;
  return { latitude: cy / (6 * area), longitude: cx / (6 * area) };
}

// The client-side check before POST /aois: every vertex and the centroid inside coverage.
export function polygonInsideCoverage(points: LatLng[], coverage: CoverageResponse): boolean {
  return [...points, centroid(points)].every((p) => pointInCoverage(p, coverage));
}

export function toPolygon(points: LatLng[]): PolygonGeometry {
  const ring: Position[] = points.map((p) => [p.longitude, p.latitude]);
  ring.push(ring[0]);
  return { type: 'Polygon', coordinates: [ring] };
}

export function fromPolygon(polygon: PolygonGeometry): LatLng[] {
  const ring = polygon.coordinates[0] ?? [];
  const open = ring.length > 1 ? ring.slice(0, -1) : ring;
  return open.map(([lon, lat]) => ({ latitude: lat, longitude: lon }));
}
