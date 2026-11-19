"""Validate stratified formulas, finite-count witnesses and synthetic-only I/O."""

from collections import Counter
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lantern_causal.pilot import analyze_observed, mask_reference, run_pilot, synthetic_reference
from lantern_causal.recovery import (
    FullRow, ObservedRow, SupportError, complete_counts, empirical_bounds,
    standardized_mar, standardized_reference, standardized_visible,
)


def observed_table(cell_counts, c="c"):
    """Expand counts in the order 00,01,10,11,missing0,missing1."""
    cells = ((0, 0), (0, 1), (1, 0), (1, 1), (None, 0), (None, 1))
    return [ObservedRow(x, y, c) for (x, y), count in zip(cells, cell_counts) for _ in range(count)]


def rd_from_counts(counts):
    """Independently score a completed aggregate table using empirical C weights."""
    n = sum(counts.values())
    result = F()
    for c in {c for c, _, _ in counts}:
        low = counts.get((c, 0, 0), 0) + counts.get((c, 0, 1), 0)
        high = counts.get((c, 1, 0), 0) + counts.get((c, 1, 1), 0)
        if not low or not high:
            raise ValueError("Empty group in independent witness score.")
        result += F(low + high, n) * (F(counts.get((c, 1, 1), 0), high)
                                       - F(counts.get((c, 0, 1), 0), low))
    return result


