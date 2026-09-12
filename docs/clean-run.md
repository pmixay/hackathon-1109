# Чистый запуск: протокол и результат

Проверка «эксперт запускает без помощи разработчика» выполнена 12.09.2026 в
пустой папке из свежего клона ветки (коммит `e3016e2`). Все команды ниже —
ровно те, что выполнялись; результат записан как есть.

## Команды

```bash
git clone --branch claude/trusting-bohr-lfy6se https://github.com/pmixay/hackathon-1109 kosmo && cd kosmo
python -m venv .venv
.venv/bin/pip install -r requirements.txt            # Windows: .venv\Scripts\pip
PYTHONPATH=src .venv/bin/python -m pytest -q          # движок src/kosmo
.venv/bin/python -m unittest discover -s app/tests    # расчётный слой интерфейса + сверка с движком
PYTHONPATH=src .venv/bin/python -m kosmo calc --lots FIRE:A ENV:A AGRI:B TRANS:B --scenario STRESS
.venv/bin/python app/server.py                        # http://127.0.0.1:8765
```

Интерфейсу зависимости не нужны: `app/server.py` работает на стандартной
библиотеке; `pandas`/`pytest` из `requirements.txt` нужны только тестам движка.

## Результат по шагам

| Шаг | Что сделано | Результат |
|---|---|---|
| 1. clone | клон ветки в пустую папку | ok, `e3016e2` |
| 2. venv | `python -m venv .venv` | Python 3.11.15 |
| 3. зависимости | `pip install -r requirements.txt` | ok, pandas 2.3.3, ~10 с |
| 4. backend | `pytest -q` (движок), `unittest` (интерфейс) | **358 passed** за 32 с; **21 тестов OK**, включая сверку каждой показанной комбинации с `src/kosmo` (метрики, девять проверок, PASS/FAIL в обоих сценариях) |
| 4. CLI | `kosmo calc … --scenario STRESS` | код выхода 0, c0 1 140, kcash 1,1837, все проверки ВЫПОЛНЕНО |
| 4. сервер | `app/server.py` | `GET /` → 200; `GET /api/dashboard` → selected `FIRE:A\|AGRI:B\|TRANS:B\|ENV:A`, c0 1 140.0, BASE и STRESS PASS, место 3 |
| 5–6. интерфейс, FINAL | открыть `#portfolio/overview` | подпись FINAL, «BASE: 9 из 9 ограничений выполнены», состав FIRE, AGRI, TRANS, ENV |
| 7. изменить портфель | «Конструктор»: AGRI → FLOOD, режим A, «Рассчитать» | пересчёт через сервер; BASE PASS (запас 63), STRESS FAIL |
| 8. увидеть FAIL | результат конструктора | «c0 = 1 237.0 > 1 180, превышение 57.0 млн руб.» |
| 9. включить STRESS | шапка → сценарий STRESS; вкладка «Ограничения» | пилюля «STRESS: 8 из 9 · c0 = 1 237.0 > 1 180, превышение 57.0 млн руб.»; строка c0 красная с тем же текстом; блок «BASE и STRESS рядом»: запас +63.0 / −57.0; «Вернуть FINAL» возвращает FINAL |
| 10. сравнить вариант | «Почему FINAL» → «Решение», V2; «Разложение балла» | 9 вариантов записки в таблице; против V2 FINAL выигрывает по 5 показателям (c0, OPEX, cash, K_cash, запас STRESS) и теряет по 2 (ценность, public core); балл 0,725 (3-е) против 0,555 (51-е) |

Шаги 5–10 пройдены скриптом Playwright в Chromium (клики по тем же
элементам, что и у эксперта) — ошибок JavaScript на странице нет. Тот же
маршрут руками — `docs/live-demo.md`.

## Замечания участнику 4 (расчётный слой)

1. **`results/` пишет только движок.** Кнопка «Экспорт results/» в
   интерфейсе вызывает `kosmo.export_bundle`, как и `python -m kosmo export`;
   произвольная комбинация из конструктора уходит в `results/variants/<id>/`
   и цифры записки не затирает. Тест `test_export_writes_the_engine_bundle`
   сравнивает выгрузку с `results/` без учёта переводов строк: `csv` пишет
   CRLF, а checkout под Linux хранит LF.
2. **Google Fonts.** Без доступа в интернет браузер один раз пишет в консоль
   `ERR_CONNECTION_RESET` на загрузке Montserrat и показывает системный
   шрифт; на работу интерфейса не влияет. Для снимков офлайн — `FONT_DIR`
   (см. `docs/mockup/README.md`).
3. **Снимки экранов.** `app/screenshot.mjs` требует глобально установленный
   `playwright` с Chromium (`npm i -g playwright && npx playwright install
   chromium`); в проверку эксперта это не входит.
4. Расхождений между цифрами интерфейса, CLI и `results/` не найдено:
   FINAL 1 140 / 313 / 1 289 / 370,5 / 1,184, запас 160/40, S2 190 / 0,607 / 123.
