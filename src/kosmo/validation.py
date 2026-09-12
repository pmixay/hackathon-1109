from __future__ import annotations

from .case import Case


class InputError(ValueError):
    kind = "invalid_input"

    def __init__(self, problems):
        self.problems = tuple(problems)
        super().__init__("; ".join(self.problems))

    def to_dict(self) -> dict:
        return {"error": self.kind, "problems": list(self.problems)}


class SelectionError(InputError):
    kind = "invalid_selection"


def normalize_selection(selection) -> tuple:
    if isinstance(selection, (str, bytes, dict)) or not hasattr(selection, "__iter__"):
        raise SelectionError([f"портфель должен быть списком пар (лот, режим), получено {type(selection).__name__}"])
    pairs = []
    problems = []
    for position, item in enumerate(selection, start=1):
        if isinstance(item, dict):
            lot_id, mode_id = item.get("lot_id"), item.get("mode_id")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            lot_id, mode_id = item
        else:
            problems.append(f"позиция {position}: ожидается пара (лот, режим), получено {item!r}")
            continue
        pairs.append((clean_id(lot_id), clean_id(mode_id)))
    if problems:
        raise SelectionError(problems)
    return tuple(pairs)


def clean_id(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def validate_selection(case: Case, pairs, scenario_id: str | None = None) -> list:
    problems = []
    if scenario_id is not None and scenario_id not in case.scenarios:
        problems.append(f"неизвестный сценарий {scenario_id!r}, доступны: {', '.join(case.scenarios)}")
    expected = case.constraints.selected_lots_exactly
    if len(pairs) != expected:
        problems.append(f"в портфеле должно быть ровно {expected} лота, передано {len(pairs)}")
    seen = set()
    for position, (lot_id, mode_id) in enumerate(pairs, start=1):
        if not lot_id:
            problems.append(f"позиция {position}: лот не выбран")
        elif lot_id not in case.lots:
            problems.append(f"позиция {position}: неизвестный лот {lot_id!r}")
        elif lot_id in seen:
            problems.append(f"позиция {position}: лот {lot_id} выбран повторно")
        seen.add(lot_id)
        if not mode_id:
            problems.append(f"позиция {position}: режим не выбран")
        elif mode_id not in case.modes:
            problems.append(f"позиция {position}: неизвестный режим {mode_id!r}, доступны: {', '.join(case.modes)}")
    return problems


def require_valid_selection(case: Case, selection, scenario_id: str | None = None) -> tuple:
    pairs = normalize_selection(selection)
    problems = validate_selection(case, pairs, scenario_id)
    if problems:
        raise SelectionError(problems)
    return pairs
