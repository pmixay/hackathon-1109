// Космо-портфель — интерфейс расчётного инструмента Кейса 02.
// Единственный вход данных: dashboard.json (контракт в app/CONTRACT.md).
// Здесь нет расчётной модели: только отображение и производные для него
// (отличия комбинаций, проценты от порога, разницы между вариантами, графики).

import { renderData, mountData } from './data.js';

const $ = (sel, root = document) => root.querySelector(sel);

// [ключ, заголовок, иконка, заголовок группы в боковой панели (если начинает группу)]
const PAGES = [
  ['portfolio', 'Портфель', '<rect x="2" y="2" width="5" height="5" rx="1"></rect><rect x="9" y="2" width="5" height="5" rx="1"></rect><rect x="2" y="9" width="5" height="5" rx="1"></rect><rect x="9" y="9" width="5" height="5" rx="1"></rect>', 'Расчёт'],
  ['why', 'Почему FINAL', '<path d="M8 14.5s5.5-3.2 5.5-7.5V3.5L8 1.5 2.5 3.5V7c0 4.3 5.5 7.5 5.5 7.5z"></path><path d="M5.5 7.5l1.8 1.8L10.5 6"></path>'],
  ['compare', 'Сравнение', '<path d="M2 13h12M4 11V6M8 11V3M12 11V8"></path>'],
  ['stress', 'Стресс', '<path d="M8 2v6l4 2"></path><circle cx="8" cy="8" r="6"></circle>'],
  ['data', 'Данные', '<ellipse cx="8" cy="4" rx="5" ry="2"></ellipse><path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4M3 8c0 1.1 2.2 2 5 2s5-.9 5-2"></path>', 'Источник'],
];
// вкладки внутри страниц; первая — по умолчанию
const TABS = {
  portfolio: [['overview', 'Обзор'], ['builder', 'Конструктор'], ['checks', 'Ограничения'], ['combos', 'Комбинации'], ['lots', 'Лоты и сервисы']],
  why: [['decision', 'Решение'], ['breakdown', 'Разложение балла'], ['s2', 'Сценарий S2']],
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
  kcash_floor: 'Покрытие OPEX (K_cash)',
  t_rep_floor: 'Воспроизводимость t_rep',
};
const SHORT = { exact_lot_count: 'лотов', territorial_archetypes: 'архетипов', capability_groups: 'групп возможностей', public_core_lots: 'лотов с public core', c0_limit: 'c0', opex_limit: 'OPEX', vpub_floor: 'ценность', kcash_floor: 'K_cash', t_rep_floor: 't_rep' };
const UNIT = { c0_limit: 'млн руб.', opex_limit: 'млн руб./год', vpub_floor: 'усл. млн руб./год', kcash_floor: '', t_rep_floor: '', exact_lot_count: 'шт.', territorial_archetypes: 'шт.', capability_groups: 'шт.', public_core_lots: 'шт.' };
const COMPOSITION = ['exact_lot_count', 'territorial_archetypes', 'capability_groups', 'public_core_lots'];
const THRESHOLDS = ['c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor'];
const DEC = { exact_lot_count: 0, territorial_archetypes: 0, capability_groups: 0, public_core_lots: 0, c0_limit: 1, opex_limit: 1, vpub_floor: 1, kcash_floor: 3, t_rep_floor: 3 };
const THR_DEC = { c0_limit: 0, opex_limit: 0, vpub_floor: 0, kcash_floor: 2, t_rep_floor: 2 };
const OP = { '<=': '≤', '>=': '≥', '=': '=' };
const CRIT = { vpub: 'Общественная ценность', c0: 'Стартовые затраты c0', kcash: 'Покрытие OPEX (K_cash)', readiness: 'Готовность', resilience: 'Устойчивость', scale: 'Тираж', stress_margin: 'Запас STRESS по c0', 'margin:STRESS:c0_limit': 'Запас STRESS по c0' };
const CRIT_DEC = { vpub: 0, c0: 1, kcash: 3, readiness: 2, resilience: 2, scale: 2, stress_margin: 1, 'margin:STRESS:c0_limit': 1 };

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
const lotsOf = (c) => c.selection.map((s) => s.lot).join(', ');
const help = (text) => `<span class="help"><i tabindex="0" role="button" aria-label="Подсказка">?</i><div class="pop">${text}</div></span>`;
const tag = (t, cls = '') => `<span class="tag${cls ? ' ' + cls : ''}">${esc(t)}</span>`;
// Итоговый портфель помечается заливным бейджем: чип того же вида, что у лотов,
// читался как пятый лот. Комбинации называются составом и режимами, а не версиями.
const finBadge = () => `<span class="fin">${ICON.tick}FINAL</span>`;
const isFinalId = (id) => id === state.data?.final;
const more = (tab, label, page = null) => `<a class="more" data-tab="${tab}"${page ? ` data-page="${page}"` : ''}>${label} ${ICON.arrow}</a>`;

// localStorage может быть недоступен (приватный режим, запрет cookies) — интерфейс работает и без памяти между сессиями
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* без памяти между сессиями */ } },
  del: (k) => { try { localStorage.removeItem(k); } catch (e) { /* нечего удалять */ } },
};

// ---------- состояние ----------
const state = {
  data: null,
  api: true,
  page: 'portfolio',
  tab: {},
  scenario: 'BASE',
  selected: null,
  builder: null,       // строки конструктора [{lot, mode} × 4]
  comparator: null,    // имя альтернативы на экране «Почему FINAL»
  collapsed: store.get('kp.collapsed') === '1',
  theme: document.documentElement.dataset.theme || 'light',
  dataset: null,
  gatesFilter: store.get('kp.gates') === '1',   // проверки команды S2 как фильтр ранжирования (только для исследования)
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

async function loadStatic() {
  state.api = false;
  const r = await fetch('data/dashboard.json', { cache: 'no-store' });
  return await r.json();
}
async function loadDashboard(selected) {
  // сервер: пересборка под выбранную комбинацию; статический хостинг (нет /api) — собранный файл
  const params = [];
  if (selected) params.push(`selected=${encodeURIComponent(selected)}`);
  params.push(`gates=${state.gatesFilter ? 'filter' : 'off'}`);
  const q = `?${params.join('&')}`;
  let r;
  try { r = await fetch(`/api/dashboard${q}`, { cache: 'no-store' }); } catch (e) { return loadStatic(); }
  if (r.status === 404 || r.status === 405) return loadStatic();
  if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(j.error || r.statusText); }
  state.api = true;
  return await r.json();
}

// ---------- производные ----------
const combo = (id) => state.data.combinations[id];
const sel = () => combo(state.selected);
const finalC = () => combo(state.data.final);
const isFinal = () => state.selected === state.data.final;

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
  return parts.join(', ') || 'без изменений';
}
const chips = (c, base = null) => {
  const ms = base ? marks(base, c) : c.selection.map((s) => ({ ...s }));
  return `<span class="lots">${ms.map((m) => `<span class="lot${m.swap ? ' swap' : ''}">${m.lot}<b${m.chg ? ' class="chg"' : ''}>${m.mode}</b></span>`).join('')}</span>`;
};
const checksOf = (c, scenario) => c.checks[scenario];
const stChip = (ok, label) => `<span class="st ${ok ? 'ok' : 'fail'}">${label}</span>`;
// проверки команды S2 (kosmo gates): диагностика, на балл не влияют, пока не включён фильтр
const gatesOf = (c) => c.gates || [];
const gateName = (g) => (g.label || g.id).replace(/^S2:\s*/, '');
const gateHead = (d) => (d.meta.gates || []).map((g) => `<th>S2 ${OP[g.op]} ${fmt(g.threshold, 2)}</th>`).join('');
const gateCells = (c) => gatesOf(c).map((g) => `<td>${stChip(g.ok, `${g.ok ? 'PASS' : 'FAIL'}, ${fmt(g.fact, 2)}`)}</td>`).join('');
const gateHelp = (d) => (d.meta.gates || []).map((g) => ` Проверка команды S2 (не канон кейса, диагностика): ${esc(g.label)} — ${g.metric} ${OP[g.op]} ${fmt(g.threshold, 2)}. ${esc(g.rationale)}${d.meta.gates_filter ? ' Сейчас включён режим «S2 как фильтр»: комбинации, не прошедшие S2, в ранжировании не участвуют и показаны серым.' : ' На ранг и балл S2 не влияет; переключатель «S2 как фильтр» на вкладке «Комбинации» показывает, как изменился бы список.'}`).join('');
const gateFailText = (g) => `${gateName(g)}: ${fmt(g.fact, 3)} ${g.op === '<=' ? '>' : '<'} ${fmt(g.threshold, 2)}`;
// Альтернатива подписывается отличием от итогового портфеля, а не именем версии.
const cmpLabel = (a) => {
  const c = combo(a.id), fin = combo(state.data.final);
  return c && fin ? describeChange(fin, c) : a.name;
};
// причина провала STRESS коротко («c0», «лотов с public core»…) для чипа FAIL в таблицах
const stressWhy = (c) => { const bad = checksOf(c, 'STRESS').filter((r) => !r.ok); return bad.some((r) => r.id === 'c0_limit') ? 'c0' : SHORT[bad[0]?.id] || ''; };
// запас по проверке: для «≤» порог − факт, для «≥» факт − порог, для «=» 0 при совпадении
const marginOf = (r) => (r.op === '<=' ? r.threshold - r.fact : r.op === '>=' ? r.fact - r.threshold : r.ok ? 0 : r.fact - r.threshold);
function failText(r) {
  // «c0 = 1 249.5 > 1 180, превышение 69.5 млн руб.» — эксперт не вычисляет причину глазами
  const d = DEC[r.id], td = THR_DEC[r.id] ?? 0, u = UNIT[r.id] ? ' ' + UNIT[r.id] : '';
  if (r.op === '<=') return `${SHORT[r.id]} = ${fmt(r.fact, d)} > ${fmt(r.threshold, td)}, превышение ${fmt(r.fact - r.threshold, d)}${u}`;
  if (r.op === '>=') return `${SHORT[r.id]} = ${fmt(r.fact, d)} < ${fmt(r.threshold, td)}, не хватает ${fmt(r.threshold - r.fact, d)}${u}`;
  return `${SHORT[r.id]} = ${fmt(r.fact, d)} ≠ ${fmt(r.threshold, td)}`;
}
const statusPill = (c, scenario) => {
  const checks = checksOf(c, scenario), ok = checks.filter((r) => r.ok).length, failing = checks.filter((r) => !r.ok);
  const gatesBad = gatesOf(c).filter((g) => !g.ok);
  const gateTxt = gatesBad.length ? `, S2 не пройден: ${gatesBad.map(gateFailText).join(', ')}` : gatesOf(c).length ? ', S2 пройден' : '';
  return failing.length
    ? `<div class="pill bad"><span class="dot">${ICON.x}</span>${scenario}: ${ok} из ${checks.length}, ${failing.map(failText).join('; ')}${gateTxt}</div>`
    : `<div class="pill${gatesBad.length ? ' warn' : ''}"><span class="dot">${gatesBad.length ? ICON.x : ICON.check}</span>${scenario}: ${ok} из ${checks.length} ограничений выполнены (c0 ≤ ${fmt(state.data.meta.scenarios[scenario].c0_max, 0)})${gateTxt}</div>`;
};

