// Шаблон «Космо · светлый»: белые карточки на светлом фоне, зелёные градиенты
// внутри данных. Собран нами по правилам презентационного шаблона КРОК
// (design.croc.ru/presentations): повторяющиеся элементы связывают слайды,
// слайд не перегружают, кегль крупный, текста мало, на слайде остаётся воздух,
// всё выровнено по одной сетке.
//
// Палитра — светлая тема интерфейса из app/static/styles.css.

export const C = {
  page: 'F4F7F5',   // фон слайда
  white: 'FFFFFF',  // карточка
  ink: '0E1F16',    // заголовки и цифры
  ink2: '3E5147',   // основной текст
  muted: '6B7C73',  // редкие подписи
  rule: 'E1E8E3',   // граница карточки
  deep: '0B4A2E',   // тёмная зелень
  brand: '0F6F40',  // акцент
  accent: '17A05C',
  mint: '55B894',
  soft: 'E8F4EC',   // светлая заливка
  brass: 'A9762B',  // запас и предупреждение
  crit: 'B1483C',   // нарушение
};

export const F = 'Montserrat';

// Сетка: 12 колонок, поля 0,72", межколонник 0,2".
export const L = { W: 13.333, H: 7.5, M: 0.72, gap: 0.22 };
L.CW = (L.W - 2 * L.M - 11 * 0.2) / 12;

export function defineLayout(pres) {
  pres.defineLayout({ name: 'KOSMO', width: L.W, height: L.H });
  pres.layout = 'KOSMO';
}

export const shadow = () => ({ type: 'outer', color: '0E1F16', blur: 14, offset: 3, angle: 90, opacity: 0.1 });

const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, fontFace: F, ...o });
export { T as text };

// Заголовок слайда: громкий, без надзаголовков и подводок.
export function head(slide, { title, size = 40 }) {
  T(slide, title, {
    x: L.M, y: 0.82, w: L.W - 2 * L.M, h: 0.86,
    fontSize: size, bold: true, color: C.ink,
  });
}

export function foot(slide, { n, total }) {
  T(slide, `${n} / ${total}`, {
    x: L.W - L.M - 1, y: 6.92, w: 1, h: 0.28,
    fontSize: 10, color: '9BAAA2', align: 'right',
  });
}

export function card(slide, { x, y, w, h, fill = C.white, line = C.rule, radius = 0.18 }) {
  slide.addShape('roundRect', {
    x, y, w, h, rectRadius: radius,
    fill: { color: fill }, line: { color: line, width: 1 }, shadow: shadow(),
  });
}

export function chip(slide, { x, y, w, h = 0.46, text, color = C.brand, border = 'C8E5D5', fill = C.white, size = 11.5, bold = true, align = 'center' }) {
  slide.addShape('roundRect', {
    x, y, w, h, rectRadius: 0.1,
    fill: { color: fill }, line: { color: border, width: 1 }, shadow: shadow(),
  });
  T(slide, text, { x: x + 0.14, y, w: w - 0.28, h, fontSize: size, bold, color, align, valign: 'middle' });
}

// Круглый значок с иконкой.
export function badge(slide, { x, y, d = 0.76, img, fill = C.soft, line = 'C8E5D5', pad = 0.19 }) {
  slide.addShape('ellipse', { x, y, w: d, h: d, fill: { color: fill }, line: { color: line, width: 1 } });
  if (img) slide.addImage({ data: img, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}

export function stat(slide, { x, y, w, value, label, size = 30, color = C.ink, align = 'left' }) {
  T(slide, value, { x, y, w, h: size / 58, fontSize: size, bold: true, color, align });
  T(slide, label, { x, y: y + size / 58 + 0.02, w, h: 0.26, fontSize: 10.5, color: C.ink2, align });
}

// Тонкая шкала «сколько до предела осталось».
export function meter(slide, { x, y, w, h = 0.12, frac, color = C.mint, track = 'E4EDE7' }) {
  slide.addShape('roundRect', { x, y, w, h, rectRadius: 0.06, fill: { color: track }, line: { color: track, width: 0 } });
  slide.addShape('roundRect', { x, y, w: Math.max(0.06, Math.min(1, frac) * w), h, rectRadius: 0.06, fill: { color }, line: { color, width: 0 } });
}

// Связка между блоками: нарисованный треугольник, а не символ стрелки.
export function flow(slide, { x, y, d = 0.18, color = C.mint, dir = 'right' }) {
  slide.addShape('triangle', {
    x, y, w: d, h: d, rotate: dir === 'right' ? 90 : 180,
    fill: { color }, line: { color, width: 0 },
  });
}
