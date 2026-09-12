from __future__ import annotations

from dataclasses import dataclass

from .case import Case
from .checks import TOLERANCE
from .custom_mode import out_of_range_coefficients

TIGHT_MARGIN_SHARE = 0.05


@dataclass(frozen=True)
class Note:
    code: str
    message: str
    lots: tuple


def management_notes(case: Case, rows, metrics, checks) -> tuple:
    notes = []
    notes.append(Note(
        "c0_funding",
        f"Источник покрытия стартовых затрат {metrics.c0:.1f} млн руб. кейсом не задан: "
        "нужно назвать плательщика (бюджет заказчика, федеральное софинансирование, ГЧП) и механизм закупки",
        tuple(row.lot_id for row in rows),
    ))
    if metrics.opex_gap > TOLERANCE:
        notes.append(Note(
            "opex_gap",
            f"Денежные поступления покрывают {metrics.kcash:.0%} годового OPEX; "
            f"непокрытые {metrics.opex_gap:.1f} млн руб./год требуют названного источника (субсидия, бюджетное обязательство)",
            tuple(row.lot_id for row in rows if row.opex_gap > TOLERANCE),
        ))
    anchor_lots = tuple(row.lot_id for row in rows if row.anchor_cash > TOLERANCE)
    if anchor_lots:
        notes.append(Note(
            "anchor_payer",
            f"Плательщик якорной компоненты ({metrics.anchor_cash:.1f} млн руб./год) кейсом не назван: "
            "назначить заказчика и договорную форму по каждому лоту",
            anchor_lots,
        ))
    federal_lots = tuple(row.lot_id for row in rows if row.federal)
    if federal_lots:
        notes.append(Note(
            "federal_lot",
            "Федеральный лот не входит в счётчик территориальных архетипов; "
            "нужен федеральный заказчик и схема софинансирования",
            federal_lots,
        ))
    for mode_id, mode in case.custom_modes.items():
        mode_lots = tuple(row.lot_id for row in rows if row.mode_id == mode_id)
        if not mode_lots:
            continue
        coefficients = ", ".join(f"{key}={getattr(mode, key)}" for key in ("k_c0", "k_opex", "k_vpub", "k_anchor", "k_commercial"))
        notes.append(Note(
            "custom_mode",
            f"Режим {mode_id} — допущение команды ({coefficients}); обоснование: {mode.rationale}",
            mode_lots,
        ))
        for key, value, low, high in out_of_range_coefficients(mode, case.canonical_modes):
            notes.append(Note(
                "custom_mode_range",
                f"Коэффициент {key}={value} режима {mode_id} вне диапазона канонических режимов [{low}; {high}] — требуется отдельное обоснование",
                mode_lots,
            ))
        if mode.public_core:
            notes.append(Note(
                "custom_mode_public_core",
                f"Режим {mode_id} засчитан как public core: базовый общественно значимый слой сервиса должен оставаться доступным без дискриминации",
                mode_lots,
            ))
    for check in checks:
        if check.code != "c0_limit" or not check.passed:
            continue
        share = check.margin / check.threshold if check.threshold else 0.0
        if share < TIGHT_MARGIN_SHARE:
            notes.append(Note(
                "c0_tight_margin",
                f"Запас по лимиту стартовых затрат в сценарии {check.scope}: {check.margin:.1f} млн руб. ({share:.1%}); "
                "портфель чувствителен к уточнению стоимости лотов",
                tuple(row.lot_id for row in rows),
            ))
    return tuple(notes)
