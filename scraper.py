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
        # 增加 slow_mo 确保页面渲染稳定
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            print("Accessing Moomoo...")
            # 访问成交额排行页
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="networkidle", timeout=60000)
            
            # 等待表格主体加载
            await page.wait_for_selector("table tbody tr", timeout=30000)
            # 额外等待，防止数据还在跳动
            await page.wait_for_timeout(3000)

            # 获取所有行
            rows = await page.query_selector_all("table tbody tr")
            msg_lines = ["*🚀 Moomoo 美股成交额 Top 5*"]
            
            count = 0
            for row in rows:
                if count >= 5: break
                
                # 获取该行所有单元格
                cells = await row.query_selector_all("td")
                if len(cells) < 5: continue

                # --- 核心改进：精准提取 ---
                # 1. 提取名称和代码 (通常在第2列)
                name_text = await cells[1].inner_text()
                clean_name = " ".join(name_text.split()) # 清理多余换行符

                # 2. 提取成交额 (Turnover)
                # 遍历所有单元格，寻找带有“B”或“M”单位且在成交额大致位置的数值
                # 或者直接锁定 Moomoo 常规的第 6 列 (index 5)
                turnover_val = await cells[5].inner_text() 
                
                # 3. 提取市值 (Market Cap) - 通常在第 11 列 (index 10)
                # 如果市值数据也需要，可以取消下面注释
                # mkt_cap_val = await cells[10].inner_text()

                msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                msg_lines.append(f"💰 成交额: `{turnover_val.strip()}`")
                # msg_lines.append(f"💎 市值: `{mkt_cap_val.strip()}`")
                
                count += 1

            if count > 0:
                final_msg = "\n".join(msg_lines)
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage", 
                    data={"chat_id": chat_id, "text": final_msg, "parse_mode": "Markdown"}
                )
                print(f"Push success. Sent {count} stocks.")
            else:
                print("No data extracted. Selector might have changed.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_and_push())
