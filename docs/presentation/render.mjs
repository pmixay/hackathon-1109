// Экспорт презентации в PDF и PNG.
//
//   node docs/presentation/render.mjs
//
// Нужны LibreOffice (soffice) и Python с пакетом pymupdf. Шрифт Montserrat
// должен быть установлен в системе, иначе LibreOffice подставит свой.

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const pptx = path.join(HERE, 'kosmo-deck.pptx');
const pdf = path.join(HERE, 'kosmo-deck.pdf');
const out = path.join(HERE, 'renders');

if (!fs.existsSync(pptx)) throw new Error('сначала node docs/presentation/build.mjs');
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

const profile = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'lo-'));
execFileSync('soffice', [
  '--headless', '--norestore', `-env:UserInstallation=file://${profile}`,
  '--convert-to', 'pdf', '--outdir', HERE, pptx,
], { stdio: 'inherit', env: { ...process.env, SAL_USE_VCLPLUGIN: 'svp' } });

execFileSync('python3', ['-c', `
import pymupdf, os
doc = pymupdf.open(${JSON.stringify(pdf)})
for i, page in enumerate(doc, 1):
    pix = page.get_pixmap(dpi=150)
    pix.save(os.path.join(${JSON.stringify(out)}, f"slide-{i:02d}.png"))
print("страниц:", len(doc))
`], { stdio: 'inherit' });

console.log('PDF:', pdf);
console.log('PNG:', out);
