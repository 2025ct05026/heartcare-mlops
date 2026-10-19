import pandas as pd
import pytest

from heartcare.data import FEATURES, ROOT, clean_frame


def test_target_mapping_and_null_preservation():
    raw = pd.DataFrame([[55 + n] + [55] * 12 + [n] for n in range(5)], columns=FEATURES + ["num"])
    raw.loc[0, "ca"] = float("nan")
    cleaned = clean_frame(raw)
    assert cleaned.target.tolist() == [0, 1, 1, 1, 1]
    assert pd.isna(cleaned.loc[0, "ca"])


@pytest.mark.parametrize("invalid", [None, -1, 5])
def test_bad_target_fails(invalid):
    raw = pd.DataFrame([[55] * 13 + [invalid]], columns=FEATURES + ["num"])
    with pytest.raises(ValueError):
        clean_frame(raw)


def test_duplicates_removed():
    raw = pd.DataFrame([[55] * 13 + [0]] * 2, columns=FEATURES + ["num"])
    assert len(clean_frame(raw)) == 1


def test_cleaned_dataset_contract():
    data = pd.read_csv(ROOT / "data/clean/heart.csv")
    assert len(data) == 303
    assert list(data.columns) == FEATURES + ["target"]
    assert set(data.target) == {0, 1}
    assert data.target.notna().all()
