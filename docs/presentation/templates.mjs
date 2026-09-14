// Черновики шаблонов на выбор: три светлых варианта с зелёными градиентами.
// Каждый вариант показан на трёх слайдах: обложка, содержательный слайд, QR.
//
//   node docs/presentation/templates.mjs
//
// Результат: docs/presentation/drafts/variant-A.pptx … variant-C.pptx

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';
import { linear, radial, pill } from './gradients.mjs';
import { icon, qr } from './assets.mjs';
import { m, c0Stress, publicC0, privateC0, nf, plus, SITE } from './data.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'drafts');
fs.mkdirSync(OUT, { recursive: true });

const W = 13.333, H = 7.5, M = 0.72;
const F = 'Montserrat';

// Светлая палитра проекта плюс зелёные градиенты.
const P = {
  page: 'FFFFFF',
  paper: 'F4F7F5',
  ink: '0E1F16',
  ink2: '3E5147',
  rule: 'E1E8E3',
  deep: '0B4A2E',
  brand: '0F6F40',
  accent: '17A05C',
  mint: '55B894',
  soft: 'E8F4EC',
  white: 'FFFFFF',
};

const G = {};
const ICONS = {};
const CHIPS = ['FIRE-A', 'ENV-A', 'AGRI-B', 'TRANS-B'];
const STATS = [
  [nf(m.c0), 'старт, млн ₽'],
  [nf(m.vpub), 'польза, млн ₽ в год'],
  [nf(m.cash, 1), 'поступления, млн ₽ в год'],
  [nf(c0Stress.margin), 'запас, млн ₽'],
];

async function prepare() {
  G.cover = await linear({ w: 1920, h: 1080, from: P.deep, mid: '13794A', to: '3FB681', angle: 125 });
  G.band = await linear({ w: 1920, h: 380, from: P.deep, mid: '146B45', to: '2E9E6A', angle: 15 });
  G.blob = await radial({ w: 1920, h: 1080, from: 'BCE6D0', to: 'F4F7F5', cx: 0.78, cy: 0.3, r: 0.62 });
  G.blob2 = await radial({ w: 1920, h: 1080, from: 'C6E9D7', to: 'F4F7F5', cx: 0.5, cy: 0.46, r: 0.5 });
  G.barA = await pill({ w: 900, h: 150, r: 30, from: P.deep, to: '2E9E6A', angle: 0 });
  G.barB = await pill({ w: 700, h: 150, r: 30, from: '2E9E6A', to: '7FD3A8', angle: 0 });
  G.tile = await pill({ w: 620, h: 620, r: 44, from: P.deep, to: '2E9E6A', angle: 130 });
  G.mark = await pill({ w: 420, h: 60, r: 12, from: 'A9E3C4', to: 'DFF3E8', angle: 0 });
  G.qrpad = await pill({ w: 900, h: 900, r: 56, from: P.deep, to: '2E9E6A', angle: 130 });
  for (const [k, n] of Object.entries({ bank: 'TbBuildingBank', brief: 'TbBriefcase' })) {
    ICONS[k] = await icon(n, P.brand);
    ICONS[k + 'W'] = await icon(n, 'FFFFFF');
  }
  G.qr = await qr(SITE, { fg: '0B2A1C', bg: 'FFFFFF', px: 900 });
  G.qrW = await qr(SITE, { fg: 'FFFFFF', bg: '0E4530', px: 900 });
}

const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: F, ...o });

