// Иконки и QR-код для слайдов: react-icons (Tabler) → SVG → PNG (sharp) → data-URI.
// Растр 256 px, цвет задаётся при генерации, поэтому иконка всегда контрастна фону.

import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import * as Tb from 'react-icons/tb';
import sharp from 'sharp';
import QRCode from 'qrcode';

const cache = new Map();

export async function icon(name, color = '55B894', px = 256) {
  const key = `${name}:${color}:${px}`;
  if (cache.has(key)) return cache.get(key);
  const Comp = Tb[name];
  if (!Comp) throw new Error(`нет иконки ${name}`);
  const svg = renderToStaticMarkup(
    React.createElement(Comp, { size: px, color: `#${color}`, strokeWidth: 1.7 }),
  );
  const png = await sharp(Buffer.from(svg)).resize(px, px).png().toBuffer();
  const uri = 'image/png;base64,' + png.toString('base64');
  cache.set(key, uri);
  return uri;
}

export async function qr(text, { fg = '55B894', bg = '0F1D17', px = 512 } = {}) {
  const buf = await QRCode.toBuffer(text, {
    type: 'png', width: px, margin: 1, errorCorrectionLevel: 'M',
    color: { dark: `#${fg}FF`, light: `#${bg}FF` },
  });
  return 'image/png;base64,' + buf.toString('base64');
}
