"""Optional online integration check: python scripts/check_market_data.py.

Unlike pytest, this explicitly contacts Yahoo Finance. Exit 1 means that the
provider check failed, which can also indicate a network outage or rate limit.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_provider import MarketDataError, YahooFinanceProvider
from src.indicators import normalize_returns


def main() -> int:
    provider = YahooFinanceProvider()
    end = datetime.now(timezone.utc).date()
    try:
        quote = provider.quote("AAPL")
        history = provider.history("AAPL", end - timedelta(days=45), end)
        print(f"AAPL: {len(history)} daily rows; latest price {quote.price:.2f} {quote.currency}; quote time {quote.timestamp}; exact={quote.timestamp_is_exact}")
        if history["Adj Close"].dropna().empty:
            print("FAIL: Adjusted close values were not returned.")
            return 1
        other = provider.history("MSFT", end - timedelta(days=45), end)
        comparison = normalize_returns({"AAPL": history["Adj Close"], "MSFT": other["Adj Close"]})
        if len(comparison) < 2 or not comparison.iloc[0].eq(0).all():
            print("FAIL: Real-data comparison did not produce a common zero baseline.")
            return 1
        print(f"AAPL / MSFT comparison: {len(comparison)} aligned trading dates")
        try:
            profile = provider.profile("AAPL")
            print(f"Company details: {profile.get('longName') or 'name unavailable'}; market cap {'available' if profile.get('marketCap') else 'unavailable'}")
        except MarketDataError as exc:
            print(f"Optional company details unavailable: {exc}")
        try:
            provider.quote("ZZZZZZZZZZ")
        except MarketDataError:
            print("Unavailable-symbol handling: passed")
        else:
            print("FAIL: The unavailable-symbol probe unexpectedly returned a quote.")
            return 1
    except MarketDataError as exc:
        print(f"Provider check could not complete: {exc}")
        return 1
    print("Online integration check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
