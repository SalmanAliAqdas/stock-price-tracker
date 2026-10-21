"""Product help and transparent data conventions."""

import streamlit as st

from src.ui import footer, note, page_header

page_header("A LITTLE CONTEXT GOES A LONG WAY", "Research with perspective.", "Market Atlas makes stock research approachable, with clear charts, useful comparisons, and honest context about the data behind them.")
left, right = st.columns([1.5, 1], gap="large")
with left:
    st.subheader("Start with a company", anchor=False)
    st.write("Enter a stock’s Yahoo Finance ticker on the Dashboard or Stock Analysis page. AAPL is Apple, MSFT is Microsoft, and BRK-B is Berkshire Hathaway Class B. US stocks are the primary focus. Some exchange suffixes, such as .L, are accepted when Yahoo supports them.")
    st.subheader("Read the chart", anchor=False)
    st.write("Hover for a date and value, drag to zoom, and double-click to reset. The line chart shows daily adjusted closes. Daily history is not a streaming price feed, and today’s daily bar may still be changing while its market is open.")
    with st.expander("What does a candlestick show?", expanded=True):
        st.write("Each candle represents one trading session. The body spans the opening and closing prices; the wick reaches the high and low. Green means the close is at or above the open. Red means the close is below it. Candles use unadjusted OHLC prices, so their values can differ from the adjusted line chart.")
    with st.expander("What is a moving average?"):
        st.write("A simple moving average smooths day-to-day price changes by averaging recent closes. SMA 20 averages 20 trading observations; SMA 50 averages 50. Earlier history warms up the calculation before your selected period where available. A new listing or missing data can leave an indicator unavailable.")
    with st.expander("What is RSI?"):
        st.write("The 14-period Relative Strength Index compares average recent gains with average losses on a 0–100 scale using Wilder’s smoothing. It needs 15 consecutive valid closes to start. Reference levels of 30 and 70 can help describe momentum, but neither predicts a guaranteed reversal. Completely flat prices are shown as 50.")
    with st.expander("What does volume tell me?"):
        st.write("Trading volume is the number of shares traded during a session. Higher volume indicates more activity; it does not by itself imply that a price will rise or fall. The latest daily volume can be partial while trading is in progress.")
    with st.expander("How are returns and comparisons calculated?"):
        st.write("Return is (ending price / starting price − 1) × 100. Line charts, moving averages, RSI, and return comparisons use Yahoo’s Adj Close, which accounts for splits and dividends. Candles, period highs and lows, and the latest price use unadjusted prices. If adjusted data is absent, returns remain unavailable rather than silently switching conventions.")
        st.write("Comparison dates are the intersection of valid trading dates for every included symbol. Each line starts at 0% on the same date, with no forward filling. Prices in the table retain each symbol’s currency. Local-currency percentage returns exclude foreign exchange movements into your home currency, fees, taxes, and trading costs.")
    with st.expander("Will my watchlist be saved?"):
        st.write("Your list stays in your current browser session and is not permanently saved. Reloads, disconnects, or cloud restarts can clear it. Export a JSON backup to restore it later. Imports replace the current list and accept up to 12 validated symbols. There are no user accounts or shared watchlist database.")
with right:
    note("A research companion", "Search, analyze, compare, and follow companies in one focused workspace. Designed for learning and exploration, with no paid API key.")
    st.write("")
    with st.container(border=True):
        st.subheader("About the data", anchor=False)
        st.write("Market data is retrieved from Yahoo Finance through the unofficial, open-source yfinance library. This application is not affiliated with Yahoo or any exchange.")
        st.write("Quotes may be delayed, incomplete, or unavailable. Market closures, newly listed stocks, delistings, network problems, and provider rate limits can affect results. No prices are generated to replace missing data.")
        st.write("Exact quote times are shown in UTC when the provider supplies them. If only a daily bar is available, the app shows its exchange-local session date and explicitly marks the exact time as unavailable. A fetch time is never presented as a quote time.")
        st.caption("Cache lifetimes: quotes 2 minutes · daily history 15 minutes · company details 1 hour. Failure responses use the same lifetimes to reduce repeated requests. There is no background polling.")
        st.markdown("[yfinance documentation](https://ranaroussi.github.io/yfinance/) · [Yahoo terms](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html)")
    st.write("")
    note("Financial disclaimer", "For education and general information only. This application does not provide financial advice or recommendations to buy or sell securities. Data accuracy is not guaranteed. Verify prices independently before making financial decisions. Past performance does not guarantee future results.")
footer()
