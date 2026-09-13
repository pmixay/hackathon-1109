// Сборка презентации защиты: docs/presentation/kosmo-deck.pptx
//
// Регламент четыре минуты на всё, поэтому в показ идут семь слайдов (около двух
// с половиной минут), остальное время — живая демонстрация инструмента.
// Ещё четыре слайда лежат в файле спрятанными: их открывают в ответ на вопрос.
//
// Цифры читаются из results/ — единственного источника чисел проекта, поэтому
// слайды и инструмент не могут разойтись.
//
// Запуск:  node docs/presentation/build.mjs

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';
import { C, L, defineLayout, head, foot, card, chip, badge, meter, flow, shadow, text as T } from './theme.mjs';
import { icon, qr } from './assets.mjs';
import { radial, pill } from './gradients.mjs';
import { buildScript } from './script.mjs';
import {
  SITE, TOTAL, base, stress, ranking, m, checkOf, c0Base, c0Stress,
  FINAL_KEY, rankRow, leader, admitted, ALL_COMBOS,
  publicC0, privateC0, dVpub, nf, plus, SCRIPT_CONTEXT,
} from './data.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SC = buildScript(SCRIPT_CONTEXT);
const notes = (n) => SC.find((x) => x.n === n).say.join(' ');

const pres = new PptxGenJS();
pres.author = 'Команда «Молоток»';
pres.company = 'Кейс 02';
pres.title = 'Космос как инфраструктура';
defineLayout(pres);

// ——— картинки: иконки, градиенты, QR ———

const I = {};
for (const [k, [n, c]] of Object.entries({
  fire: ['TbFlame', C.brand], env: ['TbLeaf', C.brand], agri: ['TbPlant2', C.brand], trans: ['TbTruckDelivery', C.brand],
  check: ['TbCheck', C.brand], users: ['TbUsers', C.brand], settings: ['TbSettings', C.brand], copy: ['TbCopy', C.brand],
  flag: ['TbFlag', C.brand], rocket: ['TbRocket', C.brand], map: ['TbMap2', C.brass],
  alert: ['TbAlertTriangle', C.brass], shield: ['TbShieldCheck', C.brand], swap: ['TbArrowsExchange', C.brand],
  target: ['TbTargetArrow', C.brand], key: ['TbKey', C.brand], sat: ['TbSatellite', C.brand],
})) I[k] = await icon(n, c);

const G = {
  cover: await radial({ w: 1920, h: 1080, from: 'BCE6D0', to: C.page, cx: 0.78, cy: 0.3, r: 0.62 }),
  final: await radial({ w: 1920, h: 1080, from: 'C6E9D7', to: C.page, cx: 0.5, cy: 0.46, r: 0.5 }),
  deep: await pill({ w: 900, h: 150, r: 26, from: C.deep, to: '2E9E6A', angle: 0 }),
  mint: await pill({ w: 900, h: 150, r: 26, from: '2E9E6A', to: '7FD3A8', angle: 0 }),
  pale: await pill({ w: 900, h: 150, r: 26, from: 'CDEBDB', to: 'EAF6EF', angle: 0 }),
  tile: await pill({ w: 620, h: 620, r: 40, from: C.deep, to: '2E9E6A', angle: 130 }),
  mark: await pill({ w: 900, h: 120, r: 14, from: 'A9E3C4', to: 'DFF3E8', angle: 0 }),
  brass: await pill({ w: 400, h: 150, r: 26, from: 'C79A4A', to: 'E6C88C', angle: 0 }),
};
const QR = await qr(SITE, { fg: '0B2A1C', bg: 'FFFFFF', px: 900 });

const page = () => {
  const s = pres.addSlide();
  s.background = { color: C.page };
  return s;
};
// Запасной слайд: в файле есть, в показе не участвует.
const backupPage = () => {
  const s = page();
  s.hidden = true;
  T(s, 'Запасной слайд', {
    x: L.W - L.M - 2.4, y: 6.92, w: 2.4, h: 0.28,
    fontSize: 10, color: '9BAAA2', align: 'right',
  });
  return s;
};

