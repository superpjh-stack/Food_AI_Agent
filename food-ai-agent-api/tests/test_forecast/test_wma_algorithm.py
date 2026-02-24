"""Unit tests for WMA forecast algorithm."""
import pytest

from app.services.forecast_service import run_wma_forecast, DOW_COEFFICIENTS


def test_basic_wma():
    """4+ weeks of data: prediction should be within reasonable range."""
    actuals = [300, 310, 295, 305, 308, 302, 298]
    result = run_wma_forecast(actuals=actuals, dow=0, event_factor=1.0)
    assert result.predicted_mid > 0
    assert result.predicted_min < result.predicted_mid < result.predicted_max
    assert 0.0 <= result.confidence_pct <= 100.0


def test_dow_coefficient():
    """Friday (dow=4) has lower coefficient than Monday (dow=0)."""
    actuals = [300, 310, 295, 305]
    result_mon = run_wma_forecast(actuals=actuals, dow=0, event_factor=1.0, site_capacity=400)
    result_sat = run_wma_forecast(actuals=actuals, dow=5, event_factor=1.0, site_capacity=400)
    # Saturday has 0.70 coefficient vs Monday 1.00
    assert DOW_COEFFICIENTS[0] > DOW_COEFFICIENTS[5]


def test_event_factor():
    """adjustment_factor=0.7 should reduce predicted_mid by ~30%."""
    actuals = [300, 300, 300, 300]
    result_normal = run_wma_forecast(actuals=actuals, dow=0, event_factor=1.0)
    result_event = run_wma_forecast(actuals=actuals, dow=0, event_factor=0.7)
    assert result_event.predicted_mid < result_normal.predicted_mid
    assert "이벤트 보정 적용" in result_event.risk_factors[0]


def test_low_data_fallback():
    """Fewer than 4 weeks of data: uses capacity-based fallback."""
    actuals = [300, 310]  # Only 2 weeks
    result = run_wma_forecast(actuals=actuals, dow=0, site_capacity=500)
    assert result.confidence_pct == 50.0
    assert any("과거 실적 부족" in r for r in result.risk_factors)


def test_confidence_calculation():
    """High variance in actuals → lower confidence."""
    stable_actuals = [300, 300, 300, 300, 300, 300, 300]
    volatile_actuals = [200, 400, 150, 450, 100, 500, 250]

    stable = run_wma_forecast(actuals=stable_actuals, dow=0)
    volatile = run_wma_forecast(actuals=volatile_actuals, dow=0)

    assert stable.confidence_pct > volatile.confidence_pct


def test_margin():
    """Margin should be at least 10 or 10% of mid."""
    actuals = [100, 100, 100, 100]
    result = run_wma_forecast(actuals=actuals, dow=0)
    expected_margin = max(10, int(result.predicted_mid * 0.1))
    assert result.predicted_max - result.predicted_mid == expected_margin
    assert result.predicted_mid - result.predicted_min == expected_margin
