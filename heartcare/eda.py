"""Run after preparing data. Plots describe the development subset only."""

import json

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split

from heartcare.data import FEATURES, NUMERIC, ROOT
from heartcare.model import SEED

plt.switch_backend("Agg")


def main():
    frame = pd.read_csv(ROOT / "data/clean/heart.csv")
    train, _ = train_test_split(frame, test_size=0.2, stratify=frame.target, random_state=SEED)
    out = ROOT / "reports/figures"
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "figure.dpi": 160})
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.5))
    for name, ax in zip(NUMERIC, axes.flat):
        ax.hist(train[name].dropna(), bins=15, color="#267b91", edgecolor="white")
        ax.set_title(name)
        ax.set_ylabel("Patients")
    axes.flat[-1].axis("off")
    fig.suptitle("Development data distributions   n = " + str(len(train)))
    fig.tight_layout()
    fig.savefig(out / "histograms.png")
    plt.close(fig)
    corr = train[FEATURES + ["target"]].corr()
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=65, ha="right")
    ax.set_yticks(range(len(corr)), corr.columns)
    fig.colorbar(im, ax=ax, label="Pearson correlation")
    ax.set_title("Development data correlation   categorical codes are descriptive only")
    fig.tight_layout()
    fig.savefig(out / "correlation.png")
    plt.close(fig)
    counts = train.target.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(5.5, 3))
    ax.bar(["Absent 0", "Present 1"], counts, color=["#267b91", "#bb6b3c"])
    for i, value in enumerate(counts):
        ax.text(i, value + 1, str(value), ha="center")
    ax.set_ylim(0, max(counts) * 1.18)
    ax.set_ylabel("Patients")
    ax.set_title("Development data class balance")
    fig.tight_layout()
    fig.savefig(out / "class_balance.png")
    plt.close(fig)
    summary = {"development_rows": len(train), "class_counts": counts.to_dict(),
               "missing": train.isna().sum().to_dict(),
               "numeric_summary": train[NUMERIC].describe().round(3).to_dict()}
    (ROOT / "reports/eda.json").write_text(json.dumps(summary, indent=2))
    print("EDA plots saved to reports/figures")


if __name__ == "__main__":
    main()
