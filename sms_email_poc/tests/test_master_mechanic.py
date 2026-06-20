import re
from sms_email_poc.master_mechanic import generate_report


def test_detects_dtcs_with_punctuation():
    report = generate_report("P0300, P0171")
    assert "P0300" in report
    assert "P0171" in report


def test_generate_includes_issue_summary():
    report = generate_report("check engine light")
    assert "ISSUE SUMMARY" in report


def test_obd_data_appears_in_report():
    report = generate_report("", obd_data={"RPM": 800, "STFT": "+2%"})
    # should include OBD-II Summary header and keys
    assert "OBD-II Summary" in report or "OBD-II" in report
    assert "RPM" in report
