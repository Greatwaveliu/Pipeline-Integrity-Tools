# Pipeline Integrity Tools User Guide

This guide explains how to use the `pipeline_integrity_tools` package to run
pipeline corrosion remaining-strength assessments from in-line inspection (ILI)
metal-loss data.

The package supports these deterministic assessment methods:

- Original ASME B31G
- Modified B31G
- DNV RP-F101 single-defect assessment
- RSTRENG-style effective-area assessment

> **Engineering caution:** The package provides calculation utilities for
> engineering screening and analysis. Confirm method applicability, input units,
> safety factors, regulatory requirements, and final decisions with the governing
> code and a qualified pipeline integrity engineer.

## 1. Where the files are

The repository is organized so each model lives in a clearly named module:

| File | Purpose |
| --- | --- |
| `pipeline_integrity_tools/b31g.py` | Original B31G and Modified B31G calculations. |
| `pipeline_integrity_tools/dnv.py` | DNV RP-F101 calculation. |
| `pipeline_integrity_tools/rstreng.py` | RSTRENG-style effective-area calculation. |
| `pipeline_integrity_tools/models.py` | Shared `CorrosionFeature` and `AssessmentResult` data models plus common helpers. |
| `pipeline_integrity_tools/analysis.py` | Runs all methods side-by-side for one feature. |
| `pipeline_integrity_tools/config.py` | Loads a JSON input file, runs batch analysis, and writes CSV output. |
| `pipeline_integrity_tools/cli.py` | Command-line interface used by `main.py` and the `pipeline-analysis` script. |
| `pipeline_input.json` | Example input file where day-to-day pipeline parameters and ILI features are edited. |
| `main.py` | Simple runner for the JSON input workflow. |

## 2. Installation

From the repository root, install the package in editable/development mode:

```bash
python -m pip install -e .
```

After installation, you can use either:

```bash
python main.py --input pipeline_input.json --output analysis_results.csv
```

or the console script:

```bash
pipeline-analysis --input pipeline_input.json --output analysis_results.csv
```

## 3. Recommended workflow: edit one JSON file

For a specific pipeline, start by editing `pipeline_input.json`. This keeps the
basic pipe parameters, analysis settings, and corrosion-feature data together in
one place.

### 3.1 JSON structure

```json
{
  "pipeline": {
    "outside_diameter": 24.0,
    "wall_thickness": 0.375,
    "smys": 52000.0,
    "ultimate_tensile_strength": 66000.0,
    "maop": 1000.0
  },
  "analysis": {
    "safety_factor": 0.72,
    "flow_stress_increment": 10000.0,
    "include_rstreng": true
  },
  "features": [
    {
      "feature_id": "ILI-001",
      "depth": 0.15,
      "length": 8.0,
      "profile": [
        [0.0, 0.0],
        [2.0, 0.10],
        [4.0, 0.15],
        [6.0, 0.12],
        [8.0, 0.0]
      ]
    }
  ]
}
```

### 3.2 `pipeline` fields

These values apply to every feature unless a feature overrides a supported
field.

| Field | Required? | Meaning |
| --- | --- | --- |
| `outside_diameter` | Yes | Pipe outside diameter, `D`. |
| `wall_thickness` | Yes | Nominal wall thickness, `t`. |
| `smys` | Yes | Specified minimum yield strength. |
| `ultimate_tensile_strength` | No | Tensile strength used by DNV RP-F101. If omitted, DNV falls back to SMYS and marks this in result details. |
| `maop` | No | Maximum allowable operating pressure used for `maop_ratio` and `passes_maop`. |

### 3.3 `analysis` fields

| Field | Default | Meaning |
| --- | --- | --- |
| `safety_factor` | `0.72` | Multiplies calculated failure pressure to produce `safe_pressure`. |
| `flow_stress_increment` | `10000.0` | Added to SMYS for Modified B31G and RSTRENG flow stress. Use `10000` for psi or an equivalent value such as `68.9476` for MPa. |
| `include_rstreng` | `true` | When true, features with a `profile` also get an RSTRENG effective-area result. |

