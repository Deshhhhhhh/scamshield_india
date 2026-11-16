"""ScamShield India — analytics dashboard (Streamlit).
Reads the same SQLite DB the API writes. Run: streamlit run dashboard/app.py"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scamshield.config import settings  # noqa: E402
from scamshield.redflags import RED_FLAGS  # noqa: E402

st.set_page_config(page_title="ScamShield India", page_icon="🛡️", layout="wide")

FLAG_LABELS = {f.id: f.label for f in RED_FLAGS}


@st.cache_data(ttl=30)
def load_df() -> pd.DataFrame:
    try:
        with sqlite3.connect(settings.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM analyses", conn)
    except Exception:
        return pd.DataFrame()
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    return df


@st.cache_data(ttl=30)
def load_advisories() -> pd.DataFrame:
    try:
        with sqlite3.connect(settings.db_path) as conn:
            return pd.read_sql_query(
                "SELECT title, source, url, published FROM advisories ORDER BY published DESC LIMIT 50", conn
            )
    except Exception:
        return pd.DataFrame()


st.title("🛡️ ScamShield India")
st.caption(
    "AI-powered scam detection trends — no personal data stored, ever. Demo data is synthetic unless fed by real usage."
)

df = load_df()

if df.empty:
    st.warning("No analyses yet.")
    st.code(
        "python scripts/seed_demo_data.py   # load demo history\n"
        "uvicorn scamshield.main:app --reload  # then forward messages to the API"
    )
    st.stop()

days = st.sidebar.slider("Window (days)", 7, 180, 90)
cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
d = df[df["created_at"] >= cutoff]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Analysed", f"{len(d):,}")
scam = (d["label"] == "scam").sum()
col2.metric("Scams caught", f"{scam:,}", f"{scam / max(len(d), 1) * 100:.0f}% of total")
col3.metric("Avg risk score", f"{d['risk_score'].mean():.0f}/100")
col4.metric("Critical alerts", int((d["band"] == "Critical").sum()))

st.sidebar.header("Filters")
band_filter = st.sidebar.multiselect(
    "Band", ["Safe", "Medium", "High", "Critical"], default=["Medium", "High", "Critical"]
)
d = d[d["band"].isin(band_filter)] if band_filter else d

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Trends", "🎯 Scam types", "🚩 Red flags", "📰 Advisories", "🔒 Privacy"])

with tab1:
    st.subheader("Analyses per day")
    daily = d.set_index("created_at").resample("D").size().rename("analyses")
    st.line_chart(daily)
    st.subheader("Average risk score per day")
    st.line_chart(d.set_index("created_at").resample("D")["risk_score"].mean().rename("avg_risk"))

with tab2:
    st.subheader("Scam type distribution")
    vc = d["scam_type"].value_counts()
    st.bar_chart(vc)
    st.dataframe(vc.rename_axis("scam_type").reset_index(name="count"), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Most common red-flag patterns")
    counts: dict[str, int] = {}
    for raw in d["red_flag_ids"].dropna():
        for fid in str(raw).split(","):
            if fid:
                counts[fid] = counts.get(fid, 0) + 1
    if counts:
        flag_df = pd.Series(counts).sort_values(ascending=True).rename_axis("flag").reset_index(name="count")
        flag_df["label"] = flag_df["flag"].map(FLAG_LABELS).fillna(flag_df["flag"])
        st.bar_chart(flag_df.set_index("label")["count"])
        st.dataframe(
            flag_df[["label", "count"]].sort_values("count", ascending=False), hide_index=True, use_container_width=True
        )
    else:
        st.info("No red flags recorded yet.")

with tab4:
    st.subheader("Collected public advisories (scheduled automation)")
    adv = load_advisories()
    if adv.empty:
        st.info("No advisories yet. Run: python automation/fetch_advisories.py --seed-if-empty")
    else:
        for _, row in adv.iterrows():
            st.markdown(f"- [{row['title']}]({row['url']}) — *{row['source']}* ({row['published'] or 'n/d'})")

with tab5:
    st.subheader("What we store — and what we never store")
    st.markdown(
        "**Stored:** SHA-256 hash of the raw message (dedup only), the *scrubbed* text, "
        "classification, risk score, red-flag ids, model/prompt versions, latency.\n\n"
        "**Never stored:** phone numbers, OTPs, Aadhaar/PAN, emails, card numbers, names — "
        "all masked by the pre-storage scrubber (`scamshield/privacy.py`).\n\n"
        "**Why:** even a database leak would expose no PII and no OTPs. See `docs/threat-model.md`."
    )
