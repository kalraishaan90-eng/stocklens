import asyncio
import os
import sys

import pytest

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.schemas import AnalyzeRequest, ReportRequest
from app.main import analyze_stocks, download_report_pdf, export_template_csv, export_sheets_csv

@pytest.mark.asyncio
async def test_report_pipeline():
    print("=== Testing StockLens Report Pipeline ===")
    req = ReportRequest(
        company_a="HAL",
        company_b="Mazagon Dock",
        student_name="Test Student",
        roll_number="ROLL-12345",
        theme="dark",
        use_offline_demo=True
    )

    print("1. Generating Dark PDF Report...")
    resp_dark = await download_report_pdf(req)
    assert resp_dark.status_code == 200
    pdf_bytes_dark = resp_dark.body
    print(f"   Dark PDF generated! Size: {len(pdf_bytes_dark)} bytes")
    assert len(pdf_bytes_dark) > 10000

    print("2. Generating Light-Ink PDF Report...")
    req.theme = "light"
    resp_light = await download_report_pdf(req)
    assert resp_light.status_code == 200
    pdf_bytes_light = resp_light.body
    print(f"   Light-Ink PDF generated! Size: {len(pdf_bytes_light)} bytes")
    assert len(pdf_bytes_light) > 10000

    print("3. Generating Template CSV...")
    csv_resp = await export_template_csv(company_a="HAL", company_b="Mazagon Dock", use_offline_demo=True)
    csv_content = csv_resp.body.decode("utf-8")
    print(f"   CSV generated! Lines: {len(csv_content.splitlines())}")
    assert "Month-Year" in csv_content
    assert "HAL" in csv_content

    print("4. Generating Google Sheets CSV...")
    sheets_resp = await export_sheets_csv(company_a="HAL", company_b="Mazagon Dock", use_offline_demo=True)
    sheets_content = sheets_resp.body.decode("utf-8")
    print(f"   Sheets CSV generated! Lines: {len(sheets_content.splitlines())}")
    assert "GOOGLEFINANCE" in sheets_content
    assert "=AVERAGE" in sheets_content

    print("=== All Report Tests Passed! ===")

if __name__ == "__main__":
    asyncio.run(test_report_pipeline())
