"""Server-rendered SVG bar charts (no external scripts or CDNs)."""
from markupsafe import Markup, escape

GREEN = "#1a7f37"
RED = "#cf222e"


def bar_chart(rows: list[dict], key: str, title: str,
              width: int = 420, height: int = 220) -> Markup:
    """Bar chart of `row[key]` (% change) per ticker; None values are skipped."""
    items = [(r["ticker"], r[key]) for r in rows if r[key] is not None]
    if not items:
        return Markup('<p class="muted">No data available.</p>')

    top, bottom, side = 24, 28, 10
    plot_h = height - top - bottom
    mid = top + plot_h / 2
    scale = (plot_h / 2 - 14) / (max(abs(v) for _, v in items) or 1.0)
    slot = (width - 2 * side) / len(items)
    bar_w = slot * 0.6

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}" xmlns="http://www.w3.org/2000/svg">',
        f'<line x1="{side}" x2="{width - side}" y1="{mid:.1f}" y2="{mid:.1f}" '
        'stroke="#8c959f" stroke-width="1"/>',
    ]
    for i, (ticker, value) in enumerate(items):
        x = side + i * slot + (slot - bar_w) / 2
        h = abs(value) * scale
        y = mid - h if value >= 0 else mid
        label_y = y - 4 if value >= 0 else y + h + 12
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="{GREEN if value >= 0 else RED}"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'font-size="12" fill="#1f2328">{value:+.2f}%</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 8}" text-anchor="middle" '
            f'font-size="12" font-weight="600" fill="#1f2328">{escape(ticker)}</text>'
        )
    parts.append("</svg>")
    return Markup("".join(parts))
