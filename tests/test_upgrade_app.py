from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src import market_data
from src.psx_provider import IndexOverview, ProviderStatus, Security

ROOT = Path(__file__).resolve().parents[1]


def start_app():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def test_ten_company_chart_has_ten_distinct_series(fake_provider):
    app = start_app().switch_page("pages/2_Stock_Comparison.py").run()
    app.text_input(key="comparison_tickers").set_value("AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,AMD,INTC,ORCL")
    next(button for button in app.button if button.label == "Compare stocks").click().run()
    assert not app.exception
    traces = json.loads(app.get("plotly_chart")[0].proto.spec)["data"]
    assert len(traces) == 10
    assert len({trace["line"]["color"] for trace in traces}) == 10
    assert len(app.dataframe[0].value) == 10
    app.text_input(key="comparison_tickers").set_value("A,B,C,D,E,F,G,H,I,J,K")
    next(button for button in app.button if button.label == "Compare stocks").click().run()
    assert app.error
    assert not app.exception


def test_large_watchlist_requests_only_visible_entries_and_supports_search(fake_provider):
    app = start_app()
    before = fake_provider.quote_calls
    app.session_state["watchlist"] = [f"STK{i:02}" for i in range(100)]
    app.switch_page("pages/3_Watchlist.py").run()
    assert not app.exception
    assert fake_provider.quote_calls - before == 10
    app.selectbox(key="watchlist_page").set_value(2).run()
    assert fake_provider.quote_calls - before == 20
    app.text_input(key="watchlist_search").set_value("STK99").run()
    assert not app.exception
    assert len(app.metric) == 1
    app.button(key="remove_STK99").click().run()
    assert len(app.session_state["watchlist"]) == 99


def test_psx_page_never_routes_to_yahoo_and_lists_are_separate(fake_provider):
    app = start_app()
    calls = fake_provider.quote_calls
    app.session_state["watchlist"] = ["MSFT"]
    app.switch_page("pages/5_Pakistan_Stock_Exchange.py").run()
    assert not app.exception
    assert all(metric.value == "—" for metric in app.metric)
    app.text_input(key="psx_watchlist_new").set_value("OGDC")
    next(button for button in app.button if button.label == "Add stock").click().run()
    assert not app.exception
    assert app.session_state["psx_watchlist"] == ["OGDC"]
    assert app.session_state["watchlist"] == ["MSFT"]
    assert fake_provider.quote_calls == calls


def test_psx_interface_works_against_a_test_only_provider(fake_provider, monkeypatch):
    class TestPSXProvider:
        def status(self):
            return ProviderStatus(name="Test-only licensed feed", available=True)

        def quote(self, symbol):
            return replace(fake_provider.quote(symbol), currency="PKR", exchange="PSX", data_source="Test-only licensed feed")

        def history(self, *args):
            return fake_provider.history(*args)

        def search(self, query):
            return [Security("OGDC", "Test-only company")]

        def index_overview(self):
            return IndexOverview("KSE-100", 123, 1, 0.5, pd.Timestamp("2026-10-20", tz="UTC"), True, "Test-only licensed feed")

    monkeypatch.setattr(market_data, "get_psx_provider", TestPSXProvider)
    app = start_app().switch_page("pages/5_Pakistan_Stock_Exchange.py").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    assert set(app.dataframe[0].value["Currency"]) == {"PKR"}
    assert not any(button.label.startswith("Download") for button in app.get("download_button"))
    app.text_input(key="psx_query").set_value("company")
    next(button for button in app.button if button.label == "Search Pakistan stocks").click().run()
    assert not app.exception
    assert app.session_state["psx_search_result"].data[0].symbol == "OGDC"


def test_portfolio_add_update_remove_and_session_isolation(fake_provider):
    app = start_app().switch_page("pages/6_Portfolio.py").run()
    assert not app.exception
    app.text_input(key="portfolio_symbol").set_value("AAPL")
    app.number_input(key="portfolio_shares").set_value(10.0)
    app.number_input(key="portfolio_price").set_value(100.0)
    app.date_input(key="portfolio_date").set_value(date(2025, 1, 1))
    next(button for button in app.button if button.label == "Add holding").click().run()
    assert not app.exception
    assert len(app.session_state["portfolio"]) == 1
    assert next(metric for metric in app.metric if metric.label == "Total invested").value == "1,000.00 USD"
    assert next(metric for metric in app.metric if metric.label == "Current estimated value").value == "— USD"
    next(button for button in app.button if button.label.startswith("Update estimates")).click().run()
    assert not app.exception
    assert next(metric for metric in app.metric if metric.label == "Current estimated value").value == "1,500.00 USD"
    assert start_app().session_state["portfolio"] == []
    next(button for button in app.button if button.label == "Remove holding").click().run()
    assert app.session_state["portfolio"] == []
