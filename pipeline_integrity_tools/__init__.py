"""Pipeline integrity calculations for corrosion metal-loss assessments.

The package exposes deterministic failure-pressure calculators that can be
combined with probabilistic/Bayesian workflows built around in-line inspection
(ILI) data.
"""

from .b31g import (
    AssessmentResult,
    CorrosionFeature,
    compare_methods,
    compare_feature_records,
    dnv_rp_f101,
    dnv_rp_f101_folias,
    modified_b31g,
    original_b31g,
    results_to_records,
    rstreng_effective_area,
)

__all__ = [
    "AssessmentResult",
    "CorrosionFeature",
    "compare_methods",
    "compare_feature_records",
    "dnv_rp_f101",
    "dnv_rp_f101_folias",
    "modified_b31g",
    "original_b31g",
    "results_to_records",
    "rstreng_effective_area",
]