// ─────────────────────────────────────────── 1. Обложка
{
  const s = page();
  s.addImage({ data: G.cover, x: 0, y: 0, w: L.W, h: L.H });
  T(s, 'Космос\nкак инфраструктура', {
    x: L.M, y: 1.42, w: 9.4, h: 2.5, fontSize: 46, bold: true, color: C.ink, lineSpacingMultiple: 1.05,
  });
  T(s, 'Четыре работающих сервиса для региона', {
    x: L.M, y: 4.02, w: 7, h: 0.4, fontSize: 16, color: C.ink2,
  });
  ['FIRE-A', 'ENV-A', 'AGRI-B', 'TRANS-B'].forEach((t, i) => {
    chip(s, { x: L.M + i * 1.82, y: 4.72, w: 1.66, h: 0.52, text: t, size: 12.5 });
  });
  [
    [nf(m.c0), 'старт, млн ₽'],
    [nf(m.vpub), 'польза, млн ₽ в год'],
    [nf(m.cash, 1), 'поступления, млн ₽ в год'],
    [nf(c0Stress.margin), 'запас, млн ₽'],
  ].forEach(([v, lab], i) => {
    const x = L.M + i * 3.06;
    card(s, { x, y: 5.5, w: 2.86, h: 1.1 });
    T(s, v, { x: x + 0.26, y: 5.64, w: 2.4, h: 0.5, fontSize: 24, bold: true, color: C.ink });
    T(s, lab, { x: x + 0.26, y: 6.12, w: 2.4, h: 0.3, fontSize: 10.5, color: C.ink2 });
  });
  T(s, 'Команда «Молоток». Голубев Павел, Петр Кузнецов, Тимофей Максимов, Лихатин Андрей, Потапенко Филипп', {
    x: L.M, y: 6.82, w: 11.5, h: 0.3, fontSize: 10.5, color: C.ink2,
  });
  s.addNotes(notes(1));
}

// ─────────────────────────────────────────── 2. Идея
{
  const s = page();
  head(s, { title: 'Регион покупает результат', lead: 'Космический сервис полезен там, где он заканчивается решением человека.' });

  const cards = [
    { ic: I.target, t: 'Готовый ответ', b: 'Короткий ответ вместо снимков: где событие, насколько ему верить и что делать дальше.' },
    { ic: I.users, t: 'Портфель целиком', b: 'Четыре сервиса в разных регионах. Общественные держат смысл, прикладные приносят деньги.' },
    { ic: I.key, t: 'Общие правила', b: 'Единый оператор, открытые форматы, права на историю данных остаются у заказчика.' },
  ];
  const cw = 3.816;
  cards.forEach((c, i) => {
    const x = L.M + i * (cw + 0.22);
    card(s, { x, y: 2.1, w: cw, h: 2.5 });
    badge(s, { x: x + 0.34, y: 2.4, d: 0.76, img: c.ic });
    T(s, c.t, { x: x + 0.34, y: 3.32, w: cw - 0.68, h: 0.34, fontSize: 16, bold: true, color: C.ink });
    T(s, c.b, { x: x + 0.34, y: 3.72, w: cw - 0.68, h: 0.76, fontSize: 12, color: C.ink2 });
  });

  card(s, { x: L.M, y: 4.9, w: 11.893, h: 1.5 });
  T(s, 'Заказчик сохраняет контроль', { x: L.M + 0.42, y: 5.14, w: 11, h: 0.38, fontSize: 17, bold: true, color: C.brand });
  T(s, 'Стандарты, права на историю данных и правила доступа остаются у него. Поставщики конкурируют за отдельные части услуги и заменяются без остановки сервиса. Следующий регион получает то же ядро и настраивает его под себя.', {
    x: L.M + 0.42, y: 5.6, w: 11, h: 0.7, fontSize: 12.5, color: C.ink2,
  });

  foot(s, { n: 2, total: TOTAL });
  s.addNotes(notes(2));
}

// ─────────────────────────────────────────── 3. Портфель
{
  const s = page();
  head(s, { title: 'Четыре сервиса. Четыре региона.', lead: 'Каждый заканчивается конкретным действием пользователя.' });

  const items = [
    { code: 'FIRE-A', ic: I.fire, region: 'Сибирь', user: 'Лесные и диспетчерские службы', act: 'проверить сигнал', kpi: 'время до проверки' },
    { code: 'ENV-A', ic: I.env, region: 'Волго-Каспий', user: 'Природоохранный орган', act: 'назначить инспекцию', kpi: 'доля подтверждённых' },
    { code: 'AGRI-B', ic: I.agri, region: 'Юг', user: 'Хозяйства и органы АПК', act: 'обследовать участок', kpi: 'сигнал с действием' },
    { code: 'TRANS-B', ic: I.trans, region: 'Центр', user: 'Операторы и перевозчики', act: 'изменить план', kpi: 'время до решения' },
  ];
  const cw = 2.83;
  items.forEach((it, i) => {
    const x = L.M + i * (cw + 0.235);
    card(s, { x, y: 2.06, w: cw, h: 3.46 });
    badge(s, { x: x + 0.3, y: 2.34, d: 0.78, img: it.ic });
    T(s, it.code, { x: x + 0.3, y: 3.26, w: cw - 0.6, h: 0.32, fontSize: 16, bold: true, color: C.ink });
    T(s, it.region, { x: x + 0.3, y: 3.58, w: cw - 0.6, h: 0.28, fontSize: 12, color: C.brand });
    s.addShape('rect', { x: x + 0.3, y: 3.94, w: cw - 0.6, h: 0.01, fill: { color: C.rule } });
    T(s, it.user, { x: x + 0.3, y: 4.08, w: cw - 0.6, h: 0.5, fontSize: 12, color: C.ink2 });
    T(s, it.act, { x: x + 0.3, y: 4.6, w: cw - 0.6, h: 0.3, fontSize: 12.5, bold: true, color: C.ink });
    s.addImage({ data: G.pale, x: x + 0.3, y: 4.98, w: cw - 0.6, h: 0.4 });
    T(s, it.kpi, { x: x + 0.3, y: 4.98, w: cw - 0.6, h: 0.4, fontSize: 11, color: C.deep, align: 'center', valign: 'middle' });
  });

  [
    { t: 'FIRE и ENV — общедоступная основа для органов', g: G.deep },
    { t: 'AGRI и TRANS — якорный слой и платная детализация', g: G.mint },
  ].forEach((st, i) => {
    const x = L.M + i * 6.05;
    s.addImage({ data: st.g, x, y: 5.78, w: 5.84, h: 0.66 });
    T(s, st.t, { x: x + 0.32, y: 5.78, w: 5.3, h: 0.66, fontSize: 12.5, bold: true, color: C.white, valign: 'middle' });
  });

  foot(s, { n: 3, total: TOTAL });
  s.addNotes(notes(3));
}

