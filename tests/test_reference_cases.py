"""Numerical regression checks for the manuscript's exact examples."""

from collections import defaultdict
from fractions import Fraction as F
from itertools import product
import unittest

from lantern_causal.distributions import marginal_xy, observe, validate_observed, visible_xy
from lantern_causal.experiments import run_example
from lantern_causal.inflation import cut_triangle_certificate
from lantern_causal.recovery import recover_with_calibrated_proxy, risk_difference, unrestricted_bounds
from lantern_causal.synthetic import make_case


class ReferenceCaseTests(unittest.TestCase):
    """Verify reference values, valid controls and the observable-information gate."""

    def test_proxy_recovers_full_joint(self):
        case = make_case("proxy")
        joint = marginal_xy(case.full)
        self.assertEqual(recover_with_calibrated_proxy(case.observed, F(1, 20)), joint)
        self.assertEqual(risk_difference(joint), F(27, 50))
        self.assertEqual(risk_difference(visible_xy(case.observed)), F(513, 3542))
        certificate = cut_triangle_certificate(case.observed)
        self.assertEqual((certificate.required_mismatch, certificate.path_upper_bound), (F(1, 2), F(19, 100)))

    def test_singular_or_wrong_proxy_calibration_is_not_a_result(self):
        observed = make_case("proxy").observed
        for error in (F(1, 2), F(-1, 10), F(49, 100)):
            with self.assertRaises(ValueError):
                recover_with_calibrated_proxy(observed, error)

    def test_bridge_changes_target_with_same_observed_evidence(self):
        case = make_case("bridge")
        self.assertEqual(risk_difference(marginal_xy(case.full)), F(9, 10))
        self.assertEqual(risk_difference(visible_xy(case.observed)), F(9, 10))
        certificate = cut_triangle_certificate(case.observed)
        self.assertTrue(certificate.incompatible)
        self.assertEqual(certificate.path_upper_bound, F(461, 2000))
        lower, upper = unrestricted_bounds(case.observed)
        self.assertAlmostEqual(float(lower), -0.1225881547, places=9)
        self.assertAlmostEqual(float(upper), 0.9515607976, places=9)
        for high_endpoint in (False, True):
            full = defaultdict(F)
            for (x, y, r, z), mass in case.observed.items():
                full[x if r else (y if high_endpoint else 1 - y), y, r, z] += mass
            self.assertEqual(observe(full), case.observed)

    def test_compatible_triangle_is_only_not_excluded(self):
        observed = defaultdict(F)
        for rz, zy, ry in product((0, 1), repeat=3):
            r, z, y = rz ^ ry, rz ^ zy, zy ^ ry
            observed[0 if r else None, y, r, z] += F(1, 8)
        certificate = cut_triangle_certificate(observed)
        self.assertFalse(certificate.incompatible)
        self.assertEqual(certificate.as_dict()["status"], "not_excluded")

    def test_exclusion_does_not_change_target_when_both_candidates_share_recovery_rule(self):
        bridge = run_example({"schema_version": 1, "scenario": "bridge"})
        control = run_example({"schema_version": 1, "scenario": "bridge_unchanged"})
        self.assertEqual(control["observable_distribution"], bridge["observable_distribution"])
        self.assertEqual(control["triangle_certificate"], bridge["triangle_certificate"])
        self.assertEqual(control["triangle_certificate"]["status"], "incompatible")
        self.assertEqual(control["before_inflation_outer_bounds"], control["after_inflation_outer_bounds"])
        self.assertEqual(control["before_inflation_outer_bounds"], [control["complete_case_rd"]] * 2)
        self.assertEqual(control["reference_rd"]["percentage_points"], 90.0)
        self.assertNotEqual(bridge["before_inflation_outer_bounds"], bridge["after_inflation_outer_bounds"])

    def test_observation_gate_prevents_hidden_value_leakage(self):
        with self.assertRaises(ValueError):
            validate_observed({(1, 0, 0, 0): F(1)})
        with self.assertRaises(ValueError):
            validate_observed({(None, 0, 0, 0): F(1, 2)})

    def test_empty_exposure_group_cannot_report_a_risk_difference(self):
        with self.assertRaises(ValueError):
            risk_difference({(1, 1): F(1)})

    def test_report_units_distinguish_probability_from_percentage_points(self):
        report = run_example({"schema_version": 1, "scenario": "proxy"})
        self.assertEqual(report["recovered_rd"]["probability_difference"], 0.54)
        self.assertEqual(report["recovered_rd"]["percentage_points"], 54.0)
        self.assertFalse(report["llm_executed"])
        self.assertFalse(report["patient_data_used"])


if __name__ == "__main__":
    unittest.main()
