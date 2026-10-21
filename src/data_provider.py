"""Provider boundary and daily-data conventions. No Streamlit or session state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import logging
from typing import Any, Protocol

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from src.indicators import percentage_return, price_change
from src.utils import finite_number, validate_dates, validate_ticker

logger = logging.getLogger(__name__)
HISTORY_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


class MarketDataError(Exception):
    """A public-safe explanation, rather than a provider stack trace."""


@dataclass(frozen=True)
class Quote:
    symbol: str
    company_name: str
    currency: str | None
    price: float
    previous_close: float | None
    change: float | None
    change_percent: float | None
    volume: float | None
    timestamp: pd.Timestamp
    timestamp_is_exact: bool
    source_label: str
    exchange: str | None = None
    data_source: str = "Yahoo Finance via yfinance"


class MarketDataProvider(Protocol):
    def history(self, symbol: str, start: date, end: date) -> pd.DataFrame: ...
    def quote(self, symbol: str) -> Quote: ...
    def profile(self, symbol: str) -> dict[str, Any]: ...


def clean_history(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=HISTORY_COLUMNS, index=pd.DatetimeIndex([], name="Date"))
    if isinstance(frame.columns, pd.MultiIndex) or "Close" not in frame:
        raise MarketDataError("The provider returned an unsupported price format. Please try again later.")
    data = frame.reindex(columns=HISTORY_COLUMNS).copy()
    for column in HISTORY_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.replace([float("inf"), -float("inf")], float("nan"))
    index = pd.DatetimeIndex(pd.to_datetime(data.index))
    if index.tz is not None:
        index = index.tz_localize(None)
    data.index = index.normalize()
    data = data.loc[~data.index.isna()]
    data = data.loc[~data.index.duplicated(keep="last")].sort_index()
    for column in HISTORY_COLUMNS[:-1]:
        data[column] = data[column].where(data[column] > 0)
    data["Volume"] = data["Volume"].where(data["Volume"] >= 0)
    return data.dropna(subset=["Close"]).rename_axis("Date")


def quote_timestamp(value: Any) -> pd.Timestamp | None:
    """yfinance may return epoch seconds or an already localized Timestamp."""
    epoch = finite_number(value)
    try:
        if epoch is not None:
            timestamp = pd.Timestamp(epoch, unit="s", tz="UTC")
        elif isinstance(value, (pd.Timestamp, str)):
            timestamp = pd.Timestamp(value)
            if timestamp.tzinfo is None:
                return None  # A timezone cannot be safely inferred.
            timestamp = timestamp.tz_convert("UTC")
        else:
            return None
        return None if pd.isna(timestamp) else timestamp
    except (ValueError, TypeError, OverflowError):
        return None


class YahooFinanceProvider:
    """Unadjusted daily OHLC + explicit Adj Close for return calculations."""

    def _history(self, ticker: Any, **kwargs: Any) -> pd.DataFrame:
        try:
            return ticker.history(interval="1d", auto_adjust=False, actions=False, timeout=12, **kwargs)
        except YFRateLimitError as exc:
            raise MarketDataError("Yahoo Finance is rate limiting requests. Wait a few minutes before trying again.") from exc
        except Exception as exc:
            logger.warning("History request failed (%s)", type(exc).__name__)
            raise MarketDataError("Market data is temporarily unavailable. Check your connection and try again later.") from exc

    def history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        symbol = validate_ticker(symbol)
        validate_dates(start, end)
        frame = self._history(yf.Ticker(symbol), start=start.isoformat(), end=(end + timedelta(days=1)).isoformat())
        data = clean_history(frame)
        # Defensive filtering also makes the inclusive end-date contract explicit.
        data = data.loc[(data.index.date >= start) & (data.index.date <= end)]
        if data.empty:
            raise MarketDataError(f"No price history was returned for {symbol} in this range. Check the Yahoo ticker or try a wider range; the provider may also be unavailable.")
        return data

    def history_many(self, symbols: tuple[str, ...], start: date, end: date) -> dict[str, pd.DataFrame | MarketDataError]:
        """Multi-symbol library download; upstream requests remain per-symbol.

        Worker threads are disabled to avoid a concurrent burst on cloud IPs.
        """
        symbols = tuple(dict.fromkeys(validate_ticker(symbol) for symbol in symbols))
        if not 1 <= len(symbols) <= 10:
            raise ValueError("Request between one and ten symbols at a time.")
        validate_dates(start, end)
        try:
            frame = yf.download(list(symbols), start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                                interval="1d", auto_adjust=False, actions=False, group_by="ticker",
                                threads=False, progress=False, timeout=12)
        except YFRateLimitError as exc:
            raise MarketDataError("Yahoo Finance is rate limiting requests. Wait a few minutes before trying again.") from exc
        except Exception as exc:
            raise MarketDataError("Comparison history is temporarily unavailable. Please try again later.") from exc
        results = {}
        for symbol in symbols:
            try:
                if isinstance(frame.columns, pd.MultiIndex):
                    levels = [level for level in range(frame.columns.nlevels) if symbol in frame.columns.get_level_values(level)]
                    raw = frame.xs(symbol, level=levels[0], axis=1) if levels else pd.DataFrame()
                else:
                    raw = frame if len(symbols) == 1 else pd.DataFrame()
                data = clean_history(raw)
                data = data.loc[(data.index.date >= start) & (data.index.date <= end)]
                if data.empty:
                    raise MarketDataError("Empty history")
                results[symbol] = data
            except (MarketDataError, ValueError, TypeError):
                results[symbol] = MarketDataError(f"History is unavailable for {symbol}. Check the symbol or range; the provider may also be rate limited.")
        return results

    def quote(self, symbol: str) -> Quote:
        symbol = validate_ticker(symbol)
        ticker = yf.Ticker(symbol)
        data = clean_history(self._history(ticker, period="1mo"))
        if data.empty:
            raise MarketDataError(f"No quote was returned for {symbol}. Check the symbol (for example, AAPL or BRK-B), or try again later.")
        try:
            metadata = ticker.get_history_metadata() or {}
        except Exception:
            metadata = {}
        currency = metadata.get("currency")
        name = metadata.get("longName") or metadata.get("shortName") or symbol
        last = data.iloc[-1]
        price = float(last["Close"])
        previous = finite_number(data["Close"].iloc[-2]) if len(data) > 1 else None
        volume = finite_number(last["Volume"])
        timestamp = pd.Timestamp(data.index[-1])
        exact = False
        label = "Latest available daily bar"
        quote_price = finite_number(metadata.get("regularMarketPrice"))
        quote_time = quote_timestamp(metadata.get("regularMarketTime"))
        if quote_time is not None and quote_price is not None and quote_price > 0:
            try:
                local_time = quote_time.tz_convert(metadata.get("exchangeTimezoneName") or "UTC")
                if local_time.date() >= timestamp.date():
                    price, timestamp, exact = quote_price, quote_time, True
                    label = "Latest available quote · may be delayed"
                    # A quote from a later session needs the last bar as its baseline.
                    if local_time.date() > data.index[-1].date():
                        previous = float(last["Close"])
            except (ValueError, TypeError, OverflowError, KeyError):
                pass
        return Quote(
            symbol=symbol, company_name=str(name), currency=currency,
            price=price, previous_close=previous, change=price_change(price, previous),
            change_percent=percentage_return(previous, price), volume=volume,
            timestamp=timestamp, timestamp_is_exact=exact, source_label=label,
            exchange=metadata.get("exchangeName"),
        )

    def profile(self, symbol: str) -> dict[str, Any]:
        symbol = validate_ticker(symbol)
        try:
            info = yf.Ticker(symbol).get_info() or {}
        except YFRateLimitError as exc:
            raise MarketDataError("Company information is rate limited. Price history may still be available.") from exc
        except Exception as exc:
            logger.warning("Profile request failed (%s)", type(exc).__name__)
            raise MarketDataError("Company details are temporarily unavailable.") from exc
        fields = ["longName", "shortName", "currency", "marketCap", "sector", "industry", "country", "longBusinessSummary", "website", "trailingPE", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fullExchangeName"]
        return {field: info.get(field) for field in fields}
