// Сборка презентации защиты: docs/presentation/kosmo-deck.pptx
//
// Цифры на слайдах читаются из results/ — единственного источника чисел проекта,
// поэтому слайды и инструмент не могут разойтись.
//
// Запуск:  node docs/presentation/build.mjs

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';
import { C, F, L, defineMasters, head, foot, card, chip, badge, stat, meter, flow } from './theme.mjs';
import { icon, qr } from './assets.mjs';
import { buildScript } from './script.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));

import {
  SITE, TOTAL, base, stress, ranking, m, checkOf, c0Base, c0Stress,
  FINAL_KEY, rankRow, leader, admitted, ALL_COMBOS, altV7,
  publicC0, privateC0, dVpub, nf, plus, SCRIPT_CONTEXT,
} from './data.mjs';

const SC = buildScript(SCRIPT_CONTEXT);
const notes = (n) => SC.find((x) => x.n === n).say.join(' ');

// ——— документ ———

const pres = new PptxGenJS();
pres.author = 'Команда «Молоток»';
pres.company = 'КосмоХакатон 2026, Кейс 02';
pres.title = 'Космос как инфраструктура';
defineMasters(pres);

const ICONS = {};
for (const [k, [n, c]] of Object.entries({
  fire: ['TbFlame', C.mint], env: ['TbLeaf', C.mint], agri: ['TbPlant2', C.mint], trans: ['TbTruckDelivery', C.mint],
  check: ['TbCheck', C.mint], bank: ['TbBuildingBank', C.mint], brief: ['TbBriefcase', C.mint],
  users: ['TbUsers', C.mint], settings: ['TbSettings', C.mint], copy: ['TbCopy', C.mint],
  flag: ['TbFlag', C.mint], rocket: ['TbRocket', C.mint], map: ['TbMap2', C.mint],
  alert: ['TbAlertTriangle', C.brass], shield: ['TbShieldCheck', C.mint], swap: ['TbArrowsExchange', C.mint],
  target: ['TbTargetArrow', C.mint], key: ['TbKey', C.mint], file: ['TbFileText', C.mint],
  dots: ['TbChartDots', C.mint], sat: ['TbSatellite', C.mint], clip: ['TbClipboardCheck', C.mint],
})) ICONS[k] = await icon(n, c);
const QR = await qr(SITE);

// ─────────────────────────────────────────── 1. Обложка
{
  const s = pres.addSlide({ masterName: 'COVER' });
  s.addText('КОСМОХАКАТОН 2026,  КЕЙС 02', {
    x: L.M, y: 0.72, w: 7, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, charSpacing: 2.4, color: C.mint,
  });
  s.addText('Космос\nкак инфраструктура', {
    x: L.M, y: 1.16, w: 7.1, h: 1.9, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 40, bold: true, color: C.ink, lineSpacingMultiple: 1.06,
  });
  s.addText('Регион получает не снимки, а четыре работающих сервиса и понятные правила доступа к ним.', {
    x: L.M, y: 3.1, w: 6.9, h: 0.6, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13, color: C.ink2,
  });

  [['FIRE-A'], ['ENV-A'], ['AGRI-B'], ['TRANS-B']].forEach(([t], i) => {
    chip(s, { x: L.M + i * 1.72, y: 3.86, w: 1.56, h: 0.46, text: t, color: C.mint, fill: C.card, border: C.mintDeep, size: 12.5, bold: true });
  });

  card(s, { x: 8.22, y: 1.16, w: 4.49, h: 4.32, fill: C.card });
  [
    [nf(m.c0), 'старт, млн ₽'],
    [nf(m.vpub), 'общественная польза, млн ₽ в год'],
    [nf(m.cash, 1), 'поступления, млн ₽ в год'],
    [nf(c0Stress.margin), 'запас при урезанном бюджете, млн ₽'],
  ].forEach(([v, lab], i) => {
    const y = 1.46 + i * 1.02;
    stat(s, { x: 8.62, y, w: 3.7, value: v, label: lab, size: 30 });
    if (i < 3) s.addShape('rect', { x: 8.62, y: y + 0.84, w: 3.7, h: 0.008, fill: { color: C.rule } });
  });

  s.addText(SITE.replace('https://', ''), {
    x: L.M, y: 6.02, w: 5, h: 0.34, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 15, bold: true, color: C.mint,
  });
  s.addText('Команда «Молоток». Голубев Павел, Петр Кузнецов, Тимофей Максимов, Лихатин Андрей, Потапенко Филипп', {
    x: L.M, y: 6.42, w: 8.8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: C.muted,
  });
  s.addImage({ data: QR, x: 11.62, y: 5.86, w: 1.09, h: 1.09 });
  s.addText('наведите камеру', {
    x: 9.4, y: 6.24, w: 2.1, h: 0.3, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9.5, color: C.muted, align: 'right',
  });
  s.addNotes(notes(1));
}

