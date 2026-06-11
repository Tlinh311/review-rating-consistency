import pandas as pd

from src.preprocessing import (
    clean_text,
    prepare_dataset,
    round_rating_half_up,
)


def test_half_up_rating_rounding():
    values = pd.Series([1.5, 2.5, 3.5, 4.5])
    assert round_rating_half_up(values).tolist() == [2.0, 3.0, 4.0, 5.0]


def test_contractions_and_negation_are_preserved():
    assert clean_text("This wasn't very good") == "this was not very good"
    assert clean_text("I can't recommend it") == "i can not recommend it"
    assert clean_text("not good") != clean_text("good")


def test_prepare_dataset_removes_invalid_empty_and_duplicate_pairs():
    raw = pd.DataFrame(
        {
            "Review": [
                "Good food",
                "Good food",
                "Good food",
                "12345",
                None,
                "Bad food",
            ],
            "Rating": [4, 4, 5, 3, 2, "Like"],
        }
    )

    cleaned, report = prepare_dataset(raw)

    assert len(cleaned) == 2
    assert sorted(cleaned["Rating"].tolist()) == [4, 5]
    assert report["duplicate_pairs_removed"] == 1
    assert report["empty_after_cleaning"] == 1
    assert report["missing_review"] == 1
    assert report["non_numeric_rating"] == 1
    assert report["conflicting_rating_groups"] == 1
