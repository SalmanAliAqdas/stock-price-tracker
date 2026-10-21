"""Historical price research and beginner-friendly indicator explanations."""

from datetime import timedelta

import streamlit as st

from src.charts import candlestick_chart, price_chart, rsi_chart, volume_chart
from src.indicators import historical_extremes, percentage_return, rsi, sma, volume_summary
from src.market_data import get_history, get_quote
from src.ui import company_heading, date_controls, footer, page_header, render_chart, ticker_search, today
from src.utils import compact_number, csv_bytes, currency_label, format_number, format_price

page_header("RESEARCH DESK", "Understand the bigger picture.", "Explore daily price action and the indicators behind it. Choose a period, look for context, and take the data with you.")
symbol = ticker_search("analysis")
start, end = date_controls("analysis")
with st.spinner(f"Loading historical prices for {symbol}…"):
    # Warm indicators before the selected range, without displaying extra dates.
    fetch_start = max(start - timedelta(days=180), today() - timedelta(days=3653))
    history = get_history(symbol, fetch_start, end)
    quote_result = get_quote(symbol)
if history.error:
    st.warning(history.error)
    st.stop()
full = history.data.copy()
full["SMA 20"] = sma(full["Adj Close"], 20)
full["SMA 50"] = sma(full["Adj Close"], 50)
full["RSI 14"] = rsi(full["Adj Close"])
data = full.loc[(full.index.date >= start) & (full.index.date <= end)].copy()
if data.empty:
    st.info("There are no trading sessions in this range. Choose a wider date range.")
    st.stop()
quote = quote_result.data
currency = currency_label(quote.currency if quote else None)
company_heading(symbol, quote.company_name if quote else symbol, quote.currency if quote else None)
if quote_result.error:
    st.caption("Quote metadata is unavailable; prices are displayed without an assumed currency.")
high, low = historical_extremes(data)
prices = data["Adj Close"].dropna()
period_return = percentage_return(prices.iloc[0], prices.iloc[-1]) if len(prices) >= 2 else None
volume = volume_summary(data["Volume"])
columns = st.columns(4)
columns[0].metric("Period adjusted return", f"{period_return:+.2f}%" if period_return is not None else "—", border=True)
columns[1].metric("Period high · raw", format_price(high, quote.currency if quote else None), border=True)
columns[2].metric("Period low · raw", format_price(low, quote.currency if quote else None), border=True)
columns[3].metric("Average daily volume", compact_number(volume["average"]), border=True)
st.caption(f"{len(data):,} trading sessions · {data.index[0]:%d %b %Y} – {data.index[-1]:%d %b %Y} · Latest daily bar may be incomplete.")
if len(prices) >= 2:
    st.caption(f"Adjusted return uses available closes from {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y}.")

with st.container(border=True):
    st.subheader("Historical prices", anchor=False)
    chart_type = st.segmented_control("Chart style", ["Line", "Candlestick"], default="Line", key="analysis_chart")
    if chart_type == "Candlestick":
        ohlc = data.dropna(subset=["Open", "High", "Low", "Close"])
        if ohlc.empty:
            st.info("Complete OHLC values are unavailable for candlesticks in this range.")
        else:
            render_chart(candlestick_chart(ohlc, currency), "analysis_candles")
        st.caption("Candles show unadjusted daily open, high, low, and close. Green closes at or above the open; red closes below it.")
    else:
        averages = st.toggle("Show SMA 20 & SMA 50", value=True)
        if prices.empty:
            st.info("Adjusted closes are unavailable. Try the candlestick chart for unadjusted daily prices.")
        else:
            render_chart(price_chart(data, currency, averages=averages), "analysis_line")
        st.caption("Line and moving averages use split- and dividend-adjusted closes. SMA windows count trading observations, including earlier history used for warmup.")
        if averages and (data["SMA 20"].isna().all() or data["SMA 50"].isna().all()):
            st.info("Some moving averages need more history. SMA 20 needs 20 valid closes; SMA 50 needs 50.")

with st.container(border=True):
    st.subheader("Trading volume", anchor=False)
    if data["Volume"].notna().any():
        render_chart(volume_chart(data), "analysis_volume")
        st.caption(f"Total shares traded: {compact_number(volume['total'])}. Volume measures participation, rather than direction.")
    else:
        st.info("Trading volume is unavailable for this range.")

with st.container(border=True):
    st.subheader("Relative Strength Index", anchor=False)
    if data["RSI 14"].notna().any():
        render_chart(rsi_chart(data["RSI 14"]), "analysis_rsi")
        st.caption(f"Latest available RSI 14: {format_number(data['RSI 14'].dropna().iloc[-1])}. Wilder smoothing on adjusted daily closes.")
    else:
        st.info("RSI 14 needs at least 15 consecutive valid closes. Try a longer date range.")
    st.caption("RSI compares recent gains and losses on a 0–100 scale. Levels 30 and 70 are reference points, not guaranteed buy or sell signals.")

with st.expander("Explore and download the data", expanded=False):
    st.caption("OHLC columns are unadjusted; Adj Close and all indicators are adjusted. Dates are exchange-local trading session dates. Missing fields remain blank.")
    st.dataframe(data, width="stretch")
    st.download_button("Download historical CSV", csv_bytes(data), f"{symbol}_{start}_{end}.csv", "text/csv", icon=":material/download:")
footer()
