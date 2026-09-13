// Числа для презентации и текста защиты: читаются из results/ — единственного
// источника цифр проекта. Модуль общий для build.mjs и notes.mjs.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const R = (p) => path.join(ROOT, p);
export const SITE = 'https://cosmo.arbuz.lol';
export const TOTAL = 6;

const readJSON = (p) => JSON.parse(fs.readFileSync(R(p), 'utf8'));
function splitCSV(line) {
  const out = []; let cur = ''; let q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === ',' && !q) { out.push(cur); cur = ''; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}
function readCSV(p) {
  const rows = fs.readFileSync(R(p), 'utf8').trim().split(/\r?\n/);
  const hdr = splitCSV(rows[0]);
  return rows.slice(1).map((line) => Object.fromEntries(splitCSV(line).map((v, i) => [hdr[i], v])));
}

export const base = readJSON('results/base.json');
export const stress = readJSON('results/stress.json');
export const ranking = readCSV('results/ranking_full.csv');
export const alts = readCSV('results/alternatives.csv');
export const detail = readCSV('results/portfolio_detail.csv');

export const m = base.metrics;
export const checkOf = (src, code) => src.checks.find((c) => c.code === code);
export const c0Base = checkOf(base, 'c0_limit');
export const c0Stress = checkOf(stress, 'c0_limit');

export const FINAL_KEY = 'FIRE:A|AGRI:B|TRANS:B|ENV:A';
export const rankRow = ranking.find((r) => r.variant === FINAL_KEY);
export const leader = ranking.find((r) => r.rank === '1');
export const admitted = ranking.length;
export const ALL_COMBOS = 5670; // 4 лота из 8, каждый в одном из трёх режимов

export const altV7 = alts.find((r) => r.variant === 'V7' && r.scenario === 'BASE');
export const lotC0 = Object.fromEntries(detail.map((r) => [r.lot_id, Number(r.c0_mrub)]));
export const publicC0 = lotC0.FIRE + lotC0.ENV;
export const privateC0 = lotC0.AGRI + lotC0.TRANS;
export const dVpub = m.vpub - Number(altV7.vpub);

export const nf = (v, d = 0) => Number(v).toLocaleString('ru-RU', { minimumFractionDigits: d, maximumFractionDigits: d });
export const plus = (v, d = 1) => (v > 0 ? '+' : '−') + nf(Math.abs(v), d);

export const SCRIPT_CONTEXT = {
  c0: nf(m.c0), vpub: nf(m.vpub), cash: nf(m.cash, 1), opex: nf(m.opex),
  balance: nf(m.cash - m.opex, 1), kcash: nf(m.kcash, 2), anchorKcash: nf(m.anchor_kcash, 3),
  margin: nf(c0Stress.margin), stressLimit: nf(c0Stress.threshold), baseLimit: nf(c0Base.threshold),
  admitted, rank: rankRow.rank, allCombos: nf(ALL_COMBOS), dVpub: nf(dVpub),
  publicC0: nf(publicC0), privateC0: nf(privateC0), site: SITE.replace('https://', ''),
};
