"""Red-flag pattern library. Deterministic, explainable, bilingual.

Each flag contributes a weight to the risk score. Explanations are written to be
understood by a non-technical reader in English or Hindi.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedFlag:
    id: str
    label: str
    explanation_en: str
    explanation_hi: str
    weight: int
    severity: str  # "low" | "medium" | "high" | "critical"
    patterns: tuple[re.Pattern[str], ...]


def _rx(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


RED_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        "otp_request",
        "Requests OTP / PIN / CVV / password",
        "No genuine bank, wallet or government body ever asks for your OTP, PIN or CVV. Sharing it gives the scammer full access.",
        "कोई भी असली बैंक या सरकारी संस्था आपसे कभी OTP, PIN या CVV नहीं माँगती। इसे साझा करने से धोखेबाज़ को पूरा एक्सेस मिल जाता है।",
        5,
        "critical",
        _rx(
            r"(share|send|tell|bata|batata|provide|enter|dene|dedo).{0,35}(otp|one[- ]?time|pin|cvv|password|m[- ]?pin)",
            r"(otp|one[- ]?time|pin|cvv|password|m[- ]?pin).{0,25}(share|send|bata|tell|de do|dena)",
        ),
    ),
    RedFlag(
        "digital_arrest",
        "Fake police / CBI / digital-arrest call",
        "'Digital arrest' does not exist in Indian law. CBI/police never demand money over a video call to close a 'case'.",
        "भारतीय कानून में 'डिजिटल अरेस्ट' जैसी कोई चीज़ नहीं है। CBI/पुलिस कभी वीडियो कॉल पर पैसे माँगकर मामला बंद नहीं करती।",
        5,
        "critical",
        _rx(
            r"digital arrest",
            r"cbi|cyber cell|ed officer|narcotics|customs officer",
            r"(video|vc) call.{0,40}(arrest|case|warrant|cbi|police)",
            r"arrest warrant",
            r"money laundering.{0,30}(case|case against)",
        ),
    ),
    RedFlag(
        "secrecy",
        "Tells you to keep it secret / stay on the line",
        "Scammers isolate victims — 'don't tell family, stay on the call' — so no one can warn you.",
        "धोखेबाज़ पीड़ित को अलग-थलग करते हैं — 'किसी को मत बताओ, कॉल पर रहो' — ताकि कोई चेतावनी न दे सके।",
        4,
        "high",
        _rx(
            r"do not tell|don't tell|dont tell|kisiko mat|kisi ko mat|keep (this|it|this matter) (secret|confidential)",
            r"stay on (the )?(line|call)|call (mat|na) kaat|do not disconnect",
        ),
    ),
    RedFlag(
        "payment_upfront",
        "Demands payment / fee to get something",
        "Money demanded before delivering a prize, job, refund or loan is always a scam. Real refunds never need an upfront fee.",
        "इनाम, नौकरी, रिफंड या लोन दिलाने से पहले पैसे माँगना हमेशा धोखा है। असली रिफंड के लिए कोई अग्रिम शुल्क नहीं लगता।",
        4,
        "high",
        _rx(
            r"(pay|deposit|transfer|send|jama|जमा).{0,40}(fee|charge|deposit|security|registration|advance|processing|customs|tax)",
            r"(registration|processing|security|advance|verification|disbursal|courier|customs|handling|onboarding|audit) (fee|charge|deposit|charges)",
            r"(fee|charge|deposit).{0,18}(refundable|non-refundable|upi|http|bit\.ly|transfer|now)",
        ),
    ),
    RedFlag(
        "collect_request",
        "UPI collect / approve request disguised as refund",
        "You never need to 'approve' or enter a PIN to RECEIVE money. Any approve request debits your account.",
        "पैसे प्राप्त करने के लिए कभी 'approve' या PIN दर्ज करने की ज़रूरत नहीं होती। कोई भी approve रिक्वेस्ट आपके खाते से पैसे काटती है।",
        4,
        "high",
        _rx(
            r"(accept|approve|authori[sz]e).{0,30}(request|collect)",
            r"collect request",
            r"(refund|cashback).{0,40}(accept|approve|pin|upi)",
            r"enter (your )?(upi )?pin.{0,20}(refund|receive|cashback)",
        ),
    ),
    RedFlag(
        "kyc_bait",
        "KYC expired / update immediately bait",
        "Banks never suspend accounts over an SMS link for KYC. This is the #1 account-takeover lure in India.",
        "बैंक कभी SMS लिंक से KYC अपडेट न कराने पर खाता बंद नहीं करते। यह भारत में खाता हथियाने का सबसे आम झांसा है।",
        3,
        "high",
        _rx(
            r"kyc.{0,35}(update|expire|verify|pending|complete|link|suspend|block)",
            r"update.{0,20}kyc",
            r"kyc (verification|link|mandatory)",
        ),
    ),
    RedFlag(
        "account_threat",
        "Threatens account block / suspension / legal action",
        "Fear is the fuel of scams. Threats of instant blocking/legal action over SMS or call are fake.",
        "डर ही धोखेबाज़ों का ईंधन है। SMS या कॉल पर तुरंत खाता ब्लॉक/कानूनी कार्रवाई की धमकी फर्जी होती है।",
        3,
        "high",
        _rx(
            r"account.{0,30}(block|suspend|deactivat|frozen|close[sd]?)",
            r"legal action",
            r"(rbi|bank|trai).{0,40}(block|suspend|deactivat)",
            r"block ho jayega",
            r"permanently (blocked|deactivated)",
        ),
    ),
    RedFlag(
        "lottery_prize",
        "Prize / lottery / lucky draw reward bait",
        "You cannot win a lottery you never entered. 'Congratulations, you won' messages are lures.",
        "जिस लॉटरी में आपने हिस्सा ही नहीं लिया, वह कभी नहीं जीत सकते। 'बधाई हो, आप जीत गए' संदेश चारा होते हैं।",
        3,
        "medium",
        _rx(
            r"(won|winner|selected|congratulations).{0,45}(prize|lottery|reward|gift|lakh|crore|draw)",
            r"lucky draw",
            r"lottery",
            r"claim.{0,30}(prize|reward|amount|winnings)",
            r"kbc|kaun banega crorepati",
        ),
    ),
    RedFlag(
        "refund_bait",
        "Fake refund / excess payment / cashback",
        "Refunds arrive automatically or after you raise a request in-app — never after sharing a PIN or clicking an unknown link.",
        "रिफंड अपने आप आता है या ऐप में रिक्वेस्ट डालकर — कभी PIN साझा करके या अनजान लिंक से नहीं।",
        3,
        "medium",
        _rx(
            r"refund.{0,30}(rs|inr|₹|amount|process|approve)",
            r"excess (payment|charge|transfer)",
            r"cashback of",
            r"wrong(ly)? (credited|transferred|paid)",
        ),
    ),
    RedFlag(
        "job_bait",
        "Work-from-home / task job too good to be true",
        "Liking videos for ₹5000/day, 'registration fee refunded later', Telegram task groups — classic job scams.",
        "₹5000/दिन वीडियो लाइक करना, 'रजिस्ट्रेशन शुल्क बाद में वापस', टेलीग्राम टास्क ग्रुप — क्लासिक नौकरी फ्रॉड।",
        4,
        "high",
        _rx(
            r"work from home.{0,40}(earn|salary|income|job)",
            r"part[- ]?time.{0,40}(earn|salary|income|work)",
            r"earn.{0,25}(per day|daily|per task|per hour)",
            r"(like|watch|review).{0,25}(videos?|posts?|products?).{0,25}(earn|salary|income|pay)",
            r"telegram.{0,30}(job|task|earn)",
            r"salary.{0,20}(lakh|high|package).{0,20}(no experience|fresher)",
        ),
    ),
    RedFlag(
        "investment_bait",
        "Guaranteed / doubled returns investment pitch",
        "No SEBI-registered advisor promises guaranteed or doubled returns. High daily profit claims = guaranteed loss.",
        "कोई SEBI-पंजीकृत सलाहकार निश्चित या दोगुना रिटर्न का वादा नहीं करता। रोज़ाना भारी मुनाफ़े के दावे = पक्का घाटा।",
        4,
        "high",
        _rx(
            r"guaranteed? (return|profit|income)",
            r"double (your )?(money|investment|capital)",
            r"daily (profit|return|income) of",
            r"\d{2,3}\s?%\s?(return|profit|interest|monthly)",
            r"(trading|investment|stock) (group|signal|tips?).{0,30}(free|telegram|join)",
            r"crypto.{0,30}(double|guaranteed|profit|invest)",
        ),
    ),
    RedFlag(
        "bill_disconnect",
        "Electricity / power disconnection tonight",
        "Power boards never threaten same-night disconnection by SMS with a call-back number. It is a known fraud pattern.",
        "बिजली विभाग कभी SMS और कॉल बैक नंबर से उसी रात कनेक्शन काटने की धमकी नहीं देता। यह जाना-पहचाना फ्रॉड तरीका है।",
        3,
        "medium",
        _rx(
            r"electricity.{0,40}(disconnect|cut|off)",
            r"power.{0,25}(disconnect|cut|off).{0,25}(today|tonight|now)",
            r"bijli.{0,25}(kat|disconnect|band)",
            r"electricity bill.{0,30}(update|kyc|verify)",
        ),
    ),
    RedFlag(
        "family_emergency",
        "Relative in accident / hospital — send money now",
        "Voice can be cloned in seconds today. Verify by calling the relative's own number on another line before sending money.",
        "आज आवाज़ सेकंडों में क्लोन हो सकती है। पैसे भेजने से पहले दूसरे फोन से सगे का अपना नंबर घुमाकर पुष्टि करें।",
        4,
        "high",
        _rx(
            r"(son|daughter|brother|sister|friend|bete|beti|relative).{0,45}(accident|hospital|arrest|police|jail|icu)",
            r"(accident|hospital|icu).{0,35}(money|transfer|urgent|immediately|help)",
            r"(send|transfer).{0,25}(money|amount|rupees?|rs).{0,25}(now|urgent|immediately|turant)",
        ),
    ),
    RedFlag(
        "short_url",
        "Shortened / disguised link",
        "Shorteners hide the real destination — usually a fake bank/KYC page that harvests credentials.",
        "छोटा लिंक असली पते को छिपाता है — आमतौर पर फर्जी बैंक/KYC पेज जो आपके क्रेडेंशियल चुराता है।",
        2,
        "medium",
        _rx(r"bit\.ly|tinyurl|t\.co|goo\.gl|is\.gd|cutt\.ly|rebrand\.ly|rb\.gy|shorturl|s\.id"),
    ),
    RedFlag(
        "url_present",
        "Contains a web link",
        "Links in unsolicited messages are untrusted. Open apps directly instead of clicking SMS links.",
        "अनचाहे संदेशों में लिंक पर भरोसा न करें। लिंक खोलने के बजाय सीधे ऐप खोलें।",
        1,
        "low",
        _rx(r"https?://|www\."),
    ),
    RedFlag(
        "payment_details_request",
        "Asks for card / bank / Aadhaar details",
        "Never share card numbers, expiry, CVV, Aadhaar or account details over SMS/call.",
        "SMS/कॉल पर कार्ड नंबर, expiry, CVV, आधार या खाता विवरण कभी साझा न करें।",
        4,
        "high",
        _rx(
            r"(share|send|provide|bata).{0,35}(card|aadhaar|aadhar|account number|a/c|ifsc|debit|credit)",
            r"(card|aadhaar|aadhar|account).{0,25}(number|details|expiry|cvv)",
        ),
    ),
    RedFlag(
        "urgency",
        "Creates extreme urgency (hours / tonight / now)",
        "Urgency stops you from thinking. Genuine institutions give days, never minutes.",
        "जल्दीबाज़ी आपको सोचने नहीं देती। असली संस्थाएँ दिन देती हैं, मिनट नहीं।",
        2,
        "medium",
        _rx(
            r"within (the )?(next )?\d+\s?(hours?|hrs?|minutes?|min)",
            r"expires? (today|tonight|now|soon)",
            r"immediately|right now|urgently?|turant|jaldi|abhi",
            r"(today|tonight) (only|tak|last)",
        ),
    ),
    RedFlag(
        "hinglish_scam_pattern",
        "Mixed-script / romanized-Hindi scam lure",
        "Romanized-Hindi payment/KYC lures ('aapka account... turant') are a common Indian bulk-scam style.",
        "romanized हिंदी भुगतान/KYC झाँसे ('आपका अकाउंट... तुरंत') भारत में थोक फ्रॉड की आम शैली है।",
        1,
        "low",
        _rx(
            r"aapka|apka|aapk|aapki|turant|jankari|refund mil|paise (bhej|transfer)|rupay",
            r"[ऀ-ॿ].{0,60}(otp|kyc|account|refund|click)",
        ),
    ),
)

_CRITICAL_IDS = {f.id for f in RED_FLAGS if f.severity == "critical"}


@dataclass
class FlagMatch:
    id: str
    label: str
    weight: int
    severity: str
    explanation_en: str
    explanation_hi: str


_NEGATION_RE = re.compile(
    r"(never|do not|don't|dont|not|kabhi|mat\s|kisi\s*ko\s*mat|no\s*one)",
    re.IGNORECASE,
)
# only these flags are suppressed by an immediately preceding negation
_NEGATABLE = {"otp_request"}


def _negated(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 40) : end]
    return bool(_NEGATION_RE.search(window))


def find_red_flags(text: str) -> list[FlagMatch]:
    """Return all red flags whose patterns match `text` (already scrubbed ideally)."""
    matches: list[FlagMatch] = []
    for flag in RED_FLAGS:
        matched = False
        for pattern in flag.patterns:
            for m in pattern.finditer(text):
                if flag.id in _NEGATABLE and _negated(text, m.start(), m.end()):
                    continue
                matched = True
                break
            if matched:
                break
        if matched:
            matches.append(
                FlagMatch(
                    id=flag.id,
                    label=flag.label,
                    weight=flag.weight,
                    severity=flag.severity,
                    explanation_en=flag.explanation_en,
                    explanation_hi=flag.explanation_hi,
                )
            )
    return matches


def has_critical_flag(flag_ids: list[str]) -> bool:
    return any(f in _CRITICAL_IDS for f in flag_ids)


def red_flag_score(flag_ids: list[str]) -> int:
    weights = {f.id: f.weight for f in RED_FLAGS}
    return sum(weights.get(fid, 0) for fid in flag_ids)
