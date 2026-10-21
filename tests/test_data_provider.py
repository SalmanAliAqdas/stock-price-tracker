from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from src import data_provider, market_data
from src.data_provider import MarketDataError, YahooFinanceProvider, clean_history


def ticker_stub(monkeypatch, frame, metadata=None, info=None):
    calls = []

    def history(**kwargs):
        calls.append(kwargs)
        return frame

    ticker = SimpleNamespace(history=history, get_history_metadata=lambda: metadata or {}, get_info=lambda: info or {})
    monkeypatch.setattr(data_provider.yf, "Ticker", lambda symbol: ticker)
    return calls


def test_history_uses_raw_and_adjusted_data_and_inclusive_end(monkeypatch):
    frame = pd.DataFrame({"Close": [10, 12, 13], "Adj Close": [9, 11, 12]}, index=pd.date_range("2025-01-01", periods=3, tz="America/New_York"))
    calls = ticker_stub(monkeypatch, frame)
    result = YahooFinanceProvider().history("aapl", date(2025, 1, 1), date(2025, 1, 2))
    assert len(result) == 2
    assert result["Close"].tolist() == [10, 12]
    assert result["Adj Close"].tolist() == [9, 11]
    assert result.index.tz is None
    assert calls[0]["end"] == "2025-01-03"
    assert calls[0]["auto_adjust"] is False
    assert calls[0]["interval"] == "1d"


def test_history_cleaner_preserves_missing_adjustment_and_volume():
    frame = pd.DataFrame({"Close": [10, None, 0, 12], "Volume": [None, 10, 20, -1]}, index=pd.date_range("2025-01-01", periods=4))
    result = clean_history(frame)
    assert result["Close"].tolist() == [10, 12]
    assert result["Adj Close"].isna().all()
    assert result["Volume"].isna().all()
    assert clean_history(None).empty
    assert clean_history(pd.DataFrame()).empty


def test_history_cleaner_deduplicates_sorts_and_rejects_bad_schema():
    frame = pd.DataFrame({"Close": [20, 10, 21]}, index=pd.to_datetime(["2025-01-02", "2025-01-01", "2025-01-02"]))
    assert clean_history(frame)["Close"].tolist() == [10, 21]
    with pytest.raises(MarketDataError, match="unsupported price format"):
        clean_history(pd.DataFrame({"unexpected": [1]}))


@pytest.mark.parametrize("timestamp_format", ["epoch", "localized"])
def test_quote_uses_provider_timestamp_not_fetch_time(monkeypatch, timestamp_format):
    frame = pd.DataFrame({"Close": [100, 102], "Volume": [10, 12]}, index=pd.to_datetime(["2025-01-01", "2025-01-02"]))
    timestamp = pd.Timestamp("2025-01-02 20:45:00", tz="UTC")
    supplied = timestamp.timestamp() if timestamp_format == "epoch" else timestamp.tz_convert("America/New_York")
    ticker_stub(monkeypatch, frame, {"regularMarketPrice": 103, "regularMarketTime": supplied, "exchangeTimezoneName": "America/New_York", "currency": "USD", "longName": "Test company"})
    quote = YahooFinanceProvider().quote("aapl")
    assert quote.timestamp == timestamp
    assert quote.timestamp_is_exact
    assert quote.price == 103
    assert quote.previous_close == 100
    assert quote.change == 3
    assert quote.company_name == "Test company"


def test_quote_daily_fallback_does_not_invent_time_or_currency(monkeypatch):
    frame = pd.DataFrame({"Close": [100, 102]}, index=pd.to_datetime(["2025-01-01", "2025-01-02"]))
    ticker_stub(monkeypatch, frame)
    quote = YahooFinanceProvider().quote("AAPL")
    assert quote.price == 102
    assert quote.change == 2
    assert not quote.timestamp_is_exact
    assert quote.timestamp == pd.Timestamp("2025-01-02")
    assert quote.currency is None
    assert quote.volume is None


def test_older_metadata_quote_does_not_replace_newer_daily_bar(monkeypatch):
    frame = pd.DataFrame({"Close": [100, 102]}, index=pd.to_datetime(["2025-01-01", "2025-01-02"]))
    ticker_stub(monkeypatch, frame, {"regularMarketPrice": 90, "regularMarketTime": pd.Timestamp("2025-01-01", tz="UTC").timestamp()})
    assert YahooFinanceProvider().quote("AAPL").price == 102


def test_quote_one_bar_has_no_fabricated_change(monkeypatch):
    ticker_stub(monkeypatch, pd.DataFrame({"Close": [100]}, index=pd.to_datetime(["2025-01-01"])))
    quote = YahooFinanceProvider().quote("AAPL")
    assert quote.change is None
    assert quote.change_percent is None


def test_empty_provider_data_is_friendly(monkeypatch):
    ticker_stub(monkeypatch, pd.DataFrame())
    with pytest.raises(MarketDataError, match="No quote was returned"):
        YahooFinanceProvider().quote("BAD")
    with pytest.raises(MarketDataError, match="No price history was returned"):
        YahooFinanceProvider().history("BAD", date(2025, 1, 1), date(2025, 2, 1))


@pytest.mark.parametrize("error,match", [(YFRateLimitError(), "rate limiting"), (TimeoutError("private details"), "temporarily unavailable")])
def test_provider_outages_have_public_safe_messages(monkeypatch, error, match):
    def fail(**kwargs):
        raise error

    monkeypatch.setattr(data_provider.yf, "Ticker", lambda symbol: SimpleNamespace(history=fail))
    with pytest.raises(MarketDataError, match=match) as exc:
        YahooFinanceProvider().quote("AAPL")
    assert "private details" not in str(exc.value)


def test_cached_success_and_failure_do_not_repeat_requests(fake_provider):
    first = market_data.get_quote("AAPL")
    second = market_data.get_quote("AAPL")
    assert first.data == second.data
    assert fake_provider.quote_calls == 1
    assert market_data.get_quote("BAD").error
    assert market_data.get_quote("BAD").error
    assert fake_provider.quote_calls == 2


def test_unexpected_provider_response_does_not_leak_technical_details(monkeypatch):
    def fail(symbol):
        raise AttributeError("technical details")

    monkeypatch.setattr(market_data, "YahooFinanceProvider", lambda: SimpleNamespace(quote=fail))
    result = market_data.get_quote("AAPL")
    assert result.error
    assert "technical details" not in result.error
