"""Shared comparison view for international and licensed Pakistan data."""

import pandas as pd
import streamlit as st

from src.charts import comparison_chart
from src.indicators import align_prices, normalize_returns
from src.market_data import get_histories, get_quote
from src.ui import date_controls, note, render_chart
from src.utils import csv_bytes, currency_label, parse_tickers


def render_comparison(market: str = "yahoo", allow_exports: bool = True) -> None:
    prefix = "comparison" if market == "yahoo" else "psx_comparison"
    default = "AAPL, MSFT, NVDA" if market == "yahoo" else "OGDC, HBL"
    with st.form(f"{prefix}_symbols"):
        raw = st.text_input("Ticker symbols", value=st.session_state.get(f"{prefix}_input", default),
                            help="Enter 2–10 different stock symbols, separated by commas.", key=f"{prefix}_tickers")
        compare = st.form_submit_button("Compare stocks", type="primary", icon=":material/compare_arrows:")
    if compare:
        st.session_state[f"{prefix}_input"] = raw
    try:
        symbols = parse_tickers(st.session_state.get(f"{prefix}_input", default))
    except ValueError as exc:
        st.error(str(exc))
        return
    start, end = date_controls(prefix)
    prices, quotes = {}, {}
    with st.spinner("Aligning adjusted price history…"):
        histories = get_histories(tuple(symbols), start, end, market)
        for symbol in symbols:
            result = histories[symbol]
            if result.error:
                st.warning(f"{symbol}: {result.error}")
                continue
            series = result.data["Adj Close"].dropna()
            if len(series) < 2:
                st.warning(f"{symbol}: At least two adjusted closes are needed. This symbol was excluded.")
                continue
            prices[symbol] = series
            quote = get_quote(symbol, market)
            quotes[symbol] = quote.data
            if quote.error:
                st.caption(f"{symbol}: company metadata is unavailable; no currency has been assumed.")
    if len(prices) < 2:
        st.info("At least two symbols with adjusted historical prices are needed. Try another symbol or a wider date range.")
        return
    aligned = align_prices(prices)
    normalized = normalize_returns(prices)
    if len(aligned) < 2:
        st.info("These stocks have fewer than two common trading dates. Choose a wider range or a different group.")
        return
    with st.container(border=True):
        st.subheader("A common starting line", anchor=False)
        st.caption(f"{aligned.index[0]:%d %b %Y} – {aligned.index[-1]:%d %b %Y} · {len(aligned):,} common trading sessions")
        render_chart(comparison_chart(normalized), f"{prefix}_chart")
        st.caption("Only dates with a valid adjusted close for every included stock are shown. No missing prices are filled or invented. Click a legend entry to hide a line; double-click to isolate it.")
    # At most three columns keeps ten-company summaries readable on narrow screens.
    names = list(aligned.columns)
    for offset in range(0, len(names), 3):
        columns = st.columns(min(3, len(names) - offset))
        for column, symbol in zip(columns, names[offset:offset + 3]):
            column.metric(symbol, f"{normalized[symbol].iloc[-1]:+.2f}%", border=True)
    rows = []
    for symbol in names:
        quote = quotes[symbol]
        rows.append({"Symbol": symbol, "Company": quote.company_name if quote else symbol,
                     "Currency": currency_label(quote.currency if quote else None),
                     "Start adjusted price": float(aligned[symbol].iloc[0]), "End adjusted price": float(aligned[symbol].iloc[-1]),
                     "Return (%)": float(normalized[symbol].iloc[-1]), "Start session": aligned.index[0].date(),
                     "End session": aligned.index[-1].date(), "Source": quote.data_source if quote else "Metadata unavailable"})
    st.subheader("The comparison, in numbers", anchor=False)
    sorting = st.selectbox("Sort comparison", ["Return: highest first", "Return: lowest first", "Symbol"], key=f"{prefix}_sort")
    table = pd.DataFrame(rows).sort_values("Symbol" if sorting == "Symbol" else "Return (%)", ascending=sorting != "Return: highest first", kind="stable")
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "Start adjusted price": st.column_config.NumberColumn(format="%.2f"),
        "End adjusted price": st.column_config.NumberColumn(format="%.2f"),
        "Return (%)": st.column_config.NumberColumn(format="%+.2f%%"),
    })
    note("Comparable returns, clearly labeled currencies", "Prices retain each stock’s own quotation currency. Percentage returns compare local-currency performance without exchange-rate conversion, fees, or taxes. Adding more symbols can shorten the shared date range.")
    if allow_exports:
        st.download_button("Download comparison returns", csv_bytes(normalized), f"{prefix}_returns_{start}_{end}.csv", "text/csv", icon=":material/download:")
    else:
        st.caption("Market-data downloads are disabled until the provider grants export rights.")
