from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

from src.config import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODELS_DIR,
    METADATA_FILENAME,
    MODEL_FILENAME,
    PROJECT_ROOT,
)
from src.modeling import (
    PRODUCTION_MODEL_NAME,
    RANDOM_STATE,
    build_classifier,
    build_feature_extractor,
    build_model_pipeline,
    compute_soft_class_weights,
)
from src.preprocessing import prepare_dataset


WEIGHT_POWERS = (0.65, 0.8, 1.0)
C_VALUES = (0.25, 0.5, 1.0)


def dataset_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_holdout_split(
    df: pd.DataFrame,
    random_state: int = RANDOM_STATE,
) -> tuple[np.ndarray, np.ndarray]:
    splitter = StratifiedGroupKFold(
        n_splits=5,
        shuffle=True,
        random_state=random_state,
    )
    train_index, test_index = next(
        splitter.split(
            df["Review"],
            df["Rating"],
            groups=df["text_clean"],
        )
    )
    return train_index, test_index


def make_inner_splits(
    df: pd.DataFrame,
    random_state: int = RANDOM_STATE + 1,
) -> list[tuple[np.ndarray, np.ndarray]]:
    splitter = StratifiedGroupKFold(
        n_splits=3,
        shuffle=True,
        random_state=random_state,
    )
    return list(
        splitter.split(
            df["Review"],
            df["Rating"],
            groups=df["text_clean"],
        )
    )


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict[str, Any]:
    labels = np.array([1, 2, 3, 4, 5])
    recalls = recall_score(
        y_true,
        y_pred,
        labels=labels,
        average=None,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted")),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "within_one_star": float(
            (np.abs(y_true - y_pred) <= 1).mean()
        ),
        "recall_per_class": {
            str(label): float(value)
            for label, value in zip(labels, recalls)
        },
        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=labels,
        ).tolist(),
    }


def _candidate_key(weight_power: float, C: float) -> str:
    return f"weight_power={weight_power}|C={C}"


def tune_logistic_regression(
    train_df: pd.DataFrame,
) -> tuple[dict[str, float], list[dict[str, Any]], np.ndarray, np.ndarray]:
    splits = make_inner_splits(train_df)
    y_all = train_df["Rating"].to_numpy()
    candidate_records: dict[str, list[dict[str, float]]] = {}
    oof_predictions: dict[str, np.ndarray] = {}
    oof_probabilities: dict[str, np.ndarray] = {}

    for weight_power in WEIGHT_POWERS:
        for C in C_VALUES:
            key = _candidate_key(weight_power, C)
            candidate_records[key] = []
            oof_predictions[key] = np.zeros(len(train_df), dtype=int)
            oof_probabilities[key] = np.zeros((len(train_df), 5), dtype=float)

    for fold_number, (fit_index, validation_index) in enumerate(splits, start=1):
        feature_extractor = build_feature_extractor()
        X_fit = feature_extractor.fit_transform(
            train_df.iloc[fit_index]["Review"]
        )
        X_validation = feature_extractor.transform(
            train_df.iloc[validation_index]["Review"]
        )
        y_fit = y_all[fit_index]
        y_validation = y_all[validation_index]

        for weight_power in WEIGHT_POWERS:
            for C in C_VALUES:
                key = _candidate_key(weight_power, C)
                classifier = build_classifier(
                    weight_power=weight_power,
                    C=C,
                )
                started_at = time.perf_counter()
                classifier.fit(X_fit, y_fit)
                predictions = classifier.predict(X_validation)
                probabilities = classifier.predict_proba(X_validation)
                fit_seconds = time.perf_counter() - started_at

                metrics = evaluate_predictions(y_validation, predictions)
                candidate_records[key].append(
                    {
                        "fold": float(fold_number),
                        "macro_f1": metrics["macro_f1"],
                        "weighted_f1": metrics["weighted_f1"],
                        "mae": metrics["mae"],
                        "fit_seconds": fit_seconds,
                    }
                )
                oof_predictions[key][validation_index] = predictions
                oof_probabilities[key][validation_index] = probabilities

    summary: list[dict[str, Any]] = []
    for weight_power in WEIGHT_POWERS:
        for C in C_VALUES:
            key = _candidate_key(weight_power, C)
            records = candidate_records[key]
            summary.append(
                {
                    "weight_power": weight_power,
                    "C": C,
                    "macro_f1": float(
                        np.mean([record["macro_f1"] for record in records])
                    ),
                    "weighted_f1": float(
                        np.mean([record["weighted_f1"] for record in records])
                    ),
                    "mae": float(
                        np.mean([record["mae"] for record in records])
                    ),
                    "fit_seconds": float(
                        np.mean([record["fit_seconds"] for record in records])
                    ),
                }
            )

    ranked = sorted(
        summary,
        key=lambda item: (
            -item["macro_f1"],
            item["mae"],
            -item["weighted_f1"],
            item["fit_seconds"],
        ),
    )
    selected = {
        "weight_power": float(ranked[0]["weight_power"]),
        "C": float(ranked[0]["C"]),
    }
    selected_key = _candidate_key(
        selected["weight_power"],
        selected["C"],
    )
    return (
        selected,
        ranked,
        oof_predictions[selected_key],
        oof_probabilities[selected_key],
    )


