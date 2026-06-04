# Pipeline Integrity Tools

Pipeline Integrity Tools is a Python package for screening pipeline corrosion
features from in-line inspection (ILI) data.  The deterministic corrosion
failure-pressure calculations can be used directly or as likelihood/model
components in Bayesian pipeline integrity workflows.

## Supported corrosion assessment methods

The package now returns side-by-side results for:

- **Original ASME B31G** using the original parabolic-area approximation
  (`2/3 d/t`) and the original Folias factor for short defects.
- **Modified B31G** using the `0.85 dL` Level 1 area approximation and the
  modified Folias factor.
- **DNV RP-F101** single-defect corrosion assessment using tensile strength and
  the DNV bulging factor.
- **RSTRENG effective area** using an axial river-bottom profile from ILI or
  field measurements and selecting the critical contiguous effective-area
  window.

> Engineering note: these functions implement deterministic screening equations.
> Confirm applicability, units, safety factors, and regulatory requirements with
> the governing code and a qualified pipeline integrity engineer before making
> operating or repair decisions.

## Installation for development

```bash
python -m pip install -e .
```

## Example

```python
from pipeline_integrity_tools import CorrosionFeature, compare_methods

feature = CorrosionFeature(
    outside_diameter=24.0,  # in
    wall_thickness=0.375,   # in
    smys=52_000.0,          # psi
    depth=0.150,            # in
    length=8.0,             # in
    maop=1_000.0,           # psi
    ultimate_tensile_strength=66_000.0,  # psi, for DNV RP-F101
)

# RSTRENG profile: (axial position, metal-loss depth)
profile = [
    (0.0, 0.00),
    (2.0, 0.10),
    (4.0, 0.15),
    (6.0, 0.12),
    (8.0, 0.00),
]

for result in compare_methods(feature, profile=profile):
    print(
        result.method,
        round(result.failure_pressure, 2),
        round(result.safe_pressure, 2),
        result.passes_maop,
    )
```

All dimensions must use a consistent unit system.  If diameter, wall thickness,
depth, and length are inches and strength is psi, pressures are returned in psi.
For Modified B31G and RSTRENG in SI units, pass the equivalent
`flow_stress_increment` (for example, `68.9476` MPa instead of the default
`10_000` psi).  For DNV RP-F101, provide `ultimate_tensile_strength` in the same
stress units used for the other material strengths.

## API overview

- `CorrosionFeature`: pipe, material, and corrosion-feature inputs.
- `original_b31g(feature, safety_factor=0.72)`: original B31G result.
- `modified_b31g(feature, safety_factor=0.72, flow_stress_increment=10_000)`: Modified B31G result.
- `dnv_rp_f101(feature, safety_factor=0.72, ultimate_tensile_strength=None)`: DNV RP-F101 single-defect result.
- `rstreng_effective_area(feature, profile, safety_factor=0.72, flow_stress_increment=10_000)`: RSTRENG-style
  effective-area result from river-bottom profile points.
- `compare_methods(feature, profile=None, safety_factor=0.72, flow_stress_increment=10_000, ultimate_tensile_strength=None)`: returns all
  requested method results for analysis.
- `compare_feature_records(feature, profile=None, safety_factor=0.72, flow_stress_increment=10_000, ultimate_tensile_strength=None)`: returns
  flat dictionaries that can be written to CSV or loaded into a dataframe.

Each result is an `AssessmentResult` dataclass containing failure pressure, safe
pressure, flow stress or tensile strength, Folias factor, area ratio, depth
ratio, length parameter, and optional MAOP pass/fail information.
