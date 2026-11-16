"""Golden-set integrity + tiny-model training smoke test."""

import csv
import re
from pathlib import Path

import pandas as pd
import pytest

from scamshield.categories import ALL_LABELS
from scamshield.model import build_pipeline, predict

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden" / "golden_set.csv"


def test_golden_set_is_valid():
    rows = list(csv.DictReader(GOLDEN.open(encoding="utf-8")))
    assert len(rows) >= 60
    for r in rows:
        assert r["label"] in ("scam", "safe")
        assert r["scam_type"] in ALL_LABELS
        if r["label"] == "scam":
            assert r["scam_type"] != "safe"
        else:
            assert r["scam_type"] == "safe"


def test_golden_has_all_scam_types():
    types = {r["scam_type"] for r in csv.DictReader(GOLDEN.open(encoding="utf-8"))}
    assert len(types - {"safe"}) >= 13


def test_golden_no_duplicates():
    texts = [re.sub(r"\s+", " ", r["text"].strip().lower()) for r in csv.DictReader(GOLDEN.open(encoding="utf-8"))]
    assert len(texts) == len(set(texts))


def test_golden_disjoint_from_training():
    train = ROOT / "data" / "training" / "train.csv"
    if not train.exists():
        pytest.skip("train.csv not built yet")
    train_texts = {re.sub(r"\s+", " ", r["text"].strip().lower()) for r in csv.DictReader(train.open(encoding="utf-8"))}
    golden_texts = {
        re.sub(r"\s+", " ", r["text"].strip().lower()) for r in csv.DictReader(GOLDEN.open(encoding="utf-8"))
    }
    assert train_texts.isdisjoint(golden_texts)


def test_pipeline_trains_and_predicts():
    df = pd.DataFrame(
        {
            "text": [
                "share your OTP now",
                "kyc update required click link",
                "you won lottery prize",
                "digital arrest CBI call now",
                "double your money guaranteed returns",
                "parcel customs fee pay now",
                "work from home earn daily fee",
                "aaj gym chalein",
                "your appointment is tomorrow",
                "salary credited to account",
                "order delivered thank you",
                "team meeting at 3pm",
                "kal subah milte hain",
                "bill pay ho gaya",
                "party kab de rahe ho",
                "phone pe kal lunch",
            ],
            "scam_type": [
                "kyc_update",
                "kyc_update",
                "lottery_prize",
                "digital_arrest",
                "investment_scam",
                "fake_delivery",
                "fake_job_offer",
                "safe",
                "safe",
                "safe",
                "safe",
                "safe",
                "safe",
                "safe",
                "safe",
                "safe",
            ],
        }
    )
    pipe = build_pipeline()
    pipe.fit(df["text"], df["scam_type"])
    label, conf, proba = predict(pipe, "kyc expired click link share otp")
    assert label in set(df["scam_type"])
    assert 0.0 <= conf <= 1.0
    assert abs(sum(proba.values()) - 1.0) < 1e-5