def select_uncertainty_threshold(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    probabilities: np.ndarray,
    minimum_accuracy: float = 0.70,
    minimum_coverage: float = 0.30,
    fallback: float = 0.45,
) -> dict[str, float]:
    scores = probabilities.max(axis=1)
    for threshold in np.arange(0.20, 0.951, 0.01):
        covered = scores >= threshold
        coverage = float(covered.mean())
        if coverage < minimum_coverage:
            continue
        accuracy = float(accuracy_score(y_true[covered], y_pred[covered]))
        if accuracy >= minimum_accuracy:
            return {
                "value": round(float(threshold), 2),
                "coverage": coverage,
                "accuracy": accuracy,
            }

    covered = scores >= fallback
    return {
        "value": fallback,
        "coverage": float(covered.mean()),
        "accuracy": (
            float(accuracy_score(y_true[covered], y_pred[covered]))
            if covered.any()
            else 0.0
        ),
    }


def compare_baselines(
    train_df: pd.DataFrame,
    selected: dict[str, float],
) -> list[dict[str, Any]]:
    splits = make_inner_splits(train_df)
    y_all = train_df["Rating"].to_numpy()
    prediction_store = {
        "weighted_logistic_regression": np.zeros(len(train_df), dtype=int),
        "unweighted_logistic_regression": np.zeros(len(train_df), dtype=int),
        "linear_svm": np.zeros(len(train_df), dtype=int),
        "complement_naive_bayes": np.zeros(len(train_df), dtype=int),
    }

    for fit_index, validation_index in splits:
        feature_extractor = build_feature_extractor()
        X_fit = feature_extractor.fit_transform(
            train_df.iloc[fit_index]["Review"]
        )
        X_validation = feature_extractor.transform(
            train_df.iloc[validation_index]["Review"]
        )
        y_fit = y_all[fit_index]

        soft_weights = compute_soft_class_weights(
            y_fit,
            selected["weight_power"],
        )
        models = {
            "weighted_logistic_regression": build_classifier(
                weight_power=selected["weight_power"],
                C=selected["C"],
            ),
            "unweighted_logistic_regression": LogisticRegression(
                C=selected["C"],
                max_iter=700,
                solver="lbfgs",
                random_state=RANDOM_STATE,
            ),
            "linear_svm": LinearSVC(
                C=0.7,
                class_weight=soft_weights,
                random_state=RANDOM_STATE,
            ),
            "complement_naive_bayes": ComplementNB(alpha=0.5),
        }

        for name, model in models.items():
            model.fit(X_fit, y_fit)
            prediction_store[name][validation_index] = model.predict(
                X_validation
            )

    comparison = []
    for name, predictions in prediction_store.items():
        metrics = evaluate_predictions(y_all, predictions)
        comparison.append(
            {
                "name": name,
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "weighted_f1": metrics["weighted_f1"],
                "mae": metrics["mae"],
                "within_one_star": metrics["within_one_star"],
            }
        )
    return sorted(comparison, key=lambda item: -item["macro_f1"])


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def validate_quality(metrics: dict[str, Any]) -> None:
    failures = []
    if metrics["macro_f1"] < 0.54:
        failures.append("macro_f1 < 0.54")
    if metrics["mae"] > 0.50:
        failures.append("mae > 0.50")
    if metrics["within_one_star"] < 0.92:
        failures.append("within_one_star < 0.92")
    if metrics["recall_per_class"]["2"] < 0.25:
        failures.append("recall for class 2 < 0.25")
    if failures:
        raise RuntimeError(
            "Model failed quality criteria: " + ", ".join(failures)
        )


