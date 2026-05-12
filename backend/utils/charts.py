"""
SVG chart generation utilities.
Extracted from server.py L90-244.

Generates inline SVG charts for PDF reports:
- Revenue/profit trend bar charts
- Daily sales line graphs
"""


def generate_trend_bars(trend_data):
    """Generate SVG bars for 3-month revenue/profit trend chart."""
    if not trend_data:
        return ""

    # Find max value for scaling
    max_val = max(
        [max(t.get('revenue', 0), t.get('profit', 0)) for t in trend_data]
    ) if trend_data else 1
    if max_val == 0:
        max_val = 1

    svg_parts = []
    bar_width = 30
    gap = 90
    start_x = 80

    for i, t in enumerate(trend_data):
        x = start_x + i * gap

        # Revenue bar (blue)
        rev_height = (t.get('revenue', 0) / max_val) * 120
        rev_y = 170 - rev_height
        svg_parts.append(
            f'<rect x="{x}" y="{rev_y}" width="{bar_width}" '
            f'height="{rev_height}" fill="#667eea" rx="2"/>'
        )

        # Profit bar (green)
        profit_height = (t.get('profit', 0) / max_val) * 120
        profit_y = 170 - profit_height
        svg_parts.append(
            f'<rect x="{x + bar_width + 5}" y="{profit_y}" '
            f'width="{bar_width}" height="{profit_height}" fill="#28a745" rx="2"/>'
        )

        # Month label
        month_label = t.get('month_name', '').split()[0][:3]
        svg_parts.append(
            f'<text x="{x + bar_width}" y="185" font-size="10" '
            f'text-anchor="middle" fill="#333">{month_label}</text>'
        )

    return '\n'.join(svg_parts)


def generate_daily_sales_line_graph(daily_data):
    """Generate SVG line graph for daily sales trend."""
    if not daily_data or len(daily_data) == 0:
        return ""

    sorted_data = sorted(daily_data, key=lambda x: x['day'])

    chart_width = 600
    chart_height = 250
    padding_left = 70
    padding_right = 30
    padding_top = 30
    padding_bottom = 50

    graph_width = chart_width - padding_left - padding_right
    graph_height = chart_height - padding_top - padding_bottom

    max_sales = max([d['sales'] for d in sorted_data]) if sorted_data else 1
    if max_sales == 0:
        max_sales = 1

    min_day = min([d['day'] for d in sorted_data])
    max_day = max([d['day'] for d in sorted_data])
    day_range = max(max_day - min_day, 1)

    # Generate path points
    points = []
    for d in sorted_data:
        x = padding_left + ((d['day'] - min_day) / day_range) * graph_width
        y = padding_top + graph_height - (d['sales'] / max_sales) * graph_height
        points.append(f"{x},{y}")

    path_d = "M " + " L ".join(points)

    # Generate dots
    dots = []
    for d in sorted_data:
        x = padding_left + ((d['day'] - min_day) / day_range) * graph_width
        y = padding_top + graph_height - (d['sales'] / max_sales) * graph_height
        dots.append(
            f'<circle cx="{x}" cy="{y}" r="4" fill="#667eea" '
            f'stroke="white" stroke-width="1"/>'
        )

    # Grid lines and labels
    grid_lines = []
    y_labels = []

    for i in range(5):
        y = padding_top + (i * graph_height / 4)
        value = max_sales * (1 - i / 4)
        grid_lines.append(
            f'<line x1="{padding_left}" y1="{y}" '
            f'x2="{chart_width - padding_right}" y2="{y}" '
            f'stroke="#e5e5e5" stroke-width="1"/>'
        )

        if value >= 100000:
            label = f"₹{value/100000:.1f}L"
        elif value >= 1000:
            label = f"₹{value/1000:.0f}K"
        else:
            label = f"₹{value:.0f}"
        y_labels.append(
            f'<text x="{padding_left - 5}" y="{y + 4}" font-size="10" '
            f'text-anchor="end" fill="#666">{label}</text>'
        )

    # X-axis labels
    x_labels = []
    for day in range(min_day, max_day + 1, 5):
        if day <= max_day:
            x = padding_left + ((day - min_day) / day_range) * graph_width
            x_labels.append(
                f'<text x="{x}" y="{chart_height - 20}" font-size="10" '
                f'text-anchor="middle" fill="#666">Day {day}</text>'
            )

    if max_day % 5 != 0:
        x = padding_left + graph_width
        x_labels.append(
            f'<text x="{x}" y="{chart_height - 20}" font-size="10" '
            f'text-anchor="middle" fill="#666">Day {max_day}</text>'
        )

    svg = f'''
    <svg viewBox="0 0 {chart_width} {chart_height}" style="width: 100%; max-width: 700px; height: auto; margin: 0 auto; display: block;">
        <rect width="{chart_width}" height="{chart_height}" fill="#fafafa" rx="8"/>
        {''.join(grid_lines)}
        <line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{padding_top + graph_height}" stroke="#ccc" stroke-width="2"/>
        <line x1="{padding_left}" y1="{padding_top + graph_height}" x2="{chart_width - padding_right}" y2="{padding_top + graph_height}" stroke="#ccc" stroke-width="2"/>
        {''.join(y_labels)}
        {''.join(x_labels)}
        <text x="{chart_width / 2}" y="{chart_height - 5}" font-size="11" text-anchor="middle" fill="#333">Day of Month</text>
        <text x="15" y="{chart_height / 2}" font-size="11" text-anchor="middle" fill="#333" transform="rotate(-90, 15, {chart_height / 2})">Sales (₹)</text>
        <path d="{path_d} L {padding_left + graph_width},{padding_top + graph_height} L {padding_left},{padding_top + graph_height} Z" fill="url(#gradient)" opacity="0.3"/>
        <path d="{path_d}" fill="none" stroke="#667eea" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        {''.join(dots)}
        <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea;stop-opacity:0.6"/>
                <stop offset="100%" style="stop-color:#667eea;stop-opacity:0.1"/>
            </linearGradient>
        </defs>
    </svg>
    '''

    return svg
