import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    # 从 GitHub Secrets 环境遍历中获取配置
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("错误: 未配置 TELEGRAM_TOKEN 或 TELEGRAM_CHAT_ID")
        return

    async with async_playwright() as p:
        # 1. 启动浏览器并配置伪装
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        print("正在打开 moomoo 成交额排行页...")
        try:
            # 2. 访问页面并设置较长的超时
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            # 3. 关键修复：使用 state='attached' 避免因元素“隐藏”导致的超时
            # 同时等待特定的表格行出现
            selector = "table tbody tr"
            await page.wait_for_selector(selector, state="attached", timeout=20000)
            
            # 额外等待 3 秒，确保 JavaScript 将具体数值填充到单元格中
            await page.wait_for_timeout(3000)

            # 4. 提取前 3 行数据
            rows = await page.query_selector_all(selector)
            
            msg_lines = ["*📊 Moomoo 美股成交额 Top 3*"]
            count = 0
            
            for row in rows:
                if count >= 3: break
                
                cells = await row.query_selector_all("td")
                # moomoo 页面通常：Index 1 为名称/代码，Index 5 为成交额
                if len(cells) >= 6:
                    name_info = await cells[1].inner_text()
                    turnover = await cells[5].inner_text()
                    
                    # 格式化处理：将换行替换为空格
                    clean_name = name_info.replace('\n', ' ').strip()
                    msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                    msg_lines.append(f"💰 成交额: `{turnover}`")
                    count += 1

            if count == 0:
                print("未提取到有效数据，请检查网页结构是否变化。")
                return

            # 5. 推送至 Telegram
            final_msg = "\n".join(msg_lines)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            response = requests.post(url, data={
                "chat_id": chat_id, 
                "text": final_msg, 
                "parse_mode": "Markdown"
            })
            
            if response.status_code == 200:
                print("推送成功！")
            else:
                print(f"推送失败: {response.text}")

        except Exception as e:
            print(
