# Контракт данных: `dashboard.json`

Единственный вход интерфейса. Его собирает `app/backend/payload.py`
(`python app/build.py` → `app/static/data/dashboard.json`, или на лету
`GET /api/dashboard?selected=<id>`). Интерфейс ничего не считает по модели:
только отображает и выводит производные (отличия комбинаций, проценты от
порога, графики). Поэтому расчёт можно заменить целиком, сохранив форму
этого файла.

## Идентификатор комбинации

`LOT:MODE|LOT:MODE|LOT:MODE|LOT:MODE` в порядке лотов, например
`FIRE:A|AGRI:B|TRANS:B|ENV:A`. Лоты — `lot_id` из `lots.csv`, режимы —
`mode_id` из `access_modes.csv`.

## Структура

```jsonc
{
  "meta": {
    "case_id": "SEP-KOSMOS-INFRA-2026",
    "case_version": "1.1",
    "generated_at": "2026-09-12T10:00:00+00:00",
    "scenarios": { "BASE": { "c0_max": 1300 }, "STRESS": { "c0_max": 1180 } },
    "constraints": { /* constraints_common из case_config.json как есть */ },
    "weights": { "vpub": 0.30, "c0": 0.15, "kcash": 0.15, "readiness": 0.10, "resilience": 0.10, "scale": 0.10, "stress_margin": 0.10 },
    "rationale": { "vpub": "главная цель заказчика", "...": "..." },
    "thin_margin_pct": 0.03,          // порог «тонкого запаса» для стресс-матрицы
    "allowed_modes": ["A", "B", "C"], // режимы, участвующие в предложениях
    "totals": { "combinations": 5670, "base_feasible": 1031, "stress_feasible": 143 }
  },

  "lots": {                           // справочник для подписей и карточек сервисов
    "FIRE": { "name": "Лесные пожары", "region": "Сибирь", "archetype": "Сибирский", "groups": ["EO"], "federal": false,
              "card": {                 // из config/lots_ui.csv (файл участника записки); null, если строки для лота нет
                "mode": "A",            // режим, для которого написаны правила доступа
                "description": "Показывает потенциальные очаги и помогает службе выбрать, что проверить первым",
                "user": "Лесная или диспетчерская служба",
                "access_base": "Карта событий, время наблюдения, уверенность, статус проверки",
                "access_extra": "История, интеграции и аналитика по отдельному заказу",
                "kpi": "Время от сигнала до проверки",
                "on_failure": "Время последнего обновления, номер инцидента, ручной канал" } }
  },
  "modes": {                          // коэффициенты access_modes.csv
    "A": { "k_c0": 1.05, "k_opex": 1.05, "k_vpub": 1.0, "k_anchor": 1.0, "k_commercial": 0.25, "public_core": true }
  },

  "selected": "FIRE:A|AGRI:B|TRANS:B|ENV:A",   // выбранный портфель (решение гейта)
  "suggestions": ["<id>", "..."],              // предложенные комбинации по порядку показа; выбранная — среди них
  "rejected": ["<id>"],                        // показываются серыми: проходят BASE, не проходят STRESS
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
                     "anchor_cash": 75.0, "commercial_cash": 8.75, "t_rep": 0.68, "readiness": 4.3, "resilience": 3.5, "scale": 4.5 } ],
      "metrics": { "c0": 1140.0, "opex": 313.0, "vpub": 1289.0, "cash": 370.5, "kcash": 1.1837, "t_rep": 0.73,
                   "readiness": 4.525, "resilience": 4.05, "scale": 4.675, "archetypes": 4, "groups": 2, "public_core": 2 },
      "checks": {                              // девять проверок check_constraints, порядок как в case_core
        "BASE":   [ { "id": "c0_limit", "ok": true, "fact": 1140.0, "op": "<=", "threshold": 1300 }, "..." ],
        "STRESS": [ "..." ]
      },
      "ok": { "BASE": true, "STRESS": true },
      "score": 0.7249,                         // балл модели выбора, 0–1
      "rank": 3                                // место среди допустимых в STRESS; null для недопустимых
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
- Карточка «Замена» — разница `stress.failing` → `selected`.
- Блок «Сервисы портфеля» — `lots[*].card` для лотов выбранной комбинации;
  строки доступа показываются, только если `card.mode` совпадает с режимом
  лота в комбинации.

## Экспорт для записки

`python app/build.py --export` (или кнопка «Экспорт results/» в шапке при
запущенном сервере) пишет `results/base.json`, `results/stress.json`
(выбранная комбинация: состав, лоты, показатели, проверки, балл, веса) и
`results/alternatives.csv` (строки `comparison`), а также
`results/portfolio_detail.csv`, `results/portfolio_metrics.json` и
`results/team_decision_config.json` в формате стартового notebook
организаторов (карточка решения — из `app/config/team.json`). Это единственный источник
цифр для записки и слайдов.
