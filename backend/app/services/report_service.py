"""
report_service.py — Exhibition-Grade Academic Science Project Report & Export Service.

Implements the complete Senior Secondary School Project Checklist:
1. Cover page: Project title, two companies & tickers, student name & roll number, date generated.
2. Table of assigned companies and stock symbols.
3. Step 1 - Data Extraction: explanation of data source & 2Y range + first 10 rows daily closes.
4. Step 2 - Monthly Summary: monthly closing table aligned across calendar months.
5. Step 3 - Moving Average Calculation: formula explanation in plain words + 3M MA template table.
6. Step 4 - Graphs: server-rendered side-by-side charts + comparative overlay chart.
7. Step 5 - Comparative Analysis: written paragraphs answering stability, growth, and MA trend.
8. Why the Prices Moved: top events per company with explanations and sources.
9. Conclusion: superior investment pick, Buy/Hold/Avoid scorecard, and academic limitations.
10. Appendix: methodology, metric definitions, scoring weights, data sources, disclaimer.

Provides:
- generate_report_html(analysis, student_name, roll_number, theme)
- generate_pdf_report(analysis, student_name, roll_number, theme)
- generate_template_table_csv(analysis)
- generate_google_sheets_csv(analysis)
"""

import io
import csv
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Environment, select_autoescape
from playwright.async_api import async_playwright

from app.models.schemas import AnalysisResponse, CompanyAnalysis
from app.services.chart_generator import generate_all_report_charts
from app.services.comparative_text import (
    generate_deterministic_comparative_text,
    polish_comparative_analysis_with_gemini
)


def generate_template_table_csv(analysis: AnalysisResponse) -> str:
    """
    Exports the project template table as standard CSV.
    Columns: Month-Year, Month-End Date, Comp1 Close, Comp1 3M-MA, Comp2 Close, Comp2 3M-MA
    """
    out = io.StringIO()
    writer = csv.writer(out)

    c1_ticker = analysis.company_a.info.ticker
    c2_ticker = analysis.company_b.info.ticker
    c1_name = analysis.company_a.info.name
    c2_name = analysis.company_b.info.name

    # Header comments
    writer.writerow([f"# StockLens Quantitative Equity Analysis Export"])
    writer.writerow([f"# Generated: {analysis.generated_at}"])
    writer.writerow([f"# Company 1: {c1_name} ({c1_ticker}) | Company 2: {c2_name} ({c2_ticker})"])
    writer.writerow([])

    # Table Header
    writer.writerow([
        "Month-Year",
        f"{c1_ticker} Close (INR)",
        f"{c1_ticker} 3M Moving Average (INR)",
        f"{c2_ticker} Close (INR)",
        f"{c2_ticker} 3M Moving Average (INR)"
    ])

    rows = analysis.project_template_table
    if not rows and hasattr(analysis, 'company_a'):
        # Fallback to monthly series if project_template_table is empty
        m_a = {p.month_year: p for p in analysis.company_a.monthly_series}
        m_b = {p.month_year: p for p in analysis.company_b.monthly_series}
        all_months = sorted(list(set(m_a.keys()).intersection(set(m_b.keys()))))
        for m in all_months:
            pa = m_a[m]
            pb = m_b[m]
            writer.writerow([
                m,
                f"{pa.adj_close:.2f}",
                f"{pa.ma_3m:.2f}" if pa.ma_3m is not None else "",
                f"{pb.adj_close:.2f}",
                f"{pb.ma_3m:.2f}" if pb.ma_3m is not None else ""
            ])
    else:
        for r in rows:
            writer.writerow([
                r.month_year,
                f"{r.company1_close:.2f}",
                f"{r.company1_ma:.2f}" if r.company1_ma is not None else "",
                f"{r.company2_close:.2f}",
                f"{r.company2_ma:.2f}" if r.company2_ma is not None else ""
            ])

    return out.getvalue()