// ─────────────────────────────────────────── 2. Идея
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Идея', title: 'Мы продаём региону результат, а не данные', lead: 'Космический сервис полезен там, где он заканчивается решением человека.' });

  const cards = [
    { ic: ICONS.target, t: 'Готовый ответ', b: 'Не снимки и не слои, а короткий ответ: где событие, насколько ему верить и что делать дальше.' },
    { ic: ICONS.users, t: 'Портфель, а не лот', b: 'Четыре сервиса в разных регионах. Общественные держат смысл, прикладные приносят деньги.' },
    { ic: ICONS.key, t: 'Общие правила', b: 'Единый оператор, открытые форматы, права на историю данных остаются у заказчика.' },
  ];
  const cw = 3.88;
  cards.forEach((c, i) => {
    const x = L.M + i * (cw + 0.22);
    card(s, { x, y: 1.94, w: cw, h: 2.5 });
    badge(s, { x: x + 0.32, y: 2.24, d: 0.74, img: c.ic });
    s.addText(c.t, { x: x + 0.32, y: 3.14, w: cw - 0.64, h: 0.32, isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: C.ink });
    s.addText(c.b, { x: x + 0.32, y: 3.52, w: cw - 0.64, h: 0.8, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: C.ink2 });
  });

  card(s, { x: L.M, y: 4.72, w: 12.09, h: 1.62, fill: C.card2 });
  s.addText('Заказчик покупает работающую услугу и сохраняет контроль', {
    x: L.M + 0.4, y: 4.96, w: 11.3, h: 0.36, isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: C.mint,
  });
  s.addText('Стандарты, права на историю данных и правила доступа остаются у него. Поставщики конкурируют за отдельные части услуги и заменяются без остановки сервиса. Регион, который придёт следующим, получает то же ядро и настраивает его под себя.', {
    x: L.M + 0.4, y: 5.38, w: 11.3, h: 0.8, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: C.ink2,
  });

  foot(s, { section: 'Идея', n: 2, total: TOTAL });
  s.addNotes(notes(2));
}

// ─────────────────────────────────────────── 3. Портфель
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Портфель', title: 'Четыре сервиса, четыре региона', lead: 'Каждый заканчивается конкретным действием пользователя.' });

  const items = [
    { code: 'FIRE-A', ic: ICONS.fire, region: 'Сибирь', user: 'Лесные и диспетчерские службы', act: 'проверить сигнал', kpi: 'время до проверки' },
    { code: 'ENV-A', ic: ICONS.env, region: 'Волго-Каспий', user: 'Природоохранный орган', act: 'назначить инспекцию', kpi: 'доля подтверждённых' },
    { code: 'AGRI-B', ic: ICONS.agri, region: 'Юг', user: 'Хозяйства и органы АПК', act: 'обследовать участок', kpi: 'сигнал с действием' },
    { code: 'TRANS-B', ic: ICONS.trans, region: 'Центр', user: 'Операторы и перевозчики', act: 'изменить план', kpi: 'время до решения' },
  ];
  const cw = 2.86;
  items.forEach((it, i) => {
    const x = L.M + i * (cw + 0.22);
    card(s, { x, y: 1.86, w: cw, h: 3.52 });
    badge(s, { x: x + 0.28, y: 2.12, d: 0.8, img: it.ic });
    s.addText(it.code, { x: x + 0.28, y: 3.02, w: cw - 0.56, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: C.ink });
    s.addText(it.region, { x: x + 0.28, y: 3.3, w: cw - 0.56, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.mint });
    s.addShape('rect', { x: x + 0.28, y: 3.66, w: cw - 0.56, h: 0.008, fill: { color: C.rule } });
    s.addText(it.user, { x: x + 0.28, y: 3.8, w: cw - 0.56, h: 0.5, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: C.ink2 });
    s.addText(it.act, { x: x + 0.28, y: 4.3, w: cw - 0.56, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 12, bold: true, color: C.ink });
    chip(s, { x: x + 0.28, y: 4.72, w: cw - 0.56, h: 0.42, text: it.kpi, fill: C.card2, border: C.rule, color: C.ink2, size: 10.5 });
  });

  [
    { t: 'FIRE и ENV работают как общедоступная основа для органов', fill: C.mintDeep, color: C.ink },
    { t: 'AGRI и TRANS дают якорный слой заказчику и платную детализацию', fill: C.card2, color: C.ink2 },
  ].forEach((st, i) => {
    const x = L.M + i * 6.13;
    s.addShape('roundRect', { x, y: 5.62, w: 5.96, h: 0.62, rectRadius: 0.09, fill: { color: st.fill }, line: { color: C.rule, width: 1 } });
    s.addText(st.t, { x: x + 0.28, y: 5.62, w: 5.4, h: 0.62, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: st.color, valign: 'middle' });
  });
  s.addText('Плательщиков называем как предположение команды: подтверждённых контрактов у нас нет.', {
    x: L.M, y: 6.36, w: 12.09, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 9.5, color: C.muted,
  });

  foot(s, { section: 'Сервисы и пользователи', n: 3, total: TOTAL });
  s.addNotes(notes(3));
}