### 3.4 `features` fields

Each item in `features` is one corrosion feature from ILI or field data.

| Field | Required? | Meaning |
| --- | --- | --- |
| `feature_id` | No | Identifier carried into CSV output. |
| `depth` | Yes | Maximum metal-loss depth, `d`. Must be less than wall thickness. |
| `length` | Yes | Axial corrosion length, `L`. |
| `maop` | No | Optional feature-level MAOP override. |
| `ultimate_tensile_strength` | No | Optional feature-level DNV tensile-strength override. |
| `profile` | No | RSTRENG river-bottom profile as `[position, depth]` pairs. Required only for RSTRENG output. |

## 4. Running the analysis

From the repository root:

```bash
python main.py --input pipeline_input.json --output analysis_results.csv
```

The command prints a summary table and writes a CSV file. The default output file
name is `analysis_results.csv`, which is ignored by git because it is generated
analysis output.

Example console output columns:

| Column | Meaning |
| --- | --- |
| `feature_id` | Feature identifier from the input file. |
| `method` | Assessment method name. |
| `failure_pressure` | Calculated predicted failure pressure. |
| `safe_pressure` | `failure_pressure * safety_factor`. |
| `passes_maop` | `true` if `safe_pressure >= maop`, `false` if not, blank when no MAOP is supplied. |

## 5. Understanding CSV output

`write_records_csv` writes a flat table suitable for Excel, pandas, or Bayesian
post-processing.

Common output columns include:

| Column | Meaning |
| --- | --- |
| `feature_id` | Feature identifier. |
| `method` | Original B31G, Modified B31G, DNV RP-F101, or RSTRENG Effective Area. |
| `failure_pressure` | Calculated failure pressure in the same pressure units as input strength. |
| `safe_pressure` | Failure pressure multiplied by safety factor. |
| `maop_ratio` | `safe_pressure / maop` when MAOP is provided. |
| `passes_maop` | MAOP pass/fail indicator when MAOP is provided. |
| `flow_stress` | Flow stress or tensile strength used by the method. |
| `folias_factor` | Bulging/Folias factor when applicable. |
| `area_ratio` | Method-specific metal-loss area/depth ratio. |
| `depth_ratio` | `depth / wall_thickness`. |
| `length_parameter` | `length^2 / (outside_diameter * wall_thickness)`. |

Some methods also include `detail_*` columns. For example:

- Original B31G includes `detail_branch` (`short_defect` or `long_defect`).
- DNV RP-F101 includes `detail_strength_source` (`feature`, `argument`, or
  `smys_fallback`).
- RSTRENG includes critical profile window positions and indices.

## 6. Unit rules

Use one consistent unit system in each run.

### Imperial example

- Diameter, wall thickness, depth, length: inches
- Strengths and MAOP: psi
- `flow_stress_increment`: `10000.0`
- Output pressures: psi

### SI example

- Diameter, wall thickness, depth, length: millimetres
- Strengths and MAOP: MPa
- `flow_stress_increment`: `68.9476` MPa instead of `10000.0` psi
- Output pressures: MPa

The package does not perform automatic unit conversion.

## 7. Programmatic Python usage

### 7.1 Run all methods for one feature

```python
from pipeline_integrity_tools import CorrosionFeature, compare_methods

feature = CorrosionFeature(
    outside_diameter=24.0,
    wall_thickness=0.375,
    smys=52_000.0,
    depth=0.150,
    length=8.0,
    maop=1_000.0,
    ultimate_tensile_strength=66_000.0,
)

profile = [
    (0.0, 0.00),
    (2.0, 0.10),
    (4.0, 0.15),
    (6.0, 0.12),
    (8.0, 0.00),
]

results = compare_methods(feature, profile=profile)
for result in results:
    print(result.method, result.failure_pressure, result.safe_pressure)
```

