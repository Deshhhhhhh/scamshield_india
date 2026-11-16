from scamshield.privacy import hash_text, leak_check, scrub_text


def test_phone_plus91():
    out = scrub_text("Call me +91 98765-43210 after 6pm").text
    assert "98765" not in out and "[PHONE]" in out


def test_phone_bare():
    out = scrub_text("reach me at 9876543210 please").text
    assert "9876543210" not in out


def test_landline():
    out = scrub_text("office 0522-2456789 tomorrow").text
    assert "2456789" not in out


def test_aadhaar_grouped():
    out = scrub_text("meraa aadhaar 4123 9876 1234 hai").text
    assert "4123" not in out and "[AADHAAR]" in out


def test_aadhaar_bare():
    out = scrub_text("aadhar 412398761234 nahi dena").text
    assert "412398761234" not in out


def test_pan():
    out = scrub_text("PAN ABCPK1234F verify karein").text
    assert "ABCPK1234F" not in out and "[PAN]" in out


def test_card():
    out = scrub_text("card 4111 1111 1111 1111 exp 12/29").text
    assert "4111" not in out and "[CARD]" in out


def test_otp_anchored():
    out = scrub_text("Your OTP is 482916, do share it").text
    assert "482916" not in out and "[OTP]" in out


def test_upi_vpa():
    out = scrub_text("send to lucky@ybl or refund@oksbi").text
    assert "lucky@ybl" not in out and "[UPI-ID]" in out


def test_email():
    out = scrub_text("write to scammer@example.com today").text
    assert "scammer@example.com" not in out and "[EMAIL]" in out


def test_url_keeps_domain_only():
    out = scrub_text("click http://sbi-secure.verify.com/login?session=abc123 now").text
    assert "session=abc123" not in out and "sbi-secure.verify.com" in out


def test_name_intro_masked():
    out = scrub_text("Hi, my name is Rohan Verma and I call from bank").text
    assert "Rohan" not in out and "[NAME]" in out


def test_clean_text_untouched():
    result = scrub_text("Kal subah 7 baje gym milega")
    assert result.total_redactions == 0


def test_hash_stable_and_distinct():
    assert hash_text("Hello World ") == hash_text("  hello world")
    assert hash_text("a") != hash_text("b")


def test_scrub_then_leakcheck_clean():
    raw = "Call +91 9876543210, OTP is 123456, aadhaar 4123 9876 1234, card 4111111111111111"
    scrubbed = scrub_text(raw).text
    assert not leak_check(scrubbed)


def test_untrusted_input_no_crash():
    assert scrub_text("").text == ""
    assert scrub_text("​​​\n\n\t").text == ""
