import pandas as pd

from src.config import DEFAULT_DATA_PATH
from src.modeling import build_feature_extractor, get_stop_words
from src.preprocessing import prepare_dataset
from src.train import make_holdout_split


def test_negation_is_not_a_stop_word_and_changes_vector():
    assert "not" not in get_stop_words()
    assert "never" not in get_stop_words()

    texts = [
        "good food",
        "not good food",
        "not good service",
        "bad service",
    ]
    extractor = build_feature_extractor()
    matrix = extractor.fit_transform(texts)

    difference = matrix[0] - matrix[1]
    assert difference.nnz > 0


def test_group_holdout_has_no_text_overlap_and_is_reproducible():
    raw = pd.read_csv(DEFAULT_DATA_PATH)
    cleaned, _ = prepare_dataset(raw)

    first_train, first_test = make_holdout_split(cleaned)
    second_train, second_test = make_holdout_split(cleaned)

    assert first_train.tolist() == second_train.tolist()
    assert first_test.tolist() == second_test.tolist()

    train_groups = set(cleaned.iloc[first_train]["text_clean"])
    test_groups = set(cleaned.iloc[first_test]["text_clean"])
    assert train_groups.isdisjoint(test_groups)
