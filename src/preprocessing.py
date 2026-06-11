import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


CONTRACTION_PATTERNS = (
    (re.compile(r"\bwon['’]t\b", re.IGNORECASE), "will not"),
    (re.compile(r"\bcan['’]t\b", re.IGNORECASE), "can not"),
    (re.compile(r"\bshan['’]t\b", re.IGNORECASE), "shall not"),
    (re.compile(r"n['’]t\b", re.IGNORECASE), " not"),
    (re.compile(r"['’]re\b", re.IGNORECASE), " are"),
    (re.compile(r"['’]ve\b", re.IGNORECASE), " have"),
    (re.compile(r"['’]ll\b", re.IGNORECASE), " will"),
    (re.compile(r"['’]m\b", re.IGNORECASE), " am"),
    (re.compile(r"['’]d\b", re.IGNORECASE), " would"),
)


def expand_contractions(text: str) -> str:
    expanded = text
    for pattern, replacement in CONTRACTION_PATTERNS:
        expanded = pattern.sub(replacement, expanded)
    return expanded


def clean_text(text: Any) -> str:
    if text is None or pd.isna(text):
        return ""

    normalized = expand_contractions(str(text).lower())
    normalized = re.sub(r"[^a-z\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def round_rating_half_up(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.floor(numeric + 0.5)


def count_tokens(text: str) -> int:
    return len(text.split()) if text else 0


def _rating_distribution(values: pd.Series) -> dict[str, int]:
    counts = values.value_counts().sort_index()
    return {str(int(key)): int(value) for key, value in counts.items()}


def prepare_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required_columns = {"Review", "Rating"}
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(
            "Dataset thiếu các cột bắt buộc: " + ", ".join(missing_columns)
        )

    working = df.copy()
    total_raw = len(working)
    raw_rating = pd.to_numeric(working["Rating"], errors="coerce")
    missing_rating = int(working["Rating"].isna().sum())
    non_numeric_rating = int(
        (working["Rating"].notna() & raw_rating.isna()).sum()
    )
    missing_review = int(working["Review"].isna().sum())
    half_star_count = int(
        np.isclose(raw_rating.dropna() % 1, 0.5).sum()
    )

    valid_base = raw_rating.notna() & working["Review"].notna()
    working = working.loc[valid_base].copy()
    working["Rating"] = round_rating_half_up(raw_rating.loc[valid_base]).astype(int)

    outside_rating = int((~working["Rating"].between(1, 5)).sum())
    working = working.loc[working["Rating"].between(1, 5)].copy()
    working["text_clean"] = working["Review"].map(clean_text)

    empty_after_cleaning = int(working["text_clean"].eq("").sum())
    working = working.loc[working["text_clean"].ne("")].copy()

    duplicate_pair_mask = working.duplicated(
        subset=["text_clean", "Rating"], keep="first"
    )
    duplicate_pairs_removed = int(duplicate_pair_mask.sum())
    duplicate_cleaned_text_rows = int(
        working["text_clean"].duplicated(keep=False).sum()
    )

    grouped = working.groupby("text_clean")["Rating"].nunique()
    conflicting_rating_groups = int((grouped > 1).sum())

    working = working.loc[~duplicate_pair_mask].reset_index(drop=True)
    clean_distribution = _rating_distribution(working["Rating"])
    total_clean = len(working)
    clean_percentages = {
        key: round(value / total_clean * 100, 2)
        for key, value in clean_distribution.items()
    }

    mostly_empty_columns = [
        str(column)
        for column in df.columns
        if total_raw and float(df[column].isna().mean()) >= 0.95
    ]

    report = {
        "total_raw": total_raw,
        "total_clean": total_clean,
        "removed_total": total_raw - total_clean,
        "missing_review": missing_review,
        "missing_rating": missing_rating,
        "non_numeric_rating": non_numeric_rating,
        "outside_rating": outside_rating,
        "half_star_count": half_star_count,
        "empty_after_cleaning": empty_after_cleaning,
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "duplicate_review_rows": int(
            df.loc[df["Review"].notna(), "Review"].duplicated().sum()
        ),
        "duplicate_cleaned_text_rows_before_deduplication": (
            duplicate_cleaned_text_rows
        ),
        "duplicate_pairs_removed": duplicate_pairs_removed,
        "conflicting_rating_groups": conflicting_rating_groups,
        "rating_distribution": clean_distribution,
        "rating_percentages": clean_percentages,
        "mostly_empty_columns": mostly_empty_columns,
    }
    return working, report


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    cleaned, _ = prepare_dataset(df)
    return cleaned


class TextCleaner(BaseEstimator, TransformerMixin):
    def fit(self, X: Any, y: Any = None) -> "TextCleaner":
        return self

    def transform(self, X: Any) -> list[str]:
        return [clean_text(value) for value in X]
