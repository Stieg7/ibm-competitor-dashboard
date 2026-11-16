"""Yahoo Finance data layer: IBM vs. four competitors over three windows."""
import logging
from datetime import timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# SAP is the NYSE-listed ADR, so every ticker is quoted in USD.
TICKERS = {
    "IBM": "IBM",
    "MSFT": "Microsoft",
    "ORCL": "Oracle",
    "SAP": "SAP",
    "CRM": "Salesforce",
}
WEEK_DAYS = 7
QUARTER_DAYS = 91


def fetch() -> pd.DataFrame:
    """Daily adjusted prices for all tickers covering the last quarter."""
    data = yf.download(
        list(TICKERS),
        period="3mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
        timeout=20,
    )
    if data.empty:
        raise RuntimeError("Yahoo Finance returned no data")
    return data


def pct_change(series: pd.Series) -> float | None:
    """Percent change from first to last value, or None if under 2 points."""
    series = series.dropna()
    if len(series) < 2:
        return None
    return round((float(series.iloc[-1]) / float(series.iloc[0]) - 1) * 100, 2)


def _window(px: pd.Series, start: pd.Timestamp) -> pd.Series:
    """Prices from the last close on/before `start` through the end."""
    before = px[px.index <= start]
    anchor = before.index[-1] if len(before) else px.index[0]
    return px.loc[anchor:]


def summarize(data: pd.DataFrame) -> tuple[list[dict], pd.Timestamp]:
    """One row per ticker: last price and % change for day, 7 days, quarter.

    Day: last close vs. prior close. Week/quarter: baseline is the close on
    or just before the window start, so the full window is measured.
    """
    close = data["Close"]
    last_date = close.dropna(how="all").index[-1]
    week_start = last_date - timedelta(days=WEEK_DAYS)
    quarter_start = last_date - timedelta(days=QUARTER_DAYS)

    rows = []
    for ticker, name in TICKERS.items():
        row = {"ticker": ticker, "company": name,
               "last": None, "day": None, "week": None, "quarter": None}
        px = close[ticker].dropna() if ticker in close.columns else pd.Series(dtype=float)
        if not px.empty:
            row["last"] = round(float(px.iloc[-1]), 2)
            row["day"] = pct_change(px.iloc[-2:])
            row["week"] = pct_change(_window(px, week_start))
            row["quarter"] = pct_change(_window(px, quarter_start))
        missing = [w for w in ("day", "week", "quarter") if row[w] is None]
        if missing:
            # A gap silently shrinks the dashboard's "rank of N", so surface it.
            logger.warning(
                "Incomplete market data for %s: no value for %s",
                ticker, ", ".join(missing),
                extra={"ticker": ticker, "missing_windows": missing},
            )
        rows.append(row)
    return rows, last_date
