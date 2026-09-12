// Вкладка «Данные»: загрузка набора в формате организаторов, проверка структуры,
// предпросмотр, применение. Обработка (пересчёт) — на стороне сервера, см. backend/ingest.py.

const LOT_COLUMNS = ['lot_id', 'territorial_archetype', 'service', 'capability_groups', 'c0_mrub', 'opex_mrub_per_year', 'anchor_cash_mrub_per_year', 'commercial_cash_mrub_per_year', 'vpub_mrub_per_year', 't_rep', 'readiness_1_5', 'resilience_1_5', 'scale_1_5', 'federal'];
const LOT_NUMERIC = LOT_COLUMNS.slice(4, 13);
const MODE_COLUMNS = ['mode_id', 'k_c0', 'k_opex', 'k_vpub', 'k_anchor', 'k_commercial', 'public_core'];
const CONFIG_COMMON = ['selected_lots_exactly', 'min_territorial_archetypes', 'min_capability_groups', 'min_public_core_lots', 'opex_max_mrub_per_year', 'vpub_min_mrub_per_year', 'kcash_min', 't_rep_min'];
const FILES = ['lots.csv', 'access_modes.csv', 'case_config.json'];
const ACCEPT = { 'lots.csv': '.csv,text/csv', 'access_modes.csv': '.csv,text/csv', 'case_config.json': '.json,application/json' };
const TITLE = { 'lots.csv': 'Лоты', 'access_modes.csv': 'Режимы доступа', 'case_config.json': 'Ограничения и сценарии' };

const upload = { files: {}, report: {}, parsed: {}, busy: false };

