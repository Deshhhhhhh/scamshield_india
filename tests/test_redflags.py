from scamshield.redflags import find_red_flags, has_critical_flag, red_flag_score


def ids(text: str) -> list[str]:
    return [f.id for f in find_red_flags(text)]


def test_otp_request_detected():
    assert "otp_request" in ids("Please share your OTP to verify the refund")


def test_negated_otp_not_flagged():
    assert "otp_request" not in ids("Your OTP is 392811. Never share OTP with anyone.")


def test_digital_arrest_detected():
    got = ids("This is CBI. You are under digital arrest. Stay on the line.")
    assert "digital_arrest" in got
    assert has_critical_flag(got)


def test_collect_request_detected():
    assert "collect_request" in ids("Open PhonePe and approve the collect request to receive refund")


def test_urgency_detected():
    assert "urgency" in ids("Your account will be blocked immediately, respond within 24 hours")


def test_hinglish_lure_detected():
    assert "hinglish_scam_pattern" in ids("aapka account band ho jayega, turant batao")


def test_clean_message_few_or_no_flags():
    assert red_flag_score(ids("Aaj gym chalein?")) == 0


def test_score_scales_with_flags():
    low = red_flag_score(ids("your parcel is on the way"))
    high = red_flag_score(ids("CBI digital arrest, share OTP now, stay on the line, do not tell anyone"))
    assert high > low
