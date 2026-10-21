"""Private session watchlists with explicit portable JSON backups."""

import streamlit as st

from src.market_data import get_quote
from src.ui import footer, note, page_header, quote_caption
from src.utils import format_price, validate_ticker
from src.watchlist import MAX_SYMBOLS, add_symbol, export_watchlist, import_watchlist, remove_symbol

page_header("YOUR SHORTLIST", "Keep your companies close.", "Build a focused watchlist and check the latest available prices. Your list belongs to this session; export a copy to bring it back later.")
with st.form("watchlist_add", clear_on_submit=True):
    left, right = st.columns([4, 1], vertical_alignment="bottom")
    with left:
        raw = st.text_input("Add a ticker", placeholder="For example, AAPL", max_chars=20)
    with right:
        submitted = st.form_submit_button("Add stock", type="primary", width="stretch", icon=":material/add:")
if submitted:
    try:
        symbol = validate_ticker(raw)
        updated = add_symbol(st.session_state["watchlist"], symbol)
        with st.spinner(f"Checking {symbol}…"):
            result = get_quote(symbol)
        if result.error:
            st.warning(result.error)
        else:
            st.session_state["watchlist"] = updated
            st.rerun()
    except ValueError as exc:
        st.warning(str(exc))

symbols = st.session_state["watchlist"]
st.caption(f"{len(symbols)} / {MAX_SYMBOLS} stocks · Quotes cached for up to two minutes.")
if not symbols:
    note("Make room for your next idea", "Add a ticker above to start following a company. You can also add a stock directly from its dashboard.")
else:
    with st.spinner("Checking your watchlist…"):
        results = {symbol: get_quote(symbol) for symbol in symbols}
    for symbol in symbols:
        result = results[symbol]
        with st.container(border=True):
            info, price, action = st.columns([2.5, 2, 1], vertical_alignment="center")
            with info:
                if result.error:
                    st.write(f"**{symbol}**")
                    st.caption(result.error)
                else:
                    quote = result.data
                    st.write(f"**{quote.company_name}** · {symbol}")
                    quote_caption(quote)
            with price:
                if not result.error:
                    quote = result.data
                    delta = f"{quote.change_percent:+.2f}%" if quote.change_percent is not None else None
                    st.metric("Latest available", format_price(quote.price, quote.currency), delta=delta)
            with action:
                if st.button("Remove", key=f"remove_{symbol}", icon=":material/close:"):
                    st.session_state["watchlist"] = remove_symbol(symbols, symbol)
                    st.rerun()

st.divider()
backup, restore = st.columns(2, gap="large")
with backup:
    st.subheader("Take your list with you", anchor=False)
    st.write("Download a small JSON backup and import it in a future session.")
    st.download_button("Export watchlist", export_watchlist(symbols), "watchlist.json", "application/json", icon=":material/download:")
with restore:
    st.subheader("Restore a watchlist", anchor=False)
    uploaded = st.file_uploader("Choose an exported JSON file", type=["json"], help="Up to 16 KB and 12 symbols. Import replaces this session’s current list.")
    if st.button("Import and replace list", disabled=uploaded is None, icon=":material/upload:"):
        try:
            st.session_state["watchlist"] = import_watchlist(uploaded.getvalue())
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
st.caption("Watchlists are stored only in Streamlit session state. Reloading, disconnecting, or a cloud restart can reset them. Market data may be shared in the public cache; personal lists are never placed in that cache.")
footer()
