"""Original and Modified ASME B31G corrosion assessment methods."""

from __future__ import annotations

from math import sqrt

from .models import (
    AssessmentResult,
    CorrosionFeature,
    positive,
    pressure_with_area,
    validate_feature,
    with_maop,
)


def original_b31g_folias(length_parameter: float) -> float:
    """Return the original B31G Folias bulging factor."""

    if length_parameter < 0:
        raise ValueError("length_parameter must be non-negative")
    return sqrt(1.0 + 0.8 * length_parameter)


def modified_b31g_folias(length_parameter: float) -> float:
    """Return the Modified B31G/RSTRENG Folias bulging factor."""

    if length_parameter < 0:
        raise ValueError("length_parameter must be non-negative")
    if length_parameter <= 50.0:
        return sqrt(1.0 + 0.6275 * length_parameter - 0.003375 * length_parameter**2)
    return 0.032 * length_parameter + 3.3


def original_b31g(feature: CorrosionFeature, *, safety_factor: float = 0.72) -> AssessmentResult:
    """Calculate failure pressure using the original ASME B31G criterion.

    Original B31G uses a parabolic-area approximation for short corrosion
    features: ``area_ratio = (2/3) * (d/t)``. When ``L^2/(D*t) > 20``, the
    long-defect branch is used and the feature is treated as infinitely long.
    """

    diameter, thickness, smys, depth, length = validate_feature(feature)
    positive(safety_factor, "safety_factor")
    depth_ratio = depth / thickness
    length_parameter = length**2 / (diameter * thickness)
    flow_stress = 1.1 * smys

    if length_parameter > 20.0:
        pressure = (2.0 * flow_stress * thickness / diameter) * (1.0 - depth_ratio)
        return with_maop(
            method="Original B31G",
            pressure=pressure,
            safety_factor=safety_factor,
            flow_stress=flow_stress,
            folias_factor=None,
            area_ratio=depth_ratio,
            depth_ratio=depth_ratio,
            length_parameter=length_parameter,
            maop=feature.maop,
            details={"branch": "long_defect"},
        )

    area_ratio = (2.0 / 3.0) * depth_ratio
    folias_factor = original_b31g_folias(length_parameter)
    pressure = pressure_with_area(
        diameter=diameter,
        thickness=thickness,
        flow_stress=flow_stress,
        area_ratio=area_ratio,
        folias_factor=folias_factor,
    )
    return with_maop(
        method="Original B31G",
        pressure=pressure,
        safety_factor=safety_factor,
        flow_stress=flow_stress,
        folias_factor=folias_factor,
        area_ratio=area_ratio,
        depth_ratio=depth_ratio,
        length_parameter=length_parameter,
        maop=feature.maop,
        details={"branch": "short_defect"},
    )


def modified_b31g(
    feature: CorrosionFeature,
    *,
    safety_factor: float = 0.72,
    flow_stress_increment: float = 10_000.0,
) -> AssessmentResult:
    """Calculate failure pressure using Modified B31G (0.85dL Level 1)."""

    diameter, thickness, smys, depth, length = validate_feature(feature)
    positive(safety_factor, "safety_factor")
    positive(flow_stress_increment, "flow_stress_increment")
    depth_ratio = depth / thickness
    length_parameter = length**2 / (diameter * thickness)
    area_ratio = 0.85 * depth_ratio
    flow_stress = smys + flow_stress_increment
    folias_factor = modified_b31g_folias(length_parameter)
    pressure = pressure_with_area(
        diameter=diameter,
        thickness=thickness,
        flow_stress=flow_stress,
        area_ratio=area_ratio,
        folias_factor=folias_factor,
    )
    return with_maop(
        method="Modified B31G",
        pressure=pressure,
        safety_factor=safety_factor,
        flow_stress=flow_stress,
        folias_factor=folias_factor,
        area_ratio=area_ratio,
        depth_ratio=depth_ratio,
        length_parameter=length_parameter,
        maop=feature.maop,
    )
