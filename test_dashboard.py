"""Tests use synthetic prices so they never touch the network."""
import logging

import pandas as pd
import pytest

import market
from app import create_app
from charts import bar_chart


def make_data(days: int = 100) -> pd.DataFrame:
    """Business-day prices: each ticker rises by a fixed step per day."""
    idx = pd.bdate_range(end="2026-11-13", periods=days)
    close = pd.DataFrame(
        {t: [100 + i * step for i in range(days)]
         for t, step in zip(market.TICKERS, (1.0, 0.5, -0.2, 0.0, 2.0))},
        index=idx,
    )
    volume = close * 0 + 1_000
    return pd.concat({"Close": close, "Volume": volume}, axis=1)


def test_pct_change_basic_and_insufficient_data():
    assert market.pct_change(pd.Series([100.0, 110.0])) == 10.0
    assert market.pct_change(pd.Series([100.0])) is None
    assert market.pct_change(pd.Series([100.0, None])) is None


def test_summarize_covers_all_tickers_and_windows():
    rows, last_date = market.summarize(make_data())
    assert [r["ticker"] for r in rows] == ["IBM", "MSFT", "ORCL", "SAP", "CRM"]
    assert last_date == pd.Timestamp("2026-11-13")
    ibm = rows[0]
    # IBM: 100 + i, last i = 99 -> 199; prior close 198.
    assert ibm["last"] == 199.0
    assert ibm["day"] == pytest.approx((199 / 198 - 1) * 100, abs=0.01)
    # 7 days before Fri 2026-11-13 is Fri 2026-11-06, which is index 94 -> 194.
    assert ibm["week"] == pytest.approx((199 / 194 - 1) * 100, abs=0.01)
    # 91 days back is Fri 2026-08-14, the 63rd business day back from the end.
    assert ibm["quarter"] is not None and ibm["quarter"] > ibm["week"]


def test_summarize_flat_and_falling_tickers():
    rows, _ = market.summarize(make_data())
    by = {r["ticker"]: r for r in rows}
    assert by["SAP"]["day"] == 0.0 and by["SAP"]["quarter"] == 0.0
    assert by["ORCL"]["day"] < 0 and by["ORCL"]["quarter"] < 0


def test_summarize_handles_ticker_with_no_data():
    data = make_data()
    data[("Close", "CRM")] = float("nan")
    rows, _ = market.summarize(data)
    crm = next(r for r in rows if r["ticker"] == "CRM")
    assert crm["last"] is None and crm["day"] is None and crm["quarter"] is None


def test_summarize_warns_when_ticker_has_no_data(caplog):
    data = make_data()
    data[("Close", "CRM")] = float("nan")
    with caplog.at_level(logging.WARNING, logger="market"):
        market.summarize(data)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].ticker == "CRM"
    assert warnings[0].missing_windows == ["day", "week", "quarter"]
    assert "CRM" in warnings[0].getMessage()


def test_summarize_does_not_warn_when_data_is_complete(caplog):
    with caplog.at_level(logging.WARNING, logger="market"):
        market.summarize(make_data())
    assert not caplog.records


def test_bar_chart_colours_and_empty_state():
    rows = [{"ticker": "IBM", "day": 2.5}, {"ticker": "ORCL", "day": -1.0}]
    svg = str(bar_chart(rows, "day", "Current day"))
    assert "+2.50%" in svg and "-1.00%" in svg
    assert "#1a7f37" in svg and "#cf222e" in svg
    assert "No data available" in str(bar_chart([{"ticker": "IBM", "day": None}], "day", "x"))


def test_bar_chart_escapes_ticker_text():
    svg = str(bar_chart([{"ticker": "<b>", "day": 1.0}], "day", "t"))
    assert "<b>" not in svg and "&lt;b&gt;" in svg


def test_dashboard_renders_all_companies_and_windows():
    client = create_app(fetch=make_data).test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for name in ("IBM", "Microsoft", "Oracle", "SAP", "Salesforce"):
        assert name in html
    for label in ("Current day", "Last 7 days", "Last quarter"):
        assert label in html
    assert "ranks" in html


def test_dashboard_returns_generic_error_when_yahoo_fails():
    def broken():
        raise RuntimeError("secret internal detail")

    resp = create_app(fetch=broken).test_client().get("/")
    assert resp.status_code == 502
    html = resp.get_data(as_text=True)
    assert "temporarily unavailable" in html
    assert "secret internal detail" not in html and "Traceback" not in html


def _company_section(html: str) -> str:
    start = html.index('id="company-chart"')
    return html[start:html.index("</div>", start)]


def test_company_defaults_to_ibm():
    html = create_app(fetch=make_data).test_client().get("/").get_data(as_text=True)
    assert '<option value="IBM" selected>' in html
    assert "IBM: % change by window" in _company_section(html)


@pytest.mark.parametrize("ticker,name", list(market.TICKERS.items()))
def test_company_selection_for_every_company(ticker, name):
    html = create_app(fetch=make_data).test_client().get(f"/?company={ticker}").get_data(as_text=True)
    assert f'<option value="{ticker}" selected>' in html
    section = _company_section(html)
    assert f"{name}: % change by window" in section
    # One bar per window, labelled with the window names.
    for label in ("Current day", "Last 7 days", "Last quarter"):
        assert label in section


def test_company_selection_is_case_insensitive():
    html = create_app(fetch=make_data).test_client().get("/?company=msft").get_data(as_text=True)
    assert '<option value="MSFT" selected>' in html


@pytest.mark.parametrize("bad", ["", "XYZ", "ibm%20", "<script>alert(1)</script>", "'; DROP TABLE x;--", "A" * 5000])
def test_invalid_company_falls_back_to_ibm_and_is_not_reflected(bad):
    resp = create_app(fetch=make_data).test_client().get("/", query_string={"company": bad})
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '<option value="IBM" selected>' in html
    assert "<script>alert(1)</script>" not in html and "DROP TABLE" not in html


def test_comparison_charts_and_table_unchanged_by_selection():
    client = create_app(fetch=make_data).test_client()
    for ticker in market.TICKERS:
        html = client.get(f"/?company={ticker}").get_data(as_text=True)
        for name in ("IBM", "Microsoft", "Oracle", "SAP", "Salesforce"):
            assert f"<td>{name}</td>" in html
        assert html.count("<svg") == 4  # three comparison charts + the company chart
        assert "ranks" in html


def test_company_chart_uses_no_javascript_or_external_assets():
    html = create_app(fetch=make_data).test_client().get("/?company=SAP").get_data(as_text=True)
    assert "<script" not in html.lower() and "http://" not in html.replace("http://www.w3.org/2000/svg", "")
