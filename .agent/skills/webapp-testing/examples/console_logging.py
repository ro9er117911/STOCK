import argparse
import asyncio
from playwright.async_api import async_playwright

async def monitor_console(url, duration=60):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        page.on("console", lambda msg: print(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: print(f"❌ Error: {exc}"))

        await page.goto(url)
        print(f"📡 Monitoring {url} for {duration} seconds...")
        await asyncio.sleep(duration)
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a page for console logs and errors.")
    parser.add_argument("url", help="URL to monitor")
    parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    args = parser.parse_args()
    asyncio.run(monitor_console(args.url, args.duration))