// ─────────────────────────────────────────── 4. Выбор
{
  const s = page();
  head(s, { title: 'Баланс важнее максимума', lead: `Из ${nf(ALL_COMBOS)} портфелей условия проходят ${admitted}. Каждая точка — один из них.` });

  card(s, { x: L.M, y: 2.06, w: 8.1, h: 4.36 });
  const pts = ranking.map((r) => ({ key: r.variant, c0: Number(r.c0), vpub: Number(r.vpub), rank: Number(r.rank) }));
  const px0 = 1.62, px1 = 8.1, py0 = 2.5, py1 = 5.72;
  const xmin = 1120, xmax = Number(c0Stress.threshold);
  const ymin = Math.floor(Math.min(...pts.map((p) => p.vpub)) / 50) * 50;
  const ymax = Math.ceil(Math.max(...pts.map((p) => p.vpub)) / 50) * 50;
  const X = (v) => px0 + ((v - xmin) / (xmax - xmin)) * (px1 - px0);
  const Y = (v) => py1 - ((v - ymin) / (ymax - ymin)) * (py1 - py0);

  for (let t = ymin; t <= ymax; t += 100) {
    s.addShape('rect', { x: px0, y: Y(t), w: px1 - px0, h: 0.007, fill: { color: 'EDF3EF' } });
    T(s, nf(t), { x: px0 - 0.82, y: Y(t) - 0.12, w: 0.74, h: 0.24, fontSize: 8.5, color: C.muted, align: 'right' });
  }
  for (const t of [1130, 1140, 1150, 1160, 1170]) {
    T(s, nf(t), { x: X(t) - 0.35, y: py1 + 0.1, w: 0.7, h: 0.24, fontSize: 8.5, color: C.muted, align: 'center' });
  }
  T(s, 'польза, млн ₽ в год', { x: px0 - 0.86, y: py0 - 0.32, w: 2.6, h: 0.24, fontSize: 9.5, color: C.ink2 });
  T(s, 'старт, млн ₽', { x: px1 - 1.8, y: py1 + 0.36, w: 1.8, h: 0.24, fontSize: 9.5, color: C.ink2, align: 'right' });

  s.addShape('rect', { x: X(xmax), y: py0 - 0.08, w: 0.014, h: py1 - py0 + 0.08, fill: { color: C.crit } });
  T(s, `предел ${nf(xmax)}`, { x: X(xmax) - 1.66, y: py0 - 0.4, w: 1.6, h: 0.24, fontSize: 9.5, bold: true, color: C.crit, align: 'right' });

  for (const p of pts) {
    if (p.key === FINAL_KEY || p.rank === 1) continue;
    s.addShape('ellipse', { x: X(p.c0) - 0.045, y: Y(p.vpub) - 0.045, w: 0.09, h: 0.09, fill: { color: C.mint, transparency: 35 }, line: { color: C.mint, width: 0 } });
  }

  // Подписи ставим туда, где под ними нет точек: перебираем позиции вокруг
  // маркера и берём ту, что накрывает меньше всего облака.
  // Ширины замерены по Montserrat Bold 9,5 pt.
  const LABEL_W = { 'первый по баллу': 1.24, 'наш выбор': 0.8 };
  const LH = 0.22;
  const place = (cx, cy, w) => {
    const around = [
      [0.18, -LH / 2], [-w - 0.18, -LH / 2],
      [-w / 2, -0.48], [-w / 2, 0.26],
      [0.16, -0.46], [-w - 0.16, -0.46],
      [0.16, 0.26], [-w - 0.16, 0.26],
    ];
    let best = null;
    for (const [dx, dy] of around) {
      const x0 = cx + dx, y0 = cy + dy, x1 = x0 + w, y1 = y0 + LH;
      if (x0 < px0 || x1 > px1 - 0.04 || y0 < py0 - 0.3 || y1 > py1) continue;
      let hits = 0;
      for (const q of pts) {
        const qx = X(q.c0), qy = Y(q.vpub);
        if (qx > x0 - 0.07 && qx < x1 + 0.07 && qy > y0 - 0.07 && qy < y1 + 0.07) hits += 1;
      }
      if (!best || hits < best.hits) best = { dx, dy, hits };
      if (hits === 0) break;
    }
    return best ?? { dx: 0.18, dy: -LH / 2, hits: 0 };
  };
  const mark = (key, color, label) => {
    const p = pts.find((q) => q.key === key);
    const cx = X(p.c0), cy = Y(p.vpub);
    const w = LABEL_W[label];
    const { dx, dy } = place(cx, cy, w);
    s.addShape('ellipse', { x: cx - 0.105, y: cy - 0.105, w: 0.21, h: 0.21, fill: { color }, line: { color: C.white, width: 1.5 } });
    T(s, label, { x: cx + dx, y: cy + dy, w, h: LH, fontSize: 9.5, bold: true, color, align: dx < 0 ? 'right' : 'left' });
  };
  mark(leader.variant, C.brass, 'первый по баллу');
  mark(FINAL_KEY, C.deep, 'наш выбор');

  const rx = 9.06;
  card(s, { x: rx, y: 2.06, w: 3.55, h: 4.36 });
  T(s, 'Почему этот', { x: rx + 0.32, y: 2.32, w: 2.9, h: 0.34, fontSize: 16, bold: true, color: C.ink });
  [
    'Больше общественной пользы, чем у дешёвых вариантов',
    'Денег хватает на содержание всех четырёх сервисов',
    'Остаётся запас, если бюджет урежут',
  ].forEach((t, i) => {
    const y = 2.84 + i * 0.68;
    s.addShape('ellipse', { x: rx + 0.34, y: y + 0.1, w: 0.11, h: 0.11, fill: { color: C.mint }, line: { color: C.mint, width: 0 } });
    T(s, t, { x: rx + 0.62, y, w: 2.66, h: 0.6, fontSize: 11.5, color: C.ink2 });
  });
  s.addImage({ data: G.mark, x: rx + 0.32, y: 4.94, w: 2.9, h: 0.56 });
  T(s, `${plus(dVpub, 0)} млн ₽ пользы в год`, { x: rx + 0.5, y: 4.94, w: 2.6, h: 0.56, fontSize: 13.5, bold: true, color: C.deep, valign: 'middle' });
  T(s, 'по сравнению с первым по баллу: он дешевле, но срезает общедоступную часть услуги.', {
    x: rx + 0.32, y: 5.62, w: 2.9, h: 0.62, fontSize: 11, color: C.ink2,
  });

  foot(s, { n: 4, total: TOTAL });
  s.addNotes(notes(4));
}

