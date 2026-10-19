"""Download the original Cleveland data and preserve missing values for pipelines."""

import hashlib
import io
import json
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/45/heart+disease.zip"
NUMERIC = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]
FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach",
            "exang", "oldpeak", "slope", "ca", "thal"]


def clean_frame(raw):
    """Validate source labels, convert num 1..4 to 1, retain null predictors."""
    if list(raw.columns) != FEATURES + ["num"]:
        raise ValueError("Expected original Cleveland columns in source order")
    frame = raw.apply(pd.to_numeric, errors="raise").copy()
    if frame["num"].isna().any() or not frame["num"].isin([0, 1, 2, 3, 4]).all():
        raise ValueError("Diagnosis must be a nonmissing code from 0 to 4")
    frame["target"] = (frame.pop("num") > 0).astype(int)
    return frame.drop_duplicates().reset_index(drop=True)


def prepare(download=False):
    raw_path = ROOT / "data/raw/processed.cleveland.data"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if download or not raw_path.exists():
        with urlopen(URL, timeout=60) as response:
            archive = ZipFile(io.BytesIO(response.read()))
        member = next(n for n in archive.namelist() if n.endswith("processed.cleveland.data"))
        raw_path.write_bytes(archive.read(member))
    raw = pd.read_csv(raw_path, names=FEATURES + ["num"], na_values="?")
    clean = clean_frame(raw)
    out = ROOT / "data/clean/heart.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out, index=False)
    provenance = {"source": URL, "doi": "10.24432/C52P4X", "license": "CC BY 4.0",
                  "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                  "raw_rows": len(raw), "clean_rows": len(clean),
                  "missing": clean.isna().sum().to_dict(),
                  "class_counts": clean.target.value_counts().sort_index().to_dict()}
    (out.parent / "provenance.json").write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance, indent=2))
    return clean


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Refresh from official UCI archive")
    prepare(parser.parse_args().download)
