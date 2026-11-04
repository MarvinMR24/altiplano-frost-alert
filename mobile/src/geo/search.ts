// Place search (geocoding) with no API key. Providers: local (the 8 coverage cells, no
// network), Photon (komoot) and Nominatim (OpenStreetMap) as a fallback. Both remote
// services are used within their usage policies: minimum query length, debounce in the
// caller, at most one request per second, an in-memory cache per query and cancellation
// of stale requests. Pure TypeScript (no React Native imports) so node can unit test it.

export interface Place {
  id: string;
  name: string;
  // Second line: municipality, department, country.
  detail: string;
  latitude: number;
  longitude: number;
  source: 'local' | 'photon' | 'nominatim';
}

export interface PlaceResult extends Place {
  inCoverage: boolean;
}

export interface SearchOptions {
  lang: 'es' | 'en';
  signal?: AbortSignal;
}

export interface Provider {
  name: Place['source'];
  search(query: string, options: SearchOptions): Promise<Place[]>;
}

type FetchFn = (url: string, init?: { headers?: Record<string, string>; signal?: AbortSignal }) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

export const MIN_QUERY_LENGTH = 3;
export const MAX_RESULTS = 6;
export const DEBOUNCE_MS = 500;
export const MIN_INTERVAL_MS = 1000;
// Coverage of the 8 cells plus a margin: west, south, east, north.
export const SEARCH_BBOX = { west: -70.2, south: -19.2, east: -65.9, north: -15.6 };

const PHOTON_URL = 'https://photon.komoot.io/api/';
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

export class SearchUnavailableError extends Error {
  constructor() {
    super('search unavailable');
    this.name = 'SearchUnavailableError';
  }
}

export function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

export function shouldSearch(query: string): boolean {
  return normalize(query).length >= MIN_QUERY_LENGTH;
}

function joinDetail(parts: (string | undefined)[], name: string): string {
  const seen = new Set<string>([normalize(name)]);
  const out: string[] = [];
  for (const part of parts) {
    if (!part) continue;
    const key = normalize(part);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(part);
  }
  return out.join(', ');
}

// Photon returns GeoJSON features with [lon, lat] points.
export function parsePhoton(json: unknown): Place[] {
  const features = (json as { features?: unknown[] })?.features;
  if (!Array.isArray(features)) return [];
  const places: Place[] = [];
  for (const f of features) {
    const feature = f as {
      geometry?: { coordinates?: [number, number] };
      properties?: Record<string, string | number | undefined>;
    };
    const coords = feature.geometry?.coordinates;
    const p = feature.properties ?? {};
    const name = typeof p.name === 'string' ? p.name : undefined;
    if (!name || !Array.isArray(coords) || coords.length < 2) continue;
    const [longitude, latitude] = coords;
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;
    const str = (k: string) => (typeof p[k] === 'string' ? (p[k] as string) : undefined);
    places.push({
      id: `photon:${p.osm_type ?? ''}${p.osm_id ?? `${latitude},${longitude}`}`,
      name,
      detail: joinDetail([str('city') ?? str('county'), str('state'), str('country')], name),
      latitude,
      longitude,
      source: 'photon',
    });
  }
  return places.slice(0, MAX_RESULTS);
}