// ─────────────────────────────────────────── 4. Инструмент
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Инструмент', title: 'Портфель собирается на экране, а не в таблице', lead: 'Эксперт меняет состав и сразу видит новый результат.' });

  const bars = [
    { w: 7.6, fill: C.card2, label: nf(ALL_COMBOS), cap: 'столько портфелей вообще можно собрать', color: C.ink, border: C.rule },
    { w: 4.3, fill: C.mintDeep, label: String(admitted), cap: 'столько остаётся, если держать условия кейса', color: C.ink, border: C.mintDeep },
    { w: 2.2, fill: C.mint, label: '1', cap: 'тот, который мы предлагаем региону', color: C.bg, border: C.mint },
  ];
  bars.forEach((b, i) => {
    const y = 2.16 + i * 1.2;
    s.addShape('roundRect', { x: L.M, y, w: b.w, h: 0.88, rectRadius: 0.1, fill: { color: b.fill }, line: { color: b.border, width: 1 } });
    s.addText(b.label, { x: L.M + 0.3, y, w: 2.6, h: 0.88, isTextBox: true, margin: 0, fontFace: F, fontSize: 29, bold: true, color: b.color, valign: 'middle' });
    s.addText(b.cap, { x: L.M + b.w + 0.26, y, w: 4.2, h: 0.88, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: C.ink2, valign: 'middle' });
    if (i < 2) flow(s, { x: L.M + 0.74, y: y + 0.94, d: 0.18, color: C.mintDeep, dir: 'down' });
  });

  card(s, { x: L.M, y: 5.86, w: 12.09, h: 0.76, fill: C.card });
  [
    ['Заменить лот и пересчитать', ICONS.swap],
    ['Переключить сценарий бюджета', ICONS.settings],
    ['Выгрузить результат для организаторов', ICONS.file],
  ].forEach(([t, ic], i) => {
    const x = L.M + 0.32 + i * 4.0;
    s.addImage({ data: ic, x, y: 6.11, w: 0.24, h: 0.24 });
    s.addText(t, { x: x + 0.34, y: 5.86, w: 3.5, h: 0.76, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.ink2, valign: 'middle' });
  });

  foot(s, { section: 'Инструмент', n: 4, total: TOTAL });
  s.addNotes(notes(4));
}

// ─────────────────────────────────────────── 5. Поле выбора
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Выбор', title: 'Мы выбирали не максимум, а баланс', lead: `Каждая точка — портфель, который проходит условия при урезанном бюджете.` });

  const pts = ranking.map((r) => ({ key: r.variant, c0: Number(r.c0), vpub: Number(r.vpub), rank: Number(r.rank) }));
  const px0 = 1.28, px1 = 8.42, py0 = 2.26, py1 = 6.02;
  const xmin = 1120, xmax = Number(c0Stress.threshold);
  const ymin = Math.floor(Math.min(...pts.map((p) => p.vpub)) / 50) * 50;
  const ymax = Math.ceil(Math.max(...pts.map((p) => p.vpub)) / 50) * 50;
  const X = (v) => px0 + ((v - xmin) / (xmax - xmin)) * (px1 - px0);
  const Y = (v) => py1 - ((v - ymin) / (ymax - ymin)) * (py1 - py0);

  for (let t = ymin; t <= ymax; t += 100) {
    s.addShape('rect', { x: px0, y: Y(t), w: px1 - px0, h: 0.006, fill: { color: C.rule } });
    s.addText(nf(t), { x: px0 - 0.86, y: Y(t) - 0.12, w: 0.78, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 8.5, color: C.muted, align: 'right' });
  }
  for (const t of [1130, 1140, 1150, 1160, 1170]) {
    s.addText(nf(t), { x: X(t) - 0.35, y: py1 + 0.1, w: 0.7, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 8.5, color: C.muted, align: 'center' });
  }
  s.addText('общественная польза, млн ₽ в год', { x: px0 - 0.9, y: py0 - 0.36, w: 3.2, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 9, color: C.muted });
  s.addText('стартовые затраты, млн ₽', { x: px1 - 2.6, y: py1 + 0.36, w: 2.6, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 9, color: C.muted, align: 'right' });

  s.addShape('rect', { x: X(xmax), y: py0 - 0.1, w: 0.014, h: py1 - py0 + 0.1, fill: { color: C.crit } });
  s.addText(`предел бюджета в стрессе ${nf(xmax)}`, { x: X(xmax) - 2.7, y: py0 - 0.44, w: 2.64, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 9, color: C.crit, align: 'right' });

  for (const p of pts) {
    if (p.key === FINAL_KEY || p.rank === 1) continue;
    s.addShape('ellipse', { x: X(p.c0) - 0.045, y: Y(p.vpub) - 0.045, w: 0.09, h: 0.09, fill: { color: C.mintDeep, transparency: 45 }, line: { color: C.mintDeep, width: 0 } });
  }
  const mark = (key, color, label, dx, dy) => {
    const p = pts.find((q) => q.key === key);
    s.addShape('ellipse', { x: X(p.c0) - 0.105, y: Y(p.vpub) - 0.105, w: 0.21, h: 0.21, fill: { color }, line: { color: C.bg, width: 1.5 } });
    s.addText(label, { x: X(p.c0) + dx, y: Y(p.vpub) + dy, w: 2.1, h: 0.24, isTextBox: true, margin: 0, fontFace: F, fontSize: 9.5, bold: true, color });
  };
  mark(leader.variant, C.brass, 'первый по баллу модели', 0.16, -0.34);
  mark(FINAL_KEY, C.mint, 'наш выбор', 0.18, -0.1);

  const rx = 8.98;
  card(s, { x: rx, y: 2.02, w: 3.73, h: 4.0 });
  s.addText('Почему этот', { x: rx + 0.3, y: 2.26, w: 3.1, h: 0.32, isTextBox: true, margin: 0, fontFace: F, fontSize: 14, bold: true, color: C.ink });
  [
    'Больше общественной пользы, чем у более дешёвых вариантов',
    'Денег хватает, чтобы содержать все четыре сервиса',
    'Остаётся запас, если бюджет урежут',
  ].forEach((t, i) => {
    const y = 2.76 + i * 0.62;
    s.addShape('ellipse', { x: rx + 0.32, y: y + 0.1, w: 0.1, h: 0.1, fill: { color: C.mint }, line: { color: C.mint, width: 0 } });
    s.addText(t, { x: rx + 0.58, y, w: 2.86, h: 0.56, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.ink2 });
  });
  s.addShape('rect', { x: rx + 0.3, y: 4.7, w: 3.13, h: 0.008, fill: { color: C.rule } });
  s.addText(`${plus(dVpub, 0)} млн ₽ пользы в год`, { x: rx + 0.3, y: 4.86, w: 3.1, h: 0.32, isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: C.mint });
  s.addText('по сравнению с первым по баллу вариантом: он дешевле, но переводит прикладные сервисы в коммерческий режим и срезает общедоступную часть.', {
    x: rx + 0.3, y: 5.2, w: 3.13, h: 0.62, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: C.ink2,
  });

  foot(s, { section: 'Сравнение вариантов', n: 5, total: TOTAL });
  s.addNotes(notes(5));
}

