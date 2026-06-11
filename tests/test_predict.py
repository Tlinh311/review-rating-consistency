import warnings

from sklearn.exceptions import InconsistentVersionWarning

from src.predict import (
    ReviewValidationError,
    load_resources,
    predict_single_review,
)


def test_artifact_loads_without_version_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pipeline, metadata = load_resources(use_cache=False)

    version_warnings = [
        item for item in caught
        if issubclass(item.category, InconsistentVersionWarning)
    ]
    assert version_warnings == []
    assert metadata["model_name"] == "review_rating_logistic_regression"
    assert pipeline.classes_.tolist() == [1, 2, 3, 4, 5]


def test_prediction_statuses():
    pipeline, metadata = load_resources()

    consistent = predict_single_review(
        "The food was excellent and the service was friendly.",
        5,
        pipeline=pipeline,
        metadata=metadata,
    )
    mismatch = predict_single_review(
        "Terrible cold food and rude service.",
        5,
        pipeline=pipeline,
        metadata=metadata,
    )
    inconclusive = predict_single_review(
        "good",
        5,
        pipeline=pipeline,
        metadata=metadata,
    )

    assert consistent["status"] == "consistent"
    assert mismatch["status"] == "potential_mismatch"
    assert mismatch["needs_review"] is True
    assert inconclusive["status"] == "inconclusive"


def test_empty_after_cleaning_is_rejected():
    pipeline, metadata = load_resources()
    try:
        predict_single_review(
            "12345",
            1,
            pipeline=pipeline,
            metadata=metadata,
        )
    except ReviewValidationError as error:
        assert "after preprocessing" in str(error)
    else:
        raise AssertionError("Empty review after preprocessing must be rejected")
