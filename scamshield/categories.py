"""Scam taxonomy used across the model, LLM, storage and dashboard.

Keep this list stable: it is part of the API contract (/v1/analyze responses)
and of the metrics label set. Add new types at the end, never renumber.
"""

SCAM_TYPES: dict[str, dict[str, str]] = {
    "kyc_update": {
        "label_en": "Fake KYC update",
        "label_hi": "फर्जी KYC अपडेट",
        "hint": "Asks you to verify/update KYC via a link or OTP; banks never do this by SMS link.",
    },
    "upi_refund": {
        "label_en": "Fake UPI refund / collect request",
        "label_hi": "फर्जी UPI रिफंड",
        "hint": "Tricks you into approving a collect request or sharing PIN to 'receive' money.",
    },
    "fake_job_offer": {
        "label_en": "Fake job offer / task scam",
        "label_hi": "फर्जी नौकरी ऑफर",
        "hint": "High salary for trivial tasks; asks for a registration/security fee up front.",
    },
    "digital_arrest": {
        "label_en": "Digital arrest / law-enforcement impersonation",
        "label_hi": "डिजिटल अरेस्ट",
        "hint": "Caller poses as police/CBI/ED, claims a case against you, demands money to settle.",
    },
    "voice_clone": {
        "label_en": "Voice-clone / family emergency",
        "label_hi": "वॉइस क्लोन आपातकाल",
        "hint": "A cloned or claimed relative/friend is in trouble and needs money urgently.",
    },
    "lottery_prize": {
        "label_en": "Lottery / prize / reward bait",
        "label_hi": "लॉटरी / इनाम का झांसा",
        "hint": "Claims you won a prize/lottery and asks for fees or details to 'claim' it.",
    },
    "investment_scam": {
        "label_en": "Fake investment / guaranteed returns",
        "label_hi": "फर्जी निवेश",
        "hint": "Promises guaranteed/doubled/daily returns, trading groups, crypto schemes.",
    },
    "fake_delivery": {
        "label_en": "Fake delivery / courier scam",
        "label_hi": "फर्जी डिलीवरी / कूरियर",
        "hint": "Parcel held at customs/depot; pay a fee or click a link to release it.",
    },
    "electricity_bill": {
        "label_en": "Electricity bill disconnection scam",
        "label_hi": "बिजली बिल कनेक्शन कटाव फ्रॉड",
        "hint": "Warns of power cut tonight unless you pay or call a number / update KYC.",
    },
    "bank_account_block": {
        "label_en": "Bank account block / suspension threat",
        "label_hi": "बैंक खाता ब्लॉक की धमकी",
        "hint": "Threatens account suspension unless you verify via link/OTP/call now.",
    },
    "government_impersonation": {
        "label_en": "Government / regulator impersonation",
        "label_hi": "सरकारी विभाग बनकर धोखाधड़ी",
        "hint": "Poses as RBI/TRAI/IT/Customs/Police for 'verification' or 'case clearance'.",
    },
    "loan_app": {
        "label_en": "Instant loan app / extortion",
        "label_hi": "इंस्टेंट लोन ऐप",
        "hint": "Instant loan with no checks; later harassment, blackmail and data misuse.",
    },
    "generic_spam": {
        "label_en": "Generic spam / unsolicited promotion",
        "label_hi": "सामान्य स्पैम",
        "hint": "Unsolicited bulk promotion; not necessarily criminal but not wanted either.",
    },
}

SAFE_TYPE = "safe"
ALL_LABELS = [SAFE_TYPE, *SCAM_TYPES.keys()]


def type_labels(scam_type: str, lang: str = "en") -> str:
    """Human label for a scam type id."""
    if scam_type == SAFE_TYPE:
        return "Safe / not a scam" if lang == "en" else "सुरक्षित / फ्रॉड नहीं"
    entry = SCAM_TYPES.get(scam_type)
    if not entry:
        return scam_type
    return entry["label_hi" if lang == "hi" else "label_en"]