// ─────────────────────────────────────────── 6. Условия кейса
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Условия', title: 'Условия кейса видно на одном экране', lead: 'Инструмент показывает не только результат, но и то, сколько до предела осталось.' });

  const labels = {
    exact_lot_count: 'Четыре лота',
    territorial_archetypes: 'Территории',
    capability_groups: 'Технологические группы',
    public_core_lots: 'Общедоступные сервисы',
    c0_limit: 'Стартовые затраты в стрессе',
    opex_limit: 'Содержание в год',
    vpub_floor: 'Общественная польза',
    kcash_floor: 'Поступления к содержанию',
    t_rep_floor: 'Тиражируемость',
  };
  const order = ['exact_lot_count', 'territorial_archetypes', 'capability_groups', 'public_core_lots', 'c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor'];
  const cw = 3.88, ch = 1.24;
  order.forEach((code, i) => {
    const c = checkOf(code === 'c0_limit' ? stress : base, code);
    const dec = Number.isInteger(c.actual) && Number.isInteger(c.threshold) ? 0 : 2;
    const x = L.M + (i % 3) * (cw + 0.22);
    const y = 1.94 + Math.floor(i / 3) * (ch + 0.2);
    const tight = c.operator === '<=' ? c.actual / c.threshold : c.threshold / c.actual;
    // Латунью отмечаем только по-настоящему тонкий запас, а не условие,
    // которое выполняется ровно (там запас нулевой по смыслу).
    const cc = tight > 0.9 && c.margin !== 0 ? C.brass : C.mint;
    const fact = c.operator === '<='
      ? `${nf(c.actual, dec)} при пределе ${nf(c.threshold, dec)}`
      : c.operator === '>='
        ? `${nf(c.actual, dec)} при минимуме ${nf(c.threshold, dec)}`
        : `${nf(c.actual, dec)}, ровно столько и нужно`;
    card(s, { x, y, w: cw, h: ch });
    s.addShape('ellipse', { x: x + 0.24, y: y + 0.24, w: 0.34, h: 0.34, fill: { color: C.card2 }, line: { color: cc, width: 1 } });
    s.addImage({ data: ICONS.check, x: x + 0.315, y: y + 0.315, w: 0.19, h: 0.19 });
    s.addText(labels[code], { x: x + 0.72, y: y + 0.2, w: cw - 0.96, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, bold: true, color: C.ink });
    s.addText(fact, { x: x + 0.72, y: y + 0.48, w: cw - 0.96, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2 });
    const mw = cw - 2.34;
    meter(s, { x: x + 0.72, y: y + 0.86, w: mw, frac: tight, color: cc });
    s.addText(c.margin === 0 ? 'ровно порог' : `запас ${nf(Math.abs(c.margin), dec)}`, {
      x: x + 0.72 + mw + 0.14, y: y + 0.76, w: 1.24, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 9.5, color: cc, align: 'left',
    });
  });

  chip(s, {
    x: L.M, y: 6.1, w: 12.09, h: 0.5,
    text: `Тоньше всего запас по стартовым затратам в стрессе: ${nf(c0Stress.margin)} млн ₽. Чем полнее полоска, тем ближе предел.`,
    fill: C.card, border: C.rule, color: C.ink2, size: 11, align: 'center',
  });

  foot(s, { section: 'Условия кейса', n: 6, total: TOTAL });
  s.addNotes(notes(6));
}

