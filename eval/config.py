from pathlib import Path

DATASET_PATH    = Path(__file__).parent / "golden_dataset.json"
RESULTS_DIR     = Path(__file__).parent / "results"
PASS_THRESHOLD  = 70    # % score to count a case as passed
SCORE_THRESHOLD = 80    # % overall to exit with code 0
RATE_LIMIT_SEC  = 0.5   # pause between API calls

SEVERITY_WEIGHTS = {
    "critical": 1.0,
    "high":     0.8,
    "medium":   0.5,
    "low":      0.3,
}