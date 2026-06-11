from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.base import clone
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.utils.class_weight import compute_class_weight

from src.preprocessing import TextCleaner


RANDOM_STATE = 42
PRODUCTION_MODEL_NAME = "review_rating_logistic_regression"
SUPPORTED_MODEL_ALIASES = {
    None,
    "production",
    "logistic_regression",
    PRODUCTION_MODEL_NAME,
}

PRESERVED_STOP_WORDS = {
    "no",
    "not",
    "nor",
    "never",
    "none",
    "nothing",
    "neither",
    "very",
    "too",
}

DOMAIN_STOP_WORDS = {
    "place",
    "order",
    "ordered",
    "try",
    "tried",
    "go",
    "went",
    "came",
    "come",
    "got",
    "get",
    "time",
    "times",
    "people",
    "restaurant",
    "bit",
    "quite",
    "really",
    "just",
    "visit",
    "staff",
}


def get_stop_words() -> list[str]:
    stop_words = set(ENGLISH_STOP_WORDS).difference(PRESERVED_STOP_WORDS)
    stop_words.update(DOMAIN_STOP_WORDS)
    return sorted(stop_words)


def compute_soft_class_weights(
    y: Any,
    weight_power: float,
) -> dict[int, float]:
    labels = np.asarray(y)
    classes = np.unique(labels)
    balanced = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=labels,
    )
    return {
        int(label): float(weight**weight_power)
        for label, weight in zip(classes, balanced)
    }


class SoftBalancedLogisticRegression(LogisticRegression):
    def __init__(
        self,
        weight_power: float = 0.8,
        C: float = 0.5,
        max_iter: int = 700,
        solver: str = "lbfgs",
        random_state: int | None = RANDOM_STATE,
    ) -> None:
        self.weight_power = weight_power
        super().__init__(
            C=C,
            max_iter=max_iter,
            solver=solver,
            random_state=random_state,
        )

    def fit(
        self,
        X: Any,
        y: Any,
        sample_weight: Any = None,
    ) -> "SoftBalancedLogisticRegression":
        self.class_weight = compute_soft_class_weights(y, self.weight_power)
        return super().fit(X, y, sample_weight=sample_weight)


def build_feature_extractor() -> Pipeline:
    stop_words = get_stop_words()
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    max_features=12000,
                    stop_words=stop_words,
                    ngram_range=(1, 2),
                    min_df=2,
                    max_df=0.95,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "character",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=20000,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("cleaner", TextCleaner()),
            ("features", features),
        ]
    )


def build_classifier(
    weight_power: float = 0.8,
    C: float = 0.5,
) -> SoftBalancedLogisticRegression:
    return SoftBalancedLogisticRegression(
        weight_power=weight_power,
        C=C,
        max_iter=700,
        solver="lbfgs",
        random_state=RANDOM_STATE,
    )


def build_model_pipeline(
    weight_power: float = 0.8,
    C: float = 0.5,
) -> Pipeline:
    feature_pipeline = build_feature_extractor()
    return Pipeline(
        [
            ("cleaner", clone(feature_pipeline.named_steps["cleaner"])),
            ("features", clone(feature_pipeline.named_steps["features"])),
            ("classifier", build_classifier(weight_power=weight_power, C=C)),
        ]
    )
