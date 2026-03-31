import argparse
import asyncio
from playwright.async_api import async_playwright

async def explore_elements(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        elements = await page.query_selector_all("button, a, [role='button']")
        print(f"🔍 Found {len(elements)} interactive elements on {url}:")
        for i, el in enumerate(elements):
            tag = await el.evaluate("node => node.tagName")
            text = await el.inner_text()
            print(f"[{i}] {tag.lower()}: {text.strip() or '[Empty]'}")
        
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find interactive elements on a webpage.")
    parser.add_argument("url", help="URL to explore")
    args = parser.parse_args()
    asyncio.run(explore_elements(args.url))
