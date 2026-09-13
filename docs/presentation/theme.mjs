// Шаблон «Космо · тёмно-зелёный» — собственный шаблон команды.
//
// Основан на правилах презентационного шаблона КРОК (design.croc.ru/presentations):
// повторяющиеся элементы связывают слайды в одну презентацию; слайд не перегружают
// информацией; крупный кегль и минимум текста; воздух на слайде, второстепенное —
// в сноски и приложения; все элементы выровнены друг относительно друга.
// Палитра своя: тёмно-зелёная тема интерфейса `app/static/styles.css`.

export const C = {
  bg: '08130E',        // фон слайда
  bgSoft: '0B1A13',    // фон вспомогательных полос
  card: '0F1D17',      // карточка
  card2: '17271F',     // приподнятая карточка
  rule: '1E3228',      // линия/обводка
  ink: 'E6F2EB',       // основной текст
  ink2: 'A5BDB0',      // вторичный текст
  muted: '7E9689',     // подписи
  mint: '55B894',      // акцент бренда
  mintDeep: '2F7A5F',  // приглушённый акцент
  deep: '0F6F40',      // плотный зелёный
  brass: 'C39E53',     // запас и диагностика
  crit: 'CC7468',      // нарушение
  white: 'FFFFFF',
};

export const F = 'Montserrat';

// Сетка: 12 колонок, поля 0,62", межколонник 0,2".
export const L = {
  W: 13.333,
  H: 7.5,
  M: 0.62,             // боковое поле
  colGap: 0.2,
  bodyTop: 1.78,       // верх контентной области
  bodyBottom: 6.72,    // низ контентной области
  footY: 6.92,
};
L.CW = (L.W - 2 * L.M - 11 * L.colGap) / 12; // ширина колонки
export const col = (n) => n * L.CW + (n - 1) * L.colGap;      // ширина n колонок
export const colX = (i) => L.M + (i - 1) * (L.CW + L.colGap); // левый край колонки i

// Повторяющиеся элементы шаблона: кольца на фоне и подвал с линией.
const rings = [
  { shape: 'ellipse', x: 9.9, y: 3.5, w: 6.2, h: 6.2, line: { color: C.rule, width: 1 }, fill: { color: C.bg, transparency: 100 } },
  { shape: 'ellipse', x: 11.4, y: 5.0, w: 3.6, h: 3.6, line: { color: C.rule, width: 1 }, fill: { color: C.bg, transparency: 100 } },
];

export function defineMasters(pres) {
  pres.defineLayout({ name: 'KOSMO', width: L.W, height: L.H });
  pres.layout = 'KOSMO';

  pres.defineSlideMaster({
    title: 'COVER',
    background: { color: C.bg },
    objects: [
      { rect: { x: 0, y: 0, w: L.W, h: 0.14, fill: { color: C.mint } } },
      ...rings.map((r) => ({ [r.shape]: { x: r.x, y: r.y, w: r.w, h: r.h, line: r.line, fill: r.fill } })),
    ],
  });

  pres.defineSlideMaster({
    title: 'BASE',
    background: { color: C.bg },
    objects: [
      { rect: { x: 0, y: 0, w: 0.14, h: L.H, fill: { color: C.mint } } },
      ...rings.map((r) => ({ [r.shape]: { x: r.x, y: r.y, w: r.w, h: r.h, line: r.line, fill: r.fill } })),
      { rect: { x: L.M, y: L.footY, w: L.W - 2 * L.M, h: 0.012, fill: { color: C.rule } } },
    ],
  });
}

// ——— типовые элементы ———

export function head(slide, { kicker, title, lead }) {
  slide.addText(kicker.toUpperCase(), {
    x: L.M, y: 0.44, w: L.W - 2 * L.M, h: 0.26, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10.5, bold: true, charSpacing: 2.2, color: C.mint,
  });
  slide.addText(title, {
    x: L.M, y: 0.76, w: L.W - 2 * L.M - 0.6, h: 0.62, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 27, bold: true, color: C.ink, lineSpacingMultiple: 1.0,
  });
  if (lead) {
    slide.addText(lead, {
      x: L.M, y: 1.36, w: L.W - 2 * L.M - 2.4, h: 0.3, isTextBox: true, margin: 0,
      fontFace: F, fontSize: 12.5, color: C.ink2,
    });
  }
}

export function foot(slide, { section, n, total }) {
  slide.addText(section, {
    x: L.M, y: L.footY + 0.06, w: 7, h: 0.26, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9, color: C.muted,
  });
  slide.addText(`${n} / ${total}`, {
    x: L.W - L.M - 2, y: L.footY + 0.06, w: 2, h: 0.26, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 9, color: C.muted, align: 'right',
  });
}

export function card(slide, { x, y, w, h, fill = C.card, line = C.rule, radius = 0.1 }) {
  slide.addShape('roundRect', {
    x, y, w, h, rectRadius: radius,
    fill: { color: fill }, line: { color: line, width: 1 },
  });
}

export function chip(slide, { x, y, w, h = 0.42, text, color = C.ink2, border = C.rule, fill = C.card, size = 11, bold = false, align = 'center' }) {
  slide.addShape('roundRect', {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: border, width: 1 },
  });
  slide.addText(text, {
    x: x + 0.1, y, w: w - 0.2, h, isTextBox: true, margin: 0,
    fontFace: F, fontSize: size, bold, color, align, valign: 'middle',
  });
}

// Круглый значок с иконкой. `img` — data-URI PNG из assets.mjs.
export function badge(slide, { x, y, d = 0.78, img, fill = C.card2, line = C.mint, pad = 0.19 }) {
  slide.addShape('ellipse', { x, y, w: d, h: d, fill: { color: fill }, line: { color: line, width: 1 } });
  if (img) slide.addImage({ data: img, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}

// Крупное число с подписью — основной способ подать цифру.
export function stat(slide, { x, y, w, value, label, unit, size = 32, color = C.ink, align = 'left' }) {
  slide.addText(
    [
      { text: value, options: { fontSize: size, bold: true, color } },
      ...(unit ? [{ text: ' ' + unit, options: { fontSize: size * 0.42, bold: true, color: C.muted } }] : []),
    ],
    { x, y, w, h: size / 62, isTextBox: true, margin: 0, fontFace: F, align },
  );
  slide.addText(label, {
    x, y: y + size / 62 + 0.02, w, h: 0.24, isTextBox: true, margin: 0,
    fontFace: F, fontSize: 10, color: C.muted, align,
  });
}

// Тонкая шкала «факт против порога».
export function meter(slide, { x, y, w, h = 0.11, frac, color = C.mint, track = C.rule }) {
  slide.addShape('roundRect', { x, y, w, h, rectRadius: 0.05, fill: { color: track }, line: { color: track, width: 0 } });
  const fw = Math.max(0.06, Math.min(1, frac) * w);
  slide.addShape('roundRect', { x, y, w: fw, h, rectRadius: 0.05, fill: { color }, line: { color, width: 0 } });
}

// Связка между блоками: нарисованный треугольник, а не символ стрелки.
export function flow(slide, { x, y, d = 0.16, color = C.mint, dir = 'right' }) {
  slide.addShape('triangle', {
    x, y, w: d, h: d,
    rotate: dir === 'right' ? 90 : 180,
    fill: { color }, line: { color, width: 0 },
  });
}
