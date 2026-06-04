"""DNV RP-F101 corrosion assessment methods."""

from __future__ import annotations

from math import sqrt

from .models import AssessmentResult, CorrosionFeature, positive, validate_feature, with_maop


def dnv_rp_f101_folias(length_parameter: float) -> float:
    """Return the DNV RP-F101 single-defect Folias/bulging factor."""

    if length_parameter < 0:
        raise ValueError("length_parameter must be non-negative")
    return sqrt(1.0 + 0.31 * length_parameter)


def _resolve_ultimate_tensile_strength(
    feature: CorrosionFeature,
    ultimate_tensile_strength: float | None,
) -> tuple[float, str]:
    if ultimate_tensile_strength is not None:
        return positive(ultimate_tensile_strength, "ultimate_tensile_strength"), "argument"
    if feature.ultimate_tensile_strength is not None:
        return positive(feature.ultimate_tensile_strength, "ultimate_tensile_strength"), "feature"
    return feature.smys, "smys_fallback"


def dnv_rp_f101(
    feature: CorrosionFeature,
    *,
    safety_factor: float = 0.72,
    ultimate_tensile_strength: float | None = None,
) -> AssessmentResult:
    """Calculate failure pressure using DNV RP-F101 single-defect corrosion."""

    diameter, thickness, _smys, depth, length = validate_feature(feature)
    positive(safety_factor, "safety_factor")
    if diameter <= thickness:
        raise ValueError("outside_diameter must be greater than wall_thickness")

    depth_ratio = depth / thickness
    length_parameter = length**2 / (diameter * thickness)
    folias_factor = dnv_rp_f101_folias(length_parameter)
    denominator = 1.0 - depth_ratio / folias_factor
    if denominator <= 0:
        raise ValueError("invalid geometry: depth_ratio / folias_factor must be less than 1")

    tensile_strength, strength_source = _resolve_ultimate_tensile_strength(
        feature,
        ultimate_tensile_strength,
    )
    pressure = (2.0 * thickness * tensile_strength / (diameter - thickness)) * (
        (1.0 - depth_ratio) / denominator
    )
    return with_maop(
        method="DNV RP-F101",
        pressure=pressure,
        safety_factor=safety_factor,
        flow_stress=tensile_strength,
        folias_factor=folias_factor,
        area_ratio=depth_ratio,
        depth_ratio=depth_ratio,
        length_parameter=length_parameter,
        maop=feature.maop,
        details={
            "assessment": "single_defect",
            "diameter_term": "outside_diameter_minus_wall_thickness",
            "strength_source": strength_source,
        },
    )