// Nominatim jsonv2 returns an array with string coordinates and a comma separated
// display_name whose first part is the place itself.
export function parseNominatim(json: unknown): Place[] {
  if (!Array.isArray(json)) return [];
  const places: Place[] = [];
  for (const item of json) {
    const r = item as { place_id?: number; lat?: string; lon?: string; name?: string; display_name?: string };
    const latitude = Number(r.lat);
    const longitude = Number(r.lon);
    const parts = (r.display_name ?? '').split(',').map((s) => s.trim()).filter(Boolean);
    const name = r.name || parts[0];
    if (!name || !Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;
    // Keep municipality, department and country: the last three parts.
    places.push({
      id: `nominatim:${r.place_id ?? `${latitude},${longitude}`}`,
      name,
      detail: joinDetail(parts.slice(1).slice(-3), name),
      latitude,
      longitude,
      source: 'nominatim',
    });
  }
  return places.slice(0, MAX_RESULTS);
}

async function getJson(fetchFn: FetchFn, url: string, headers: Record<string, string>, signal?: AbortSignal) {
  const response = await fetchFn(url, { headers, signal });
  if (!response.ok) throw new Error(`http ${response.status}`);
  return response.json();
}

export function photonProvider(fetchFn: FetchFn, headers: Record<string, string> = {}): Provider {
  const { west, south, east, north } = SEARCH_BBOX;
  return {
    name: 'photon',
    async search(query, { lang, signal }) {
      const url =
        `${PHOTON_URL}?q=${encodeURIComponent(query)}&limit=${MAX_RESULTS}&lang=${lang}` +
        `&bbox=${west},${south},${east},${north}`;
      return parsePhoton(await getJson(fetchFn, url, headers, signal));
    },
  };
}

export function nominatimProvider(fetchFn: FetchFn, headers: Record<string, string> = {}): Provider {
  const { west, south, east, north } = SEARCH_BBOX;
  return {
    name: 'nominatim',
    async search(query, { lang, signal }) {
      const url =
        `${NOMINATIM_URL}?format=jsonv2&q=${encodeURIComponent(query)}&limit=${MAX_RESULTS}` +
        `&countrycodes=bo,pe&viewbox=${west},${north},${east},${south}&bounded=1&accept-language=${lang}`;
      return parseNominatim(await getJson(fetchFn, url, headers, signal));
    },
  };
}

// Offline search in the coverage cell names (from GET /coverage).
export function localSearch(query: string, places: Place[]): Place[] {
  const q = normalize(query);
  if (!q) return [];
  return places.filter((p) => normalize(p.name).includes(q)).slice(0, MAX_RESULTS);
}

function isAbort(err: unknown): boolean {
  return (err as { name?: string })?.name === 'AbortError';
}

// Remote search with fallback, cache and a minimum interval between requests.
export class PlaceSearcher {
  private cache = new Map<string, Place[]>();
  private lastRequestAt = -Infinity;
  // Plain fields (no parameter properties) so node can strip the types in unit tests.
  private providers: Provider[];
  private clock: { now(): number; sleep(ms: number): Promise<void> };

  constructor(
    providers: Provider[],
    clock: { now(): number; sleep(ms: number): Promise<void> } = {
      now: () => Date.now(),
      sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    },
  ) {
    this.providers = providers;
    this.clock = clock;
  }

  cached(query: string, lang: string): Place[] | undefined {
    return this.cache.get(`${lang}:${normalize(query)}`);
  }

  async search(query: string, options: SearchOptions): Promise<Place[]> {
    const key = `${options.lang}:${normalize(query)}`;
    const hit = this.cache.get(key);
    if (hit) return hit;
    let lastError: unknown = null;
    for (const provider of this.providers) {
      const wait = this.lastRequestAt + MIN_INTERVAL_MS - this.clock.now();
      if (wait > 0) await this.clock.sleep(wait);
      if (options.signal?.aborted) throw abortError();
      this.lastRequestAt = this.clock.now();
      try {
        const places = await provider.search(query, options);
        this.cache.set(key, places);
        return places;
      } catch (err) {
        if (isAbort(err)) throw err;
        lastError = err;
      }
    }
    throw lastError ? new SearchUnavailableError() : abortError();
  }
}

function abortError(): Error {
  const err = new Error('aborted');
  err.name = 'AbortError';
  return err;
}

// Marks results inside the coverage and puts local (cell) results first, without duplicates.
export function mergeResults(local: Place[], remote: Place[], isCovered: (p: Place) => boolean): PlaceResult[] {
  const seen = new Set<string>();
  const out: PlaceResult[] = [];
  for (const p of [...local, ...remote]) {
    const key = `${normalize(p.name)}:${p.latitude.toFixed(2)},${p.longitude.toFixed(2)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ ...p, inCoverage: p.source === 'local' || isCovered(p) });
  }
  return out.slice(0, MAX_RESULTS);
}

// Trailing debounce with injectable timers (for tests).
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  ms: number,
  timers: { set: (cb: () => void, ms: number) => unknown; clear: (id: unknown) => void } = {
    set: (cb, delay) => setTimeout(cb, delay),
    clear: (id) => clearTimeout(id as ReturnType<typeof setTimeout>),
  },
): { call: (...args: A) => void; cancel: () => void } {
  let id: unknown = null;
  return {
    call: (...args) => {
      if (id !== null) timers.clear(id);
      id = timers.set(() => {
        id = null;
        fn(...args);
      }, ms);
    },
    cancel: () => {
      if (id !== null) timers.clear(id);
      id = null;
    },
  };
}
