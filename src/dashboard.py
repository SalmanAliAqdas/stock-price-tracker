"""The primary stock overview."""

import streamlit as st

from src.charts import price_chart
from src.indicators import percentage_return
from src.market_data import get_history, get_profile, get_quote
from src.ui import add_to_watchlist_button, company_heading, footer, note, page_header, period_control, quote_caption, quote_metrics, render_chart, ticker_search
from src.utils import currency_label, format_number, format_price


def render_dashboard() -> None:
    page_header("YOUR MARKET, IN FOCUS", "A clearer view of the market.", "Follow the companies that matter to you. Explore price history, understand the momentum, and put performance in perspective.")
    symbol = ticker_search("dashboard")
    with st.spinner(f"Finding the latest available data for {symbol}…"):
        result = get_quote(symbol)
    if result.error:
        st.warning(result.error)
        note("A good place to start", "Try AAPL for Apple, MSFT for Microsoft, or NVDA for NVIDIA. Yahoo Finance uses BRK-B for Berkshire Hathaway Class B.")
        footer()
        return
    quote = result.data
    with st.spinner("Loading company details…"):
        profile_result = get_profile(symbol)
    profile = profile_result.data or {}
    name = profile.get("longName") or quote.company_name
    company_heading(symbol, name, quote.currency, quote.exchange)
    quote_caption(quote)
    quote_metrics(quote, profile.get("marketCap"))
    st.write("")
    main, side = st.columns([3.2, 1.2], gap="large")
    with main, st.container(border=True):
        st.subheader("Price performance", anchor=False)
        start, end = period_control("dashboard_period")
        with st.spinner("Loading daily price history…"):
            history = get_history(symbol, start, end)
        if history.error:
            st.warning(history.error)
        else:
            data = history.data
            adjusted = data["Adj Close"].dropna()
            if adjusted.empty:
                st.info("Adjusted prices are unavailable for this symbol. Use Stock Analysis to inspect its daily OHLC candles.")
            else:
                change = percentage_return(adjusted.iloc[0], adjusted.iloc[-1]) if len(adjusted) >= 2 else None
                if change is not None:
                    st.caption(f"{change:+.2f}% adjusted return · {adjusted.index[0]:%d %b %Y} – {adjusted.index[-1]:%d %b %Y}")
                render_chart(price_chart(data, currency_label(quote.currency)), "dashboard_price")
                st.caption("Daily adjusted closes account for splits and dividends. The latest daily bar may still be in progress; this is not a live price chart.")
    with side:
        with st.container(border=True):
            st.subheader("Company snapshot", anchor=False)
            for label, value in (("Sector", profile.get("sector")), ("Industry", profile.get("industry")), ("Exchange", profile.get("fullExchangeName") or quote.exchange), ("Country", profile.get("country"))):
                st.caption(label.upper())
                st.write(str(value or "Unavailable"))
            st.divider()
            add_to_watchlist_button(symbol, "dashboard_watchlist")
        if profile_result.error:
            st.caption(profile_result.error)
        note("Go beyond the headline", "Open Stock Analysis for candlesticks, moving averages, RSI, and a downloadable price history.")
    summary = profile.get("longBusinessSummary")
    if summary:
        with st.expander(f"About {name}"):
            st.write(summary)
            st.caption(f"52-week high: {format_price(profile.get('fiftyTwoWeekHigh'), quote.currency)} · 52-week low: {format_price(profile.get('fiftyTwoWeekLow'), quote.currency)} · Trailing P/E: {format_number(profile.get('trailingPE'))}")
    footer()
