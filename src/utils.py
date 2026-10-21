"""Input validation and display helpers with no network or UI dependencies."""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any

import pandas as pd

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z0-9]{1,4})?$")


def validate_ticker(value: str) -> str:
    """Return a canonical Yahoo symbol; syntax validation does not prove listing."""
    if not isinstance(value, str):
        raise ValueError("Enter a ticker symbol, such as AAPL or BRK-B.")
    symbol = value.strip().upper()
    if not TICKER_PATTERN.fullmatch(symbol):
        raise ValueError("Use a ticker such as AAPL, MSFT, or BRK-B (letters, numbers, a dot or dash).")
    return symbol


def parse_tickers(value: str, minimum: int = 2, maximum: int = 4) -> list[str]:
    symbols = list(dict.fromkeys(validate_ticker(part) for part in re.split(r"[,\s]+", value.strip()) if part))
    if not minimum <= len(symbols) <= maximum:
        raise ValueError(f"Enter {minimum}–{maximum} different tickers, separated by commas.")
    return symbols


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def format_number(value: Any, decimals: int = 2) -> str:
    number = finite_number(value)
    return "—" if number is None else f"{number:,.{decimals}f}"


def compact_number(value: Any) -> str:
    number = finite_number(value)
    if number is None:
        return "—"
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(number) >= threshold:
            return f"{number / threshold:,.2f}{suffix}"
    return f"{number:,.0f}"


def currency_label(currency: str | None) -> str:
    return currency.strip() if isinstance(currency, str) and currency.strip() else "currency unavailable"


def format_price(value: Any, currency: str | None) -> str:
    return f"{format_number(value)} {currency_label(currency)}"


def validate_dates(start: date, end: date, today: date | None = None) -> None:
    if start >= end:
        raise ValueError("Choose an end date after the start date.")
    if end > (today or date.today()):
        raise ValueError("The end date cannot be in the future.")
    if (end - start).days > 3653:
        raise ValueError("Choose a date range of ten years or less.")


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Export numeric market data and a named session-date index."""
    return frame.rename_axis("Date").to_csv().encode("utf-8")
