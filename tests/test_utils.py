from datetime import date

import pandas as pd
import pytest

from src.utils import compact_number, csv_bytes, finite_number, format_price, format_quote_timestamp, parse_tickers, validate_dates, validate_ticker


@pytest.mark.parametrize("value,expected", [(" aapl ", "AAPL"), ("brk-b", "BRK-B"), ("VOD.L", "VOD.L"), ("GOOGL", "GOOGL"), ("0700.HK", "0700.HK"), ("7203.T", "7203.T")])
def test_valid_tickers(value, expected):
    assert validate_ticker(value) == expected


@pytest.mark.parametrize("value", ["", "  ", "../secret", "AAPL;dir", "<script>", "AAPL MSFT", "^GSPC", "A" * 30, None, 123])
def test_invalid_tickers(value):
    with pytest.raises(ValueError):
        validate_ticker(value)


def test_parse_symbols_deduplicates_and_bounds_count():
    assert parse_tickers("aapl, MSFT aapl") == ["AAPL", "MSFT"]
    assert len(parse_tickers("A,B,C,D,E,F,G,H,I,J")) == 10
    for value in ["AAPL", "", "A,B,C,D,E,F,G,H,I,J,K"]:
        with pytest.raises(ValueError):
            parse_tickers(value)


def test_date_validation():
    validate_dates(date(2025, 1, 1), date(2025, 2, 1), today=date(2025, 3, 1))
    for start, end in [(date(2025, 1, 2), date(2025, 1, 1)), (date(2025, 1, 1), date(2025, 1, 1)), (date(2025, 1, 1), date(2026, 1, 1)), (date(2000, 1, 1), date(2025, 1, 1))]:
        with pytest.raises(ValueError):
            validate_dates(start, end, today=date(2025, 3, 1))


def test_display_helpers_never_assume_usd():
    assert format_price(12.5, "GBP") == "12.50 GBP"
    assert format_price(None, None) == "— currency unavailable"
    assert compact_number(2_500_000_000) == "2.50B"
    assert compact_number(None) == "—"
    assert finite_number(float("inf")) is None
    assert finite_number(True) is None


def test_csv_contains_real_date_index_and_blank_missing_fields():
    frame = pd.DataFrame({"Close": [10.5, None]}, index=pd.date_range("2025-01-01", periods=2))
    payload = csv_bytes(frame).decode()
    assert "Date,Close" in payload
    assert "2025-01-01,10.5" in payload
    assert "2025-01-02," in payload


def test_quote_timezones_are_converted_before_labeling_as_utc():
    value = pd.Timestamp("2025-01-02 16:00", tz="Asia/Karachi")
    assert format_quote_timestamp(value, True) == "02 Jan 2025, 11:00:00 UTC"
    assert "UTC" not in format_quote_timestamp(pd.Timestamp("2025-01-02 16:00"), True)
    daily = format_quote_timestamp(pd.Timestamp("2025-01-02"), False)
    assert "Session date" in daily
    assert "00:00" not in daily
    assert format_quote_timestamp(pd.NaT, True) == "Quote timestamp unavailable"
