// Космо-портфель — интерфейс расчётного инструмента Кейса 02.
// Единственный вход данных: dashboard.json (контракт в app/CONTRACT.md).
// Здесь нет расчётной модели: только отображение и производные для него
// (отличия комбинаций, проценты от порога, графики).

import { renderData, mountData } from './data.js';

const $ = (sel, root = document) => root.querySelector(sel);

// [ключ, заголовок, иконка, заголовок группы в боковой панели (если начинает группу)]
const PAGES = [
  ['portfolio', 'Портфель', '<rect x="2" y="2" width="5" height="5" rx="1"></rect><rect x="9" y="2" width="5" height="5" rx="1"></rect><rect x="2" y="9" width="5" height="5" rx="1"></rect><rect x="9" y="9" width="5" height="5" rx="1"></rect>', 'Расчёт'],
  ['compare', 'Сравнение', '<path d="M2 13h12M4 11V6M8 11V3M12 11V8"></path>'],
  ['stress', 'Стресс', '<path d="M8 2v6l4 2"></path><circle cx="8" cy="8" r="6"></circle>'],
  ['data', 'Данные', '<ellipse cx="8" cy="4" rx="5" ry="2"></ellipse><path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4M3 8c0 1.1 2.2 2 5 2s5-.9 5-2"></path>', 'Источник'],
];
// вкладки внутри страниц; первая — по умолчанию
const TABS = {
  portfolio: [['overview', 'Обзор'], ['combos', 'Комбинации'], ['checks', 'Ограничения'], ['lots', 'Лоты и сервисы']],
  compare: [['charts', 'Графики'], ['table', 'Таблица']],
  stress: [['margins', 'Запасы'], ['actions', 'Действия']],
  data: [['current', 'Текущий набор'], ['upload', 'Загрузка'], ['format', 'Формат']],
};
const SCENARIO_NOTE = { BASE: 'базовый бюджет', STRESS: 'сокращённый бюджет' };

const CHECK = {
  exact_lot_count: 'Лотов',
  territorial_archetypes: 'Территориальных архетипов',
  capability_groups: 'Групп возможностей',
  public_core_lots: 'Лотов с public core',
  c0_limit: 'Стартовые затраты c0',
  opex_limit: 'OPEX в год',
  vpub_floor: 'Общественная ценность',
  kcash_floor: 'Покрытие OPEX',
  t_rep_floor: 'Воспроизводимость t_rep',
};
const COMPOSITION = ['exact_lot_count', 'territorial_archetypes', 'capability_groups', 'public_core_lots'];
const THRESHOLDS = ['c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor'];
const DEC = { exact_lot_count: 0, territorial_archetypes: 0, capability_groups: 0, public_core_lots: 0, c0_limit: 1, opex_limit: 1, vpub_floor: 1, kcash_floor: 3, t_rep_floor: 3 };
const THR_DEC = { c0_limit: 0, opex_limit: 0, vpub_floor: 0, kcash_floor: 2, t_rep_floor: 2 };
const OP = { '<=': '≤', '>=': '≥', '=': '=' };

const ICON = {
  check: '<svg viewBox="0 0 16 16" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3L13 4.5"></path></svg>',
  x: '<svg viewBox="0 0 16 16" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4l8 8M12 4l-8 8"></path></svg>',
  tick: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3L13 4.5"></path></svg>',
  chev: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"></path></svg>',
  arrow: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h10M9 4l4 4-4 4"></path></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"></path></svg>',
};

// ---------- утилиты ----------
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (v, d = 1) => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const s = Math.abs(v).toFixed(d);
  const [int, frac] = s.split('.');
  const grouped = int.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return (v < 0 ? '−' : '') + grouped + (frac ? '.' + frac : '');
};
const signed = (v, d = 1) => (v > 0 ? '+' : v < 0 ? '−' : '') + fmt(Math.abs(v), d);
const pct = (x) => Math.round(x * 100) + ' %';
const modesOf = (c) => c.selection.map((s) => s.mode).join('');
const lotsOf = (c) => c.selection.map((s) => s.lot).join(' · ');
const help = (text, open = false) => `<span class="help${open ? ' open' : ''}"><i>?</i><div class="pop">${text}</div></span>`;
const tag = (t) => `<span class="tag">${esc(t)}</span>`;
const more = (tab, label) => `<a class="more" data-tab="${tab}">${label} ${ICON.arrow}</a>`;

// ---------- состояние ----------
const state = {
  data: null,
  api: true,
  page: 'portfolio',
  tab: {},
  scenario: 'BASE',
  selected: null,
  collapsed: localStorage.getItem('kp.collapsed') === '1',
  theme: document.documentElement.dataset.theme || 'light',
  dataset: null,
};
const curTab = (page = state.page) => state.tab[page] || TABS[page][0][0];
function parseHash() {
  const [p, t] = location.hash.replace('#', '').split('/');
  if (!PAGES.some(([k]) => k === p)) return false;
  state.page = p;
  if (t && TABS[p].some(([k]) => k === t)) state.tab[p] = t;
  return true;
}
const hashOf = () => `${state.page}/${curTab()}`;

async function loadDashboard(selected) {
  const q = selected ? `?selected=${encodeURIComponent(selected)}` : '';
  try {
    const r = await fetch(`/api/dashboard${q}`, { cache: 'no-store' });
    if (!r.ok) throw new Error(await r.text());
    state.api = true;
    return await r.json();
  } catch (e) {
    state.api = false;
    const r = await fetch('data/dashboard.json', { cache: 'no-store' });
    return await r.json();
  }
}

// ---------- производные ----------
const combo = (id) => state.data.combinations[id];
const sel = () => combo(state.selected);

