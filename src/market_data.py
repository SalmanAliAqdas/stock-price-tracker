"""Cache only public market data, including short-lived failure results."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
from typing import Any

import streamlit as st

from src.data_provider import MarketDataError, YahooFinanceProvider

logger = logging.getLogger(__name__)


@dataclass
class DataResult:
    data: Any = None
    error: str | None = None
    fetched_at: datetime | None = None


def _fetch(method: str, *args: Any) -> DataResult:
    try:
        data = getattr(YahooFinanceProvider(), method)(*args)
        return DataResult(data=data, fetched_at=datetime.now(timezone.utc))
    except (MarketDataError, ValueError) as exc:
        return DataResult(error=str(exc), fetched_at=datetime.now(timezone.utc))
    except Exception as exc:
        logger.warning("Unexpected provider response (%s)", type(exc).__name__)
        return DataResult(error="The market data provider returned an unreadable response. Please try again later.", fetched_at=datetime.now(timezone.utc))


@st.cache_data(ttl=900, max_entries=128, show_spinner=False)
def get_history(symbol: str, start: date, end: date) -> DataResult:
    return _fetch("history", symbol, start, end)


@st.cache_data(ttl=120, max_entries=128, show_spinner=False)
def get_quote(symbol: str) -> DataResult:
    return _fetch("quote", symbol)


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def get_profile(symbol: str) -> DataResult:
    return _fetch("profile", symbol)