def train_model(
    data_path: Path = DEFAULT_DATA_PATH,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> dict[str, Any]:
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")

    raw_df = pd.read_csv(data_path)
    clean_df, data_report = prepare_dataset(raw_df)
    train_index, test_index = make_holdout_split(clean_df)
    train_df = clean_df.iloc[train_index].reset_index(drop=True)
    test_df = clean_df.iloc[test_index].reset_index(drop=True)

    overlap = set(train_df["text_clean"]).intersection(test_df["text_clean"])
    if overlap:
        raise RuntimeError("Duplicate clean_text detected between train and test")
 
    print(f"Original data size: {len(raw_df)}")
    print(f"Cleaned data size: {len(clean_df)}")
    print(f"Train: {len(train_df)} | Test: {len(test_df)}")
    print("Tuning hyperparameters using group cross-validation")

    selected, tuning_results, oof_pred, oof_prob = (
        tune_logistic_regression(train_df)
    )
    threshold = select_uncertainty_threshold(
        train_df["Rating"].to_numpy(),
        oof_pred,
        oof_prob,
    )
    print(
        "Selected configuration: "
        f"weight_power={selected['weight_power']}, C={selected['C']}"
    )
 
    print("Comparing baseline models")
    comparison = compare_baselines(train_df, selected)

    pipeline = build_model_pipeline(
        weight_power=selected["weight_power"],
        C=selected["C"],
    )
    fit_started = time.perf_counter()
    pipeline.fit(train_df["Review"], train_df["Rating"])
    final_fit_seconds = time.perf_counter() - fit_started

    test_predictions = pipeline.predict(test_df["Review"])
    holdout_metrics = evaluate_predictions(
        test_df["Rating"].to_numpy(),
        test_predictions,
    )
    validate_quality(holdout_metrics)

    classifier = pipeline.named_steps["classifier"]
    metadata = {
        "schema_version": 1,
        "model_name": PRODUCTION_MODEL_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "path": str(data_path.relative_to(PROJECT_ROOT)),
            "sha256": dataset_sha256(data_path),
        },
        "libraries": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "split": {
            "strategy": "StratifiedGroupKFold",
            "group": "text_clean",
            "random_state": RANDOM_STATE,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "group_overlap": 0,
        },
        "features": {
            "word_tfidf": {
                "ngram_range": [1, 2],
                "max_features": 12000,
                "min_df": 2,
                "max_df": 0.95,
                "sublinear_tf": True,
            },
            "character_tfidf": {
                "analyzer": "char_wb",
                "ngram_range": [3, 5],
                "max_features": 20000,
                "min_df": 2,
                "sublinear_tf": True,
            },
        },
        "selected_parameters": selected,
        "class_weights": classifier.class_weight,
        "uncertainty_threshold": threshold,
        "tuning_results": tuning_results,
        "model_comparison": comparison,
        "holdout_metrics": holdout_metrics,
        "final_fit_seconds": final_fit_seconds,
        "data_report": data_report,
        "limitations": [
            "The model measures consistency between English text and rating.",
            "Results do not prove that a review is fake or spam.",
            "The model score is an internal score not calibrated to probabilities.",
            "Reviews that are too short or have low model scores return as inconclusive.",
        ],
    }

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / MODEL_FILENAME
    metadata_path = models_dir / METADATA_FILENAME
    temporary_model_path = models_dir / f"{MODEL_FILENAME}.tmp"
    temporary_metadata_path = models_dir / f"{METADATA_FILENAME}.tmp"

    joblib.dump(pipeline, temporary_model_path)
    temporary_model_path.replace(model_path)
    temporary_metadata_path.write_text(
        json.dumps(
            _json_ready(metadata),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary_metadata_path.replace(metadata_path)

    print(f"Saved model to: {model_path}")
    print(f"Saved metadata to: {metadata_path}")
    print(
        "Holdout macro-F1: "
        f"{holdout_metrics['macro_f1']:.4f} | "
        f"MAE: {holdout_metrics['mae']:.4f} | "
        f"Within-one-star: {holdout_metrics['within_one_star']:.4f}"
    )
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train model for review consistency analysis"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to CSV dataset",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help="Directory to save model artifacts",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    try:
        train_model(
            data_path=arguments.data.resolve(),
            models_dir=arguments.models_dir.resolve(),
        )
    except Exception as error:
        print(f"Training failed: {error}", file=sys.stderr)
        raise