function marks(base, other) {
  // чипы лотов other с пометками: swap — лот заменён, chg — другой режим
  const b = Object.fromEntries(base.selection.map((s) => [s.lot, s.mode]));
  return other.selection.map((s) => ({ lot: s.lot, mode: s.mode, swap: !(s.lot in b), chg: s.lot in b && b[s.lot] !== s.mode }));
}
function describeChange(base, other) {
  const b = Object.fromEntries(base.selection.map((s) => [s.lot, s.mode]));
  const o = Object.fromEntries(other.selection.map((s) => [s.lot, s.mode]));
  const removed = Object.keys(b).filter((l) => !(l in o));
  const added = Object.keys(o).filter((l) => !(l in b));
  const parts = added.map((a, i) => `${a} вместо ${removed[i] ?? '—'}`);
  const byMode = {};
  for (const l of Object.keys(o)) if (l in b && b[l] !== o[l]) (byMode[o[l]] ||= []).push(l);
  for (const [m, ls] of Object.entries(byMode)) parts.push(`${ls.join(', ')} → ${m}`);
  return parts.join(' · ') || 'без изменений';
}
const chips = (c, base = null) => {
  const ms = base ? marks(base, c) : c.selection.map((s) => ({ ...s }));
  return `<span class="lots">${ms.map((m) => `<span class="lot${m.swap ? ' swap' : ''}">${m.lot}<b${m.chg ? ' class="chg"' : ''}>${m.mode}</b></span>`).join('')}</span>`;
};
const checksOf = (c, scenario) => c.checks[scenario];
const gatesOf = (c) => c.gates || [];
const gateName = (g) => (g.label || g.id).replace(/^S2:\s*/, '');
const gateChip = (c) => gatesOf(c).map((g) => stChip(g.ok, `${g.ok ? 'PASS' : 'FAIL'} · ${fmt(g.fact, 2)}`)).join(' ');
const gateHead = (d) => (d.meta.gates || []).map((g) => `<th>S2 ${OP[g.op]} ${fmt(g.threshold, 2)}</th>`).join('');
const gateCells = (c) => gatesOf(c).map((g) => `<td>${stChip(g.ok, `${g.ok ? 'PASS' : 'FAIL'} · ${fmt(g.fact, 2)}`)}</td>`).join('');
const gateHelp = (d) => (d.meta.gates || []).map((g) => ` Проверка команды S2 (не канон кейса): ${esc(g.label)} — ${g.metric} ${OP[g.op]} ${fmt(g.threshold, 2)}. ${esc(g.rationale)} Комбинации, не прошедшие S2, в ранжировании не участвуют и показаны серым.`).join('');
const stChip = (ok, label) => `<span class="st ${ok ? 'ok' : 'fail'}">${label}</span>`;

// ---------- шапка, навигация, вкладки ----------
function renderChrome() {
  const d = state.data;
  $('#nav').innerHTML = PAGES.map(([k, t, ic, grp]) => (grp ? `<div class="grp">${grp}</div>` : '') + `<a data-page="${k}" class="${k === state.page ? 'on' : ''}"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${ic}</svg><span>${t}</span></a>`).join('');
  const sc = d.meta.scenarios;
  if (!(state.scenario in sc)) state.scenario = Object.keys(sc)[0];
  $('#scenario').innerHTML = `<button class="dd-btn" type="button" title="Сценарий бюджета"><span class="k">Сценарий</span><b>${esc(state.scenario)}</b>${ICON.chev}</button>
<div class="dd-pop">${Object.keys(sc).map((s) => `<div class="dd-it${s === state.scenario ? ' on' : ''}" data-s="${esc(s)}"><span class="ck">${ICON.tick}</span><div><b>${esc(s)}</b><span>${SCENARIO_NOTE[s] || 'сценарий кейса'}</span></div></div>`).join('')}</div>`;
  $('#theme').innerHTML = `<button type="button" data-theme="light" class="${state.theme === 'light' ? 'on' : ''}" title="Светлая тема">${ICON.sun}</button><button type="button" data-theme="dark" class="${state.theme === 'dark' ? 'on' : ''}" title="Тёмная тема">${ICON.moon}</button>`;
  const src = d.meta.dataset ? (d.meta.dataset.source === 'организаторы' ? '' : ' · загружено') : '';
  $('#ver').textContent = `данные v${d.meta.case_version}${src}${state.api ? '' : ' · статический файл'}`;
  $('#shell').classList.toggle('collapsed', state.collapsed);
}
const tabsHtml = (page) => `<nav class="tabs">${TABS[page].map(([k, t]) => `<a data-tab="${k}" class="${k === curTab(page) ? 'on' : ''}">${t}</a>`).join('')}</nav>`;
const pageHead = (title, pill, page = state.page) => `<div class="top"><h1>${title}</h1>${pill}</div>${tabsHtml(page)}`;

