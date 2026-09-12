# Расчётный слой `src/kosmo` — как им пользоваться

Единственное место, где считаются показатели, проверяются ограничения и сравниваются варианты. Интерфейс (участник 5), записка и слайды берут числа только отсюда. Чистый Python 3.10+, без внешних зависимостей; pandas нужен только тесту на совпадение с канонической `case_core.py`.

## Файлы

| Путь | Что это | Кто меняет |
|---|---|---|
| `data/lots.csv`, `data/access_modes.csv`, `config/case_config.json`, `src/case_core.py` | неизменённые файлы организаторов | никто; хэши зафиксированы в `config/case_checksums.json`, при расхождении движок падает с `CaseIntegrityError` |
| `config/portfolio.json` | итоговый портфель FINAL: FIRE-A, ENV-A, AGRI-B, TRANS-B (подтверждён 12.09 11:02) | E/B при смене решения |
| `config/alternatives.json` | сравниваемые варианты: FINAL (итоговый) и V1–V6 | B |
| `config/weights.json` | критерии, направления, веса модели выбора | B |
| `config/custom_mode.json` | режим D; если файла нет — D недоступен; `custom_mode.example.json` — шаблон | C/D |
| `config/assumptions.json` | допущения команды: SLA по каждому сервису, источники данных, правила по облачности, истории, API, журналу доступа, контрольной выборке поставщика; проектное описание, движком не читается | участник 4 (роль D) |
| `config/team.json` | карточка решения: команда, метод, тезис, шесть управленческих полей для `team_decision_config.json` | C, D, E |
| `results/` | выгрузка для записки: `base.json`, `stress.json`, `alternatives.csv`, `scores.csv`, `sensitivity.csv`, `repairs_*.csv`, `enumeration.csv`, плюс `portfolio_detail.csv`, `portfolio_metrics.json`, `team_decision_config.json` в формате стартового notebook организаторов | только `python -m kosmo export` или кнопка «Экспорт results/» интерфейса (та же `export_bundle`) |
| `app/` | интерфейс команды; тонкий слой `app/backend` вызывает движок и собирает `dashboard.json` (`app/CONTRACT.md`) | участник 5 (экраны), участник 4 (слой над движком) |
| `variants/` | сохранённые варианты с настройками и результатами | `python -m kosmo variant save` |
| `examples/` | зафиксированный пример входа/выхода для интерфейса | — |

## Запуск

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Linux/macOS: .venv/bin/pip
set PYTHONPATH=src                                  # Linux/macOS: export PYTHONPATH=src
python -m kosmo calc                                # портфель из config/portfolio.json, оба сценария
python -m kosmo calc --lots FIRE:A FLOOD:A TRANS:A ENV:A --scenario STRESS
python -m kosmo calc --json                         # тот же результат в JSON
python -m kosmo compare --weights config/weights.json
python -m kosmo enumerate --out results/enumeration.csv
python -m kosmo repairs --lots FIRE:A FLOOD:A TRANS:A ENV:A
python -m kosmo export                              # всё в results/
python -m kosmo variant save V1 --lots FIRE:A AGRI:A TRANS:A ENV:A
python -m kosmo variant check V1                    # пересчёт совпал с сохранённым?
python -m pytest -q                                 # 353 теста, ~25 с; сверка с case_core.py на всех 5670 комбинациях, плюс тесты интерфейсного слоя app/tests
python app/build.py                                 # dashboard.json интерфейса из движка
python app/server.py                                # интерфейс на http://127.0.0.1:8765
```

Коды выхода `calc`: 0 — все ограничения выполнены, 1 — есть нарушения, 2 — некорректный вход (портфель, режим D, веса), 3 — исходные файлы изменены или не читаются, 4 — файл не найден / битый JSON / конфликт имён варианта.

Любая ошибка входа — подкласс `InputError` (`SelectionError`, `CustomModeError`, `WeightsError`) с полем `problems` и методом `to_dict()` → `{"error": "invalid_selection", "problems": [...]}`; именно это лежит в `examples/response_invalid.json`.

## Вызов из Python (для интерфейса)

```python
import sys
sys.path.insert(0, "src")

from kosmo import load_case, load_custom_mode, calculate, calculate_all_scenarios, SelectionError

case = load_case(".")
custom = load_custom_mode("config/custom_mode.json")
if custom is not None:
    case = case.with_custom_mode(custom)

try:
    result = calculate(case, [("FIRE", "A"), ("AGRI", "A"), ("TRANS", "A"), ("ENV", "A")], "STRESS")
except SelectionError as error:
    print(error.problems)
else:
    payload = result.to_dict()
