"""Session-state-compatible watchlists; no global or filesystem persistence."""

from __future__ import annotations

import json
import csv
import io

from src.utils import validate_ticker

MAX_SYMBOLS = 100
MAX_IMPORT_BYTES = 65_536


def validate_market(market: str) -> str:
    if market not in {"yahoo", "psx"}:
        raise ValueError("Choose the international or Pakistan market.")
    return market


def clean_watchlist(symbols: list[str]) -> list[str]:
    if not isinstance(symbols, list):
        raise ValueError("Watchlist symbols must be a list.")
    result = list(dict.fromkeys(validate_ticker(symbol) for symbol in symbols))
    if len(result) > MAX_SYMBOLS:
        raise ValueError(f"A watchlist can contain up to {MAX_SYMBOLS} stocks.")
    return result


def add_symbol(symbols: list[str], symbol: str) -> list[str]:
    return clean_watchlist([*symbols, validate_ticker(symbol)])


def remove_symbol(symbols: list[str], symbol: str) -> list[str]:
    target = validate_ticker(symbol)
    return [item for item in clean_watchlist(symbols) if item != target]


def filter_symbols(symbols: list[str], query: str = "", descending: bool = False) -> list[str]:
    query = query.strip().upper()
    return sorted((symbol for symbol in clean_watchlist(symbols) if query in symbol), reverse=descending)


def export_watchlist(symbols: list[str], market: str = "yahoo", file_format: str = "json") -> str:
    market = validate_market(market)
    symbols = clean_watchlist(symbols)
    if file_format == "json":
        return json.dumps({"version": 2, "market": market, "symbols": symbols}, indent=2)
    if file_format != "csv":
        raise ValueError("Choose JSON or CSV.")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["market", "symbol"])
    writer.writerows((market, symbol) for symbol in symbols)
    return buffer.getvalue()


def import_watchlist(payload: bytes | str, market: str = "yahoo", file_format: str = "json") -> list[str]:
    market = validate_market(market)
    if not isinstance(payload, (bytes, str)):
        raise ValueError("Choose a UTF-8 JSON or CSV watchlist file.")
    if len(payload.encode("utf-8") if isinstance(payload, str) else payload) > MAX_IMPORT_BYTES:
        raise ValueError("Watchlist files must be smaller than 64 KB.")
    try:
        text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload.lstrip("\ufeff")
        if file_format == "csv":
            reader = csv.DictReader(io.StringIO(text))
            if reader.fieldnames != ["market", "symbol"]:
                raise ValueError("CSV must have market,symbol columns, as exported by Market Atlas.")
            rows = list(reader)
            if any(set(row) != {"market", "symbol"} or row["market"] != market for row in rows):
                raise ValueError("This backup belongs to another market or has invalid columns.")
            return clean_watchlist([row["symbol"] for row in rows])
        if file_format != "json":
            raise ValueError("Choose JSON or CSV.")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, csv.Error) as exc:
        raise ValueError("The file is not a valid UTF-8 watchlist backup.") from exc
    if not isinstance(data, dict) or type(data.get("version")) is not int:
        raise ValueError("Use a watchlist exported by Market Atlas.")
    if data["version"] == 1:
        if market != "yahoo":
            raise ValueError("Legacy watchlists belong to the international market.")
    elif data["version"] != 2 or data.get("market") != market:
        raise ValueError("This backup uses an unsupported version or belongs to another market.")
    return clean_watchlist(data.get("symbols"))