// ─────────────────────────────────────────── 5. Деньги
{
  const s = page();
  head(s, { title: 'Деньги сходятся', lead: 'Два контура на старте, положительный баланс в год и запас при урезанном бюджете.' });

  // Старт
  card(s, { x: L.M, y: 2.06, w: 7.0, h: 2.5 });
  T(s, 'Старт, млн ₽', { x: L.M + 0.38, y: 2.3, w: 5, h: 0.3, fontSize: 12, color: C.ink2 });
  const sw = 6.24, sy = 2.7, sh = 0.9;
  const wPub = sw * (publicC0 / m.c0) - 0.04;
  s.addImage({ data: G.deep, x: L.M + 0.38, y: sy, w: wPub, h: sh });
  s.addImage({ data: G.mint, x: L.M + 0.38 + wPub + 0.06, y: sy, w: sw - wPub - 0.06, h: sh });
  T(s, nf(publicC0), { x: L.M + 0.66, y: sy, w: 1.6, h: sh, fontSize: 20, bold: true, color: C.white, valign: 'middle' });
  T(s, nf(privateC0), { x: L.M + 0.72 + wPub, y: sy, w: 1.6, h: sh, fontSize: 20, bold: true, color: C.white, valign: 'middle' });
  [['Бюджет за FIRE и ENV', L.M + 0.38], ['Частный партнёр за AGRI и TRANS', L.M + 0.44 + wPub]].forEach(([t, x]) => {
    T(s, t, { x, y: sy + sh + 0.2, w: 3.4, h: 0.3, fontSize: 12, color: C.ink2 });
  });

  // Год
  card(s, { x: 8.06, y: 2.06, w: 4.55, h: 2.5 });
  T(s, 'Год, млн ₽', { x: 8.44, y: 2.3, w: 3, h: 0.3, fontSize: 12, color: C.ink2 });
  const bh = 1.14, by = 3.0, maxV = Math.max(m.cash, m.opex);
  [[m.cash, 'поступления', G.deep], [m.opex, 'содержание', G.mint]].forEach(([v, t, g], i) => {
    const h = (v / maxV) * bh, x = 8.44 + i * 1.4;
    s.addImage({ data: g, x, y: by + bh - h, w: 1.14, h });
    T(s, nf(v, v % 1 ? 1 : 0), { x: x - 0.12, y: by + bh - h - 0.38, w: 1.38, h: 0.34, fontSize: 15, bold: true, color: C.ink, align: 'center' });
    T(s, t, { x: x - 0.22, y: by + bh + 0.1, w: 1.58, h: 0.3, fontSize: 10.5, color: C.ink2, align: 'center' });
  });
  s.addImage({ data: G.tile, x: 11.24, y: 2.94, w: 1.1, h: 1.1 });
  T(s, plus(m.cash - m.opex, 1), { x: 11.24, y: 3.24, w: 1.1, h: 0.44, fontSize: 15, bold: true, color: C.white, align: 'center' });

  // Запас при урезанном бюджете
  card(s, { x: L.M, y: 4.78, w: 11.893, h: 1.74 });
  T(s, 'Если бюджет урежут', { x: L.M + 0.4, y: 4.98, w: 5, h: 0.32, fontSize: 14, bold: true, color: C.ink });
  const gx = L.M + 0.4, gw = 11.09, gy = 5.44, gh = 0.56;
  const scale = (v) => (v / Number(c0Base.threshold)) * gw;
  s.addShape('roundRect', { x: gx, y: gy, w: gw, h: gh, rectRadius: 0.08, fill: { color: 'EDF3EF' }, line: { color: 'E4EDE7', width: 1 } });
  s.addImage({ data: G.deep, x: gx, y: gy, w: scale(m.c0), h: gh });
  s.addImage({ data: G.brass, x: gx + scale(m.c0) + 0.02, y: gy, w: scale(c0Stress.margin) - 0.02, h: gh });
  T(s, `старт ${nf(m.c0)}`, { x: gx + 0.26, y: gy, w: 2.6, h: gh, fontSize: 14, bold: true, color: C.white, valign: 'middle' });
  // Метки пределов правым краем к своей риске. Ширины замерены по Montserrat
  // Bold 10 pt, чтобы подписи не наезжали друг на друга: риски всего в дюйме.
  [
    [Number(c0Stress.threshold), `урезанный бюджет ${nf(c0Stress.threshold)}`, 1.9, C.crit],
    [Number(c0Base.threshold), nf(c0Base.threshold), 0.42, '8D9E95'],
  ].forEach(([v, label, lw, color]) => {
    s.addShape('rect', { x: gx + scale(v), y: gy - 0.16, w: 0.014, h: gh + 0.32, fill: { color } });
    T(s, label, { x: gx + scale(v) - lw - 0.04, y: gy - 0.44, w: lw, h: 0.24, fontSize: 10, bold: true, color, align: 'right' });
  });
  T(s, `запас ${nf(c0Stress.margin)} млн ₽`, {
    x: gx, y: gy + gh + 0.14, w: 3, h: 0.26, fontSize: 11, bold: true, color: C.brass,
  });
  T(s, 'Без коммерческой выручки не хватит 123 млн ₽ в год, покрывать придётся заказчику.', {
    x: gx + 3.1, y: gy + gh + 0.14, w: 8, h: 0.26, fontSize: 11, color: C.ink2, align: 'right',
  });

  foot(s, { n: 5, total: TOTAL });
  s.addNotes(notes(5));
}

