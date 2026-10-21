from datetime import date

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from src import data_provider, market_data
from src.data_provider import MarketDataError, YahooFinanceProvider


def test_bulk_download_retains_valid_symbols_and_reports_missing(monkeypatch, history_frame):
    frame = pd.concat({"AAPL": history_frame, "MSFT": history_frame * 2}, axis=1)
    calls = []

    def download(symbols, **kwargs):
        calls.append((symbols, kwargs))
        return frame

    monkeypatch.setattr(data_provider.yf, "download", download)
    start, end = history_frame.index[0].date(), history_frame.index[-1].date()
    results = YahooFinanceProvider().history_many(("AAPL", "MSFT", "BAD"), start, end)
    assert not results["AAPL"].empty
    assert results["MSFT"]["Close"].iloc[0] == history_frame["Close"].iloc[0] * 2
    assert isinstance(results["BAD"], MarketDataError)
    assert len(calls) == 1
    assert calls[0][1]["threads"] is False
    assert calls[0][1]["auto_adjust"] is False
    assert calls[0][1]["timeout"] == 12


def test_bulk_download_handles_reversed_column_levels(monkeypatch, history_frame):
    frame = pd.concat({"AAPL": history_frame, "MSFT": history_frame}, axis=1).swaplevel(axis=1)
    monkeypatch.setattr(data_provider.yf, "download", lambda *args, **kwargs: frame)
    results = YahooFinanceProvider().history_many(("AAPL", "MSFT"), history_frame.index[0].date(), history_frame.index[-1].date())
    assert len(results["AAPL"]) == len(history_frame)


def test_bulk_empty_and_rate_limited_results_are_graceful(monkeypatch):
    monkeypatch.setattr(data_provider.yf, "download", lambda *args, **kwargs: pd.DataFrame())
    provider = YahooFinanceProvider()
    results = provider.history_many(("AAPL", "MSFT"), date(2025, 1, 1), date(2025, 2, 1))
    assert all(isinstance(value, MarketDataError) for value in results.values())

    def limited(*args, **kwargs):
        raise YFRateLimitError()

    monkeypatch.setattr(data_provider.yf, "download", limited)
    with pytest.raises(MarketDataError, match="rate limiting"):
        provider.history_many(("AAPL", "MSFT"), date(2025, 1, 1), date(2025, 2, 1))


def test_cached_batches_are_order_independent_and_cache_partial_failures(fake_provider, monkeypatch, history_frame):
    calls = []

    def batch(symbols, start, end):
        calls.append(symbols)
        return {symbol: MarketDataError("Unavailable") if symbol == "BAD" else history_frame for symbol in symbols}

    monkeypatch.setattr(fake_provider, "history_many", batch, raising=False)
    first = market_data.get_histories(("AAPL", "BAD"), date(2025, 1, 1), date(2025, 2, 1))
    second = market_data.get_histories(("BAD", "AAPL"), date(2025, 1, 1), date(2025, 2, 1))
    assert first["BAD"].error == second["BAD"].error
    assert len(calls) == 1
    assert first["AAPL"].error is None


def test_batch_limits_are_checked_before_network():
    for symbols in [(), tuple(f"STK{i}" for i in range(11))]:
        with pytest.raises(ValueError):
            market_data.get_histories(symbols, date(2025, 1, 1), date(2025, 2, 1))


def test_malformed_batch_response_is_a_friendly_error(fake_provider, monkeypatch):
    monkeypatch.setattr(fake_provider, "history_many", lambda *args: None, raising=False)
    result = market_data.get_histories(("AAPL", "MSFT"), date(2025, 1, 1), date(2025, 2, 1))
    assert all(value.error and value.data is None for value in result.values())
