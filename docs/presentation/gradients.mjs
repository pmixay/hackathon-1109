// Градиенты для слайдов: pptxgenjs заливок градиентом не умеет, поэтому
// градиент рисуется как SVG, растрируется sharp и вставляется картинкой.

import sharp from 'sharp';

const cache = new Map();

function svgLinear({ w, h, from, to, angle, mid }) {
  const rad = (angle * Math.PI) / 180;
  const x2 = (Math.cos(rad) * 0.5 + 0.5).toFixed(4);
  const y2 = (Math.sin(rad) * 0.5 + 0.5).toFixed(4);
  const x1 = (1 - x2).toFixed(4);
  const y1 = (1 - y2).toFixed(4);
  const stops = mid
    ? `<stop offset="0" stop-color="#${from}"/><stop offset="0.52" stop-color="#${mid}"/><stop offset="1" stop-color="#${to}"/>`
    : `<stop offset="0" stop-color="#${from}"/><stop offset="1" stop-color="#${to}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs><linearGradient id="g" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${stops}</linearGradient></defs>
    <rect width="${w}" height="${h}" fill="url(#g)"/></svg>`;
}

function svgRadial({ w, h, from, to, cx = 0.5, cy = 0.5, r = 0.75, fade = false, alpha = 1 }) {
  // fade: пятно уходит в прозрачность, а не в цвет. Так у картинки не видно
  // собственного края на любом фоне.
  const stops = fade
    ? `<stop offset="0" stop-color="#${from}" stop-opacity="${alpha}"/><stop offset="1" stop-color="#${from}" stop-opacity="0"/>`
    : `<stop offset="0" stop-color="#${from}"/><stop offset="1" stop-color="#${to}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">
    <defs><radialGradient id="g" cx="${cx}" cy="${cy}" r="${r}">${stops}</radialGradient></defs>
    <rect width="${w}" height="${h}" fill="url(#g)"/></svg>`;
}

async function raster(svg, key) {
  if (cache.has(key)) return cache.get(key);
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  const uri = 'image/png;base64,' + png.toString('base64');
  cache.set(key, uri);
  return uri;
}

// Линейный градиент. angle: 0 — слева направо, 90 — сверху вниз.
export function linear(opts) {
  const o = { w: 1600, h: 900, angle: 135, ...opts };
  return raster(svgLinear(o), `l:${JSON.stringify(o)}`);
}

// Радиальное пятно — мягкий акцент на светлом фоне.
export function radial(opts) {
  const o = { w: 1200, h: 1200, ...opts };
  return raster(svgRadial(o), `r:${JSON.stringify(o)}`);
}

// Скруглённая плашка с градиентом: рисуем сразу со скруглением, чтобы
// не подкладывать под картинку фигуру.
export async function pill(opts) {
  const o = { w: 800, h: 200, r: 40, angle: 0, ...opts };
  const rad = (o.angle * Math.PI) / 180;
  const x2 = (Math.cos(rad) * 0.5 + 0.5).toFixed(4);
  const y2 = (Math.sin(rad) * 0.5 + 0.5).toFixed(4);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${o.w}" height="${o.h}">
    <defs><linearGradient id="g" x1="${(1 - x2).toFixed(4)}" y1="${(1 - y2).toFixed(4)}" x2="${x2}" y2="${y2}">
      <stop offset="0" stop-color="#${o.from}"/><stop offset="1" stop-color="#${o.to}"/>
    </linearGradient></defs>
    <rect width="${o.w}" height="${o.h}" rx="${o.r}" ry="${o.r}" fill="url(#g)"/></svg>`;
  return raster(svg, `p:${JSON.stringify(o)}`);
}
