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

const art = { PIN: constant('PIN'), MOUNTAINS: constant('MOUNTAINS'), SNOWCAP: constant('SNOWCAP'), FLAKE: constant('FLAKE') };
// The mono file has no snowcap (one color); the others have every part.
const files = { 'logo.svg': Object.keys(art), 'logo-horizontal.svg': Object.keys(art), 'logo-mono.svg': ['PIN', 'MOUNTAINS', 'FLAKE'] };
let failed = false;
for (const [file, keys] of Object.entries(files)) {
  const svg = readFileSync(join(root, 'assets', file), 'utf8');
  const missing = keys.filter((key) => !svg.includes(art[key]));
  if (missing.length) {
    failed = true;
    console.error(`${file}: missing ${missing.join(', ')}`);
  }
}
if (failed) process.exit(1);
console.log(`logo in sync (${Object.keys(files).length} files)`);
