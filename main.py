"""Run pipeline corrosion analysis from the shared input file.

Edit ``pipeline_input.json`` to change pipe parameters, material properties,
analysis settings, corrosion features, and optional RSTRENG profiles.  Then run:

    python main.py --input pipeline_input.json --output analysis_results.csv
"""

from pipeline_integrity_tools.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
