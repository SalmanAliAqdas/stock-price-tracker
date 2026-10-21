"""Session-state-compatible watchlists; no global or filesystem persistence."""

from __future__ import annotations

import json

from src.utils import validate_ticker

MAX_SYMBOLS = 12
MAX_IMPORT_BYTES = 16_384


def clean_watchlist(symbols: list[str]) -> list[str]:
    if not isinstance(symbols, list):
        raise ValueError("Watchlist symbols must be a JSON list.")
    result = list(dict.fromkeys(validate_ticker(symbol) for symbol in symbols))
    if len(result) > MAX_SYMBOLS:
        raise ValueError(f"A watchlist can contain up to {MAX_SYMBOLS} stocks.")
    return result


def add_symbol(symbols: list[str], symbol: str) -> list[str]:
    return clean_watchlist([*symbols, validate_ticker(symbol)])


def remove_symbol(symbols: list[str], symbol: str) -> list[str]:
    target = validate_ticker(symbol)
    return [item for item in clean_watchlist(symbols) if item != target]


def export_watchlist(symbols: list[str]) -> str:
    return json.dumps({"version": 1, "symbols": clean_watchlist(symbols)}, indent=2)


def import_watchlist(payload: bytes | str) -> list[str]:
    if not isinstance(payload, (bytes, str)):
        raise ValueError("Choose a UTF-8 JSON watchlist file.")
    if len(payload.encode("utf-8") if isinstance(payload, str) else payload) > MAX_IMPORT_BYTES:
        raise ValueError("Watchlist files must be smaller than 16 KB.")
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ValueError("The file is not valid UTF-8 JSON.") from exc
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Use a version 1 watchlist exported by Market Atlas.")
    return clean_watchlist(data.get("symbols"))
