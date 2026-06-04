"""RSTRENG-style effective-area corrosion assessment."""

from __future__ import annotations

from typing import Iterable, Sequence

from .b31g import modified_b31g_folias
from .models import (
    AssessmentResult,
    CorrosionFeature,
    positive,
    pressure_with_area,
    validate_feature,
    with_maop,
)


def _normalise_profile(profile: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    points = [(float(position), float(depth)) for position, depth in profile]
    if len(points) < 2:
        raise ValueError("profile must contain at least two (position, depth) points")
    points.sort(key=lambda item: item[0])
    for index, (position, depth) in enumerate(points):
        if depth < 0:
            raise ValueError("profile depths must be non-negative")
        if index and position <= points[index - 1][0]:
            raise ValueError("profile positions must be unique and increasing")
    return points


def _trapezoid_area(points: Sequence[tuple[float, float]]) -> float:
    area = 0.0
    for (x0, d0), (x1, d1) in zip(points, points[1:]):
        area += 0.5 * (d0 + d1) * (x1 - x0)
    return area


def rstreng_effective_area(
    feature: CorrosionFeature,
    profile: Iterable[tuple[float, float]],
    *,
    safety_factor: float = 0.72,
    flow_stress_increment: float = 10_000.0,
) -> AssessmentResult:
    """Calculate failure pressure using a RSTRENG effective-area approach.

    ``profile`` is an axial river-bottom profile expressed as ``(position,
    metal_loss_depth)`` pairs. The function evaluates every contiguous profile
    window and returns the lowest predicted failure pressure.
    """

    diameter, thickness, smys, _depth, _length = validate_feature(feature)
    positive(safety_factor, "safety_factor")
    positive(flow_stress_increment, "flow_stress_increment")
    points = _normalise_profile(profile)
    max_depth = max(depth for _position, depth in points)
    if max_depth >= thickness:
        raise ValueError("profile depths must be less than wall_thickness")

    flow_stress = smys + flow_stress_increment
    best: tuple[float, float, float, float, int, int] | None = None

    for start in range(len(points) - 1):
        for end in range(start + 1, len(points)):
            window = points[start : end + 1]
            length = window[-1][0] - window[0][0]
            if length <= 0:
                continue
            effective_area = _trapezoid_area(window)
            gross_area = thickness * length
            area_ratio = effective_area / gross_area
            if area_ratio <= 0:
                continue
            if area_ratio >= 1:
                raise ValueError("profile effective area must be less than t * L")
            length_parameter = length**2 / (diameter * thickness)
            folias_factor = modified_b31g_folias(length_parameter)
            pressure = pressure_with_area(
                diameter=diameter,
                thickness=thickness,
                flow_stress=flow_stress,
                area_ratio=area_ratio,
                folias_factor=folias_factor,
            )
            if best is None or pressure < best[0]:
                best = (pressure, area_ratio, length_parameter, folias_factor, start, end)

    if best is None:
        raise ValueError("profile must include at least one non-zero-depth interval")

    pressure, area_ratio, length_parameter, folias_factor, start, end = best
    return with_maop(
        method="RSTRENG Effective Area",
        pressure=pressure,
        safety_factor=safety_factor,
        flow_stress=flow_stress,
        folias_factor=folias_factor,
        area_ratio=area_ratio,
        depth_ratio=max_depth / thickness,
        length_parameter=length_parameter,
        maop=feature.maop,
        details={
            "critical_start_index": start,
            "critical_end_index": end,
            "critical_start_position": points[start][0],
            "critical_end_position": points[end][0],
        },
    )
