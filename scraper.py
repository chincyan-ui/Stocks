import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    # 环境变量获取
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ 错误: 环境变量丢失")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 模拟较宽的屏幕以显示所有列
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1200}
        )
        page = await context.new_page()

        try:
            print("🚀 正在访问 Moomoo 美股成交额榜单...")
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            # 等待表格加载
            row_selector = "table tbody tr"
            await page.wait_for_selector(row_selector, state="attached", timeout=30000)
            
            # 滚动页面以触发前20行的完整加载
            await page.evaluate("window.scrollTo(0, 800)")
            await page.wait_for_timeout(5000) 

            # 动态识别列索引
            headers = await page.query_selector_all("table thead th")
            turnover_idx, mkt_cap_idx = -1, -1
            for idx, header in enumerate(headers):
                text = await header.inner_text()
                if "Turnover" in text or "成交额" in text: turnover_idx = idx
                elif "Market Cap" in text or "市值" in text: mkt_cap_idx = idx

            # 默认值兜底
            turnover_idx = turnover_idx if turnover_idx != -1 else 5
            mkt_cap_idx = mkt_cap_idx if mkt_cap_idx != -1 else 10

            rows = await page.query_selector_all(row_selector)
            msg_lines = [f"*📊 Moomoo 美股成交额 Top 20*"]
            
            count = 0
            for row in rows:
                if count >= 20: break # 修改为 20
                cells = await row.query_selector_all("td")
                
                if len(cells) > max(turnover_idx, mkt_cap_idx):
                    # 提取名称信息并精简（去掉多余空格）
                    raw_name = await cells[1].inner_text()
                    clean_name = " ".join(raw_name.split())
                    
                    turnover_val = (await cells[turnover_idx].inner_text()).strip()
                    mkt_cap_val = (await cells[mkt_cap_idx].inner_text()).strip()
                    
                    # 采用更紧凑的排版以节省空间
                    line = f"{count+1:02d}. *{clean_name}* \n    💰`{turnover_val}` | 💎`{mkt_cap_val}`"
                    msg_lines.append(line)
                    count += 1

            if count > 0:
                final_msg = "\n".join(msg_lines)
                print(f"📤 正在推送 {count} 只股票信息...")
                
                # 发送请求
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {
                    "chat_id": chat_id, 
                    "text": final_msg, 
                    "parse_mode": "Markdown"
                }
                resp = requests.post(url, data=payload)
                
                if resp.status_code == 200:
                    print("✅ 推送成功！")
                else:
                    # 如果消息太长导致 400 错误，这里会打印原因
                    print(f"❌ 推送失败: {resp.text}")
            else:
                print("⚠️ 未抓取到数据")

        except Exception as e:
            print(f"💥 异常: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_and_push())
