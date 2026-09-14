# Контракт данных: `dashboard.json`

Единственный вход интерфейса. Его собирает `app/backend/payload.py`
(`python app/build.py` → `app/static/data/dashboard.json`, или на лету
`GET /api/dashboard?selected=<id>`) из результатов расчётного движка
`src/kosmo`: показатели, проверки и заметки — `kosmo.calculate_all_scenarios`,
балл и ранг — `kosmo.score_variants` с весами `config/weights.json`.
Интерфейс ничего не считает по модели: только отображает и выводит
производные (отличия комбинаций, проценты от порога, графики).

## Идентификатор комбинации

`LOT:MODE|LOT:MODE|LOT:MODE|LOT:MODE` в порядке лотов `lots.csv`, например
`FIRE:A|AGRI:B|TRANS:B|ENV:A`. Лоты — `lot_id` из `lots.csv`, режимы —
`mode_id` из `access_modes.csv` (плюс пользовательский режим из
`config/custom_mode.json`, если он задан). Id в другом порядке лотов
принимается и приводится к каноническому.

## Структура

```jsonc
{
  "meta": {
    "case_id": "SEP-KOSMOS-INFRA-2026",
    "case_version": "1.1",
    "engine": { "name": "kosmo", "verified": true,          // контрольные суммы файлов кейса сошлись с config/case_checksums.json
                "checksums": { "data/lots.csv": "8e2b…", "...": "..." },
                "portfolio": "FINAL", "portfolio_id": "FIRE:A|AGRI:B|TRANS:B|ENV:A",   // из config/portfolio.json
                "weights_file": "config/weights.json" },
    "generated_at": "2026-09-12T10:00:00+00:00",
    "scenarios": { "BASE": { "c0_max": 1300 }, "STRESS": { "c0_max": 1180 } },
    "constraints": { /* constraints_common из case_config.json как есть */ },
    "weights": { "vpub": 0.30, "c0": 0.15, "kcash": 0.15, "readiness": 0.10, "resilience": 0.10, "scale": 0.10, "stress_margin": 0.10 },
    "rationale": { "vpub": "главная цель заказчика", "...": "..." },   // из config/weights.json; margin:STRESS:c0_limit показан как stress_margin
    "gates": [ { "id": "anchor_coverage", "label": "S2: покрытие OPEX якорными платежами", "metric": "anchor_kcash",
                 "op": ">=", "threshold": 0.6, "unit": "доля", "rationale": "..." } ],   // проверки команды из config/weights.json → gates (диагностика S2)
    "gates_filter": false,            // false: gates только показываются; true: не прошедшие gates исключены из ранжирования (?gates=filter)
    "feasible_scenario": "STRESS",    // среди каких комбинаций нормируется балл и считается ранг
    "thin_margin_pct": 0.03,          // порог «тонкого запаса» для стресс-матрицы
    "allowed_modes": ["A", "B", "C"], // режимы, участвующие в предложениях
    "dataset": { "source": "организаторы", "root": ".", "case_version": "1.1" },
    "totals": { "combinations": 5670, "base_feasible": 1031, "stress_feasible": 143, "admitted": 143, "ranked": 143, "pareto": 30 }
                                      // admitted — допустимы в feasible_scenario (при gates_filter — и прошли все gates); ranked = admitted;
                                      // pareto — сколько из них недоминируемы (kosmo.pareto_front по ценности, c0 и покрытию OPEX)
  },

  "lots": {                           // справочник для подписей и карточек сервисов
    "FIRE": { "name": "Лесные пожары", "region": "Сибирь", "archetype": "Сибирский", "groups": ["EO"], "federal": false,
              "card": {                 // из app/config/lots_ui.csv (файл участника записки); null, если строки для лота нет
                "mode": "A",            // режим, для которого написаны правила доступа
                "description": "Показывает потенциальные очаги и помогает службе выбрать, что проверить первым",
                "user": "Лесная или диспетчерская служба",
                "access_base": "Карта событий, время наблюдения, уверенность, статус проверки",
                "access_extra": "История, интеграции и аналитика по отдельному заказу",
                "kpi": "Время от сигнала до проверки",
                "on_failure": "Время последнего обновления, номер инцидента, ручной канал",
                "problem": "Большая территория и риск позднего обнаружения пожаров",
                "payer": "МЧС — предположительно, по консультации трекера 12.09",   // всегда с пометкой «предположительно»
                "risk": "Задержка или ложный сигнал; зависимость от одного источника",
                "effect": "Сокращение времени управленческого решения; конечный ущерб зависит от наземного реагирования",
                "core": "Модель события, API, роли, уведомления, SLA, журнал качества",        // тиражируемое ядро (П8)
                "adaptation": "Границы лесов, сезонные пороги, каналы диспетчеризации и принимающие службы" } }
  },
  "modes": {                          // коэффициенты access_modes.csv; custom = true у режима из config/custom_mode.json
    "A": { "k_c0": 1.05, "k_opex": 1.05, "k_vpub": 1.0, "k_anchor": 1.0, "k_commercial": 0.25, "public_core": true, "custom": false }
  },

  "frontier": [                       // точки графика «ценность против затрат» на экране «Почему FINAL»:
    { "id": "FIRE:A|AGRI:B|TRANS:B|ENV:A",   // все ранжируемые комбинации (при gates_filter — только прошедшие S2),
      "c0": 1140.0, "vpub": 1289.0,          // по возрастанию c0; числа те же, что в combinations
      "kcash": 1.1837, "score": 0.7249, "rank": 3,
      "pareto": true }                       // недоминируемая: kosmo.pareto_front (ценность выше, c0 ниже, покрытие OPEX выше)
  ],

  "selected": "FIRE:A|AGRI:B|TRANS:B|ENV:A",   // показанный портфель: FINAL или произвольный из конструктора (GET /api/dashboard?selected=<id>)
  "final": "FIRE:A|AGRI:B|TRANS:B|ENV:A",      // решение гейта из config/portfolio.json (= meta.engine.portfolio_id); всегда есть в combinations
  "final_name": "FINAL",
  "alternatives": [ { "name": "V2", "id": "FLOOD:A|AGRI:A|TRANS:B|ENV:A", "note": "..." } ],   // config/alternatives.json (участник 3), id в порядке лотов; все есть в combinations
  "why_final": { "status": "...", "headline": "...", "pareto": "...", "price": "...", "robustness": "...", "comparator": "V2" },  // app/config/why_final.json, тексты записки
  "suggestions": ["<id>", "..."],              // предложенные комбинации по убыванию балла; выбранная и портфель команды — всегда среди них
  "rejected": ["<id>"],                        // показываются серыми и не предлагаются: максимум ценности среди проходящих BASE, но не STRESS
                                               // (= stress.failing); при gates_filter перед ней — лучшая по баллу комбинация, не прошедшая gates
  "comparison": ["<id>", "..."],               // строки экрана «Сравнение» и стресс-матрицы
  "stress": {
    "failing": "<id>",                         // комбинация для блока «Что можно сделать»
    "actions": [ { "label": "FLOOD в режим B", "id": "<id>", "margin": -100.0 } ]   // margin = c0_max(STRESS) − c0
  },

  "combinations": {                            // все id, на которые ссылаются поля выше
    "<id>": {
      "id": "<id>",
      "selection": [ { "lot": "FIRE", "mode": "A" }, "..." ],
      "per_lot": [ { "lot": "FIRE", "mode": "A", "public_core": true, "c0": 336.0, "opex": 89.25, "vpub": 560.0, "cash": 83.75,
                     "anchor_cash": 75.0, "commercial_cash": 8.75, "opex_gap": 5.5, "t_rep": 0.68, "readiness": 4.3, "resilience": 3.5, "scale": 4.5 } ],
      "metrics": { "c0": 1140.0, "opex": 313.0, "vpub": 1289.0, "cash": 370.5, "anchor_cash": 190.0, "commercial_cash": 180.5,
                   "kcash": 1.1837, "opex_gap": -57.5, "t_rep": 0.73,
                   "readiness": 4.525, "resilience": 4.05, "scale": 4.675, "archetypes": 4, "groups": 2, "public_core": 2 },
      "checks": {                              // девять проверок kosmo.run_checks, порядок и коды как в case_core.check_constraints
        "BASE":   [ { "id": "c0_limit", "ok": true, "fact": 1140.0, "op": "<=", "threshold": 1300.0 }, "..." ],
        "STRESS": [ "..." ]
      },
      "ok": { "BASE": true, "STRESS": true },
      "gates": [ { "id": "anchor_coverage", "ok": true, "fact": 0.607, "op": ">=", "threshold": 0.6,
                   "label": "S2: покрытие OPEX якорными платежами", "metric": "anchor_kcash" } ],   // проверки команды (kosmo.run_team_checks), не канон
      "admitted": true,                        // ok[feasible_scenario] (и все gates, если gates_filter); только такие комбинации получают rank
      "notes": {                               // управленческие заметки движка (что кейс не задаёт, что решать команде)
        "BASE": [ { "code": "c0_funding", "message": "...", "lots": ["FIRE", "AGRI", "TRANS", "ENV"] } ], "STRESS": [ "..." ]
      },
      "score": 0.7249,                         // балл kosmo.score_variants по всем admitted, 0–1 (для остальных — экстраполяция в тех же границах)
      "rank": 3,                               // место среди admitted; null для остальных
      "s2": { "cash": 190.0, "kcash": 0.607, "opex_gap": 123.0, "kcash_ok": true },   // сценарий команды «commercial cash = 0» из metrics и gate anchor_coverage; не официальный STRESS
      "breakdown": [ { "key": "vpub", "direction": "max", "raw": 1289.0, "lo": 1001.4, "hi": 1370.4, "z": 0.7794, "weight": 0.3, "contribution": 0.2338 }, "..." ]
                                               // разложение балла по критериям config/weights.json (ключ margin:STRESS:c0_limit — запас STRESS); Σ contribution = score; null, если ранжировать нечего
    }
  }
}
```

