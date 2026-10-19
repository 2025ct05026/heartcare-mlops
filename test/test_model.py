import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from heartcare.data import FEATURES, NUMERIC, ROOT
from heartcare.model import SEED, build_pipeline


@pytest.mark.parametrize("kind", ["logistic", "forest"])
def test_roundtrip_and_null_prediction(kind, tmp_path):
    data = pd.read_csv(ROOT / "data/clean/heart.csv")
    pipe = build_pipeline(kind).fit(data[FEATURES], data.target)
    example = data[FEATURES].iloc[:3].copy()
    example.loc[:, "ca"] = np.nan
    before = pipe.predict_proba(example)
    path = tmp_path / "pipeline.joblib"
    joblib.dump(pipe, path)
    np.testing.assert_allclose(before, joblib.load(path).predict_proba(example))
    assert np.isfinite(before).all()
    assert ((before >= 0) & (before <= 1)).all()
    np.testing.assert_allclose(before.sum(axis=1), 1)


def test_imputer_uses_only_training_partition():
    data = pd.read_csv(ROOT / "data/clean/heart.csv")
    train, holdout = train_test_split(data, test_size=0.2, stratify=data.target, random_state=SEED)
    assert set(train.index).isdisjoint(holdout.index)
    pipe = build_pipeline("logistic").fit(train[FEATURES], train.target)
    imputer = pipe.named_steps["preprocess"].named_transformers_["numeric"].named_steps["impute"]
    np.testing.assert_allclose(imputer.statistics_, train[NUMERIC].median().to_numpy())


def test_unknown_model_fails():
    with pytest.raises(ValueError):
        build_pipeline("unknown")