// ---------- страница «Портфель» ----------
function renderPortfolio() {
  const d = state.data, s = sel(), sc = state.scenario;
  const checks = checksOf(s, sc);
  const ok = checks.filter((r) => r.ok).length;
  const failing = checks.filter((r) => !r.ok);
  const gates = gatesOf(s), gatesBad = gates.filter((g) => !g.ok);
  const gateTxt = gatesBad.length ? ` · S2 не пройден: ${gatesBad.map((g) => `${gateName(g)} ${fmt(g.fact, 2)} ${g.op === '<=' ? '>' : '<'} ${fmt(g.threshold, 2)}`).join(', ')}` : gates.length ? ' · S2 пройден' : '';
  const pill = failing.length || gatesBad.length
    ? `<div class="pill bad"><span class="dot">${ICON.x}</span>${ok} из ${checks.length}${failing.length ? ' · нарушено: ' + failing.map((r) => `${CHECK[r.id]} ${fmt(r.fact, DEC[r.id])} ${r.op === '<=' ? '>' : '<'} ${fmt(r.threshold, THR_DEC[r.id] ?? 0)}`).join(', ') : ''}${gateTxt}</div>`
    : `<div class="pill"><span class="dot">${ICON.check}</span>${ok} из ${checks.length} ограничений выполнены${gateTxt}</div>`;
  const t = d.meta.totals, w = d.meta.weights, m = s.metrics, cons = d.meta.constraints, c0max = d.meta.scenarios[sc].c0_max;
  const weightsTxt = `ценность ${w.vpub}, c0 ${w.c0}, cash / OPEX ${w.kcash}, готовность ${w.readiness}, устойчивость ${w.resilience}, тираж ${w.scale}, запас по STRESS ${w.stress_margin}`;
  const helpChecks = `Девять проверок <b>check_constraints</b>. Состав: ровно ${cons.selected_lots_exactly} лота, ≥ ${cons.min_territorial_archetypes} территориальных архетипа среди нефедеральных, ≥ ${cons.min_capability_groups} группы возможностей, ≥ ${cons.min_public_core_lots} лота с public core. Пороги: c0 ≤ ${fmt(d.meta.scenarios.BASE.c0_max, 0)} в BASE и ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)} в STRESS, OPEX ≤ ${cons.opex_max_mrub_per_year} млн руб./год, ценность ≥ ${fmt(cons.vpub_min_mrub_per_year, 0)}, cash / OPEX ≥ ${cons.kcash_min.toFixed(2)}, воспроизводимость t_rep (среднее по лотам) ≥ ${cons.t_rep_min}. Границы включительно. Сценарий в шапке меняет лимит c0.${gateHelp(d)}`;

  const body = {
    overview() {
      const helpHero = `Выбранный портфель — решение гейта из <b>config/portfolio.json</b>: четыре лота, у каждого режим доступа (буква в чипе; public core — режим с общественным ядром). В карточке лота — название из карточки сервиса, регион и архетип, стартовые затраты c0 лота с учётом режима. Место — среди ${t.ranked} комбинаций, допустимых в STRESS${d.meta.gates?.length ? ' и прошедших проверку команды S2' : ''}, по баллу модели выбора (0–1; веса: ${weightsTxt}). Другую комбинацию можно выбрать на вкладке «Комбинации».`;
      const lotCards = s.per_lot.map((r) => {
        const L = d.lots[r.lot];
        return `<div class="hl-lot"><div class="hl-h"><span class="hl-code">${r.lot}</span><span class="mode">${r.mode}${r.public_core ? ' · public core' : ''}</span></div><div class="hl-name">${esc(L.name)}</div><div class="hl-sub">${esc(L.region)} · ${esc(L.archetype)} архетип</div><div class="hl-c0">${fmt(r.c0)}<small>c0, млн руб.</small></div></div>`;
      }).join('');
      const score = `<div class="hl-score"><div class="k">Место по баллу</div><div class="v">${s.rank ?? '—'}<small>из ${t.ranked}</small></div><div class="s">балл модели <b>${s.score.toFixed(2)}</b></div>${more('combos', 'Все комбинации')}</div>`;
      const helpTiles = `Показатели выбранной комбинации в сценарии ${sc}. Тёмная часть полосы — использовано или порог, светлая — запас или превышение порога. c0 и OPEX — млн руб.; общественная ценность — усл. млн руб./год (синтетическая шкала кейса, не деньги); покрытие OPEX — поступления cash за год, делённые на OPEX. Запас по c0 — расстояние до лимита в каждом сценарии; отрицательный — лимит превышен.`;
      const tile = (title, val, unit, reqW, lblA, lblB) => `<div class="tile"><div class="tl">${title}</div><div class="tv">${val}<small>${unit}</small></div><div class="seg"><i class="req" style="width:${(reqW * 100).toFixed(1)}%"></i><i class="sur" style="width:${((1 - reqW) * 100).toFixed(1)}%"></i></div><div class="seglbl"><span><i class="sw" style="background:var(--seg-a)"></i>${lblA}</span><span><i class="sw" style="background:var(--seg-b)"></i>${lblB}</span></div></div>`;
      const mB = d.meta.scenarios.BASE.c0_max - m.c0, mS = d.meta.scenarios.STRESS.c0_max - m.c0;
      const tiles = `<div class="tiles">
${tile('Стартовые затраты c0', fmt(m.c0), 'млн руб.', Math.min(1, m.c0 / c0max), 'использовано ' + fmt(m.c0), (c0max - m.c0 >= 0 ? 'запас ' : 'превышение ') + fmt(Math.abs(c0max - m.c0)))}
${tile('OPEX в год', fmt(m.opex), 'млн руб.', Math.min(1, m.opex / cons.opex_max_mrub_per_year), 'использовано ' + fmt(m.opex), 'запас ' + fmt(cons.opex_max_mrub_per_year - m.opex))}
${tile('Общественная ценность', fmt(m.vpub, 0), 'усл. млн руб.', Math.min(1, cons.vpub_min_mrub_per_year / m.vpub), 'порог ' + fmt(cons.vpub_min_mrub_per_year, 0), 'сверх ' + signed(m.vpub - cons.vpub_min_mrub_per_year, 0))}
${tile('Покрытие OPEX', fmt(m.kcash, 2), 'cash / OPEX', Math.min(1, cons.kcash_min / m.kcash), 'порог ' + fmt(cons.kcash_min, 2), 'сверх ' + signed(m.kcash - cons.kcash_min, 2))}
<div class="tile"><div class="tl">Запас по c0${help(helpTiles)}</div><div class="two"><div><span>BASE</span><b class="${mB < 0 ? 'neg' : ''}">${fmt(mB)}</b></div><div><span>STRESS</span><b class="${mS < 0 ? 'neg' : ''}">${fmt(mS)}</b></div></div></div>
</div>`;
      const grp = (title, ids) => {
        const rs = checks.filter((r) => ids.includes(r.id)), okN = rs.filter((r) => r.ok).length, all = okN === rs.length;
        return `<div class="sum-it"><div class="sum-h"><span class="circ${all ? '' : ' bad'}">${all ? ICON.check : ICON.x}</span><span class="t">${title}</span><span class="n">${okN} из ${rs.length}</span></div><div class="sum-l">${rs.map((r) => `<span class="${r.ok ? '' : 'bad'}"><i></i>${CHECK[r.id]}</span>`).join('')}</div></div>`;
      };
      const grpGates = () => {
        if (!gates.length) return '';
        const all = gatesBad.length === 0;
        return `<div class="sum-it"><div class="sum-h"><span class="circ${all ? '' : ' bad'}">${all ? ICON.check : ICON.x}</span><span class="t">Проверка команды S2</span><span class="n">${gates.length - gatesBad.length} из ${gates.length}</span></div><div class="sum-l">${gates.map((g) => `<span class="${g.ok ? '' : 'bad'}"><i></i>${esc(gateName(g))}</span>`).join('')}</div></div>`;
      };
      return `<div class="card"><h2>Выбранная комбинация${help(helpHero)}</h2><div class="hero">${lotCards}${score}</div></div>
${tiles}
<div class="card"><h2>Ограничения ${tag(sc)}${more('checks', 'Факт и пороги')}${help(helpChecks)}</h2><div class="sum">${grp('Состав портфеля', COMPOSITION)}${grp('Финансовые и качественные пороги', THRESHOLDS)}${grpGates()}</div></div>`;
    },
    combos() {
      const helpSug = `Инструмент перебирает все ${fmt(t.combinations, 0)} комбинаций «4 лота × режимы» через канонический <b>case_core.py</b>, оставляет ${t.stress_feasible} допустимых в STRESS${d.meta.gates?.length ? `, из них ${t.ranked} проходят проверку команды S2,` : ''} и ранжирует их моделью выбора команды: min–max нормализация по допущенным вариантам, веса — ${weightsTxt}. Портфель не собирается вручную по лотам: выбирается одна из предложенных комбинаций (клик по строке), отличия показаны относительно выбранной: жёлтый лот — замена, жёлтая буква — другой режим. Выбранная комбинация — ${s.rank ?? '—'}-я из ${t.ranked} по баллу. Серые строки не предлагаются: лучшая по баллу комбинация, не прошедшая S2, и максимум ценности среди проходящих BASE, но не STRESS.${gateHelp(d)}`;
      const rows = [...d.suggestions, ...d.rejected.filter((id) => !d.suggestions.includes(id))].map((id) => {
        const c = combo(id), isSel = id === state.selected, dim = !c.admitted;
        const why = isSel ? 'выбрана' : describeChange(s, c) + (!c.ok.STRESS ? ' · не проходит STRESS' : dim ? ' · не проходит S2' : '');
        return `<tr class="pick${isSel ? ' hl' : ''}${dim ? ' dim' : ''}" data-id="${esc(id)}"><td><span class="radio${isSel ? ' on' : ''}"></span></td><td>${chips(c, s)}</td><td class="why">${esc(why)}</td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td class="num">${fmt(c.metrics.kcash, 2)}</td><td>${stChip(c.ok.BASE, c.ok.BASE ? 'PASS' : 'FAIL')}</td><td>${stChip(c.ok.STRESS, c.ok.STRESS ? 'PASS' : 'FAIL · ' + (checksOf(c, 'STRESS').find((r) => !r.ok)?.id === 'c0_limit' ? 'c0' : 'см. стресс'))}</td>${gateCells(c)}<td class="num">${isSel ? '<b>' + c.score.toFixed(2) + '</b>' : c.score.toFixed(2)}</td></tr>`;
      }).join('');
      return `<div class="card"><h2>Предложенные комбинации${help(helpSug)}</h2>
<table><tr><th></th><th>Состав и режимы</th><th>Отличие от выбранной</th><th class="num">c0</th><th class="num">Ценность</th><th class="num">Cash / OPEX</th><th>BASE</th><th>STRESS</th>${gateHead(d)}<th class="num">Балл</th></tr>${rows}</table></div>`;
    },
    checks() {
      const jr = (r) => {
        const ratio = r.threshold ? r.fact / r.threshold : 1;
        const bar = r.op === '<=' ? Math.min(1, ratio) : 1;
        return `<div class="jr${r.ok ? '' : ' bad'}"><span class="circ">${r.ok ? ICON.check : ICON.x}</span><div>${CHECK[r.id]}</div><div class="m"><b>${fmt(r.fact, DEC[r.id])}</b> ${OP[r.op]} ${fmt(r.threshold, THR_DEC[r.id] ?? 0)}</div><div><div class="mbar"><i style="width:${(bar * 100).toFixed(1)}%"></i></div><div class="mtxt">${r.ok ? pct(ratio) : 'нарушено'}</div></div></div>`;
      };
      const group = (title, ids) => {
        const rs = checks.filter((r) => ids.includes(r.id)), okN = rs.filter((r) => r.ok).length;
        return `<div class="jobs"><div class="jh${okN === rs.length ? '' : ' bad'}"><span class="circ">${okN === rs.length ? ICON.check : ICON.x}</span>${title}<span class="cnt">${okN} из ${rs.length}</span></div>${rs.map(jr).join('')}</div>`;
      };
      const jg = (g) => {
        const ratio = g.threshold ? g.fact / g.threshold : 1;
        return `<div class="jr${g.ok ? '' : ' bad'}"><span class="circ">${g.ok ? ICON.check : ICON.x}</span><div>${esc(gateName(g))}</div><div class="m"><b>${fmt(g.fact, 3)}</b> ${OP[g.op]} ${fmt(g.threshold, 2)}</div><div><div class="mbar"><i style="width:${(Math.min(1, ratio) * 100).toFixed(1)}%"></i></div><div class="mtxt">${g.ok ? pct(ratio) : 'нарушено'}</div></div></div>`;
      };
      const groupGates = () => gates.length ? `<div class="jobs"><div class="jh${gatesBad.length ? ' bad' : ''}"><span class="circ">${gatesBad.length ? ICON.x : ICON.check}</span>Проверка команды S2 — стресс спроса<span class="cnt">${gates.length - gatesBad.length} из ${gates.length}</span></div>${gates.map(jg).join('')}</div>` : '';
      return `<div class="card"><h2>Проверка ограничений ${tag(sc)}${help(helpChecks + ' Процент справа — факт в долях порога: для «≤» ниже 100 % значит внутри лимита, для «≥» выше 100 % значит порог перекрыт.')}</h2><div class="jobs2">${group('Состав портфеля', COMPOSITION)}${group('Финансовые и качественные пороги', THRESHOLDS)}${groupGates()}</div></div>`;
    },
    lots() {
      const lotRow = (r) => {
        const L = d.lots[r.lot];
        return `<tr><td><div class="name"><span class="code">${r.lot}</span> · ${esc(L.name)}</div><div class="sub">${esc(L.archetype)} архетип · ${L.groups.join(', ')}</div></td><td><span class="mode">${r.mode}${r.public_core ? ' · public core' : ''}</span></td><td class="num">${fmt(r.c0)}</td><td class="num">${fmt(r.opex, 2)}</td><td class="num">${fmt(r.vpub)}</td><td class="num">${fmt(r.cash, 2)}</td><td class="num">${fmt(r.t_rep, 2)}</td><td class="num">${fmt(r.readiness, 1)}</td><td class="num">${fmt(r.resilience, 1)}</td><td class="num">${fmt(r.scale, 1)}</td></tr>`;
      };
      const modesTxt = Object.entries(d.modes).map(([k, v]) => `<b>Режим ${k}:</b> k_c0 ${v.k_c0}, k_opex ${v.k_opex}, ценность ×${v.k_vpub}, якорные ×${v.k_anchor}, коммерческие ×${v.k_commercial}${v.public_core ? ', public core' : ''}`).join('. ');
      const helpLots = `c0, OPEX и cash — млн руб.; ценность — усл. млн руб./год; готовность, устойчивость и тираж — индексы 1–5 из <b>lots.csv</b>. Значения после применения режима: c0 и OPEX умножены на k_c0 и k_opex, ценность — на k_vpub, поступления = якорные × k_anchor + коммерческие × k_commercial. ${modesTxt}. t_rep — показатель воспроизводимости лота (коэффициент масштабируемости решения). В строке «Портфель» — суммы; для t_rep и индексов — средние.`;
      // карточки сервисов: название для интерфейса и тексты из config/lots_ui.csv (файл участника записки)
      const svcCard = (r) => {
        const L = d.lots[r.lot], c = L.card;
        const head = `<div class="sv-h"><div class="name"><span class="code">${r.lot}</span> · ${esc(L.name)}</div><span class="mode">${r.mode}${r.public_core ? ' · public core' : ''}</span></div>`;
        if (!c) return `<div class="sv">${head}<div class="sv-r">${esc(L.region)}</div><p class="muted">Карточка сервиса не подготовлена</p></div>`;
        const sameMode = !c.mode || c.mode === r.mode;
        const row = (k, v) => (v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : '');
        const access = sameMode ? row('Базовый доступ', c.access_base) + row('Дополнительно', c.access_extra) : `<dt>Доступ</dt><dd class="muted">описан для режима ${esc(c.mode)}, в комбинации — ${r.mode}</dd>`;
        return `<div class="sv">${head}<div class="sv-r">${esc(L.region)}${c.user ? ' · ' + esc(c.user) : ''}</div><p>${esc(c.description)}</p><dl>${access}${row('KPI', c.kpi)}${row('При сбое', c.on_failure)}</dl></div>`;
      };
      const helpSvc = `Что получает пользователь каждого лота. Карточки сервисов из <b>config/lots_ui.csv</b> — файла участника записки (формат «участник 5»: название для интерфейса, короткое описание, основной пользователь, базовый и дополнительный доступ, главный KPI, что показать при сбое). Название лота берётся отсюда же, поэтому в интерфейсе и записке оно одно. Правила доступа описаны для режима из карточки; если в выбранной комбинации режим другой, строки доступа не показываются. Плательщик, оператор, приёмка и риски — в полных карточках записки, в инструменте не дублируются.`;
      return `<div class="card"><h2>Лоты портфеля${help(helpLots)}</h2>
<table><tr><th>Лот</th><th>Режим</th><th class="num">c0</th><th class="num">OPEX</th><th class="num">Ценность</th><th class="num">Cash</th><th class="num">t_rep</th><th class="num">Готовность</th><th class="num">Устойчивость</th><th class="num">Тираж</th></tr>
${s.per_lot.map(lotRow).join('')}
<tr class="total"><td>Портфель</td><td></td><td class="num">${fmt(m.c0)}</td><td class="num">${fmt(m.opex, 2)}</td><td class="num">${fmt(m.vpub)}</td><td class="num">${fmt(m.cash, 2)}</td><td class="num">${fmt(m.t_rep, 3)}</td><td class="num">${fmt(m.readiness, 2)}</td><td class="num">${fmt(m.resilience, 2)}</td><td class="num">${fmt(m.scale, 2)}</td></tr></table></div>
<div class="card"><h2>Сервисы портфеля${help(helpSvc)}</h2><div class="svc">${s.per_lot.map(svcCard).join('')}</div></div>`;
    },
  };
  return pageHead('Портфель', pill) + body[curTab('portfolio')]();
}