// ---------- шапка, навигация, вкладки ----------
function renderChrome() {
  const d = state.data;
  $('#nav').innerHTML = PAGES.map(([k, t, ic, grp]) => (grp ? `<div class="grp">${grp}</div>` : '') + `<a data-page="${k}" class="${k === state.page ? 'on' : ''}"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${ic}</svg><span>${t}</span></a>`).join('');
  const sc = d.meta.scenarios;
  if (!(state.scenario in sc)) state.scenario = Object.keys(sc)[0];
  $('#scenario').innerHTML = `<button class="dd-btn" type="button" title="Сценарий бюджета: меняется только лимит c0 (${esc(state.scenario)}: ≤ ${fmt(sc[state.scenario].c0_max, 0)})"><span class="k">Сценарий</span><b>${esc(state.scenario)}</b>${ICON.chev}</button>
<div class="dd-pop">${Object.keys(sc).map((s) => `<div class="dd-it${s === state.scenario ? ' on' : ''}" data-s="${esc(s)}"><span class="ck">${ICON.tick}</span><div><b>${esc(s)}</b><span>${SCENARIO_NOTE[s] || 'сценарий кейса'}</span></div></div>`).join('')}</div>`;
  $('#theme').innerHTML = `<button type="button" data-theme="light" class="${state.theme === 'light' ? 'on' : ''}" title="Светлая тема">${ICON.sun}</button><button type="button" data-theme="dark" class="${state.theme === 'dark' ? 'on' : ''}" title="Тёмная тема">${ICON.moon}</button>`;
  const src = d.meta.dataset ? (d.meta.dataset.source === 'организаторы' ? '' : ', загружено') : '';
  $('#ver').textContent = `данные v${d.meta.case_version}${src}${state.api ? '' : ', статический файл'}`;
  $('#shell').classList.toggle('collapsed', state.collapsed);
}
const tabsHtml = (page) => `<nav class="tabs">${TABS[page].map(([k, t]) => `<a data-tab="${k}" class="${k === curTab(page) ? 'on' : ''}">${t}</a>`).join('')}</nav>`;
const pageHead = (title, pill, page = state.page) => `<div class="top"><h1>${title}</h1>${pill}</div>${tabsHtml(page)}`;
const portfolioTag = () => (isFinal() ? finBadge() : tag('произвольный портфель', 'warn') + `<a class="more" data-final="1">Вернуть FINAL ${ICON.arrow}</a>`);

