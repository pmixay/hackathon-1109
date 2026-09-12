from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .calc import calculate, calculate_all_scenarios
from .case import Case, CaseFormatError, CaseIntegrityError, load_case
from .checks import format_value
from .custom_mode import load_custom_mode
from .enumeration import enumerate_portfolios, failure_counts, feasible_in, lot_frequency, lot_set_summary
from .export import (
    write_alternatives,
    write_enumeration,
    write_repairs,
    write_scenario_results,
    write_scored,
    write_sensitivity,
)
from .repairs import single_step_repairs
from .selection import load_selection_model, parameter_sensitivity, score_variants, weight_sensitivity
from .validation import InputError, SelectionError
from .variants import Variant, VariantStore, load_portfolio, load_variants

DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def open_case(root: Path) -> Case:
    case = load_case(root)
    custom = load_custom_mode(root / "config" / "custom_mode.json")
    if custom is not None:
        case = case.with_custom_mode(custom)
    return case


def parse_pairs(tokens) -> list:
    pairs = []
    problems = []
    for token in tokens:
        lot_id, separator, mode_id = token.partition(":")
        if not separator:
            problems.append(f"ожидается формат ЛОТ:РЕЖИМ, получено {token!r}")
            continue
        pairs.append((lot_id.strip(), mode_id.strip()))
    if problems:
        raise SelectionError(problems)
    return pairs


def resolve_variant(args, root: Path) -> Variant:
    if args.lots:
        return Variant(name=args.name or "ad-hoc", selection=tuple(parse_pairs(args.lots)))
    return load_portfolio(root / args.portfolio)


def table(rows: list, columns: list) -> str:
    cells = [[str(column) for column in columns]]
    for row in rows:
        cells.append([format_cell(row.get(column, "")) for column in columns])
    widths = [max(len(line[index]) for line in cells) for index in range(len(columns))]
    lines = []
    for position, line in enumerate(cells):
        lines.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(line)))
        if position == 0:
            lines.append("  ".join("-" * width for width in widths))
    return "\n".join(lines)


def format_cell(value) -> str:
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        return format_value(value)
    return str(value)


def print_result(result) -> None:
    metrics = result.metrics
    print(f"Сценарий: {result.scenario}")
    print("Портфель: " + ", ".join(f"{lot_id}/{mode_id}" for lot_id, mode_id in result.selection))
    print()
    print(table(
        [{
            "лот": row.lot_id, "режим": row.mode_id, "c0": row.c0, "opex": row.opex, "vpub": row.vpub,
            "cash": row.cash, "дефицит opex": row.opex_gap, "public core": row.public_core,
        } for row in result.lots],
        ["лот", "режим", "c0", "opex", "vpub", "cash", "дефицит opex", "public core"],
    ))
    print()
    print(table(
        [
            {"показатель": "c0, млн руб.", "значение": metrics.c0},
            {"показатель": "opex, млн руб./год", "значение": metrics.opex},
            {"показатель": "vpub, млн руб./год", "значение": metrics.vpub},
            {"показатель": "cash, млн руб./год", "значение": metrics.cash},
            {"показатель": "kcash = cash / opex", "значение": metrics.kcash},
            {"показатель": "дефицит opex, млн руб./год", "значение": metrics.opex_gap},
            {"показатель": "t_rep (среднее)", "значение": metrics.t_rep},
            {"показатель": "readiness (среднее)", "значение": metrics.readiness},
            {"показатель": "resilience (среднее)", "значение": metrics.resilience},
            {"показатель": "scale (среднее)", "значение": metrics.scale},
            {"показатель": "территориальные архетипы", "значение": metrics.territorial_archetypes},
            {"показатель": "capability groups", "значение": f"{metrics.capability_groups} ({', '.join(metrics.capability_set)})"},
            {"показатель": "лоты public core", "значение": metrics.public_core_lots},
        ],
        ["показатель", "значение"],
    ))
    print()
    print(table(
        [{
            "условие": check.label, "показатель": check.metric, "порог": f"{check.operator} {format_value(check.threshold)}",
            "факт": check.actual, "ед.": check.unit, "запас": check.margin, "статус": check.status.upper(),
        } for check in result.checks],
        ["условие", "показатель", "порог", "факт", "ед.", "запас", "статус"],
    ))
    print()
    print("Итог: " + ("все ограничения выполнены" if result.feasible else "нарушены: " + ", ".join(result.failed_checks)))
    if result.notes:
        print()
        print("Требует управленческого обоснования:")
        for note in result.notes:
            print(f"  - [{note.code}] {note.message}")


