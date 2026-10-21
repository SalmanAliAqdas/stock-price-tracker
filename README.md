# Market Atlas

A stock research dashboard built with Python and Streamlit. Track the latest
available prices, explore historical performance, compare companies, and keep a
private session watchlist in a focused dark navy interface.

## Features

| Page | Capabilities |
| --- | --- |
| Dashboard | Ticker search, latest available quote, daily change, volume, market capitalization, company profile, adjusted history chart |
| Stock Analysis | Inclusive date ranges, line and candlestick charts, volume, SMA 20/50, Wilder RSI 14, period high/low and adjusted return, CSV export |
| Stock Comparison | Two to four symbols, aligned trading dates, percentage performance, start/end adjusted prices, currency labels, CSV export |
| Watchlist | Add/remove up to 12 stocks, available quotes, JSON backup and restore, per-session isolation |
| About & Help | Chart and indicator explanations, price conventions, data limitations, privacy and financial disclaimer |

The interface uses Streamlit navigation, forms, metric cards, accessible controls,
responsive columns, and interactive Plotly charts. Custom CSS styles only
application-owned markup; it does not target Streamlit's internal class names.
No API key or paid service is required.

## Requirements

- Python 3.11 or newer; the current dependency set was verified on Python 3.13.
- An internet connection to retrieve market data from Yahoo Finance.
- Git for source control.

Direct dependencies are pinned in `requirements.txt`. Test dependencies are in
`requirements-dev.txt`. Transitive dependencies are resolved by pip; these files
are not a complete environment lock.

## Local installation

From the project directory, create an isolated environment and install dependencies.

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**macOS / Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m streamlit run app.py
```

Open the local address printed by Streamlit, normally `http://localhost:8501`.
Activation is optional when using the environment's Python executable directly.
For an application-only installation, use `requirements.txt` instead.

## Using the dashboard

1. Search for a Yahoo Finance ticker such as `AAPL`, `MSFT`, `NVDA`, or `BRK-B`.
   Syntax validation happens before a network request. A correctly formatted
   symbol may still be unavailable or unlisted. US stocks are the primary focus;
   supported exchange suffixes such as `VOD.L` can also be entered.
2. Choose a historical horizon on the Dashboard or an inclusive date range in
   Stock Analysis. Date ranges are limited to ten years.
3. Hover over charts to inspect values, drag to zoom, and double-click to reset.
   Switch between adjusted line charts and unadjusted daily candles in Analysis.
4. Compare two to four unique symbols, separated by commas. Unavailable symbols
   are excluded with an explanation; at least two usable symbols must remain.
5. Add stocks to the Watchlist. Export JSON before ending a session, then import
   the file to restore the list. An import replaces the current list.
6. Expand the analysis data table to download historical OHLC, adjusted closes,
   volume, and indicator columns as CSV.

## Data and financial conventions

### Quotes and timestamps

