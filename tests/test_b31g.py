from math import isclose

from pipeline_integrity_tools import CorrosionFeature, compare_feature_records, compare_methods
from pipeline_integrity_tools.b31g import modified_b31g, original_b31g
from pipeline_integrity_tools.dnv import dnv_rp_f101
from pipeline_integrity_tools.rstreng import rstreng_effective_area


def test_original_b31g_matches_hand_calculation_short_defect():
    feature = CorrosionFeature(
        outside_diameter=24.0,
        wall_thickness=0.375,
        smys=52_000.0,
        depth=0.150,
        length=8.0,
    )

    result = original_b31g(feature)

    assert result.method == "Original B31G"
    assert result.details["branch"] == "short_defect"
    assert isclose(result.length_parameter, 7.1111111111)
    assert isclose(result.failure_pressure, 1461.5283866)
    assert isclose(result.safe_pressure, 1052.3004383)


def test_original_b31g_long_defect_branch():
    feature = CorrosionFeature(
        outside_diameter=24.0,
        wall_thickness=0.375,
        smys=52_000.0,
        depth=0.150,
        length=20.0,
    )

    result = original_b31g(feature)

    assert result.details["branch"] == "long_defect"
    assert result.folias_factor is None
    assert isclose(result.failure_pressure, 1072.5)


def test_modified_b31g_returns_maop_indicator():
    feature = CorrosionFeature(
        outside_diameter=24.0,
        wall_thickness=0.375,
        smys=52_000.0,
        depth=0.150,
        length=8.0,
        maop=1000.0,
    )

    result = modified_b31g(feature)

    assert result.method == "Modified B31G"
    assert result.passes_maop is True
    assert result.maop_ratio and result.maop_ratio > 1.0


def test_dnv_rp_f101_uses_ultimate_tensile_strength():
    feature = CorrosionFeature(
        outside_diameter=24.0,
        wall_thickness=0.375,
        smys=52_000.0,
        depth=0.150,
        length=8.0,
        ultimate_tensile_strength=66_000.0,
    )

    result = dnv_rp_f101(feature)

    assert result.method == "DNV RP-F101"
    assert result.details["assessment"] == "single_defect"
    assert result.details["strength_source"] == "feature"
    assert isclose(result.folias_factor, 1.7900962109)
    assert isclose(result.failure_pressure, 1618.8855473)
    assert isclose(result.safe_pressure, 1165.5975940)


def test_dnv_rp_f101_accepts_tensile_strength_argument():
    feature = CorrosionFeature(24.0, 0.375, 52_000.0, 0.150, 8.0)

    result = dnv_rp_f101(feature, ultimate_tensile_strength=66_000.0)

    assert result.details["strength_source"] == "argument"
    assert isclose(result.flow_stress, 66_000.0)


def test_rstreng_effective_area_uses_critical_profile_window():
    feature = CorrosionFeature(
        outside_diameter=24.0,
        wall_thickness=0.375,
        smys=52_000.0,
        depth=0.150,
        length=8.0,
    )
    profile = [(0.0, 0.0), (2.0, 0.10), (4.0, 0.15), (6.0, 0.12), (8.0, 0.0)]

    result = rstreng_effective_area(feature, profile)

    assert result.method == "RSTRENG Effective Area"
    assert result.failure_pressure > 0
    assert result.details["critical_start_index"] == 0
    assert result.details["critical_end_index"] == 4


def test_compare_methods_includes_optional_rstreng():
    feature = CorrosionFeature(24.0, 0.375, 52_000.0, 0.150, 8.0)
    profile = [(0.0, 0.0), (4.0, 0.15), (8.0, 0.0)]

    results = compare_methods(feature, profile=profile)

    assert [result.method for result in results] == [
        "Original B31G",
        "Modified B31G",
        "DNV RP-F101",
        "RSTRENG Effective Area",
    ]


def test_compare_feature_records_flattens_results_for_analysis():
    feature = CorrosionFeature(24.0, 0.375, 52_000.0, 0.150, 8.0, feature_id="F-1")

    records = compare_feature_records(feature)

    assert len(records) == 3
    assert records[0]["feature_id"] == "F-1"
    assert records[0]["method"] == "Original B31G"
    assert "detail_branch" in records[0]