// ─────────────────────────────────────────── 7. Деньги
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Деньги', title: 'Кто платит за старт и кто платит за год', lead: 'Два контура на старте и положительный баланс в год.' });

  s.addText('Старт, млн ₽', { x: L.M, y: 1.94, w: 5.9, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.muted });
  const sw = 5.96, sy = 2.3, sh = 0.86;
  const wPub = sw * (publicC0 / m.c0) - 0.03; // зазор между долями
  s.addShape('roundRect', { x: L.M, y: sy, w: sw, h: sh, rectRadius: 0.1, fill: { color: C.mintDeep }, line: { color: C.mintDeep, width: 0 } });
  s.addShape('roundRect', { x: L.M, y: sy, w: wPub, h: sh, rectRadius: 0.1, fill: { color: C.deep }, line: { color: C.deep, width: 0 } });
  s.addText(nf(publicC0), { x: L.M + 0.24, y: sy, w: 1.6, h: sh, isTextBox: true, margin: 0, fontFace: F, fontSize: 17, bold: true, color: C.ink, valign: 'middle' });
  s.addText(nf(privateC0), { x: L.M + wPub + 0.24, y: sy, w: 1.6, h: sh, isTextBox: true, margin: 0, fontFace: F, fontSize: 17, bold: true, color: C.ink, valign: 'middle' });
  [[ICONS.bank, 'Бюджет за FIRE и ENV', L.M], [ICONS.brief, 'Частный партнёр за AGRI и TRANS', L.M + wPub]].forEach(([ic, t, x]) => {
    s.addImage({ data: ic, x, y: sy + sh + 0.2, w: 0.2, h: 0.2 });
    s.addText(t, { x: x + 0.28, y: sy + sh + 0.16, w: 3.3, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2 });
  });
  s.addText(`вместе ${nf(m.c0)} млн ₽`, { x: L.M, y: sy + sh + 0.56, w: 5.96, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, bold: true, color: C.mint });

  const bx = 7.37;
  s.addText('Год, млн ₽', { x: bx, y: 1.94, w: 5.3, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.muted });
  const bh = 2.0, by = 2.66, maxV = Math.max(m.cash, m.opex);
  [
    { v: m.cash, t: 'поступления', c: C.mint, x: bx + 0.3 },
    { v: m.opex, t: 'содержание', c: C.mintDeep, x: bx + 2.0 },
  ].forEach((b) => {
    const h = (b.v / maxV) * bh;
    s.addShape('roundRect', { x: b.x, y: by + bh - h, w: 1.3, h, rectRadius: 0.06, fill: { color: b.c }, line: { color: b.c, width: 0 } });
    s.addText(nf(b.v, b.v % 1 ? 1 : 0), { x: b.x, y: by + bh - h - 0.36, w: 1.3, h: 0.32, isTextBox: true, margin: 0, fontFace: F, fontSize: 15, bold: true, color: C.ink, align: 'center' });
    s.addText(b.t, { x: b.x - 0.1, y: by + bh + 0.1, w: 1.5, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2, align: 'center' });
  });
  card(s, { x: bx + 3.6, y: by + 0.44, w: 1.72, h: 1.2, fill: C.card2 });
  s.addText(plus(m.cash - m.opex, 1), { x: bx + 3.6, y: by + 0.6, w: 1.72, h: 0.5, isTextBox: true, margin: 0, fontFace: F, fontSize: 22, bold: true, color: C.mint, align: 'center' });
  s.addText('остаётся\nв год', { x: bx + 3.6, y: by + 1.08, w: 1.72, h: 0.46, isTextBox: true, margin: 0, fontFace: F, fontSize: 9.5, color: C.ink2, align: 'center' });

  s.addShape('rect', { x: L.M, y: 5.42, w: 12.09, h: 0.008, fill: { color: C.rule } });
  [
    ['10 лет', 'срок партнёрства: за семь частный контур не возвращает вложенное'],
    ['2027–2033', 'горизонт расчёта, без дисконтирования и налогов'],
    ['спрос', 'коммерческая часть пока гипотеза, её проверяют пилот и тарифный тест'],
  ].forEach(([v, cap], i) => {
    const x = L.M + i * 4.03;
    s.addText(v, { x, y: 5.6, w: 3.8, h: 0.34, isTextBox: true, margin: 0, fontFace: F, fontSize: 16, bold: true, color: C.ink });
    s.addText(cap, { x, y: 5.96, w: 3.8, h: 0.5, isTextBox: true, margin: 0, fontFace: F, fontSize: 10, color: C.muted });
  });

  foot(s, { section: 'Финансирование', n: 7, total: TOTAL });
  s.addNotes(notes(7));
}

