"""Pipeline integrity calculations for corrosion metal-loss assessments.

The package exposes deterministic failure-pressure calculators that can be
combined with probabilistic/Bayesian workflows built around in-line inspection
(ILI) data.
"""

from .analysis import compare_feature_records, compare_methods
from .b31g import (
    modified_b31g,
    modified_b31g_folias,
    original_b31g,
    original_b31g_folias,
)
from .config import (
    AnalysisConfig,
    AnalysisSettings,
    FeatureInput,
    PipelineParameters,
    config_from_mapping,
    load_config,
    run_config,
    run_config_file,
    write_records_csv,
)
from .dnv import dnv_rp_f101, dnv_rp_f101_folias
from .models import AssessmentResult, CorrosionFeature, results_to_records
from .rstreng import rstreng_effective_area

__all__ = [
    "AnalysisConfig",
    "AnalysisSettings",
    "AssessmentResult",
    "CorrosionFeature",
    "FeatureInput",
    "PipelineParameters",
    "compare_methods",
    "config_from_mapping",
    "compare_feature_records",
    "dnv_rp_f101",
    "dnv_rp_f101_folias",
    "modified_b31g",
    "modified_b31g_folias",
    "original_b31g",
    "original_b31g_folias",
    "load_config",
    "results_to_records",
    "run_config",
    "run_config_file",
    "rstreng_effective_area",
    "write_records_csv",
]
