// Renders each screen of a single-file mockup to PNG (1440 px wide, 2x).
// Usage: node render.mjs <mockup.html> <outDir> [--fullpage <name>]
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const [,, htmlPath, outDir, ...rest] = process.argv;
const fullName = rest[0] === '--fullpage' ? rest[1] : null;
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1520, height: 1000 }, deviceScaleFactor: 2 });
// Optional offline font cache: FONT_DIR holds local-fonts.css (Google Fonts CSS rewritten to ./*.woff2) plus the files.
const fontDir = process.env.FONT_DIR;
if (fontDir) {
  await page.route(/^https:\/\/fonts\.googleapis\.com\//, (route) => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith('.woff2')) return route.fulfill({ path: path.join(fontDir, path.basename(u.pathname)), contentType: 'font/woff2' });
    return route.fulfill({ path: path.join(fontDir, 'local-fonts.css'), contentType: 'text/css' });
  });
}
await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(300);
const loaded = await page.evaluate(() => Array.from(document.fonts).filter((f) => f.status === 'loaded').map((f) => f.family));
console.log('fonts loaded:', [...new Set(loaded)].join(', ') || 'none');
if (fullName) {
  await page.screenshot({ path: path.join(outDir, fullName + '.png'), fullPage: true });
  console.log('wrote', fullName + '.png');
} else {
  const ids = await page.$$eval('section.shell', (els) => els.map((e) => [e.id.replace(/^screen-/, ''), Math.round(e.getBoundingClientRect().height)]));
  for (const [id, h] of ids) {
    const el = await page.$('#screen-' + id);
    await el.screenshot({ path: path.join(outDir, id + '.png') });
    console.log('wrote', id + '.png', 'height', h);
  }
  // one extra shot with a help popover open (the constraints block on the portfolio screen)
  const helpBtn = await page.$('#screen-portfolio .row2 .card .help i');
  if (helpBtn) {
    await helpBtn.click();
    await (await page.$('#screen-portfolio')).screenshot({ path: path.join(outDir, 'portfolio-help.png') });
    console.log('wrote portfolio-help.png');
  }
}
await browser.close();
