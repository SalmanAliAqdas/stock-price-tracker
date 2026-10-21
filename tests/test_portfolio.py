from dataclasses import replace
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from src.data_provider import Quote
from src.portfolio import MAX_HOLDINGS, add_holding, create_holding, summarize_portfolio, value_holding


def holding(currency="USD", market="yahoo", shares="10", price="100"):
    return create_holding("OGDC" if market == "psx" else "AAPL", shares, price, date(2025, 1, 1), currency, market)


def quote(symbol="AAPL", currency="USD", price=120):
    return Quote(symbol, "Test company", currency, price, 119, 1, 1 / 119 * 100, 1000,
                 pd.Timestamp("2025-02-01 20:00", tz="UTC"), True, "Test quote")


def test_invested_current_pnl_and_percentage_are_exact():
    row = value_holding(holding(), quote())
    assert row["invested"] == Decimal("1000")
    assert row["current_value"] == Decimal("1200")
    assert row["unrealized_pnl"] == Decimal("200")
    assert row["return_percent"] == Decimal("20")
    loss = value_holding(holding(), quote(price=75))
    assert loss["unrealized_pnl"] == Decimal("-250")
    assert loss["return_percent"] == Decimal("-25")


def test_fractional_shares_do_not_accumulate_binary_rounding_error():
    row = value_holding(holding(shares="0.1", price="0.2"), quote(price=0.3))
    assert row["invested"] == Decimal("0.02")
    assert row["unrealized_pnl"] == Decimal("0.01")


def test_currencies_stay_separate_and_missing_quotes_are_not_zero():
    rows = [value_holding(holding(), quote()), value_holding(holding("PKR", "psx"), None)]
    groups = summarize_portfolio(rows)
    assert set(groups) == {"USD", "PKR"}
    assert groups["USD"]["current_value"] == Decimal("1200")
    assert groups["PKR"]["total_invested"] == Decimal("1000")
    assert groups["PKR"]["current_value"] is None
    assert groups["PKR"]["unrealized_pnl"] is None
    assert summarize_portfolio([]) == {}


def test_partial_coverage_keeps_overall_return_unavailable():
    rows = [value_holding(holding(), quote()), value_holding(holding(), None)]
    summary = summarize_portfolio(rows)["USD"]
    assert summary["total_invested"] == 2000
    assert summary["priced_value"] == 1200
    assert summary["priced_lots"] == 1
    assert summary["current_value"] is None
    assert summary["return_percent"] is None


@pytest.mark.parametrize("bad_quote", [quote(currency="PKR"), quote(currency=None), quote(currency="bad currency"), quote(symbol="MSFT"), quote(price=0), quote(price=float("nan")), replace(quote(), timestamp=pd.Timestamp("2024-01-01"))])
def test_unusable_quote_is_unavailable(bad_quote):
    result = value_holding(holding(), bad_quote)
    assert result["current_value"] is None
    assert result["unrealized_pnl"] is None


def test_pence_are_not_silently_converted_to_pounds():
    row = value_holding(holding("GBP"), quote(currency="GBp"))
    assert row["current_value"] is None
    assert set(summarize_portfolio([value_holding(holding("GBP"), None), value_holding(holding("GBp"), None)])) == {"GBP", "GBp"}


@pytest.mark.parametrize("bad_value", [0, -1, "NaN", "Infinity", "bad", None, True, "1000000000001"])
def test_rejects_invalid_shares_and_purchase_prices(bad_value):
    with pytest.raises(ValueError):
        holding(shares=bad_value)
    with pytest.raises(ValueError):
        holding(price=bad_value)


def test_purchase_date_currency_and_market_validation():
    with pytest.raises(ValueError, match="future"):
        create_holding("AAPL", 1, 100, date(2025, 3, 1), "USD", today=date(2025, 1, 1))
    with pytest.raises(ValueError, match="PKR"):
        holding("USD", "psx")
    with pytest.raises(ValueError):
        holding("US dollars")
    with pytest.raises(ValueError):
        holding(market="unknown")


def test_purchase_lots_are_distinct_and_add_does_not_mutate():
    first, second = holding(), holding()
    assert first.id != second.id
    original = [first]
    assert add_holding(original, second) == [first, second]
    assert original == [first]
    with pytest.raises(ValueError):
        add_holding([first] * MAX_HOLDINGS, second)
