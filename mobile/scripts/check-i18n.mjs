// Key parity: es.ts is the source of truth. en.ts must have exactly the same keys;
// ay.ts and qu.ts spread es plus native overrides, so their override keys must be a
// subset of es keys. Run: node scripts/check-i18n.mjs
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'i18n');
const read = (name) => readFileSync(join(dir, name), 'utf8');

function keysOf(source) {
  return [...source.matchAll(/^\s*'([A-Za-z0-9_.]+)':/gm)].map((m) => m[1]);
}

const es = read('es.ts');
const esKeys = new Set(keysOf(es));
let failed = false;

function check(name, source, subset) {
  const keys = keysOf(source);
  const dupes = keys.filter((k, i) => keys.indexOf(k) !== i);
  const unknown = keys.filter((k) => !esKeys.has(k));
  if (dupes.length > 0 || unknown.length > 0) {
    failed = true;
    console.error(`${name}: dupes=[${[...new Set(dupes)]}] unknown=[${[...new Set(unknown)]}]`);
  }
  if (!subset) {
    const missing = [...esKeys].filter((k) => !keys.includes(k));
    if (missing.length > 0) {
      failed = true;
      console.error(`${name}: missing=[${missing}]`);
    }
  }
  console.log(`${name}: ${keys.length} keys ok${subset ? ' (subset of es)' : ''}`);
}

check('en.ts', read('en.ts'), false);
for (const name of ['ay.ts', 'qu.ts']) {
  const source = read(name);
  if (!source.includes('...es,')) {
    failed = true;
    console.error(`${name}: must spread es for the Spanish fallback`);
  }
  check(name, source, true);
}

// Every override key in ay/qu must differ from es (else it is not a translation).
for (const name of ['ay.ts', 'qu.ts']) {
  const source = read(name);
  const same = [];
  for (const m of source.matchAll(/^\s*'([A-Za-z0-9_.]+)':\s*'((?:[^'\\]|\\.)*)',?\s*$/gm)) {
    const esMatch = es.match(new RegExp(`^\\s*'${m[1]}':\\s*'((?:[^'\\\\]|\\\\.)*)',?\\s*$`, 'm'));
    if (esMatch && esMatch[1] === m[2]) same.push(m[1]);
  }
  if (same.length > 0) console.log(`${name}: identical to es (keep only for shared words): [${same}]`);
}

if (failed) process.exit(1);
console.log('i18n parity ok');
