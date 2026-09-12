from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

CAPABILITY_ALIASES = {"PNT": "PNT/InSAR", "InSAR": "PNT/InSAR", "PNT/InSAR": "PNT/InSAR"}

SOURCE_FILES = (
    "data/lots.csv",
    "data/access_modes.csv",
    "config/case_config.json",
    "src/case_core.py",
)

CHECKSUMS_FILE = "config/case_checksums.json"


class CaseIntegrityError(Exception):
    pass


class CaseFormatError(ValueError):
    pass


@dataclass(frozen=True)
class Lot:
    lot_id: str
    territorial_archetype: str
    service: str
    capability_groups: tuple
    c0: float
    opex: float
    anchor_cash: float
    commercial_cash: float
    vpub: float
    t_rep: float
    readiness: float
    resilience: float
    scale: float
    federal: bool

    @property
    def capability_set(self) -> frozenset:
        return frozenset(CAPABILITY_ALIASES.get(token, token) for token in self.capability_groups)


@dataclass(frozen=True)
class AccessMode:
    mode_id: str
    k_c0: float
    k_opex: float
    k_vpub: float
    k_anchor: float
    k_commercial: float
    public_core: bool
    custom: bool = False
    name: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class Constraints:
    selected_lots_exactly: int
    min_territorial_archetypes: int
    min_capability_groups: int
    min_public_core_lots: int
    opex_max: float
    vpub_min: float
    kcash_min: float
    t_rep_min: float


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    c0_max: float


@dataclass(frozen=True)
class Case:
    case_id: str
    version: str
    lots: dict
    modes: dict
    constraints: Constraints
    scenarios: dict
    checksums: dict
    verified: bool

    @property
    def canonical_modes(self) -> dict:
        return {mode_id: mode for mode_id, mode in self.modes.items() if not mode.custom}

    @property
    def custom_modes(self) -> dict:
        return {mode_id: mode for mode_id, mode in self.modes.items() if mode.custom}

    def with_custom_mode(self, mode: AccessMode) -> Case:
        if not mode.custom:
            raise ValueError(f"mode {mode.mode_id} is not marked as custom")
        existing = self.modes.get(mode.mode_id)
        if existing is not None and not existing.custom:
            raise ValueError(f"mode {mode.mode_id} is canonical and cannot be overridden")
        return replace(self, modes={**self.modes, mode.mode_id: mode})


def parse_bool(value, field: str, row_id: str) -> bool:
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise CaseFormatError(f"{row_id}.{field}: expected a boolean, got {value!r}")


def parse_number(value, field: str, row_id: str) -> float:
    if isinstance(value, bool):
        raise CaseFormatError(f"{row_id}.{field}: expected a number, got {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise CaseFormatError(f"{row_id}.{field}: expected a number, got {value!r}") from None
    if not math.isfinite(number):
        raise CaseFormatError(f"{row_id}.{field}: value must be finite, got {value!r}")
    return number


def parse_int(value, field: str, row_id: str) -> int:
    number = parse_number(value, field, row_id)
    if number != int(number):
        raise CaseFormatError(f"{row_id}.{field}: expected an integer, got {value!r}")
    return int(number)


def split_capabilities(raw: str) -> tuple:
    return tuple(token.strip() for token in str(raw).split(";") if token.strip())


LOT_COLUMNS = (
    "lot_id", "territorial_archetype", "service", "capability_groups", "c0_mrub", "opex_mrub_per_year",
    "anchor_cash_mrub_per_year", "commercial_cash_mrub_per_year", "vpub_mrub_per_year",
    "t_rep", "readiness_1_5", "resilience_1_5", "scale_1_5", "federal",
)

MODE_COLUMNS = ("mode_id", "k_c0", "k_opex", "k_vpub", "k_anchor", "k_commercial", "public_core")


def read_rows(path: Path, columns: tuple) -> list:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in reader.fieldnames or []]
        missing = [name for name in columns if name not in header]
        if missing:
            raise CaseFormatError(f"{path.name}: missing columns {', '.join(missing)}")
        return [{key.strip(): value or "" for key, value in row.items() if key is not None} for row in reader]


def read_lots(path: Path) -> dict:
    lots = {}
    for row in read_rows(path, LOT_COLUMNS):
        lot_id = row["lot_id"].strip()
        if not lot_id:
            raise CaseFormatError(f"{path.name}: empty lot_id")
        if lot_id in lots:
            raise CaseFormatError(f"{path.name}: duplicate lot_id {lot_id}")
        lots[lot_id] = Lot(
            lot_id=lot_id,
            territorial_archetype=row["territorial_archetype"].strip(),
            service=row["service"].strip(),
            capability_groups=split_capabilities(row["capability_groups"]),
            c0=parse_number(row["c0_mrub"], "c0_mrub", lot_id),
            opex=parse_number(row["opex_mrub_per_year"], "opex_mrub_per_year", lot_id),
            anchor_cash=parse_number(row["anchor_cash_mrub_per_year"], "anchor_cash_mrub_per_year", lot_id),
            commercial_cash=parse_number(row["commercial_cash_mrub_per_year"], "commercial_cash_mrub_per_year", lot_id),
            vpub=parse_number(row["vpub_mrub_per_year"], "vpub_mrub_per_year", lot_id),
            t_rep=parse_number(row["t_rep"], "t_rep", lot_id),
            readiness=parse_number(row["readiness_1_5"], "readiness_1_5", lot_id),
            resilience=parse_number(row["resilience_1_5"], "resilience_1_5", lot_id),
            scale=parse_number(row["scale_1_5"], "scale_1_5", lot_id),
            federal=parse_bool(row["federal"], "federal", lot_id),
        )
    if not lots:
        raise CaseFormatError(f"{path.name}: no lots found")
    return lots