Идентификаторы проверок: `exact_lot_count`, `territorial_archetypes`,
`capability_groups`, `public_core_lots`, `c0_limit`, `opex_limit`,
`vpub_floor`, `kcash_floor`, `t_rep_floor`. Знак `op` ∈ `=`, `<=`, `>=`;
границы включительно. `t_rep` — показатель воспроизводимости лота (коэффициент масштабируемости решения); в
`metrics.t_rep` — среднее по лотам портфеля, к нему и применяется порог.

## Что интерфейс выводит сам (и чего не надо класть в JSON)

- «Отличие от выбранной» и подсветка чипов — из `selection` двух комбинаций.
- Проценты от порога, запасы BASE/STRESS, статусы плиток — из `checks` и `metrics`.
- Стресс-матрица (запас, доля, тонкий/нарушение) — из `checks.STRESS` и `thin_margin_pct`.
- Графики сравнения — из `metrics` комбинаций в `comparison`.
- График «ценность против затрат» и линия фронта — из `frontier`; интерфейс
  только рисует точки, отбор недоминируемых делает движок.
- Карточка «Замена» — разница `stress.failing` → `selected`.
- Блок «Сервисы портфеля» — `lots[*].card` для лотов выбранной комбинации;
  строки доступа показываются, только если `card.mode` совпадает с режимом
  лота в комбинации. Блок «Тиражирование: ядро и адаптация» — `card.core` и
  `card.adaptation` тех же лотов (П8); лот без карточки получает строку
  «карточка не подготовлена».
