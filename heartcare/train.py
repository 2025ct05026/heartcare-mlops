"""Six CV experiments, deterministic selection, then one holdout evaluation."""

import hashlib
import json
import platform
from time import perf_counter

import joblib
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (ConfusionMatrixDisplay, RocCurveDisplay, accuracy_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from heartcare.data import FEATURES, ROOT
from heartcare.model import SEED, build_pipeline

plt.switch_backend("Agg")


def main():
    started = perf_counter()
    frame = pd.read_csv(ROOT / "data/clean/heart.csv")
    train, test = train_test_split(frame, test_size=0.2, stratify=frame.target, random_state=SEED)
    x, y = train[FEATURES], train.target
    figures = ROOT / "reports/figures"
    figures.mkdir(parents=True, exist_ok=True)
    (ROOT / "models").mkdir(exist_ok=True)
    mlflow.set_tracking_uri("sqlite:///" + (ROOT / "mlflow.db").as_posix())
    experiment = mlflow.get_experiment_by_name("heartcare-cleveland")
    if experiment is None:
        mlflow.create_experiment("heartcare-cleveland", artifact_location=(ROOT / "mlartifacts").as_uri())
    mlflow.set_experiment("heartcare-cleveland")
    candidates = [("logistic", {"C": c}) for c in [0.1, 1.0, 10.0]]
    candidates += [("forest", {"max_depth": d, "min_samples_leaf": 2}) for d in [3, 5, None]]
    scoring = {"accuracy": "accuracy", "precision": "precision", "recall": "recall", "roc_auc": "roc_auc"}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    dataset_hash = hashlib.sha256((ROOT / "data/clean/heart.csv").read_bytes()).hexdigest()
    rows = []
    for number, (kind, params) in enumerate(candidates, 1):
        label = f"{kind}_{number}"
        pipe = build_pipeline(kind, **params)
        with mlflow.start_run(run_name=label) as run:
            mlflow.log_params({"model_kind": kind, "seed": SEED, "cv_folds": 5,
                               "train_rows": len(train), "test_rows": len(test), **params})
            mlflow.set_tags({"dataset_sha256": dataset_hash, "selection_metric": "cv_roc_auc",
                             "python": platform.python_version(), "sklearn": sklearn.__version__})
            scores = cross_validate(pipe, x, y, cv=cv, scoring=scoring, error_score="raise")
            metrics = {}
            for metric in scoring:
                values = scores["test_" + metric]
                metrics["cv_" + metric] = float(values.mean())
                metrics["cv_" + metric + "_std"] = float(values.std())
            mlflow.log_metrics(metrics)
            pipe.fit(x, y)
            model_path = ROOT / "models" / f"{label}.joblib"
            joblib.dump(pipe, model_path)
            mlflow.log_artifact(str(model_path), "pipeline")
            for plot in figures.glob("*.png"):
                if plot.stem in ["histograms", "correlation", "class_balance"]:
                    mlflow.log_artifact(str(plot), "eda")
            pd.DataFrame({k: v for k, v in scores.items()}).to_csv(ROOT / "reports/fold_scores.csv", index=False)
            mlflow.log_artifact(str(ROOT / "reports/fold_scores.csv"))
            rows.append({"candidate": label, "kind": kind, "params": params,
                         "run_id": run.info.run_id, **metrics})
    # Stable tie break: earlier candidate wins. The holdout cannot affect this choice.
    winner = max(rows, key=lambda row: row["cv_roc_auc"])
    selected = joblib.load(ROOT / "models" / f"{winner['candidate']}.joblib")
    probability = selected.predict_proba(test[FEATURES])[:, 1]
    prediction = (probability >= 0.5).astype(int)
    holdout = {"accuracy": accuracy_score(test.target, prediction),
               "precision": precision_score(test.target, prediction, zero_division=0),
               "recall": recall_score(test.target, prediction, zero_division=0),
               "roc_auc": roc_auc_score(test.target, probability)}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    ConfusionMatrixDisplay.from_predictions(test.target, prediction, ax=axes[0], colorbar=False)
    RocCurveDisplay.from_predictions(test.target, probability, ax=axes[1], name=winner["candidate"])
    axes[0].set_title("Holdout confusion matrix   threshold 0.50")
    axes[1].set_title("Holdout ROC curve")
    fig.tight_layout()
    fig.savefig(figures / "evaluation.png", dpi=170)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar([r["candidate"] for r in rows], [r["cv_roc_auc"] for r in rows],
           yerr=[r["cv_roc_auc_std"] for r in rows], color="#267b91", capsize=4)
    ax.set_ylim(0.5, 1)
    ax.set_ylabel("Mean validation ROC AUC")
    ax.set_title("Five fold comparison   error bars show fold standard deviation")
    fig.tight_layout()
    fig.savefig(figures / "comparison.png", dpi=170)
    plt.close(fig)
    model_path = ROOT / "models/model.joblib"
    joblib.dump(selected, model_path)
    metadata = {"model_name": winner["candidate"], "run_id": winner["run_id"],
                "threshold": 0.5, "features": FEATURES, "dataset_sha256": dataset_hash,
                "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                "python": platform.python_version(), "sklearn": sklearn.__version__,
                "train_rows": len(train), "test_rows": len(test), "seed": SEED,
                "holdout_metrics": holdout}
    (ROOT / "models/metadata.json").write_text(json.dumps(metadata, indent=2))
    results = {"candidates": rows, "selected": winner["candidate"], "holdout": holdout,
               "seconds": perf_counter() - started}
    (ROOT / "reports/results.json").write_text(json.dumps(results, indent=2))
    pd.DataFrame([{k: v for k, v in r.items() if k != "params"} for r in rows]).to_csv(
        ROOT / "reports/experiments.csv", index=False)
    pd.DataFrame({"row_index": test.index, "target": test.target,
                  "probability": probability, "prediction": prediction}).to_csv(
        ROOT / "reports/holdout_predictions.csv", index=False)
    with mlflow.start_run(run_id=winner["run_id"]):
        mlflow.log_metrics({"holdout_" + k: v for k, v in holdout.items()})
        mlflow.set_tag("selected", "true")
        for artifact in [ROOT / "reports/results.json", ROOT / "models/metadata.json",
                         figures / "evaluation.png", figures / "comparison.png"]:
            mlflow.log_artifact(str(artifact), "selection")
    # Keep one serving artifact; candidates remain stored in MLflow.
    for candidate_file in (ROOT / "models").glob("*_*.joblib"):
        candidate_file.unlink()
    print(json.dumps(results, indent=2))
    assert np.isfinite(probability).all()


if __name__ == "__main__":
    main()
