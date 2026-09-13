// Текст защиты отдельным документом: docs/presentation/speaker-notes.docx
//
//   node docs/presentation/notes.mjs
//
// Источник текста — script.mjs, тот же, что и заметки внутри презентации.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  BorderStyle, Table, TableRow, TableCell, WidthType, ShadingType, LevelFormat,
} from 'docx';
import { buildScript } from './script.mjs';
import { SCRIPT_CONTEXT } from './data.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SC = buildScript(SCRIPT_CONTEXT);
const total = SC.reduce((a, s) => a + s.seconds, 0);

const INK = '13251C';
const MUTED = '5C7267';
const GREEN = '0F6F40';

const p = (text, o = {}) => new Paragraph({
  spacing: { after: o.after ?? 120, line: 300 },
  alignment: o.align,
  children: [new TextRun({ text, font: 'Calibri', size: o.size ?? 22, bold: o.bold, italics: o.italics, color: o.color ?? INK })],
});

const rule = () => new Paragraph({
  spacing: { after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: 'D6E2DA' } },
  children: [],
});

function bullets(items, color) {
  return items.map((t) => new Paragraph({
    numbering: { reference: 'dots', level: 0 },
    spacing: { after: 60, line: 300 },
    children: [new TextRun({ text: t, font: 'Calibri', size: 21, color: color ?? INK })],
  }));
}

const body = [];

// Титул
body.push(new Paragraph({
  spacing: { after: 60 },
  children: [new TextRun({ text: 'КОСМОХАКАТОН 2026, КЕЙС 02', font: 'Calibri', size: 18, bold: true, color: GREEN, characterSpacing: 40 })],
}));
body.push(new Paragraph({
  spacing: { after: 80 },
  children: [new TextRun({ text: 'Космос как инфраструктура', font: 'Calibri', size: 44, bold: true, color: INK })],
}));
const mm = Math.floor(total / 60);
const ss = total % 60;
body.push(p(`Текст защиты к презентации kosmo-deck.pptx. Двенадцать слайдов, ${mm} минут ${ss} секунд без демонстрации инструмента.`, { color: MUTED, size: 21 }));
body.push(p('Команда «Молоток». Голубев Павел, Петр Кузнецов, Тимофей Максимов, Лихатин Андрей, Потапенко Филипп.', { color: MUTED, size: 21, after: 240 }));

// Хронометраж
body.push(new Paragraph({
  spacing: { before: 120, after: 120 },
  children: [new TextRun({ text: 'Хронометраж', font: 'Calibri', size: 26, bold: true, color: INK })],
}));
const W = [1000, 6600, 1400];
body.push(new Table({
  columnWidths: W,
  width: { size: W.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: [
    new TableRow({
      tableHeader: true,
      children: ['Слайд', 'О чём', 'Секунд'].map((t, i) => new TableCell({
        width: { size: W[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, fill: 'EAF2ED' },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: t, font: 'Calibri', size: 20, bold: true, color: INK })] })],
      })),
    }),
    ...SC.map((s) => new TableRow({
      children: [String(s.n), s.title, String(s.seconds)].map((t, i) => new TableCell({
        width: { size: W[i], type: WidthType.DXA },
        margins: { top: 70, bottom: 70, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: t, font: 'Calibri', size: 20, color: i === 1 ? INK : MUTED })] })],
      })),
    })),
    new TableRow({
      children: ['', 'Вместе', `${total}`].map((t, i) => new TableCell({
        width: { size: W[i], type: WidthType.DXA },
        margins: { top: 70, bottom: 70, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: t, font: 'Calibri', size: 20, bold: true, color: INK })] })],
      })),
    }),
  ],
}));

// Слайды
for (const s of SC) {
  body.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 40 },
    children: [new TextRun({ text: `Слайд ${s.n}. ${s.title}`, font: 'Calibri', size: 28, bold: true, color: INK })],
  }));
  body.push(new Paragraph({
    spacing: { after: 140 },
    children: [new TextRun({ text: `${s.section}, ${s.seconds} секунд`, font: 'Calibri', size: 19, color: MUTED })],
  }));
  for (const line of s.say) body.push(p(line));

  if (s.figures.length) {
    body.push(p('Цифры под рукой', { bold: true, size: 21, after: 60 }));
    body.push(...bullets(s.figures, MUTED));
  }
  if (s.questions.length) {
    body.push(p('Если спросят', { bold: true, size: 21, after: 60 }));
    for (const qa of s.questions) {
      body.push(new Paragraph({
        spacing: { after: 40, line: 300 },
        children: [new TextRun({ text: qa.q, font: 'Calibri', size: 21, italics: true, color: GREEN })],
      }));
      body.push(p(qa.a, { size: 21, after: 140 }));
    }
  }
  if (s.n < SC.length) body.push(rule());
}

// Общие правила показа
body.push(new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 360, after: 120 },
  children: [new TextRun({ text: 'Перед выступлением', font: 'Calibri', size: 28, bold: true, color: INK })],
}));
body.push(...bullets([
  'Инструмент открыт заранее, сценарий в шапке — обычный бюджет, на экране наш портфель.',
  'Если сеть недоступна, показываем снимки экранов из app/screenshots.',
  'Числа на слайдах и в инструменте совпадают: и то и другое берётся из results.',
  'Ни одну цифру организаторов мы не меняли, свои допущения помечаем словом «предположение».',
  'На вопрос, которого нет в этом тексте, отвечает участник, отвечающий за раздел, а не докладчик.',
]));

const doc = new Document({
  creator: 'Команда «Молоток»',
  title: 'Космос как инфраструктура. Текст защиты',
  numbering: {
    config: [{
      reference: 'dots',
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 380, hanging: 200 } } },
      }],
    }],
  },
  sections: [{
    properties: { page: { margin: { top: 1100, bottom: 1100, left: 1100, right: 1100 } } },
    children: body,
  }],
});

const out = path.join(HERE, 'speaker-notes.docx');
fs.writeFileSync(out, await Packer.toBuffer(doc));
console.log('готово:', out, `· слайдов ${SC.length}, ${total} секунд`);
