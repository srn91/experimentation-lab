from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = ROOT_DIR / "generated"
SIMULATION_CSV = GENERATED_DIR / "experiment_assignments.csv"
REPORT_JSON = GENERATED_DIR / "decision_report.json"

