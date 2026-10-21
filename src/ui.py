"""Shared Streamlit controls and styling; CSS targets only our own markup."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html import escape

import streamlit as st

from src.data_provider import Quote
from src.utils import compact_number, currency_label, format_price, format_quote_timestamp, validate_dates, validate_ticker
from src.watchlist import add_symbol

PLOT_CONFIG = {"displaylogo": False, "scrollZoom": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
PERIODS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1096, "5Y": 1826}


def today() -> date:
    return datetime.now(timezone.utc).date()


def initialize_session() -> None:
    st.session_state.setdefault("selected_symbol", "AAPL")
    st.session_state.setdefault("watchlist", [])
    st.session_state.setdefault("psx_watchlist", [])
    st.session_state.setdefault("psx_selected_symbol", "OGDC")
    st.session_state.setdefault("portfolio", [])


def apply_styles() -> None:
    st.html("""
    <style>
    .atlas-brand {display:flex; align-items:center; gap:11px; margin:6px 0 28px;}
    .atlas-mark {display:grid; place-items:center; height:38px; width:38px; border-radius:11px;
       color:#08171a; background:#5ee0b5; font-weight:900; font-size:24px;}
    .atlas-brand-name {color:#f1f6ff; font-size:18px; font-weight:750; letter-spacing:-.5px;}
    .atlas-brand-sub {color:#8396b3; font-size:10px; letter-spacing:2.2px; text-transform:uppercase;}
    .atlas-eyebrow {color:#5ee0b5; font-size:11px; letter-spacing:2.2px; font-weight:700; margin:5px 0 10px;}
    .atlas-title {font-size:clamp(30px,4vw,46px); font-weight:720; letter-spacing:-1.8px;
       line-height:1.15; color:#f1f6ff; margin:0 0 12px;}
    .atlas-subtitle {color:#9aacc6; font-size:15px; line-height:1.65; max-width:740px; margin:0 0 24px;}
    .atlas-company {display:flex; flex-wrap:wrap; align-items:center; gap:12px; margin:12px 0 14px;}
    .atlas-company-name {font-size:27px; font-weight:650; color:#e8eef7; letter-spacing:-.7px;}
    .atlas-chip {border:1px solid #2a3b54; background:#142238; color:#b7c8e3;
       border-radius:7px; padding:5px 9px; font-size:12px; font-weight:600;}
    .atlas-note {padding:18px 20px; border:1px solid #25354c; border-radius:13px;
       color:#9badc8; background:linear-gradient(120deg,#111e31,#0d1829); line-height:1.7; font-size:13px;}
    .atlas-note strong {color:#e8eef7;}
    .atlas-footer {color:#7e91ad; font-size:11px; line-height:1.7; padding:16px 0 0;
       margin-top:30px; border-top:1px solid #203049;}
    @media (max-width:640px) {
       .atlas-title {letter-spacing:-1px;} .atlas-company-name {font-size:23px;}
       .atlas-subtitle {font-size:14px;} .atlas-note {padding:14px;}
    }
    </style>
    """)


def page_header(eyebrow: str, title: str, description: str) -> None:
    st.html(f'<div class="atlas-eyebrow">{escape(eyebrow)}</div><h1 class="atlas-title">{escape(title)}</h1><p class="atlas-subtitle">{escape(description)}</p>')


def note(title: str, description: str) -> None:
    st.html(f'<div class="atlas-note"><strong>{escape(title)}</strong><br>{escape(description)}</div>')


def footer() -> None:
    st.html('<div class="atlas-footer">MARKET ATLAS &nbsp; / &nbsp; Research with perspective.<br>Data sources are shown with quotes · Data may be delayed or unavailable. For education only; not investment advice.</div>')


def ticker_search(key: str) -> str:
    with st.form(f"{key}_search"):
        left, right = st.columns([4, 1], vertical_alignment="bottom")
        with left:
            raw = st.text_input("Stock symbol", value=st.session_state["selected_symbol"], placeholder="AAPL, MSFT, BRK-B…", key=f"{key}_ticker", max_chars=32)
        with right:
            submitted = st.form_submit_button("Search", type="primary", width="stretch", icon=":material/search:")
    if submitted:
        try:
            st.session_state["selected_symbol"] = validate_ticker(raw)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
    return st.session_state["selected_symbol"]


def period_control(key: str, default: str = "1Y") -> tuple[date, date]:
    period = st.segmented_control("Time horizon", list(PERIODS), default=default, key=key, selection_mode="single")
    end = today()
    return end - timedelta(days=PERIODS[period or default]), end


def date_controls(key: str) -> tuple[date, date]:
    left, right = st.columns(2)
    end_limit = today()
    with left:
        start = st.date_input("Start date", value=end_limit - timedelta(days=365), min_value=end_limit - timedelta(days=3650), max_value=end_limit, key=f"{key}_start")
    with right:
        end = st.date_input("End date (inclusive)", value=end_limit, min_value=end_limit - timedelta(days=3650), max_value=end_limit, key=f"{key}_end")
    try:
        validate_dates(start, end, end_limit)
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()
    return start, end


def company_heading(symbol: str, name: str, currency: str | None, exchange: str | None = None) -> None:
    chips = [symbol, currency_label(currency)]
    if exchange:
        chips.append(exchange)
    st.html('<div class="atlas-company"><span class="atlas-company-name">' + escape(name) + '</span>' + ''.join(f'<span class="atlas-chip">{escape(str(chip))}</span>' for chip in chips) + '</div>')


def quote_caption(quote: Quote) -> None:
    when = format_quote_timestamp(quote.timestamp, quote.timestamp_is_exact)
    st.caption(f"{quote.data_source} · {quote.source_label} · {when}")


def quote_metrics(quote: Quote, market_cap: float | None = None) -> None:
    columns = st.columns(4)
    delta = f"{quote.change:+,.2f} ({quote.change_percent:+.2f}%)" if quote.change is not None and quote.change_percent is not None else None
    with columns[0]:
        st.metric("Latest available price", format_price(quote.price, quote.currency), delta=delta, border=True, help="Change from the previous available daily close; the current session may be incomplete.")
    with columns[1]:
        st.metric("Previous daily close", format_price(quote.previous_close, quote.currency), border=True)
    with columns[2]:
        st.metric("Latest daily volume", compact_number(quote.volume), border=True, help="Shares in the latest daily bar; partial while the session is in progress.")
    with columns[3]:
        st.metric("Market capitalization", compact_number(market_cap), border=True, help=f"Company value in {currency_label(quote.currency)} when provided. Company details are cached for one hour.")


def add_to_watchlist_button(symbol: str, key: str) -> None:
    present = symbol in st.session_state["watchlist"]
    if st.button("In your watchlist" if present else "Add to watchlist", icon=":material/bookmark:", disabled=present, key=key):
        try:
            st.session_state["watchlist"] = add_symbol(st.session_state["watchlist"], symbol)
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))


def render_chart(figure, key: str) -> None:
    st.plotly_chart(figure, width="stretch", config=PLOT_CONFIG, key=key)
