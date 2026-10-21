"""Session-only purchase-lot tracker; no brokerage or currency conversion."""

import pandas as pd
import streamlit as st

from src.market_data import get_quote
from src.portfolio import MAX_HOLDINGS, add_holding, create_holding, summarize_portfolio, value_holding
from src.ui import footer, note, page_header, today
from src.utils import format_price, format_quote_timestamp

page_header("YOUR HOLDINGS", "Track the numbers behind your ideas.", "Record purchase lots, estimate unrealized gains, and understand allocation. Every currency has its own totals; no exchange-rate conversion is applied.")
with st.form("portfolio_add", clear_on_submit=True):
    left, right = st.columns(2)
    with left:
        symbol = st.text_input("Company symbol", placeholder="AAPL or OGDC", key="portfolio_symbol", max_chars=32)
        shares = st.number_input("Number of shares", min_value=0.0, max_value=1e12, value=1.0, step=1.0, format="%.6f", key="portfolio_shares")
        purchased = st.date_input("Purchase date", value=today(), max_value=today(), key="portfolio_date")
    with right:
        market_label = st.selectbox("Market", ["International / Yahoo", "Pakistan / PSX"], key="portfolio_market")
        price = st.number_input("Purchase price per share", min_value=0.0, max_value=1e12, value=0.0, format="%.6f", key="portfolio_price")
        currency = st.text_input("Currency", value="USD", help="Use PKR for PSX. GBp means pence and is distinct from GBP.", max_chars=3, key="portfolio_currency")
    submitted = st.form_submit_button("Add holding", type="primary", icon=":material/add:")
if submitted:
    try:
        holding = create_holding(symbol, shares, price, purchased, currency, "psx" if market_label == "Pakistan / PSX" else "yahoo", today())
        st.session_state["portfolio"] = add_holding(st.session_state["portfolio"], holding)
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))

holdings = st.session_state["portfolio"]
st.caption(f"{len(holdings)} / {MAX_HOLDINGS} purchase lots · Holdings are private to this session. Export before leaving.")
if not holdings:
    note("Start with a purchase", "Enter a symbol, shares, purchase price, purchase date, and currency. Invested cost is available immediately; current values need a matching market quote.")
else:
    estimates = st.session_state.setdefault("portfolio_estimates", {})
    keys = list(dict.fromkeys((holding.market, holding.symbol) for holding in holdings))
    # The cursor cycles over small groups. Ordinary reruns never contact providers.
    cursor = st.session_state.get("portfolio_quote_cursor", 0) % len(keys)
    pending = keys[cursor:cursor + 10]
    if st.button(f"Update estimates ({len(pending)} companies)", type="primary", icon=":material/refresh:"):
        with st.spinner("Updating available estimates…"):
            for market, symbol in pending:
                estimates[(market, symbol)] = get_quote(symbol, market)
        st.session_state["portfolio_quote_cursor"] = (cursor + len(pending)) % len(keys)
    st.caption("Updates cover up to ten companies per click and reuse the two-minute quote cache. Repeated clicks move through larger portfolios. Missing or mismatched-currency quotes leave totals unavailable.")
    valuations = []
    for holding in holdings:
        result = estimates.get((holding.market, holding.symbol))
        valuations.append(value_holding(holding, result.data if result else None, result.error if result and result.error else "Quote not loaded"))
    summaries = summarize_portfolio(valuations)
    selected = st.selectbox("Currency account", sorted(summaries), key="portfolio_account")
    summary = summaries[selected]
    rows = [row for row in valuations if row["holding"].currency == selected]
    columns = st.columns(2)
    columns[0].metric("Total invested", format_price(summary["total_invested"], selected), border=True)
    columns[1].metric("Current estimated value", format_price(summary["current_value"], selected), border=True)
    columns = st.columns(2)
    columns[0].metric("Unrealized profit / loss", format_price(summary["unrealized_pnl"], selected), border=True)
    columns[1].metric("Return", f"{summary['return_percent']:+.2f}%" if summary["return_percent"] is not None else "—", border=True)
    if not summary["complete"]:
        st.info(f"Quotes cover {summary['priced_lots']} of {summary['total_lots']} lots in {selected}. The priced portion is {format_price(summary['priced_value'], selected)}. Overall value and return remain unavailable until all lots are priced.")
    records = []
    for row in rows:
        holding, quote = row["holding"], row["quote"]
        records.append({"Symbol": holding.symbol, "Market": holding.market, "Shares": float(holding.shares),
                        "Purchase price": float(holding.purchase_price), "Purchase date": holding.purchase_date,
                        "Currency": holding.currency, "Invested": float(row["invested"]),
                        "Current value": float(row["current_value"]) if row["current_value"] is not None else None,
                        "Unrealized P/L": float(row["unrealized_pnl"]) if row["unrealized_pnl"] is not None else None,
                        "Return (%)": float(row["return_percent"]) if row["return_percent"] is not None else None,
                        "Quote timestamp": format_quote_timestamp(quote.timestamp, quote.timestamp_is_exact) if quote else "Unavailable",
                        "Timestamp precision": "Exact" if quote and quote.timestamp_is_exact else "Session date" if quote else "Unavailable",
                        "Source": quote.data_source if quote else "Unavailable", "Status": row["status"]})
    table = pd.DataFrame(records)
    st.dataframe(table, hide_index=True, width="stretch")
    st.subheader(f"Allocation by invested cost · {selected}", anchor=False)
    allocation = table.groupby(["Market", "Symbol"], sort=True)["Invested"].sum()
    allocation.index = [f"{market} · {symbol}" for market, symbol in allocation.index]
    allocation = (allocation / allocation.sum() * 100).rename("Allocation (%)")
    st.bar_chart(allocation, color="#5EE0B5", width="stretch")
    st.caption("Allocation uses purchase cost within the selected currency, including lots with unavailable quotes. Estimates exclude fees, taxes, dividends, and corporate-action adjustments. Adjust shares and cost manually after splits.")
    # Export only entered lots, never licensed market quotes.
    backup = pd.DataFrame([{"market": holding.market, "symbol": holding.symbol, "shares": str(holding.shares),
                            "purchase_price": str(holding.purchase_price), "purchase_date": holding.purchase_date,
                            "currency": holding.currency} for holding in holdings])
    st.download_button("Export holdings CSV", backup.to_csv(index=False).encode("utf-8"), "portfolio_holdings.csv", "text/csv")
    with st.expander("Remove a purchase lot"):
        selected_id = st.selectbox("Purchase lot", [holding.id for holding in holdings],
                                   format_func=lambda key: next(f"{h.symbol} · {h.shares} shares · {h.purchase_date} · {h.currency}" for h in holdings if h.id == key))
        if st.button("Remove holding"):
            st.session_state["portfolio"] = [holding for holding in holdings if holding.id != selected_id]
            st.rerun()
note("Tracking and calculation only", "This is not a brokerage or trading system. Holdings and estimates are session-only. A delayed quote is an estimate, and no order can be placed here.")
footer()