// ---------- страница «Портфель» ----------
function renderPortfolio() {
  const d = state.data, s = sel(), sc = state.scenario;
  const checks = checksOf(s, sc), gates = gatesOf(s), gatesBad = gates.filter((g) => !g.ok);
  const pill = statusPill(s, sc);
  const t = d.meta.totals, w = d.meta.weights, m = s.metrics, cons = d.meta.constraints, c0max = d.meta.scenarios[sc].c0_max;
  const weightsTxt = `ценность ${w.vpub}, c0 ${w.c0}, cash / OPEX ${w.kcash}, готовность ${w.readiness}, устойчивость ${w.resilience}, тираж ${w.scale}, запас по STRESS ${w.stress_margin}`;
  const helpChecks = `Девять проверок <b>check_constraints</b>. Состав: ровно ${cons.selected_lots_exactly} лота, ≥ ${cons.min_territorial_archetypes} территориальных архетипа среди нефедеральных, ≥ ${cons.min_capability_groups} группы возможностей, ≥ ${cons.min_public_core_lots} лота с public core. Пороги: c0 ≤ ${fmt(d.meta.scenarios.BASE.c0_max, 0)} в BASE и ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)} в STRESS, OPEX ≤ ${cons.opex_max_mrub_per_year} млн руб./год, ценность ≥ ${fmt(cons.vpub_min_mrub_per_year, 0)}, cash / OPEX ≥ ${cons.kcash_min.toFixed(2)}, воспроизводимость t_rep (среднее по лотам) ≥ ${cons.t_rep_min}. Границы включительно. Сценарий в шапке меняет лимит c0.${gateHelp(d)}`;

  const body = {
    overview() {
      const helpHero = `Показанный портфель: FINAL — решение гейта из <b>config/portfolio.json</b>, или произвольный портфель из конструктора. Четыре лота, у каждого режим доступа (буква в чипе; public core — режим с общественным ядром). В карточке лота — название из карточки сервиса, регион и архетип, стартовые затраты c0 лота с учётом режима. Место — среди ${t.ranked} комбинаций, допустимых в STRESS${d.meta.gates_filter ? ' и прошедших проверку команды S2' : ''}, по баллу модели выбора (0–1; веса: ${weightsTxt}); модель — советник, выбор портфеля управленческий.`;
      const lotCards = s.per_lot.map((r) => {
        const L = d.lots[r.lot];
        return `<div class="hl-lot"><div class="hl-h"><span class="hl-code">${r.lot}</span><span class="mode">${r.mode}${r.public_core ? ', public core' : ''}</span></div><div class="hl-name">${esc(L.name)}</div><div class="hl-sub">${esc(L.region)}</div><div class="hl-c0">${fmt(r.c0)}<small>c0, млн руб.</small></div></div>`;
      }).join('');
      const score = `<div class="hl-score"><div class="k">Место по баллу</div><div class="v">${s.rank ?? '—'}<small>из ${t.ranked}</small></div><div class="s">балл модели <b>${s.score.toFixed(2)}</b></div>${more('decision', 'Почему FINAL', 'why')}</div>`;
      const helpTiles = `Показатели портфеля в сценарии ${sc}. Тёмная часть полосы — использовано или порог, светлая — запас или превышение порога. c0 и OPEX — млн руб.; общественная ценность — усл. млн руб./год (синтетическая шкала кейса, не деньги); покрытие OPEX — поступления cash за год, делённые на OPEX. Запас по c0 — расстояние до лимита в каждом сценарии; отрицательный — лимит превышен.`;
      const tile = (title, val, unit, reqW, lblA, lblB) => `<div class="tile"><div class="tl">${title}</div><div class="tv">${val}<small>${unit}</small></div><div class="seg"><i class="req" style="width:${(reqW * 100).toFixed(1)}%"></i><i class="sur" style="width:${((1 - reqW) * 100).toFixed(1)}%"></i></div><div class="seglbl"><span><i class="sw" style="background:var(--seg-a)"></i>${lblA}</span><span><i class="sw" style="background:var(--seg-b)"></i>${lblB}</span></div></div>`;
      const mB = d.meta.scenarios.BASE.c0_max - m.c0, mS = d.meta.scenarios.STRESS.c0_max - m.c0;
      const tiles = `<div class="tiles">
${tile(`Стартовые затраты c0, лимит ${sc} ${fmt(c0max, 0)}`, fmt(m.c0), 'млн руб.', Math.min(1, m.c0 / c0max), 'использовано ' + fmt(m.c0), (c0max - m.c0 >= 0 ? 'запас ' : 'превышение ') + fmt(Math.abs(c0max - m.c0)))}
${tile('OPEX в год', fmt(m.opex), 'млн руб.', Math.min(1, m.opex / cons.opex_max_mrub_per_year), 'использовано ' + fmt(m.opex), (cons.opex_max_mrub_per_year - m.opex >= 0 ? 'запас ' : 'превышение ') + fmt(Math.abs(cons.opex_max_mrub_per_year - m.opex)))}
${tile('Общественная ценность', fmt(m.vpub, 0), 'усл. млн руб.', Math.min(1, cons.vpub_min_mrub_per_year / m.vpub), 'порог ' + fmt(cons.vpub_min_mrub_per_year, 0), (m.vpub >= cons.vpub_min_mrub_per_year ? 'сверх ' : 'ниже порога ') + signed(m.vpub - cons.vpub_min_mrub_per_year, 0))}
${tile('Покрытие OPEX', fmt(m.kcash, 2), 'cash / OPEX', Math.min(1, cons.kcash_min / m.kcash), 'порог ' + fmt(cons.kcash_min, 2), (m.kcash >= cons.kcash_min ? 'сверх ' : 'ниже порога ') + signed(m.kcash - cons.kcash_min, 2))}
<div class="tile"><div class="tl">Запас по c0${help(helpTiles)}</div><div class="two"><div><span>BASE</span><b class="${mB < 0 ? 'neg' : ''}">${fmt(mB)}</b></div><div><span>STRESS</span><b class="${mS < 0 ? 'neg' : ''}">${fmt(mS)}</b></div></div></div>
</div>`;
      const grp = (title, ids) => {
        const rs = checks.filter((r) => ids.includes(r.id)), okN = rs.filter((r) => r.ok).length, all = okN === rs.length;
        return `<div class="sum-it"><div class="sum-h"><span class="circ${all ? '' : ' bad'}">${all ? ICON.check : ICON.x}</span><span class="t">${title}</span><span class="n">${okN} из ${rs.length}</span></div><div class="sum-l">${rs.map((r) => `<span class="${r.ok ? '' : 'bad'}"><i></i>${CHECK[r.id]}${r.ok ? '' : ', ' + esc(failText(r))}</span>`).join('')}</div></div>`;
      };
      const grpGates = () => {
        if (!gates.length) return '';
        const all = gatesBad.length === 0;
        return `<div class="sum-it"><div class="sum-h"><span class="circ${all ? '' : ' bad'}">${all ? ICON.check : ICON.x}</span><span class="t">Проверка команды S2 <span class="tag warn">диагностика</span></span><span class="n">${gates.length - gatesBad.length} из ${gates.length}</span></div><div class="sum-l">${gates.map((g) => `<span class="${g.ok ? '' : 'bad'}"><i></i>${esc(gateName(g))}${g.ok ? '' : ', ' + esc(gateFailText(g))}</span>`).join('')}</div></div>`;
      };
      return `<div class="card"><h2>${isFinal() ? 'Итоговый портфель' : 'Показанный портфель'} ${portfolioTag()}${help(helpHero)}</h2><div class="hero">${lotCards}${score}</div></div>
${tiles}
<div class="card"><h2>Ограничения ${tag(sc)}${more('checks', 'Факт и пороги')}${help(helpChecks)}</h2><div class="sum">${grp('Состав портфеля', COMPOSITION)}${grp('Финансовые и качественные пороги', THRESHOLDS)}${grpGates()}</div></div>`;
    },
    builder() {
      if (!state.builder) state.builder = s.selection.map((x) => ({ lot: x.lot, mode: x.mode }));
      const st = builderStatus();
      const lotOpts = (cur) => Object.entries(d.lots).map(([lid, L]) => `<option value="${lid}"${lid === cur ? ' selected' : ''}>${lid}, ${esc(L.name)}</option>`).join('');
      const rows = state.builder.map((r, i) => {
        const L = d.lots[r.lot], dup = state.builder.filter((x) => x.lot === r.lot).length > 1;
        const M = d.modes[r.mode] || {};
        const eff = [`c0 ×${M.k_c0}`, `OPEX ×${M.k_opex}`, `ценность ×${M.k_vpub}`].join(', ');
        return `<div class="bld-row${dup ? ' dup' : ''}"><span class="bld-n">${i + 1}</span>
<label class="bld-sel"><select class="bld-lot" data-i="${i}">${lotOpts(r.lot)}</select>${ICON.chev}</label>
<div class="segc bld-mode" data-i="${i}" role="group" aria-label="Режим доступа">${Object.keys(d.modes).map((mm) => `<span tabindex="0" role="button" data-m="${mm}" class="${mm === r.mode ? 'on' : ''}">${mm}</span>`).join('')}</div>
<div class="bld-info"><span class="bld-where">${esc(L.region)}, ${L.groups.join(', ')}${L.federal ? ', федеральный' : ''}</span><span class="bld-eff">режим ${r.mode}: ${eff}${M.public_core ? ', public core' : ''}</span></div></div>`;
      }).join('');
      const same = st.id === state.selected;
      const helpB = `Эксперт собирает любой портфель без правки JSON: четыре разных лота из <b>lots.csv</b> и режим доступа A/B/C каждого (коэффициенты из <b>access_modes.csv</b>; A и режимы с public core отмечены). Порядок строк не важен — комбинация приводится к порядку лотов кейса. Счёт делает сервер (<b>app/backend</b>, формулы case_core); интерфейс только показывает результат. Сценарий BASE/STRESS выбирается в шапке и меняет лимит c0. Кнопка «Вернуть FINAL» возвращает решение гейта.`;
      const form = `<div class="card"><h2>Собрать портфель${help(helpB)}</h2><div class="bld">${rows}</div>
${st.error ? `<div class="bld-err">${esc(st.error)}</div>` : ''}
<div class="acts2"><span class="btn${st.error || same ? ' off' : ''}" tabindex="0" role="button" id="bld-calc">Рассчитать</span><span class="btn ghost${isFinal() && same ? ' off' : ''}" tabindex="0" role="button" data-final="1">Вернуть FINAL</span>${st.error ? '' : `<span class="bld-state${same ? ' ok' : ''}">${same ? 'Показанные экраны соответствуют этому составу' : 'Состав не рассчитан'}</span>`}</div></div>`;
      const res = (scn) => {
        const cs = checksOf(s, scn), bad = cs.filter((r) => !r.ok), lim = cs.find((r) => r.id === 'c0_limit');
        return `<div class="res${bad.length ? ' bad' : ''}"><div class="res-h"><span class="res-s">${scn}</span>${stChip(!bad.length, bad.length ? 'FAIL' : 'PASS')}<span class="res-n">${cs.length - bad.length} из ${cs.length}</span></div>
<div class="res-c0">c0 ${fmt(lim.fact)} ${OP[lim.op]} ${fmt(lim.threshold, 0)}, ${marginOf(lim) >= 0 ? 'запас' : 'превышение'} ${fmt(Math.abs(marginOf(lim)))}</div>
${bad.length ? `<ul class="res-f">${bad.map((r) => `<li>${esc(failText(r))}</li>`).join('')}</ul>` : '<div class="res-ok">Все ограничения выполнены</div>'}</div>`;
      };
      const result = `<div class="card"><h2>Результат расчёта ${chips(s, finalC())} ${portfolioTag()}${more('checks', 'Все 9 проверок')}${help('Результат для показанного портфеля в обоих сценариях: PASS/FAIL, положение c0 относительно лимита и текст каждого нарушенного условия. Жёлтый лот в чипах — отличие от FINAL по составу, жёлтая буква — по режиму. Подробная таблица с фактом, порогом и запасом по всем девяти проверкам — на вкладке «Ограничения».')}</h2><div class="res2">${res('BASE')}${res('STRESS')}</div></div>`;
      return form + result;
    },
    checks() {
      const thin = d.meta.thin_margin_pct;
      const row = (r) => {
        const mg = marginOf(r), comp = COMPOSITION.includes(r.id);
        const rel = !comp && r.threshold ? mg / r.threshold : null;   // доля от порога — только для числовых порогов
        const cls = !r.ok ? 'fail' : r.op === '=' ? 'ok' : comp ? (mg === 0 ? 'edge' : 'ok') : rel < thin ? 'thin' : 'ok';
        const status = cls === 'fail' ? stChip(false, 'FAIL') : cls === 'thin' ? '<span class="st thin">PASS, тонкий запас</span>' : cls === 'edge' ? '<span class="st thin">PASS, граница</span>' : stChip(true, 'PASS');
        return `<tr class="${r.ok ? '' : 'bad'}"><td><div class="name">${CHECK[r.id]}${UNIT[r.id] ? `<span class="unit">${UNIT[r.id]}</span>` : ''}</div>${r.ok ? '' : `<div class="sub fail">${esc(failText(r))}</div>`}</td><td class="num req">${OP[r.op]} ${fmt(r.threshold, THR_DEC[r.id] ?? 0)}</td><td class="num"><b>${fmt(r.fact, DEC[r.id])}</b></td><td class="num ${cls === 'fail' ? 'neg' : cls === 'thin' || cls === 'edge' ? 'warn' : ''}">${r.op === '=' ? (r.ok ? 'ровно — по правилу кейса' : signed(mg, 0)) : signed(mg, DEC[r.id])}${rel !== null && r.ok ? `<span class="rel">${pct(Math.abs(rel))}</span>` : ''}</td><td>${status}</td></tr>`;
      };
      const group = (title, ids) => {
        const rs = checks.filter((r) => ids.includes(r.id)), okN = rs.filter((r) => r.ok).length;
        return `<tr class="grp"><td colspan="5"><span class="circ${okN === rs.length ? '' : ' bad'}">${okN === rs.length ? ICON.check : ICON.x}</span>${title}<span class="cnt">${okN} из ${rs.length}</span></td></tr>${rs.map(row).join('')}`;
      };
      const gateRow = (g) => {
        const mg = g.op === '<=' ? g.threshold - g.fact : g.fact - g.threshold, rel = g.threshold ? mg / g.threshold : null;
        const cls = !g.ok ? 'fail' : rel !== null && rel < thin ? 'thin' : 'ok';
        return `<tr class="${g.ok ? '' : 'bad'}"><td><div class="name">${esc(gateName(g))}<span class="unit">${esc(g.metric)}</span></div>${g.ok ? '' : `<div class="sub fail">${esc(gateFailText(g))}</div>`}</td><td class="num req">${OP[g.op]} ${fmt(g.threshold, 2)}</td><td class="num"><b>${fmt(g.fact, 3)}</b></td><td class="num ${cls === 'fail' ? 'neg' : cls === 'thin' ? 'warn' : ''}">${signed(mg, 3)}${rel !== null && g.ok ? `<span class="rel">${pct(Math.abs(rel))}</span>` : ''}</td><td>${cls === 'fail' ? stChip(false, 'FAIL') : cls === 'thin' ? '<span class="st thin">PASS, тонкий запас</span>' : stChip(true, 'PASS')}</td></tr>`;
      };
      const groupGates = () => gates.length ? `<tr class="grp"><td colspan="5"><span class="circ${gatesBad.length ? ' bad' : ''}">${gatesBad.length ? ICON.x : ICON.check}</span>Проверка команды S2 — стресс спроса <span class="tag warn">не канон кейса</span><span class="cnt">${gates.length - gatesBad.length} из ${gates.length}</span></td></tr>${gates.map(gateRow).join('')}` : '';
      const table = `<div class="card"><h2>Все девять ограничений ${tag(sc)} ${portfolioTag()}${help(helpChecks + ` Запас: для «≤» порог минус факт, для «≥» факт минус порог; рядом доля от порога. Жёлтый статус — запас меньше ${Math.round(thin * 100)} % порога.`)}</h2>
<div class="tw"><table class="chk"><tr><th>Условие</th><th class="num">Требование</th><th class="num">Факт</th><th class="num">Запас</th><th>Статус</th></tr>${group('Состав портфеля', COMPOSITION)}${group('Финансовые и качественные пороги', THRESHOLDS)}${groupGates()}</table></div></div>`;
      const scn = Object.keys(d.meta.scenarios);
      const cell = (fn) => scn.map((k) => `<td class="num">${fn(k)}</td>`).join('');
      const okN = (k) => checksOf(s, k).filter((r) => r.ok).length;
      const nCk = checksOf(s, scn[0]).length;
      const side = `<div class="card"><h2>BASE и STRESS рядом${help('Официально при переходе BASE → STRESS меняется только лимит бюджета c0 (case_config.json, scenarios). Стоимость лотов, OPEX, ценность и поступления не меняются, поэтому все проверки, кроме c0, в обоих сценариях одинаковы. Отрицательный запас — лимит превышен.')}</h2>
<div class="tw"><table class="bs"><tr><th>Показатель</th>${scn.map((k) => `<th class="num">${k}</th>`).join('')}</tr>
<tr><td>Лимит c0, млн руб.</td>${cell((k) => fmt(d.meta.scenarios[k].c0_max, 0))}</tr>
<tr><td>c0 портфеля, млн руб.</td>${cell(() => fmt(m.c0))}</tr>
<tr class="big"><td>Запас по c0</td>${cell((k) => { const v = d.meta.scenarios[k].c0_max - m.c0; return `<b class="${v < 0 ? 'neg' : ''}">${signed(v)}</b>`; })}</tr>
<tr><td>Проверок выполнено</td>${cell((k) => `${okN(k)} из ${nCk}`)}</tr>
<tr><td>Допустимость</td>${cell((k) => stChip(s.ok[k], s.ok[k] ? 'PASS' : 'FAIL'))}</tr></table></div>
<div class="callout">Меняется лимит бюджета, а не стоимость лотов: c0 портфеля в обоих сценариях один и тот же.</div></div>`;
      return `<div class="row2 chk2">${table}${side}</div>`;
    },
    combos() {
      const helpSug = `Инструмент перебирает все ${fmt(t.combinations, 0)} комбинаций «4 лота × режимы» через канонический <b>case_core.py</b>, оставляет ${t.stress_feasible} допустимых в STRESS${d.meta.gates_filter ? `, из них ${t.ranked} проходят проверку команды S2,` : ''} и ранжирует их моделью выбора команды: min–max нормализация по ${t.ranked} допустимым вариантам, веса — ${weightsTxt}. Здесь предложены лучшие по баллу наборы лотов относительно показанного портфеля (клик по строке выбирает), отличия показаны относительно него: жёлтый лот — замена, жёлтая буква — другой режим. Серая строка — максимум ценности среди проходящих BASE, но она не проходит STRESS и не предлагается. Варианты, стоящие выше FINAL по баллу, не скрываются — см. «Почему FINAL».${gateHelp(d)}`;
      const rows = [...d.suggestions, ...d.rejected.filter((id) => !d.suggestions.includes(id))].map((id) => {
        const c = combo(id), isSel = id === state.selected, dim = !(c.admitted ?? c.ok.STRESS), nm = isFinalId(id) ? finBadge() : '';
        const why = isSel ? 'показана' : describeChange(s, c) + (!c.ok.STRESS ? ', не проходит STRESS' : dim ? ', не проходит S2' : '');
        return `<tr class="pick${isSel ? ' hl' : ''}${dim ? ' dim' : ''}" tabindex="0" role="button" aria-pressed="${isSel}" data-id="${esc(id)}"><td><span class="radio${isSel ? ' on' : ''}"></span></td><td>${chips(c, s)}${nm ? ' ' + nm : ''}</td><td class="why">${esc(why)}</td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td class="num">${fmt(c.metrics.kcash, 2)}</td><td>${stChip(c.ok.BASE, c.ok.BASE ? 'PASS' : 'FAIL')}</td><td>${stChip(c.ok.STRESS, c.ok.STRESS ? 'PASS' : 'FAIL, ' + stressWhy(c))}</td>${gateCells(c)}<td class="num">${isSel ? '<b>' + c.score.toFixed(2) + '</b>' : c.score.toFixed(2)}${c.rank ? `<span class="rk">${c.rank}-е</span>` : ''}</td></tr>`;
      }).join('');
      const gatesToggle = (d.meta.gates || []).length ? `<label class="tog"><input type="checkbox" id="gates-filter"${d.meta.gates_filter ? ' checked' : ''}> S2 как фильтр</label>` : '';
      return `<div class="card"><h2>Предложенные комбинации ${portfolioTag()}${gatesToggle}${help(helpSug)}</h2>
<div class="tw wide"><table><tr><th></th><th>Состав и режимы</th><th>Отличие от показанной</th><th class="num">c0</th><th class="num">Ценность</th><th class="num">Cash / OPEX</th><th>BASE</th><th>STRESS</th>${gateHead(d)}<th class="num">Балл, место</th></tr>${rows}</table></div></div>`;
    },
    lots() {
      const lotRow = (r) => {
        const L = d.lots[r.lot];
        return `<tr><td><div class="name"><span class="code">${r.lot}</span>, ${esc(L.name)}</div><div class="sub">${esc(L.archetype)} архетип, ${L.groups.join(', ')}</div></td><td><span class="mode">${r.mode}${r.public_core ? ', public core' : ''}</span></td><td class="num">${fmt(r.c0)}</td><td class="num">${fmt(r.opex, 2)}</td><td class="num">${fmt(r.vpub)}</td><td class="num">${fmt(r.cash, 2)}</td><td class="num">${fmt(r.t_rep, 2)}</td><td class="num">${fmt(r.readiness, 1)}</td><td class="num">${fmt(r.resilience, 1)}</td><td class="num">${fmt(r.scale, 1)}</td></tr>`;
      };
      const modesTxt = Object.entries(d.modes).map(([k, v]) => `<b>Режим ${k}:</b> k_c0 ${v.k_c0}, k_opex ${v.k_opex}, ценность ×${v.k_vpub}, якорные ×${v.k_anchor}, коммерческие ×${v.k_commercial}${v.public_core ? ', public core' : ''}`).join('. ');
      const helpLots = `c0, OPEX и cash — млн руб.; ценность — усл. млн руб./год; готовность, устойчивость и тираж — индексы 1–5 из <b>lots.csv</b>. Значения после применения режима: c0 и OPEX умножены на k_c0 и k_opex, ценность — на k_vpub, поступления = якорные × k_anchor + коммерческие × k_commercial. ${modesTxt}. t_rep — показатель воспроизводимости лота (коэффициент масштабируемости решения). В строке «Портфель» — суммы; для t_rep и индексов — средние.`;
      // карточки сервисов: название для интерфейса и тексты из app/config/lots_ui.csv (файл участника записки)
      const svcCard = (r) => {
        const L = d.lots[r.lot], c = L.card;
        const head = `<div class="sv-h"><div class="name"><span class="code">${r.lot}</span>, ${esc(L.name)}</div><span class="mode">${r.mode}${r.public_core ? ', public core' : ''}</span></div>`;
        if (!c) return `<div class="sv">${head}<div class="sv-r">${esc(L.region)}</div><p class="muted">Карточка сервиса не подготовлена</p></div>`;
        const sameMode = !c.mode || c.mode === r.mode;
        const row = (k, v) => (v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : '');
        const access = sameMode ? row('Базовый доступ', c.access_base) + row('Дополнительно', c.access_extra) : `<dt>Доступ</dt><dd class="muted">описан для режима ${esc(c.mode)}, в комбинации — ${r.mode}</dd>`;
        return `<div class="sv">${head}<div class="sv-r">${esc(L.region)}${c.user ? ', ' + esc(c.user) : ''}</div>${c.problem ? `<div class="sv-p"><b>Проблема:</b> ${esc(c.problem)}</div>` : ''}<p>${esc(c.description)}</p><dl>${access}${row('KPI', c.kpi)}${c.payer ? `<dt>Плательщик</dt><dd>${esc(c.payer)} <span class="hyp">предположение</span></dd>` : ''}${row('Ключевой риск', c.risk)}${row('При сбое', c.on_failure)}</dl></div>`;
      };
      const helpSvc = `Что получает пользователь каждого лота. Карточки сервисов из <b>app/config/lots_ui.csv</b> — файла участника записки: проблема, короткое описание, основной пользователь, базовый и дополнительный доступ, главный KPI, предполагаемый плательщик, ключевой риск, что показать при сбое. Плательщики — гипотезы по консультации трекера 12.09, не подтверждённые назначения. Название лота берётся отсюда же, поэтому в интерфейсе и записке оно одно. Правила доступа описаны для режима из карточки; если в комбинации режим другой, строки доступа не показываются. Оператор, приёмка и полный текст рисков — в записке.`;
      return `<div class="card"><h2>Лоты портфеля ${portfolioTag()}${help(helpLots)}</h2>
<div class="tw wide"><table><tr><th>Лот</th><th>Режим</th><th class="num">c0</th><th class="num">OPEX</th><th class="num">Ценность</th><th class="num">Cash</th><th class="num">t_rep</th><th class="num">Готовность</th><th class="num">Устойчивость</th><th class="num">Тираж</th></tr>
${s.per_lot.map(lotRow).join('')}
<tr class="total"><td>Портфель</td><td></td><td class="num">${fmt(m.c0)}</td><td class="num">${fmt(m.opex, 2)}</td><td class="num">${fmt(m.vpub)}</td><td class="num">${fmt(m.cash, 2)}</td><td class="num">${fmt(m.t_rep, 3)}</td><td class="num">${fmt(m.readiness, 2)}</td><td class="num">${fmt(m.resilience, 2)}</td><td class="num">${fmt(m.scale, 2)}</td></tr></table></div></div>
<div class="card"><h2>Сервисы портфеля${help(helpSvc)}</h2><div class="svc">${s.per_lot.map(svcCard).join('')}</div></div>`;
    },
  };
  return pageHead('Портфель', pill) + body[curTab('portfolio')]();
}

