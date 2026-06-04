import csv

from pipeline_integrity_tools import config_from_mapping, run_config, write_records_csv


def _sample_config_mapping():
    return {
        "pipeline": {
            "outside_diameter": 24.0,
            "wall_thickness": 0.375,
            "smys": 52_000.0,
            "ultimate_tensile_strength": 66_000.0,
            "maop": 1_000.0,
        },
        "analysis": {
            "safety_factor": 0.72,
            "flow_stress_increment": 10_000.0,
            "include_rstreng": True,
        },
        "features": [
            {
                "feature_id": "ILI-001",
                "depth": 0.150,
                "length": 8.0,
                "profile": [[0.0, 0.0], [4.0, 0.15], [8.0, 0.0]],
            },
            {
                "feature_id": "ILI-002",
                "depth": 0.100,
                "length": 5.5,
            },
        ],
    }


def test_config_from_mapping_groups_common_pipeline_parameters():
    config = config_from_mapping(_sample_config_mapping())

    assert config.pipeline.outside_diameter == 24.0
    assert config.pipeline.ultimate_tensile_strength == 66_000.0
    assert config.settings.include_rstreng is True
    assert config.features[0].feature_id == "ILI-001"
    assert config.features[0].profile == ((0.0, 0.0), (4.0, 0.15), (8.0, 0.0))


def test_run_config_returns_all_methods_per_feature():
    config = config_from_mapping(_sample_config_mapping())

    records = run_config(config)

    assert len(records) == 7
    assert {record["feature_id"] for record in records} == {"ILI-001", "ILI-002"}
    first_feature_methods = [
        record["method"] for record in records if record["feature_id"] == "ILI-001"
    ]
    assert first_feature_methods == [
        "Original B31G",
        "Modified B31G",
        "DNV RP-F101",
        "RSTRENG Effective Area",
    ]


def test_write_records_csv_outputs_analysis_table(tmp_path):
    records = run_config(config_from_mapping(_sample_config_mapping()))
    output_path = tmp_path / "results.csv"

    write_records_csv(records, output_path)

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["feature_id"] == "ILI-001"
    assert rows[0]["method"] == "Original B31G"
    assert "failure_pressure" in rows[0]
