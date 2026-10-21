"""Pakistan workspace; empty states remain explicit until a licensed adapter exists."""

import streamlit as st

from src.charts import candlestick_chart, price_chart, volume_chart
from src.comparison_ui import render_comparison
from src.market_data import get_history, get_psx_index, get_quote, provider_for, search_psx
from src.ui import company_heading, date_controls, footer, note, page_header, quote_caption, render_chart
from src.utils import compact_number, csv_bytes, format_price, format_quote_timestamp, validate_ticker
from src.watchlist import add_symbol
from src.watchlist_ui import render_watchlist

page_header("PAKISTAN STOCK EXCHANGE", "A dedicated view of Pakistan’s market.", "Research Pakistani companies in PKR, compare price history, and keep a separate watchlist. Market prices require an authorized data connection.")
status = provider_for("psx").status()
if not status.available:
    st.info(status.message)
st.caption(f"Data source: {status.name}")
overview, stocks, comparison, watchlist, access = st.tabs(["KSE-100", "Stock research", "Compare companies", "Pakistan watchlist", "Data access"])

with overview:
    st.subheader("KSE-100 index overview", anchor=False)
    index = get_psx_index()
    if index.error:
        columns = st.columns(2)
        columns[0].metric("Index level · points", "—", border=True)
        columns[1].metric("Daily change", "—", border=True)
        st.caption("Index values and quote timestamp are unavailable until licensed index coverage is connected.")
    else:
        data = index.data
        columns = st.columns(2)
        columns[0].metric("Index level · points", f"{data.level:,.2f}", border=True)
        columns[1].metric("Daily change", f"{data.change_percent:+.2f}%" if data.change_percent is not None else "—", border=True)
        when = format_quote_timestamp(data.timestamp, data.timestamp_is_exact)
        st.caption(f"{data.data_source} · {when}")
    st.caption("An index level is measured in points, rather than Pakistani rupees.")

with stocks:
    with st.form("psx_lookup"):
        query = st.text_input("Search Pakistani companies", placeholder="Company name or PSX symbol", max_chars=100, key="psx_query")
        searched = st.form_submit_button("Search Pakistan stocks", type="primary")
    if searched:
        with st.spinner("Searching the licensed company directory…"):
            result = search_psx(query)
        st.session_state["psx_search_result"] = result
    result = st.session_state.get("psx_search_result")
    if result:
        if result.error:
            st.warning(result.error)
        elif not result.data:
            st.info("No matching companies were returned by the provider.")
        else:
            security = st.selectbox("Search results", result.data, format_func=lambda item: f"{item.symbol} · {item.name}")
            if st.button("Open company"):
                st.session_state["psx_selected_symbol"] = security.symbol
                st.rerun()
    with st.form("psx_symbol_form"):
        symbol_input = st.text_input("PSX symbol", value=st.session_state["psx_selected_symbol"], key="psx_symbol", max_chars=32)
        opened = st.form_submit_button("Load PSX symbol")
    if opened:
        try:
            st.session_state["psx_selected_symbol"] = validate_ticker(symbol_input)
        except ValueError as exc:
            st.error(str(exc))
    symbol = st.session_state["psx_selected_symbol"]
    start, end = date_controls("psx_stock")
    if st.button("Add to Pakistan watchlist", disabled=symbol in st.session_state["psx_watchlist"]):
        try:
            st.session_state["psx_watchlist"] = add_symbol(st.session_state["psx_watchlist"], symbol)
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
    if not status.available:
        note("Research controls are ready", "Search results, PKR quotes, daily changes, volume, and price charts will use the licensed provider. Saved symbols remain unverified while the data connection is unavailable.")
    else:
        with st.spinner(f"Loading {symbol} from the PSX provider…"):
            quote_result = get_quote(symbol, "psx")
            history = get_history(symbol, start, end, "psx")
        if quote_result.error:
            st.warning(quote_result.error)
        elif quote_result.data.currency != "PKR":
            st.error("The provider did not confirm PKR denomination; this quote cannot be displayed as a Pakistan equity price.")
        else:
            quote = quote_result.data
            company_heading(symbol, quote.company_name, "PKR", quote.exchange)
            quote_caption(quote)
            columns = st.columns(3)
            columns[0].metric("Latest available price", format_price(quote.price, "PKR"), border=True)
            columns[1].metric("Daily change", f"{quote.change_percent:+.2f}%" if quote.change_percent is not None else "—", border=True)
            columns[2].metric("Daily volume", compact_number(quote.volume), border=True)
        if history.error:
            st.warning(history.error)
        elif not quote_result.error and quote_result.data.currency == "PKR":
            data = history.data
            style = st.segmented_control("Pakistan chart style", ["Line", "Candlestick"], default="Line", key="psx_chart_style")
            if style == "Candlestick":
                candles = data.dropna(subset=["Open", "High", "Low", "Close"])
                if candles.empty:
                    st.info("Complete candle prices are unavailable for this range.")
                else:
                    render_chart(candlestick_chart(candles, "PKR"), "psx_candles")
            else:
                adjusted = data["Adj Close"].notna().any()
                render_chart(price_chart(data, "PKR", adjusted=adjusted), "psx_price")
                st.caption("Adjusted daily closes" if adjusted else "Unadjusted daily closes; adjusted prices have not been supplied.")
            if data["Volume"].notna().any():
                render_chart(volume_chart(data), "psx_volume")
            if status.allow_exports:
                st.download_button("Download Pakistan history", csv_bytes(data), f"PSX_{symbol}_{start}_{end}.csv", "text/csv")

with comparison:
    if status.available:
        render_comparison("psx", allow_exports=status.allow_exports)
    else:
        st.subheader("Compare Pakistani companies", anchor=False)
        with st.form("psx_comparison_preview"):
            st.text_input("PSX symbols (2–10)", value="OGDC, HBL", help="Symbol examples only; no market data is preloaded.")
            st.form_submit_button("Compare Pakistan stocks", disabled=True)
        st.info("Comparisons require licensed historical prices. Adjusted percentage returns will remain unavailable if the provider does not supply adjusted history.")

with watchlist:
    render_watchlist("psx")

with access:
    note("What is needed to connect data", "Obtain PSX public-display rights and a vendor agreement covering quotes, KSE-100, historical data, storage, derived calculations, and any permitted downloads. Then implement and test the documented provider adapter. An API key alone does not activate this workspace.")
    st.markdown("[PSX data services and licensing](https://www.psx.com.pk/psx/product-and-services/data-services-vending) · [Capital Stake API documentation](https://www.capitalstake.com/docs/)")
    st.write("Credentials must stay in Streamlit Cloud secrets or an ignored local secrets file. No credentials are requested in public browser controls. This release contains no PSX scraping, undocumented endpoints, or guessed Yahoo ticker mappings.")
footer()
