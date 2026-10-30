"""Versioned direct-cost model; this is not an event probability forecast.

All intermediate arithmetic is exact Decimal arithmetic in an isolated context.
Each displayed result rounds once to two decimals with ROUND_HALF_UP. Totals use
unrounded monthly values, so they may differ from displayed monthly cost × months.
Only plain decimal strings, Decimal objects and integers are accepted as numbers;
floats are rejected to avoid carrying binary floating-point approximation.
"""

import re
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext

ENGINE_VERSION = "direct-cost-v1.0.0"
ASSUMPTIONS = (
    "Учебная модель прямого воздействия на затраты; не AI-прогноз и не оценка вероятности события.",
    "Источник параметров: пользователь. Начальные значения иллюстративные.",
    "Объёмы, доля затронутых затрат и удорожание постоянны на всём горизонте.",
    "Валютные изменения, реакция спроса, запасы, налоги и вторичные эффекты отдельно не моделируются.",
    "Дополнительные затраты = месячные затраты × доля / 100 × удорожание / 100 × число месяцев.",
    "Итоги рассчитаны без промежуточного округления; вывод округляется до двух знаков по ROUND_HALF_UP.",
)

_FIELDS = frozenset({"kind", "monthly_cost", "exposure", "shock", "months", "currency"})
_DECIMAL_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?\Z")
_CENT = Decimal("0.01")


def _decimal(value, field, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{field}: use a decimal string, integer or Decimal")
    if isinstance(value, str):
        if len(value) > 32 or not _DECIMAL_PATTERN.fullmatch(value):
            raise ValueError(f"{field}: use a plain decimal with at most two decimal places")
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError(f"{field}: value must be finite")
    if number.as_tuple().exponent < -2:
        raise ValueError(f"{field}: at most two decimal places are allowed")
    if not minimum <= number <= maximum:
        raise ValueError(f"{field}: value must be between {minimum} and {maximum}")
    return number.copy_abs()  # Canonicalize Decimal negative zero.


def _validate(input_data):
    if not isinstance(input_data, dict) or set(input_data) != _FIELDS:
        raise ValueError("Provide exactly kind, monthly_cost, exposure, shock, months and currency")
    kind = input_data["kind"]
    if not isinstance(kind, str) or kind not in ("trade", "supply", "energy"):
        raise ValueError("kind: expected trade, supply or energy")
    if input_data["currency"] != "USD":
        raise ValueError("currency: only USD is supported")
    months = input_data["months"]
    if type(months) is not int or months not in (1, 3, 6, 12):
        raise ValueError("months: expected the integer 1, 3, 6 or 12")
    return (
        _decimal(input_data["monthly_cost"], "monthly_cost", 1, 10**9),
        _decimal(input_data["exposure"], "exposure", 0, 100),
        _decimal(input_data["shock"], "shock", 0, 100),
        months,
    )


def calculate(input_data: dict) -> dict:
    """Calculate JSON-ready costs, rejecting unsupported or ambiguous inputs.

    Returned percentage and monetary amounts are fixed two-place decimal strings.
    The input and global assumptions are never modified. Scenario kind supplies
    context only: all three kinds use the same direct-cost formula in this version.
    """
    with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
        monthly, exposure, shock, months = _validate(input_data)
        exposed = monthly * exposure / 100
        additional = exposed * shock / 100
        baseline = monthly * months
        values = {
            "exposed_monthly": exposed,
            "additional_monthly": additional,
            "additional_total": additional * months,
            "baseline_total": baseline,
            "scenario_total": baseline + additional * months,
            "increase_percent": exposure * shock / 100,
        }
        return {
            **{key: format(value.quantize(_CENT), ".2f") for key, value in values.items()},
            "currency": "USD",
            "engine_version": ENGINE_VERSION,
            "assumptions": list(ASSUMPTIONS),
        }
