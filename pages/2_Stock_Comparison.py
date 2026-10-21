"""Compare aligned adjusted percentage performance, never mixed raw prices."""

import pandas as pd
import streamlit as st

from src.charts import comparison_chart
from src.indicators import align_prices, normalize_returns
from src.market_data import get_history, get_quote
from src.ui import date_controls, footer, note, page_header, render_chart
from src.utils import csv_bytes, currency_label, parse_tickers

page_header("SIDE BY SIDE", "Put performance in perspective.", "Compare up to four companies from the same starting point. Every line begins at 0%, using adjusted prices on shared trading dates.")
with st.form("comparison_symbols"):
    raw = st.text_input("Ticker symbols", value=st.session_state.get("comparison_input", "AAPL, MSFT, NVDA"), help="Enter 2–4 Yahoo Finance stock symbols, separated by commas.")
    compare = st.form_submit_button("Compare stocks", type="primary", icon=":material/compare_arrows:")
if compare:
    st.session_state["comparison_input"] = raw
try:
    symbols = parse_tickers(st.session_state.get("comparison_input", "AAPL, MSFT, NVDA"))
except ValueError as exc:
    st.error(str(exc))
    st.stop()
start, end = date_controls("comparison")
prices, quotes = {}, {}
with st.spinner("Aligning adjusted price history…"):
    for symbol in symbols:
        result = get_history(symbol, start, end)
        if result.error:
            st.warning(f"{symbol}: {result.error}")
            continue
        series = result.data["Adj Close"].dropna()
        if len(series) < 2:
            st.warning(f"{symbol}: At least two adjusted closes are needed. This symbol was excluded.")
            continue
        prices[symbol] = series
        quote = get_quote(symbol)
        quotes[symbol] = quote.data
        if quote.error:
            st.caption(f"{symbol}: company metadata is unavailable; no currency has been assumed.")
if len(prices) < 2:
    st.info("At least two symbols with adjusted historical prices are needed. Try another symbol or a wider date range.")
    st.stop()
aligned = align_prices(prices)
normalized = normalize_returns(prices)
if len(aligned) < 2:
    st.info("These stocks have fewer than two common trading dates. Choose a wider range or a different group.")
    st.stop()
with st.container(border=True):
    st.subheader("A common starting line", anchor=False)
    st.caption(f"{aligned.index[0]:%d %b %Y} – {aligned.index[-1]:%d %b %Y} · {len(aligned):,} common trading sessions")
    render_chart(comparison_chart(normalized), "comparison_chart")
    st.caption("Only dates with a valid adjusted close for every included stock are shown. No missing prices are filled or invented.")

columns = st.columns(len(aligned.columns))
for column, symbol in zip(columns, aligned.columns):
    with column:
        value = float(normalized[symbol].iloc[-1])
        st.metric(symbol, f"{value:+.2f}%", delta=f"{value:+.2f}%", border=True, help="Adjusted local-currency return from the common starting date, before fees and tax.")

rows = []
for symbol in aligned.columns:
    quote = quotes[symbol]
    rows.append({
        "Symbol": symbol,
        "Company": quote.company_name if quote else symbol,
        "Currency": currency_label(quote.currency if quote else None),
        "Start adjusted price": float(aligned[symbol].iloc[0]),
        "End adjusted price": float(aligned[symbol].iloc[-1]),
        "Return (%)": float(normalized[symbol].iloc[-1]),
        "Start session": aligned.index[0].date(),
        "End session": aligned.index[-1].date(),
    })
st.subheader("The comparison, in numbers", anchor=False)
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
    "Start adjusted price": st.column_config.NumberColumn(format="%.2f"),
    "End adjusted price": st.column_config.NumberColumn(format="%.2f"),
    "Return (%)": st.column_config.NumberColumn(format="%+.2f%%"),
})
note("Comparable returns, clearly labeled currencies", "Start and end prices are in each stock’s own quotation currency. Percentage returns compare local-currency performance; they do not include exchange-rate movements into an investor’s home currency. No currency conversion is performed.")
st.download_button("Download comparison returns", csv_bytes(normalized), f"comparison_returns_{start}_{end}.csv", "text/csv", icon=":material/download:")
footer()
