from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .calc import calculate_all_scenarios
from .case import Case
from .custom_mode import custom_mode_to_dict, parse_custom_mode
from .validation import SelectionError, normalize_selection

FORMAT_VERSION = 1


@dataclass(frozen=True)
class Variant:
    name: str
    selection: tuple
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "selection": [{"lot_id": lot_id, "mode_id": mode_id} for lot_id, mode_id in self.selection],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, raw) -> Variant:
        if not isinstance(raw, dict):
            raise SelectionError([f"описание варианта должно быть объектом JSON с полями name и selection, получено {type(raw).__name__}"])
        name = str(raw.get("name") or "").strip()
        if not name:
            raise SelectionError(["у варианта должно быть имя (name)"])
        return cls(name=name, selection=normalize_selection(raw.get("selection") or []), note=str(raw.get("note") or ""))


def load_variants(path) -> list:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw.get("variants") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise SelectionError([f"{Path(path).name}: ожидается список вариантов в поле variants"])
    return [Variant.from_dict(item) for item in items]


def load_portfolio(path) -> Variant:
    return Variant.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def used_custom_modes(case: Case, selection) -> list:
    used = {mode_id for _, mode_id in selection}
    return [mode for mode_id, mode in case.custom_modes.items() if mode_id in used]


def variant_snapshot(case: Case, variant: Variant) -> dict:
    results = calculate_all_scenarios(case, variant.selection)
    return {
        "format_version": FORMAT_VERSION,
        "case": {"case_id": case.case_id, "version": case.version, "checksums": case.checksums},
        "variant": variant.to_dict(),
        "custom_modes": [custom_mode_to_dict(mode) for mode in used_custom_modes(case, variant.selection)],
        "results": {scenario_id: result.to_dict() for scenario_id, result in results.items()},
    }


def slug(name: str) -> str:
    text = re.sub(r"[^\w]+", "-", name, flags=re.UNICODE).strip("-").lower()
    return text or "variant"


class VariantStore:
    def __init__(self, directory):
        self.directory = Path(directory)

    def path_for(self, name: str) -> Path:
        return self.directory / f"{slug(name)}.json"

    def names(self) -> list:
        return [read_snapshot(path)["variant"]["name"] for path in sorted(self.directory.glob("*.json"))]

    def save(self, case: Case, variant: Variant) -> Path:
        snapshot = variant_snapshot(case, variant)
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(variant.name)
        if path.exists():
            existing = read_snapshot(path)["variant"]["name"]
            if existing != variant.name:
                raise FileExistsError(f"{path.name} already holds variant {existing!r}; pick a different name for {variant.name!r}")
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, name: str) -> dict:
        path = self.path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"variant {name!r} is not saved at {path}")
        return read_snapshot(path)

    def case_for(self, case: Case, snapshot: dict) -> Case:
        restored = case
        for raw in snapshot.get("custom_modes", []):
            restored = restored.with_custom_mode(parse_custom_mode(raw))
        return restored

    def recompute(self, case: Case, name: str) -> tuple:
        snapshot = self.load(name)
        variant = Variant.from_dict(snapshot["variant"])
        fresh = variant_snapshot(self.case_for(case, snapshot), variant)
        return snapshot, fresh, snapshot["results"] == fresh["results"]


def read_snapshot(path: Path) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("variant"), dict) or not snapshot["variant"].get("name"):
        raise SelectionError([f"{path.name}: это не сохранённый вариант (нет поля variant.name)"])
    version = snapshot.get("format_version")
    if version != FORMAT_VERSION:
        raise SelectionError([f"{path.name}: формат снимка {version!r} не поддерживается, ожидается {FORMAT_VERSION}"])
    if not isinstance(snapshot.get("results"), dict):
        raise SelectionError([f"{path.name}: в снимке нет результатов расчёта"])
    return snapshot
