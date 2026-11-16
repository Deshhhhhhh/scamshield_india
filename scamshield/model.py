"""Baseline ML model: TF-IDF (word + char n-grams) + multinomial LogisticRegression.

Multiclass: one class per scam type + 'safe'. Ships with a deterministic trainer so
anyone can rebuild the artifact from data/training/. The LLM layer sits on top (see
llm.py); this model is the cheap, offline, always-available first opinion.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from . import MODEL_VERSION
from .categories import ALL_LABELS


def build_pipeline() -> Pipeline:
    word = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=30000,
        min_df=2,
        sublinear_tf=True,
        strip_accents="unicode",
    )
    char = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        max_features=20000,
        min_df=2,
        sublinear_tf=True,
    )
    features = FeatureUnion([("word", word), ("char", char)])
    clf = LogisticRegression(
        max_iter=2000,
        C=4.0,
        class_weight="balanced",
        solver="lbfgs",
    )
    return Pipeline([("features", features), ("clf", clf)])


def train_from_csv(csv_path: Path, model_out: Path, meta_out: Path, test_size: float = 0.15) -> dict:
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["text", "scam_type"])
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 3]

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"],
        df["scam_type"],
        test_size=test_size,
        random_state=42,
        stratify=df["scam_type"],
    )
    pipe = build_pipeline()
    t0 = time.time()
    pipe.fit(X_train, y_train)
    train_seconds = time.time() - t0

    preds = pipe.predict(X_test)
    acc = accuracy_score(y_test, preds)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_test,
        preds,
        average="macro",
        zero_division=0,
    )
    scam_true = (y_test != "safe").astype(int)
    scam_pred = (preds != "safe").astype(int)
    s_prec, s_rec, s_f1, _ = precision_recall_fscore_support(
        scam_true,
        scam_pred,
        average="binary",
        zero_division=0,
    )
    meta = {
        "model_version": MODEL_VERSION,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "classes": list(pipe.classes_),
        "all_labels_known": list(ALL_LABELS),
        "holdout_accuracy": round(float(acc), 4),
        "holdout_macro_f1": round(float(f1), 4),
        "holdout_macro_precision": round(float(prec), 4),
        "holdout_macro_recall": round(float(rec), 4),
        "holdout_scam_precision": round(float(s_prec), 4),
        "holdout_scam_recall": round(float(s_rec), 4),
        "holdout_scam_f1": round(float(s_f1), 4),
        "train_seconds": round(train_seconds, 2),
        "package": "scikit-learn",
    }
    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, model_out)
    meta_out.write_text(json.dumps(meta, indent=2))
    return meta


def load_model(model_path: Path) -> Pipeline:
    return joblib.load(model_path)


def predict(pipe: Pipeline, text: str) -> tuple[str, float, dict[str, float]]:
    """Returns (predicted_scam_type, confidence, full class→proba map)."""
    proba = pipe.predict_proba([text])[0]
    idx = int(np.argmax(proba))
    classes = list(pipe.classes_)
    return classes[idx], float(proba[idx]), {c: float(p) for c, p in zip(classes, proba, strict=True)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/training/train.csv")
    ap.add_argument("--model-out", default="models/scam_model.joblib")
    ap.add_argument("--meta-out", default="models/model_meta.json")
    args = ap.parse_args()
    result = train_from_csv(Path(args.csv), Path(args.model_out), Path(args.meta_out))
    print(json.dumps(result, indent=2))
