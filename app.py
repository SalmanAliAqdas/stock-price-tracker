"""Streamlit entry point: python -m streamlit run app.py."""

import streamlit as st

from src.dashboard import render_dashboard
from src.ui import apply_styles, initialize_session, note

st.set_page_config(page_title="Market Atlas | Stock Price Tracker", page_icon=":material/monitoring:", layout="wide", initial_sidebar_state="expanded")
initialize_session()
apply_styles()

with st.sidebar:
    st.html('<div class="atlas-brand"><div class="atlas-mark">↗</div><div><div class="atlas-brand-name">Market Atlas</div><div class="atlas-brand-sub">Stock intelligence</div></div></div>')

page = st.navigation([
    st.Page(render_dashboard, title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("pages/1_Stock_Analysis.py", title="Stock Analysis", icon=":material/candlestick_chart:"),
    st.Page("pages/2_Stock_Comparison.py", title="Stock Comparison", icon=":material/compare_arrows:"),
    st.Page("pages/3_Watchlist.py", title="Watchlist", icon=":material/bookmarks:"),
    st.Page("pages/4_About.py", title="About & Help", icon=":material/help_outline:"),
], position="sidebar")

with st.sidebar:
    st.divider()
    st.caption("YOUR WORKSPACE")
    st.write(f"Following **{st.session_state['selected_symbol']}**")
    st.caption(f"{len(st.session_state['watchlist'])} stocks in your session watchlist")
    st.write("")
    note("Built for a thoughtful view", "Daily history, clear context, and simple research tools. No API key required.")
    st.caption("Quotes may be delayed. Watchlists last for this session; export a copy to keep them.")

page.run()