// ---------- страница «Сравнение» ----------
function barChart(items) {
  const n = items.length, W = 560, x0 = 52, x1 = 550, top = 30, base = 190;
  const maxV = Math.max(2000, ...items.map((c) => c.metrics.vpub));
  const scaleY = (base - top) / maxV;
  const step = (x1 - x0) / n, bw = Math.min(28, step * 0.34);
  const ticks = [0, 500, 1000, 1500, 2000].filter((v) => v <= maxV);
  let g = ticks.filter((v) => v).map((v) => `<line class="grid" x1="${x0}" x2="${x1}" y1="${(base - v * scaleY).toFixed(1)}" y2="${(base - v * scaleY).toFixed(1)}"></line>`).join('');
  g += ticks.map((v) => `<text class="n" x="${x0 - 8}" y="${(base - v * scaleY + 4).toFixed(1)}" text-anchor="end">${v}</text>`).join('');
  const floor = state.data.meta.constraints.vpub_min_mrub_per_year;
  g += `<line x1="${x0}" x2="${x1}" y1="${(base - floor * scaleY).toFixed(1)}" y2="${(base - floor * scaleY).toFixed(1)}" style="stroke:var(--crit)" stroke-dasharray="4 3" stroke-width="1.5"></line>`;
  items.forEach((c, i) => {
    const cx = x0 + step * (i + 0.5);
    const hv = c.metrics.vpub * scaleY, hc = c.metrics.cash * scaleY;
    g += `<rect x="${(cx - bw - 2).toFixed(1)}" y="${(base - hv).toFixed(1)}" width="${bw}" height="${hv.toFixed(1)}" rx="3" style="fill:var(--s1)"></rect><rect x="${(cx + 2).toFixed(1)}" y="${(base - hc).toFixed(1)}" width="${bw}" height="${hc.toFixed(1)}" rx="3" style="fill:var(--s2)"></rect>`;
    g += `<text class="n t" x="${(cx - bw / 2 - 2).toFixed(1)}" y="${(base - hv - 6).toFixed(1)}" text-anchor="middle">${fmt(c.metrics.vpub, 0)}</text>`;
    const lots = c.selection.map((s) => s.lot);
    g += `<g class="xl"><text x="${cx.toFixed(1)}" y="204" text-anchor="middle">${lots.slice(0, 2).join(' · ')}</text><text x="${cx.toFixed(1)}" y="215" text-anchor="middle">${lots.slice(2).join(' · ')}</text></g><g class="xm"><text x="${cx.toFixed(1)}" y="228" text-anchor="middle">${modesOf(c)}</text></g>`;
  });
  return `<svg viewBox="0 0 ${W} 244" width="100%" role="img" aria-label="Общественная ценность и поступления"><line class="axis" x1="${x0}" x2="${x1}" y1="${base}" y2="${base}"></line>${g}</svg>
<div class="legend"><span><i style="background:var(--s1)"></i>Общественная ценность</span><span><i style="background:var(--s2)"></i>Поступления cash</span><span><i class="line"></i>порог ${fmt(floor, 0)}</span></div>`;
}
function c0Chart(items) {
  const sc = state.data.meta.scenarios, lo0 = sc.STRESS.c0_max, hi0 = sc.BASE.c0_max;
  const vals = items.map((c) => c.metrics.c0);
  const dmin = Math.min(1100, Math.floor((Math.min(...vals) - 10) / 50) * 50), dmax = Math.max(1300, Math.ceil((Math.max(...vals) + 10) / 50) * 50);
  const x0 = 210, x1 = 540, k = (x1 - x0) / (dmax - dmin), X = (v) => x0 + (v - dmin) * k;
  const top = 40, rowH = 24, base = top + rowH * items.length + 8;
  let g = `<rect x="${x0}" y="${top}" width="${(X(lo0) - x0).toFixed(1)}" height="${base - top}" style="fill:var(--good-soft)"></rect><rect x="${X(lo0).toFixed(1)}" y="${top}" width="${(X(hi0) - X(lo0)).toFixed(1)}" height="${base - top}" style="fill:var(--warn-soft)"></rect>`;
  if (X(hi0) < x1) g += `<rect x="${X(hi0).toFixed(1)}" y="${top}" width="${(x1 - X(hi0)).toFixed(1)}" height="${base - top}" style="fill:var(--crit-soft)"></rect>`;
  g += `<text class="xl" x="${((x0 + X(lo0)) / 2).toFixed(1)}" y="30" text-anchor="middle" style="fill:var(--good-ink)">≤ ${fmt(lo0, 0)} · STRESS и BASE</text><text class="xl" x="${((X(lo0) + X(hi0)) / 2).toFixed(1)}" y="30" text-anchor="middle" style="fill:var(--warn-ink)">${fmt(lo0, 0)}–${fmt(hi0, 0)} · только BASE</text>`;
  g += `<line x1="${X(lo0).toFixed(1)}" x2="${X(lo0).toFixed(1)}" y1="${top - 4}" y2="${base + 4}" style="stroke:var(--warn)" stroke-width="2"></line><line x1="${X(hi0).toFixed(1)}" x2="${X(hi0).toFixed(1)}" y1="${top - 4}" y2="${base + 4}" style="stroke:var(--crit)" stroke-width="2"></line>`;
  items.forEach((c, i) => {
    const y = top + rowH * (i + 0.7), cx = X(c.metrics.c0), ok = c.ok.STRESS;
    g += `<text class="xl" x="200" y="${(y + 4).toFixed(1)}" text-anchor="end" style="fill:var(--ink)">${lotsOf(c)} · ${modesOf(c)}</text><line class="grid" x1="${x0}" x2="${x1}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"></line><circle cx="${cx.toFixed(1)}" cy="${y.toFixed(1)}" r="6" style="fill:var(${ok ? '--good' : c.ok.BASE ? '--warn' : '--crit'});stroke:var(--surface)" stroke-width="2"></circle>`;
    const right = cx + 70 <= x1; // подпись справа от точки, у правого края — слева
    g += right ? `<text class="n t" x="${(cx + 11).toFixed(1)}" y="${(y + 4).toFixed(1)}">${fmt(c.metrics.c0)}</text>` : `<text class="n t" x="${(cx - 11).toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="end">${fmt(c.metrics.c0)}</text>`;
  });
  g += `<line class="axis" x1="${x0}" x2="${x1}" y1="${base}" y2="${base}"></line>`;
  for (let v = dmin; v <= dmax; v += 50) g += `<text class="n" x="${X(v).toFixed(1)}" y="${base + 18}" text-anchor="middle">${fmt(v, 0)}</text>`;
  return `<svg viewBox="0 0 560 ${base + 28}" width="100%" role="img" aria-label="c0 относительно лимитов">${g}</svg>
<div class="legend"><span><i style="background:var(--good);border-radius:50%"></i>оба сценария</span><span><i style="background:var(--warn);border-radius:50%"></i>только BASE</span></div>`;
}
function renderCompare() {
  const d = state.data, s = sel();
  const items = d.comparison.map(combo);
  const okS = items.filter((c) => c.ok.STRESS).length;
  const w = d.meta.weights;
  const pill = `<div class="pill${okS === items.length ? '' : ' warn'}"><span class="dot">${ICON.check}</span>${okS} из ${items.length} проходят STRESS</div>`;
  const body = {
    charts() {
      return `<div class="row2">
<div class="card"><h2>Ценность и поступления в год${help('Общественная ценность vpub — синтетическая шкала кейса в усл. млн руб./год, не деньги; с денежными поступлениями cash (млн руб./год) не складывается. Пунктир — минимум ценности по кейсу. Cash = якорные × k_anchor + коммерческие × k_commercial за год. Под столбцами — состав и режимы в порядке лотов.')}</h2>${barChart(items)}</div>
<div class="card"><h2>Стартовые затраты c0 и лимиты${help(`Положение c0 (млн руб.) каждой комбинации относительно лимитов: ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)} проходит STRESS и BASE, ${fmt(d.meta.scenarios.STRESS.c0_max, 0)}–${fmt(d.meta.scenarios.BASE.c0_max, 0)} — только BASE, выше — не проходит ни один сценарий. Границы включительно.`)}</h2>${c0Chart(items)}</div>
</div>`;
    },
    table() {
      const helpTable = `${items.length} комбинаций, посчитанных по одним правилам. Балл — взвешенная сумма нормированных (min–max по ${d.meta.totals.ranked} комбинациям, допустимым в STRESS${d.meta.gates?.length ? ' и прошедшим S2' : ''}) критериев с весами: ценность ${w.vpub}, c0 ${w.c0}, cash / OPEX ${w.kcash}, готовность ${w.readiness}, устойчивость ${w.resilience}, тираж ${w.scale}, запас по STRESS ${w.stress_margin}. Подсвечена выбранная комбинация; строка с FAIL по STRESS — отвергнутая альтернатива с максимумом ценности; строка с FAIL по S2 — лучшая по баллу без проверки команды. c0, OPEX и cash — млн руб., ценность — усл. млн руб./год.${gateHelp(d)}`;
      const rows = items.map((c) => `<tr class="${c.id === s.id ? 'hl' : ''}"><td>${chips(c)}</td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.opex)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td class="num">${fmt(c.metrics.cash)}</td><td class="num">${fmt(c.metrics.kcash, 2)}</td><td class="num">${fmt(c.metrics.t_rep, 3)}</td><td>${stChip(c.ok.BASE, c.ok.BASE ? 'PASS' : 'FAIL')}</td><td>${stChip(c.ok.STRESS, c.ok.STRESS ? 'PASS' : 'FAIL · c0')}</td>${gateCells(c)}<td class="num">${c.id === s.id ? '<b>' + c.score.toFixed(2) + '</b>' : c.score.toFixed(2)}</td></tr>`).join('');
      return `<div class="card"><h2>Комбинации в сравнении${help(helpTable)}</h2>
<table><tr><th>Состав и режимы</th><th class="num">c0</th><th class="num">OPEX</th><th class="num">Ценность</th><th class="num">Cash</th><th class="num">Cash / OPEX</th><th class="num">t_rep</th><th>BASE</th><th>STRESS</th>${gateHead(d)}<th class="num">Балл</th></tr>${rows}</table></div>`;
    },
  };
  return pageHead('Сравнение вариантов', pill) + body[curTab('compare')]();
}

