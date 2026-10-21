"""Cache only public market data, including short-lived failure results."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
from typing import Any

import streamlit as st

from src.data_provider import MarketDataError, YahooFinanceProvider
from src.psx_provider import get_psx_provider
from src.utils import validate_ticker
from src.watchlist import validate_market

logger = logging.getLogger(__name__)


@dataclass
class DataResult:
    data: Any = None
    error: str | None = None
    fetched_at: datetime | None = None


def provider_for(market: str = "yahoo"):
    validate_market(market)
    return YahooFinanceProvider() if market == "yahoo" else get_psx_provider()


def _fetch(method: str, *args: Any, market: str = "yahoo") -> DataResult:
    try:
        data = getattr(provider_for(market), method)(*args)
        return DataResult(data=data, fetched_at=datetime.now(timezone.utc))
    except (MarketDataError, ValueError) as exc:
        return DataResult(error=str(exc), fetched_at=datetime.now(timezone.utc))
    except Exception as exc:
        logger.warning("Unexpected provider response (%s)", type(exc).__name__)
        return DataResult(error="The market data provider returned an unreadable response. Please try again later.", fetched_at=datetime.now(timezone.utc))


@st.cache_data(ttl=900, max_entries=512, show_spinner=False)
def get_history(symbol: str, start: date, end: date, market: str = "yahoo") -> DataResult:
    return _fetch("history", symbol, start, end, market=market)


@st.cache_data(ttl=120, max_entries=512, show_spinner=False)
def get_quote(symbol: str, market: str = "yahoo") -> DataResult:
    return _fetch("quote", symbol, market=market)


@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def get_profile(symbol: str, market: str = "yahoo") -> DataResult:
    return _fetch("profile", symbol, market=market)


@st.cache_data(ttl=900, max_entries=64, show_spinner=False)
def _get_histories(symbols: tuple[str, ...], start: date, end: date, market: str) -> dict[str, DataResult]:
    provider = provider_for(market)
    if hasattr(provider, "history_many"):
        result = _fetch("history_many", symbols, start, end, market=market)
        if result.error:
            return {symbol: DataResult(error=result.error) for symbol in symbols}
        if not isinstance(result.data, dict):
            return {symbol: DataResult(error="The provider returned an unreadable comparison response. Please try again later.") for symbol in symbols}
        results = {}
        for symbol in symbols:
            value = result.data.get(symbol)
            if isinstance(value, MarketDataError):
                results[symbol] = DataResult(error=str(value))
            elif value is None:
                results[symbol] = DataResult(error=f"No history was returned for {symbol}.")
            else:
                results[symbol] = DataResult(data=value)
        return results
    return {symbol: get_history(symbol, start, end, market) for symbol in symbols}


def get_histories(symbols: tuple[str, ...], start: date, end: date, market: str = "yahoo") -> dict[str, DataResult]:
    canonical = tuple(sorted(set(validate_ticker(symbol) for symbol in symbols)))
    if not 1 <= len(canonical) <= 10:
        raise ValueError("Request between one and ten symbols at a time.")
    validate_market(market)
    return _get_histories(canonical, start, end, market)


@st.cache_data(ttl=3600, max_entries=64, show_spinner=False)
def search_psx(query: str) -> DataResult:
    if not query.strip() or len(query) > 100:
        return DataResult(error="Enter a company name or PSX symbol (up to 100 characters).")
    return _fetch("search", query.strip(), market="psx")


@st.cache_data(ttl=120, max_entries=1, show_spinner=False)
def get_psx_index() -> DataResult:
    return _fetch("index_overview", market="psx")
