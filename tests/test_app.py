"""Streamlit's own app harness verifies page rendering and widget behavior."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def start_app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def test_dashboard_loads_and_searches(fake_provider):
    app = start_app()
    assert not app.exception
    assert any(metric.label == "Latest available price" for metric in app.metric)
    app.text_input(key="dashboard_ticker").set_value("MSFT")
    next(button for button in app.button if button.label == "Search").click().run()
    assert not app.exception
    assert app.session_state["selected_symbol"] == "MSFT"
    app.button(key="dashboard_watchlist").click().run()
    assert app.session_state["watchlist"] == ["MSFT"]


def test_invalid_ticker_and_empty_quote_show_messages(fake_provider):
    app = start_app()
    app.text_input(key="dashboard_ticker").set_value("../invalid")
    next(button for button in app.button if button.label == "Search").click().run()
    assert app.error
    assert not app.exception
    app.text_input(key="dashboard_ticker").set_value("BAD")
    next(button for button in app.button if button.label == "Search").click().run()
    assert app.warning
    assert not app.exception


@pytest.mark.parametrize("page,chart_count", [("pages/1_Stock_Analysis.py", 3), ("pages/2_Stock_Comparison.py", 1), ("pages/3_Watchlist.py", 0), ("pages/4_About.py", 0)])
def test_every_page_renders_without_errors(fake_provider, page, chart_count):
    app = start_app().switch_page(page).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == chart_count


def test_analysis_can_switch_to_candles(fake_provider):
    app = start_app().switch_page("pages/1_Stock_Analysis.py").run()
    app.segmented_control(key="analysis_chart").set_value("Candlestick").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3


def test_watchlist_add_remove_and_session_isolation(fake_provider):
    app = start_app().switch_page("pages/3_Watchlist.py").run()
    app.text_input[0].set_value("NVDA")
    next(button for button in app.button if button.label == "Add stock").click().run()
    assert not app.exception
    assert app.session_state["watchlist"] == ["NVDA"]
    other = start_app()
    assert other.session_state["watchlist"] == []
    app.button(key="remove_NVDA").click().run()
    assert app.session_state["watchlist"] == []
    assert not app.exception


def test_comparison_keeps_valid_stocks_when_one_symbol_is_missing(fake_provider):
    app = start_app().switch_page("pages/2_Stock_Comparison.py").run()
    app.text_input[0].set_value("AAPL, BAD, VOD.L")
    next(button for button in app.button if button.label == "Compare stocks").click().run()
    assert not app.exception
    assert app.warning
    assert len(app.get("plotly_chart")) == 1
    table = app.dataframe[0].value
    assert table["Symbol"].tolist() == ["AAPL", "VOD.L"]
    assert table["Currency"].tolist() == ["USD", "GBP"]
