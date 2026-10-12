import asyncio

from playwright.async_api import async_playwright


def test_pdf():
    async def run():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content("<html><body><h1>StockLens report</h1><p>PDF export check</p></body></html>")
            pdf = await page.pdf(format="A4", print_background=True)
            await browser.close()
            assert pdf.startswith(b"%PDF-")

    asyncio.run(run())
