from __future__ import annotations

import json
import math
from pathlib import Path

from .case import AccessMode
from .validation import InputError

DEFAULT_CUSTOM_MODE_ID = "D"
CANONICAL_MODE_IDS = ("A", "B", "C")
COEFFICIENTS = ("k_c0", "k_opex", "k_vpub", "k_anchor", "k_commercial")
STRICTLY_POSITIVE = ("k_c0", "k_opex", "k_vpub")


class CustomModeError(InputError):
    kind = "invalid_custom_mode"


def parse_custom_mode(raw) -> AccessMode:
    if not isinstance(raw, dict):
        raise CustomModeError([f"описание режима должно быть объектом JSON, получено {type(raw).__name__}"])
    problems = []
    mode_id = str(raw.get("mode_id", DEFAULT_CUSTOM_MODE_ID)).strip()
    if not mode_id:
        problems.append("mode_id: пустой идентификатор режима")
    elif mode_id in CANONICAL_MODE_IDS:
        problems.append(f"mode_id: {mode_id} занят каноническим режимом, используйте другой идентификатор")
    values = {}
    for key in COEFFICIENTS:
        value = raw.get(key)
        if value is None:
            problems.append(f"{key}: коэффициент не задан")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(f"{key}: ожидается конечное число, получено {value!r}")
            continue
        if key in STRICTLY_POSITIVE and value <= 0:
            problems.append(f"{key}: коэффициент должен быть больше нуля, получено {value}")
            continue
        if value < 0:
            problems.append(f"{key}: коэффициент не может быть отрицательным, получено {value}")
            continue
        values[key] = float(value)
    public_core = raw.get("public_core")
    if not isinstance(public_core, bool):
        problems.append("public_core: ожидается true или false")
    rationale = str(raw.get("rationale") or "").strip()
    if not rationale:
        problems.append("rationale: обоснование пользовательского режима обязательно")
    if problems:
        raise CustomModeError(problems)
    return AccessMode(
        mode_id=mode_id,
        k_c0=values["k_c0"],
        k_opex=values["k_opex"],
        k_vpub=values["k_vpub"],
        k_anchor=values["k_anchor"],
        k_commercial=values["k_commercial"],
        public_core=public_core,
        custom=True,
        name=str(raw.get("name") or "").strip(),
        rationale=rationale,
    )


def load_custom_mode(path) -> AccessMode | None:
    path = Path(path)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and not is_enabled(raw.get("enabled", True)):
        return None
    return parse_custom_mode(raw)


def is_enabled(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "")
    return bool(value)


def custom_mode_to_dict(mode: AccessMode) -> dict:
    return {
        "mode_id": mode.mode_id,
        "name": mode.name,
        "k_c0": mode.k_c0,
        "k_opex": mode.k_opex,
        "k_vpub": mode.k_vpub,
        "k_anchor": mode.k_anchor,
        "k_commercial": mode.k_commercial,
        "public_core": mode.public_core,
        "rationale": mode.rationale,
    }


def coefficient_ranges(canonical_modes: dict) -> dict:
    ranges = {}
    for key in COEFFICIENTS:
        values = [getattr(mode, key) for mode in canonical_modes.values()]
        ranges[key] = (min(values), max(values))
    return ranges


def out_of_range_coefficients(mode: AccessMode, canonical_modes: dict) -> list:
    outliers = []
    for key, (low, high) in coefficient_ranges(canonical_modes).items():
        value = getattr(mode, key)
        if value < low or value > high:
            outliers.append((key, value, low, high))
    return outliers
