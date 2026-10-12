"""
chart_generator.py — High-resolution server-side chart rendering for PDF reports.
Uses matplotlib in headless Agg mode to generate base64-encoded PNG data URLs.
Supports both 'dark' (editorial neon) and 'light' (clean light-ink print) themes.
"""

import io
import base64
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


def _get_theme_palette(theme: str = 'dark') -> Dict[str, Any]:
    if theme == 'light':
        return {
            'bg': '#ffffff',
            'card_bg': '#f8fafc',
            'text_main': '#0f172a',
            'text_muted': '#475569',
            'grid': '#cbd5e1',
            'grid_alpha': 0.5,
            'spine': '#94a3b8',
            'c1_line': '#2563eb',     # Strong Blue
            'c1_ma': '#d97706',       # Dark Amber
            'c2_line': '#059669',     # Deep Emerald
            'c2_ma': '#dc2626',       # Crimson Red
            'overlay_a': '#2563eb',
            'overlay_b': '#059669',
            'baseline': '#64748b'
        }
    else:  # dark editorial
        return {
            'bg': '#0f172a',          # Deep slate
            'card_bg': '#1e293b',
            'text_main': '#f8fafc',
            'text_muted': '#94a3b8',
            'grid': '#334155',
            'grid_alpha': 0.4,
            'spine': '#334155',
            'c1_line': '#38bdf8',     # Vibrant Sky Blue
            'c1_ma': '#fbbf24',       # Glowing Amber
            'c2_line': '#34d399',     # Neon Emerald
            'c2_ma': '#f472b6',       # Hot Pink
            'overlay_a': '#818cf8',   # Indigo
            'overlay_b': '#34d399',   # Emerald
            'baseline': '#64748b'
        }


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', dpi=180)
    plt.close(fig)
    b64_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64_data}"