// конструктор: проверка строк и id в порядке лотов кейса
// Состав в конструкторе не совпадает с рассчитанным: уходить молча нельзя.
function builderDirty() {
  if (state.page !== 'portfolio' || curTab() !== 'builder' || !state.builder) return false;
  const order = Object.keys(state.data.lots);
  const id = state.builder.slice().sort((a, b) => order.indexOf(a.lot) - order.indexOf(b.lot)).map((r) => `${r.lot}:${r.mode}`).join('|');
  return id !== state.selected;
}
let pendingNav = null;   // куда хотели уйти, пока висит вопрос
function askBeforeLeave(goThere) {
  pendingNav = goThere;
  const st = builderStatus();
  const calc = st.error ? '' : '<span class="btn" data-leave="calc">Рассчитать и перейти</span>';
  const why = st.error ? esc(st.error) : 'Собранный состав ещё не рассчитан: другие экраны показывают прежний портфель.';
  $('#dlg').innerHTML = `<div class="dlg-box" role="dialog" aria-modal="true" aria-labelledby="dlg-t">
<h3 id="dlg-t">Состав изменён</h3><p>${why}</p>
<div class="dlg-a">${calc}<span class="btn ghost" data-leave="drop">Уйти без расчёта</span><span class="btn ghost" data-leave="stay">Остаться</span></div></div>`;
  $('#dlg').classList.add('open');
}
function closeDialog() { $('#dlg').classList.remove('open'); $('#dlg').innerHTML = ''; pendingNav = null; }

