from scamshield.redflags import find_red_flags
from scamshield.risk import band_for, combine


def flags(text):
    return find_red_flags(text)


def test_clean_safe_scores_low():
    r = combine("safe", 0.05, False, "safe", 0.7, [])
    assert r.label == "safe" and r.risk_score < 25 and r.band == "Safe"


def test_critical_flag_forces_scam():
    f = flags("share your OTP immediately")
    r = combine("safe", 0.4, False, "safe", 0.6, f)
    assert r.label == "scam" and r.risk_score >= 68


def test_both_models_agree_scam():
    f = flags("CBI digital arrest, stay on the line, pay now")
    r = combine("digital_arrest", 0.92, True, "digital_arrest", 0.9, f)
    assert r.band in ("High", "Critical") and r.risk_score >= 60


def test_band_boundaries():
    assert band_for(0) == "Safe" and band_for(24) == "Safe"
    assert band_for(25) == "Medium" and band_for(49) == "Medium"
    assert band_for(50) == "High" and band_for(74) == "High"
    assert band_for(75) == "Critical" and band_for(100) == "Critical"


def test_score_capped():
    f = flags("CBI digital arrest! share OTP, stay on the line, pay fee now, do not tell anyone, urgent!!!")
    r = combine("digital_arrest", 0.99, True, "digital_arrest", 0.99, f)
    assert r.risk_score <= 97
