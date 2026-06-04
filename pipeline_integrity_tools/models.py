"""Shared data models and calculation helpers for corrosion assessments."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Mapping


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
            used by DNV RP-F101. A DNV function call can also pass this value
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


def positive(value: float, name: str) -> float:
    """Validate that a numeric input is positive."""

    if value <= 0:
        raise ValueError(f"{name} must be positive; got {value!r}")
    return value


def validate_feature(feature: CorrosionFeature) -> tuple[float, float, float, float, float]:
    """Validate common corrosion-feature inputs and return core values."""

    diameter = positive(feature.outside_diameter, "outside_diameter")
    thickness = positive(feature.wall_thickness, "wall_thickness")
    smys = positive(feature.smys, "smys")
    depth = positive(feature.depth, "depth")
    length = positive(feature.length, "length")
    if depth >= thickness:
        raise ValueError("depth must be less than wall_thickness for pressure calculation")
    if feature.maop is not None:
        positive(feature.maop, "maop")
    return diameter, thickness, smys, depth, length


def pressure_with_area(
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


def with_maop(
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
    """Build an assessment result with optional MAOP pass/fail fields."""

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
