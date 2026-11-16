"""Golden-set evaluation: baseline ML vs LLM(fallback) vs combined fusion.

The golden set (data/golden/golden_set.csv) is hand-written, disjoint from training,
and never seen by the model during fitting. Numbers here are the honest estimate —
the holdout split numbers in model_meta.json are inflated by synthetic templates.
"""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from scamshield import MODEL_VERSION, PROMPT_VERSION
from scamshield.categories import type_labels
from scamshield.llm import FallbackExplainer
from scamshield.model import predict
from scamshield.privacy import scrub_text
from scamshield.redflags import find_red_flags
from scamshield.risk import combine

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "golden_set.csv"
TRAIN = ROOT / "data" / "training" / "train.csv"
MODEL = ROOT / "models" / "scam_model.joblib"
RESULTS_JSON = ROOT / "models" / "eval_results.json"
RESULTS_MD = ROOT / "docs" / "results.md"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def load_golden() -> list[dict]:
    with GOLDEN.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def metrics_for(true_labels: list[str], pred_labels: list[str]) -> dict:
    scam_true = [1 if t == "scam" else 0 for t in true_labels]
    scam_pred = [1 if p == "scam" else 0 for p in pred_labels]
    prec, rec, f1, _ = precision_recall_fscore_support(scam_true, scam_pred, average="binary", zero_division=0)
    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        true_labels, pred_labels, average="macro", zero_division=0, labels=["safe", "scam"]
    )
    tn, fp, fn, tp = confusion_matrix(scam_true, scam_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": round(accuracy_score(true_labels, pred_labels), 4),
        "scam_precision": round(prec, 4),
        "scam_recall": round(rec, 4),
        "scam_f1": round(f1, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
    }


def main() -> None:
    golden = load_golden()
    train_texts = {norm(r["text"]) for r in csv.DictReader(TRAIN.open())} if TRAIN.exists() else set()
    overlap = [r["text"] for r in golden if norm(r["text"]) in train_texts]
    if overlap:
        raise SystemExit(f"GOLDEN/TRAIN OVERLAP: {overlap}")

    pipe = joblib.load(MODEL)
    llm = FallbackExplainer()

    rows = []
    for item in golden:
        text = item["text"]
        scrubbed = scrub_text(text).text

        ml_type, _conf, proba = predict(pipe, scrubbed)
        ml_scam_proba = 1.0 - proba.get("safe", 0.0)
        ml_label = "safe" if ml_type == "safe" else "scam"

        verdict = llm.analyze(scrubbed)
        llm_label = "scam" if verdict.scam else "safe"

        flags = find_red_flags(scrubbed)
        fused = combine(ml_type, ml_scam_proba, verdict.scam, verdict.scam_type, verdict.confidence, flags)

        rows.append(
            {
                "text": text[:120],
                "true_label": item["label"],
                "true_scam_type": item["scam_type"],
                "ml_pred": ml_label,
                "ml_type": ml_type,
                "llm_pred": llm_label,
                "llm_type": verdict.scam_type,
                "combined_pred": fused.label,
                "combined_type": fused.scam_type,
                "risk": fused.risk_score,
                "band": fused.band,
            }
        )

    y_true = [r["true_label"] for r in rows]
    results = {
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "golden_set_size": len(rows),
        "model_version": MODEL_VERSION,
        "prompt_version": PROMPT_VERSION,
        "baseline_ml": metrics_for(y_true, [r["ml_pred"] for r in rows]),
        "llm_fallback": metrics_for(y_true, [r["llm_pred"] for r in rows]),
        "combined": metrics_for(y_true, [r["combined_pred"] for r in rows]),
    }

    # per-type accuracy for combined (scam types only)
    per_type: dict[str, dict[str, int]] = {}
    for r in rows:
        if r["true_scam_type"] == "safe":
            continue
        d = per_type.setdefault(r["true_scam_type"], {"n": 0, "correct": 0})
        d["n"] += 1
        d["correct"] += int(r["combined_type"] == r["true_scam_type"])
    results["per_type_accuracy_combined"] = {
        k: {"n": v["n"], "accuracy": round(v["correct"] / v["n"], 3)} for k, v in sorted(per_type.items())
    }
    results["errors"] = [
        {"text": r["text"], "true": r["true_label"], "pred": r["combined_pred"], "risk": r["risk"]}
        for r in rows
        if r["true_label"] != r["combined_pred"]
    ]

    RESULTS_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    md = [
        "# Evaluation results — golden set",
        "",
        f"Evaluated: {results['evaluated_at']}  |  golden: {results['golden_set_size']} messages"
        " (65 scam / 15 safe, hand-written, disjoint from training)",
        f"Model: `{MODEL_VERSION}`  Prompt: `{PROMPT_VERSION}`  LLM: offline FallbackExplainer (no paid API)",
        "",
        "| System | Accuracy | Precision (scam) | Recall (scam) | F1 (scam) | Macro F1 |",
        "|---|---|---|---|---|---|",
    ]
    for key, name in (
        ("baseline_ml", "Baseline ML (TF-IDF+LogReg)"),
        ("llm_fallback", "LLM fallback (offline explainer)"),
        ("combined", "Combined (ML + LLM + red flags)"),
    ):
        m = results[key]
        md.append(
            f"| {name} | {m['accuracy']:.2%} | {m['scam_precision']:.2%} | {m['scam_recall']:.2%} "
            f"| {m['scam_f1']:.2%} | {m['macro_f1']:.2%} |"
        )
    md += [
        "",
        "## Confusion (combined)",
        f"- TP={results['combined']['true_positives']} FP={results['combined']['false_positives']} "
        f"FN={results['combined']['false_negatives']} TN={results['combined']['true_negatives']}",
        "",
        "## Combined: per-scam-type accuracy (top-1 scam_type correct)",
        "",
        "| Scam type | n | Accuracy |",
        "|---|---|---|",
    ]
    for k, v in results["per_type_accuracy_combined"].items():
        md.append(f"| {type_labels(k)} | {v['n']} | {v['accuracy']:.0%} |")
    md += [
        "",
        "## Errors (combined)",
        "",
    ]
    if results["errors"]:
        for e in results["errors"]:
            md.append(f"- true={e['true']} pred={e['pred']} risk={e['risk']}: “{e['text']}…”")
    else:
        md.append("None on this golden set.")
    md += [
        "",
        "**Read this table honestly:** the golden set is small and templated-adjacent. Treat these as",
        "engineering regression targets, not real-world guarantees. See `docs/model-card.md`.",
        "",
    ]
    RESULTS_MD.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({k: results[k] for k in ["baseline_ml", "llm_fallback", "combined"]}, indent=2))
    print(f"\nPer-type (combined): {results['per_type_accuracy_combined']}")
    print(f"Wrote {RESULTS_JSON} and {RESULTS_MD}")


if __name__ == "__main__":
    main()
