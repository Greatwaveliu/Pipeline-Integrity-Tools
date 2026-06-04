"""Configuration-driven pipeline corrosion analysis helpers.

This module lets users keep common pipe/material parameters and per-feature ILI
measurements in one JSON input file instead of editing Python source files for
every pipeline or scenario.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from .b31g import CorrosionFeature, compare_feature_records


ProfilePoint = tuple[float, float]


@dataclass(frozen=True)
class PipelineParameters:
    """Common pipe/material parameters shared by all corrosion features."""

    outside_diameter: float
    wall_thickness: float
    smys: float
    maop: float | None = None
    ultimate_tensile_strength: float | None = None


@dataclass(frozen=True)
class FeatureInput:
    """Per-feature metal-loss inputs from ILI or field measurement data."""

    depth: float
    length: float
    feature_id: str | None = None
    maop: float | None = None
    ultimate_tensile_strength: float | None = None
    profile: tuple[ProfilePoint, ...] | None = None


@dataclass(frozen=True)
class AnalysisSettings:
    """Method settings for a configuration-driven analysis run."""

    safety_factor: float = 0.72
    flow_stress_increment: float = 10_000.0
    include_rstreng: bool = True


@dataclass(frozen=True)
class AnalysisConfig:
    """Complete pipeline analysis configuration loaded from an input file."""

    pipeline: PipelineParameters
    features: tuple[FeatureInput, ...]
    settings: AnalysisSettings = field(default_factory=AnalysisSettings)


def _optional_float(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number or null")
    return float(value)


def _required_float(mapping: Mapping[str, Any], key: str, context: str) -> float:
    if key not in mapping:
        raise ValueError(f"{context} is missing required field {key!r}")
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context}.{key} must be a number")
    return float(value)


def _optional_bool(value: Any, name: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false")
    return value


def _profile_points(raw_profile: Any, context: str) -> tuple[ProfilePoint, ...] | None:
    if raw_profile is None:
        return None
    if not isinstance(raw_profile, list):
        raise ValueError(f"{context}.profile must be a list of [position, depth] pairs")

    points: list[ProfilePoint] = []
    for index, point in enumerate(raw_profile):
        if not isinstance(point, list | tuple) or len(point) != 2:
            raise ValueError(f"{context}.profile[{index}] must be [position, depth]")
        position, depth = point
        if isinstance(position, bool) or not isinstance(position, (int, float)):
            raise ValueError(f"{context}.profile[{index}][0] must be a number")
        if isinstance(depth, bool) or not isinstance(depth, (int, float)):
            raise ValueError(f"{context}.profile[{index}][1] must be a number")
        points.append((float(position), float(depth)))
    return tuple(points)


def config_from_mapping(data: Mapping[str, Any]) -> AnalysisConfig:
    """Build an :class:`AnalysisConfig` from a parsed JSON-style mapping."""

    raw_pipeline = data.get("pipeline")
    if not isinstance(raw_pipeline, Mapping):
        raise ValueError("configuration must include a 'pipeline' object")

    pipeline = PipelineParameters(
        outside_diameter=_required_float(raw_pipeline, "outside_diameter", "pipeline"),
        wall_thickness=_required_float(raw_pipeline, "wall_thickness", "pipeline"),
        smys=_required_float(raw_pipeline, "smys", "pipeline"),
        maop=_optional_float(raw_pipeline.get("maop"), "pipeline.maop"),
        ultimate_tensile_strength=_optional_float(
            raw_pipeline.get("ultimate_tensile_strength"),
            "pipeline.ultimate_tensile_strength",
        ),
    )

    raw_settings = data.get("analysis", {})
    if not isinstance(raw_settings, Mapping):
        raise ValueError("configuration 'analysis' field must be an object when provided")
    safety_factor = _optional_float(raw_settings.get("safety_factor"), "analysis.safety_factor")
    flow_stress_increment = _optional_float(
        raw_settings.get("flow_stress_increment"),
        "analysis.flow_stress_increment",
    )
    settings = AnalysisSettings(
        safety_factor=0.72 if safety_factor is None else safety_factor,
        flow_stress_increment=10_000.0
        if flow_stress_increment is None
        else flow_stress_increment,
        include_rstreng=_optional_bool(
            raw_settings.get("include_rstreng"),
            "analysis.include_rstreng",
            default=True,
        ),
    )

    raw_features = data.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise ValueError("configuration must include a non-empty 'features' list")

    features: list[FeatureInput] = []
    for index, raw_feature in enumerate(raw_features):
        context = f"features[{index}]"
        if not isinstance(raw_feature, Mapping):
            raise ValueError(f"{context} must be an object")
        feature_id = raw_feature.get("feature_id")
        if feature_id is not None and not isinstance(feature_id, str):
            raise ValueError(f"{context}.feature_id must be a string or null")
        features.append(
            FeatureInput(
                feature_id=feature_id,
                depth=_required_float(raw_feature, "depth", context),
                length=_required_float(raw_feature, "length", context),
                maop=_optional_float(raw_feature.get("maop"), f"{context}.maop"),
                ultimate_tensile_strength=_optional_float(
                    raw_feature.get("ultimate_tensile_strength"),
                    f"{context}.ultimate_tensile_strength",
                ),
                profile=_profile_points(raw_feature.get("profile"), context),
            )
        )

    return AnalysisConfig(pipeline=pipeline, features=tuple(features), settings=settings)


def load_config(path: str | Path) -> AnalysisConfig:
    """Load an analysis configuration from a JSON file."""

    with Path(path).open(encoding="utf-8") as file:
        raw_data = json.load(file)
    if not isinstance(raw_data, Mapping):
        raise ValueError("top-level configuration must be a JSON object")
    return config_from_mapping(raw_data)


def _feature_from_config(pipeline: PipelineParameters, feature: FeatureInput) -> CorrosionFeature:
    return CorrosionFeature(
        outside_diameter=pipeline.outside_diameter,
        wall_thickness=pipeline.wall_thickness,
        smys=pipeline.smys,
        depth=feature.depth,
        length=feature.length,
        maop=feature.maop if feature.maop is not None else pipeline.maop,
        feature_id=feature.feature_id,
        ultimate_tensile_strength=feature.ultimate_tensile_strength
        if feature.ultimate_tensile_strength is not None
        else pipeline.ultimate_tensile_strength,
    )


def run_config(config: AnalysisConfig) -> list[dict[str, float | str | bool | int | None]]:
    """Run all configured corrosion features and return flat result records."""

    records: list[dict[str, float | str | bool | int | None]] = []
    for feature_input in config.features:
        feature = _feature_from_config(config.pipeline, feature_input)
        profile = feature_input.profile if config.settings.include_rstreng else None
        records.extend(
            compare_feature_records(
                feature,
                profile=profile,
                safety_factor=config.settings.safety_factor,
                flow_stress_increment=config.settings.flow_stress_increment,
            )
        )
    return records


def run_config_file(path: str | Path) -> list[dict[str, float | str | bool | int | None]]:
    """Load and run an analysis configuration file."""

    return run_config(load_config(path))


def write_records_csv(
    records: Iterable[Mapping[str, float | str | bool | int | None]],
    path: str | Path,
) -> None:
    """Write flat result records to a CSV file."""

    record_list = list(records)
    if not record_list:
        raise ValueError("records must contain at least one result")

    preferred_fields = [
        "feature_id",
        "method",
        "failure_pressure",
        "safe_pressure",
        "maop_ratio",
        "passes_maop",
        "flow_stress",
        "folias_factor",
        "area_ratio",
        "depth_ratio",
        "length_parameter",
    ]
    extra_fields = sorted(
        {key for record in record_list for key in record.keys()} - set(preferred_fields)
    )
    fieldnames = [field for field in preferred_fields if any(field in r for r in record_list)]
    fieldnames.extend(extra_fields)

    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(record_list)