// ─────────────────────────────────────────── 6. План
{
  const s = page();
  head(s, { title: 'Пять шагов до 2033 года', lead: 'У каждого шага есть результат, ответственный и признак завершения.' });

  const stages = [
    { y: '2027, первое полугодие', t: 'Заказчики и договоры', o: 'заказчик', ic: I.flag },
    { y: '2027–2028', t: 'Пилоты по пожарам и экологии', o: 'оператор', ic: I.target },
    { y: '2028, второе полугодие', t: 'Разбор пилотов и обновление ядра', o: 'оператор', ic: I.settings },
    { y: '2029–2030', t: 'Запуск полей и транспорта', o: 'частный партнёр', ic: I.rocket },
    { y: '2031–2033', t: 'Тираж в новые регионы', o: 'заказчик', ic: I.copy },
  ];
  const cw = 2.26;
  s.addShape('rect', { x: L.M + 0.4, y: 3.32, w: 11.893 - 0.8, h: 0.012, fill: { color: 'DCE7E0' } });
  stages.forEach((st, i) => {
    const x = L.M + i * (cw + 0.19);
    T(s, st.y, { x, y: 2.36, w: cw, h: 0.52, fontSize: 11, bold: true, color: C.brand, align: 'center' });
    s.addShape('ellipse', { x: x + cw / 2 - 0.25, y: 3.07, w: 0.5, h: 0.5, fill: { color: C.white }, line: { color: C.mint, width: 1.5 } });
    T(s, String(i + 1), { x: x + cw / 2 - 0.25, y: 3.07, w: 0.5, h: 0.5, fontSize: 12.5, bold: true, color: C.brand, align: 'center', valign: 'middle' });
    card(s, { x, y: 3.84, w: cw, h: 1.96 });
    s.addImage({ data: st.ic, x: x + cw / 2 - 0.15, y: 4.1, w: 0.3, h: 0.3 });
    T(s, st.t, { x: x + 0.16, y: 4.56, w: cw - 0.32, h: 0.78, fontSize: 12, bold: true, color: C.ink, align: 'center' });
    T(s, st.o, { x: x + 0.16, y: 5.38, w: cw - 0.32, h: 0.28, fontSize: 10.5, color: C.ink2, align: 'center' });
  });

  card(s, { x: L.M, y: 5.98, w: 11.893, h: 0.72 });
  [
    ['Оператор один', I.settings],
    ['Поставщика можно заменить', I.swap],
    ['Ядро переносится в новый регион', I.copy],
  ].forEach(([t, ic], i) => {
    const x = L.M + 0.42 + i * 3.9;
    s.addImage({ data: ic, x, y: 6.22, w: 0.24, h: 0.24 });
    T(s, t, { x: x + 0.34, y: 5.98, w: 3.4, h: 0.72, fontSize: 12, color: C.ink2, valign: 'middle' });
  });

  foot(s, { n: 6, total: TOTAL });
  s.addNotes(notes(6));
}

