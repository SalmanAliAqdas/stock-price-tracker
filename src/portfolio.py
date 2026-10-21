"""Pure portfolio calculations with decimal amounts and currency isolation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from uuid import uuid4

from src.data_provider import Quote
from src.utils import validate_ticker
from src.watchlist import validate_market

MAX_HOLDINGS = 100


def amount(value) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Enter a finite positive number.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Enter a finite positive number.") from exc
    if not result.is_finite() or not 0 < result <= Decimal("1000000000000"):
        raise ValueError("Shares and purchase prices must be greater than zero and at most one trillion.")
    return result


def validate_currency(value: str) -> str:
    # Yahoo's GBp denotes pence, distinct from pounds sterling (GBP).
    if not isinstance(value, str):
        raise ValueError("Enter a three-letter currency code.")
    currency = value.strip()
    if currency != "GBp":
        currency = currency.upper()
    if not re.fullmatch(r"[A-Z]{3}|GBp", currency):
        raise ValueError("Enter a three-letter currency code, such as USD or PKR.")
    return currency


@dataclass(frozen=True)
class Holding:
    id: str
    symbol: str
    shares: Decimal
    purchase_price: Decimal
    purchase_date: date
    currency: str
    market: str = "yahoo"


def create_holding(symbol: str, shares, purchase_price, purchase_date: date,
                   currency: str, market: str = "yahoo", today: date | None = None) -> Holding:
    market = validate_market(market)
    currency = validate_currency(currency)
    if market == "psx" and currency != "PKR":
        raise ValueError("Pakistan holdings must use PKR. Currency conversion is not available.")
    if type(purchase_date) is not date or purchase_date > (today or date.today()):
        raise ValueError("Choose a valid purchase date that is not in the future.")
    return Holding(uuid4().hex, validate_ticker(symbol), amount(shares), amount(purchase_price), purchase_date, currency, market)


def add_holding(holdings: list[Holding], holding: Holding) -> list[Holding]:
    if len(holdings) >= MAX_HOLDINGS:
        raise ValueError(f"A session portfolio can contain up to {MAX_HOLDINGS} purchase lots.")
    return [*holdings, holding]


def value_holding(holding: Holding, quote: Quote | None, reason: str = "Quote not loaded") -> dict:
    invested = holding.shares * holding.purchase_price
    current = pnl = pct = None
    if quote is not None:
        try:
            quote_currency = validate_currency(quote.currency) if quote.currency else None
        except ValueError:
            quote_currency = None
        if quote.symbol != holding.symbol:
            reason = "Quote symbol does not match this holding"
        elif quote_currency != holding.currency:
            reason = "Quote currency differs or is unknown; no conversion performed"
        elif quote.timestamp.date() < holding.purchase_date:
            reason = "Available quote predates the purchase"
        else:
            try:
                current = holding.shares * amount(quote.price)
                pnl = current - invested
                pct = pnl / invested * 100
                reason = "Available estimate; quote may be delayed"
            except ValueError:
                reason = "Quote price is unavailable"
    return {"holding": holding, "invested": invested, "current_value": current,
            "unrealized_pnl": pnl, "return_percent": pct, "status": reason,
            "quote": quote if current is not None else None}


def summarize_portfolio(valuations: list[dict]) -> dict[str, dict]:
    """Never sum currencies or treat missing quotes as zero-value holdings."""
    grouped = {}
    for row in valuations:
        grouped.setdefault(row["holding"].currency, []).append(row)
    results = {}
    for currency, rows in grouped.items():
        invested = sum((row["invested"] for row in rows), Decimal(0))
        covered = [row for row in rows if row["current_value"] is not None]
        complete = len(covered) == len(rows)
        priced_value = sum((row["current_value"] for row in covered), Decimal(0))
        current = priced_value if complete else None
        pnl = current - invested if complete else None
        results[currency] = {"total_invested": invested, "current_value": current,
                             "unrealized_pnl": pnl, "return_percent": pnl / invested * 100 if complete else None,
                             "priced_value": priced_value, "priced_lots": len(covered), "total_lots": len(rows),
                             "complete": complete}
    return results