// ────────────────────────────────────────────────────── Вариант A: градиентная шапка
function variantA(pres) {
  // 1. Обложка
  {
    const s = pres.addSlide();
    s.addImage({ data: G.cover, x: 0, y: 0, w: W, h: H });
    T(s, 'Космос\nкак инфраструктура', { x: M, y: 1.5, w: 8.2, h: 2.6, fontSize: 50, bold: true, color: P.white, lineSpacingMultiple: 1.04 });
    T(s, 'Четыре работающих сервиса для региона', { x: M, y: 4.16, w: 7.4, h: 0.4, fontSize: 16, color: 'D7F0E2' });
    CHIPS.forEach((c, i) => {
      const x = M + i * 1.82;
      s.addShape('roundRect', { x, y: 4.86, w: 1.66, h: 0.5, rectRadius: 0.25, fill: { color: P.white, transparency: 86 }, line: { color: 'A9E3C4', width: 1 } });
      T(s, c, { x, y: 4.86, w: 1.66, h: 0.5, fontSize: 12.5, bold: true, color: P.white, align: 'center', valign: 'middle' });
    });
    STATS.forEach(([v, lab], i) => {
      const y = 1.62 + i * 1.14;
      T(s, v, { x: 9.5, y, w: 3.2, h: 0.6, fontSize: 30, bold: true, color: P.white, align: 'right' });
      T(s, lab, { x: 9.5, y: y + 0.56, w: 3.2, h: 0.3, fontSize: 11, color: 'BEE6D2', align: 'right' });
    });
  }
  // 2. Содержательный
  {
    const s = pres.addSlide();
    s.background = { color: P.page };
    s.addImage({ data: G.band, x: 0, y: 0, w: W, h: 1.86 });
    T(s, 'Кто платит', { x: M, y: 0.6, w: 8, h: 0.8, fontSize: 40, bold: true, color: P.white });
    T(s, 'Два контура на старте, положительный баланс в год', { x: M, y: 1.34, w: 8, h: 0.34, fontSize: 13.5, color: 'CDEBDC' });

    T(s, 'Старт, млн ₽', { x: M, y: 2.3, w: 5, h: 0.3, fontSize: 12, color: P.ink2 });
    const sw = 6.0, sy = 2.72, sh = 0.94;
    const wPub = sw * (publicC0 / m.c0);
    s.addImage({ data: G.barA, x: M, y: sy, w: wPub, h: sh });
    s.addImage({ data: G.barB, x: M + wPub + 0.04, y: sy, w: sw - wPub - 0.04, h: sh });
    T(s, nf(publicC0), { x: M + 0.3, y: sy, w: 1.6, h: sh, fontSize: 20, bold: true, color: P.white, valign: 'middle' });
    T(s, nf(privateC0), { x: M + wPub + 0.3, y: sy, w: 1.6, h: sh, fontSize: 20, bold: true, color: P.white, valign: 'middle' });
    [[ICONS.bank, 'Бюджет за FIRE и ENV', M], [ICONS.brief, 'Частный партнёр за AGRI и TRANS', M + wPub]].forEach(([ic, t, x]) => {
      s.addImage({ data: ic, x, y: sy + sh + 0.24, w: 0.22, h: 0.22 });
      T(s, t, { x: x + 0.32, y: sy + sh + 0.2, w: 3.4, h: 0.3, fontSize: 12, color: P.ink2 });
    });

    const bx = 7.6, bh = 1.98, by = 2.98, maxV = Math.max(m.cash, m.opex);
    T(s, 'Год, млн ₽', { x: bx, y: 2.3, w: 4, h: 0.3, fontSize: 12, color: P.ink2 });
    [[m.cash, 'поступления', G.barA], [m.opex, 'содержание', G.barB]].forEach(([v, t, g], i) => {
      const h = (v / maxV) * bh, x = bx + i * 1.7;
      s.addImage({ data: g, x, y: by + bh - h, w: 1.28, h });
      T(s, nf(v, v % 1 ? 1 : 0), { x, y: by + bh - h - 0.42, w: 1.28, h: 0.38, fontSize: 17, bold: true, color: P.ink, align: 'center' });
      T(s, t, { x: x - 0.15, y: by + bh + 0.12, w: 1.58, h: 0.3, fontSize: 11.5, color: P.ink2, align: 'center' });
    });
    s.addImage({ data: G.tile, x: 11.0, y: 3.06, w: 1.72, h: 1.72 });
    T(s, plus(m.cash - m.opex, 1), { x: 11.0, y: 3.42, w: 1.72, h: 0.5, fontSize: 22, bold: true, color: P.white, align: 'center' });
    T(s, 'остаётся в год', { x: 11.0, y: 3.94, w: 1.72, h: 0.3, fontSize: 10.5, color: 'CDEBDC', align: 'center' });

    T(s, '10 лет партнёрства. Горизонт 2027–2033.', { x: M, y: 6.1, w: 8, h: 0.34, fontSize: 13, bold: true, color: P.brand });
    T(s, '2', { x: W - M - 1, y: 6.86, w: 1, h: 0.3, fontSize: 10, color: '9BAAA2', align: 'right' });
  }
  // 3. QR
  {
    const s = pres.addSlide();
    s.background = { color: P.page };
    T(s, 'Попробуйте сами', { x: M, y: 1.5, w: 6.4, h: 0.9, fontSize: 44, bold: true, color: P.ink });
    T(s, 'Инструмент открыт. Соберите свой портфель и посмотрите, что изменится.', { x: M, y: 2.5, w: 5.8, h: 0.8, fontSize: 15, color: P.ink2 });
    T(s, SITE.replace('https://', ''), { x: M, y: 3.6, w: 6, h: 0.5, fontSize: 24, bold: true, color: P.brand });
    s.addImage({ data: G.qrpad, x: 8.1, y: 1.35, w: 4.5, h: 4.5 });
    s.addImage({ data: G.qr, x: 8.62, y: 1.87, w: 3.46, h: 3.46 });
  }
}