// ─────────────────────────────────────────── 7. Демонстрация
{
  const s = page();
  s.addImage({ data: G.final, x: 0, y: 0, w: L.W, h: L.H });
  T(s, 'Дальше — живая демонстрация', {
    x: 0, y: 1.0, w: L.W, h: 0.9, fontSize: 44, bold: true, color: C.ink, align: 'center',
  });
  T(s, 'Соберём портфель, сломаем его заменой лота и вернём обратно.', {
    x: 0, y: 1.92, w: L.W, h: 0.4, fontSize: 16, color: C.ink2, align: 'center',
  });
  s.addShape('roundRect', {
    x: 4.72, y: 2.62, w: 3.9, h: 3.9, rectRadius: 0.26,
    fill: { color: C.white }, line: { color: C.rule, width: 1 }, shadow: shadow(),
  });
  s.addImage({ data: QR, x: 5.03, y: 2.93, w: 3.28, h: 3.28 });
  T(s, SITE.replace('https://', ''), {
    x: 0, y: 6.68, w: L.W, h: 0.44, fontSize: 20, bold: true, color: C.brand, align: 'center',
  });
  s.addNotes(notes(7));
}

// ─────────────────────────────────────────── 8. Запасной: инструмент
{
  const s = backupPage();
  head(s, { title: 'Портфель собирается за минуту', lead: 'Эксперт меняет состав и сразу видит новый результат.' });

  const bars = [
    { w: 7.4, g: G.pale, label: nf(ALL_COMBOS), cap: 'столько портфелей вообще можно собрать', color: C.deep },
    { w: 4.3, g: G.mint, label: String(admitted), cap: 'столько остаётся, если держать условия кейса', color: C.white },
    { w: 2.3, g: G.deep, label: '1', cap: 'тот, который мы предлагаем региону', color: C.white },
  ];
  bars.forEach((b, i) => {
    const y = 2.16 + i * 1.16;
    s.addImage({ data: b.g, x: L.M, y, w: b.w, h: 0.88 });
    T(s, b.label, { x: L.M + 0.32, y, w: 2.6, h: 0.88, fontSize: 28, bold: true, color: b.color, valign: 'middle' });
    T(s, b.cap, { x: L.M + b.w + 0.3, y, w: 4.6, h: 0.88, fontSize: 12.5, color: C.ink2, valign: 'middle' });
    if (i < 2) flow(s, { x: L.M + 0.78, y: y + 0.92, d: 0.2, color: C.mint, dir: 'down' });
  });

  card(s, { x: L.M, y: 5.72, w: 11.893, h: 0.92 });
  ['открыть портфель', 'переключить бюджет', 'заменить лот', 'увидеть, что сломалось', 'вернуть обратно'].forEach((t, i) => {
    const x = L.M + 0.34 + i * 2.32;
    T(s, String(i + 1), { x, y: 5.72, w: 0.26, h: 0.92, fontSize: 13, bold: true, color: C.mint, valign: 'middle' });
    T(s, t, { x: x + 0.28, y: 5.72, w: 1.78, h: 0.92, fontSize: 11.5, color: C.ink2, valign: 'middle' });
    if (i < 4) flow(s, { x: x + 2.06, y: 6.09, d: 0.16, color: 'BBD3C6' });
  });

  s.addNotes(notes(8));
}

