"""Remaining-strength methods for corroded pipelines.

The equations in this module are intended for engineering screening and
analysis of in-line inspection (ILI) metal-loss features.  They implement three
commonly compared corrosion-assessment methods:

* original ASME B31G (parabolic defect shape, 2/3 area factor),
* Modified B31G / 0.85dL (Level 1),
* DNV RP-F101 single-defect corrosion assessment, and
* RSTRENG effective-area style assessment for a measured river-bottom profile.

All inputs must use a consistent unit system.  For example, if dimensions are
provided in inches and stresses in psi, calculated pressures are returned in
psi.  If dimensions are provided in millimetres and stresses in MPa, pressures
are returned in MPa.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class CorrosionFeature:
    """Input geometry and material data for a corrosion feature.

    Attributes:
        outside_diameter: Pipe outside diameter, D.
        wall_thickness: Nominal wall thickness, t.
        smys: Specified minimum yield strength of the pipe material.
        depth: Maximum metal-loss depth, d.
        length: Axial length of the metal-loss feature, L.
        maop: Optional maximum allowable operating pressure used to calculate
            pressure ratios and pass/fail indicators.
        feature_id: Optional identifier carried through batch result tables.
        ultimate_tensile_strength: Optional specified minimum tensile strength
            used by DNV RP-F101.  A DNV function call can also pass this value
            directly.
    """

    outside_diameter: float
    wall_thickness: float
    smys: float
    depth: float
    length: float
    maop: float | None = None
    feature_id: str | None = None
    ultimate_tensile_strength: float | None = None


@dataclass(frozen=True)
class AssessmentResult:
    """Calculated result for a single corrosion assessment method."""

    method: str
    failure_pressure: float
    safe_pressure: float
    flow_stress: float
    folias_factor: float | None
    area_ratio: float
    depth_ratio: float
    length_parameter: float
    maop_ratio: float | None = None
    passes_maop: bool | None = None
    details: Mapping[str, float | str | int | None] = field(default_factory=dict)

    def as_dict(self) -> dict[str, float | str | bool | int | None]:
        """Return a flat dictionary suitable for CSV/data-frame analysis."""

        record = asdict(self)
        details = record.pop("details")
        for key, value in details.items():
            record[f"detail_{key}"] = value
        return record


def _positive(value: float, name: str) -> float:
    if value <= 0:
        raise ValueError(f"{name} must be positive; got {value!r}")
    return value


def _validate_feature(feature: CorrosionFeature) -> tuple[float, float, float, float, float]:
    diameter = _positive(feature.outside_diameter, "outside_diameter")
    thickness = _positive(feature.wall_thickness, "wall_thickness")
    smys = _positive(feature.smys, "smys")
    depth = _positive(feature.depth, "depth")
    length = _positive(feature.length, "length")
    if depth >= thickness:
        raise ValueError("depth must be less than wall_thickness for pressure calculation")
    if feature.maop is not None:
        _positive(feature.maop, "maop")
    return diameter, thickness, smys, depth, length


def original_b31g_folias(length_parameter: float) -> float:
    """Return the original B31G Folias bulging factor.

    The original criterion uses ``sqrt(1 + 0.8 * z)`` while ``z <= 20``.  For
    longer flaws, original B31G treats the defect as infinitely long in the
    pressure equation, so callers normally do not use this finite factor.
    """

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


def dnv_rp_f101_folias(length_parameter: float) -> float:
    """Return the DNV RP-F101 single-defect Folias/bulging factor."""

    if length_parameter < 0:
        raise ValueError("length_parameter must be non-negative")
    return sqrt(1.0 + 0.31 * length_parameter)


def _pressure_with_area(
    *,
    diameter: float,
    thickness: float,
    flow_stress: float,
    area_ratio: float,
    folias_factor: float,
) -> float:
    """Calculate failure pressure from an area ratio and Folias factor."""

    denominator = 1.0 - area_ratio / folias_factor
    if denominator <= 0:
        raise ValueError("invalid geometry: area_ratio / folias_factor must be less than 1")
    return (2.0 * flow_stress * thickness / diameter) * ((1.0 - area_ratio) / denominator)


def _resolve_ultimate_tensile_strength(
    feature: CorrosionFeature,
    ultimate_tensile_strength: float | None,
) -> tuple[float, str]:
    if ultimate_tensile_strength is not None:
        return _positive(ultimate_tensile_strength, "ultimate_tensile_strength"), "argument"
    if feature.ultimate_tensile_strength is not None:
        return _positive(feature.ultimate_tensile_strength, "ultimate_tensile_strength"), "feature"
    return feature.smys, "smys_fallback"


def _with_maop(
    *,
    method: str,
    pressure: float,
    safety_factor: float,
    flow_stress: float,
    folias_factor: float | None,
    area_ratio: float,
    depth_ratio: float,
    length_parameter: float,
    maop: float | None,
    details: Mapping[str, float | str | int | None] | None = None,
) -> AssessmentResult:
    safe_pressure = pressure * safety_factor
    maop_ratio = None if maop is None else safe_pressure / maop
    passes_maop = None if maop is None else safe_pressure >= maop
    return AssessmentResult(
        method=method,
        failure_pressure=pressure,
        safe_pressure=safe_pressure,
        flow_stress=flow_stress,
        folias_factor=folias_factor,
        area_ratio=area_ratio,
        depth_ratio=depth_ratio,
        length_parameter=length_parameter,
        maop_ratio=maop_ratio,
        passes_maop=passes_maop,
        details=details or {},
    )


def original_b31g(feature: CorrosionFeature, *, safety_factor: float = 0.72) -> AssessmentResult:
    """Calculate failure pressure using the original ASME B31G criterion.

    Original B31G uses a parabolic-area approximation for short corrosion
    features: ``area_ratio = (2/3) * (d/t)``.  When ``L^2/(D*t) > 20``, the
    long-defect branch is used and the feature is treated as infinitely long.
    """

    diameter, thickness, smys, depth, length = _validate_feature(feature)
    _positive(safety_factor, "safety_factor")
    depth_ratio = depth / thickness
    length_parameter = length**2 / (diameter * thickness)
    flow_stress = 1.1 * smys

    if length_parameter > 20.0:
        pressure = (2.0 * flow_stress * thickness / diameter) * (1.0 - depth_ratio)
        return _with_maop(
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
    pressure = _pressure_with_area(
        diameter=diameter,
        thickness=thickness,
        flow_stress=flow_stress,
        area_ratio=area_ratio,
        folias_factor=folias_factor,
    )
    return _with_maop(
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
    """Calculate failure pressure using Modified B31G (0.85dL Level 1).

    The modified criterion uses ``flow_stress = SMYS + flow_stress_increment``
    and ``area_ratio = 0.85 * d/t``.  The default increment is 10,000 psi; use
    the equivalent increment, such as 68.9476 MPa, when working in SI units.
    """

    diameter, thickness, smys, depth, length = _validate_feature(feature)
    _positive(safety_factor, "safety_factor")
    _positive(flow_stress_increment, "flow_stress_increment")
    depth_ratio = depth / thickness
    length_parameter = length**2 / (diameter * thickness)
    area_ratio = 0.85 * depth_ratio
    flow_stress = smys + flow_stress_increment
    folias_factor = modified_b31g_folias(length_parameter)
    pressure = _pressure_with_area(
        diameter=diameter,
        thickness=thickness,
        flow_stress=flow_stress,
        area_ratio=area_ratio,
        folias_factor=folias_factor,
    )
    return _with_maop(
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



def dnv_rp_f101(
    feature: CorrosionFeature,
    *,
    safety_factor: float = 0.72,
    ultimate_tensile_strength: float | None = None,
) -> AssessmentResult:
    """Calculate failure pressure using DNV RP-F101 single-defect corrosion.

    DNV RP-F101 uses the specified minimum tensile strength (SMTS/UTS) rather
    than SMYS.  Pass ``ultimate_tensile_strength`` or set it on
    ``CorrosionFeature`` for a method-specific result.  If neither is provided,
    the function falls back to SMYS and marks that assumption in ``details`` so
    side-by-side comparison workflows remain possible.
    """

    diameter, thickness, _smys, depth, length = _validate_feature(feature)
    _positive(safety_factor, "safety_factor")
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
    return _with_maop(
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
    metal_loss_depth)`` pairs.  The default flow-stress increment is 10,000 psi;
    use the equivalent increment, such as 68.9476 MPa, when working in SI units.
    The function evaluates every contiguous profile
    window and returns the lowest predicted failure pressure, which is the
    critical effective area for that feature.
    """

    diameter, thickness, smys, _depth, _length = _validate_feature(feature)
    _positive(safety_factor, "safety_factor")
    _positive(flow_stress_increment, "flow_stress_increment")
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
            pressure = _pressure_with_area(
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
    return _with_maop(
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


def results_to_records(
    results: Iterable[AssessmentResult],
    *,
    feature_id: str | None = None,
) -> list[dict[str, float | str | bool | int | None]]:
    """Convert assessment results to flat records for analysis/export."""

    records = []
    for result in results:
        record = result.as_dict()
        if feature_id is not None:
            record["feature_id"] = feature_id
        records.append(record)
    return records


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
