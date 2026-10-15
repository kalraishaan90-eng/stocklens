"""
generate_tabs_pdf.py - Generates an executive 4-page PDF with tab screenshots alongside detailed text.
"""
import os
import pymupdf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (Pages 2-4)
        if self._pageNumber > 1:
            self.drawString(36, 756, "StockLens  |  Platform Architecture & Operational Interfaces")
            self.drawRightString(576, 756, "Dual Equity Analytics System")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.75)
            self.line(36, 750, 576, 750)
            
        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(36, 38, 576, 38)
        
        self.setFont("Helvetica", 7.5)
        self.drawString(36, 26, "StockLens  *  Verified Historical Attribution  *  Algorithmic Recommendation Engine  *  Educational Exhibition")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.setFont("Helvetica-Bold", 7.5)
        self.drawRightString(576, 26, page_str)
        self.restoreState()

def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A")
    )

    doc_subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569")
    )

    badge_style = ParagraphStyle(
        'TabBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#B45309")
    )

    h1_style = ParagraphStyle(
        'TabHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#0F172A")
    )

    section_lbl_style = ParagraphStyle(
        'SectionLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    body_style = ParagraphStyle(
        'TabBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )

    bullet_style = ParagraphStyle(
        'TabBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        leftIndent=4
    )

    caption_style = ParagraphStyle(
        'ImageCaption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#64748B"),
        alignment=1
    )

    spec_hdr_style = ParagraphStyle(
        'SpecHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    spec_text_style = ParagraphStyle(
        'SpecText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#475569")
    )

    tabs = [
        {
            "tab_num": "TAB 01",
            "name": "Home Interface",
            "route": "Route: /",
            "badge": "DISCOVERY & PAIRING CONTROL CENTER",
            "img": "D:/StockLens/docs/screenshots/tab_1_home.png",
            "caption": "Figure 1: StockLens Home Interface — Dual company selector, curated exhibition pairs, and offline snapshot switcher.",
            "lead": "The Home Tab serves as the central command portal for StockLens. It allows evaluators and students to immediately configure comparative equity evaluations through one-click curated pairs or arbitrary ticker exploration.",
            "capabilities": [
                "<b>9 Curated Exhibition Pairs:</b> One-click comparative analysis for leading sector peers (Apple vs Microsoft, Nvidia vs AMD, Coca-Cola vs PepsiCo, Tesla vs Ford, TVS vs Tata Motors, HAL vs Mazagon Dock).",
                "<b>Rapid Autocomplete Search:</b> Instant ticker and corporate name resolution against US & Indian equity databases with input validation.",
                "<b>Offline Exhibition Snapshot Mode:</b> Deterministic offline demo mode (Ctrl+Shift+D) backed by pre-fetched, audited datasets for guaranteed zero-latency demos without network reliance.",
                "<b>Mobile Handoff QR Code:</b> On-screen QR generator enabling judges and exhibition visitors to scan and open the active comparison on their personal mobile devices."
            ],
            "workflow": "<b>Operational Workflow:</b> Select two companies via autocomplete or preset pill -> Preview summary parameters -> Launch deep-dive evaluation via the primary 'Run Comparative Analysis' action.",
            "specs": "<b>Architecture & Stack:</b> React 18, TypeScript, Tailwind CSS · <b>Key Modules:</b> <code>Home.tsx</code>, <code>CompanyInput.tsx</code> · <b>State Management:</b> Active pairing cached in browser <code>localStorage</code> for persistent cross-tab routing · <b>Modes:</b> Normal, Kiosk (<code>?kiosk=1</code>, 90s reset), Presenter Mode."
        },
        {
            "tab_num": "TAB 02",
            "name": "Analysis Interface",
            "route": "Route: /analysis",
            "badge": "DEEP QUANTITATIVE COMPARATIVE ENGINE",
            "img": "D:/StockLens/docs/screenshots/tab_2_analysis.png",
            "caption": "Figure 2: StockLens Analysis Dashboard — Synchronized interactive charts, volatility bands, and rule-based verdicts.",
            "lead": "The flagship quantitative dashboard delivering side-by-side evaluation across 2-year adjusted closing prices. It marries mathematical risk and return metrics with verifiable event attribution and algorithmic decision scoring.",
            "capabilities": [
                "<b>Synchronized Interactive Visualizations:</b> Normalized performance charts (base 100), 3-month rolling moving averages, historical drawdown profiles, and rolling volatility curves.",
                "<b>Mathematical Risk/Return Statistics:</b> Rigorous calculation of Cumulative Return, CAGR, Annualized Volatility (ddof=1, √252), Sharpe-style ratio, Beta, and Pearson Correlation.",
                "<b>'Why It Moved' Anomaly Engine:</b> Flags statistically anomalous daily price moves exceeding 2.5 standard deviations (σ) and links contextual Google News headlines with publisher attribution.",
                "<b>Deterministic Verdict Scorecard:</b> Six weighted rule-based signals (Trend, Momentum, Volatility, Sharpe Quality, 52-Week Position, Valuation Proxy) mapped into clear Buy, Hold, or Avoid recommendations."
            ],
            "workflow": "<b>Operational Workflow:</b> Review KPI cards -> Evaluate rebased growth curves -> Inspect flagged historical anomaly dates -> Review signal breakdown behind algorithmic verdict.",
            "specs": "<b>Architecture & Stack:</b> Recharts, Lucide Icons, FastAPI · <b>Key Modules:</b> <code>Analysis.tsx</code>, <code>TerminalChart.tsx</code>, <code>MetricCard.tsx</code> · <b>Hotkeys:</b> Press 'P' for auto-scrolling Presenter Mode · <b>Data Flow:</b> Yahoo Finance adjusted price pipeline with statistical anomaly filtering."
        },
        {
            "tab_num": "TAB 03",
            "name": "Report Interface",
            "route": "Route: /report",
            "badge": "EXECUTIVE AUDIT DOSSIER & EXPORT HUB",
            "img": "D:/StockLens/docs/screenshots/tab_3_report.png",
            "caption": "Figure 3: StockLens Executive Report — Print-first layout with high-density metric matrices and compliance audit logs.",
            "lead": "The Report Tab converts dual-equity mathematical evaluations into an executive-ready, printable dossier. Crafted with print-first styling and high information density, it is structured for physical printing, PDF distribution, and formal judge assessment.",
            "capabilities": [
                "<b>Executive Summary Matrix:</b> Clear side-by-side scorecard highlighting performance leaders, risk minimizers, and Sharpe winners across all evaluated metrics.",
                "<b>Month-End Tabular Breakdown:</b> Full historical table of monthly adjusted close prices, moving averages, and monthly percentage changes with sorted alignment.",
                "<b>Chronological Anomaly Log:</b> Complete audit trail of flagged unusual volatility days, complete with dates, percentage price moves, and corroborated news source links.",
                "<b>Browser & PDF Print Layouts:</b> Clean CSS media print styles that eliminate extraneous UI controls, banners, and interactive buttons for pristine paper or PDF output."
            ],
            "workflow": "<b>Operational Workflow:</b> Review executive summary comparisons -> Filter monthly pricing table -> Export clean CSV for spreadsheet modeling -> Trigger 1-click Print/PDF export for paper presentation.",
            "specs": "<b>Architecture & Stack:</b> CSS Paged Media, Vite · <b>Key Modules:</b> <code>Report.tsx</code>, <code>SummaryMatrix.tsx</code>, <code>PrintHeader.tsx</code> · <b>Export Formats:</b> Direct PDF via browser print engine, formatted CSV download · <b>Compliance:</b> Embedded timestamp and legal disclaimer stamps."
        },
        {
            "tab_num": "TAB 04",
            "name": "About Interface",
            "route": "Route: /about",
            "badge": "METHODOLOGY, MATHEMATICS & GOVERNANCE",
            "img": "D:/StockLens/docs/screenshots/tab_4_about.png",
            "caption": "Figure 4: StockLens About & Methodology — Explicit mathematical definitions, statistical thresholds, and ethical safeguards.",
            "lead": "The About Tab provides complete transparency into the quantitative logic, statistical parameters, attribution boundaries, and academic principles underlying StockLens. It reinforces the system's commitment to verifiable and explainable analytics.",
            "capabilities": [
                "<b>Mathematical Formula Transparency:</b> Explicit documentation of all equations including CAGR: (last/first)^(365.25/days)-1, Volatility: s*√252, and Sharpe-style metric: (CAGR - Rf)/Volatility.",
                "<b>Attribution Governance & Ethics:</b> Clear delineation between observed correlation and causal claims: historical news headlines provide contextual evidence rather than causal proof.",
                "<b>Signal Weighting Disclosure:</b> Transparent inspection of the six signal weights powering the recommendation engine, ensuring zero black-box obscurity.",
                "<b>Educational & Regulatory Disclaimer:</b> Explicit disclaimers establishing that StockLens is an educational demonstration project and does not offer financial or investment advice."
            ],
            "workflow": "<b>Operational Workflow:</b> Read five-step explainer -> Inspect mathematical formulas behind risk metrics -> Verify signal scoring weights -> Review judge Q&A and attribution guidelines.",
            "specs": "<b>Architecture & Stack:</b> Markdown documentation, Lucide Icons · <b>Key Modules:</b> <code>About.tsx</code>, <code>FormulaCard.tsx</code> · <b>Integrity Safeguards:</b> Data cleaning rules for dividends/splits, missing date handling · <b>Pedigree:</b> Developed for senior secondary science & technology exhibition."
        }
    ]

    story = []

    for idx, tab in enumerate(tabs):
        # Header banner
        if idx == 0:
            story.append(Paragraph("StockLens — Platform & Interface Overview", doc_title_style))
            story.append(Spacer(1, 3))
            story.append(Paragraph("A comprehensive architectural and functional walkthrough of the four primary operational interfaces with side-by-side screenshots, functional breakdowns, and underlying quantitative mechanics.", doc_subtitle_style))
            story.append(Spacer(1, 10))

        # Card Title Header
        header_table = Table([
            [
                Paragraph(f"{tab['badge']} · {tab['tab_num']}", badge_style),
                Paragraph(f"<font color='#64748B'><b>{tab['route']}</b></font>", ParagraphStyle('HRight', parent=badge_style, alignment=2))
            ],
            [
                Paragraph(tab['name'], h1_style),
                Paragraph("<font color='#059669'>System Online & Verified</font>", ParagraphStyle('StatusR', parent=spec_text_style, alignment=2))
            ]
        ], colWidths=[380, 140])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        # Left Column (Text & Capabilities)
        left_items = [
            Paragraph(tab['lead'], body_style),
            Spacer(1, 6),
            Paragraph("Core Capabilities & Operational Features:", section_lbl_style),
            Spacer(1, 3),
        ]
        for cap in tab['capabilities']:
            left_items.append(Paragraph(f"• {cap}", bullet_style))
            left_items.append(Spacer(1, 2.5))

        left_items.append(Spacer(1, 4))
        left_items.append(Paragraph(tab['workflow'], body_style))

        # Right Column (Image + Caption)
        right_items = []
        if os.path.exists(tab['img']):
            img = Image(tab['img'], width=255, height=159)
            right_items.append(img)
            right_items.append(Spacer(1, 4))
            right_items.append(Paragraph(tab['caption'], caption_style))
        else:
            right_items.append(Paragraph("[Screenshot not found]", caption_style))

        # Mid Grid: 2 Columns Side-by-Side
        mid_grid = Table(
            [[left_items, right_items]],
            colWidths=[265, 255]
        )
        mid_grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 8),
            ('LEFTPADDING', (1, 0), (1, 0), 0),
            ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Bottom Bar: Technical Specifications
        spec_box = Table(
            [[
                Paragraph("<b>Technical Architecture & Implementation Details:</b>", spec_hdr_style),
            ],
            [
                Paragraph(tab['specs'], spec_text_style)
            ]],
            colWidths=[520]
        )
        spec_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        # Outer Card encapsulating Header, Mid-Grid, and Spec-Box
        card_contents = [
            header_table,
            Spacer(1, 6),
            mid_grid,
            Spacer(1, 8),
            spec_box
        ]

        outer_card = Table(
            [[card_contents]],
            colWidths=[540]
        )
        outer_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(outer_card)

        if idx < len(tabs) - 1:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated clean PDF with {len(tabs)} tabs at: {output_path}")

def render_pdf_to_images(pdf_path: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    print(f"PDF has {len(doc)} pages.")
    for idx, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_path = os.path.join(output_dir, f"page_{idx+1}.png")
        pix.save(img_path)
        print(f"Saved {img_path}")

if __name__ == '__main__':
    pdf_out = "D:/StockLens/StockLens_Tabs_Overview.pdf"
    pdf_docs = "D:/StockLens/docs/StockLens_Tabs_Overview.pdf"
    build_pdf(pdf_out)
    build_pdf(pdf_docs)
    render_pdf_to_images(pdf_out, "D:/StockLens/docs/screenshots/pdf_pages")