// ─────────────────────────────────────────── 9. Запасной: условия
{
  const s = backupPage();
  head(s, { title: 'Девять условий кейса', lead: 'Инструмент показывает по каждому факт, предел и остаток.' });

  const labels = {
    exact_lot_count: 'Четыре лота',
    territorial_archetypes: 'Территории',
    capability_groups: 'Технологические группы',
    public_core_lots: 'Общедоступные сервисы',
    c0_limit: 'Стартовые затраты',
    opex_limit: 'Содержание в год',
    vpub_floor: 'Общественная польза',
    kcash_floor: 'Поступления к содержанию',
    t_rep_floor: 'Тиражируемость',
  };
  const order = ['exact_lot_count', 'territorial_archetypes', 'capability_groups', 'public_core_lots', 'c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor'];
  const cw = 3.816, ch = 1.24;
  order.forEach((code, i) => {
    const c = checkOf(code === 'c0_limit' ? stress : base, code);
    const dec = Number.isInteger(c.actual) && Number.isInteger(c.threshold) ? 0 : 2;
    const x = L.M + (i % 3) * (cw + 0.22);
    const y = 2.06 + Math.floor(i / 3) * (ch + 0.2);
    const tight = c.operator === '<=' ? c.actual / c.threshold : c.threshold / c.actual;
    const tense = tight > 0.9 && c.margin !== 0;
    const cc = tense ? C.brass : C.brand;
    const fact = c.operator === '<='
      ? `${nf(c.actual, dec)} при пределе ${nf(c.threshold, dec)}`
      : c.operator === '>='
        ? `${nf(c.actual, dec)} при минимуме ${nf(c.threshold, dec)}`
        : `${nf(c.actual, dec)}, ровно столько и нужно`;
    card(s, { x, y, w: cw, h: ch });
    badge(s, { x: x + 0.26, y: y + 0.24, d: 0.38, img: I.check, pad: 0.095, line: tense ? 'E3CFA6' : 'C8E5D5' });
    T(s, labels[code], { x: x + 0.76, y: y + 0.22, w: cw - 1.0, h: 0.28, fontSize: 12, bold: true, color: C.ink });
    T(s, fact, { x: x + 0.76, y: y + 0.5, w: cw - 1.0, h: 0.26, fontSize: 11, color: C.ink2 });
    const mw = cw - 2.3;
    meter(s, { x: x + 0.76, y: y + 0.88, w: mw, frac: tight, color: cc });
    T(s, c.margin === 0 ? 'ровно порог' : `запас ${nf(Math.abs(c.margin), dec)}`, {
      x: x + 0.76 + mw + 0.14, y: y + 0.78, w: 1.22, h: 0.3, fontSize: 9.5, color: cc,
    });
  });

  s.addImage({ data: G.mark, x: L.M, y: 6.34, w: 6.9, h: 0.54 });
  T(s, `Тоньше всего запас по старту при урезанном бюджете: ${nf(c0Stress.margin)} млн ₽`, {
    x: L.M + 0.28, y: 6.34, w: 6.5, h: 0.54, fontSize: 12, bold: true, color: C.deep, valign: 'middle',
  });

  s.addNotes(notes(9));
}

