// Экспорт презентации в PDF и PNG.
//
//   node docs/presentation/render.mjs
//
// LibreOffice сам не кладёт спрятанные слайды в PDF, поэтому kosmo-deck.pdf —
// ровно то, что идёт в показ. Запасные слайды рендерятся отдельно в
// renders/backup-*.png из временной копии, где снят флаг «спрятан».
//
// Нужны LibreOffice (soffice) и Python с пакетом pymupdf. Шрифт Montserrat
// должен быть установлен в системе, иначе LibreOffice подставит свой.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const AdmZip = require('adm-zip');

const HERE = path.dirname(fileURLToPath(import.meta.url));
const pptx = path.join(HERE, 'kosmo-deck.pptx');
const pdf = path.join(HERE, 'kosmo-deck.pdf');
const out = path.join(HERE, 'renders');

if (!fs.existsSync(pptx)) throw new Error('сначала node docs/presentation/build.mjs');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

const soffice = (file, dir) => execFileSync('soffice', [
  '--headless', '--norestore',
  `-env:UserInstallation=file://${fs.mkdtempSync(path.join(os.tmpdir(), 'lo-'))}`,
  '--convert-to', 'pdf', '--outdir', dir, file,
], { stdio: 'inherit', env: { ...process.env, SAL_USE_VCLPLUGIN: 'svp' } });

const toPng = (src, dir, prefix, from = 1) => execFileSync('python3', ['-c', `
import pymupdf, os
doc = pymupdf.open(${JSON.stringify(src)})
n = 0
for i, page in enumerate(doc, 1):
    if i < ${from}: continue
    n += 1
    page.get_pixmap(dpi=150).save(os.path.join(${JSON.stringify(dir)}, f"${prefix}-{i:02d}.png"))
print("${prefix}: страниц", n)
`], { stdio: 'inherit' });

// Показ
soffice(pptx, HERE);
toPng(pdf, out, 'slide');

// Запасные слайды: снимаем show="0" во временной копии и рендерим только их
const zip = new AdmZip(pptx);
const slides = zip.getEntries()
  .map((e) => e.entryName.match(/^ppt\/slides\/slide(\d+)\.xml$/))
  .filter(Boolean)
  .map((mm) => Number(mm[1]))
  .sort((a, b) => a - b);
const hidden = slides.filter((n) => zip.readAsText(`ppt/slides/slide${n}.xml`).slice(0, 600).includes('show="0"'));

if (hidden.length) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'deck-'));
  for (const n of hidden) {
    const name = `ppt/slides/slide${n}.xml`;
    zip.updateFile(name, Buffer.from(zip.readAsText(name).replace(' show="0"', ''), 'utf8'));
  }
  const allPptx = path.join(tmp, 'all.pptx');
  zip.writeZip(allPptx);
  soffice(allPptx, tmp);
  toPng(path.join(tmp, 'all.pdf'), out, 'backup', Math.min(...hidden));
  fs.rmSync(tmp, { recursive: true, force: true });
}

console.log('PDF:', pdf, `(показ, ${slides.length - hidden.length} слайдов)`);
console.log('PNG:', out);
