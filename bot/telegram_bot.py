"""ScamShield Telegram bot — one client of the /v1/analyze API.

Zero frameworks: raw long-polling over the Telegram Bot API with httpx.
Env vars:
  TELEGRAM_BOT_TOKEN   (from @BotFather — never commit this)
  SCAMSHIELD_API_URL   (default http://localhost:8000)

Run: python bot/telegram_bot.py
Commands: /start /help /stats ; any other text message is analyzed.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = os.environ.get("SCAMSHIELD_API_URL", "http://localhost:8000").rstrip("/")
TG = f"https://api.telegram.org/bot{TOKEN}"

HELP = (
    "ScamShield India 🛡️\n"
    "Forward me any suspicious SMS/WhatsApp message and I'll tell you:\n"
    "• scam or safe\n• scam type (KYC, UPI refund, digital arrest, fake job…)\n"
    "• risk score 0-100 and red flags in plain English/Hindi\n\n"
    "Commands:\n/stats – community scam trends (last 90 days)\n/help – this message\n\n"
    "⚠️ Never share OTPs or PINs with ANYONE, including me. "
    "Report cyber fraud: cybercrime.gov.in or call 1930."
)

BAND_ICON = {"Safe": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}


def tg_call(method: str, **kwargs: Any) -> dict:
    with httpx.Client(timeout=30) as client:
        resp = client.post(f"{TG}/{method}", json=kwargs)
        resp.raise_for_status()
        return resp.json()


def send_message(chat_id: int, text: str) -> None:
    try:
        tg_call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as exc:  # noqa: BLE001
        print(f"send failed: {exc}", file=sys.stderr)


def analyze_text(text: str) -> str:
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(f"{API}/v1/analyze", json={"message": text, "language": "auto"})
        if resp.status_code == 429:
            return "⏳ Too many requests — please wait a minute and try again."
        if resp.status_code != 200:
            return f"⚠️ Analysis service returned {resp.status_code}. Try again shortly."
        data = resp.json()
    except httpx.HTTPError:
        return "⚠️ Can't reach ScamShield API. Is it running? (SCAMSHIELD_API_URL)"

    icon = BAND_ICON.get(data["band"], "⚪")
    lines = [
        f"{icon} <b>{data['band']} risk</b> — {data['label'].upper()}",
        f"Type: {data['scam_type_label']}",
        f"Risk score: {data['risk_score']}/100",
        "",
        f"💡 {data['explanation']}",
    ]
    if data["red_flags"]:
        lines.append("")
        lines.append("🚩 <b>Red flags:</b>")
        for flag in data["red_flags"][:4]:
            lines.append(f"• {flag['label']} — {flag['explanation']}")
    lines.append("")
    lines.append(f"<i>id {data['analysis_id'][:8]} · model {data['model_version']}</i>")
    return "\n".join(lines)


def stats_text() -> str:
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{API}/v1/stats", params={"days": 90})
        data = resp.json()
        top = ", ".join(f"{r['scam_type']} ({r['n']})" for r in data["by_type"][:5])
        return (
            f"📊 <b>Scam trends — last 90 days</b>\n"
            f"Analysed: {data['total_analyzed']} | scams: {data['scam_share_pct']}%\n"
            f"Top types: {top or 'n/a'}\n"
            f"Advisories collected: {data['advisories_collected']}"
        )
    except Exception:  # noqa: BLE001
        return "⚠️ Stats unavailable right now."


def run() -> None:
    if not TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN (get one from @BotFather).")
    tg_call("deleteWebhook")
    offset = 0
    print(f"ScamShield bot up. API={API}")
    while True:
        try:
            updates = tg_call("getUpdates", offset=offset, timeout=25, allowed_updates=["message"]).get("result", [])
        except Exception as exc:  # noqa: BLE001
            print(f"polling error: {exc}; retrying in 3s", file=sys.stderr)
            time.sleep(3)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message") or {}
            chat_id = (msg.get("chat") or {}).get("id")
            text = (msg.get("text") or "").strip()
            if not chat_id or not text:
                continue
            if text == "/start" or text == "/help":
                send_message(chat_id, HELP)
            elif text == "/stats":
                send_message(chat_id, stats_text())
            elif text.startswith("/"):
                send_message(chat_id, "Unknown command. Use /help")
            else:
                send_message(chat_id, analyze_text(text))


if __name__ == "__main__":
    run()