def cmd_calc(args, root: Path) -> int:
    case = open_case(root)
    variant = resolve_variant(args, root)
    scenarios = list(case.scenarios) if args.scenario == "all" else [args.scenario]
    results = {scenario_id: calculate(case, variant.selection, scenario_id) for scenario_id in scenarios}
    if args.json:
        print(json.dumps({scenario_id: result.to_dict() for scenario_id, result in results.items()}, ensure_ascii=False, indent=2))
    else:
        for index, result in enumerate(results.values()):
            if index:
                print("\n" + "=" * 72 + "\n")
            print_result(result)
    return 0 if all(result.feasible for result in results.values()) else 1


def cmd_compare(args, root: Path) -> int:
    case = open_case(root)
    variants = load_variants(root / args.alternatives)
    rows = []
    for variant in variants:
        for scenario_id, result in calculate_all_scenarios(case, variant.selection).items():
            metrics = result.metrics
            rows.append({
                "вариант": variant.name, "сценарий": scenario_id,
                "лоты": "+".join(lot_id for lot_id, _ in variant.selection),
                "режимы": "".join(mode_id for _, mode_id in variant.selection),
                "c0": metrics.c0, "opex": metrics.opex, "vpub": metrics.vpub, "cash": metrics.cash, "kcash": metrics.kcash,
                "t_rep": metrics.t_rep, "public core": metrics.public_core_lots,
                "допустим": result.feasible, "нарушено": ", ".join(result.failed_checks),
            })
    print(table(rows, ["вариант", "сценарий", "лоты", "режимы", "c0", "opex", "vpub", "cash", "kcash", "t_rep", "public core", "допустим", "нарушено"]))
    if args.weights:
        model = load_selection_model(root / args.weights)
        evaluated = {variant.name: calculate_all_scenarios(case, variant.selection) for variant in variants}
        scored = score_variants(evaluated, model)
        print()
        print(f"Модель выбора: {model.method}, допустимость по сценарию {model.feasibility_scenario}")
        print(table(
            [{"вариант": item.name, "ранг": item.rank if item.rank is not None else "-", "балл": item.score if item.score is not None else "-",
              **{criterion.key: item.values[criterion.key] for criterion in model.criteria}} for item in scored],
            ["вариант", "ранг", "балл"] + [criterion.key for criterion in model.criteria],
        ))
        print()
        print("Чувствительность к весам (±20%):")
        print(table(
            [{"критерий": item.key, "множитель": item.factor, "вес": item.weight, "лидер": item.leader or "-", "лидер сменился": item.leader_changed}
             for item in weight_sensitivity(evaluated, model)],
            ["критерий", "множитель", "вес", "лидер", "лидер сменился"],
        ))
    return 0


def cmd_enumerate(args, root: Path) -> int:
    case = open_case(root)
    portfolios = enumerate_portfolios(case)
    scenario_ids = list(case.scenarios)
    print(f"комбинаций: {len(portfolios)}")
    for scenario_id in scenario_ids:
        feasible = feasible_in(portfolios, scenario_id)
        print(f"{scenario_id}: допустимы {len(feasible)}; причины отсева: {dict(failure_counts(portfolios, scenario_id))}")
    print()
    print("Наборы лотов с допустимыми назначениями режимов (vpub max и c0 min — только среди допустимых):")
    summary = [row for row in lot_set_summary(portfolios, scenario_ids) if any(row[scenario_id] for scenario_id in scenario_ids)]
    columns = ["лоты"]
    for scenario_id in scenario_ids:
        columns += [scenario_id, f"vpub max {scenario_id}", f"c0 min {scenario_id}"]
    rows = []
    for row in summary:
        cells = {"лоты": "+".join(row["lots"])}
        for scenario_id in scenario_ids:
            cells[scenario_id] = row[scenario_id]
            cells[f"vpub max {scenario_id}"] = row[f"vpub_max_{scenario_id}"] if row[scenario_id] else "-"
            cells[f"c0 min {scenario_id}"] = row[f"c0_min_{scenario_id}"] if row[scenario_id] else "-"
        rows.append(cells)
    print(table(rows, columns))
    last = scenario_ids[-1]
    print()
    print(f"Частота лотов среди допустимых в {last}: {dict(lot_frequency(feasible_in(portfolios, last)).most_common())}")
    if args.out:
        path = write_enumeration(portfolios, scenario_ids, root / args.out)
        print(f"\nтаблица записана: {path}")
    return 0