class StratifiedRecoveryTests(unittest.TestCase):
    def test_exact_mar_recovers_joint_instead_of_visible_case_target(self):
        # Complete XY counts 12,4,4,12; visibility 1/4 for Y=0, 3/4 for Y=1.
        rows = observed_table((3, 3, 1, 9, 12, 4))
        self.assertEqual(standardized_mar(rows), F(1, 2))
        self.assertEqual(standardized_visible(rows), F(2, 5))

    def test_exposure_dependent_recording_recovers_target_without_mar(self):
        # Same complete joint; visibility 1/4 for X=0, 3/4 for X=1.
        rows = observed_table((3, 1, 3, 9, 10, 6))
        self.assertEqual(standardized_visible(rows), F(1, 2))
        self.assertNotEqual(standardized_mar(rows), F(1, 2))

    def test_weights_use_all_rows_even_when_recording_varies_by_stratum(self):
        first = observed_table((1, 0, 0, 1, 2, 4), "first")  # 8 total, RD=1
        second = observed_table((0, 1, 1, 0, 11, 11), "second")  # 24 total, RD=-1
        self.assertEqual(standardized_visible(first + second), F(-1, 2))
        self.assertEqual(standardized_mar(first + second), F(-1, 2))

    def test_reference_uses_identical_weights_without_missingness(self):
        full = [FullRow(0, 0, "first"), FullRow(1, 1, "first")]
        full += [FullRow(0, 1, "second"), FullRow(1, 0, "second")] * 3
        observed = [ObservedRow(row.x, row.y, row.c) for row in full]
        self.assertEqual(standardized_reference(full), F(-1, 2))
        self.assertEqual(standardized_mar(observed), standardized_reference(full))
        self.assertEqual(standardized_visible(observed), standardized_reference(full))
        bounds = empirical_bounds(observed)
        self.assertEqual((bounds.lower, bounds.upper), (F(-1, 2), F(-1, 2)))

    def test_positive_outcome_mass_requires_visible_support_for_mar(self):
        rows = observed_table((1, 0, 1, 0, 0, 1))
        with self.assertRaises(SupportError):
            standardized_mar(rows)
        self.assertEqual(standardized_visible(rows), 0)
        result = analyze_observed(rows)
        self.assertEqual(result["estimators"]["assume_r_independent_x_given_y_c"]["status"],
                         "insufficient_support")
        # A zero-mass outcome cell contributes zero rather than causing failure.
        self.assertEqual(standardized_mar(observed_table((1, 0, 1, 0, 1, 0))), 0)

    def test_missing_exposure_group_is_a_failure_not_a_zero_risk(self):
        rows = observed_table((1, 1, 0, 0, 1, 1))
        for estimator in (standardized_mar, standardized_visible):
            with self.assertRaises(SupportError):
                estimator(rows)
        # Compatible complete cohorts can still have both groups.
        self.assertLess(empirical_bounds(rows).lower, empirical_bounds(rows).upper)

    def test_protocol_example_bounds_and_equal_prevalence_counterexample(self):
        rows = observed_table((34, 8, 16, 12, 15, 15))
        bounds = empirical_bounds(rows)
        self.assertEqual(bounds.lower, F(12, 43) - F(23, 57))
        self.assertEqual(bounds.upper, F(27, 43) - F(8, 57))
        first = complete_counts(rows, {("c", 1): 8, ("c", 0): 14})
        second = complete_counts(rows, {("c", 1): 14, ("c", 0): 8})
        self.assertEqual(rd_from_counts(first), F(1, 10))
        self.assertEqual(rd_from_counts(second), F(17, 50))
        for counts in (first, second):
            self.assertEqual(sum(n for (_, x, _), n in counts.items() if x == 1), 50)

    def test_bounds_agree_with_exhaustive_completions_including_empty_extremes(self):
        # Enumerate all 728 nonempty small observed tables and every integer
        # completion. This checks the monotone endpoint algorithm independently.
        for cells in product(range(3), repeat=6):
            if not sum(cells):
                continue
            rows = observed_table(cells)
            a, b, c, d, m0, m1 = cells
            values = []
            for u0, u1 in product(range(m0 + 1), range(m1 + 1)):
                low, high = a + b + m0 + m1 - u0 - u1, c + d + u0 + u1
                if low and high:
                    values.append(F(d + u1, high) - F(b + m1 - u1, low))
            if not values:
                with self.assertRaises(SupportError, msg=str(cells)):
                    empirical_bounds(rows)
                continue
            bounds = empirical_bounds(rows)
            self.assertEqual((bounds.lower, bounds.upper), (min(values), max(values)), str(cells))
            for value, allocation in ((bounds.lower, bounds.lower_allocation),
                                      (bounds.upper, bounds.upper_allocation)):
                self.assertEqual(rd_from_counts(complete_counts(rows, allocation)), value)

    def test_witnesses_preserve_full_observation_gate_in_every_stratum(self):
        full = synthetic_reference()
        rows, _ = mask_reference(full, "C", seed=1)
        counts = Counter((row.c, row.x, row.y) for row in rows)
        bounds = empirical_bounds(rows)
        for expected_rd, allocation in ((bounds.lower, bounds.lower_allocation),
                                        (bounds.upper, bounds.upper_allocation)):
            completed = complete_counts(rows, allocation)
            reconstructed = Counter()
            # Reapply the observation gate to a full X,Y,C,R table: keep
            # visible cells and collapse only the allocated masked cells.
            for (c, x, y), n in counts.items():
                if x is not None:
                    reconstructed[c, x, y] += n
            for (c, y), high in allocation.items():
                missing = counts[c, None, y]
                for assigned, n in ((1, high), (0, missing - high)):
                    self.assertEqual(completed[c, assigned, y], counts[c, assigned, y] + n)
                    masked_full_row = (assigned, y, c, 0)
                    x, outcome, stratum, r = masked_full_row
                    reconstructed[stratum, x if r else None, outcome] += n
            self.assertEqual(reconstructed, counts)
            self.assertEqual(rd_from_counts(completed), expected_rd)
        self.assertLessEqual(bounds.lower, standardized_reference(full))
        self.assertGreaterEqual(bounds.upper, standardized_reference(full))

    def test_invalid_rows_and_allocations_do_not_produce_estimates(self):
        for fields in ((2, 0, "c"), (True, 0, "c"), (0, None, "c"), (0, 0, "")):
            with self.assertRaises(ValueError):
                ObservedRow(*fields)
        with self.assertRaises(ValueError):
            FullRow(None, 0, "c")
        with self.assertRaises(ValueError):
            standardized_mar([FullRow(0, 0, "c")])
        with self.assertRaises(ValueError):
            empirical_bounds([])
        rows = observed_table((1, 1, 1, 1, 1, 1))
        for allocation in ({}, {("c", 0): 2, ("c", 1): 0},
                           {("c", 0): True, ("c", 1): 0}):
            with self.assertRaises(ValueError):
                complete_counts(rows, allocation)


