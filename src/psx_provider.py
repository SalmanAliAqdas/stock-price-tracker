"""Licensed PSX integration contract; no scraping or assumed Yahoo mappings."""

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from src.data_provider import MarketDataError, MarketDataProvider

PSX_REQUIREMENT = (
    "PSX market data is not connected. A licensed provider, documented API access, "
    "and permission to display data in this public app are required. Prices, "
    "history, and KSE-100 levels remain unavailable until that connection is implemented."
)


@dataclass(frozen=True)
class Security:
    symbol: str
    name: str


@dataclass(frozen=True)
class ProviderStatus:
    name: str = "PSX licensed feed not connected"
    available: bool = False
    message: str = PSX_REQUIREMENT
    allow_exports: bool = False


@dataclass(frozen=True)
class IndexOverview:
    name: str
    level: float
    change: float | None
    change_percent: float | None
    timestamp: pd.Timestamp
    timestamp_is_exact: bool
    data_source: str


class PakistanDataProvider(MarketDataProvider, Protocol):
    def status(self) -> ProviderStatus: ...
    def search(self, query: str) -> list[Security]: ...
    def index_overview(self) -> IndexOverview: ...


class UnconfiguredPSXProvider:
    def status(self) -> ProviderStatus:
        return ProviderStatus()

    def _unavailable(self, *args, **kwargs):
        raise MarketDataError(PSX_REQUIREMENT)

    quote = history = profile = search = index_overview = _unavailable


def get_psx_provider() -> PakistanDataProvider:
    """Return an authorized adapter only after a vendor contract is established.

    No credential or configuration flag alone activates this placeholder. Add a
    tested adapter against the contracted API; see docs/psx-data-providers.md.
    """
    return UnconfiguredPSXProvider()
