"""All learned preprocessing stays inside the fitted model pipeline."""

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from heartcare.data import CATEGORICAL, NUMERIC

SEED = 42


def build_pipeline(kind, **params):
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler())])
    categorical = Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    transform = ColumnTransformer([("numeric", numeric, NUMERIC),
                                   ("categorical", categorical, CATEGORICAL)])
    if kind == "logistic":
        classifier = LogisticRegression(max_iter=2000, random_state=SEED, **params)
    elif kind == "forest":
        classifier = RandomForestClassifier(n_estimators=200, random_state=SEED,
                                            n_jobs=1, **params)
    else:
        raise ValueError(f"Unknown model kind: {kind}")
    return Pipeline([("preprocess", transform), ("classifier", classifier)])
