// Unit tests for pure helpers (calendar grid, catalog search) plus content checks on
// the shipped catalogs. No test framework: plain node asserts. Run: node scripts/unit-tests.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { addMonths, monthGrid, monthName, toIso, weekdayNames, yearsInRange } from '../src/date/calendar.ts';
import { itemMatches, labelFor, normalizeQuery } from '../src/catalog/catalog.ts';
import {
  debounce,
  localSearch,
  mergeResults,
  nominatimProvider,
  parseNominatim,
  parsePhoton,
  photonProvider,
  PlaceSearcher,
  SearchUnavailableError,
  shouldSearch,
} from '../src/geo/search.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
let count = 0;
function ok(value, message) {
  count++;
  assert.ok(value, message);
}

// Calendar: month boundaries. August 2024: the 1st was a Thursday.
{
  const weeks = monthGrid(2024, 7);
  ok(weeks.length === 5, `aug 2024 has 5 weeks, got ${weeks.length}`);
  ok(weeks[0][0] === null && weeks[0][3]?.iso === '2024-08-01', 'aug 1 2024 lands on Thursday');
  ok(weeks[4][5]?.iso === '2024-08-31', 'aug 31 2024 lands on Saturday');
  ok(weeks[4][6] === null, 'the cell after aug 31 2024 is empty');
  ok(weeks.every((w) => w.length === 7), 'every week has 7 cells');
}
// Leap year: Feb 2024 has 29 days, Feb 2023 has 28.
{
  const days = (y) => monthGrid(y, 1).flat().filter(Boolean).length;
  ok(days(2024) === 29, 'feb 2024 has 29 days');
  ok(days(2023) === 28, 'feb 2023 has 28 days');
}
// Monday first: Jan 2024 starts on Monday, Sep 2024 starts on Sunday.
{
  const jan = monthGrid(2024, 0);
  ok(jan[0][0]?.iso === '2024-01-01', 'jan 1 2024 is the first cell (Monday)');
  const sep = monthGrid(2024, 8);
  ok(sep[0][6]?.iso === '2024-09-01', 'sep 1 2024 is the last cell (Sunday)');
}
ok(toIso(2024, 0, 5) === '2024-01-05', 'toIso pads month and day');
ok(JSON.stringify(addMonths(2024, 11, 1)) === JSON.stringify({ year: 2025, month: 0 }), 'dec + 1 wraps the year');
ok(JSON.stringify(addMonths(2024, 0, -1)) === JSON.stringify({ year: 2023, month: 11 }), 'jan - 1 wraps the year');
ok(monthName('es', 7).toLowerCase().startsWith('ago'), `spanish august, got ${monthName('es', 7)}`);
ok(weekdayNames('es').length === 7 && weekdayNames('en').length === 7, 'seven weekday names');
ok(JSON.stringify(yearsInRange('2018-07-15', '2026-10-26')) === JSON.stringify([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]), 'year range');

// Catalog search: accents, case, synonyms, language fallback.
{
  const item = { id: 'x', category: 'tuber', labels: { es: 'Haba', en: 'Broad bean', qu: 'Hawas' }, synonyms: ['habas'], icon: 'legume' };
  ok(normalizeQuery('ChUñO') === 'chuno', 'normalize strips accents and case');
  ok(itemMatches(item, 'haba', 'es'), 'matches the spanish label');
  ok(itemMatches(item, 'HABAS', 'en'), 'matches synonyms case insensitively');
  ok(itemMatches(item, 'broad', 'en'), 'matches the english label');
  ok(itemMatches(item, 'hawas', 'qu'), 'matches the quechua label');
  ok(!itemMatches(item, 'papa', 'es'), 'rejects other words');
  ok(labelFor(item, 'qu') === 'Hawas', 'quechua label wins when present');
  ok(labelFor(item, 'ay') === 'Haba', 'aymara falls back to spanish');
}

// Catalog content: old ids kept, minimum sizes, no invented agronomy.
for (const [file, minItems, oldIds] of [
  ['src/catalog/crops.ts', 30, ['potato', 'quinoa', 'barley', 'broad_bean', 'oca', 'alfalfa']],
  ['src/catalog/livestock.ts', 12, ['llama', 'alpaca', 'sheep', 'cattle']],
]) {
  const source = readFileSync(join(root, file), 'utf8');
  const code = source.replace(/^\/\/.*$/gm, '');
  const ids = [...code.matchAll(/id: '([a-z0-9_]+)'/g)].map((m) => m[1]);
  ok(ids.length >= minItems, `${file} has ${ids.length} items, need ${minItems}`);
  ok(new Set(ids).size === ids.length, `${file} ids are unique`);
  for (const id of oldIds) ok(ids.includes(id), `${file} keeps old id ${id}`);
  ok(!/°C|threshold|damage/i.test(code), `${file} has no invented agronomy numbers`);
  ok(!/vicu/i.test(code), `${file} has no vicuña`);
}

