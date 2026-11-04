// Dev-only icon builder. Reads mobile/assets/logo.svg and logo-mono.svg and
// writes the PNG assets that app.json references. Run: node scripts/build-icons.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Resvg } from '@resvg/resvg-js';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const assets = join(root, 'assets');
const NAVY = '#0F2A44';

function render(svg, width) {
  const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: width } });
  return resvg.render().asPng();
}

function solidSvg(color, size = 432) {
  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="${color}"/></svg>`,
  );
}

const mark = readFileSync(join(assets, 'logo.svg'));
// icon.png must be opaque: paint the navy background first.
const opaqueIcon = Buffer.from(
  mark.toString().replace(/<svg([^>]*)>/, `<svg$1><rect width="512" height="512" fill="${NAVY}"/>`),
);
const mono = Buffer.from(
  readFileSync(join(assets, 'logo-mono.svg'))
    .toString()
    .replaceAll('currentColor', '#FFFFFF'),
);

const outputs = [
  ['icon.png', render(opaqueIcon, 1024)],
  ['splash-icon.png', render(mark, 512)],
  ['favicon.png', render(mark, 48)],
  ['android-icon-foreground.png', render(mark, 432)],
  ['android-icon-background.png', render(solidSvg(NAVY), 432)],
  ['android-icon-monochrome.png', render(mono, 432)],
];

for (const [name, png] of outputs) {
  writeFileSync(join(assets, name), png);
  console.log(`wrote assets/${name} (${png.length} bytes)`);
}