def render_single_company_ma_chart(
    company_name: str,
    ticker: str,
    monthly_series: List[Any],
    color_line: str,
    color_ma: str,
    theme: str = 'dark'
) -> str:
    """
    Renders Month-End Adjusted Close vs 3-Month Moving Average.
    """
    pal = _get_theme_palette(theme)
    fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=180)
    fig.patch.set_facecolor(pal['bg'])
    ax.set_facecolor(pal['bg'])

    labels = [p.month_label for p in monthly_series]
    closes = [p.adj_close for p in monthly_series]
    ma3 = [p.ma_3m if p.ma_3m is not None else np.nan for p in monthly_series]

    x = np.arange(len(labels))

    # Plot lines
    ax.plot(x, closes, label='Month-End Adj Close', color=color_line, linewidth=2.0, marker='o', markersize=3.5, alpha=0.95)
    ax.plot(x, ma3, label='3-Month Moving Avg (MA-3M)', color=color_ma, linewidth=2.0, linestyle='--', marker='s', markersize=3, alpha=0.9)

    # Style spines and ticks
    for spine in ax.spines.values():
        spine.set_color(pal['spine'])
        spine.set_linewidth(0.8)

    ax.grid(True, linestyle=':', alpha=pal['grid_alpha'], color=pal['grid'])
    ax.tick_params(colors=pal['text_muted'], labelsize=7.5)

    # Thin down x-axis ticks so they don't crowd
    step = max(1, len(labels) // 7)
    tick_indices = list(range(0, len(labels), step))
    if (len(labels) - 1) not in tick_indices:
        tick_indices.append(len(labels) - 1)

    ax.set_xticks(tick_indices)
    ax.set_xticklabels([labels[i] for i in tick_indices], rotation=30, ha='right', color=pal['text_muted'], fontsize=7)

    ax.set_title(f"{company_name} ({ticker}) — Close vs 3M-MA", fontsize=9.5, fontweight='bold', color=pal['text_main'], pad=8)
    ax.set_ylabel("Price (INR ₹)", fontsize=7.5, color=pal['text_muted'], labelpad=4)

    leg = ax.legend(loc='upper left', fontsize=7.2, facecolor=pal['card_bg'], edgecolor=pal['spine'], labelcolor=pal['text_main'], framealpha=0.9)
    leg.get_frame().set_linewidth(0.8)

    return _fig_to_base64(fig)


def render_overlay_chart(
    name_a: str,
    ticker_a: str,
    name_b: str,
    ticker_b: str,
    overlay_series: List[Any],
    theme: str = 'dark'
) -> str:
    """
    Renders Head-to-Head Comparative Overlay Chart rebased to 100 on start date.
    """
    pal = _get_theme_palette(theme)
    fig, ax = plt.subplots(figsize=(11.5, 3.6), dpi=180)
    fig.patch.set_facecolor(pal['bg'])
    ax.set_facecolor(pal['bg'])

    dates = [p.date for p in overlay_series]
    reb_a = [p.company_a_rebased if hasattr(p, 'company_a_rebased') else getattr(p, 'company1_rebased', 100.0) for p in overlay_series]
    reb_b = [p.company_b_rebased if hasattr(p, 'company_b_rebased') else getattr(p, 'company2_rebased', 100.0) for p in overlay_series]

    x = np.arange(len(dates))

    # Baseline 100 line
    ax.axhline(100.0, color=pal['baseline'], linestyle=':', linewidth=1.2, label='Baseline (100.0)', alpha=0.7)

    # Plot both series
    ax.plot(x, reb_a, label=f"{ticker_a} ({name_a[:18]})", color=pal['overlay_a'], linewidth=2.2, alpha=0.95)
    ax.plot(x, reb_b, label=f"{ticker_b} ({name_b[:18]})", color=pal['overlay_b'], linewidth=2.2, alpha=0.95)

    for spine in ax.spines.values():
        spine.set_color(pal['spine'])
        spine.set_linewidth(0.8)

    ax.grid(True, linestyle=':', alpha=pal['grid_alpha'], color=pal['grid'])
    ax.tick_params(colors=pal['text_muted'], labelsize=7.5)

    # Thin down x-axis ticks
    step = max(1, len(dates) // 10)
    tick_indices = list(range(0, len(dates), step))
    if (len(dates) - 1) not in tick_indices:
        tick_indices.append(len(dates) - 1)

    ax.set_xticks(tick_indices)
    ax.set_xticklabels([dates[i] for i in tick_indices], rotation=25, ha='right', color=pal['text_muted'], fontsize=7)

    ax.set_title(f"Head-to-Head Comparative Growth Overlay (Rebased to 100.0)", fontsize=10, fontweight='bold', color=pal['text_main'], pad=8)
    ax.set_ylabel("Rebased Index (Start = 100)", fontsize=7.5, color=pal['text_muted'], labelpad=4)

    leg = ax.legend(loc='upper left', fontsize=7.5, facecolor=pal['card_bg'], edgecolor=pal['spine'], labelcolor=pal['text_main'], framealpha=0.9)
    leg.get_frame().set_linewidth(0.8)

    return _fig_to_base64(fig)


def generate_all_report_charts(
    company_a_name: str,
    ticker_a: str,
    monthly_a: List[Any],
    company_b_name: str,
    ticker_b: str,
    monthly_b: List[Any],
    overlay_series: List[Any],
    theme: str = 'dark'
) -> Dict[str, str]:
    """
    Renders all 3 required charts for the school project PDF.
    Returns: { 'chart_a': data_url, 'chart_b': data_url, 'chart_overlay': data_url }
    """
    pal = _get_theme_palette(theme)
    chart_a = render_single_company_ma_chart(
        company_name=company_a_name,
        ticker=ticker_a,
        monthly_series=monthly_a,
        color_line=pal['c1_line'],
        color_ma=pal['c1_ma'],
        theme=theme
    )
    chart_b = render_single_company_ma_chart(
        company_name=company_b_name,
        ticker=ticker_b,
        monthly_series=monthly_b,
        color_line=pal['c2_line'],
        color_ma=pal['c2_ma'],
        theme=theme
    )
    chart_overlay = render_overlay_chart(
        name_a=company_a_name,
        ticker_a=ticker_a,
        name_b=company_b_name,
        ticker_b=ticker_b,
        overlay_series=overlay_series,
        theme=theme
    )

    return {
        'chart_a': chart_a,
        'chart_b': chart_b,
        'chart_overlay': chart_overlay
    }
