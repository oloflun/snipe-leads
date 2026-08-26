"""is_cancellation_risk — uppsägningsavsikten bär beslutet, missnöje kan
bara förstärka den (2026-08-26, S2-felklassningen)."""

from app.agent.retention_classifier import is_cancellation_risk


def test_tydlig_uppsagningsavsikt_ar_risk_oavsett_missnoje():
    assert is_cancellation_risk(0.9, 0.0) is True
    assert is_cancellation_risk(0.6, 0.2) is True


def test_rent_missnoje_utan_uppsagningssignal_ar_inte_retention_risk():
    """S2-fallet: en irriterad leveransfråga. Missnöjet ägs av
    sentiment-eskaleringen — retention-etiketten ska vara sann."""
    assert is_cancellation_risk(0.0, 0.7) is False
    assert is_cancellation_risk(0.1, 0.9) is False
    assert is_cancellation_risk(0.0, 1.0) is False


def test_gransfall_med_bade_signal_och_starkt_missnoje_ar_risk():
    assert is_cancellation_risk(0.4, 0.7) is True
    assert is_cancellation_risk(0.5, 0.8) is True


def test_svag_signal_med_milt_missnoje_ar_inte_risk():
    assert is_cancellation_risk(0.4, 0.6) is False
    assert is_cancellation_risk(0.3, 0.9) is False