class SyntheticPilotTests(unittest.TestCase):
    def test_masks_repeat_without_exposing_hidden_values_or_generator_fields(self):
        full = synthetic_reference()
        one, alpha = mask_reference(full, "A", 1)
        repeated, repeated_alpha = mask_reference(full, "A", 1)
        other, _ = mask_reference(full, "A", 2)
        self.assertEqual((one, alpha), (repeated, repeated_alpha))
        self.assertNotEqual(one, other)
        self.assertEqual(sum(row.x is None for row in one), 312)
        self.assertTrue(all(set(vars(row)) == {"x", "y", "c"} for row in one))
        self.assertEqual(standardized_reference(full), F(39, 400))
        # Independent check of the calibrated average expected visibility.
        import math
        visibility = sum(1 / (1 + math.exp(-alpha - 0.4 * row.c.startswith("65plus_")
                                         - 0.2 * row.c.endswith("_female") - math.log(2) * row.y))
                         for row in full) / len(full)
        self.assertAlmostEqual(visibility, 0.7, places=12)

    def test_three_scenarios_report_errors_witnesses_and_no_point_claim_for_c(self):
        report = run_pilot({"schema_version": 1, "seeds": [1, 2]})
        self.assertFalse(report["patient_data_used"])
        self.assertFalse(report["llm_executed"])
        self.assertEqual(report["reference_rd"]["percentage_points"], 9.75)
        self.assertEqual(len(report["runs"]), 6)
        for run in report["runs"]:
            self.assertTrue(run["scoring"]["reference_in_bounds"])
            if run["scenario"] == "C":
                self.assertIsNone(run["known_graph_baseline"]["point_estimate"])
                self.assertEqual(run["known_graph_baseline"]["empirical_status"], "nonunique_witness")
        for result in report["summary"].values():
            self.assertEqual(result["repetitions"], 2)
            self.assertEqual(result["reference_in_bounds"], 2)
            self.assertEqual(result["paired_absolute_error_comparison"]["pairs"], 2)

    def test_same_effective_config_has_same_fingerprint_and_results(self):
        a = run_pilot({"schema_version": 1, "seeds": [1]})
        b = run_pilot({"expected_missing_rate": 0.3, "seeds": [1], "schema_version": 1})
        self.assertEqual(a, b)

    def test_invalid_config_is_rejected_before_running(self):
        bad_configs = [[], {}, {"schema_version": True},
                       {"schema_version": 1, "seeds": [1, 1]},
                       {"schema_version": 1, "seeds": []},
                       {"schema_version": 1, "seeds": [True]},
                       {"schema_version": 1, "expected_missing_rate": float("nan")},
                       {"schema_version": 1, "expected_missing_rate": 1},
                       {"schema_version": 1, "expected_missing_rate": True},
                       {"schema_version": 1, "typo": 1}]
        for config in bad_configs:
            with self.assertRaises(ValueError, msg=str(config)):
                run_pilot(config)
        with self.assertRaises(ValueError):
            mask_reference([FullRow(0, 0, "unmapped_stratum")], "A", 1)

    def test_pilot_cli_works_outside_repository_and_writes_the_same_json(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.json"
            output = Path(temp) / "nested" / "report.json"
            config.write_text(json.dumps({"schema_version": 1, "seeds": [1]}), encoding="utf-8")
            process = subprocess.run(
                [sys.executable, "-m", "lantern_causal", "pilot", "--config", str(config),
                 "--output", str(output)], cwd=temp, capture_output=True, text=True, check=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(process.stdout), report)
            self.assertEqual(len(report["runs"]), 3)


if __name__ == "__main__":
    unittest.main()