// ─────────────────────────────────────────── 8. Урезанный бюджет
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Устойчивость', title: 'Если бюджет урежут, состав не меняется', lead: 'В стрессовом сценарии падает предел затрат, а стоимость сервисов остаётся прежней.' });

  const gx = L.M, gw = 12.09, gy = 2.86, gh = 0.78;
  const scale = (v) => (v / Number(c0Base.threshold)) * gw;
  s.addShape('roundRect', { x: gx, y: gy, w: gw, h: gh, rectRadius: 0.1, fill: { color: C.card }, line: { color: C.rule, width: 1 } });
  s.addShape('roundRect', { x: gx, y: gy, w: scale(m.c0), h: gh, rectRadius: 0.1, fill: { color: C.mintDeep }, line: { color: C.mintDeep, width: 0 } });
  s.addShape('rect', { x: gx + scale(m.c0), y: gy, w: scale(c0Stress.margin), h: gh, fill: { color: C.brass, transparency: 30 } });
  s.addText(`наш старт ${nf(m.c0)}`, { x: gx + 0.28, y: gy, w: 3.4, h: gh, isTextBox: true, margin: 0, fontFace: F, fontSize: 18, bold: true, color: C.ink, valign: 'middle' });

  const tick = (v, label, color, labelY) => {
    s.addShape('rect', { x: gx + scale(v), y: gy - 0.3, w: 0.014, h: gh + 0.6, fill: { color } });
    s.addText(label, { x: gx + scale(v) - 2.7, y: labelY, w: 2.62, h: 0.26, isTextBox: true, margin: 0, fontFace: F, fontSize: 10, bold: true, color, align: 'right' });
  };
  tick(Number(c0Base.threshold), `обычный бюджет ${nf(c0Base.threshold)}`, C.muted, gy - 1.02);
  tick(Number(c0Stress.threshold), `урезанный бюджет ${nf(c0Stress.threshold)}`, C.crit, gy - 0.64);
  s.addText(`запас ${nf(c0Stress.margin)} млн ₽`, {
    x: gx + scale(Number(c0Stress.threshold)) - 2.86, y: gy + gh + 0.16, w: 2.62, h: 0.28, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 11, bold: true, color: C.brass, align: 'right',
  });

  [
    { ic: ICONS.shield, t: 'Состав сохраняем', b: 'Не нужно заново согласовывать пользователей, доступ и договоры. Портфель остаётся тем же, просто с меньшим запасом.', color: C.mint },
    { ic: ICONS.alert, t: 'Если спрос не придёт', b: 'Мы посчитали и такой вариант: без коммерческой выручки содержание сервисов недофинансировано на 123 млн ₽ в год, и покрывать это придётся заказчику.', color: C.brass },
  ].forEach((cd, i) => {
    const x = L.M + i * 6.13;
    card(s, { x, y: 4.24, w: 5.96, h: 1.72 });
    badge(s, { x: x + 0.3, y: 4.5, d: 0.62, img: cd.ic, line: cd.color, pad: 0.15 });
    s.addText(cd.t, { x: x + 1.08, y: 4.52, w: 4.6, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 13, bold: true, color: cd.color });
    s.addText(cd.b, { x: x + 1.08, y: 4.84, w: 4.6, h: 0.98, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2 });
  });
  s.addText('Второй сценарий — наша собственная проверка, а не требование кейса.', {
    x: L.M, y: 6.14, w: 12.09, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 9.5, color: C.muted,
  });

  foot(s, { section: 'Устойчивость', n: 8, total: TOTAL });
  s.addNotes(notes(8));
}

// ─────────────────────────────────────────── 9. Как это устроено
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Организация', title: 'Один оператор, сменяемые поставщики', lead: 'Заказчик держит стандарты и данные, конкуренция сохраняется.' });

  const chain = [
    { ic: ICONS.users, t: 'Заказчик', b: 'стандарты, права на историю данных, правила доступа и приёмка' },
    { ic: ICONS.settings, t: 'Оператор', b: 'единый сервис, SLA, журналы, интеграции и поддержка' },
    { ic: ICONS.sat, t: 'Поставщики', b: 'отдельные компоненты и периоды услуги, конкурируют между собой' },
  ];
  const cw = 3.72;
  chain.forEach((c, i) => {
    const x = L.M + i * (cw + 0.52);
    card(s, { x, y: 1.9, w: cw, h: 1.86 });
    badge(s, { x: x + 0.28, y: 2.14, d: 0.62, img: c.ic, pad: 0.15 });
    s.addText(c.t, { x: x + 1.04, y: 2.18, w: cw - 1.3, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 13, bold: true, color: C.ink });
    s.addText(c.b, { x: x + 0.28, y: 2.92, w: cw - 0.56, h: 0.72, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2 });
    if (i < 2) flow(s, { x: x + cw + 0.16, y: 2.72, d: 0.2 });
  });

  card(s, { x: L.M, y: 4.0, w: 5.96, h: 1.9, fill: C.card });
  badge(s, { x: L.M + 0.28, y: 4.24, d: 0.62, img: ICONS.swap, pad: 0.15 });
  s.addText('Когда меняем поставщика', { x: L.M + 1.04, y: 4.28, w: 4.6, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 13, bold: true, color: C.ink });
  s.addText('Повторно нарушен критический SLA, утрачены права на данные или закрыт формат выгрузки. Прежний поставщик отдаёт историю и настройки, новый проходит контрольный пересчёт и период параллельной работы.', {
    x: L.M + 0.28, y: 4.98, w: 5.4, h: 0.84, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, color: C.ink2,
  });

  card(s, { x: 7.37, y: 4.0, w: 5.34, h: 1.9, fill: C.card });
  badge(s, { x: 7.65, y: 4.24, d: 0.62, img: ICONS.alert, line: C.brass, pad: 0.15 });
  s.addText('Восемь рисков, у каждого владелец', { x: 8.41, y: 4.28, w: 4.2, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 13, bold: true, color: C.brass });
  ['данные', 'ложный сигнал', 'поставщик', 'внедрение', 'доступ', 'спрос', 'платежи', 'KPI'].forEach((r, i) => {
    chip(s, {
      x: 7.65 + (i % 4) * 1.28, y: 5.02 + Math.floor(i / 4) * 0.4, w: 1.2, h: 0.32,
      text: r, fill: C.card2, border: C.rule, color: C.ink2, size: 8.5,
    });
  });
  s.addText('Для каждого риска записаны признак, мера и тот, кто за неё отвечает.', {
    x: L.M, y: 6.06, w: 12.09, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 10, color: C.muted,
  });

  foot(s, { section: 'Договорная схема', n: 9, total: TOTAL });
  s.addNotes(notes(9));
}

