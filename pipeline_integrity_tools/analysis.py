"""Side-by-side analysis helpers that combine all corrosion assessment methods."""

from __future__ import annotations

from typing import Iterable

from .b31g import modified_b31g, original_b31g
from .dnv import dnv_rp_f101
from .models import AssessmentResult, CorrosionFeature, results_to_records
from .rstreng import rstreng_effective_area


def compare_methods(
    feature: CorrosionFeature,
    *,
    profile: Iterable[tuple[float, float]] | None = None,
    safety_factor: float = 0.72,
    flow_stress_increment: float = 10_000.0,
    ultimate_tensile_strength: float | None = None,
) -> list[AssessmentResult]:
    """Return Original B31G, Modified B31G, DNV, and optional RSTRENG results."""

    results = [
        original_b31g(feature, safety_factor=safety_factor),
        modified_b31g(
            feature,
            safety_factor=safety_factor,
            flow_stress_increment=flow_stress_increment,
        ),
        dnv_rp_f101(
            feature,
            safety_factor=safety_factor,
            ultimate_tensile_strength=ultimate_tensile_strength,
        ),
    ]
    if profile is not None:
        results.append(
            rstreng_effective_area(
                feature,
                profile,
                safety_factor=safety_factor,
                flow_stress_increment=flow_stress_increment,
            )
        )
    return results


def compare_feature_records(
    feature: CorrosionFeature,
    *,
    profile: Iterable[tuple[float, float]] | None = None,
    safety_factor: float = 0.72,
    flow_stress_increment: float = 10_000.0,
    ultimate_tensile_strength: float | None = None,
) -> list[dict[str, float | str | bool | int | None]]:
    """Return all method outputs as flat records for downstream analysis."""

    return results_to_records(
        compare_methods(
            feature,
            profile=profile,
            safety_factor=safety_factor,
            flow_stress_increment=flow_stress_increment,
            ultimate_tensile_strength=ultimate_tensile_strength,
        ),
        feature_id=feature.feature_id,
    )
