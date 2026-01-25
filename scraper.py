import asyncio
import os
import requests
from playwright.async_api import async_playwright

async def fetch_and_push():
    # 获取 GitHub Secrets
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: Environment variables missing.")
        return

    async with async_playwright() as p:
        # 1. 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            print("正在访问 Moomoo 排行榜...")
            # 访问成交额排行页
            await page.goto("https://www.moomoo.com/quote/us/stock-list/all-us-stocks/top-turnover", 
                            wait_until="domcontentloaded", timeout=60000)
            
            # 2. 等待表格加载
            table_selector = "table"
            row_selector = "table tbody tr"
            await page.wait_for_selector(row_selector, state="attached", timeout=20000)
            
            # 给 JS 一点时间渲染具体数值
            await page.wait_for_timeout(5000)

            # 3. 【核心逻辑】动态定位“成交额”列索引
            headers = await page.query_selector_all("table thead th")
            turnover_idx = -1
            
            for idx, header in enumerate(headers):
                header_text = await header.inner_text()
                # 兼容中英文表头
                if "Turnover" in header_text or "成交额" in header_text:
                    turnover_idx = idx
                    print(f"找到成交额列，索引为: {turnover_idx}")
                    break
            
            # 如果没找到，默认回退到第 6 列 (index 5)
            if turnover_idx == -1:
                turnover_idx = 5
                print("未匹配到表头，使用默认索引 5")

            # 4. 抓取前 3 行数据
            rows = await page.query_selector_all(row_selector)
            msg_lines = ["*📊 Moomoo 美股成交额 Top 3*"]
            
            count = 0
            for row in rows:
                if count >= 3: break
                cells = await row.query_selector_all("td")
                
                if len(cells) > turnover_idx:
                    # Index 1 通常是股票代码和名称
                    name_info = await cells[1].inner_text()
                    # 使用动态找到的 turnover_idx
                    turnover_value = await cells[turnover_idx].inner_text()
                    
                    # 格式化文本
                    clean_name = name_info.replace('\n', ' ').strip()
                    msg_lines.append(f"\n{count+1}️⃣ *{clean_name}*")
                    msg_lines.append(f"💰 成交额: `{turnover_value}`")
                    count