def generate_google_sheets_csv(analysis: AnalysisResponse) -> str:
    """
    Exports CSV specifically structured for Google Sheets demonstration,
    including GOOGLEFINANCE formulas and =AVERAGE(...) 3-month moving average formulas.
    """
    out = io.StringIO()
    writer = csv.writer(out)

    c1_ticker = analysis.company_a.info.ticker
    c2_ticker = analysis.company_b.info.ticker
    c1_name = analysis.company_a.info.name
    c2_name = analysis.company_b.info.name

    writer.writerow(["# StockLens Dual Equity Comparative Analysis - Google Sheets Export"])
    writer.writerow([f"# Target Equities: NSE:{c1_ticker} ({c1_name}) and NSE:{c2_ticker} ({c2_name})"])
    writer.writerow(["# GOOGLEFINANCE history formula uses each row's NSE symbol and month-end date; Google may not cover every NSE ticker."])
    writer.writerow(["# Moving average formulas use the three source close cells above the current row, including the current row."])
    writer.writerow([])

    # Column Headers
    writer.writerow([
        "Month-Year",
        "Month-End Date",
        "Comp1 Symbol",
        f"{c1_ticker} Close (INR)",
        f"{c1_ticker} 3M-MA Formula",
        f"{c1_ticker} GOOGLEFINANCE Close",
        f"{c1_ticker} MA Value",
        "Comp2 Symbol",
        f"{c2_ticker} Close (INR)",
        f"{c2_ticker} 3M-MA Formula",
        f"{c2_ticker} GOOGLEFINANCE Close",
        f"{c2_ticker} MA Value"
    ])

    rows = analysis.project_template_table
    start_row = 7  # Excel/Sheets row number for first data row
    month_dates = {p.month_year: p.date for p in analysis.company_a.monthly_series}

    for i, r in enumerate(rows):
        cur_row = start_row + i
        if i >= 2:
            ma1_formula = f"=AVERAGE(D{cur_row-2}:D{cur_row})"
            ma2_formula = f"=AVERAGE(I{cur_row-2}:I{cur_row})"
        else:
            ma1_formula = '""'
            ma2_formula = '""'
        quote1_formula = f'=IFERROR(INDEX(GOOGLEFINANCE(C{cur_row},"price",B{cur_row}),2,2),"")'
        quote2_formula = f'=IFERROR(INDEX(GOOGLEFINANCE(G{cur_row},"price",B{cur_row}),2,2),"")'

        writer.writerow([
            r.month_year,
            month_dates.get(r.month_year, f"{r.month_year}-01"),
            f"NSE:{c1_ticker.removesuffix('.NS')}",
            f"{r.company1_close:.2f}",
            ma1_formula,
            quote1_formula,
            f"{r.company1_ma:.2f}" if r.company1_ma is not None else "",
            f"NSE:{c2_ticker.removesuffix('.NS')}",
            f"{r.company2_close:.2f}",
            ma2_formula,
            quote2_formula,
            f"{r.company2_ma:.2f}" if r.company2_ma is not None else ""
        ])

    return out.getvalue()


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>StockLens Report: {{ company_a.info.ticker }} vs {{ company_b.info.ticker }}</title>
<style>
  @page {
    size: A4 portrait;
    margin: 14mm 12mm 14mm 12mm;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.45;
    font-size: 8.5pt;
    color: {{ theme.text_main }};
    background-color: {{ theme.bg }};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Page Break Utilities */
  .cover-page {
    height: 94vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    page-break-after: always;
    break-after: page;
    padding: 20px 10px;
  }

  .page-break {
    page-break-before: always;
    break-before: page;
    padding-top: 10px;
  }

  .avoid-break {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  /* Typography */
  h1, h2, h3, h4 {
    font-weight: 800;
    color: {{ theme.text_main }};
    letter-spacing: -0.02em;
  }

  p {
    color: {{ theme.text_body }};
    margin-bottom: 6px;
    font-size: 8.5pt;
  }

  .section-title {
    font-size: 11pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {{ theme.accent_primary }};
    border-bottom: 1.5px solid {{ theme.border }};
    padding-bottom: 4px;
    margin-top: 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .section-subtitle {
    font-size: 7.5pt;
    color: {{ theme.text_muted }};
    font-weight: normal;
    text-transform: none;
    letter-spacing: normal;
  }

  /* Containers & Cards */
  .card {
    background-color: {{ theme.card_bg }};
    border: 1px solid {{ theme.border }};
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 10px;
  }

  .card-highlight {
    background: {{ theme.highlight_bg }};
    border: 1px solid {{ theme.highlight_border }};
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 10px;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7.8pt;
    margin-bottom: 10px;
  }

  th {
    background-color: {{ theme.table_header_bg }};
    color: {{ theme.table_header_text }};
    font-weight: 700;
    text-align: left;
    padding: 5px 7px;
    border: 1px solid {{ theme.border }};
  }

  td {
    padding: 4.5px 7px;
    border: 1px solid {{ theme.border }};
    color: {{ theme.text_body }};
  }

  tr:nth-child(even) td {
    background-color: {{ theme.table_stripe_bg }};
  }

  .num {
    text-align: right;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-variant-numeric: tabular-nums;
  }

  .center {
    text-align: center;
  }

  .tag {
    display: inline-block;
    padding: 1.5px 6px;
    border-radius: 4px;
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
  }

  .tag-buy { background: {{ theme.tag_buy_bg }}; color: {{ theme.tag_buy_text }}; border: 1px solid {{ theme.tag_buy_border }}; }
  .tag-hold { background: {{ theme.tag_hold_bg }}; color: {{ theme.tag_hold_text }}; border: 1px solid {{ theme.tag_hold_border }}; }
  .tag-avoid { background: {{ theme.tag_avoid_bg }}; color: {{ theme.tag_avoid_text }}; border: 1px solid {{ theme.tag_avoid_border }}; }
  .tag-jump { background: {{ theme.tag_jump_bg }}; color: {{ theme.tag_jump_text }}; }
  .tag-drop { background: {{ theme.tag_drop_bg }}; color: {{ theme.tag_drop_text }}; }

  /* Grid Layouts */
  .grid-2 {
    display: flex;
    gap: 10px;
    width: 100%;
  }

  .col-2 {
    flex: 1;
    min-width: 0;
  }

  .grid-3 {
    display: flex;
    gap: 8px;
    width: 100%;
  }

  .col-3 {
    flex: 1;
    min-width: 0;
  }

  .chart-img {
    width: 100%;
    height: auto;
    border-radius: 4px;
    border: 1px solid {{ theme.border }};
    display: block;
    margin-top: 4px;
  }

  /* Academic Formula Callout */
  .formula-box {
    background: {{ theme.formula_bg }};
    border-left: 3px solid {{ theme.accent_primary }};
    padding: 7px 10px;
    font-size: 8pt;
    margin-bottom: 8px;
    border-radius: 0 4px 4px 0;
  }

  .formula-equation {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8.5pt;
    font-weight: bold;
    color: {{ theme.accent_primary }};
    margin: 3px 0;
  }
</style>
</head>
<body>

<!-- ========================================================================= -->
<!-- 1. COVER PAGE -->
<!-- ========================================================================= -->
<div class="cover-page">
  <div style="border-bottom: 2px solid {{ theme.border }}; padding-bottom: 12px; margin-top: 15px;">
    <span style="font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: {{ theme.accent_primary }};">
      StockLens Institutional Equity Research & Analytics
    </span>
    <p style="font-size: 7.5pt; color: {{ theme.text_muted }}; margin-top: 2px;">
      Quantitative Dual Equity Valuation & Time-Series Attribution
    </p>
  </div>

  <div style="text-align: center; margin: 30px 0;">
    <h1 style="font-size: 23pt; line-height: 1.25; margin-bottom: 14px; color: {{ theme.text_main }};">
      Comparative Stock Trend Analysis<br>Using Moving Averages
    </h1>
    <p style="font-size: 11pt; font-weight: 600; color: {{ theme.accent_primary }}; margin-bottom: 6px;">
      {{ company_a.info.name }} (NSE: {{ company_a.info.ticker }})<br>
      <span style="font-size: 9pt; color: {{ theme.text_muted }}; font-weight: normal;">versus</span><br>
      {{ company_b.info.name }} (NSE: {{ company_b.info.ticker }})
    </p>
    <div style="display: inline-block; background: {{ theme.card_bg }}; border: 1px solid {{ theme.border }}; border-radius: 6px; padding: 6px 16px; margin-top: 12px;">
      <span style="font-size: 8pt; color: {{ theme.text_muted }};">Analytical Window:</span>
      <strong style="font-size: 8pt; color: {{ theme.text_main }}; margin-left: 4px;">{{ date_range }}</strong>
    </div>
  </div>

  <!-- Analyst & Verification Block -->
  <div style="background: {{ theme.card_bg }}; border: 1px solid {{ theme.border }}; border-radius: 8px; padding: 18px 24px; margin-bottom: 20px;">
    <div class="grid-2">
      <div class="col-2" style="border-right: 1px solid {{ theme.border }}; padding-right: 15px;">
        <span style="font-size: 7pt; text-transform: uppercase; font-weight: 700; color: {{ theme.accent_primary }}; letter-spacing: 0.08em; display: block; margin-bottom: 6px;">
          Research Attribution
        </span>
        <table style="border: none; margin: 0;">
          <tr style="background: transparent;"><td style="border: none; padding: 2px 0; width: 35%; color: {{ theme.text_muted }}; font-weight: 600;">Prepared by:</td><td style="border: none; padding: 2px 0; font-weight: bold; color: {{ theme.text_main }}; font-size: 9.5pt;">{{ student_name }}</td></tr>
          <tr style="background: transparent;"><td style="border: none; padding: 2px 0; color: {{ theme.text_muted }}; font-weight: 600;">Reference ID:</td><td style="border: none; padding: 2px 0; font-family: monospace; font-size: 9pt; color: {{ theme.text_main }};">{{ roll_number }}</td></tr>
          <tr style="background: transparent;"><td style="border: none; padding: 2px 0; color: {{ theme.text_muted }}; font-weight: 600;">Date Compiled:</td><td style="border: none; padding: 2px 0; color: {{ theme.text_main }};">{{ generated_date }}</td></tr>
          <tr style="background: transparent;"><td style="border: none; padding: 2px 0; color: {{ theme.text_muted }}; font-weight: 600;">Analytical Engine:</td><td style="border: none; padding: 2px 0; color: {{ theme.text_main }}; font-size: 7.5pt;">{{ analysis.ai_engine }}</td></tr>
        </table>
      </div>

      <div class="col-2" style="padding-left: 15px;">
        <span style="font-size: 7pt; text-transform: uppercase; font-weight: 700; color: {{ theme.accent_primary }}; letter-spacing: 0.08em; display: block; margin-bottom: 6px;">
          Verification & Signatures
        </span>
        <div style="margin-top: 14px;">
          <div style="border-bottom: 1px dotted {{ theme.border }}; height: 20px;"></div>
          <span style="font-size: 7pt; color: {{ theme.text_muted }};">Quantitative Analyst / Author Sign-off</span>
        </div>
        <div style="margin-top: 16px;">
          <div style="border-bottom: 1px dotted {{ theme.border }}; height: 20px;"></div>
          <span style="font-size: 7pt; color: {{ theme.text_muted }};">Reviewing Director / Compliance Sign-off & Date</span>
        </div>
      </div>
    </div>
  </div>

  <div style="text-align: center; border-top: 1px solid {{ theme.border }}; padding-top: 10px;">
    <p style="font-size: 7pt; color: {{ theme.text_muted }};">
      StockLens Automated Financial Research Suite • Strict Zero-Hallucination Academic Standard
    </p>
  </div>
</div>


<!-- ========================================================================= -->
<!-- 2. TABLE OF ASSIGNED COMPANIES & STOCK SYMBOLS -->
<!-- ========================================================================= -->
<div class="page-break">
  <div class="section-title">
    <span>2. Table of Selected Companies & Stock Symbols</span>
    <span class="section-subtitle">Quantitative Research Asset Register</span>
  </div>

  <p>
    This quantitative study investigates two actively traded public corporations listed on the National Stock Exchange of India (NSE).
    Adjusted closing prices are compared across the observed analysis window.
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 20%;">Company Name</th>
        <th style="width: 14%;">Ticker Symbol</th>
        <th style="width: 12%;">Exchange</th>
        <th style="width: 18%;">Sector & Industry</th>
        <th style="width: 12%;">Currency</th>
        <th style="width: 24%;">Temporal Window</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>{{ company_a.info.name }}</strong></td>
        <td class="num" style="text-align: left; font-weight: bold; color: {{ theme.accent_primary }};">{{ company_a.info.ticker }}</td>
        <td>{{ company_a.info.exchange }}</td>
        <td>{{ company_a.info.sector }} / {{ company_a.info.industry }}</td>
        <td>{{ company_a.info.currency }} (₹)</td>
        <td>{{ date_range }}</td>
      </tr>
      <tr>
        <td><strong>{{ company_b.info.name }}</strong></td>
        <td class="num" style="text-align: left; font-weight: bold; color: {{ theme.accent_secondary }};">{{ company_b.info.ticker }}</td>
        <td>{{ company_b.info.exchange }}</td>
        <td>{{ company_b.info.sector }} / {{ company_b.info.industry }}</td>
        <td>{{ company_b.info.currency }} (₹)</td>
        <td>{{ date_range }}</td>
      </tr>
    </tbody>
  </table>

  <!-- ========================================================================= -->
  <!-- 3. STEP 1 - DATA EXTRACTION -->
  <!-- ========================================================================= -->
  <div class="section-title" style="margin-top: 18px;">
    <span>Step 1: Data Extraction & Historical Time-Series</span>
    <span class="section-subtitle">Sample of First 10 Trading Sessions</span>
  </div>

  <p>
    <strong>Data Extraction Methodology:</strong> Daily market-session records were obtained from {{ analysis.metadata.data_source }} for the observed date range {{ date_range }}.
    The analysis uses <em>Adjusted Close</em> rather than Unadjusted Raw Close.
    Adjusted closing prices retroactively scale down pre-split history when corporate actions occur, guaranteeing that technical moving average
    calculations do not register false collapse signals when a stock splits or pays a dividend.
  </p>

  <div class="grid-2 avoid-break">
    <div class="col-2">
      <div style="font-weight: bold; font-size: 7.5pt; margin-bottom: 4px; color: {{ theme.accent_primary }};">
        {{ company_a.info.ticker }} — First 10 Daily Closing Sessions
      </div>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th class="num">Close (₹)</th>
            <th class="num">Adj Close (₹)</th>
            <th class="num">Volume</th>
          </tr>
        </thead>
        <tbody>
          {% for row in sample_daily_a %}
          <tr>
            <td>{{ row.date }}</td>
            <td class="num">₹{{ "%.2f"|format(row.close) }}</td>
            <td class="num"><strong>₹{{ "%.2f"|format(row.adj_close) }}</strong></td>
            <td class="num">{{ "{:,}".format(row.volume) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="col-2">
      <div style="font-weight: bold; font-size: 7.5pt; margin-bottom: 4px; color: {{ theme.accent_secondary }};">
        {{ company_b.info.ticker }} — First 10 Daily Closing Sessions
      </div>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th class="num">Close (₹)</th>
            <th class="num">Adj Close (₹)</th>
            <th class="num">Volume</th>
          </tr>
        </thead>
        <tbody>
          {% for row in sample_daily_b %}
          <tr>
            <td>{{ row.date }}</td>
            <td class="num">₹{{ "%.2f"|format(row.close) }}</td>
            <td class="num"><strong>₹{{ "%.2f"|format(row.adj_close) }}</strong></td>
            <td class="num">{{ "{:,}".format(row.volume) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- 4. STEP 2 - MONTHLY SUMMARY -->
  <!-- ========================================================================= -->
  <div class="page-break">
  <div class="section-title" style="margin-top: 18px;">
    <span>Step 2: Monthly Summary & Resampling</span>
    <span class="section-subtitle">Calendar Month-End Adjusted Closes</span>
  </div>

  <p>
    <strong>Resampling Rationale:</strong> Daily equity prices exhibit micro-structural noise (intraday bid-ask friction, algorithmic front-running, and liquidity spikes). 
    To establish an academic baseline for moving average modeling, daily sessions are grouped by calendar month, selecting the final verified trading session 
    as the representative closing quote (replicating the Excel formula <code>=TEXT(Date, "YYYY-MM")</code> + group lookup).
  </p>

  <table class="avoid-break">
    <thead>
      <tr>
        <th style="width: 18%;">Month-Year</th>
        <th style="width: 20%;">Date of Final Session</th>
        <th class="num" style="width: 22%;">{{ company_a.info.ticker }} Month-End Close (₹)</th>
        <th class="num" style="width: 22%;">{{ company_b.info.ticker }} Month-End Close (₹)</th>
        <th class="center" style="width: 18%;">Higher Absolute Close</th>
      </tr>
    </thead>
    <tbody>
      {% for row in monthly_summary_table %}
      <tr>
        <td><strong>{{ row.month_label }}</strong></td>
        <td>{{ row.date }}</td>
        <td class="num" style="color: {{ theme.accent_primary }}; font-weight: bold;">₹{{ "%.2f"|format(row.company1_adj_close) }}</td>
        <td class="num" style="color: {{ theme.accent_secondary }}; font-weight: bold;">₹{{ "%.2f"|format(row.company2_adj_close) }}</td>
        <td class="center font-bold">
          {% if row.company1_adj_close > row.company2_adj_close %}
            {{ company_a.info.ticker }}
          {% else %}
            {{ company_b.info.ticker }}
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
</div>


<!-- ========================================================================= -->
<!-- 5. STEP 3 - MOVING AVERAGE CALCULATION -->
<!-- ========================================================================= -->
<div class="page-break">
  <div class="section-title">
    <span>Step 3: Moving Average Calculation & Technical Smoothing</span>
    <span class="section-subtitle">Mathematical Formulation & Analytical Series</span>
  </div>

  <div class="formula-box">
    <strong>Mathematical Formulation in Plain Words:</strong>
    <p style="margin: 4px 0;">
      A Simple Moving Average (SMA) creates a constantly updated average price over a specified temporal lookback. 
      In this analysis, a <strong>3-Month Moving Average (MA-3M)</strong> is applied to month-end adjusted closing prices.
      It adds the closing price of the current month and the two preceding months, then divides the sum by 3:
    </p>
    <div class="formula-equation">
      MA-3M(Month t) = [ Price(Month t) + Price(Month t-1) + Price(Month t-2) ] / 3
    </div>
    <p style="font-size: 7.5pt; color: {{ theme.text_muted }}; margin-top: 3px;">
      *Note on Initial Periods: The first two months (Months 1 and 2) cannot have a 3-month moving average because three full months of data 
      have not yet accumulated. In spreadsheet software (Google Sheets / Excel), the formula <code>=AVERAGE(B2:B4)</code> is initiated on Row 4 and dragged down.
    </p>
  </div>

  <div style="font-weight: bold; font-size: 8pt; margin-bottom: 4px; color: {{ theme.text_main }};">
    Comparative Valuation Table: Month-Year | Company 1 Close | Company 1 MA | Company 2 Close | Company 2 MA
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 14%;">Month-Year</th>
        <th class="num" style="width: 21%;">{{ company_a.info.ticker }} Close (₹)</th>
        <th class="num" style="width: 22%;">{{ company_a.info.ticker }} 3M-MA (₹)</th>
        <th class="num" style="width: 21%;">{{ company_b.info.ticker }} Close (₹)</th>
        <th class="num" style="width: 22%;">{{ company_b.info.ticker }} 3M-MA (₹)</th>
      </tr>
    </thead>
    <tbody>
      {% for r in template_table %}
      <tr>
        <td><strong>{{ r.month_year }}</strong></td>
        <td class="num">₹{{ "%.2f"|format(r.company1_close) }}</td>
        <td class="num" style="color: {{ theme.accent_primary }};">
          {% if r.company1_ma is not none %}
            <strong>₹{{ "%.2f"|format(r.company1_ma) }}</strong>
          {% else %}
            <span style="color: {{ theme.text_muted }};">— (Building Window)</span>
          {% endif %}
        </td>
        <td class="num">₹{{ "%.2f"|format(r.company2_close) }}</td>
        <td class="num" style="color: {{ theme.accent_secondary }};">
          {% if r.company2_ma is not none %}
            <strong>₹{{ "%.2f"|format(r.company2_ma) }}</strong>
          {% else %}
            <span style="color: {{ theme.text_muted }};">— (Building Window)</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- ========================================================================= -->
  <!-- 6. STEP 4 - GRAPHS -->
  <!-- ========================================================================= -->
  <div class="page-break">
  <div class="section-title" style="margin-top: 16px;">
    <span>Step 4: Graphical Representation & Trend Visualizations</span>
    <span class="section-subtitle">Side-by-Side MA Charts & Normalized Head-to-Head Overlay</span>
  </div>

  <p>
    The charts below are rendered server-side using Matplotlib. The side-by-side graphs illustrate each company's month-end price alongside its 
    3-month moving average baseline. The bottom overlay chart normalizes both securities to 100.0 on day one to eliminate nominal price disparities and 
    enable direct, fair visual comparison of 2-year compounding trajectory.
  </p>

  <div class="grid-2 avoid-break" style="margin-top: 6px;">
    <div class="col-2">
      <img src="{{ charts.chart_a }}" class="chart-img" alt="Chart A">
    </div>
    <div class="col-2">
      <img src="{{ charts.chart_b }}" class="chart-img" alt="Chart B">
    </div>
  </div>

  <div class="avoid-break" style="margin-top: 8px;">
    <img src="{{ charts.chart_overlay }}" class="chart-img" alt="Comparative Overlay Chart">
  </div>
  </div>
</div>


<!-- ========================================================================= -->
<!-- 7. STEP 5 - COMPARATIVE ANALYSIS -->
<!-- ========================================================================= -->
<div class="page-break">
  <div class="section-title">
    <span>Step 5: Comparative Quantitative Analysis</span>
    <span class="section-subtitle">Statistical Metrics & Analytical Evaluation</span>
  </div>

  <!-- Key Quantitative Metrics Table -->
  <table>
    <thead>
      <tr>
        <th style="width: 32%;">Analytical Performance Metric</th>
        <th class="num" style="width: 24%;">{{ company_a.info.name }} ({{ company_a.info.ticker }})</th>
        <th class="num" style="width: 24%;">{{ company_b.info.name }} ({{ company_b.info.ticker }})</th>
        <th class="center" style="width: 20%;">Dimension Winner</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Latest Adjusted Close</td>
        <td class="num">₹{{ "%.2f"|format(company_a.metrics.current_price) }}</td>
        <td class="num">₹{{ "%.2f"|format(company_b.metrics.current_price) }}</td>
        <td class="center">—</td>
      </tr>
      <tr>
        <td>2-Year Total Price Return</td>
        <td class="num" style="font-weight: bold; color: {{ theme.accent_primary }};">{{ "%+.1f"|format(company_a.metrics.total_return_pct) }}%</td>
        <td class="num" style="font-weight: bold; color: {{ theme.accent_secondary }};">{{ "%+.1f"|format(company_b.metrics.total_return_pct) }}%</td>
        <td class="center font-bold">{% if company_a.metrics.total_return_pct > company_b.metrics.total_return_pct %}{{ company_a.info.ticker }}{% else %}{{ company_b.info.ticker }}{% endif %}</td>
      </tr>
      <tr>
        <td>Compound Annual Growth Rate (CAGR)</td>
        <td class="num" style="font-weight: bold; color: {{ theme.accent_primary }};">+{{ "%.1f"|format(company_a.metrics.cagr_pct) }}%</td>
        <td class="num" style="font-weight: bold; color: {{ theme.accent_secondary }};">+{{ "%.1f"|format(company_b.metrics.cagr_pct) }}%</td>
        <td class="center font-bold">{% if company_a.metrics.cagr_pct > company_b.metrics.cagr_pct %}{{ company_a.info.ticker }}{% else %}{{ company_b.info.ticker }}{% endif %}</td>
      </tr>
      <tr>
        <td>Annualized Volatility (Risk)</td>
        <td class="num">{{ "%.1f"|format(company_a.metrics.annualized_volatility_pct) }}%</td>
        <td class="num">{{ "%.1f"|format(company_b.metrics.annualized_volatility_pct) }}%</td>
        <td class="center font-bold">{% if company_a.metrics.annualized_volatility_pct < company_b.metrics.annualized_volatility_pct %}{{ company_a.info.ticker }} (Lower){% else %}{{ company_b.info.ticker }} (Lower){% endif %}</td>
      </tr>
      <tr>
        <td>Maximum Peak-to-Trough Drawdown</td>
        <td class="num">-{{ "%.1f"|format(company_a.metrics.max_drawdown_pct) }}%</td>
        <td class="num">-{{ "%.1f"|format(company_b.metrics.max_drawdown_pct) }}%</td>
        <td class="center font-bold">{% if company_a.metrics.max_drawdown_pct < company_b.metrics.max_drawdown_pct %}{{ company_a.info.ticker }} (Safer){% else %}{{ company_b.info.ticker }} (Safer){% endif %}</td>
      </tr>
      <tr>
        <td>Sharpe Ratio (Rf = 6.5% Benchmark)</td>
        <td class="num" style="font-weight: bold;">{{ "%.2f"|format(company_a.metrics.sharpe_ratio) }}</td>
        <td class="num" style="font-weight: bold;">{{ "%.2f"|format(company_b.metrics.sharpe_ratio) }}</td>
        <td class="center font-bold">{% if company_a.metrics.sharpe_ratio > company_b.metrics.sharpe_ratio %}{{ company_a.info.ticker }}{% else %}{{ company_b.info.ticker }}{% endif %}</td>
      </tr>
      <tr>
        <td>Stability Score (0 to 100 Index)</td>
        <td class="num">{{ "%.1f"|format(company_a.metrics.stability_score or 50.0) }}/100</td>
        <td class="num">{{ "%.1f"|format(company_b.metrics.stability_score or 50.0) }}/100</td>
        <td class="center font-bold">{% if (company_a.metrics.stability_score or 0) > (company_b.metrics.stability_score or 0) %}{{ company_a.info.ticker }}{% else %}{{ company_b.info.ticker }}{% endif %}</td>
      </tr>
      <tr>
        <td>Growth Score (0 to 100 Index)</td>
        <td class="num">{{ "%.1f"|format(company_a.metrics.growth_score or 50.0) }}/100</td>
        <td class="num">{{ "%.1f"|format(company_b.metrics.growth_score or 50.0) }}/100</td>
        <td class="center font-bold">{% if (company_a.metrics.growth_score or 0) > (company_b.metrics.growth_score or 0) %}{{ company_a.info.ticker }}{% else %}{{ company_b.info.ticker }}{% endif %}</td>
      </tr>
      <tr>
        <td>2-Year Pearson Daily Correlation (r)</td>
        <td class="num center" colspan="2"><strong>{{ "%.3f"|format(analysis.correlation_2y) }}</strong> (Co-movement Coefficient)</td>
        <td class="center">{% if analysis.correlation_2y > 0.7 %}Strong Direct{% elif analysis.correlation_2y > 0.4 %}Moderate Direct{% else %}Weak / Independent{% endif %}</td>
      </tr>
    </tbody>
  </table>

  <!-- Written Synthesis Answering Checklist Questions -->
  <div class="card avoid-break" style="margin-top: 10px;">
    <div style="font-weight: 800; font-size: 8.5pt; color: {{ theme.accent_primary }}; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em;">
      Structured Academic Evaluation: Stability, Growth & Moving Average Revelations
    </div>
    
    <div style="font-size: 8pt; line-height: 1.5; color: {{ theme.text_body }}; white-space: pre-line;">
      {{ comparative_text }}
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- 8. WHY THE PRICES MOVED -->
  <!-- ========================================================================= -->
  <div class="section-title" style="margin-top: 16px;">
    <span>8. Why the Prices Moved: Anomaly Attribution & News Catalysts</span>
    <span class="section-subtitle">Verified Contemporaneous Head-to-Head Headlines</span>
  </div>

  <p>
    The analytical engine monitors historical single-day price fluctuations exceeding &plusmn;3.2%. Detected anomalies are cross-referenced with 
    archived journalistic news feeds to identify the fundamental catalyst. Below are the verified top headline events for each company:
  </p>

  <div class="grid-2 avoid-break">
    <!-- Company A Events -->
    <div class="col-2">
      <div style="font-weight: bold; font-size: 7.8pt; color: {{ theme.accent_primary }}; margin-bottom: 4px;">
        {{ company_a.info.name }} ({{ company_a.info.ticker }}) Events
      </div>
      {% for ev in company_a.movement_events[:3] %}
      <div style="background: {{ theme.card_bg }}; border: 1px solid {{ theme.border }}; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
          <span class="tag {% if ev.direction == 'jump' %}tag-jump{% else %}tag-drop{% endif %}">
            {{ ev.direction|upper }} {{ "%+.1f"|format(ev.change_pct) }}%
          </span>
          <span style="font-size: 7pt; color: {{ theme.text_muted }}; font-family: monospace;">{{ ev.date }}</span>
        </div>
        <p style="font-weight: 600; font-size: 7.5pt; color: {{ theme.text_main }}; margin-bottom: 2px;">
          "{{ ev.headline }}"
        </p>
        <p style="font-size: 7pt; color: {{ theme.text_muted }}; margin-bottom: 2px;">
          {% if ev.url and ev.url.startswith('https://') %}<a href="{{ ev.url }}" target="_blank" rel="noopener noreferrer">Source: <strong>{{ ev.source }}</strong></a>{% else %}Source: <strong>{{ ev.source }}</strong>{% endif %} | Confidence: {{ ev.confidence }}
        </p>
        <p style="font-size: 7.2pt; color: {{ theme.text_body }}; margin: 0;">
          {{ ev.explanation }}
        </p>
      </div>
      {% endfor %}
    </div>

    <!-- Company B Events -->
    <div class="col-2">
      <div style="font-weight: bold; font-size: 7.8pt; color: {{ theme.accent_secondary }}; margin-bottom: 4px;">
        {{ company_b.info.name }} ({{ company_b.info.ticker }}) Events
      </div>
      {% for ev in company_b.movement_events[:3] %}
      <div style="background: {{ theme.card_bg }}; border: 1px solid {{ theme.border }}; border-radius: 4px; padding: 6px 8px; margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
          <span class="tag {% if ev.direction == 'jump' %}tag-jump{% else %}tag-drop{% endif %}">
            {{ ev.direction|upper }} {{ "%+.1f"|format(ev.change_pct) }}%
          </span>
          <span style="font-size: 7pt; color: {{ theme.text_muted }}; font-family: monospace;">{{ ev.date }}</span>
        </div>
        <p style="font-weight: 600; font-size: 7.5pt; color: {{ theme.text_main }}; margin-bottom: 2px;">
          "{{ ev.headline }}"
        </p>
        <p style="font-size: 7pt; color: {{ theme.text_muted }}; margin-bottom: 2px;">
          {% if ev.url and ev.url.startswith('https://') %}<a href="{{ ev.url }}" target="_blank" rel="noopener noreferrer">Source: <strong>{{ ev.source }}</strong></a>{% else %}Source: <strong>{{ ev.source }}</strong>{% endif %} | Confidence: {{ ev.confidence }}
        </p>
        <p style="font-size: 7.2pt; color: {{ theme.text_body }}; margin: 0;">
          {{ ev.explanation }}
        </p>
      </div>
      {% endfor %}
    </div>
  </div>

  <div class="formula-box" style="margin-top: 4px; border-left-color: #f59e0b;">
    <strong>Mandatory Scientific Causation Notice:</strong>
    <p style="font-size: 7.2pt; margin: 0; color: {{ theme.text_muted }};">
      {{ analysis.causation_warning }}
    </p>
  </div>
</div>


<!-- ========================================================================= -->
<!-- 9. CONCLUSION & INVESTMENT VERDICT -->
<!-- ========================================================================= -->
<div class="page-break">
  <div class="section-title">
    <span>9. Conclusion & Research Verdict</span>
    <span class="section-subtitle">Comparative Determination & Analytical Limitations</span>
  </div>

  <!-- Arbiter Winner Banner -->
  <div class="card-highlight avoid-break">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <span style="font-size: 7.5pt; font-weight: bold; text-transform: uppercase; color: {{ theme.accent_primary }}; letter-spacing: 0.08em;">
          Comparative Research Verdict
        </span>
        <h3 style="font-size: 13pt; margin-top: 2px; color: {{ theme.text_main }};">
          {{ analysis.head_to_head.winner_name }} ({{ analysis.head_to_head.winner_ticker }}) — {{ analysis.head_to_head.margin }}
        </h3>
      </div>
      <div style="text-align: right;">
        <span style="font-size: 7.5pt; color: {{ theme.text_muted }}; display: block;">Score Outperformance</span>
        <strong style="font-size: 12pt; color: {{ theme.accent_primary }};">+{{ "%.1f"|format(analysis.head_to_head.score_diff) }} pts</strong>
      </div>
    </div>
    <p style="margin-top: 6px; font-size: 8pt; line-height: 1.45; color: {{ theme.text_main }};">
      {{ analysis.head_to_head.verdict_text }}
    </p>
  </div>

  <!-- Buy/Hold/Avoid Scorecard Grid -->
  <div class="grid-2 avoid-break" style="margin-top: 6px;">
    <!-- Company A Scorecard -->
    <div class="col-2 card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong style="font-size: 8.5pt; color: {{ theme.text_main }};">{{ company_a.info.name }}</strong>
        <span class="tag {% if company_a.recommendation.action == 'BUY' %}tag-buy{% elif company_a.recommendation.action == 'HOLD' %}tag-hold{% else %}tag-avoid{% endif %}">
          {{ company_a.recommendation.action }} ({{ company_a.recommendation.score }}/100)
        </span>
      </div>
      <p style="font-size: 7.2pt; color: {{ theme.text_muted }}; margin-bottom: 4px;">
        Risk Level: <strong style="color: {{ theme.text_main }};">{{ company_a.recommendation.risk_level }}</strong>
      </p>
      <p style="font-size: 7.5pt; line-height: 1.4; color: {{ theme.text_body }}; margin-bottom: 4px;">
        {{ company_a.recommendation.summary }}
      </p>
      {% if company_a.recommendation.key_drivers %}
      <div style="font-size: 7pt; color: {{ theme.text_muted }}; border-top: 1px dotted {{ theme.border }}; padding-top: 3px;">
        <strong>Key Drivers:</strong>
        <ul style="margin-left: 12px; margin-top: 2px;">
          {% for d in company_a.recommendation.key_drivers[:2] %}
          <li>{{ d }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>

    <!-- Company B Scorecard -->
    <div class="col-2 card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong style="font-size: 8.5pt; color: {{ theme.text_main }};">{{ company_b.info.name }}</strong>
        <span class="tag {% if company_b.recommendation.action == 'BUY' %}tag-buy{% elif company_b.recommendation.action == 'HOLD' %}tag-hold{% else %}tag-avoid{% endif %}">
          {{ company_b.recommendation.action }} ({{ company_b.recommendation.score }}/100)
        </span>
      </div>
      <p style="font-size: 7.2pt; color: {{ theme.text_muted }}; margin-bottom: 4px;">
        Risk Level: <strong style="color: {{ theme.text_main }};">{{ company_b.recommendation.risk_level }}</strong>
      </p>
      <p style="font-size: 7.5pt; line-height: 1.4; color: {{ theme.text_body }}; margin-bottom: 4px;">
        {{ company_b.recommendation.summary }}
      </p>
      {% if company_b.recommendation.key_drivers %}
      <div style="font-size: 7pt; color: {{ theme.text_muted }}; border-top: 1px dotted {{ theme.border }}; padding-top: 3px;">
        <strong>Key Drivers:</strong>
        <ul style="margin-left: 12px; margin-top: 2px;">
          {% for d in company_b.recommendation.key_drivers[:2] %}
          <li>{{ d }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>
  </div>

  <!-- Limitations Paragraph -->
  <div class="card avoid-break" style="margin-top: 8px; border-left: 3px solid #dc2626;">
    <strong style="font-size: 8pt; color: {{ theme.text_main }}; text-transform: uppercase;">
      Limitations of this Study:
    </strong>
    <p style="font-size: 7.5pt; line-height: 1.45; color: {{ theme.text_body }}; margin-top: 3px;">
      This project is conducted exclusively on historical technical price data, adjusted month-end closes, and 3-month moving averages.
      It explicitly does <strong>not</strong> include corporate fundamental evaluations such as balance sheet liquidity, profit & loss statement cash flows,
      P/E multiple valuations relative to industry peers, or debt-to-equity leverage. Technical moving averages are inherently lagging indicators 
      that reflect past investor sentiment; historical outperformance provides no guarantee of future financial market returns.
    </p>
  </div>

  <!-- ========================================================================= -->
  <!-- 10. APPENDIX -->
  <!-- ========================================================================= -->
  <div class="section-title" style="margin-top: 14px;">
    <span>10. Appendix: Methodology, Formulations & Regulatory Disclaimer</span>
    <span class="section-subtitle">Academic Audit Documentation</span>
  </div>

  <div class="grid-2 avoid-break" style="font-size: 7.2pt; color: {{ theme.text_body }};">
    <div class="col-2">
      <strong style="color: {{ theme.text_main }}; display: block; margin-bottom: 2px;">Scientific Formulas & Definitions:</strong>
      <ul style="margin-left: 12px; line-height: 1.4;">
        <li><strong>CAGR:</strong> <code>(P_end / P_start)^(365.25 / delta_days) - 1</code></li>
        <li><strong>Annualized Volatility:</strong> <code>Daily_StdDev * sqrt(252)</code></li>
        <li><strong>Sharpe Ratio:</strong> <code>(CAGR - Rf) / Ann_Vol</code> with Indian 10Y Rf = 6.5%.</li>
        <li><strong>Max Drawdown:</strong> Deepest percentage loss from prior historical peak.</li>
        <li><strong>MA-3M:</strong> Arithmetic 3-period rolling average over calendar month closes.</li>
      </ul>
    </div>

    <div class="col-2">
      <strong style="color: {{ theme.text_main }}; display: block; margin-bottom: 2px;">Scoring Weights & Data Sources:</strong>
      <ul style="margin-left: 12px; line-height: 1.4;">
        <li><strong>Stability Index:</strong> 40% Volatility, 35% Drawdown, 25% Trend Consistency.</li>
        <li><strong>Growth Index:</strong> 45% CAGR, 30% 3M-Momentum, 25% Technical Trend.</li>
        <li><strong>Recommendation Thresholds:</strong> BUY (Score &ge; 70), HOLD (45–69), AVOID (&lt; 45).</li>
        <li><strong>Data Source:</strong> {{ analysis.metadata.data_source }}; symbols are shown with their listing exchange.</li>
      </ul>
    </div>
  </div>

  <div style="border-top: 1px solid {{ theme.border }}; padding-top: 6px; margin-top: 8px; font-size: 6.8pt; color: {{ theme.text_muted }};">
    <strong>Mandatory Academic Disclaimer:</strong> {{ analysis.disclaimer }}
    This report was generated using the StockLens dual-equity comparative analytics pipeline for educational presentation purposes.
  </div>
</div>

</body>
</html>
"""


def _get_html_theme_dict(theme_name: str) -> Dict[str, str]:
    if theme_name == "light":
        return {
            "bg": "#ffffff",
            "text_main": "#0f172a",
            "text_body": "#334155",
            "text_muted": "#64748b",
            "border": "#cbd5e1",
            "card_bg": "#f8fafc",
            "highlight_bg": "#eff6ff",
            "highlight_border": "#93c5fd",
            "accent_primary": "#2563eb",
            "accent_secondary": "#059669",
            "table_header_bg": "#f1f5f9",
            "table_header_text": "#0f172a",
            "table_stripe_bg": "#f8fafc",
            "formula_bg": "#f8fafc",
            "tag_buy_bg": "#dcfce7",
            "tag_buy_text": "#166534",
            "tag_buy_border": "#86efac",
            "tag_hold_bg": "#fef3c7",
            "tag_hold_text": "#92400e",
            "tag_hold_border": "#fde68a",
            "tag_avoid_bg": "#fee2e2",
            "tag_avoid_text": "#991b1b",
            "tag_avoid_border": "#fca5a5",
            "tag_jump_bg": "#dcfce7",
            "tag_jump_text": "#166534",
            "tag_drop_bg": "#fee2e2",
            "tag_drop_text": "#991b1b"
        }
    else:  # dark editorial
        return {
            "bg": "#0b0f19",
            "text_main": "#f8fafc",
            "text_body": "#cbd5e1",
            "text_muted": "#94a3b8",
            "border": "#283553",
            "card_bg": "#131b2e",
            "highlight_bg": "linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.9))",
            "highlight_border": "#3b82f6",
            "accent_primary": "#38bdf8",
            "accent_secondary": "#34d399",
            "table_header_bg": "#1e293b",
            "table_header_text": "#f8fafc",
            "table_stripe_bg": "#0f172a",
            "formula_bg": "#131b2e",
            "tag_buy_bg": "rgba(16, 185, 129, 0.18)",
            "tag_buy_text": "#34d399",
            "tag_buy_border": "rgba(16, 185, 129, 0.4)",
            "tag_hold_bg": "rgba(245, 158, 11, 0.18)",
            "tag_hold_text": "#fbbf24",
            "tag_hold_border": "rgba(245, 158, 11, 0.4)",
            "tag_avoid_bg": "rgba(239, 68, 68, 0.18)",
            "tag_avoid_text": "#f87171",
            "tag_avoid_border": "rgba(239, 68, 68, 0.4)",
            "tag_jump_bg": "rgba(16, 185, 129, 0.2)",
            "tag_jump_text": "#34d399",
            "tag_drop_bg": "rgba(239, 68, 68, 0.2)",
            "tag_drop_text": "#f87171"
        }


async def generate_report_html(
    analysis: AnalysisResponse,
    student_name: str = "Senior Secondary Student",
    roll_number: str = "SEC-2026-042",
    theme: str = "dark"
) -> str:
    """
    Renders the complete exhibition-grade HTML document.
    """
    theme_dict = _get_html_theme_dict(theme)

    # 1. Server-side Charts
    charts = generate_all_report_charts(
        company_a_name=analysis.company_a.info.name,
        ticker_a=analysis.company_a.info.ticker,
        monthly_a=analysis.company_a.monthly_series,
        company_b_name=analysis.company_b.info.name,
        ticker_b=analysis.company_b.info.ticker,
        monthly_b=analysis.company_b.monthly_series,
        overlay_series=analysis.overlay_series,
        theme=theme
    )

    # 2. Comparative text
    comp_text_data = generate_deterministic_comparative_text(
        comp_a=analysis.company_a,
        comp_b=analysis.company_b,
        comparison_obj=analysis.comparison_object
    )
    raw_comparative_text = comp_text_data["full_analysis"]

    # Optionally polish with Gemini if key is present
    polished_text = await polish_comparative_analysis_with_gemini(
        raw_analysis=raw_comparative_text,
        company_a_name=analysis.company_a.info.name,
        company_b_name=analysis.company_b.info.name
    )

    # 3. Monthly Summary Rows
    m_a = {p.month_year: p for p in analysis.company_a.monthly_series}
    m_b = {p.month_year: p for p in analysis.company_b.monthly_series}
    common_months = sorted(list(set(m_a.keys()).intersection(set(m_b.keys()))))
    monthly_summary_table = []
    for m in common_months:
        pa = m_a[m]
        pb = m_b[m]
        monthly_summary_table.append({
            "month_label": pa.month_label,
            "date": pa.date,
            "company1_adj_close": pa.adj_close,
            "company2_adj_close": pb.adj_close
        })

    # 4. Project Template Table Rows
    template_table = analysis.project_template_table
    if not template_table:
        template_table = []
        for m in common_months:
            pa = m_a[m]
            pb = m_b[m]
            from app.models.schemas import ProjectTemplateTableRow
            template_table.append(ProjectTemplateTableRow(
                month_year=m,
                company1_close=pa.adj_close,
                company1_ma=pa.ma_3m,
                company2_close=pb.adj_close,
                company2_ma=pb.ma_3m
            ))

    # 5. First 10 daily samples
    sample_daily_a = analysis.company_a.daily_series[:10]
    sample_daily_b = analysis.company_b.daily_series[:10]

    template = Environment(autoescape=select_autoescape(default_for_string=True)).from_string(HTML_TEMPLATE)
    dates = [
        date
        for company in (analysis.company_a, analysis.company_b)
        for point in company.daily_series
        if (date := point.date)
    ]
    date_range = f"{min(dates)} to {max(dates)}" if dates else "Historical analysis window"
    html_output = template.render(
        company_a=analysis.company_a,
        company_b=analysis.company_b,
        analysis=analysis,
        charts=charts,
        comparative_text=polished_text,
        student_name=student_name,
        roll_number=roll_number,
        generated_date=datetime.now().strftime("%d %B %Y"),
        date_range=date_range,
        monthly_summary_table=monthly_summary_table,
        template_table=template_table,
        sample_daily_a=sample_daily_a,
        sample_daily_b=sample_daily_b,
        theme=theme_dict
    )

    return html_output


async def generate_pdf_report(
    analysis: AnalysisResponse,
    student_name: str = "Senior Secondary Student",
    roll_number: str = "SEC-2026-042",
    theme: str = "dark"
) -> bytes:
    """
    Renders HTML report and executes Playwright PDF print with header/footer page numbers.
    """
    html_content = await generate_report_html(
        analysis=analysis,
        student_name=student_name,
        roll_number=roll_number,
        theme=theme
    )

    theme_dict = _get_html_theme_dict(theme)
    header_color = theme_dict["text_muted"]
    border_color = theme_dict["border"]

    header_template = f'''
    <div style="font-size: 7.5px; width: 100%; display: flex; justify-content: space-between; padding: 0 12mm; color: {header_color}; font-family: -apple-system, sans-serif; border-bottom: 0.5px solid {border_color}; padding-bottom: 2px;">
      <span>StockLens: {analysis.company_a.info.ticker} vs {analysis.company_b.info.ticker} (Comparative Stock Trend Analysis)</span>
      <span>{datetime.now().strftime("%b %Y")}</span>
    </div>
    '''

    footer_template = f'''
    <div style="font-size: 7.5px; width: 100%; display: flex; justify-content: space-between; padding: 0 12mm; color: {header_color}; font-family: -apple-system, sans-serif; border-top: 0.5px solid {border_color}; padding-top: 2px;">
      <span>StockLens Institutional Dual Equity Analytics Platform</span>
      <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
    </div>
    '''

    async with async_playwright() as p:
        # Launch browser with channels fallback
        browser = None
        for ch in ["msedge", "chrome", None]:
            try:
                if ch:
                    browser = await p.chromium.launch(channel=ch, headless=True)
                else:
                    browser = await p.chromium.launch(headless=True)
                break
            except Exception:
                continue

        if not browser:
            raise RuntimeError("Could not initialize Chromium browser for PDF rendering.")

        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")

        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template,
            margin={"top": "14mm", "bottom": "14mm", "left": "10mm", "right": "10mm"}
        )

        await browser.close()
        return pdf_bytes
