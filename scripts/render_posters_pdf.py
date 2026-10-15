import os
import sys
from playwright.sync_api import sync_playwright

def generate_pdf():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(script_dir, "posters.html")
    output_pdf = os.path.join(script_dir, "StockLens_Exhibition_Posters.pdf")
    
    file_url = f"file:///{html_file.replace(os.sep, '/')}"
    print(f"Loading {file_url}...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1697})
        page.goto(file_url, wait_until="networkidle")
        # Ensure webfonts are loaded
        page.evaluate("() => document.fonts.ready")
        
        print("Rendering print-ready PDF...")
        page.pdf(
            path=output_pdf,
            width="1200px",
            height="1697px",
            print_background=True,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
        )
        browser.close()
        
    print(f"Successfully generated: {output_pdf}")
    if os.path.exists(output_pdf):
        print(f"File size: {os.path.getsize(output_pdf) / 1024:.2f} KB")

if __name__ == "__main__":
    generate_pdf()