### 7.2 Run one method directly

```python
from pipeline_integrity_tools import CorrosionFeature
from pipeline_integrity_tools.b31g import modified_b31g
from pipeline_integrity_tools.dnv import dnv_rp_f101
from pipeline_integrity_tools.rstreng import rstreng_effective_area

feature = CorrosionFeature(24.0, 0.375, 52_000.0, 0.150, 8.0)

modified = modified_b31g(feature)
dnv = dnv_rp_f101(feature, ultimate_tensile_strength=66_000.0)
rstreng = rstreng_effective_area(feature, [(0.0, 0.0), (4.0, 0.15), (8.0, 0.0)])
```

### 7.3 Load and run a JSON config from Python

```python
from pipeline_integrity_tools import run_config_file, write_records_csv

records = run_config_file("pipeline_input.json")
write_records_csv(records, "analysis_results.csv")
```

## 8. Method-specific notes

### 8.1 Original B31G

Function: `pipeline_integrity_tools.b31g.original_b31g`

- Uses flow stress `1.1 * SMYS`.
- Uses a short-defect branch with area ratio `(2/3) * (d/t)`.
- Uses a long-defect branch when `L^2 / (D*t) > 20`.

### 8.2 Modified B31G

Function: `pipeline_integrity_tools.b31g.modified_b31g`

- Uses area ratio `0.85 * (d/t)`.
- Uses flow stress `SMYS + flow_stress_increment`.
- Default `flow_stress_increment` is `10000.0`, appropriate for psi inputs.

### 8.3 DNV RP-F101

Function: `pipeline_integrity_tools.dnv.dnv_rp_f101`

- Uses tensile strength rather than yield strength when
  `ultimate_tensile_strength` is provided.
- Tensile strength can be set globally in `pipeline_input.json` under
  `pipeline.ultimate_tensile_strength` or per feature under
  `features[].ultimate_tensile_strength`.
- If tensile strength is omitted, the function falls back to SMYS and records
  `detail_strength_source = smys_fallback`.

### 8.4 RSTRENG effective area

Function: `pipeline_integrity_tools.rstreng.rstreng_effective_area`

- Requires a river-bottom profile as `[position, metal_loss_depth]` pairs in
  JSON or `(position, depth)` tuples in Python.
- The profile positions must be unique and increasing after sorting.
- The function evaluates contiguous profile windows and returns the lowest
  predicted failure pressure as the critical effective-area result.
- If `include_rstreng` is `true` but a feature has no `profile`, that feature is
  still evaluated with Original B31G, Modified B31G, and DNV RP-F101 only.

## 9. Input validation and common errors

| Error | Likely cause | Fix |
| --- | --- | --- |
| `depth must be less than wall_thickness` | Metal-loss depth is greater than or equal to nominal wall thickness. | Check depth units and ILI import values. |
| `profile must contain at least two...` | RSTRENG profile has fewer than two points. | Add at least start/end profile points. |
| `profile positions must be unique...` | Repeated axial positions in RSTRENG profile. | Remove duplicates or combine readings. |
| `flow_stress_increment must be positive` | Zero or negative Modified B31G/RSTRENG increment. | Use `10000.0` psi or equivalent SI value. |
| No RSTRENG row in CSV | Feature does not include a profile, or `include_rstreng` is false. | Add a `profile` for that feature and enable `include_rstreng`. |

## 10. Suggested analysis process

1. Copy `pipeline_input.json` for the pipeline or segment you want to analyze.
2. Enter common pipe/material data in the `pipeline` object.
3. Enter assessment settings in the `analysis` object.
4. Add each ILI corrosion feature to the `features` list.
5. Add `profile` points for features where RSTRENG effective-area output is
   needed.
6. Run `python main.py --input your_input.json --output your_results.csv`.
7. Review the printed summary and the CSV output.
8. Use the CSV output for comparisons, plots, Bayesian updating, or reporting.
