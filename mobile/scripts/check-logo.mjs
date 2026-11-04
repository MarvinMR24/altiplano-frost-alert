// Checks that the logo SVG files use the same artwork constants as src/ui/logo.tsx.
// Run: node scripts/check-logo.mjs
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tsx = readFileSync(join(root, 'src/ui/logo.tsx'), 'utf8');

function constant(name) {
  const match = tsx.match(new RegExp(`const ${name} =\\s*'([^']+)'`));
  if (!match) throw new Error(`constant ${name} not found in logo.tsx`);
  return match[1];
}

const art = { ARM: constant('ARM'), HEX: constant('HEX'), MOON: constant('MOON'), MASSIF: constant('MASSIF') };
const files = ['logo.svg', 'logo-mono.svg', 'logo-horizontal.svg'];
let failed = false;
for (const file of files) {
  const svg = readFileSync(join(root, 'assets', file), 'utf8');
  const arms = [...svg.matchAll(/d="(M11 0H48[^"]*)"/g)].map((m) => m[1]);
  const problems = [];
  if (arms.length !== 6 || arms.some((d) => d !== art.ARM)) problems.push(`snowflake arms differ (${arms.length} found)`);
  for (const key of ['HEX', 'MOON', 'MASSIF']) if (!svg.includes(art[key])) problems.push(`${key} path missing`);
  if (problems.length) {
    failed = true;
    console.error(`${file}: ${problems.join('; ')}`);
  }
}
if (failed) process.exit(1);
console.log(`logo in sync (${files.length} files)`);
