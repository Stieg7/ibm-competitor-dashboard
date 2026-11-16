# IBM vs. Competitors: Finance Dashboard

A small Flask app that tracks IBM and four competitors (Microsoft, Oracle, SAP and Salesforce) using Yahoo Finance data over three windows: the current day, the last 7 days and the last quarter.

- A bar chart per window, plus a summary table with IBM highlighted and IBM's quarterly rank.
- A company selector (`/?company=MSFT`) that shows one company's change across all three windows. The default is IBM. Unknown values fall back to IBM and are never echoed into the page.
- Charts are server-rendered SVG, so the page needs no JavaScript and loads nothing from external sites.
- If Yahoo Finance is unavailable, the page shows a generic message and the details go to the server log only.
- A warning is logged when a ticker comes back with missing data.

## Run it

Requires Python 3.15 (the version used in CI).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Then open http://127.0.0.1:5000. The server binds to `127.0.0.1` only.

On macOS or Linux, use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`.

## Test it

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The 25 tests use synthetic prices, so they need no network access. GitHub Actions runs them on every pull request and every push to `main`.

## Layout

| File | Purpose |
|---|---|
| `market.py` | Fetches Yahoo Finance data and computes % change per window |
| `charts.py` | Server-rendered SVG bar charts |
| `app.py` | Flask app and company selection |
| `templates/index.html` | Page template |
| `test_dashboard.py` | Tests |

## Notes

- Prices are adjusted closes in USD. SAP is the NYSE-listed ADR, so every ticker is quoted in USD.
- Yahoo Finance data is unofficial and is provided through the `yfinance` library. It is for learning and demonstration, not for investment decisions.

## License

MIT. See [LICENSE](LICENSE).