function builderStatus() {
  const d = state.data, rows = state.builder;
  const lots = rows.map((r) => r.lot);
  const dup = [...new Set(lots.filter((l, i) => lots.indexOf(l) !== i))];
  if (dup.length) return { error: `Лот ${dup.join(', ')} выбран дважды — нужны четыре разных лота` };
  if (rows.some((r) => !(r.mode in d.modes))) return { error: 'У каждого лота должен быть режим A, B или C' };
  const order = Object.keys(d.lots);
  const id = rows.slice().sort((a, b) => order.indexOf(a.lot) - order.indexOf(b.lot)).map((r) => `${r.lot}:${r.mode}`).join('|');
  if (!state.api && !d.combinations[id]) return { id, error: 'Без сервера доступны только комбинации из собранного файла. Запустите python app/server.py — тогда считается любой портфель.' };
  return { id };
}

// ---------- страница «Почему FINAL» ----------
function renderWhy() {
  const d = state.data, f = finalC(), why = d.why_final || {}, cons = d.meta.constraints, t = d.meta.totals;
  const alts = (d.alternatives || []).filter((a) => a.id !== d.final);
  if (!state.comparator || !alts.some((a) => a.name === state.comparator)) state.comparator = alts.some((a) => a.name === why.comparator) ? why.comparator : alts[0]?.name;
  const cmpA = alts.find((a) => a.name === state.comparator), cmp = cmpA ? combo(cmpA.id) : null;
  const mS = d.meta.scenarios.STRESS.c0_max - f.metrics.c0;
  const pill = `<div class="pill"><span class="dot">${ICON.check}</span>${f.rank ? `${f.rank}-е место из ${t.ranked}` : 'вне ranking'}, балл ${f.score.toFixed(2)}</div>`;
  const notFinal = isFinal() ? '' : `<div class="callout warn">Сейчас на других экранах показан произвольный портфель; этот экран — про решение команды FINAL. <a class="more" data-final="1">Вернуть FINAL ${ICON.arrow}</a></div>`;
  const metricsRow = [
    ['vpub', 'Общественная ценность', 'усл. млн руб./год', 0, +1],
    ['c0', 'Стартовые затраты c0', 'млн руб.', 1, -1],
    ['opex', 'OPEX', 'млн руб./год', 2, -1],
    ['cash', 'Поступления cash', 'млн руб./год', 1, +1],
    ['kcash', 'Покрытие OPEX (K_cash)', '', 3, +1],
    ['margin', 'Запас STRESS по c0', 'млн руб.', 1, +1],
    ['public_core', 'Лотов с public core', 'шт.', 0, +1],
  ];
  const val = (c, k) => (k === 'margin' ? d.meta.scenarios.STRESS.c0_max - c.metrics.c0 : c.metrics[k]);
  const body = {
    decision() {
      const hero = `<div class="card"><h2>Выбранный командой вариант ${tag('FINAL')}${help(`Формулировки — из записки участника 3 (<b>docs/note/02-selection.md</b>), тексты хранятся в <b>app/config/why_final.json</b>. Балл и место посчитаны на полном множестве ${t.ranked} STRESS-допустимых комбинаций; веса утверждены до просмотра результата.${why.source ? ' Источник: ' + esc(why.source) + '.' : ''}`)}</h2>
<div class="why-hero"><div class="why-txt"><div class="why-st">${esc(why.status || 'Выбранный командой вариант после управленческого отбора.')}</div>${why.headline ? `<p>${esc(why.headline)}</p>` : ''}${why.pareto ? `<p class="why-pareto">${esc(why.pareto)}</p>` : ''}</div>
<div class="why-stats"><div class="ws"><span>Состав</span>${chips(f)}</div><div class="ws"><span>Место по баллу</span><b>${f.rank ?? '—'}<small>из ${t.ranked}</small></b></div><div class="ws"><span>Запас STRESS по c0</span><b>${signed(mS)}<small>млн руб.</small></b></div><div class="ws"><span>Операционный баланс</span><b>${signed(-f.metrics.opex_gap)}<small>млн руб./год</small></b></div></div></div></div>`;
      const alt = (d.alternatives || []).map((a) => combo(a.id) && { ...a, c: combo(a.id) }).filter(Boolean).sort((a, b) => (a.id === d.final ? -1 : b.id === d.final ? 1 : (b.c.rank ?? 1e9) === (a.c.rank ?? 1e9) ? 0 : (a.c.rank ?? 1e9) - (b.c.rank ?? 1e9)));
      const rows = alt.map(({ name, id, note, c }) => `<tr class="${id === d.final ? 'hl' : ''}"><td><div class="alt-h"><span class="alt-code">${esc(name)}</span>${chips(c, f)}${id === d.final ? finBadge() : ''}</div><div class="sub">${esc(note)}</div></td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.opex, 2)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td class="num">${fmt(c.metrics.cash)}</td><td class="num">${fmt(c.metrics.kcash, 3)}</td><td class="num ${c.ok.STRESS ? '' : 'neg'}">${signed(val(c, 'margin'))}</td><td>${stChip(c.ok.BASE, c.ok.BASE ? 'PASS' : 'FAIL')} ${stChip(c.ok.STRESS, c.ok.STRESS ? 'PASS' : 'FAIL')}</td><td class="num">${c.rank ? `<b>${c.score.toFixed(3)}</b><span class="rk">${c.rank}-е</span>` : '<span class="muted">без места</span>'}</td></tr>`).join('');
      const table = `<div class="card"><h2>Ближайшие альтернативы${help(`Сопоставимые варианты записки из <b>config/alternatives.json</b>, подписанные составом и режимами, все посчитаны по одним правилам. Жёлтый лот — отличие от FINAL по составу, жёлтая буква — по режиму. Место — среди ${t.ranked} STRESS-допустимых комбинаций; вариант, не проходящий STRESS, места не получает. Варианты выше FINAL по баллу показаны, а не скрыты.`)}</h2>
<div class="tw wide"><table class="alts"><tr><th>Состав и режимы</th><th class="num">c0</th><th class="num">OPEX</th><th class="num">Ценность</th><th class="num">Cash</th><th class="num">K_cash</th><th class="num">Запас STRESS</th><th>BASE, STRESS</th><th class="num">Балл, место</th></tr>${rows}</table></div></div>${why.base_only ? `<div class="card"><h2>Почему BASE-only вариант отведён до расширения${help('Отвергнутый по бюджету вариант с максимальной общественной ценностью показан серым на вкладке «Комбинации» и в сравнении. Объяснение — формулировка записки (участник 3).')}</h2><p>${esc(why.base_only)}</p></div>` : ''}`;
      let wl = '';
      if (cmp) {
        const win = [], lose = [], even = [];
        for (const [k, label, unit, dec, dir] of metricsRow) {
          const a = val(f, k), b = val(cmp, k), dlt = a - b;
          const item = `<li><span>${label}</span><em><b>${fmt(a, dec)}</b> против ${fmt(b, dec)}</em><i>${signed(dlt, dec)}${unit ? ' ' + unit : ''}</i></li>`;
          if (Math.abs(dlt) < 1e-9) even.push(item); else if (dlt * dir > 0) win.push(item); else lose.push(item);
        }
        wl = `<div class="card"><h2>Что выигрываем и что теряем <span class="cmp-pick">${alts.map((a) => `<span class="chip${a.name === state.comparator ? ' on' : ''}" data-cmp="${esc(a.name)}" tabindex="0" role="button"><b>${esc(a.name)}</b> ${esc(cmpLabel(a))}</span>`).join('')}</span>${help('FINAL против выбранной альтернативы: каждый показатель попадает в «выигрываем» или «теряем» по направлению критерия (ценность, cash, K_cash, запас и public core — больше лучше; c0 и OPEX — меньше лучше). Разницы считаются из показателей обеих комбинаций. Текст «цена решения» — формулировка записки.')}</h2>
<div class="wl"><div class="wl-col win"><div class="wl-h">${ICON.tick} FINAL выигрывает у варианта «${esc(cmpLabel(cmpA))}»</div><ul>${win.join('') || '<li class="none">ничего</li>'}</ul></div><div class="wl-col lose"><div class="wl-h">FINAL теряет против варианта «${esc(cmpLabel(cmpA))}»</div><ul>${lose.join('') || '<li class="none">ничего</li>'}</ul>${even.length ? `<div class="wl-even">Одинаково: ${even.length} показ.</div>` : ''}</div></div>
<div class="cmp-note">${chips(cmp, f)} — ${esc(cmpA.note)}</div>
${why.price ? `<div class="callout">${esc(why.price)}</div>` : ''}</div>`;
      }
      const rob = why.robustness ? `<div class="card"><h2>Устойчивость выбора${help('Sensitivity по полному множеству 143 STRESS-допустимых комбинаций (results/sensitivity_full.csv, tools/case02_robustness.py): изменение каждого веса на ±20 %, случайные векторы весов, запас по c0 и OPEX. Вывод записки: выбор не устойчив как математический лидер, но остаётся осознанным управленческим решением на фронте Парето.')}</h2><p class="why-rob">${esc(why.robustness)}</p></div>` : '';
      return notFinal + hero + table + wl + rob;
    },
    breakdown() {
      const bf = f.breakdown || [], bc = cmp?.breakdown || [];
      const maxW = Math.max(...bf.map((b) => b.weight));
      const bar = (b) => (b ? `<div class="mini"><i style="width:${((b.contribution / maxW) * 100).toFixed(1)}%"></i><span>${b.contribution.toFixed(3)}</span></div>` : '');
      const rows = bf.map((b, i) => {
        const c = bc[i];
        return `<tr><td><div class="name">${CRIT[b.key] || b.key}</div><div class="sub">${b.direction === 'max' ? 'больше — лучше' : 'меньше — лучше'}, min ${fmt(b.lo, CRIT_DEC[b.key])}, max ${fmt(b.hi, CRIT_DEC[b.key])}</div></td><td class="num">${b.weight.toFixed(2)}</td><td class="num">${fmt(b.raw, CRIT_DEC[b.key])}</td><td class="num">${b.z.toFixed(2)}</td><td>${bar(b)}</td>${c ? `<td class="num">${fmt(c.raw, CRIT_DEC[b.key])}</td><td class="num">${c.z.toFixed(2)}</td><td>${bar(c)}</td>` : ''}</tr>`;
      }).join('');
      const total = `<tr class="total"><td>Балл</td><td class="num">${bf.reduce((a, b) => a + b.weight, 0).toFixed(2)}</td><td></td><td></td><td class="num"><b>${f.score.toFixed(3)}</b>${f.rank ? `<span class="rk">${f.rank}-е</span>` : ''}</td>${cmp ? `<td></td><td></td><td class="num"><b>${cmp.score.toFixed(3)}</b>${cmp.rank ? `<span class="rk">${cmp.rank}-е</span>` : ''}</td>` : ''}</tr>`;
      return notFinal + `<div class="card"><h2>Из чего сложился балл <span class="cmp-pick">${alts.map((a) => `<span class="chip${a.name === state.comparator ? ' on' : ''}" data-cmp="${esc(a.name)}" tabindex="0" role="button"><b>${esc(a.name)}</b> ${esc(cmpLabel(a))}</span>`).join('')}</span>${help(`Балл = Σ вес × z. Для каждого критерия z — min–max нормализация по ${t.ranked} STRESS-допустимым комбинациям: 0 — худшее значение среди них, 1 — лучшее (для c0 шкала перевёрнута). Вклад = вес × z; сумма вкладов и есть балл. Веса из <b>config/weights.json</b> (участник 3), утверждены до просмотра результата. Комбинация вне STRESS получает z по той же шкале, но места не получает.`)}</h2>
<div class="tw wide"><table class="brk"><tr><th>Критерий</th><th class="num">Вес</th><th class="num">FINAL: значение</th><th class="num">z</th><th>Вклад</th>${cmp ? `<th class="num">${esc(cmpLabel(cmpA))}: значение</th><th class="num">z</th><th>Вклад</th>` : ''}</tr>${rows}${total}</table></div></div>`;
    },
    s2() {
      const s2 = f.s2 || {}, m = f.metrics;
      const above = s2.cash - cons.kcash_min * m.opex; // запас над порогом K_cash в деньгах
      const tile = (title, val, unit, note = '', cls = '') => `<div class="tile${cls}"><div class="tl">${title}</div><div class="tv">${val}<small>${unit}</small></div>${note ? `<div class="tc">${note}</div>` : ''}</div>`;
      return notFinal + `<div class="card s2"><h2>Дополнительный сценарий команды: commercial cash = 0 ${tag('не официальный STRESS', 'warn')}${help('Риск-сценарий команды (участник 3, config/assumptions.json → commercial_zero_sensitivity): коммерческие поступления обнуляются, остаются только якорные. Он не входит в официальные BASE/STRESS кейса, не фильтрует ranking и не заменяет их; показывает риск ликвидности и потребность в резервном финансировании. Официальный STRESS меняет только лимит c0.')}</h2>
<div class="tiles four">
${tile('Якорные поступления', fmt(s2.cash), 'млн руб./год', `коммерческие ${fmt(m.commercial_cash)} → 0`)}
${tile('OPEX', fmt(m.opex), 'млн руб./год')}
${tile('K_cash в S2', fmt(s2.kcash, 3), 'anchor / OPEX', `порог ${cons.kcash_min.toFixed(2)}, ${s2.kcash_ok ? 'выполнен, запас ' + fmt(above) + ' млн руб./год' : 'нарушен'}`, s2.kcash_ok ? ' thin' : ' bad')}
${tile('Непокрытый OPEX', fmt(s2.opex_gap), 'млн руб./год', 'требует ежегодного покрытия', ' bad')}
</div>
<div class="callout warn">Формальный порог K_cash ≥ ${cons.kcash_min.toFixed(2)} ${s2.kcash_ok ? 'сохраняется только за счёт якорных поступлений' : 'не выполняется'}; для эксплуатации потребуется покрытие ${fmt(s2.opex_gap)} млн руб./год. Это анализ чувствительности команды, а не требование организаторов.</div></div>`;
    },
  };
  return pageHead('Почему FINAL', pill) + body[curTab('why')]();
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
    const lots = c.selection.map((s) => s.lot);
    // столбцы одной комбинации — в группе с прозрачной областью наведения (подсветка столбца, подпись cash, всплывающая подсказка)
    g += `<g class="cb"><title>${esc(`${lotsOf(c)}, ${modesOf(c)} — ценность ${fmt(c.metrics.vpub, 0)}, cash ${fmt(c.metrics.cash, 1)}`)}</title>`;
    g += `<rect class="hit" x="${(cx - step / 2).toFixed(1)}" y="18" width="${step.toFixed(1)}" height="216" rx="8"></rect>`;
    g += `<rect class="b b1" x="${(cx - bw - 2).toFixed(1)}" y="${(base - hv).toFixed(1)}" width="${bw}" height="${hv.toFixed(1)}" rx="3" style="fill:var(--s1)"></rect><rect class="b b2" x="${(cx + 2).toFixed(1)}" y="${(base - hc).toFixed(1)}" width="${bw}" height="${hc.toFixed(1)}" rx="3" style="fill:var(--s2)"></rect>`;
    g += `<text class="n t" x="${(cx - bw / 2 - 2).toFixed(1)}" y="${(base - hv - 6).toFixed(1)}" text-anchor="middle">${fmt(c.metrics.vpub, 0)}</text>`;
    g += `<text class="n t cv" x="${(cx + bw / 2 + 2).toFixed(1)}" y="${(base - hc - 6).toFixed(1)}" text-anchor="middle">${fmt(c.metrics.cash, 0)}</text>`;
    g += `<g class="xl"><text x="${cx.toFixed(1)}" y="204" text-anchor="middle">${lots.slice(0, 2).join(', ')}</text><text x="${cx.toFixed(1)}" y="215" text-anchor="middle">${lots.slice(2).join(', ')}</text></g><g class="xm"><text x="${cx.toFixed(1)}" y="228" text-anchor="middle">${modesOf(c)}</text></g></g>`;
  });
  return `<div class="chart"><svg viewBox="0 0 ${W} 244" width="100%" role="img" aria-label="Общественная ценность и поступления"><line class="axis" x1="${x0}" x2="${x1}" y1="${base}" y2="${base}"></line>${g}</svg>
<div class="legend"><span class="lg lg1"><i style="background:var(--s1)"></i>Общественная ценность</span><span class="lg lg2"><i style="background:var(--s2)"></i>Поступления cash</span><span class="lg lg3"><i class="line"></i>порог ${fmt(floor, 0)}</span></div></div>`;
}
function c0Chart(items) {
  const sc = state.data.meta.scenarios, lo0 = sc.STRESS.c0_max, hi0 = sc.BASE.c0_max;
  const vals = items.map((c) => c.metrics.c0);
  const dmin = Math.min(1100, Math.floor((Math.min(...vals) - 10) / 50) * 50), dmax = Math.max(1300, Math.ceil((Math.max(...vals) + 10) / 50) * 50);
  const x0 = 210, x1 = 540, k = (x1 - x0) / (dmax - dmin), X = (v) => x0 + (v - dmin) * k;
  const top = 40, rowH = 24, base = top + rowH * items.length + 8;
  let g = `<rect x="${x0}" y="${top}" width="${(X(lo0) - x0).toFixed(1)}" height="${base - top}" style="fill:var(--good-soft)"></rect><rect x="${X(lo0).toFixed(1)}" y="${top}" width="${(X(hi0) - X(lo0)).toFixed(1)}" height="${base - top}" style="fill:var(--warn-soft)"></rect>`;
  if (X(hi0) < x1) g += `<rect x="${X(hi0).toFixed(1)}" y="${top}" width="${(x1 - X(hi0)).toFixed(1)}" height="${base - top}" style="fill:var(--crit-soft)"></rect>`;
  g += `<text class="xl" x="${((x0 + X(lo0)) / 2).toFixed(1)}" y="30" text-anchor="middle" style="fill:var(--good-ink)">≤ ${fmt(lo0, 0)}, STRESS и BASE</text><text class="xl" x="${((X(lo0) + X(hi0)) / 2).toFixed(1)}" y="30" text-anchor="middle" style="fill:var(--warn-ink)">${fmt(lo0, 0)}–${fmt(hi0, 0)}, только BASE</text>`;
  g += `<line x1="${X(lo0).toFixed(1)}" x2="${X(lo0).toFixed(1)}" y1="${top - 4}" y2="${base + 4}" style="stroke:var(--warn)" stroke-width="2"></line><line x1="${X(hi0).toFixed(1)}" x2="${X(hi0).toFixed(1)}" y1="${top - 4}" y2="${base + 4}" style="stroke:var(--crit)" stroke-width="2"></line>`;
  items.forEach((c, i) => {
    const y = top + rowH * (i + 0.7), cx = X(c.metrics.c0), ok = c.ok.STRESS;
    const pc = ok ? 'ok' : c.ok.BASE ? 'warn' : 'bad';
    // строка одной комбинации — в группе с прозрачной областью наведения (подсветка строки и всплывающая подсказка)
    g += `<g class="cb"><title>${esc(`${lotsOf(c)}, ${modesOf(c)} — c0 ${fmt(c.metrics.c0)} млн руб., STRESS ${ok ? 'проходит' : 'не проходит'}`)}</title><rect class="hit" x="0" y="${(y - rowH / 2).toFixed(1)}" width="${x1}" height="${rowH}" rx="6"></rect>`;
    g += `<text class="xl" x="200" y="${(y + 4).toFixed(1)}" text-anchor="end" style="fill:var(--ink)">${lotsOf(c)}, ${modesOf(c)}</text><line class="grid" x1="${x0}" x2="${x1}" y1="${y.toFixed(1)}" y2="${y.toFixed(1)}"></line><circle class="p ${pc}" cx="${cx.toFixed(1)}" cy="${y.toFixed(1)}" r="6" style="fill:var(${ok ? '--good' : c.ok.BASE ? '--warn' : '--crit'});stroke:var(--surface)" stroke-width="2"></circle>`;
    const right = cx + 70 <= x1; // подпись справа от точки, у правого края — слева
    g += right ? `<text class="n t" x="${(cx + 11).toFixed(1)}" y="${(y + 4).toFixed(1)}">${fmt(c.metrics.c0)}</text>` : `<text class="n t" x="${(cx - 11).toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="end">${fmt(c.metrics.c0)}</text>`;
    g += '</g>';
  });
  g += `<line class="axis" x1="${x0}" x2="${x1}" y1="${base}" y2="${base}"></line>`;
  for (let v = dmin; v <= dmax; v += 50) g += `<text class="n" x="${X(v).toFixed(1)}" y="${base + 18}" text-anchor="middle">${fmt(v, 0)}</text>`;
  return `<div class="chart"><svg viewBox="0 0 560 ${base + 28}" width="100%" role="img" aria-label="c0 относительно лимитов">${g}</svg>
<div class="legend"><span class="lg lg1"><i style="background:var(--good);border-radius:50%"></i>оба сценария</span><span class="lg lg2"><i style="background:var(--warn);border-radius:50%"></i>только BASE</span></div></div>`;
}
function renderCompare() {
  const d = state.data, s = sel();
  const items = d.comparison.map(combo);
  const altName = {};
  (d.alternatives || []).forEach((a) => { altName[a.id] = a.name; });
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
      const helpTable = `${items.length} комбинаций, посчитанных по одним правилам: предложенные относительно показанного портфеля и отвергнутая с максимумом ценности. Балл — взвешенная сумма нормированных (min–max по ${d.meta.totals.ranked} комбинациям, допустимым в STRESS${d.meta.gates_filter ? ' и прошедшим S2' : ''}) критериев с весами: ценность ${w.vpub}, c0 ${w.c0}, cash / OPEX ${w.kcash}, готовность ${w.readiness}, устойчивость ${w.resilience}, тираж ${w.scale}, запас по STRESS ${w.stress_margin}. Подсвечен показанный портфель; S2 — диагностическая проверка команды, на балл не влияет. c0, OPEX и cash — млн руб., ценность — усл. млн руб./год. Именованные варианты записки — на экране «Почему FINAL».${gateHelp(d)}`;
      const rows = items.map((c) => `<tr class="${c.id === s.id ? 'hl' : ''}"><td>${altName[c.id] ? `<span class="alt-code">${esc(altName[c.id])}</span>` : ''}${chips(c)}${isFinalId(c.id) ? ' ' + finBadge() : ''}</td><td class="num">${fmt(c.metrics.c0)}</td><td class="num">${fmt(c.metrics.opex)}</td><td class="num">${fmt(c.metrics.vpub)}</td><td class="num">${fmt(c.metrics.cash)}</td><td class="num">${fmt(c.metrics.kcash, 2)}</td><td class="num">${fmt(c.metrics.t_rep, 3)}</td><td>${stChip(c.ok.BASE, c.ok.BASE ? 'PASS' : 'FAIL')}</td><td>${stChip(c.ok.STRESS, c.ok.STRESS ? 'PASS' : 'FAIL, ' + stressWhy(c))}</td>${gateCells(c)}<td class="num">${c.id === s.id ? '<b>' + c.score.toFixed(2) + '</b>' : c.score.toFixed(2)}${c.rank ? `<span class="rk">${c.rank}-е</span>` : ''}</td></tr>`).join('');
      return `<div class="card"><h2>Комбинации в сравнении${help(helpTable)}</h2>
<div class="tw wide"><table><tr><th>Состав и режимы</th><th class="num">c0</th><th class="num">OPEX</th><th class="num">Ценность</th><th class="num">Cash</th><th class="num">Cash / OPEX</th><th class="num">t_rep</th><th>BASE</th><th>STRESS</th>${gateHead(d)}<th class="num">Балл, место</th></tr>${rows}</table></div></div>`;
    },
  };
  return pageHead('Сравнение вариантов', pill) + body[curTab('compare')]();
}

