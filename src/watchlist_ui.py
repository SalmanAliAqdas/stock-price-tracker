"""Paginated session watchlists: quotes are requested only for visible entries."""

import math

import streamlit as st

from src.market_data import get_quote
from src.ui import note, quote_caption
from src.utils import format_price, validate_ticker
from src.watchlist import MAX_SYMBOLS, add_symbol, export_watchlist, filter_symbols, import_watchlist, remove_symbol

PAGE_SIZE = 10


def render_watchlist(market: str = "yahoo") -> None:
    state_key = "watchlist" if market == "yahoo" else "psx_watchlist"
    prefix = "" if market == "yahoo" else "psx_"
    with st.form(f"{prefix}watchlist_add", clear_on_submit=True):
        left, right = st.columns([4, 1], vertical_alignment="bottom")
        with left:
            raw = st.text_input("Add a ticker", placeholder="For example, AAPL" if market == "yahoo" else "For example, OGDC", max_chars=32, key=f"{prefix}watchlist_new")
        with right:
            submitted = st.form_submit_button("Add stock", type="primary", width="stretch", icon=":material/add:")
    if submitted:
        try:
            st.session_state[state_key] = add_symbol(st.session_state[state_key], validate_ticker(raw))
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
    symbols = st.session_state[state_key]
    left, right = st.columns([2, 1])
    query = left.text_input("Search watchlist symbols", key=f"{prefix}watchlist_search", placeholder="Filter your saved tickers…")
    sorting = right.selectbox("Sort symbols", ["A–Z", "Z–A"], key=f"{prefix}watchlist_sort")
    filtered = filter_symbols(symbols, query, descending=sorting == "Z–A")
    st.caption(f"{len(symbols)} / {MAX_SYMBOLS} stocks · {len(filtered)} matching · Quotes cached for two minutes; only ten visible entries are requested.")
    if not symbols:
        note("Make room for your next idea", "Add a ticker above or import a watchlist backup. Symbol validation checks format; listing availability is reported with each quote.")
    elif not filtered:
        st.info("No saved symbols match this search.")
    else:
        pages = list(range(1, math.ceil(len(filtered) / PAGE_SIZE) + 1))
        page = st.selectbox("Watchlist page", pages, key=f"{prefix}watchlist_page")
        visible = filtered[(page - 1) * PAGE_SIZE:page * PAGE_SIZE]
        with st.spinner("Checking visible watchlist entries…"):
            results = {symbol: get_quote(symbol, market) for symbol in visible}
        for symbol in visible:
            result = results[symbol]
            with st.container(border=True):
                info, price, action = st.columns([2.5, 2, 1], vertical_alignment="center")
                with info:
                    st.write(f"**{result.data.company_name if result.data else symbol}** · {symbol}")
                    if result.error:
                        st.caption(result.error)
                    else:
                        quote_caption(result.data)
                with price:
                    if result.data:
                        quote = result.data
                        delta = f"{quote.change_percent:+.2f}%" if quote.change_percent is not None else None
                        st.metric("Latest available", format_price(quote.price, quote.currency), delta=delta)
                    else:
                        st.caption("Price unavailable · symbol not verified")
                with action:
                    if st.button("Remove", key=f"{prefix}remove_{symbol}", icon=":material/close:"):
                        st.session_state[state_key] = remove_symbol(symbols, symbol)
                        st.rerun()
    st.divider()
    backup, restore = st.columns(2, gap="large")
    with backup:
        st.subheader("Take your list with you", anchor=False)
        st.write("Backups contain your saved symbols and market, without market prices.")
        for file_format in ("json", "csv"):
            st.download_button(f"Export {file_format.upper()}", export_watchlist(symbols, market, file_format),
                               f"watchlist_{market}.{file_format}", "application/json" if file_format == "json" else "text/csv", key=f"{prefix}export_{file_format}")
    with restore:
        st.subheader("Restore a watchlist", anchor=False)
        uploaded = st.file_uploader("Choose a JSON or CSV backup", type=["json", "csv"], key=f"{prefix}watchlist_upload", help="Up to 64 KB and 100 unique symbols. Import replaces this market's current list.")
        if st.button("Import and replace list", disabled=uploaded is None, key=f"{prefix}watchlist_import"):
            try:
                file_format = "csv" if uploaded.name.lower().endswith(".csv") else "json"
                st.session_state[state_key] = import_watchlist(uploaded.getvalue(), market, file_format)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.caption("Watchlists are private to this Streamlit session. Reloads, disconnects, and cloud restarts can reset them. Export a backup to keep them. International and Pakistan lists are separate; neither uses a shared database.")
