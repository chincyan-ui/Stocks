import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: Environment variables missing.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("Fetching data from moomoo...")
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            # 这里的 selector 必须准确
            selector = "table tbody tr"
            await page.wait_for_selector(selector, state="attached", timeout=20000)
            await page.wait_for_timeout(3000)

            rows = await page.query_selector_all(selector)
            msg_lines = ["*📊 Moomoo 美股成交额 Top 3*"]
            
            count = 0
            for row in rows:
                if count >= 3: break
                cells = await row.query_selector_all("td")
                if len(cells) >= 6:
                    name_info = await cells[1].inner_text()
                    turnover = await cells[5].inner_text()
                    clean_name = name_info.replace('\n', ' ').strip()
                    msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                    msg_lines.append(f"💰 成交额: `{turnover}`")
                    count += 1

            if count > 0:
                final_msg = "\n".join(msg_lines)
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                              data={"chat_id": chat_id, "text": final_msg, "parse_mode": "Markdown"})
                print("Push successful.")
            else:
                print("No data found.")

        except Exception as e:
            print(f"Runtime error: {e}")
        finally:
            await browser.close()

# 确保以下两行完整无误
if __name__ == "__main__":
    asyncio.run(fetch_and_push())
