import math

from worker.workflows.market_scan import (
    AssetReport,
    build_crypto_report,
    build_email_html,
    build_etf_report,
    build_stock_report,
    compute_drawdown_pct,
    compute_sma,
    evaluate_buffett_stock,
    is_opportunity,
    sma_trend_positive,
)


def test_compute_sma_basic():
    closes = [float(i) for i in range(1, 401)]
    assert math.isclose(compute_sma(closes, 200), sum(closes[200:]) / 200)


def test_compute_sma_insufficient_data():
    assert compute_sma([1.0, 2.0, 3.0], 200) is None


def test_compute_drawdown():
    closes = [100.0, 200.0, 150.0]
    assert math.isclose(compute_drawdown_pct(closes), 25.0)


def test_sma_trend_positive():
    rising = [float(i) for i in range(1, 400)]
    assert sma_trend_positive(rising) is True
    falling = [float(400 - i) for i in range(1, 400)]
    assert sma_trend_positive(falling) is False


def test_evaluate_buffett_stock_strong():
    info = {
        "returnOnEquity": 0.20,
        "profitMargins": 0.25,
        "debtToEquity": 30,
        "revenueGrowth": 0.08,
        "trailingPE": 18,
    }
    score, reasons = evaluate_buffett_stock(info)
    assert score == 5
    assert len(reasons) == 5


def test_evaluate_buffett_stock_weak():
    info = {
        "returnOnEquity": 0.02,
        "profitMargins": 0.03,
        "debtToEquity": 300,
        "revenueGrowth": -0.10,
        "trailingPE": 90,
    }
    score, _ = evaluate_buffett_stock(info)
    assert score == 0


def test_build_stock_report_below_sma():
    closes = [200.0] * 250 + [100.0]
    info = {
        "returnOnEquity": 0.18,
        "profitMargins": 0.20,
        "debtToEquity": 50,
        "revenueGrowth": 0.06,
        "trailingPE": 15,
    }
    report = build_stock_report("TEST", closes, info)
    assert report.below_sma_200w is True
    assert report.buffett_score == 5
    assert is_opportunity(report, 3) is True


def test_build_stock_report_uses_full_name():
    closes = [200.0] * 250 + [100.0]
    info = {"longName": "UnitedHealth Group"}
    report = build_stock_report("UNH", closes, info)
    assert report.name == "UnitedHealth Group"


def test_build_crypto_report_full_name():
    closes = [100.0] * 150 + [50.0] * 120 + [30.0]
    report = build_crypto_report("BTC-USD", closes)
    assert report.name == "Bitcoin"
    html = build_email_html([report])
    assert "Bitcoin (BTC-USD)" in html


def test_build_stock_report_above_sma_not_opportunity():
    closes = [100.0] * 200 + [300.0]
    info = {"returnOnEquity": 0.18}
    report = build_stock_report("TEST", closes, info)
    assert report.below_sma_200w is False
    assert is_opportunity(report, 3) is False


def test_build_crypto_report_criteria():
    closes = [100.0] * 150 + [50.0] * 120 + [30.0]
    report = build_crypto_report("BTC-USD", closes)
    assert report.below_sma_200w is True
    assert report.drawdown_from_ath_pct is not None and report.drawdown_from_ath_pct > 40
    assert report.buffett_score >= 2
    assert is_opportunity(report, 2) is True


def test_build_etf_report_criteria():
    closes = [100.0] * 250 + [70.0]
    report = build_etf_report("DCAM.PA", closes, {"longName": "Amundi PEA Monde (MSCI World)"})
    assert report.asset_type == "etf"
    assert report.name == "Amundi PEA Monde (MSCI World)"
    assert report.below_sma_200w is True
    assert report.drawdown_from_ath_pct is not None and report.drawdown_from_ath_pct >= 20
    assert report.buffett_score >= 2


def test_is_opportunity_error_report():
    report = AssetReport(symbol="X", asset_type="stock", error="no data")
    assert is_opportunity(report, 3) is False


def test_build_email_html_contains_alerts():
    closes = [200.0] * 250 + [100.0]
    info = {"returnOnEquity": 0.18, "profitMargins": 0.20, "debtToEquity": 50}
    report = build_stock_report("TEST", closes, info)
    html = build_email_html([report])
    assert "TEST" in html
    assert "MM200" in html
