"""Загрузка набора данных в формате организаторов: проверка, сохранение, активация.

Интерфейс (вкладка «Данные») присылает тексты трёх файлов — lots.csv,
access_modes.csv, case_config.json. Здесь они проверяются на структуру,
сохраняются в app/data/uploads/<метка времени>/ в раскладке организаторов
(data/*.csv, config/case_config.json) и становятся активным набором.

`apply_dataset` переключает активный корень; движок kosmo читает новый набор
через ту же `load_case`, что и файлы организаторов (без проверки контрольных
сумм — в meta.engine.verified будет false).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import shutil
from pathlib import Path

from . import evaluate as ev

APP = Path(__file__).resolve().parents[1]
DATA_DIR = APP / "data"
UPLOADS = DATA_DIR / "uploads"
ACTIVE = DATA_DIR / "active.json"

FILES = {
    "lots.csv": "data/lots.csv",
    "access_modes.csv": "data/access_modes.csv",
    "case_config.json": "config/case_config.json",
}
LOT_COLUMNS = [
    "lot_id", "territorial_archetype", "service", "capability_groups", "c0_mrub", "opex_mrub_per_year",
    "anchor_cash_mrub_per_year", "commercial_cash_mrub_per_year", "vpub_mrub_per_year", "t_rep",
    "readiness_1_5", "resilience_1_5", "scale_1_5", "federal",
]
LOT_NUMERIC = LOT_COLUMNS[4:13]
MODE_COLUMNS = ["mode_id", "k_c0", "k_opex", "k_vpub", "k_anchor", "k_commercial", "public_core"]
MODE_NUMERIC = MODE_COLUMNS[1:6]
CONFIG_COMMON = [
    "selected_lots_exactly", "min_territorial_archetypes", "min_capability_groups", "min_public_core_lots",
    "opex_max_mrub_per_year", "vpub_min_mrub_per_year", "kcash_min", "t_rep_min",
]
BOOL = {"true", "false"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _csv_rows(text: str):
    rows = list(csv.DictReader(io.StringIO(text)))
    header = list(rows[0].keys()) if rows else next(csv.reader(io.StringIO(text)), [])
    return header, rows


def validate_lots(text: str) -> dict:
    errors, warnings = [], []
    header, rows = _csv_rows(text)
    missing = [c for c in LOT_COLUMNS if c not in header]
    if missing:
        errors.append(f"нет столбцов: {', '.join(missing)}")
    extra = [c for c in header if c not in LOT_COLUMNS]
    if extra:
        warnings.append(f"лишние столбцы игнорируются: {', '.join(extra)}")
    if not rows:
        errors.append("нет строк с лотами")
    ids = [r.get("lot_id", "") for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        errors.append(f"повторяющиеся lot_id: {', '.join(dup)}")
    for r in rows:
        for c in LOT_NUMERIC:
            if c in header and not _is_number(r.get(c)):
                errors.append(f"{r.get('lot_id', '?')}: {c} не число ({r.get(c)!r})")
        if "federal" in header and str(r.get("federal", "")).lower() not in BOOL:
            errors.append(f"{r.get('lot_id', '?')}: federal должен быть true/false")
    if len(rows) < 4:
        errors.append(f"лотов {len(rows)}, портфель требует 4")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": {"rows": len(rows), "columns": len(header), "lots": ids}}


def validate_modes(text: str) -> dict:
    errors, warnings = [], []
    header, rows = _csv_rows(text)
    missing = [c for c in MODE_COLUMNS if c not in header]
    if missing:
        errors.append(f"нет столбцов: {', '.join(missing)}")
    if not rows:
        errors.append("нет строк с режимами")
    for r in rows:
        for c in MODE_NUMERIC:
            if c in header and not _is_number(r.get(c)):
                errors.append(f"режим {r.get('mode_id', '?')}: {c} не число")
        if "public_core" in header and str(r.get("public_core", "")).lower() not in BOOL:
            errors.append(f"режим {r.get('mode_id', '?')}: public_core должен быть true/false")
    if rows and not any(str(r.get("public_core", "")).lower() == "true" for r in rows):
        warnings.append("ни один режим не даёт public core — условие «≥ 2 лота с public core» невыполнимо")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": {"rows": len(rows), "modes": [r.get("mode_id") for r in rows]}}


def validate_config(text: str) -> dict:
    errors, warnings = [], []
    try:
        cfg = json.loads(text)
    except json.JSONDecodeError as e:
        return {"ok": False, "errors": [f"не JSON: {e.msg} (строка {e.lineno})"], "warnings": [], "summary": {}}
    common = cfg.get("constraints_common")
    if not isinstance(common, dict):
        errors.append("нет объекта constraints_common")
    else:
        for k in CONFIG_COMMON:
            if k not in common:
                errors.append(f"constraints_common: нет {k}")
            elif not _is_number(common[k]):
                errors.append(f"constraints_common.{k} не число")
    scen = cfg.get("scenarios")
    if not isinstance(scen, dict) or not scen:
        errors.append("нет объекта scenarios")
    else:
        for name, s in scen.items():
            if not isinstance(s, dict) or not _is_number(s.get("c0_max_mrub")):
                errors.append(f"scenarios.{name}: нет числового c0_max_mrub")
        if "BASE" not in scen or "STRESS" not in scen:  # модель выбора и экраны построены на этих двух сценариях
            errors.append("нужны сценарии BASE и STRESS — на них построены расчёт и экраны")
    if "case_version" not in cfg:
        warnings.append("нет case_version")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "summary": {"case_version": cfg.get("case_version"), "scenarios": list(scen) if isinstance(scen, dict) else [], "constraints": len(common) if isinstance(common, dict) else 0}}


VALIDATORS = {"lots.csv": validate_lots, "access_modes.csv": validate_modes, "case_config.json": validate_config}


def validate(files: dict[str, str]) -> dict:
    report = {}
    for name, fn in VALIDATORS.items():
        if name in files and files[name] is not None:
            report[name] = fn(files[name])
            report[name]["sha"] = sha(files[name])
        else:
            report[name] = {"ok": True, "errors": [], "warnings": ["файл не передан — остаётся текущий"], "summary": {}, "sha": None, "kept": True}
    return report


def store(files: dict[str, str], base_root: Path | None = None) -> Path:
    """Сохранить набор в раскладке организаторов; непереданные файлы взять из текущего активного набора."""
    base_root = base_root or active_root()
    root = UPLOADS / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for name, rel in FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if files.get(name) is not None:
            target.write_text(files[name], encoding="utf-8")
        else:
            shutil.copyfile(base_root / rel, target)
    return root


def active_root() -> Path:
    if ACTIVE.exists():
        try:
            root = Path(json.loads(ACTIVE.read_text(encoding="utf-8"))["root"])
            if (root / "data" / "lots.csv").exists():
                return root
        except (json.JSONDecodeError, KeyError):
            pass
    return ev.CASE_DIR


def apply_dataset(root: Path) -> None:
    """Сделать набор активным. Точка интеграции роли A (см. docstring модуля)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(json.dumps({"root": str(root), "activated_at": dt.datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False), encoding="utf-8")


def reset() -> None:
    if ACTIVE.exists():
        ACTIVE.unlink()


def describe(root: Path | None = None) -> dict:
    root = root or active_root()
    shown = root.relative_to(ev.REPO).as_posix() if root.is_relative_to(ev.REPO) else str(root)
    out = {"root": shown or ".", "source": "организаторы" if root == ev.CASE_DIR else "загружено", "files": {}}
    if ACTIVE.exists() and root != ev.CASE_DIR:
        try:
            out["activated_at"] = json.loads(ACTIVE.read_text(encoding="utf-8")).get("activated_at")
        except json.JSONDecodeError:
            pass
    for name, rel in FILES.items():
        p = root / rel
        if p.exists():
            text = p.read_text(encoding="utf-8")
            rep = VALIDATORS[name](text)
            out["files"][name] = {"sha": sha(text), "bytes": len(text.encode("utf-8")), "summary": rep["summary"], "ok": rep["ok"]}
        else:
            out["files"][name] = {"missing": True}
    cfg = out["files"].get("case_config.json", {}).get("summary", {})
    out["case_version"] = cfg.get("case_version")
    return out
