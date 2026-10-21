# Pakistan Stock Exchange data integration

Research reviewed on **21 October 2026**. No licensed PSX feed or credentials are
included in this repository, and no PSX market-data requests are made by this release.

## Current implementation

The Pakistan Stock Exchange page has KSE-100, stock research, comparison, and a
separate 100-symbol watchlist. `src/psx_provider.py` defines `PakistanDataProvider`,
`Security`, `ProviderStatus`, and `IndexOverview`. The default adapter deliberately
returns an explanatory unavailable result instead of prices.

The watchlist and PKR purchase-cost calculations work without market data.
Quotes, historical charts, directory search results, index values, and current
portfolio valuations require a concrete licensed provider adapter. An API key or
an environment flag alone does not activate the placeholder. No scraped endpoint,
Yahoo symbol guess, or fabricated price is used.

## Provider investigation

| Candidate | Documentation and access | Licensing and current decision |
| --- | --- | --- |
| PSX directly | Official data services cover feeds, end-of-day, and historical data. Delivery specifications, credentials, and commercial terms require discussion with the exchange. | Public display requires appropriate rights; no anonymous public redistribution API was established. |
| Capital Stake | Published REST documentation, HTTPS production/UAT endpoints, and bearer-token authentication. Documented index coverage includes KSE100. | A credible integration candidate, but this project has no contract, token, or grant of public-display rights. No connection is activated. |
| Mettis Global / MG Link | Official API product describes JSON, SOAP, and XML delivery over the internet or dedicated connectivity. | Detailed endpoint access, credentials, PSX entitlements, and redistribution permission must be obtained from the vendor. |
| EODHD / Twelve Data | General API documentation and licensing information are available. | PSX equity/index coverage and public-display rights for this deployment were not established. Neither is treated as a PSX provider. |

### PSX policy

The exchange's published notice covers dissemination of live and delayed data,
including prices, volume, and index levels. Website visibility does not establish
permission to republish data in another application. Its data-services page also
identifies vendors, with redistribution subject to the relevant PSX permissions.
The listed licensing contact is `marketdatarequest@psx.com.pk`.

Sources: [PSX data services](https://www.psx.com.pk/psx/product-and-services/data-services-vending)
and [PSX market-data legal notice](https://www.psx.com.pk/psx/themes/psx/uploads/PSX_Data_Legal_Notice.pdf).

### Capital Stake

The [official getting-started guide](https://www.capitalstake.com/docs/rest/intro)
documents `Authorization: Bearer …`, HTTPS JSON responses, and rate limits agreed
with support. Its [index endpoint](https://www.capitalstake.com/docs/rest/api/stocks/market-quotes-and-trading/stocks-index-overview/market-index)
documents `GET /3.0/market/index?code=KSE100`. The
[data-solutions page](https://www.capitalstake.com/data-solutions) describes stock,
historical, and index datasets, with sales-led access.

Before implementing an adapter, obtain the actual response schema, entitlements,
request quotas, adjustment methodology, timestamp timezone, and usage agreement.
For example, a percentage field's unit must be confirmed from an entitled response
and vendor specification before mapping it to this application's percentage units.
No sample response values are embedded as market prices.

### Mettis Global and other candidates

[MG Link's official API product page](https://mettisglobal.news/MGAPIs) describes
integration for internal and client-facing systems. It does not provide this
project with an access token, an endpoint contract, or permission to redistribute
PSX data; those remain vendor onboarding requirements.

[EODHD's quick start](https://eodhd.com/financial-apis/quick-start-with-our-financial-data-apis)
requires an API token and recommends checking coverage per endpoint. No guessed
exchange suffix is used. [Twelve Data's usage policy](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage)
distinguishes individual access from public/commercial display and redistribution.
These general APIs should be evaluated only after confirming PSX-specific coverage
and the applicable exchange rights.

## Integration requirements

1. Obtain written rights for this public application's intended audience, data
   delay, index display, cached storage, derived calculations, and any downloads.
2. Obtain vendor API credentials, documented equity/index identifiers, historical
   schemas, rate limits, and corporate-action/adjustment conventions.
3. Implement the `PakistanDataProvider` methods and select that adapter in
   `get_psx_provider()`. `status().available` should reflect a configured, entitled
   adapter. Keep exports disabled unless their rights have been granted.
4. Return PKR equity prices, exact aware timestamps where available, source names,
   raw OHLC, and genuinely adjusted prices when supplied. Missing adjustments must
   remain missing. Index levels are in points, not PKR. Never copy raw closes into
   `Adj Close` simply to enable comparisons.
5. Add offline adapter tests for credentials/errors, entitlements, rate limits,
   empty responses, unit conversions, timezones, and corporate-action handling.
6. Test a small number of entitled requests in the deployment environment before
   making the adapter available publicly.

`allow_exports` controls the application's explicit market-data download buttons.
It is not a security boundary against copying data already displayed in a browser.
Watchlist backups and portfolio exports contain user-entered records rather than
licensed market prices.

## Streamlit Community Cloud compatibility

**Engineering assessment:** A vendor's HTTPS REST API is a suitable integration
path for Streamlit's Python server, subject to that vendor's hosting permissions
and network restrictions. This is not a claim that access has been tested from
the current cloud deployment.

Store a future adapter's token in Community Cloud secrets or an ignored local
`.streamlit/secrets.toml`, read it only on the server, and send it in the documented
authorization header. Do not put credentials in chart payloads, cache arguments,
URLs, browser inputs, logs, or committed files.

Confirm that shared cloud IPs are permitted. An agreement requiring a fixed source
IP, private connectivity, uninterrupted streaming, or durable local storage may
need different hosting. Use negotiated cache lifetimes and quotas rather than
assuming the default Yahoo intervals satisfy the PSX contract. Continuous feed
connections are outside this release's design.