// ---------- разбор и проверка (зеркало backend/ingest.py) ----------
function parseCsv(text) {
  const rows = [];
  let row = [], field = '', q = false;
  const s = text.replace(/\r\n?/g, '\n');
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (q) {
      if (ch === '"' && s[i + 1] === '"') { field += '"'; i++; } else if (ch === '"') q = false; else field += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
    else field += ch;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const header = (rows.shift() || []).map((h) => h.trim());
  const recs = rows.filter((r) => r.some((v) => v !== '')).map((r) => Object.fromEntries(header.map((h, i) => [h, (r[i] ?? '').trim()])));
  return { header, rows: recs };
}
const isNum = (v) => v !== '' && v !== undefined && !Number.isNaN(Number(v));
const isBool = (v) => ['true', 'false'].includes(String(v).toLowerCase());

function validateLots(text) {
  const { header, rows } = parseCsv(text), errors = [], warnings = [];
  const missing = LOT_COLUMNS.filter((c) => !header.includes(c));
  if (missing.length) errors.push('нет столбцов: ' + missing.join(', '));
  const extra = header.filter((c) => !LOT_COLUMNS.includes(c));
  if (extra.length) warnings.push('лишние столбцы игнорируются: ' + extra.join(', '));
  if (!rows.length) errors.push('нет строк с лотами');
  const ids = rows.map((r) => r.lot_id);
  const dup = [...new Set(ids.filter((v, i) => ids.indexOf(v) !== i))];
  if (dup.length) errors.push('повторяющиеся lot_id: ' + dup.join(', '));
  for (const r of rows) {
    for (const c of LOT_NUMERIC) if (header.includes(c) && !isNum(r[c])) errors.push(`${r.lot_id || '?'}: ${c} не число (${r[c]})`);
    if (header.includes('federal') && !isBool(r.federal)) errors.push(`${r.lot_id || '?'}: federal должен быть true/false`);
  }
  if (rows.length && rows.length < 4) errors.push(`лотов ${rows.length}, портфель требует 4`);
  return { ok: !errors.length, errors, warnings, summary: { rows: rows.length, columns: header.length }, table: { header, rows } };
}
function validateModes(text) {
  const { header, rows } = parseCsv(text), errors = [], warnings = [];
  const missing = MODE_COLUMNS.filter((c) => !header.includes(c));
  if (missing.length) errors.push('нет столбцов: ' + missing.join(', '));
  if (!rows.length) errors.push('нет строк с режимами');
  for (const r of rows) {
    for (const c of MODE_COLUMNS.slice(1, 6)) if (header.includes(c) && !isNum(r[c])) errors.push(`режим ${r.mode_id || '?'}: ${c} не число`);
    if (header.includes('public_core') && !isBool(r.public_core)) errors.push(`режим ${r.mode_id || '?'}: public_core должен быть true/false`);
  }
  if (rows.length && !rows.some((r) => String(r.public_core).toLowerCase() === 'true')) warnings.push('ни один режим не даёт public core');
  return { ok: !errors.length, errors, warnings, summary: { rows: rows.length }, table: { header, rows } };
}
function validateConfig(text) {
  const errors = [], warnings = [];
  let cfg;
  try { cfg = JSON.parse(text); } catch (e) { return { ok: false, errors: ['не JSON: ' + e.message], warnings, summary: {} }; }
  const common = cfg.constraints_common;
  if (!common || typeof common !== 'object') errors.push('нет объекта constraints_common');
  else for (const k of CONFIG_COMMON) { if (!(k in common)) errors.push('constraints_common: нет ' + k); else if (!isNum(common[k])) errors.push(`constraints_common.${k} не число`); }
  const scen = cfg.scenarios;
  if (!scen || typeof scen !== 'object' || !Object.keys(scen).length) errors.push('нет объекта scenarios');
  else {
    for (const [n, s] of Object.entries(scen)) if (!s || !isNum(s.c0_max_mrub)) errors.push(`scenarios.${n}: нет числового c0_max_mrub`);
    if (!('BASE' in scen && 'STRESS' in scen)) errors.push('нужны сценарии BASE и STRESS — на них построены расчёт и экраны');
  }
  if (!('case_version' in cfg)) warnings.push('нет case_version');
  return { ok: !errors.length, errors, warnings, summary: { case_version: cfg.case_version, scenarios: scen ? Object.keys(scen) : [] }, cfg };
}
const VALIDATE = { 'lots.csv': validateLots, 'access_modes.csv': validateModes, 'case_config.json': validateConfig };

// ---------- отображение ----------
export function renderData(ctx) {
  const { esc, help, state } = ctx;
  const ds = state.dataset;
  const cur = ds ? `<div class="tw"><table><tr><th>Файл</th><th>Содержание</th><th>Хэш</th><th class="num">Байт</th></tr>${FILES.map((n) => {
    const f = ds.files[n] || {};
    const s = f.summary || {};
    const what = n === 'lots.csv' ? `${s.rows ?? '?'} лотов, ${s.columns ?? '?'} полей` : n === 'access_modes.csv' ? `режимы ${(s.modes || []).join(', ')}` : `версия ${s.case_version ?? '—'}, сценарии ${(s.scenarios || []).join(', ')}, ${s.constraints ?? '?'} ограничений`;
    return `<tr><td><span class="code">${n}</span></td><td>${f.missing ? '<span class="st fail">нет файла</span>' : esc(what)}</td><td class="mono">${f.sha || '—'}</td><td class="num">${f.bytes ?? '—'}</td></tr>`;
  }).join('')}</table></div><div class="note">${esc(ds.source === 'организаторы' ? 'Файлы организаторов (копия cases/case02 в data/ и config/, сверена движком по контрольным суммам). Расчёт идёт по ним через src/kosmo.' : `Загруженный набор, активирован ${ds.activated_at || ''}. Папка: ${ds.root}`)}</div>`
    : `<div class="empty">${state.api ? 'Загрузка…' : 'Сведения о наборе доступны только с сервером (python app/server.py). Проверка файлов ниже работает и без него.'}</div>`;
  const pill = ds ? `<div class="pill"><span class="dot">${ctx.icon.check}</span>${ds.source === 'организаторы' ? 'файлы организаторов' : 'загруженный набор'} · v${ds.case_version ?? '—'}</div>` : '';

  const slot = (n) => {
    const rep = upload.report[n];
    const st = !rep ? '' : rep.ok ? `<span class="st ok">OK${rep.warnings.length ? ' · ' + rep.warnings.length + ' предупр.' : ''}</span>` : `<span class="st fail">${rep.errors.length} ошиб.</span>`;
    return `<label class="slot${rep ? (rep.ok ? ' ok' : ' bad') : ''}" data-file="${n}"><input type="file" accept="${ACCEPT[n]}" data-file="${n}"><div class="slot-t"><b>${n}</b><span>${TITLE[n]}</span></div><div class="slot-s">${st || '<span class="muted">перетащите или выберите</span>'}</div></label>`;
  };
  const issues = FILES.filter((n) => upload.report[n]).map((n) => {
    const r = upload.report[n];
    if (!r.errors.length && !r.warnings.length) return '';
    return `<div class="issues"><b>${n}</b>${r.errors.map((e) => `<div class="iss bad">${esc(e)}</div>`).join('')}${r.warnings.map((w) => `<div class="iss warn">${esc(w)}</div>`).join('')}</div>`;
  }).join('');
  const anyLoaded = FILES.some((n) => upload.files[n] !== undefined);
  const allOk = anyLoaded && FILES.every((n) => !upload.report[n] || upload.report[n].ok);
  const previews = FILES.filter((n) => upload.report[n]?.ok).map((n) => previewOf(n, ctx)).join('');
  const helpUpload = 'Три файла в формате организаторов, можно загружать по одному: lots.csv (14 полей на лот), access_modes.csv (коэффициенты режимов и public_core), case_config.json (constraints_common и scenarios с c0_max_mrub). Файлы проверяются здесь на структуру и типы, затем на сервере, сохраняются в app/data/uploads и становятся активным набором; все экраны пересчитываются. Непереданные файлы берутся из текущего набора. «Вернуть файлы организаторов» возвращает исходный набор (копия cases/case02).';
  const fmtCard = `<div class="card"><h2>Формат организаторов${help('Обязательные столбцы и типы. Лишние столбцы игнорируются, порядок не важен. Разделитель — запятая, кодировка UTF-8. capability_groups — список через точку с запятой (EO; PNT/InSAR; SATCOM; SSA), federal и public_core — true/false. В scenarios обязательны BASE и STRESS (на них построены расчёт и экраны), другие сценарии допускаются.')}</h2>
<div class="fmt"><div><b>lots.csv</b><div class="cols">${LOT_COLUMNS.map((c) => `<span class="lot${LOT_NUMERIC.includes(c) ? '' : ' txt'}">${c}</span>`).join('')}</div></div>
<div><b>access_modes.csv</b><div class="cols">${MODE_COLUMNS.map((c) => `<span class="lot${c === 'mode_id' || c === 'public_core' ? ' txt' : ''}">${c}</span>`).join('')}</div></div>
<div><b>case_config.json</b><div class="cols"><span class="lot txt">case_version</span>${CONFIG_COMMON.map((c) => `<span class="lot">constraints_common.${c}</span>`).join('')}<span class="lot">scenarios.&lt;имя&gt;.c0_max_mrub</span></div></div></div>
<div class="legend"><span><i style="background:var(--rule-2)"></i>число</span><span><i style="background:var(--brand-soft)"></i>текст или true/false</span></div></div>`;

  const body = {
    current: () => `<div class="card"><h2>Текущий набор${help('По этому набору считаются все экраны. Активный набор данных: исходные файлы организаторов или загруженный набор. Хэш — первые 12 знаков SHA-256 содержимого; он же подтверждает, что файлы организаторов не менялись.')}</h2>${cur}</div>`,
    upload: () => `<div class="card dz" id="dz"><h2>Загрузить новый набор${help(helpUpload)}</h2>
<div class="slots">${FILES.map(slot).join('')}</div>${issues}
<div class="acts2"><span class="btn${allOk && state.api && !upload.busy ? '' : ' off'}" id="apply">${upload.busy ? 'Применяю…' : 'Применить и пересчитать'}</span><span class="btn ghost${anyLoaded ? '' : ' off'}" id="clear">Очистить</span><span class="btn ghost${state.api && ds && ds.source !== 'организаторы' ? '' : ' off'}" id="reset">Вернуть файлы организаторов</span>${!state.api ? '<span class="note">применение требует сервера</span>' : ''}</div></div>
${previews}`,
    format: () => fmtCard,
  };
  return ctx.head('Данные', pill) + body[ctx.tab()]();
}

function previewOf(n, ctx) {
  const { esc } = ctx, rep = upload.report[n];
  if (n === 'case_config.json') {
    const c = rep.cfg;
    const rows = Object.entries(c.constraints_common || {}).map(([k, v]) => `<tr><td><span class="code">${k}</span></td><td class="num">${esc(String(v))}</td></tr>`).join('');
    const sc = Object.entries(c.scenarios || {}).map(([k, v]) => `<tr><td><span class="code">scenarios.${k}.c0_max_mrub</span></td><td class="num">${esc(String(v.c0_max_mrub))}</td></tr>`).join('');
    return `<div class="card"><h2>Предпросмотр · case_config.json<span class="u">версия ${esc(String(c.case_version ?? '—'))}</span></h2><div class="tw"><table class="half"><tr><th>Параметр</th><th class="num">Значение</th></tr>${rows}${sc}</table></div></div>`;
  }
  const { header, rows } = rep.table;
  const cols = (n === 'lots.csv' ? LOT_COLUMNS : MODE_COLUMNS).filter((c) => header.includes(c));
  const numeric = n === 'lots.csv' ? LOT_NUMERIC : MODE_COLUMNS.slice(1, 6);
  return `<div class="card"><h2>Предпросмотр · ${n}<span class="u">${rows.length} строк</span></h2><div class="scroll"><table><tr>${cols.map((c) => `<th${numeric.includes(c) ? ' class="num"' : ''}>${c}</th>`).join('')}</tr>${rows.map((r) => `<tr>${cols.map((c) => numeric.includes(c) ? `<td class="num">${esc(r[c])}</td>` : `<td>${c.endsWith('_id') ? '<span class="code">' + esc(r[c]) + '</span>' : esc(r[c])}</td>`).join('')}</tr>`).join('')}</table></div></div>`;
}

// ---------- события ----------
export async function mountData(ctx) {
  const { state } = ctx;
  if (state.api && !state.dataset) {
    try { const r = await fetch('/api/data', { cache: 'no-store' }); if (r.ok) { state.dataset = await r.json(); ctx.render(); return; } } catch {}
  }
  const main = document.querySelector('#main');
  const takeFile = async (name, file) => {
    const text = await file.text();
    upload.files[name] = text;
    upload.report[name] = VALIDATE[name](text);
    ctx.render();
  };
  main.querySelectorAll('input[type=file]').forEach((inp) => inp.addEventListener('change', () => { if (inp.files[0]) takeFile(inp.dataset.file, inp.files[0]); }));
  const dz = main.querySelector('#dz');
  if (dz) {
    dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('over'));
    dz.addEventListener('drop', async (e) => {
      e.preventDefault(); dz.classList.remove('over');
      for (const f of e.dataTransfer.files) {
        const name = FILES.find((n) => f.name.toLowerCase() === n) || (f.name.toLowerCase().endsWith('.json') ? 'case_config.json' : null);
        if (name) await takeFile(name, f); else ctx.toast(`Не узнаю файл ${f.name}: ожидаю lots.csv, access_modes.csv или case_config.json`, false);
      }
    });
  }
  main.querySelector('#clear')?.addEventListener('click', () => { upload.files = {}; upload.report = {}; ctx.render(); });
  main.querySelector('#reset')?.addEventListener('click', async (e) => {
    if (e.currentTarget.classList.contains('off')) return;
    try {
      const r = await fetch('/api/data/reset', { method: 'POST' });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
      state.dataset = null; upload.files = {}; upload.report = {};
      await ctx.reload();
      ctx.toast('Возвращены файлы организаторов');
    } catch (err) { ctx.toast('Не удалось вернуть файлы организаторов: ' + err.message, false); }
  });
  main.querySelector('#apply')?.addEventListener('click', async (e) => {
    if (e.currentTarget.classList.contains('off')) return;
    upload.busy = true; ctx.render();
    try {
      const r = await fetch('/api/data', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files: upload.files, apply: true }) });
      const j = await r.json();
      if (!r.ok || !j.ok) {
        for (const [n, rep] of Object.entries(j.report || {})) if (upload.report[n]) upload.report[n] = { ...upload.report[n], ...rep, table: upload.report[n].table, cfg: upload.report[n].cfg };
        throw new Error(j.error || 'сервер отклонил набор');
      }
      state.dataset = j.dataset; upload.files = {}; upload.report = {};
      await ctx.reload();
      ctx.toast('Набор применён, экраны пересчитаны');
    } catch (err) { ctx.toast('Не применено: ' + err.message, false); }
    finally { upload.busy = false; ctx.render(); }
  });
}
