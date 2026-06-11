import json
from pathlib import Path


METADATA_PATH = Path("models/model_metadata.json")


def test_production_model_meets_quality_thresholds():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    metrics = metadata["holdout_metrics"]

    assert metrics["macro_f1"] >= 0.54
    assert metrics["mae"] <= 0.50
    assert metrics["within_one_star"] >= 0.92
    assert metrics["recall_per_class"]["2"] >= 0.25
    assert metadata["split"]["group_overlap"] == 0