// Place search: parsing, coverage filtering, fallback, cache, rate limit, debounce.
// fetch is mocked; no request leaves the machine.
{
  const photon = {
    features: [
      { geometry: { coordinates: [-68.25, -17.25] }, properties: { osm_type: 'N', osm_id: 1, name: 'Patacamaya', county: 'Aroma', state: 'La Paz', country: 'Bolivia' } },
      { geometry: { coordinates: [-71.97, -13.53] }, properties: { osm_type: 'N', osm_id: 2, name: 'Cusco', city: 'Cusco', state: 'Cusco', country: 'Perú' } },
      { geometry: {}, properties: { name: 'broken' } },
    ],
  };
  const parsed = parsePhoton(photon);
  ok(parsed.length === 2, 'photon skips features without coordinates');
  ok(parsed[0].name === 'Patacamaya' && parsed[0].latitude === -17.25 && parsed[0].longitude === -68.25, 'photon reads [lon, lat]');
  ok(parsed[0].detail === 'Aroma, La Paz, Bolivia', `photon detail, got ${parsed[0].detail}`);
  ok(parsed[1].detail === 'Perú', 'photon detail drops parts equal to the name');

  const nominatim = [{ place_id: 9, lat: '-17.65', lon: '-68.50', name: 'Corocoro', display_name: 'Corocoro, Pacajes, La Paz, Bolivia' }];
  const n = parseNominatim(nominatim);
  ok(n.length === 1 && n[0].latitude === -17.65 && n[0].detail === 'Pacajes, La Paz, Bolivia', 'nominatim parsing');
  ok(parsePhoton(null).length === 0 && parseNominatim({}).length === 0, 'bad payloads give no results');

  ok(!shouldSearch('pa') && shouldSearch('pat') && !shouldSearch('  á '), 'minimum 3 characters');

  const cells = [{ id: 'cell:patacamaya', name: 'Patacamaya', detail: '', latitude: -17.24, longitude: -67.92, source: 'local' }];
  ok(localSearch('PATAC', cells).length === 1 && localSearch('oruro', cells).length === 0, 'local search by cell name');
  const covered = (p) => p.longitude > -69 && p.latitude < -16;
  const merged = mergeResults(cells, parsed, covered);
  ok(merged[0].source === 'local' && merged[0].inCoverage, 'local results come first and are covered');
  ok(merged.find((r) => r.name === 'Cusco')?.inCoverage === false, 'outside results are marked');

  // Fallback to Nominatim when Photon fails; cache; one request per second.
  const urls = [];
  let photonUp = false;
  const fakeFetch = async (url) => {
    urls.push(url);
    if (url.includes('photon') && !photonUp) return { ok: false, status: 503, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => (url.includes('photon') ? photon : nominatim) };
  };
  let now = 0;
  const sleeps = [];
  const clock = { now: () => now, sleep: async (ms) => { sleeps.push(ms); now += ms; } };
  const searcher = new PlaceSearcher([photonProvider(fakeFetch), nominatimProvider(fakeFetch)], clock);
  const first = await searcher.search('corocoro', { lang: 'es' });
  ok(first[0].source === 'nominatim', 'falls back to nominatim');
  ok(urls[0].includes('bbox=-70.2,-19.2,-65.9,-15.6') && urls[0].includes('lang=es'), 'photon url has bbox and lang');
  ok(urls[1].includes('viewbox=-70.2,-15.6,-65.9,-19.2') && urls[1].includes('bounded=1') && urls[1].includes('countrycodes=bo,pe'), 'nominatim url has viewbox');
  ok(sleeps.length === 1 && sleeps[0] === 1000, `waits 1 s between requests, got ${sleeps}`);
  await searcher.search('Corocoro ', { lang: 'es' });
  ok(urls.length === 2, 'second identical query is served from cache');

  const down = new PlaceSearcher([photonProvider(async () => { throw new TypeError('offline'); })], clock);
  let offline = false;
  try { await down.search('oruro', { lang: 'es' }); } catch (err) { offline = err instanceof SearchUnavailableError; }
  ok(offline, 'network failure reports search unavailable');

  const controller = new AbortController();
  controller.abort();
  let aborted = false;
  try { await new PlaceSearcher([photonProvider(fakeFetch)], clock).search('oruro', { lang: 'es', signal: controller.signal }); }
  catch (err) { aborted = err.name === 'AbortError'; }
  ok(aborted, 'an aborted search does not request');

  // Debounce: only the last call inside the window runs.
  const timers = [];
  const fakeTimers = { set: (cb) => { timers.push(cb); return timers.length - 1; }, clear: (id) => { timers[id] = null; } };
  const calls = [];
  const d = debounce((q) => calls.push(q), 500, fakeTimers);
  d.call('pat'); d.call('pata'); d.call('patac');
  timers.forEach((cb) => cb?.());
  ok(calls.length === 1 && calls[0] === 'patac', 'debounce keeps only the last query');
}

console.log(`unit tests ok (${count} assertions)`);