// ---------- страница «Стресс» ----------
function renderStress() {
  const d = state.data, s = sel(), thin = d.meta.thin_margin_pct;
  const items = d.comparison.map(combo);
  const bad = items.filter((c) => !c.ok.STRESS).length;
  const pill = bad ? `<div class="pill bad"><span class="dot">${ICON.x}</span>${bad} из ${items.length} не проходит STRESS</div>` : `<div class="pill"><span class="dot">${ICON.check}</span>все ${items.length} проходят STRESS</div>`;
  const failId = d.stress.failing, fail = failId ? combo(failId) : null;
  const body = {
    margins() {
      const cols = ['c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor', 'public_core_lots'];
      const head = { c0_limit: `c0 ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)}`, opex_limit: `OPEX ≤ ${d.meta.constraints.opex_max_mrub_per_year}`, vpub_floor: `Ценность ≥ ${fmt(d.meta.constraints.vpub_min_mrub_per_year, 0)}`, kcash_floor: `Cash / OPEX ≥ ${d.meta.constraints.kcash_min.toFixed(2)}`, t_rep_floor: `t_rep ≥ ${d.meta.constraints.t_rep_min}`, public_core_lots: `public core ≥ ${d.meta.constraints.min_public_core_lots}` };
      const short = { c0_limit: 'c0', opex_limit: 'OPEX', vpub_floor: 'ценность', kcash_floor: 'cash / OPEX', t_rep_floor: 't_rep', public_core_lots: 'public core' };
      const cell = (r) => {
        const margin = r.op === '<=' ? r.threshold - r.fact : r.fact - r.threshold;
        const rel = r.threshold ? margin / r.threshold : 0;
        if (r.id === 'public_core_lots') return { cls: !r.ok ? 'bad' : margin === 0 ? 'thin' : 'ok', text: `${r.fact} · ${margin === 0 ? 'граница' : signed(margin, 0)}`, rel: margin === 0 ? 0 : rel };
        const dec = r.id === 'kcash_floor' || r.id === 't_rep_floor' || r.metric ? 2 : r.id === 'vpub_floor' ? 0 : 1;
        const relTxt = Math.abs(rel) < 0.1 ? (rel * 100).toFixed(1) : Math.round(rel * 100);
        return { cls: !r.ok ? 'bad' : rel < thin ? 'thin' : 'ok', text: `${signed(margin, dec)} · ${relTxt} %`, rel };
      };
      const gcols = (d.meta.gates || []).map((g) => g.id);
      const rows = items.map((c) => {
        const rs = Object.fromEntries(checksOf(c, 'STRESS').map((r) => [r.id, r]));
        gatesOf(c).forEach((g) => { rs[g.id] = g; short[g.id] = 'S2'; });
        const all = [...cols, ...gcols];
        const cells = all.map((k) => cell(rs[k]));
        const badCols = all.filter((k, i) => cells[i].cls === 'bad');
        const weakest = badCols.length ? badCols.map((k) => short[k]).join(' · ') + ' · нарушение' : all.filter((k, i) => cells[i].cls === 'thin').map((k) => short[k]).join(' · ') || short[all[cells.map((x) => x.rel).indexOf(Math.min(...cells.map((x) => x.rel)))]];
        return `<tr class="${c.id === s.id ? 'hl' : ''}"><td><div class="name">${lotsOf(c)}</div><div class="sub">${modesOf(c)}${c.id === s.id ? ' · выбрана' : ''}</div></td>${cells.map((x) => `<td><span class="cell ${x.cls}">${x.text}</span></td>`).join('')}<td>${weakest}</td></tr>`;
      }).join('');
      const helpMatrix = `<div class="lg"><span><i class="sw ok"></i>запас ≥ ${Math.round(thin * 100)} %</span><span><i class="sw thin"></i>тонкий запас или граница</span><span><i class="sw bad"></i>нарушение</span></div>В ячейке — факт минус порог и доля от порога в сценарии STRESS (c0 ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)}). Состав (4 лота, архетипы, группы) выполнен у всех и в таблицу не вынесен. «Слабое место» — нарушенное или самое тонкое условие.${gateHelp(d)}`;
      const gateHeads = (d.meta.gates || []).map((g) => `<th>S2: якорь / OPEX ${OP[g.op]} ${fmt(g.threshold, 2)}</th>`).join('');
      return `<div class="card"><h2>Запас по каждому ограничению ${tag('STRESS')}${help(helpMatrix)}</h2>
<table class="matrix"><tr><th>Вариант</th>${cols.map((k) => `<th>${head[k]}</th>`).join('')}${gateHeads}<th>Слабое место</th></tr>${rows}</table></div>`;
    },
    actions() {
      if (!fail) return `<div class="card"><h2>Что можно сделать</h2><div class="empty">Все комбинации в сравнении проходят STRESS — действий не требуется.</div></div>`;
      const rowsA = d.stress.actions.map((a) => {
        const c = combo(a.id);
        return `<tr class="${a.id === s.id ? 'hl' : ''}"><td>${a.id === s.id ? '<b>' + esc(a.label) + '</b>' : esc(a.label)}</td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td>${stChip(a.margin >= 0, signed(a.margin))}</td></tr>`;
      }).join('');
      const rowD = (label, a, b, dec) => `<tr><td>${label}</td><td class="num">${fmt(a, dec)}</td><td class="num">${fmt(b, dec)}</td><td class="num">${signed(b - a, dec)}</td></tr>`;
      const change = describeChange(fail, s);
      return `<div class="row2 w">
<div class="card"><h2>Что можно сделать${chips(fail)}${help(`Комбинация ${lotsOf(fail)} · ${modesOf(fail)} не проходит STRESS. Правило кейса: лимит бюджета не меняет исходную стоимость лотов, c0 снижается только сменой режима или состава. Перевод лота из A в B даёт −5 % его c0 и −18 % ценности, но лот перестаёт быть public core. Каждая строка пересчитана через case_core; в столбце STRESS — запас до лимита c0.`)}</h2>
<table><tr><th>Действие</th><th class="num">c0</th><th class="num">Ценность</th><th>STRESS</th></tr>${rowsA}</table></div>
<div class="card"><h2>Замена: ${esc(change)}${help('Что меняется — цена управленческого решения при сокращении бюджета: разница между отвергнутой комбинацией с максимальной ценностью и выбранной. Решение принимает межрегиональный заказчик; договоры по исключённому лоту не заключаются до второго этапа.')}</h2>
<table><tr><th></th><th class="num">до</th><th class="num">после</th><th class="num">Δ</th></tr>
${rowD('Стартовые затраты c0', fail.metrics.c0, s.metrics.c0, 1)}${rowD('Общественная ценность', fail.metrics.vpub, s.metrics.vpub, 0)}${rowD('Cash / OPEX', fail.metrics.kcash, s.metrics.kcash, 2)}${rowD('Лотов с public core', fail.metrics.public_core, s.metrics.public_core, 0)}
</table></div></div>`;
    },
  };
  return pageHead('Стресс', pill) + body[curTab('stress')]();
}

