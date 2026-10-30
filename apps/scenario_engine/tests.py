"""Contract tests independent of Django or a database."""

import json
import unittest
from decimal import Decimal, localcontext

from apps.scenario_engine.engine import ASSUMPTIONS, ENGINE_VERSION, calculate


def inputs(**changes):
    return {
        "kind": "trade", "monthly_cost": "1000000.00", "exposure": "35",
        "shock": "20", "months": 3, "currency": "USD", **changes,
    }


class EngineTests(unittest.TestCase):
    def test_matches_frontend_default_formula(self):
        self.assertEqual(calculate(inputs()), {
            "exposed_monthly": "350000.00", "additional_monthly": "70000.00",
            "additional_total": "210000.00", "baseline_total": "3000000.00",
            "scenario_total": "3210000.00", "increase_percent": "7.00",
            "currency": "USD", "engine_version": ENGINE_VERSION,
            "assumptions": list(ASSUMPTIONS),
        })

    def test_each_scenario_kind_uses_same_explicit_cost_formula(self):
        for kind in ("trade", "supply", "energy"):
            with self.subTest(kind=kind):
                self.assertEqual(calculate(inputs(kind=kind))["additional_total"], "210000.00")

    def test_accepts_decimal_and_integer_inputs_and_returns_json(self):
        result = calculate(inputs(monthly_cost=Decimal("125.25"), exposure=50, shock=Decimal("10.25")))
        self.assertEqual(result["additional_monthly"], "6.42")
        self.assertEqual(result["additional_total"], "19.26")
        json.dumps(result, allow_nan=False)

    def test_rounds_half_up_and_totals_from_unrounded_values(self):
        result = calculate(inputs(monthly_cost="1", exposure="50", shock="1", months=3))
        self.assertEqual(result["additional_monthly"], "0.01")
        self.assertEqual(result["additional_total"], "0.02")
        self.assertEqual(result["scenario_total"], "3.02")

    def test_zero_and_maximum_boundaries(self):
        for exposure, shock in ((0, 100), (100, 0), (0, 0)):
            self.assertEqual(calculate(inputs(exposure=exposure, shock=shock))["additional_total"], "0.00")
        result = calculate(inputs(monthly_cost=10**9, exposure=100, shock=100, months=12))
        self.assertEqual(result["scenario_total"], "24000000000.00")
        self.assertEqual(result["increase_percent"], "100.00")

    def test_all_allowed_horizons(self):
        for months in (1, 3, 6, 12):
            self.assertEqual(calculate(inputs(months=months))["baseline_total"], f"{1000000 * months}.00")

    def test_input_and_assumptions_are_not_mutated_or_shared(self):
        value = inputs()
        before = value.copy()
        result = calculate(value)
        result["assumptions"].clear()
        self.assertEqual(value, before)
        self.assertTrue(calculate(value)["assumptions"])

    def test_result_is_independent_of_callers_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            result = calculate(inputs())
        self.assertEqual(result["scenario_total"], "3210000.00")

    def test_rejects_missing_unknown_and_non_object_inputs(self):
        for field in inputs():
            with self.subTest(missing=field), self.assertRaises(ValueError):
                calculate({key: value for key, value in inputs().items() if key != field})
        for value in (None, [], "", 3, {**inputs(), "extra": 1}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate(value)

    def test_rejects_invalid_kind_currency_and_months(self):
        for field, values in {
            "kind": ["other", None, True, []],
            "currency": ["EUR", "usd", None, True, []],
            "months": [0, 2, 13, True, "3", 3.0, Decimal(3), None, []],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate(inputs(**{field: value}))

    def test_rejects_invalid_numeric_types_nonfinite_and_precision(self):
        values = [True, False, 1.0, None, [], {}, "", "NaN", "Infinity",
                  "-Infinity", Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
                  float("nan"), float("inf"), "1.001", Decimal("1.001"), " 1 ",
                  "1_000", "1e2", "1" * 1000]
        for field in ("monthly_cost", "exposure", "shock"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate(inputs(**{field: value}))

    def test_rejects_out_of_range_inputs(self):
        for field, values in {
            "monthly_cost": [0, "0.99", -1, "1000000000.01", Decimal("1e1000000")],
            "exposure": [-1, "100.01"], "shock": [-1, "100.01"],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate(inputs(**{field: value}))


if __name__ == "__main__":
    unittest.main()