// ────────────────────────────────────────────────────── Вариант B: светлые карточки
function variantB(pres) {
  const shadow = () => ({ type: 'outer', color: '0E1F16', blur: 14, offset: 3, angle: 90, opacity: 0.1 });
  {
    const s = pres.addSlide();
    s.background = { color: P.paper };
    s.addImage({ data: G.blob, x: 0, y: 0, w: W, h: H });
    T(s, 'Космос\nкак инфраструктура', { x: M, y: 1.6, w: 9.4, h: 2.6, fontSize: 46, bold: true, color: P.ink, lineSpacingMultiple: 1.04 });
    T(s, 'Четыре работающих сервиса для региона', { x: M, y: 4.26, w: 7, h: 0.4, fontSize: 16, color: P.ink2 });
    CHIPS.forEach((c, i) => {
      const x = M + i * 1.82;
      s.addShape('roundRect', { x, y: 4.96, w: 1.66, h: 0.52, rectRadius: 0.26, fill: { color: P.white }, line: { color: 'C8E5D5', width: 1 }, shadow: shadow() });
      T(s, c, { x, y: 4.96, w: 1.66, h: 0.52, fontSize: 12.5, bold: true, color: P.brand, align: 'center', valign: 'middle' });
    });
    STATS.forEach(([v, lab], i) => {
      const x = M + i * 3.06;
      s.addShape('roundRect', { x, y: 5.86, w: 2.86, h: 1.1, rectRadius: 0.16, fill: { color: P.white }, line: { color: P.rule, width: 1 }, shadow: shadow() });
      T(s, v, { x: x + 0.24, y: 6.0, w: 2.4, h: 0.5, fontSize: 24, bold: true, color: P.ink });
      T(s, lab, { x: x + 0.24, y: 6.48, w: 2.4, h: 0.3, fontSize: 10.5, color: P.ink2 });
    });
  }
  {
    const s = pres.addSlide();
    s.background = { color: P.paper };
    T(s, 'Кто платит', { x: M, y: 0.62, w: 8, h: 0.8, fontSize: 40, bold: true, color: P.ink });
    T(s, 'Два контура на старте, положительный баланс в год', { x: M, y: 1.42, w: 8, h: 0.34, fontSize: 13.5, color: P.ink2 });

    s.addShape('roundRect', { x: M, y: 2.1, w: 7.0, h: 2.5, rectRadius: 0.18, fill: { color: P.white }, line: { color: P.rule, width: 1 }, shadow: shadow() });
    T(s, 'Старт, млн ₽', { x: M + 0.36, y: 2.36, w: 5, h: 0.3, fontSize: 12, color: P.ink2 });
    const sw = 6.28, sy = 2.78, sh = 0.9;
    const wPub = sw * (publicC0 / m.c0);
    s.addImage({ data: G.barA, x: M + 0.36, y: sy, w: wPub, h: sh });
    s.addImage({ data: G.barB, x: M + 0.36 + wPub + 0.04, y: sy, w: sw - wPub - 0.04, h: sh });
    T(s, nf(publicC0), { x: M + 0.62, y: sy, w: 1.6, h: sh, fontSize: 19, bold: true, color: P.white, valign: 'middle' });
    T(s, nf(privateC0), { x: M + 0.62 + wPub, y: sy, w: 1.6, h: sh, fontSize: 19, bold: true, color: P.white, valign: 'middle' });
    [['Бюджет за FIRE и ENV', M + 0.36], ['Частный партнёр за AGRI и TRANS', M + 0.36 + wPub]].forEach(([t, x]) => {
      T(s, t, { x, y: sy + sh + 0.2, w: 3.4, h: 0.3, fontSize: 12, color: P.ink2 });
    });

    s.addShape('roundRect', { x: 8.1, y: 2.1, w: 4.5, h: 2.5, rectRadius: 0.18, fill: { color: P.white }, line: { color: P.rule, width: 1 }, shadow: shadow() });
    T(s, 'Год, млн ₽', { x: 8.46, y: 2.36, w: 3, h: 0.3, fontSize: 12, color: P.ink2 });
    const bh = 1.16, by = 3.06, maxV = Math.max(m.cash, m.opex);
    [[m.cash, 'поступления', G.barA], [m.opex, 'содержание', G.barB]].forEach(([v, t, g], i) => {
      const h = (v / maxV) * bh, x = 8.46 + i * 1.42;
      s.addImage({ data: g, x, y: by + bh - h, w: 1.16, h });
      T(s, nf(v, v % 1 ? 1 : 0), { x: x - 0.1, y: by + bh - h - 0.38, w: 1.36, h: 0.34, fontSize: 15, bold: true, color: P.ink, align: 'center' });
      T(s, t, { x: x - 0.2, y: by + bh + 0.1, w: 1.56, h: 0.3, fontSize: 10.5, color: P.ink2, align: 'center' });
    });
    s.addImage({ data: G.tile, x: 11.3, y: 3.1, w: 1.1, h: 1.1 });
    T(s, plus(m.cash - m.opex, 1), { x: 11.3, y: 3.4, w: 1.1, h: 0.4, fontSize: 15, bold: true, color: P.white, align: 'center' });

    s.addShape('roundRect', { x: M, y: 4.92, w: 11.89, h: 1.24, rectRadius: 0.18, fill: { color: P.white }, line: { color: P.rule, width: 1 }, shadow: shadow() });
    [['10 лет', 'срок партнёрства'], ['2027–2033', 'горизонт расчёта'], [nf(m.kcash, 2), 'поступления к содержанию']].forEach(([v, lab], i) => {
      const x = M + 0.4 + i * 3.9;
      T(s, v, { x, y: 5.14, w: 3.4, h: 0.42, fontSize: 20, bold: true, color: P.brand });
      T(s, lab, { x, y: 5.58, w: 3.4, h: 0.3, fontSize: 11.5, color: P.ink2 });
    });
    T(s, '2', { x: W - M - 1, y: 6.86, w: 1, h: 0.3, fontSize: 10, color: '9BAAA2', align: 'right' });
  }
  {
    const s = pres.addSlide();
    s.background = { color: P.paper };
    s.addImage({ data: G.blob2, x: 0, y: 0, w: W, h: H });
    T(s, 'Попробуйте сами', { x: 0, y: 1.16, w: W, h: 0.9, fontSize: 44, bold: true, color: P.ink, align: 'center' });
    s.addShape('roundRect', { x: 4.62, y: 2.34, w: 4.1, h: 4.1, rectRadius: 0.24, fill: { color: P.white }, line: { color: P.rule, width: 1 }, shadow: shadow() });
    s.addImage({ data: G.qr, x: 4.96, y: 2.68, w: 3.42, h: 3.42 });
    T(s, SITE.replace('https://', ''), { x: 0, y: 6.62, w: W, h: 0.4, fontSize: 19, bold: true, color: P.brand, align: 'center' });
  }
}