// ---------- сборка ----------
const ctx = { state, esc, fmt, help, tag, icon: ICON, head: (title, pill) => pageHead(title, pill), tab: () => curTab(), toast: (...a) => toast(...a), render: () => render(), reload: async () => { state.data = await loadDashboard(); state.selected = state.data.selected; localStorage.removeItem('kp.selected'); render(); } };
function render() {
  renderChrome();
  const pages = { portfolio: renderPortfolio, compare: renderCompare, stress: renderStress, data: () => renderData(ctx) };
  $('#main').innerHTML = (pages[state.page] || renderPortfolio)();
  if (state.page === 'data') mountData(ctx);
  window.scrollTo(0, 0);
}
function go(page, tab) {
  state.page = page;
  if (tab) state.tab[page] = tab;
  if (location.hash.replace('#', '') !== hashOf()) location.hash = hashOf();
  render();
}
async function select(id) {
  if (id === state.selected) return;
  if (state.api) state.data = await loadDashboard(id);
  state.selected = id;
  localStorage.setItem('kp.selected', id);
  render();
}
function toast(msg, ok = true) {
  const t = $('#toast'); t.textContent = msg; t.style.color = ok ? 'var(--good)' : 'var(--crit)'; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3500);
}
const closeMenus = () => document.querySelectorAll('.help.open,.dd.open').forEach((o) => o.classList.remove('open'));

