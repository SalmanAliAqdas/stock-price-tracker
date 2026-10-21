from datetime import date

import pytest

from src import market_data
from src.data_provider import MarketDataError
from src.psx_provider import get_psx_provider


def test_unconfigured_provider_never_returns_prices():
    provider = get_psx_provider()
    assert not provider.status().available
    for method, args in [("quote", ("OGDC",)), ("history", ("OGDC", date(2025, 1, 1), date(2025, 2, 1))),
                         ("profile", ("OGDC",)), ("search", ("bank",)), ("index_overview", ())]:
        with pytest.raises(MarketDataError, match="licensed"):
            getattr(provider, method)(*args)


def test_psx_cache_boundary_does_not_call_yahoo(fake_provider):
    assert market_data.get_quote("OGDC", "psx").error
    assert market_data.get_history("OGDC", date(2025, 1, 1), date(2025, 2, 1), "psx").error
    assert market_data.search_psx("bank").error
    assert market_data.get_psx_index().error
    assert fake_provider.quote_calls == 0
    assert fake_provider.history_calls == 0


def test_unknown_market_and_empty_psx_search_are_rejected():
    with pytest.raises(ValueError):
        market_data.provider_for("unknown")
    assert market_data.search_psx("").error
