"""Scheduled collector for public scam/cyber-fraud advisories (RSS).

Run by GitHub Actions cron (.github/workflows/advisories.yml) or manually:
    python automation/fetch_advisories.py --online           # fetch live RSS
    python automation/fetch_advisories.py --seed-if-empty    # insert curated demo advisories

Design rules:
  * Never crash the scheduler: every source is try/except; failures are logged.
  * Only stores title/source/url/published/category — no full article text.
  * 'seeded' entries are paraphrased summaries of real public advisories (sources: RBI, MHA-I4C,
    DoT Sanchar Saathi, CERT-In) for demo purposes; --online replaces them with live items.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import defusedxml.ElementTree as ET
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scamshield import storage  # noqa: E402
from scamshield.config import settings  # noqa: E402
from scamshield.observability import get_logger  # noqa: E402

log = get_logger("advisory_fetcher")

KEYWORDS = (
    "scam",
    "fraud",
    "cyber",
    "otp",
    "kyc",
    "upi",
    "phish",
    "digital arrest",
    "loan app",
    "impersonat",
    "fake call",
    "sim swap",
)

RSS_SOURCES = [
    {"name": "The Hindu — National", "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
    {"name": "Times of India — India", "url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"},
]

CURATED_SEED = [
    {
        "title": "RBI alerts public against 'digital arrest' fraud calls posing as police/CBI/ED and demanding money",
        "source": "Reserve Bank of India",
        "url": "https://www.rbi.org.in",
        "category": "digital_arrest",
        "published": "2024-10-15",
    },
    {
        "title": "MHA/I4C advisory: cyber criminals impersonate agencies; report fraud at NCRP or call 1930 within 'golden hour'",
        "source": "Ministry of Home Affairs (I4C)",
        "url": "https://www.cybercrime.gov.in",
        "category": "digital_arrest",
        "published": "2024-10-18",
    },
    {
        "title": "DoT's Sanchar Saathi / Chakshu portal lets citizens report suspected fraud calls, SMS and apps",
        "source": "Department of Telecommunications",
        "url": "https://sancharsaathi.gov.in",
        "category": "advisory",
        "published": "2024-03-07",
    },
    {
        "title": "CERT-In advisory on phishing campaigns misusing bank/KYC branding to steal credentials",
        "source": "CERT-In",
        "url": "https://www.cert-in.org.in",
        "category": "kyc_update",
        "published": "2024-07-12",
    },
    {
        "title": "RBI: banks/NBFCs never ask customers to share OTP/PIN or approve 'collect requests' to receive money",
        "source": "Reserve Bank of India",
        "url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "category": "upi_refund",
        "published": "2023-12-04",
    },
    {
        "title": "Fake 'instant loan app' operators harass borrowers; RBI lists legitimate lending apps via Sachet portal",
        "source": "Reserve Bank of India — Sachet",
        "url": "https://sachet.rbi.org.in",
        "category": "loan_app",
        "published": "2024-01-31",
    },
    {
        "title": "TRAI warns against SMS/calls demanding TRAI KYC or threatening number disconnection — banks not involved",
        "source": "Telecom Regulatory Authority of India",
        "url": "https://www.trai.gov.in",
        "category": "government_impersonation",
        "published": "2024-05-20",
    },
    {
        "title": "PIB fact-check: no government scheme distributes prizes via WhatsApp/SMS against 'processing fee'",
        "source": "Press Information Bureau",
        "url": "https://pib.gov.in",
        "category": "lottery_prize",
        "published": "2024-08-09",
    },
    {
        "title": "I4C reports surge in 'task-based job' scams on messaging apps promising daily income for liking videos",
        "source": "Indian Cybercrime Coordination Centre",
        "url": "https://www.cybercrime.gov.in",
        "category": "fake_job_offer",
        "published": "2024-11-05",
    },
    {
        "title": "CERT-In: increase in electricity-bill disconnection scam calls/SMS targeting households",
        "source": "CERT-In",
        "url": "https://www.cert-in.org.in",
        "category": "electricity_bill",
        "published": "2024-09-17",
    },
]


def fetch_rss(source: dict, timeout: float = 10.0) -> list[dict]:
    items: list[dict] = []
    try:
        resp = requests.get(
            source["url"], timeout=timeout, headers={"User-Agent": "ScamShieldBot/1.0 (+public advisories)"}
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            blob = f"{title}".lower()
            if not title or not link:
                continue
            if not any(k in blob for k in KEYWORDS):
                continue
            items.append(
                {"title": title, "source": source["name"], "url": link, "published": pub, "category": "advisory"}
            )
        log.info("rss_fetched", extra={"source": source["name"], "kept": len(items)})
    except Exception as exc:  # noqa: BLE001 — scheduler resilience
        log.warning("rss_failed", extra={"source": source["name"], "reason": type(exc).__name__})
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true", help="Fetch live RSS sources")
    ap.add_argument("--seed-if-empty", action="store_true", help="Insert curated advisories if DB has none")
    ap.add_argument("--out", default=None, help="Also dump stored advisories to this JSON path (for the cron workflow)")
    args = ap.parse_args()

    inserted = 0
    if args.online:
        for src in RSS_SOURCES:
            inserted += storage.upsert_advisories(settings.db_path, fetch_rss(src))
    inserted += (
        storage.upsert_advisories(settings.db_path, CURATED_SEED) if (args.seed_if_empty or not args.online) else 0
    )
    print(f"advisories processed; newly inserted = {inserted}")
    if args.out:
        Path(args.out).write_text(
            json.dumps(storage.recent_advisories(settings.db_path, 200), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
