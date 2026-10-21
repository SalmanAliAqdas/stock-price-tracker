import json

import pytest

from src.watchlist import MAX_SYMBOLS, add_symbol, export_watchlist, filter_symbols, import_watchlist


@pytest.mark.parametrize("market", ["yahoo", "psx"])
@pytest.mark.parametrize("file_format", ["json", "csv"])
def test_one_hundred_symbols_round_trip(market, file_format):
    symbols = [f"STK{i}" for i in range(100)]
    assert MAX_SYMBOLS >= 50
    assert import_watchlist(export_watchlist(symbols, market, file_format).encode(), market, file_format) == symbols


def test_legacy_backups_are_preserved_for_international_watchlists():
    legacy = json.dumps({"version": 1, "symbols": ["AAPL", "MSFT"]})
    assert import_watchlist(legacy) == ["AAPL", "MSFT"]
    with pytest.raises(ValueError, match="Legacy"):
        import_watchlist(legacy, "psx")


@pytest.mark.parametrize("file_format", ["json", "csv"])
def test_market_backups_cannot_cross_lists(file_format):
    backup = export_watchlist(["OGDC"], "psx", file_format)
    with pytest.raises(ValueError):
        import_watchlist(backup, "yahoo", file_format)


@pytest.mark.parametrize("payload", ["symbol\nAAPL", "market,symbol\nyahoo,../../secret", "market,symbol\nyahoo,AAPL,extra", "market,symbol\nyahoo,=cmd"])
def test_bad_csv_is_rejected(payload):
    with pytest.raises(ValueError):
        import_watchlist(payload, file_format="csv")


def test_search_and_sort_do_not_mutate_list():
    original = ["NVDA", "AAPL", "AMZN", "MSFT"]
    assert filter_symbols(original, "a") == ["AAPL", "AMZN", "NVDA"]
    assert filter_symbols(original, descending=True) == ["NVDA", "MSFT", "AMZN", "AAPL"]
    assert original == ["NVDA", "AAPL", "AMZN", "MSFT"]
    assert filter_symbols(original, "missing") == []


def test_large_list_duplicate_is_allowed_but_new_symbol_is_rejected():
    symbols = [f"STK{i}" for i in range(MAX_SYMBOLS)]
    assert add_symbol(symbols, "STK0") == symbols
    with pytest.raises(ValueError):
        add_symbol(symbols, "EXTRA")