def cmd_repairs(args, root: Path) -> int:
    case = open_case(root)
    variant = resolve_variant(args, root)
    original = calculate(case, variant.selection, args.scenario)
    print_result(original)
    repairs = single_step_repairs(case, variant.selection, args.scenario)
    print()
    if original.feasible:
        print(f"Портфель проходит {args.scenario}; варианты с одним изменением, также проходящие: {len(repairs)}")
    else:
        print(f"Варианты с одним изменением, проходящие {args.scenario}: {len(repairs)}")
    print(table(
        [{"изменение": repair.description, "лоты": "+".join(lot_id for lot_id, _ in repair.selection),
          "режимы": "".join(mode_id for _, mode_id in repair.selection), "c0": repair.metrics.c0,
          "Δ c0": repair.delta_c0, "vpub": repair.metrics.vpub, "Δ vpub": repair.delta_vpub, "kcash": repair.metrics.kcash,
          **{f"{scenario_id}": feasible for scenario_id, feasible in repair.feasible.items()}}
         for repair in repairs[: args.limit]],
        ["изменение", "лоты", "режимы", "c0", "Δ c0", "vpub", "Δ vpub", "kcash"] + list(case.scenarios),
    ))
    return 0


def cmd_export(args, root: Path) -> int:
    case = open_case(root)
    out = root / args.out
    portfolio = load_portfolio(root / args.portfolio)
    written = write_scenario_results(case, portfolio, out)
    for scenario_id, path in written.items():
        print(f"{scenario_id}: {path}")
    variants = load_variants(root / args.alternatives)
    if portfolio.name not in {variant.name for variant in variants}:
        variants.insert(0, portfolio)
    print(f"альтернативы: {write_alternatives(case, variants, out / 'alternatives.csv')}")
    evaluated = {variant.name: calculate_all_scenarios(case, variant.selection) for variant in variants}
    model = load_selection_model(root / args.weights)
    print(f"баллы модели выбора: {write_scored(score_variants(evaluated, model), out / 'scores.csv')}")
    print(f"чувствительность: {write_sensitivity(weight_sensitivity(evaluated, model), parameter_sensitivity(case, portfolio.selection), out / 'sensitivity.csv')}")
    portfolios = enumerate_portfolios(case)
    full_evaluated = {
        "|".join(f"{lot}:{mode}" for lot, mode in zip(item.lots, item.modes)): calculate_all_scenarios(case, tuple(zip(item.lots, item.modes)))
        for item in portfolios
        if item.feasible[model.feasibility_scenario]
    }
    print(f"полный ranking: {write_scored(score_variants(full_evaluated, model), out / 'ranking_full.csv')}")
    print(f"полная чувствительность: {write_sensitivity(weight_sensitivity(full_evaluated, model), parameter_sensitivity(case, portfolio.selection, parameters=('vpub', 'cash', 'opex', 'c0')), out / 'sensitivity_full.csv')}")
    for scenario_id in case.scenarios:
        repairs = single_step_repairs(case, portfolio.selection, scenario_id)
        print(f"варианты с одним изменением ({scenario_id}): {write_repairs(repairs, list(case.scenarios), out / f'repairs_{scenario_id.lower()}.csv')}")
    if not args.skip_enumeration:
        print(f"перебор: {write_enumeration(portfolios, list(case.scenarios), out / 'enumeration.csv')}")
    return 0


