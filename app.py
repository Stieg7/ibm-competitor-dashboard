"""Finance dashboard: IBM vs. Microsoft, Oracle, SAP and Salesforce."""
import logging

from flask import Flask, render_template, request

import market
from charts import bar_chart

logger = logging.getLogger(__name__)

WINDOWS = (
    ("day", "Current day"),
    ("week", "Last 7 days"),
    ("quarter", "Last quarter"),
)
DEFAULT_COMPANY = "IBM"


def pick_company(value: str | None) -> str:
    """Allowlist the requested ticker; anything unknown falls back to IBM."""
    value = (value or "").strip().upper()
    return value if value in market.TICKERS else DEFAULT_COMPANY


def create_app(fetch=market.fetch) -> Flask:
    """App factory; `fetch` is injectable so tests never hit the network."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        try:
            rows, last_date = market.summarize(fetch())
        except Exception:
            logger.error("Market data retrieval failed", exc_info=True)
            return render_template("index.html", error=True), 502
        charts = [(label, bar_chart(rows, key, label)) for key, label in WINDOWS]
        selected = pick_company(request.args.get("company"))
        selected_row = next(r for r in rows if r["ticker"] == selected)
        company_title = f"{selected_row['company']} across windows"
        company_chart = bar_chart(
            [{"ticker": label, "value": selected_row[key]} for key, label in WINDOWS],
            "value", company_title, width=620,
        )
        ibm = next(r for r in rows if r["ticker"] == "IBM")
        ranked = sorted((r for r in rows if r["quarter"] is not None),
                        key=lambda r: r["quarter"], reverse=True)
        ibm_rank = next((i for i, r in enumerate(ranked, 1) if r["ticker"] == "IBM"), None)
        return render_template(
            "index.html", error=False, rows=rows, charts=charts,
            last_date=f"{last_date:%Y-%m-%d}", ibm=ibm,
            ibm_rank=ibm_rank, total=len(ranked),
            tickers=market.TICKERS, selected=selected,
            selected_name=selected_row["company"], company_chart=company_chart,
        )

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="127.0.0.1", port=5000)