// ---------- страница «Стресс» ----------
function renderStress() {
  const d = state.data, s = sel(), thin = d.meta.thin_margin_pct;
  const items = d.comparison.map(combo);
  const bad = items.filter((c) => !c.ok.STRESS).length;
  const pill = bad ? `<div class="pill bad"><span class="dot">${ICON.x}</span>${bad} из ${items.length} сравниваемых не проходит STRESS</div>` : `<div class="pill"><span class="dot">${ICON.check}</span>все ${items.length} сравниваемых проходят STRESS</div>`;
  const failId = d.stress.failing, fail = failId ? combo(failId) : null;
  const body = {
    margins() {
      const cols = ['c0_limit', 'opex_limit', 'vpub_floor', 'kcash_floor', 't_rep_floor', 'public_core_lots'];
      const head = { c0_limit: `c0 ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)}`, opex_limit: `OPEX ≤ ${d.meta.constraints.opex_max_mrub_per_year}`, vpub_floor: `Ценность ≥ ${fmt(d.meta.constraints.vpub_min_mrub_per_year, 0)}`, kcash_floor: `Cash / OPEX ≥ ${d.meta.constraints.kcash_min.toFixed(2)}`, t_rep_floor: `t_rep ≥ ${d.meta.constraints.t_rep_min}`, public_core_lots: `public core ≥ ${d.meta.constraints.min_public_core_lots}` };
      const short = { c0_limit: 'c0', opex_limit: 'OPEX', vpub_floor: 'ценность', kcash_floor: 'cash / OPEX', t_rep_floor: 't_rep', public_core_lots: 'public core' };
      const cell = (r) => {
        const margin = r.op === '<=' ? r.threshold - r.fact : r.fact - r.threshold;
        const rel = r.threshold ? margin / r.threshold : 0;
        if (r.id === 'public_core_lots') return { cls: !r.ok ? 'bad' : margin === 0 ? 'thin' : 'ok', text: `${r.fact}, ${margin === 0 ? 'граница' : signed(margin, 0)}`, rel: margin === 0 ? 0 : rel };
        const dec = r.id === 'kcash_floor' || r.id === 't_rep_floor' || r.metric ? 2 : r.id === 'vpub_floor' ? 0 : 1;
        const relTxt = Math.abs(rel) < 0.1 ? (rel * 100).toFixed(1) : Math.round(rel * 100);
        return { cls: !r.ok ? 'bad' : rel < thin ? 'thin' : 'ok', text: `${signed(margin, dec)}, ${relTxt} %`, rel };
      };
      const gcols = (d.meta.gates || []).map((g) => g.id);
      const rows = items.map((c) => {
        const rs = Object.fromEntries(checksOf(c, 'STRESS').map((r) => [r.id, r]));
        gatesOf(c).forEach((g) => { rs[g.id] = g; short[g.id] = 'S2'; });
        const all = [...cols, ...gcols];
        const cells = all.map((k) => cell(rs[k]));
        const badCols = all.filter((k, i) => cells[i].cls === 'bad');
        const weakest = badCols.length ? badCols.map((k) => short[k]).join(', ') + ', нарушение' : all.filter((k, i) => cells[i].cls === 'thin').map((k) => short[k]).join(', ') || short[all[cells.map((x) => x.rel).indexOf(Math.min(...cells.map((x) => x.rel)))]];
        return `<tr class="${c.id === s.id ? 'hl' : ''}"><td><div class="name">${lotsOf(c)}</div><div class="sub">${modesOf(c)}${c.id === s.id ? ', показана' : ''}${isFinalId(c.id) ? ', FINAL' : ''}</div></td>${cells.map((x) => `<td><span class="cell ${x.cls}">${x.text}</span></td>`).join('')}<td>${weakest}</td></tr>`;
      }).join('');
      const helpMatrix = `<div class="lg"><span><i class="sw ok"></i>запас ≥ ${Math.round(thin * 100)} %</span><span><i class="sw thin"></i>тонкий запас или граница</span><span><i class="sw bad"></i>нарушение</span></div>В ячейке — факт минус порог и доля от порога в сценарии STRESS (c0 ≤ ${fmt(d.meta.scenarios.STRESS.c0_max, 0)}). Состав (4 лота, архетипы, группы) выполнен у всех и в таблицу не вынесен. «Слабое место» — нарушенное или самое тонкое условие. Счётчик в заголовке относится к сравниваемым вариантам, а не к FINAL.${gateHelp(d)}`;
      const gateHeads = (d.meta.gates || []).map((g) => `<th>S2: якорь / OPEX ${OP[g.op]} ${fmt(g.threshold, 2)}</th>`).join('');
      return `<div class="card"><h2>Запас по каждому ограничению ${tag('STRESS')}${help(helpMatrix)}</h2>
<div class="tw wide"><table class="matrix"><tr><th>Вариант</th>${cols.map((k) => `<th>${head[k]}</th>`).join('')}${gateHeads}<th>Слабое место</th></tr>${rows}</table></div></div>`;
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
<div class="card"><h2>Что можно сделать${chips(fail)}${help(`Комбинация ${lotsOf(fail)}, ${modesOf(fail)} не проходит STRESS. Правило кейса: лимит бюджета не меняет исходную стоимость лотов, c0 снижается только сменой режима или состава. Перевод лота из A в B даёт −5 % его c0 и −18 % ценности, но лот перестаёт быть public core. Каждая строка пересчитана через case_core; в столбце STRESS — запас до лимита c0.`)}</h2>
<div class="tw"><table><tr><th>Действие</th><th class="num">c0</th><th class="num">Ценность</th><th>STRESS</th></tr>${rowsA}</table></div></div>
<div class="card"><h2>Замена: ${esc(change)}${help('Что меняется — цена управленческого решения при сокращении бюджета: разница между отвергнутой комбинацией с максимальной ценностью и показанным портфелем. Решение принимает межрегиональный заказчик; договоры по исключённому лоту не заключаются до второго этапа.')}</h2>
<div class="tw"><table><tr><th></th><th class="num">до</th><th class="num">после</th><th class="num">Δ</th></tr>
${rowD('Стартовые затраты c0', fail.metrics.c0, s.metrics.c0, 1)}${rowD('Общественная ценность', fail.metrics.vpub, s.metrics.vpub, 0)}${rowD('Cash / OPEX', fail.metrics.kcash, s.metrics.kcash, 2)}${rowD('Лотов с public core', fail.metrics.public_core, s.metrics.public_core, 0)}
</table></div></div></div>`;
    },
  };
  return pageHead('Стресс', pill) + body[curTab('stress')]();
}

// ---------- сборка ----------
const ctx = { state, esc, help, icon: ICON, head: (title, pill) => pageHead(title, pill), tab: () => curTab(), toast: (...a) => toast(...a), render: () => render(), reload: async () => { state.data = await loadDashboard(); state.selected = state.data.selected; state.builder = null; store.del('kp.selected'); render(); } };
let lastView = null;   // страница/вкладка последнего рендера
function render() {
  renderChrome();
  const pages = { portfolio: renderPortfolio, why: renderWhy, compare: renderCompare, stress: renderStress, data: () => renderData(ctx) };
  $('#main').innerHTML = (pages[state.page] || renderPortfolio)();
  if (state.page === 'data') mountData(ctx);
  // Наверх — только при переходе на другую страницу или вкладку. Перерисовка на месте
  // (смена варианта сравнения, фильтр S2, выбор комбинации) не должна сбрасывать прокрутку.
  const view = `${state.page}/${curTab()}`;
  if (view !== lastView) { window.scrollTo(0, 0); lastView = view; }
}
function go(page, tab) {
  state.page = page;
  if (tab) state.tab[page] = tab;
  if (location.hash.replace('#', '') !== hashOf()) location.hash = hashOf();
  render();
}
async function select(id) {
  if (id !== state.selected) {
    if (state.api) {
      try { state.data = await loadDashboard(id); } catch (e) { toast('Не рассчитано: ' + e.message, false); return; }
    } else if (!state.data.combinations[id]) { toast('Без сервера доступны только комбинации из собранного файла', false); return; }
    state.selected = id;
    store.set('kp.selected', id);
  }
  // строки конструктора всегда приводятся к показанному портфелю — в том числе «Вернуть FINAL» при неизменённом выборе
  state.builder = state.data.combinations[id].selection.map((x) => ({ lot: x.lot, mode: x.mode }));
  render();
}
let toastTimer = 0;
// Смена темы. Новая тема раскрывается кругом от самой кнопки, чтобы было видно,
// откуда она пришла. Где нет View Transitions — короткий переход цвета через класс
// .theming, который тут же снимается. При prefers-reduced-motion — мгновенно, как раньше.
function setTheme(next, btn) {
  const apply = () => {
    state.theme = next;
    store.set('kp.theme', next);
    document.documentElement.dataset.theme = next;
    renderChrome();
  };
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (still || !document.startViewTransition) {
    if (!still) {
      document.documentElement.classList.add('theming');
      setTimeout(() => document.documentElement.classList.remove('theming'), 260);
    }
    apply();
    return;
  }
  // радиус берём до перерисовки: renderChrome() заменит саму кнопку
  const r = btn.getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const far = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  document.startViewTransition(apply).ready.then(() => {
    document.documentElement.animate(
      { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${far}px at ${x}px ${y}px)`] },
      { duration: 420, easing: 'cubic-bezier(.4, 0, .2, 1)', pseudoElement: '::view-transition-new(root)' },
    );
  }).catch(() => { /* переход пропущен браузером — тема уже применена */ });
}