def read_modes(path: Path) -> dict:
    modes = {}
    for row in read_rows(path, MODE_COLUMNS):
        mode_id = row["mode_id"].strip()
        if not mode_id:
            raise CaseFormatError(f"{path.name}: empty mode_id")
        if mode_id in modes:
            raise CaseFormatError(f"{path.name}: duplicate mode_id {mode_id}")
        modes[mode_id] = AccessMode(
            mode_id=mode_id,
            k_c0=parse_number(row["k_c0"], "k_c0", mode_id),
            k_opex=parse_number(row["k_opex"], "k_opex", mode_id),
            k_vpub=parse_number(row["k_vpub"], "k_vpub", mode_id),
            k_anchor=parse_number(row["k_anchor"], "k_anchor", mode_id),
            k_commercial=parse_number(row["k_commercial"], "k_commercial", mode_id),
            public_core=parse_bool(row["public_core"], "public_core", mode_id),
        )
    if not modes:
        raise CaseFormatError(f"{path.name}: no access modes found")
    return modes


def read_config(path: Path) -> tuple:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        return parse_config(raw, path.name)
    except KeyError as error:
        raise CaseFormatError(f"{path.name}: missing key {error.args[0]!r}") from None
    except (TypeError, AttributeError):
        raise CaseFormatError(f"{path.name}: unexpected structure") from None


def parse_config(raw: dict, source: str) -> tuple:
    common = raw["constraints_common"]
    constraints = Constraints(
        selected_lots_exactly=parse_int(common["selected_lots_exactly"], "selected_lots_exactly", "constraints"),
        min_territorial_archetypes=parse_int(common["min_territorial_archetypes"], "min_territorial_archetypes", "constraints"),
        min_capability_groups=parse_int(common["min_capability_groups"], "min_capability_groups", "constraints"),
        min_public_core_lots=parse_int(common["min_public_core_lots"], "min_public_core_lots", "constraints"),
        opex_max=parse_number(common["opex_max_mrub_per_year"], "opex_max_mrub_per_year", "constraints"),
        vpub_min=parse_number(common["vpub_min_mrub_per_year"], "vpub_min_mrub_per_year", "constraints"),
        kcash_min=parse_number(common["kcash_min"], "kcash_min", "constraints"),
        t_rep_min=parse_number(common["t_rep_min"], "t_rep_min", "constraints"),
    )
    scenarios = {}
    for scenario_id, values in raw["scenarios"].items():
        scenarios[scenario_id] = Scenario(
            scenario_id=scenario_id,
            c0_max=parse_number(values["c0_max_mrub"], "c0_max_mrub", scenario_id),
        )
    if not scenarios:
        raise CaseFormatError(f"{source}: no scenarios defined")
    return str(raw["case_id"]), str(raw["case_version"]), constraints, scenarios


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_checksums(root: Path) -> dict:
    return {name: file_sha256(root / name) for name in SOURCE_FILES if (root / name).exists()}


def verify_checksums(root: Path, actual: dict) -> bool:
    expected_path = root / CHECKSUMS_FILE
    if not expected_path.exists():
        return False
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if not isinstance(expected, dict):
        raise CaseIntegrityError(f"{CHECKSUMS_FILE} must map file names to sha256 strings")
    unlisted = sorted(set(SOURCE_FILES) - set(expected))
    if unlisted:
        raise CaseIntegrityError(f"{CHECKSUMS_FILE} does not cover: " + ", ".join(unlisted))
    missing = sorted(name for name in expected if name not in actual)
    if missing:
        raise CaseIntegrityError("fixed source files are missing: " + ", ".join(missing))
    changed = sorted(name for name in expected if actual[name] != expected[name])
    if changed:
        raise CaseIntegrityError("source case files differ from the fixed version: " + ", ".join(changed))
    return True


def load_case(root) -> Case:
    root = Path(root)
    checksums = compute_checksums(root)
    verified = verify_checksums(root, checksums)
    case_id, version, constraints, scenarios = read_config(root / "config" / "case_config.json")
    return Case(
        case_id=case_id,
        version=version,
        lots=read_lots(root / "data" / "lots.csv"),
        modes=read_modes(root / "data" / "access_modes.csv"),
        constraints=constraints,
        scenarios=scenarios,
        checksums=checksums,
        verified=verified,
    )