Yahoo Finance data is accessed through the unofficial
[yfinance library](https://ranaroussi.github.io/yfinance/). Quotes can be delayed;
the application does not claim to provide a live trading feed.

When available, the quote's provider-supplied `regularMarketTime` is displayed in
UTC, paired with its regular market price. Both epoch and localized timestamp
formats are supported. Metadata older than the latest daily session is ignored.
If an exact quote time is unavailable, the application labels the latest daily
bar with its exchange-local session date. A daily bar's midnight index or the
time a request completed is never presented as an exact quote time. The current
daily bar and its volume may still be incomplete during market hours.

Daily change is measured against the previous available unadjusted daily close.
If only one daily bar exists, the change remains unavailable. Missing company
details, market capitalization, volume, or currency are shown as unavailable;
USD is never assumed for an unknown currency.

### Historical prices and returns

Requests explicitly use `auto_adjust=False` to retain raw OHLC and `Adj Close`.

- Candlesticks, period intraday high/low, and latest-price cards use unadjusted
  values. Historical OHLC can still reflect the provider's own split handling.
- Historical line charts, SMA, RSI, and period/comparison returns use Yahoo's
  split- and dividend-adjusted `Adj Close`. The adjusted series is a provider
  convention, not a simulation of an investor's executed trades.
- Return is `(end / start - 1) × 100`. Missing or nonpositive starting values
  yield unavailable results. No adjusted-to-unadjusted fallback is performed.
- SMA requires a full window of valid observations. Analysis requests up to 180
  earlier calendar days to warm up indicators where available, while displaying
  only the selected range. The overall ten-year request limit still applies.
- RSI 14 uses Wilder's arithmetic seed and recursive smoothing. It needs 15
  consecutive valid closes. Missing values restart warmup; a flat series is 50,
  only gains is 100, and only losses is 0. Levels 30/70 are descriptive references.
- Volume summaries ignore missing or negative values; absent volume is not
  replaced with fictional trading activity.

### Comparisons and currencies

Each symbol's exchange-local calendar session dates are aligned with an inner
join. Only common dates with valid, positive adjusted prices are retained. There
is no forward filling, extrapolation, or assumed price for a missing date.
At least two common dates are required. Every percentage line begins at zero on
the same actual starting date, which can be later than the requested start date.

The comparison table labels each stock's own quotation currency. Percentage
returns compare **local-currency performance**, excluding foreign exchange
effects into an investor's home currency. Raw prices across currencies are not
plotted together. No currency conversion, fee, tax, or execution-cost model is
included. Matching calendar dates across exchanges do not imply simultaneous
closing times.

### Caching and outages

| Public data | Cache lifetime | Entry limit |
| --- | --- | --- |
| Quotes | 120 seconds | 128 |
| Daily history | 15 minutes | 128 |
| Company details | 1 hour | 128 |

Failure results share these lifetimes to avoid repeatedly contacting a failing
or rate-limited provider. There is no automatic polling or retry loop. Streamlit
reruns reuse cached results until expiry. After a provider failure, wait for the
relevant cache lifetime before trying again; broader Yahoo rate limits may last
longer. Empty data can mean an unavailable symbol, a nontrading date range, a
delisting, or a provider issue. The application does not invent replacement data.

## Watchlist privacy and persistence

Watchlists are stored only in `st.session_state`, independently for each Streamlit
session. No watchlist is cached globally, stored in SQLite, or written to the
server filesystem. Public market data caches may be shared between sessions;
personal lists are not.

Reloading the page, losing a session, or restarting the cloud instance may clear
the list. JSON export is an explicit browser download. Imports are parsed as data
only, with a versioned schema, validated symbols, a 16 KB limit, and a 12-symbol
limit. An import never executes file content or uses an uploaded path.

This release has no authentication or durable user-specific persistence. A shared
SQLite watchlist would mix unrelated visitors and is intentionally excluded.
Future persistence requires authenticated user isolation and a reliable external
store; a local database alone is unsuitable for public multi-user watchlists.

## Project structure

```text
stock-price-tracker/
├── app.py                         # Navigation and shared application shell
├── requirements.txt               # Pinned application dependencies
├── requirements-dev.txt           # Application + pytest
├── pytest.ini
├── .python-version                # Local Python preference; select cloud version separately
├── .streamlit/config.toml         # Theme and deployment-safe defaults
├── src/
│   ├── __init__.py
│   ├── data_provider.py           # Provider protocol and Yahoo adapter
│   ├── market_data.py             # Streamlit public-data cache boundary
│   ├── indicators.py              # Pure, testable calculations
│   ├── charts.py                  # Plotly figure builders
│   ├── dashboard.py               # Dashboard page renderer
│   ├── ui.py                      # Shared controls and application-owned CSS
│   ├── utils.py                   # Validation, formatting, CSV
│   └── watchlist.py               # Pure list operations and JSON validation
├── pages/
│   ├── 1_Stock_Analysis.py
│   ├── 2_Stock_Comparison.py
│   ├── 3_Watchlist.py
│   └── 4_About.py
├── scripts/
│   ├── check_market_data.py       # Explicit, optional online integration check
│   └── check_startup.py           # Temporary local HTTP readiness check
└── tests/
    ├── conftest.py
    ├── test_indicators.py
    ├── test_utils.py
    ├── test_watchlist.py
    ├── test_data_provider.py
    └── test_app.py
```

The extra `market_data.py` module keeps UI caching outside the replaceable provider
adapter. `ui.py` and `dashboard.py` keep the entry point small while sharing page
controls. A provider implementing `MarketDataProvider` can be substituted at the
cache boundary without rewriting calculations or chart builders.

## Tests and verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_startup.py
```

The pytest suite uses synthetic fixtures confined to tests and blocks Yahoo ticker
creation unless explicitly mocked. It requires no internet access. Tests cover
calculation reference values and edge cases, date alignment, missing adjustment
data, ticker validation, timestamps, outages/rate limits, cache reuse, watchlist
isolation and JSON validation, all five pages, and form/chart interactions through
Streamlit's native `AppTest` harness.

The startup check launches a temporary server on a free localhost port, verifies
the health endpoint and application HTML both return HTTP 200, then stops its
process. It does not perform a browser visual review or contact Yahoo Finance.

An optional integration check makes a small number of real Yahoo requests:

```powershell
.\.venv\Scripts\python.exe scripts/check_market_data.py
```

This checks AAPL quotes, AAPL/MSFT adjusted history and alignment, optional company
details, and an unavailable-symbol response.
It is separate from pytest because network access and upstream availability are
not deterministic. Its failure can indicate a rate limit or network issue.

## GitHub publication

The project contains no API keys and does not require a secrets file. `.gitignore`
excludes virtual environments, local credentials, caches, databases, and watchlist
backups. Before publication:

1. Run the offline tests and inspect the app locally.
2. Review tracked files and choose a project license before granting reuse rights.
3. Initialize a Git repository if necessary, stage source files, and create a commit.
4. Create or select a GitHub repository and push the reviewed commit.

GitHub publication and remote repository changes are separate, explicit actions.

## Deploying on Streamlit Community Cloud

The application is prepared for Community Cloud with `app.py` at the repository
root, a root `requirements.txt`, and `.streamlit/config.toml`. No paid service,
local absolute path, database file, or secret is needed at runtime.

1. Publish the reviewed project to GitHub.
2. In [Streamlit Community Cloud](https://share.streamlit.io), create an app and
   select the repository and branch.
3. Set the main file path to `app.py`.
4. In Advanced settings, choose Python **3.13**, matching the verified local
   environment. `.python-version` does not replace the cloud version selection.
5. Deploy and inspect Dashboard, Analysis, Comparison, Watchlist, and About.
   Test Yahoo access from the hosted app and check its logs if data is unavailable.

See the official [Community Cloud deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

Community Cloud instances can sleep or restart, memory caches can be discarded,
and outbound requests can be rate limited or blocked by the provider. Local disk
is not durable user storage. Watchlists remain session-only. Successful local
Yahoo access does not guarantee uninterrupted access from a shared cloud IP.

## Data usage and financial disclaimer

Market Atlas is an educational research project, unaffiliated with Yahoo Finance,
any exchange, or any listed company. yfinance is an unofficial client and does not
grant market-data redistribution rights. Review applicable
[Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) and exchange
restrictions before operating a public instance or redistributing downloaded data.

Information may be delayed, incomplete, or inaccurate. Nothing in this application
is financial advice or a recommendation to buy or sell securities. Indicators are
descriptive tools, not guaranteed signals. Verify data independently before making
financial decisions. Past performance does not guarantee future results.