- Конструктор — id собирается из четырёх лотов и режимов в порядке `lots`
  и запрашивается `GET /api/dashboard?selected=<id>`; без сервера доступны
  только комбинации из собранного файла.
- Экран «Почему FINAL» — `alternatives`, `why_final`, `breakdown` и `s2`
  комбинаций; Δ относительно FINAL считаются из `metrics`. Вкладка
  «Сценарий S2» кроме `s2` берёт `metrics` и `per_lot` FINAL: сравнение с
  BASE и разложение непокрытого OPEX по лотам считаются в интерфейсе как
  разности уже посчитанных движком величин.

## Экспорт для записки

`python app/build.py --export` вызывает `kosmo.export_bundle` — ту же функцию,
что `python -m kosmo export`. Из интерфейса выгрузка не запускается: кнопки
экспорта в шапке нет. Для портфеля из `config/portfolio.json` файлы
ложатся в `results/` (`base.json`, `stress.json`, `alternatives.csv`,
`scores.csv`, `sensitivity.csv`, `repairs_base.csv`, `repairs_stress.csv`;
формат описан в `docs/calc-engine.md`; плюс `portfolio_detail.csv`,
`portfolio_metrics.json`, `team_decision_config.json` в формате стартового
notebook организаторов, карточка решения — из `config/team.json`), для любой
другой комбинации — в `results/variants/<id>/`. `results/` остаётся
единственным источником цифр для записки и слайдов.