function toast(msg, ok = true) {
  const t = $('#toast'); t.textContent = msg; t.style.color = ok ? 'var(--good)' : 'var(--crit)'; t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
}
const closeMenus = () => document.querySelectorAll('.help.open,.dd.open').forEach((o) => o.classList.remove('open'));

document.addEventListener('click', async (e) => {
  // сначала всплывающие элементы: кнопка «?», выбор сценария; любой другой клик вне подсказки закрывает их
  const hb = e.target.closest('.help i');
  if (hb) {
    const h = hb.parentElement, was = h.classList.contains('open');
    closeMenus();
    if (!was) h.classList.add('open');
    return;
  }
  if (e.target.closest('#scenario .dd-btn')) { const dd = $('#scenario'), was = dd.classList.contains('open'); closeMenus(); if (!was) dd.classList.add('open'); return; }
  const it = e.target.closest('#scenario .dd-it');
  if (it) { state.scenario = it.dataset.s; closeMenus(); render(); return; }
  if (!e.target.closest('.pop')) closeMenus();
  const leave = e.target.closest('[data-leave]');
  if (leave) {
    const how = leave.dataset.leave, next = pendingNav;
    if (how === 'stay') return closeDialog();
    if (how === 'calc') { const st = builderStatus(); closeDialog(); if (!st.error) await select(st.id); next?.(); return; }
    state.builder = null;                      // вернуть форму к рассчитанному составу
    closeDialog(); next?.(); return;
  }
  const nav = e.target.closest('#nav a');
  if (nav) { const p = nav.dataset.page; if (p !== state.page && builderDirty()) return askBeforeLeave(() => go(p)); go(p); return; }
  const fin = e.target.closest('[data-final]');
  if (fin) { await select(state.data.final); return; }
  const tab = e.target.closest('[data-tab]');
  if (tab) {
    const pg = tab.dataset.page || state.page, tb = tab.dataset.tab;
    if ((pg !== state.page || tb !== curTab()) && builderDirty()) return askBeforeLeave(() => go(pg, tb));
    go(pg, tb); return;
  }
  const cmp = e.target.closest('[data-cmp]');
  if (cmp) { state.comparator = cmp.dataset.cmp; render(); return; }
  const mode = e.target.closest('.bld-mode span');
  if (mode) { state.builder[+mode.parentElement.dataset.i].mode = mode.dataset.m; render(); return; }
  if (e.target.closest('#bld-calc')) { const st = builderStatus(); if (!st.error) await select(st.id); return; }
  const th = e.target.closest('#theme button');
  if (th) { setTheme(th.dataset.theme, th); return; }
  if (e.target.closest('#collapse')) { state.collapsed = !state.collapsed; store.set('kp.collapsed', state.collapsed ? '1' : '0'); $('#shell').classList.toggle('collapsed', state.collapsed); return; }
  const gt = e.target.closest('#gates-filter');
  // Без сервера пересчитать нечего: не меняем состояние и не запоминаем флаг,
  // иначе следующий запуск с сервером молча поднимется с включённым фильтром S2.
  if (gt) {
    if (!state.api) { render(); return toast('«S2 как фильтр» доступен только с сервером (python app/server.py)', false); }
    state.gatesFilter = gt.checked; store.set('kp.gates', gt.checked ? '1' : '0');
    try { state.data = await loadDashboard(state.selected); } catch (err) { toast('Не пересчитано: ' + err.message, false); }
    render(); return;
  }
  const row = e.target.closest('tr.pick');
  if (row) { if (row.dataset.id !== state.selected) await select(row.dataset.id); return; }
});
document.addEventListener('change', (e) => {
  const lotSel = e.target.closest('select.bld-lot');
  if (lotSel) { state.builder[+lotSel.dataset.i].lot = lotSel.value; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenus(); });
// Клавиатурная доступность: Enter и пробел работают как клик для строк выбора, чипов сравнения,
// режимов в конструкторе, кнопок и кнопки подсказки «?».
document.addEventListener('keydown', async (e) => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const t = e.target;
  if (!t || !t.closest) return;
  const hb = t.closest('.help i');
  if (hb) { e.preventDefault(); hb.click(); return; }
  const row = t.closest('tr.pick');
  if (row) { e.preventDefault(); if (row.dataset.id !== state.selected) await select(row.dataset.id); return; }
  const cmp = t.closest('[data-cmp]');
  if (cmp) { e.preventDefault(); state.comparator = cmp.dataset.cmp; render(); return; }
  const mode = t.closest('.bld-mode span');
  if (mode) { e.preventDefault(); state.builder[+mode.parentElement.dataset.i].mode = mode.dataset.m; render(); return; }
  const btn = t.closest('span.btn, span.chip[data-cmp]');
  if (btn) { e.preventDefault(); btn.click(); return; }
});
window.addEventListener('hashchange', () => { const before = hashOf(); if (parseHash() && hashOf() !== before) render(); });

(async () => {
  const remembered = store.get('kp.selected');
  try {
    // запомненный id может устареть (другой набор данных) — тогда сервер отвечает 400 и берём портфель по умолчанию
    try { state.data = await loadDashboard(remembered || undefined); } catch (e) { state.data = await loadDashboard(); }
  } catch (e) {
    $('#main').innerHTML = `<div class="empty">Не удалось загрузить данные: ${esc(e.message)}. Запустите python app/server.py или соберите файл командой python app/build.py.</div>`;
    return;
  }
  if (remembered && !state.data.combinations[remembered]) store.del('kp.selected');
  state.selected = state.data.combinations[remembered] ? remembered : state.data.selected;
  parseHash();
  render();
})();