// ─────────────────────────────────────────── 10. Тиражирование
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Тиражирование', title: 'Ядро переносим, регион настраиваем', lead: 'Следующий регион получает готовую основу, а не проект с нуля.' });

  [
    { t: 'Переносим как есть', ic: ICONS.copy, color: C.mint, items: ['каталог сервисов и ролей', 'обработку данных и модель событий', 'интерфейсы и форматы выгрузки', 'доступ и журналирование', 'шаблоны SLA и договоров', 'методику KPI и базу знаний'] },
    { t: 'Настраиваем на месте', ic: ICONS.map, color: C.brass, items: ['границы и сезонные пороги для пожаров', 'зоны и типы событий для экологии', 'поля, культуры и права хозяйств', 'объекты, маршруты и регламент реакции'] },
  ].forEach((cl, i) => {
    const x = L.M + i * 6.13;
    card(s, { x, y: 1.9, w: 5.96, h: 3.16 });
    badge(s, { x: x + 0.3, y: 2.12, d: 0.62, img: cl.ic, line: cl.color, pad: 0.15 });
    s.addText(cl.t, { x: x + 1.08, y: 2.16, w: 4.6, h: 0.32, isTextBox: true, margin: 0, fontFace: F, fontSize: 14, bold: true, color: cl.color });
    cl.items.forEach((it, j) => {
      const y = 2.94 + j * 0.34;
      s.addShape('ellipse', { x: x + 0.34, y: y + 0.1, w: 0.09, h: 0.09, fill: { color: cl.color }, line: { color: cl.color, width: 0 } });
      s.addText(it, { x: x + 0.58, y, w: 5.1, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.ink2 });
    });
  });

  s.addText('Как передаём опыт', { x: L.M, y: 5.26, w: 6, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.muted });
  ['пилот в регионе', 'разбор и обновление ядра', 'следующий регион по шаблону'].forEach((t, i) => {
    const x = L.M + i * 4.16;
    chip(s, { x, y: 5.6, w: 3.66, h: 0.56, text: t, fill: C.card, border: C.mintDeep, color: C.ink, size: 11 });
    if (i < 2) flow(s, { x: x + 3.8, y: 5.78, d: 0.2 });
  });

  foot(s, { section: 'Тиражирование', n: 10, total: TOTAL });
  s.addNotes(notes(10));
}

