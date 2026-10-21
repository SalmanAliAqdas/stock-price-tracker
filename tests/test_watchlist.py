import json

import pytest

from src.watchlist import MAX_IMPORT_BYTES, MAX_SYMBOLS, add_symbol, export_watchlist, import_watchlist, remove_symbol


def test_add_is_canonical_unique_and_does_not_mutate_original():
    original = ["MSFT"]
    assert add_symbol(original, " aapl ") == ["MSFT", "AAPL"]
    assert original == ["MSFT"]
    assert add_symbol(["AAPL"], "aapl") == ["AAPL"]


def test_remove_is_safe_and_does_not_mutate_original():
    original = ["AAPL", "MSFT"]
    assert remove_symbol(original, "aapl") == ["MSFT"]
    assert remove_symbol(original, "NVDA") == original
    assert original == ["AAPL", "MSFT"]


def test_lists_are_isolated():
    first, second = [], []
    first = add_symbol(first, "AAPL")
    assert second == []
    assert first == ["AAPL"]


def test_export_import_roundtrip():
    symbols = ["AAPL", "BRK-B", "VOD.L"]
    assert import_watchlist(export_watchlist(symbols).encode()) == symbols
    assert json.loads(export_watchlist([])) == {"version": 1, "symbols": []}


@pytest.mark.parametrize("payload", [b"not json", b"\xff", "[]", '{"version": 2, "symbols": []}', '{"version": true, "symbols": []}', '{"version": 1, "symbols": "AAPL"}', '{"version": 1, "symbols": ["../../file"]}', '{"version": 1, "symbols": [1]}'])
def test_import_rejects_bad_schema_and_symbols(payload):
    with pytest.raises(ValueError):
        import_watchlist(payload)


def test_capacity_and_import_size_limits():
    symbols = [f"STK{i}" for i in range(MAX_SYMBOLS)]
    assert add_symbol(symbols, symbols[0]) == symbols
    with pytest.raises(ValueError):
        add_symbol(symbols, "NEXT")
    with pytest.raises(ValueError):
        import_watchlist(b" " * (MAX_IMPORT_BYTES + 1))