document.addEventListener('click', async (e) => {
  const nav = e.target.closest('#nav a');
  if (nav) { go(nav.dataset.page); return; }
  const tab = e.target.closest('[data-tab]');
  if (tab) { go(state.page, tab.dataset.tab); return; }
  if (e.target.closest('#scenario .dd-btn')) { const dd = $('#scenario'), was = dd.classList.contains('open'); closeMenus(); if (!was) dd.classList.add('open'); return; }
  const it = e.target.closest('#scenario .dd-it');
  if (it) { state.scenario = it.dataset.s; closeMenus(); render(); return; }
  const th = e.target.closest('#theme button');
  if (th) { state.theme = th.dataset.theme; localStorage.setItem('kp.theme', state.theme); document.documentElement.dataset.theme = state.theme; renderChrome(); return; }
  if (e.target.closest('#collapse')) { state.collapsed = !state.collapsed; localStorage.setItem('kp.collapsed', state.collapsed ? '1' : '0'); $('#shell').classList.toggle('collapsed', state.collapsed); return; }
  const row = e.target.closest('tr.pick');
  if (row) { await select(row.dataset.id); return; }
  const hb = e.target.closest('.help i');
  if (hb) {
    const h = hb.parentElement, was = h.classList.contains('open');
    closeMenus();
    if (!was) h.classList.add('open');
    return;
  }
  if (!e.target.closest('.pop')) closeMenus();
  if (e.target.closest('#export')) {
    if (!state.api) return toast('Экспорт доступен только с сервером (python app/server.py)', false);
    try {
      const r = await fetch('/api/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ selected: state.selected }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      toast(`Движок kosmo записал ${j.written.length} файлов в ${j.dir}/: ${j.written.map((f) => f.split('/').pop()).join(', ')}`);
    } catch (err) { toast('Ошибка экспорта: ' + err.message, false); }
  }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenus(); });
window.addEventListener('hashchange', () => { const before = hashOf(); if (parseHash() && hashOf() !== before) render(); });

(async () => {
  const remembered = localStorage.getItem('kp.selected');
  state.data = await loadDashboard(remembered || undefined);
  if (state.api && remembered && !state.data.combinations[remembered]) state.data = await loadDashboard();
  state.selected = state.data.combinations[remembered] ? remembered : state.data.selected;
  parseHash();
  render();
})();
