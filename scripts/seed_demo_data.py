"""Seed the local DB with realistic-looking HISTORICAL analyses so the dashboard
and /v1/stats have something to show in a demo. Clearly synthetic; timestamps spread
over --days. Never presented as real user data."""

from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scamshield import MODEL_VERSION, PROMPT_VERSION, storage  # noqa: E402
from scamshield.config import settings  # noqa: E402

TYPE_WEIGHTS = {
    "kyc_update": 22,
    "upi_refund": 16,
    "fake_job_offer": 14,
    "digital_arrest": 5,
    "voice_clone": 4,
    "lottery_prize": 8,
    "investment_scam": 7,
    "fake_delivery": 7,
    "electricity_bill": 6,
    "bank_account_block": 6,
    "government_impersonation": 2,
    "loan_app": 2,
    "generic_spam": 1,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--n", type=int, default=420)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    types = list(TYPE_WEIGHTS)
    weights = list(TYPE_WEIGHTS.values())
    now = time.time()

    for i in range(args.n):
        # slight upward trend: weight recent days more heavily
        age_days = rng.triangular(0, args.days, args.days * 0.25)
        ts = now - age_days * 86400
        if rng.random() < 0.22:
            scam_type, label, risk = "safe", "safe", rng.randint(0, 22)
            band = "Safe"
        else:
            scam_type = rng.choices(types, weights=weights, k=1)[0]
            label = "scam"
            risk = rng.randint(55, 98) if scam_type != "generic_spam" else rng.randint(30, 70)
            band = "Critical" if risk >= 75 else "High" if risk >= 50 else "Medium"
        storage.save_analysis(
            settings.db_path,
            {
                "id": "demo-" + uuid.uuid4().hex[:16],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S+0000", time.localtime(ts)),
                "text_sha256": uuid.uuid4().hex + uuid.uuid4().hex,
                "scrubbed_text": f"[demo] simulated {scam_type} message #{i}",
                "label": label,
                "scam_type": scam_type,
                "risk_score": risk,
                "band": band,
                "ml_type": scam_type,
                "ml_proba": round(rng.uniform(0.6, 0.99), 3),
                "llm_used": False,
                "llm_path": "seed-demo",
                "red_flag_ids": rng.choice(
                    [
                        ["kyc_bait", "url_present"],
                        ["collect_request", "refund_bait"],
                        ["payment_upfront", "job_bait"],
                        ["digital_arrest", "secrecy", "urgency"],
                        ["lottery_prize", "payment_upfront"],
                        ["otp_request"],
                        ["short_url", "urgency"],
                    ]
                ),
                "model_version": MODEL_VERSION,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": round(rng.uniform(20, 250), 1),
            },
        )
    print(f"seeded {args.n} demo analyses into {settings.db_path}")


if __name__ == "__main__":
    main()
