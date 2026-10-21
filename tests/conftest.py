"""All fixtures are synthetic and confined to tests; network is disabled."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from src import data_provider, market_data
from src.data_provider import MarketDataError, Quote


@pytest.fixture(autouse=True)
def prevent_network_and_clear_cache(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not contact Yahoo Finance.")

    monkeypatch.setattr(data_provider.yf, "Ticker", blocked)
    monkeypatch.setattr(data_provider.yf, "download", blocked)
    for function in (market_data.get_history, market_data.get_quote, market_data.get_profile, market_data._get_histories, market_data.search_psx, market_data.get_psx_index):
        function.clear()
    yield
    for function in (market_data.get_history, market_data.get_quote, market_data.get_profile, market_data._get_histories, market_data.search_psx, market_data.get_psx_index):
        function.clear()


@pytest.fixture
def history_frame():
    index = pd.bdate_range(end=datetime.now(timezone.utc).date(), periods=550, name="Date")
    closes = pd.Series([100 + i * 0.2 + (i % 9) * 0.1 for i in range(len(index))], index=index)
    return pd.DataFrame({"Open": closes - 0.5, "High": closes + 1, "Low": closes - 1, "Close": closes, "Adj Close": closes * 0.98, "Volume": [1_000_000 + i * 100 for i in range(len(index))]})


@pytest.fixture
def fake_provider(monkeypatch, history_frame):
    class FakeProvider:
        history_calls = 0
        quote_calls = 0

        def history(self, symbol, start, end):
            self.history_calls += 1
            if symbol == "BAD":
                raise MarketDataError("No price history was returned for BAD.")
            frame = history_frame.loc[(history_frame.index.date >= start) & (history_frame.index.date <= end)].copy()
            if frame.empty:
                raise MarketDataError("No prices in this range.")
            return frame

        def quote(self, symbol):
            self.quote_calls += 1
            if symbol == "BAD":
                raise MarketDataError("No quote was returned for BAD.")
            return Quote(symbol, f"{symbol} test company", "GBP" if symbol.endswith(".L") else "USD", 150, 148, 2, 2 / 148 * 100, 1_000_000, pd.Timestamp("2026-10-20 20:00", tz="UTC"), True, "Latest available quote · may be delayed", "NASDAQ")

        def profile(self, symbol):
            return {"longName": f"{symbol} test company", "marketCap": 2_000_000_000, "sector": "Technology", "currency": "USD", "longBusinessSummary": "A fictional company used only in tests."}

    provider = FakeProvider()
    monkeypatch.setattr(market_data, "YahooFinanceProvider", lambda: provider)
    return provider