// ─────────────────────────────────────────── 10. Запасной: договорная схема
{
  const s = backupPage();
  head(s, { title: 'Кто за что отвечает', lead: 'Заказчик держит стандарты и данные, конкуренция сохраняется.' });

  const chain = [
    { ic: I.users, t: 'Заказчик', b: 'стандарты, права на историю данных, правила доступа и приёмка' },
    { ic: I.settings, t: 'Оператор', b: 'единый сервис, SLA, журналы, интеграции и поддержка' },
    { ic: I.sat, t: 'Поставщики', b: 'отдельные компоненты и периоды услуги, конкурируют между собой' },
  ];
  const cw = 3.68;
  chain.forEach((c, i) => {
    const x = L.M + i * (cw + 0.52);
    card(s, { x, y: 2.1, w: cw, h: 1.9 });
    badge(s, { x: x + 0.3, y: 2.36, d: 0.66, img: c.ic, pad: 0.16 });
    T(s, c.t, { x: x + 1.1, y: 2.4, w: cw - 1.36, h: 0.32, fontSize: 14, bold: true, color: C.ink });
    T(s, c.b, { x: x + 0.3, y: 3.16, w: cw - 0.6, h: 0.72, fontSize: 11.5, color: C.ink2 });
    if (i < 2) flow(s, { x: x + cw + 0.16, y: 2.95, d: 0.2 });
  });

  card(s, { x: L.M, y: 4.28, w: 5.84, h: 2.0 });
  badge(s, { x: L.M + 0.32, y: 4.56, d: 0.66, img: I.swap, pad: 0.16 });
  T(s, 'Когда меняем поставщика', { x: L.M + 1.12, y: 4.6, w: 4.4, h: 0.32, fontSize: 14, bold: true, color: C.ink });
  T(s, 'Повторно нарушен критический SLA, утрачены права на данные или закрыт формат выгрузки. Прежний поставщик отдаёт историю и настройки, новый проходит контрольный пересчёт и период параллельной работы.', {
    x: L.M + 0.32, y: 5.36, w: 5.2, h: 0.8, fontSize: 11.5, color: C.ink2,
  });

  card(s, { x: 6.77, y: 4.28, w: 5.84, h: 2.0 });
  badge(s, { x: 7.09, y: 4.56, d: 0.66, img: I.alert, pad: 0.16, line: 'E3CFA6' });
  T(s, 'Восемь рисков, у каждого владелец', { x: 7.89, y: 4.6, w: 4.5, h: 0.32, fontSize: 14, bold: true, color: C.brass });
  ['данные', 'ложный сигнал', 'поставщик', 'внедрение', 'доступ', 'спрос', 'платежи', 'KPI'].forEach((r, i) => {
    chip(s, {
      x: 7.09 + (i % 4) * 1.36, y: 5.36 + Math.floor(i / 4) * 0.46, w: 1.28, h: 0.38,
      text: r, fill: C.soft, border: 'D5EADF', color: C.deep, size: 9, bold: false,
    });
  });

  s.addNotes(notes(10));
}

// ─────────────────────────────────────────── 11. Запасной: тиражирование
{
  const s = backupPage();
  head(s, { title: 'Тираж без переделки', lead: 'Следующий регион получает готовую основу.' });

  [
    { t: 'Переносим как есть', ic: I.copy, color: C.brand, items: ['каталог сервисов и ролей', 'обработку данных и модель событий', 'интерфейсы и форматы выгрузки', 'доступ и журналирование', 'шаблоны SLA и договоров', 'методику KPI и базу знаний'] },
    { t: 'Настраиваем на месте', ic: I.map, color: C.brass, items: ['границы и сезонные пороги для пожаров', 'зоны и типы событий для экологии', 'поля, культуры и права хозяйств', 'объекты, маршруты и регламент реакции'] },
  ].forEach((cl, i) => {
    const x = L.M + i * 6.05;
    card(s, { x, y: 2.1, w: 5.84, h: 3.2 });
    badge(s, { x: x + 0.32, y: 2.36, d: 0.66, img: cl.ic, pad: 0.16, line: i ? 'E3CFA6' : 'C8E5D5' });
    T(s, cl.t, { x: x + 1.12, y: 2.4, w: 4.4, h: 0.34, fontSize: 15, bold: true, color: cl.color });
    cl.items.forEach((it, j) => {
      const y = 3.2 + j * 0.34;
      s.addShape('ellipse', { x: x + 0.36, y: y + 0.1, w: 0.1, h: 0.1, fill: { color: cl.color }, line: { color: cl.color, width: 0 } });
      T(s, it, { x: x + 0.62, y, w: 5.0, h: 0.3, fontSize: 11.5, color: C.ink2 });
    });
  });

  ['пилот в регионе', 'разбор и обновление ядра', 'следующий регион по шаблону'].forEach((t, i) => {
    const x = L.M + i * 4.12;
    chip(s, { x, y: 5.68, w: 3.6, h: 0.6, text: t, size: 12, color: C.deep });
    if (i < 2) flow(s, { x: x + 3.74, y: 5.88, d: 0.2 });
  });

  s.addNotes(notes(11));
}

const out = path.join(HERE, 'kosmo-deck.pptx');
await pres.writeFile({ fileName: out });
const shown = SC.filter((x) => !x.backup);
const secs = shown.reduce((a, x) => a + x.seconds, 0);
console.log('готово:', out);
console.log(`показываем ${shown.length} слайдов (${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}), запасных ${SC.length - shown.length}`);
