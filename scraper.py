import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", wait_until="networkidle")
        
        await page.wait_for_selector("table tbody tr")
        rows = await page.query_selector_all("table tbody tr")
        
        msg_lines = ["*📊 Moomoo 美股成交额 Top 3* \n"]
        for i, row in enumerate(rows[:3]):
            cells = await row.query_selector_all("td")
            if len(cells) >= 6:
                name_info = await cells[1].inner_text()
                turnover = await cells[5].inner_text()
                msg_lines.append(f"{i+1}️⃣ *{name_info.replace(chr(10), ' ')}* \n💰 成交额: `{turnover}`\n")
        
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      data={"chat_id": chat_id, "text": "\n".join(msg_lines), "parse_mode": "Markdown"})
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_and_push())