```

`calculate_all_scenarios(case, selection)` возвращает `{"BASE": result, "STRESS": result}` за один проход.

`export_bundle(case, portfolio, variants, model, out, with_enumeration=True, team=None)` пишет весь набор `results/` и возвращает словарь `{"BASE": path, "STRESS": path, "portfolio_detail": path, "portfolio_metrics": path, "team_decision_config": path, "alternatives": path, "scores": path, "sensitivity": path, "repairs_BASE": path, "repairs_STRESS": path, "enumeration": path}`; `python -m kosmo export` и интерфейс вызывают именно её. `team` — словарь из `config/team.json` (`load_team_card`).

Так устроен интерфейс (`app/backend`): `enumerate_all` прогоняет `calculate_all_scenarios` по всем 5670 комбинациям, `make_scorer` берёт балл и ранг из `score_variants` с `config/weights.json` (нормализация по допустимым в STRESS), строки проверок для экрана — `{"id": check.code, "ok": check.passed, "fact": check.actual, "op": check.operator, "threshold": check.threshold}` (оператор `==` показывается как `=`). Тест `app/tests/test_backend.py` сверяет dashboard с `results/base.json` и с прямым вызовом движка.

Пары можно передавать кортежами `("FIRE", "A")` или словарями `{"lot_id": "FIRE", "mode_id": "A"}`.

Порядок пар не влияет на числа: суммы считаются через `math.fsum`, поэтому один и тот же портфель в любом порядке даёт побитово одинаковые метрики и проверки. Порядок строк `lots` в ответе повторяет порядок входа. `to_dict()` возвращает только типы JSON (списки, словари, числа, строки, bool).

## Вход

| Поле | Тип | Правила |
|---|---|---|
| `selection` | список из 4 пар `(lot_id, mode_id)` | ровно 4, лоты уникальны, `lot_id` ∈ lots.csv, `mode_id` ∈ {A, B, C} (+ D, если включён) |
| `scenario` | `"BASE"` или `"STRESS"` | из `case_config.json` |
| режим D | `config/custom_mode.json` | все 5 коэффициентов — конечные числа, `k_c0`, `k_opex`, `k_vpub` > 0, `public_core` — bool, `rationale` — непустой текст; `"enabled": false` (или `0`, `"no"`) выключает режим, не удаляя файл |

Любое нарушение — `SelectionError.problems` (список строк на русском), расчёт не запускается.

## Выход (`result.to_dict()`)

```text
scenario         "BASE" | "STRESS"
selection        [{lot_id, mode_id}, ...]
lots             [ по каждому лоту: c0, opex, vpub, anchor_cash, commercial_cash, cash, opex_gap,
                   t_rep, readiness, resilience, scale, public_core, territorial_archetype, federal,
                   capability_groups (как в csv), capability_set (нормализовано) ]
metrics          c0, opex, vpub, cash, anchor_cash, commercial_cash, kcash, opex_gap,
                 t_rep, readiness, resilience, scale (средние),
                 territorial_archetypes, capability_groups, capability_set, public_core_lots, selected_lots
checks           9 строк: code, label, metric, operator, threshold, actual, unit, scope, passed, margin, status
feasible         true, если все 9 проверок пройдены
failed_checks    коды нарушенных проверок
notes            вопросы, требующие управленческого обоснования: code, message, lots
```

`margin` — запас: для `<=` это `порог − факт`, для `>=` это `факт − порог`, для `==` ноль при совпадении. Отрицательный запас = нарушение.

Полный пример: `examples/request.json` → `examples/response.json`; ошибочный вход: `examples/request_invalid.json` → `examples/response_invalid.json`.

## Формулы

По лоту (коэффициенты из `access_modes.csv` для выбранного режима):

```text
c0    = c0_mrub × k_c0                                    млн руб., единовременно
opex  = opex_mrub_per_year × k_opex                       млн руб./год
vpub  = vpub_mrub_per_year × k_vpub                       млн руб./год по шкале кейса, не деньги
cash  = anchor_cash × k_anchor + commercial_cash × k_commercial   млн руб./год
opex_gap = opex − cash                                    непокрытая часть OPEX
```

По портфелю: суммы `c0`, `opex`, `vpub`, `cash`; `kcash = cash / opex`; средние `t_rep`, `readiness`, `resilience`, `scale`; число разных `territorial_archetype` среди нефедеральных лотов; число разных групп после нормализации `PNT`, `InSAR`, `PNT/InSAR` → `PNT/InSAR`; число лотов с `public_core = true`.

Ограничения (границы включаются, допуск 1e-9):

| код | условие | BASE | STRESS |
|---|---|---|---|
| exact_lot_count | selected_lots == 4 | | |
| territorial_archetypes | ≥ 3 | | |
| capability_groups | ≥ 2 | | |
| public_core_lots | ≥ 2 | | |
| c0_limit | c0 ≤ лимит | 1300 | 1180 |
| opex_limit | opex ≤ 360 | | |
| vpub_floor | vpub ≥ 1000 | | |
| kcash_floor | kcash ≥ 0.6 | | |
| t_rep_floor | t_rep ≥ 0.63 | | |

Совпадение с `case_core.py` организаторов проверяется тестом на всех 5670 комбинациях (`tests/test_canonical_equivalence.py`).

## Модель выбора (`config/weights.json`)

Взвешенная сумма нормированных критериев по допустимым вариантам:

```text
z_i = (x_i − min) / (max − min)          для direction = max
z_i = 1 − (x_i − min) / (max − min)      для direction = min
score = Σ w_i z_i / Σ w_i                 ∈ [0, 1]
```

Недопустимые варианты (по сценарию `feasibility_scenario`) в нормализацию не входят и ранга не получают. Критерий `margin:STRESS:c0_limit` — запас по лимиту c0 в стрессе. Чувствительность: каждый вес ±20 % → сменился ли лидер; `vpub`/`cash` портфеля ±20 % → проходят ли ограничения.

## Что движок не считает и не реализует

Дисконтирование, NPV/IRR, налоги, помесячные потоки, вероятностный спрос, SLA, стоимость смены поставщика, горизонт. Всё это — собственные допущения команды в `config/assumptions.json` и тексте записки.

Эксплуатационная архитектура сервисов (модель рабочих событий с `source_updated_at`, `processing_version`, `confidence`, `stale`, `access_class`; REST API; журнал доступа; история событий; два поставщика и контрольная выборка нового поставщика) в этом репозитории **не реализована**. Она описана как целевая архитектура в `config/assumptions.json` и в разделах П5/П7 записки. На защите об этом говорится «предлагаем в архитектуре», а не «реализовано». Реализованы только CLI и Python API расчётного движка.