// ────────────────────────────────────────────────────── Вариант C: крупный акцент
function variantC(pres) {
  {
    const s = pres.addSlide();
    s.background = { color: P.page };
    s.addImage({ data: G.band, x: 0, y: H - 1.5, w: W, h: 1.5 });
    T(s, 'Космос', { x: M, y: 1.16, w: 11, h: 1.2, fontSize: 54, bold: true, color: P.ink });
    s.addImage({ data: G.mark, x: M - 0.12, y: 2.44, w: 8.43 + 0.24, h: 0.82 });
    T(s, 'как инфраструктура', { x: M, y: 2.26, w: 11, h: 1.2, fontSize: 54, bold: true, color: P.ink });
    T(s, 'Четыре работающих сервиса для региона', { x: M, y: 3.86, w: 8, h: 0.4, fontSize: 17, color: P.ink2 });
    STATS.forEach(([v, lab], i) => {
      const x = M + i * 3.06;
      T(s, v, { x, y: 4.66, w: 2.9, h: 0.6, fontSize: 30, bold: true, color: P.brand });
      T(s, lab, { x, y: 5.24, w: 2.9, h: 0.3, fontSize: 11, color: P.ink2 });
      if (i) s.addShape('rect', { x: x - 0.2, y: 4.76, w: 0.01, h: 0.72, fill: { color: P.rule } });
    });
    T(s, CHIPS.join('   ·   '), { x: M, y: H - 1.02, w: 11, h: 0.5, fontSize: 15, bold: true, color: P.white, valign: 'middle' });
  }
  {
    const s = pres.addSlide();
    s.background = { color: P.page };
    T(s, 'Кто платит', { x: M, y: 0.72, w: 9, h: 1.0, fontSize: 46, bold: true, color: P.ink });
    s.addShape('rect', { x: M, y: 1.86, w: 11.89, h: 0.012, fill: { color: P.rule } });

    T(s, 'СТАРТ', { x: M, y: 2.2, w: 5, h: 0.3, fontSize: 11, bold: true, charSpacing: 2, color: P.accent });
    const sw = 6.4, sy = 2.66, sh = 1.0;
    const wPub = sw * (publicC0 / m.c0);
    s.addImage({ data: G.barA, x: M, y: sy, w: wPub, h: sh });
    s.addImage({ data: G.barB, x: M + wPub + 0.04, y: sy, w: sw - wPub - 0.04, h: sh });
    T(s, nf(publicC0), { x: M + 0.3, y: sy, w: 1.8, h: sh, fontSize: 22, bold: true, color: P.white, valign: 'middle' });
    T(s, nf(privateC0), { x: M + wPub + 0.3, y: sy, w: 1.8, h: sh, fontSize: 22, bold: true, color: P.white, valign: 'middle' });
    T(s, 'Бюджет за FIRE и ENV', { x: M, y: sy + sh + 0.22, w: 3.4, h: 0.3, fontSize: 12.5, color: P.ink2 });
    T(s, 'Частный партнёр за AGRI и TRANS', { x: M + wPub, y: sy + sh + 0.22, w: 3.6, h: 0.3, fontSize: 12.5, color: P.ink2 });

    T(s, 'ГОД', { x: 8.2, y: 2.2, w: 4, h: 0.3, fontSize: 11, bold: true, charSpacing: 2, color: P.accent });
    const rows = [[m.cash, 'поступления', G.barA, 1], [m.opex, 'содержание', G.barB, m.opex / m.cash]];
    rows.forEach(([v, t, g, frac], i) => {
      const y = 2.66 + i * 1.02;
      s.addImage({ data: g, x: 8.2, y, w: 3.2 * frac, h: 0.68 });
      T(s, nf(v, v % 1 ? 1 : 0), { x: 8.2 + 3.2 * frac + 0.16, y, w: 1.4, h: 0.68, fontSize: 17, bold: true, color: P.ink, valign: 'middle' });
      T(s, t, { x: 8.36, y, w: 3, h: 0.68, fontSize: 12, color: P.white, valign: 'middle' });
    });
    T(s, plus(m.cash - m.opex, 1), { x: 8.2, y: 4.86, w: 2.4, h: 0.5, fontSize: 26, bold: true, color: P.brand });
    T(s, 'остаётся в год', { x: 8.2, y: 5.36, w: 3, h: 0.3, fontSize: 12, color: P.ink2 });

    s.addImage({ data: G.mark, x: M - 0.06, y: 6.04, w: 4.5, h: 0.56 });
    T(s, '10 лет партнёрства, горизонт 2027–2033', { x: M, y: 6.04, w: 6, h: 0.56, fontSize: 13.5, bold: true, color: P.deep, valign: 'middle' });
    T(s, '2', { x: W - M - 1, y: 6.86, w: 1, h: 0.3, fontSize: 10, color: '9BAAA2', align: 'right' });
  }
  {
    const s = pres.addSlide();
    s.addImage({ data: G.cover, x: 0, y: 0, w: W, h: H });
    T(s, 'Попробуйте сами', { x: 0, y: 0.96, w: W, h: 0.9, fontSize: 46, bold: true, color: P.white, align: 'center' });
    s.addShape('roundRect', { x: 4.63, y: 1.92, w: 4.08, h: 4.08, rectRadius: 0.24, fill: { color: 'FFFFFF' }, line: { color: 'FFFFFF', width: 0 } });
    s.addImage({ data: G.qr, x: 4.93, y: 2.22, w: 3.48, h: 3.48 });
    T(s, SITE.replace('https://', ''), { x: 0, y: 6.06, w: W, h: 0.44, fontSize: 22, bold: true, color: 'CDEBDC', align: 'center' });
  }
}

await prepare();
for (const [id, fn] of [['A', variantA], ['B', variantB], ['C', variantC]]) {
  const pres = new PptxGenJS();
  pres.defineLayout({ name: 'K', width: W, height: H });
  pres.layout = 'K';
  fn(pres);
  const file = path.join(OUT, `variant-${id}.pptx`);
  await pres.writeFile({ fileName: file });
  console.log('готово:', file);
}
