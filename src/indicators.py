"""Pure financial calculations. Returns are percentages, never fractions."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from src.utils import finite_number


def price_change(current: float | None, previous: float | None) -> float | None:
    current, previous = finite_number(current), finite_number(previous)
    return None if current is None or previous is None else current - previous


def percentage_return(start: float | None, end: float | None) -> float | None:
    start, end = finite_number(start), finite_number(end)
    if start is None or end is None or start <= 0:
        return None
    return (end / start - 1) * 100


def numeric_series(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").astype(float).replace([float("inf"), -float("inf")], float("nan"))


def sma(prices: pd.Series, window: int) -> pd.Series:
    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError("Moving average window must be a positive integer.")
    return numeric_series(prices).rolling(window, min_periods=window).mean()


def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI: arithmetic seed, then smoothing with alpha=1/period.

    A missing value resets the warmup. Flat prices have RSI 50; no losses
    gives 100 and no gains gives 0. At least period+1 closes are needed.
    """
    if not isinstance(period, int) or isinstance(period, bool) or period < 1:
        raise ValueError("RSI period must be a positive integer.")
    values = numeric_series(prices)
    result = pd.Series(float("nan"), index=values.index, name=f"RSI {period}")
    gains: list[float] = []
    losses: list[float] = []
    previous = average_gain = average_loss = None
    for position, current in enumerate(values):
        if pd.isna(current):
            previous = average_gain = average_loss = None
            gains, losses = [], []
            continue
        if previous is None:
            previous = current
            continue
        difference = current - previous
        previous = current
        gain, loss = max(difference, 0), max(-difference, 0)
        if average_gain is None:
            gains.append(gain)
            losses.append(loss)
            if len(gains) < period:
                continue
            average_gain = sum(gains) / period
            average_loss = sum(losses) / period
        else:
            average_gain = (average_gain * (period - 1) + gain) / period
            average_loss = (average_loss * (period - 1) + loss) / period
        if average_gain == average_loss == 0:
            value = 50.0
        elif average_loss == 0:
            value = 100.0
        else:
            value = 100 - 100 / (1 + average_gain / average_loss)
        result.iloc[position] = value
    return result


def historical_extremes(frame: pd.DataFrame) -> tuple[float | None, float | None]:
    """Return the period's raw intraday high and low, or None when absent."""
    high = finite_number(numeric_series(frame["High"]).max()) if "High" in frame else None
    low = finite_number(numeric_series(frame["Low"]).min()) if "Low" in frame else None
    return high, low


def volume_summary(volume: pd.Series) -> dict[str, float | None]:
    values = numeric_series(volume)
    values = values[values >= 0].dropna()
    if values.empty:
        return {"total": None, "average": None, "latest": None}
    return {"total": float(values.sum()), "average": float(values.mean()), "latest": float(values.iloc[-1])}


def align_prices(prices: Mapping[str, pd.Series]) -> pd.DataFrame:
    """Inner-join positive prices on exchange-local calendar session dates.

    No forward filling: every plotted point has an observation for each stock.
    Time zones are removed without shifting the local trading date.
    """
    if not prices:
        return pd.DataFrame()
    cleaned = {}
    for symbol, series in prices.items():
        values = numeric_series(series).copy()
        index = pd.DatetimeIndex(pd.to_datetime(values.index))
        if index.tz is not None:
            index = index.tz_localize(None)
        values.index = index.normalize()
        values = values[~values.index.duplicated(keep="last")].sort_index()
        cleaned[symbol] = values.where(values > 0)
    aligned = pd.concat(cleaned, axis=1, join="inner").dropna(how="any")
    return aligned.rename_axis("Date")


def normalize_returns(prices: Mapping[str, pd.Series]) -> pd.DataFrame:
    aligned = align_prices(prices)
    if aligned.empty:
        return aligned
    return (aligned.div(aligned.iloc[0]) - 1) * 100