def cmd_variant(args, root: Path) -> int:
    case = open_case(root)
    store = VariantStore(root / args.directory)
    if args.action == "list":
        for name in store.names():
            print(name)
        return 0
    if args.action == "save":
        variant = Variant(name=args.name, selection=tuple(parse_pairs(args.lots)), note=args.note or "")
        path = store.save(case, variant)
        print(f"сохранено: {path}")
        return 0
    if args.action == "check":
        snapshot, fresh, identical = store.recompute(case, args.name)
        print(f"вариант {args.name}: пересчёт " + ("совпадает с сохранённым" if identical else "ОТЛИЧАЕТСЯ от сохранённого"))
        if snapshot["case"]["checksums"] != fresh["case"]["checksums"]:
            print("контрольные суммы исходных файлов изменились")
        return 0 if identical else 1
    raise SystemExit(f"неизвестное действие {args.action!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kosmo", description="Расчётный слой кейса «Космос как инфраструктура»")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="корень репозитория с data/, config/, results/")
    commands = parser.add_subparsers(dest="command", required=True)

    calc = commands.add_parser("calc", help="посчитать портфель и проверить ограничения")
    calc.add_argument("--portfolio", default="config/portfolio.json")
    calc.add_argument("--lots", nargs="*", metavar="ЛОТ:РЕЖИМ", help="портфель прямо из командной строки, например FIRE:A AGRI:A TRANS:A ENV:A")
    calc.add_argument("--name", default=None)
    calc.add_argument("--scenario", default="all", help="BASE, STRESS или all")
    calc.add_argument("--json", action="store_true")
    calc.set_defaults(handler=cmd_calc)

    compare = commands.add_parser("compare", help="сравнить сохранённые альтернативы в обоих сценариях")
    compare.add_argument("--alternatives", default="config/alternatives.json")
    compare.add_argument("--weights", default=None, help="config/weights.json для расчёта баллов модели выбора")
    compare.set_defaults(handler=cmd_compare)

    enumerate_cmd = commands.add_parser("enumerate", help="перебрать все комбинации лотов и режимов")
    enumerate_cmd.add_argument("--out", default=None, help="куда записать CSV, например results/enumeration.csv")
    enumerate_cmd.set_defaults(handler=cmd_enumerate)

    repairs = commands.add_parser("repairs", help="показать варианты с одним изменением, проходящие сценарий")
    repairs.add_argument("--portfolio", default="config/portfolio.json")
    repairs.add_argument("--lots", nargs="*", metavar="ЛОТ:РЕЖИМ")
    repairs.add_argument("--name", default=None)
    repairs.add_argument("--scenario", default="STRESS")
    repairs.add_argument("--limit", type=int, default=15)
    repairs.set_defaults(handler=cmd_repairs)

    export = commands.add_parser("export", help="выгрузить results/ для записки и слайдов")
    export.add_argument("--portfolio", default="config/portfolio.json")
    export.add_argument("--alternatives", default="config/alternatives.json")
    export.add_argument("--weights", default="config/weights.json")
    export.add_argument("--out", default="results")
    export.add_argument("--skip-enumeration", action="store_true")
    export.set_defaults(handler=cmd_export)

    variant = commands.add_parser("variant", help="сохранить, перечислить или перепроверить сохранённый вариант")
    variant.add_argument("action", choices=["save", "check", "list"])
    variant.add_argument("name", nargs="?")
    variant.add_argument("--lots", nargs="*", metavar="ЛОТ:РЕЖИМ")
    variant.add_argument("--note", default="")
    variant.add_argument("--directory", default="variants")
    variant.set_defaults(handler=cmd_variant)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        return args.handler(args, root)
    except InputError as error:
        for problem in error.problems:
            print(f"ошибка входа: {problem}", file=sys.stderr)
        return 2
    except CaseIntegrityError as error:
        print(f"нарушена целостность исходных данных: {error}", file=sys.stderr)
        return 3
    except CaseFormatError as error:
        print(f"исходные файлы кейса не читаются: {error}", file=sys.stderr)
        return 3
    except FileNotFoundError as error:
        print(f"файл не найден: {error}", file=sys.stderr)
        return 4
    except FileExistsError as error:
        print(f"конфликт имён: {error}", file=sys.stderr)
        return 4
    except json.JSONDecodeError as error:
        print(f"некорректный JSON: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
