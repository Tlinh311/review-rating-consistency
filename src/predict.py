from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn

from src.config import DEFAULT_METADATA_PATH, DEFAULT_MODEL_PATH
from src.modeling import SUPPORTED_MODEL_ALIASES
from src.preprocessing import clean_text, count_tokens
_RESOURCE_CACHE: dict[tuple[str, str], tuple[Any, dict[str, Any]]] = {}


class ModelResourceError(RuntimeError):
    pass


class ReviewValidationError(ValueError):
    pass


def reset_resource_cache() -> None:
    _RESOURCE_CACHE.clear()


def load_resources(
    model_path: Path = DEFAULT_MODEL_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
    use_cache: bool = True,
) -> tuple[Any, dict[str, Any]]:
    model_path = model_path.resolve()
    metadata_path = metadata_path.resolve()
    cache_key = (str(model_path), str(metadata_path))
    if use_cache and cache_key in _RESOURCE_CACHE:
        return _RESOURCE_CACHE[cache_key]

    if not metadata_path.exists():
        raise ModelResourceError(
            f"Model metadata not found: {metadata_path}"
        )
    if not model_path.exists():
        raise ModelResourceError(f"Model artifact not found: {model_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    trained_version = metadata.get("libraries", {}).get("scikit_learn")
    if trained_version != sklearn.__version__:
        raise ModelResourceError(
            "Incompatible scikit-learn version. "
            f"Model uses {trained_version}, runtime uses {sklearn.__version__}."
        )

    pipeline = joblib.load(model_path)
    resources = (pipeline, metadata)
    if use_cache:
        _RESOURCE_CACHE[cache_key] = resources
    return resources


def validate_model_name(model_name: str | None) -> None:
    if model_name not in SUPPORTED_MODEL_ALIASES:
        raise ReviewValidationError(
            f"Model '{model_name}' is not supported."
        )


def predict_single_review(
    review_text: str,
    actual_rating: int,
    model_name: str | None = None,
    pipeline: Any = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_model_name(model_name)
    if not 1 <= int(actual_rating) <= 5:
        raise ReviewValidationError("Rating must be between 1 and 5.")

    cleaned_text = clean_text(review_text)
    if not cleaned_text:
        raise ReviewValidationError(
            "Review has no valid English words after preprocessing."
        )

    if pipeline is None or metadata is None:
        pipeline, metadata = load_resources()

    token_count = count_tokens(cleaned_text)
    probabilities = pipeline.predict_proba([review_text])[0]
    classes = pipeline.classes_
    predicted_rating = int(classes[int(np.argmax(probabilities))])
    top_score = float(np.max(probabilities))
    rating_gap = abs(int(actual_rating) - predicted_rating)
    uncertainty_threshold = float(
        metadata.get("uncertainty_threshold", {}).get("value", 0.45)
    )

    if token_count < 2 or top_score < uncertainty_threshold:
        status = "inconclusive"
    elif rating_gap <= 1:
        status = "consistent"
    else:
        status = "potential_mismatch"

    class_scores = {
        str(int(label)): round(float(score) * 100, 2)
        for label, score in zip(classes, probabilities)
    }
    return {
        "actual_rating": int(actual_rating),
        "predicted_rating": predicted_rating,
        "rating_gap": rating_gap,
        "class_scores": class_scores,
        "top_model_score": round(top_score * 100, 2),
        "cleaned_text": cleaned_text,
        "token_count": token_count,
        "status": status,
        "needs_review": status == "potential_mismatch",
    }