// ─────────────────────────────────────────── 11. План
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'План', title: 'Пять шагов с 2027 по 2033 год', lead: 'У каждого шага есть результат, ответственный и признак завершения.' });

  const stages = [
    { y: '2027, первое полугодие', t: 'Заказчики и договоры', o: 'заказчик', ic: ICONS.flag },
    { y: '2027–2028', t: 'Пилоты по пожарам и экологии', o: 'оператор', ic: ICONS.target },
    { y: '2028, второе полугодие', t: 'Разбор пилотов и обновление ядра', o: 'оператор', ic: ICONS.settings },
    { y: '2029–2030', t: 'Запуск полей и транспорта', o: 'частный партнёр', ic: ICONS.rocket },
    { y: '2031–2033', t: 'Тираж в новые регионы', o: 'заказчик', ic: ICONS.copy },
  ];
  const cw = 2.29;
  s.addShape('rect', { x: L.M + 0.4, y: 3.22, w: 12.09 - 0.8, h: 0.012, fill: { color: C.rule } });
  stages.forEach((st, i) => {
    const x = L.M + i * (cw + 0.16);
    s.addText(st.y, { x, y: 2.3, w: cw, h: 0.52, isTextBox: true, margin: 0, fontFace: F, fontSize: 10.5, bold: true, color: C.mint, align: 'center' });
    s.addShape('ellipse', { x: x + cw / 2 - 0.24, y: 2.98, w: 0.48, h: 0.48, fill: { color: C.bg }, line: { color: C.mint, width: 1.5 } });
    s.addText(String(i + 1), { x: x + cw / 2 - 0.24, y: 2.98, w: 0.48, h: 0.48, isTextBox: true, margin: 0, fontFace: F, fontSize: 12, bold: true, color: C.mint, align: 'center', valign: 'middle' });
    card(s, { x, y: 3.72, w: cw, h: 1.92 });
    s.addImage({ data: st.ic, x: x + cw / 2 - 0.14, y: 3.96, w: 0.28, h: 0.28 });
    s.addText(st.t, { x: x + 0.16, y: 4.4, w: cw - 0.32, h: 0.76, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, bold: true, color: C.ink, align: 'center' });
    s.addText(st.o, { x: x + 0.16, y: 5.2, w: cw - 0.32, h: 0.28, isTextBox: true, margin: 0, fontFace: F, fontSize: 10, color: C.muted, align: 'center' });
  });

  chip(s, {
    x: L.M, y: 5.94, w: 12.09, h: 0.56,
    text: 'Шаг считается пройденным по принятым KPI и подписанной приёмке. Календарные сроки — наше допущение, а не условие кейса.',
    fill: C.card, border: C.rule, color: C.ink2, size: 11,
  });

  foot(s, { section: 'План реализации', n: 11, total: TOTAL });
  s.addNotes(notes(11));
}

// ─────────────────────────────────────────── 12. Финал
{
  const s = pres.addSlide({ masterName: 'BASE' });
  head(s, { kicker: 'Показ', title: 'Откройте и попробуйте сами', lead: 'Ничего не зашито: любой состав портфеля считается заново.' });

  const steps = ['открыть наш портфель', 'переключить бюджет на урезанный', 'заменить любой лот', 'увидеть, что именно сломалось', 'вернуть портфель обратно'];
  const cw = 2.29;
  steps.forEach((t, i) => {
    const x = L.M + i * (cw + 0.16);
    const last = i === steps.length - 1;
    card(s, { x, y: 2.0, w: cw, h: 1.5, fill: last ? C.mintDeep : C.card, line: last ? C.mintDeep : C.rule });
    s.addText(String(i + 1), { x: x + 0.2, y: 2.16, w: 0.5, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 12, bold: true, color: last ? C.ink : C.mint });
    s.addText(t, { x: x + 0.2, y: 2.54, w: cw - 0.4, h: 0.8, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, color: C.ink });
    if (!last) flow(s, { x: x + cw + 0.0, y: 2.66, d: 0.16 });
  });

  card(s, { x: L.M, y: 3.78, w: 8.3, h: 1.9, fill: C.card });
  s.addText('Что открыто вместе с инструментом', { x: L.M + 0.3, y: 3.98, w: 7.7, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 12.5, bold: true, color: C.ink });
  [
    ['управленческая записка и одностраничное резюме по стрессу', ICONS.file],
    ['расчётный движок, данные организаторов и выгрузка результатов', ICONS.dots],
    ['снимки всех экранов и сценарий показа на минуту', ICONS.clip],
  ].forEach(([t, ic], i) => {
    const y = 4.44 + i * 0.4;
    s.addImage({ data: ic, x: L.M + 0.3, y: y + 0.03, w: 0.22, h: 0.22 });
    s.addText(t, { x: L.M + 0.64, y, w: 7.4, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 11, color: C.ink2 });
  });

  card(s, { x: 9.14, y: 3.78, w: 3.57, h: 1.9, fill: C.card });
  s.addImage({ data: QR, x: 9.42, y: 4.0, w: 1.44, h: 1.44 });
  s.addText(SITE.replace('https://', ''), { x: 11.02, y: 4.34, w: 1.6, h: 0.3, isTextBox: true, margin: 0, fontFace: F, fontSize: 11.5, bold: true, color: C.mint });
  s.addText('или локально,\nодной командой', { x: 11.02, y: 4.66, w: 1.6, h: 0.5, isTextBox: true, margin: 0, fontFace: F, fontSize: 9.5, color: C.muted });

  s.addShape('roundRect', { x: L.M, y: 5.96, w: 12.09, h: 0.66, rectRadius: 0.1, fill: { color: C.mint }, line: { color: C.mint, width: 0 } });
  s.addText('Регион получает четыре работающих сервиса, понятные правила и запас на случай урезанного бюджета.', {
    x: L.M + 0.3, y: 5.96, w: 11.49, h: 0.66, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 13, bold: true, color: C.bg, valign: 'middle', align: 'center',
  });

  foot(s, { section: 'Показ', n: 12, total: TOTAL });
  s.addNotes(notes(12));
}

const out = path.join(HERE, 'kosmo-deck.pptx');
await pres.writeFile({ fileName: out });
console.log('готово:', out);
console.log(`слайдов ${TOTAL}, c0 ${m.c0}, польза ${m.vpub}, поступления ${m.cash}, запас ${c0Stress.margin}, допустимых ${admitted}, место ${rankRow.rank}`);
