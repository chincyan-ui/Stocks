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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            print("Accessing Moomoo...")
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            row_selector = "table tbody tr"
            await page.wait_for_selector(row_selector, state="attached", timeout=20000)
            await page.wait_for_timeout(5000)

            # 动态识别“成交额”列
            headers = await page.query_selector_all("table thead th")
            turnover_idx = -1
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                if "Turnover" in text or "成交额" in text:
                    turnover_idx = idx
                    break
            
            if turnover_idx == -1:
                turnover_idx = 5 # 备选默认值

            rows = await page.query_selector_all(row_selector)
            msg_lines = ["*📊 Moomoo 美股成交额 Top 3*"]
            
            count = 0
            for row in rows:
                if count >= 3: break
                cells = await row.query_selector_all("td")
                if len(cells) > turnover_idx:
                    name_info = await cells[1].inner_text()
                    turnover_val = await cells[turnover_idx].inner_text()
                    clean_name = name_info.replace('\n', ' ').strip()
                    msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                    msg_lines.append(f"💰 成交额: `{turnover_val}`")
                    count += 1

            if count > 0:
                final_msg = "\n".join(msg_lines)
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                              data={"chat_id": chat_id, "text": final_msg, "parse_mode": "Markdown"})
                print("Push success.")
            else:
                print("No data extracted.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

# 请确保下面这两行没有任何多余的缩进，且完整闭合
if __name__ == "__main__":
    asyncio.run(fetch_and_push())
