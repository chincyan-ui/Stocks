import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    # 从环境变量获取配置
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ 错误: 环境变量 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID 未设置")
        return

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            print("🚀 正在访问 Moomoo 美股榜单...")
            # 访问成交额榜单页
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            # 使用 attached 状态避免可见性判断导致的超时
            row_selector = "table tbody tr"
            await page.wait_for_selector(row_selector, state="attached", timeout=30000)
            
            # 模拟微量滚动并等待渲染
            await page.evaluate("window.scrollTo(0, 300)")
            await page.wait_for_timeout(5000) 

            # --- 动态识别列索引 ---
            headers = await page.query_selector_all("table thead th")
            turnover_idx = -1
            mkt_cap_idx = -1
            
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                if "Turnover" in text or "成交额" in text:
                    turnover_idx = idx
                elif "Market Cap" in text or "市值" in text:
                    mkt_cap_idx = idx

            print(f"DEBUG: 成交额列索引={turnover_idx}, 市值列索引={mkt_cap_idx}")

            # 备选默认值（以防表头识别失败）
            if turnover_idx == -1: turnover_idx = 5
            if mkt_cap_idx == -1: mkt_cap_idx = 10

            # 获取所有行
            rows = await page.query_selector_all(row_selector)
            msg_lines = ["*📊 Moomoo 美股成交额 Top 5*"]
            
            count = 0
            for row in rows:
                if count >= 5: break
                cells = await row.query_selector_all("td")
                
                if len(cells) > max(turnover_idx, mkt_cap_idx):
                    # 1. 提取名称和代码
                    name_info = await cells[1].inner_text()
                    clean_name = " ".join(name_info.split()) 
                    
                    # 2. 提取成交额
                    turnover_val = await cells[turnover_idx].inner_text()
                    
                    # 3. 提取市值
                    mkt_cap_val = await cells[mkt_cap_idx].inner_text()
                    
                    msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                    msg_lines.append(f"💰 成交额: `{turnover_val.strip()}`")
                    msg_lines.append(f"💎 市值: `{mkt_cap_val.strip()}`")
                    count += 1

            if count > 0:
                final_msg = "\n".join(msg_lines)
                print("📤 正在推送至 Telegram...")
                payload = {
                    "chat_id": chat_id, 
                    "text": final_msg, 
                    "parse_mode": "Markdown"
                }
                resp = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
                if resp.status_code == 200:
                    print("✅ 推送成功！")
                else:
                    print(f"❌ 推送失败: {resp.text}")
            else:
                print("⚠️ 未能提取到有效数据。")

        except Exception as e:
            print(f"💥 运行中出错: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_and_push())
