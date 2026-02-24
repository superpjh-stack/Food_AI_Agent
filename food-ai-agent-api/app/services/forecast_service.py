"""Forecast service — WMA-based headcount prediction algorithm."""
import statistics
from typing import NamedTuple

DOW_COEFFICIENTS = {0: 1.00, 1: 0.98, 2: 0.97, 3: 0.96, 4: 0.95, 5: 0.70, 6: 0.30}
WMA_WEIGHTS = [0.05, 0.05, 0.10, 0.10, 0.15, 0.20, 0.35]  # 최근 7주, 최신에 가중


class ForecastResult(NamedTuple):
    predicted_min: int
    predicted_mid: int
    predicted_max: int
    confidence_pct: float
    risk_factors: list[str]


def run_wma_forecast(
    actuals: list[int],
    dow: int,
    event_factor: float = 1.0,
    site_capacity: int = 500,
) -> ForecastResult:
    """WMA 기반 식수 예측.

    Args:
        actuals: 최근 N주 동일 요일 실적 (오래된 것 → 최신 순서)
        dow: 예측 대상 요일 (0=월요일, 6=일요일)
        event_factor: 이벤트 보정 계수 (0.0~1.0)
        site_capacity: 현장 최대 수용 인원 (데이터 부족 시 기준)

    Returns:
        ForecastResult namedtuple
    """
    risk_factors: list[str] = []

    if len(actuals) < 4:
        # 데이터 부족: 계획 식수 × DOW 계수
        confidence = 50.0
        mid = int(site_capacity * DOW_COEFFICIENTS[dow] * event_factor)
        risk_factors.append("과거 실적 부족 (4주 미만)")
    else:
        weights = WMA_WEIGHTS[-len(actuals):]
        w_sum = sum(weights)
        mid = int(sum(a * w for a, w in zip(actuals, weights)) / w_sum * event_factor)

        # 신뢰도: 표준편차 기반 (최근 4주)
        recent = actuals[-4:] if len(actuals) >= 4 else actuals
        std = statistics.stdev(recent) if len(recent) >= 2 else mid * 0.1
        confidence = max(40.0, min(95.0, 100.0 - (std / mid * 100) if mid > 0 else 50.0))

    margin = max(10, int(mid * 0.1))

    if event_factor < 0.9:
        risk_factors.append(f"이벤트 보정 적용 ({event_factor:.0%})")
    if dow in (5, 6):
        risk_factors.append(f"주말 수요 저하 (DOW={dow})")

    return ForecastResult(
        predicted_min=max(0, mid - margin),
        predicted_mid=mid,
        predicted_max=mid + margin,
        confidence_pct=round(confidence, 1),
        risk_factors=risk_factors,
    )
