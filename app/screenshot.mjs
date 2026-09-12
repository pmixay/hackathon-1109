// Снимки экранов живого интерфейса. Запускает сервер на 8766, снимает каждую вкладку каждой страницы, останавливает сервер.
//   node app/screenshot.mjs [outDir=app/screenshots]
// Файлы: <страница>.png — первая вкладка (светлая тема), <страница>-<вкладка>.png — остальные вкладки,
// <страница>-dark.png — первая вкладка в тёмной теме, scenario-menu.png — открытый выбор сценария,
// portfolio-builder-fail.png и portfolio-checks-fail.png — произвольный портфель с нарушением STRESS (конструктор и таблица проверок).
// Нужен playwright с Chromium (npm i -g playwright && npx playwright install chromium).
// FONT_DIR — локальный кэш Google Fonts (см. docs/mockup/README.md), если сеть недоступна.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const outDir = process.argv[2] || path.join('app', 'screenshots');
fs.mkdirSync(outDir, { recursive: true });
const PORT = 8766, BASE = `http://127.0.0.1:${PORT}/`;
const PAGES = [
  ['portfolio', ['overview', 'builder', 'checks', 'combos', 'lots']],
  ['why', ['decision', 'breakdown', 's2']],
  ['compare', ['charts', 'table']],
  ['stress', ['margins', 'actions']],
  ['data', ['current', 'upload', 'format']],
];
const server = spawn('python3', ['app/server.py', '--port', String(PORT)], { stdio: ['ignore', 'pipe', 'inherit'] });
for (let i = 0; i < 60; i++) { try { const r = await fetch(BASE); if (r.ok) break; } catch {} await new Promise((r) => setTimeout(r, 250)); }
const browser = await chromium.launch();
const fontDir = process.env.FONT_DIR;
async function open(theme) {
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  await page.addInitScript((t) => localStorage.setItem('kp.theme', t), theme);
  if (fontDir) await page.route(/^https:\/\/fonts\.googleapis\.com\//, (route) => {
    const u = new URL(route.request().url());
    if (u.pathname.endsWith('.woff2')) return route.fulfill({ path: path.join(fontDir, path.basename(u.pathname)), contentType: 'font/woff2' });
    return route.fulfill({ path: path.join(fontDir, 'local-fonts.css'), contentType: 'text/css' });
  });
  return page;
}
async function shot(page, hash, file, opts = {}) {
  await page.goto(BASE + '#' + hash, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  if (opts.before) await opts.before(page);
  await page.screenshot({ path: path.join(outDir, file), fullPage: !opts.viewport });
  console.log('wrote', file);
}
try {
  const light = await open('light');
  for (const [p, tabs] of PAGES) for (const [i, t] of tabs.entries()) await shot(light, `${p}/${t}`, i ? `${p}-${t}.png` : `${p}.png`);
  await shot(light, 'portfolio/overview', 'scenario-menu.png', { viewport: true, before: async (page) => { await page.click('#scenario .dd-btn'); await page.waitForTimeout(150); } });
  // конструктор: один лот заменён (AGRI-B → FLOOD-A), STRESS нарушен — экран с текстом нарушения
  await shot(light, 'portfolio/builder', 'portfolio-builder-fail.png', { before: async (page) => {
    const i = await page.$$eval('select.bld-lot', (els) => els.findIndex((e) => e.value === 'AGRI'));
    await page.selectOption(`select.bld-lot[data-i="${i}"]`, 'FLOOD');
    await page.click(`.bld-mode[data-i="${i}"] span[data-m="A"]`);
    await page.click('#bld-calc');
    await page.waitForFunction(() => document.querySelector('.res.bad'));
    await page.waitForTimeout(300);
  } });
  await shot(light, 'portfolio/checks', 'portfolio-checks-fail.png', { before: async (page) => { await page.click('#scenario .dd-btn'); await page.click('#scenario .dd-it[data-s="STRESS"]'); await page.waitForTimeout(300); } });
  await light.evaluate(() => localStorage.removeItem('kp.selected'));
  await light.close();
  const dark = await open('dark');
  for (const [p, tabs] of PAGES) await shot(dark, `${p}/${tabs[0]}`, `${p}-dark.png`);
  await dark.close();
} finally {
  await browser.close();
  server.kill();
}
