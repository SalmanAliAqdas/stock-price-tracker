import pandas as pd
import pytest

from src.indicators import align_prices, historical_extremes, normalize_returns, percentage_return, price_change, rsi, sma, volume_summary


@pytest.mark.parametrize("current,previous,expected", [(110, 100, 10), (90, 100, -10), (0, 100, -100), (None, 1, None), (1, float('nan'), None), (float('inf'), 1, None)])
def test_price_change(current, previous, expected):
    assert price_change(current, previous) == expected


@pytest.mark.parametrize("start,end,expected", [(100, 120, 20), (100, 75, -25), (50, 0, -100), (0, 20, None), (-1, 20, None), (None, 5, None), (float('nan'), 5, None)])
def test_percentage_return(start, end, expected):
    result = percentage_return(start, end)
    assert result is None if expected is None else result == pytest.approx(expected)


def test_sma_requires_full_valid_window():
    values = pd.Series([1, 2, 3, float('nan'), 5, 6, 7])
    result = sma(values, 3)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2] == 2
    assert result.iloc[3:6].isna().all()
    assert result.iloc[6] == 6
    assert sma(pd.Series(dtype=float), 20).empty


@pytest.mark.parametrize("window", [0, -1, 2.5, True])
def test_invalid_indicator_windows(window):
    with pytest.raises(ValueError):
        sma(pd.Series([1, 2]), window)
    with pytest.raises(ValueError):
        rsi(pd.Series([1, 2]), window)


def test_rsi_wilder_reference_values():
    # Classic hand-checkable Wilder example; the second result tests recursion.
    prices = pd.Series([44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])
    result = rsi(prices)
    assert result.iloc[:14].isna().all()
    assert result.iloc[14] == pytest.approx(70.464135, abs=1e-5)
    assert result.iloc[15] == pytest.approx(66.249619, abs=1e-5)


@pytest.mark.parametrize("values,expected", [(range(1, 18), 100), (range(18, 1, -1), 0), ([5] * 17, 50)])
def test_rsi_boundary_cases(values, expected):
    assert rsi(pd.Series(values)).dropna().eq(expected).all()
    assert len(rsi(pd.Series(values)).dropna()) == 3


def test_rsi_missing_values_restart_warmup():
    assert rsi(pd.Series([1, 2, 3])).isna().all()
    assert rsi(pd.Series(dtype=float)).empty
    values = pd.Series([1, 2, 3, None, 4, 5, 6, 7])
    result = rsi(values, 2)
    assert result.iloc[2] == 100
    assert result.iloc[3:6].isna().all()
    assert result.iloc[6] == 100


def test_comparison_uses_common_dates_and_independent_bases():
    first = pd.Series([90, 100, 120], index=pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]))
    second = pd.Series([50, 45, 40], index=pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-04"]))
    normalized = normalize_returns({"A": first, "B": second})
    assert len(normalized) == 2
    assert normalized.iloc[0].tolist() == [0, 0]
    assert normalized.iloc[-1].tolist() == pytest.approx([20, -10])


def test_alignment_does_not_fill_missing_or_use_zero_bases():
    index = pd.date_range("2025-01-01", periods=4, tz="America/New_York")
    a = pd.Series([0, 10, None, 12], index=index)
    b = pd.Series([5, 10, 11, 15], index=index.tz_localize(None))
    aligned = align_prices({"A": a, "B": b})
    assert list(aligned.index.day) == [2, 4]
    assert normalize_returns({"A": a, "B": b}).iloc[-1].tolist() == pytest.approx([20, 50])
    assert normalize_returns({}).empty
    assert normalize_returns({"A": pd.Series(dtype=float), "B": b}).empty


def test_extremes_and_volume_handle_missing_data():
    assert historical_extremes(pd.DataFrame()) == (None, None)
    assert historical_extremes(pd.DataFrame({"High": [10, 12, None], "Low": [8, 7, 9]})) == (12, 7)
    assert volume_summary(pd.Series([10, None, -3, 30])) == {"total": 40, "average": 20, "latest": 30}
    assert volume_summary(pd.Series(dtype=float)) == {"total": None, "average": None, "latest": None}
