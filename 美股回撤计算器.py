import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import os

def 获取全量市场数据():
    print("正在拉取全量美股名单...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    response = requests.get(url, headers=headers, timeout=30)
    data = response.json()['data']['rows']
    df_all = pd.DataFrame(data)

    df_all['marketCap'] = df_all['marketCap'].str.replace('$', '').str.replace(',', '').replace('', '0').astype(float)
    df_all['lastsale'] = df_all['lastsale'].str.replace('$', '').str.replace(',', '').replace('', '0').astype(float)

    门槛 = 1000 * 10**8
    筛选后的数据 = df_all[df_all['marketCap'] >= 门槛].copy()
    return 筛选后的数据

def 计算前复权盘中回撤(df):
    结果列表 = []
    代码列表 = df['symbol'].tolist()
    print(f"共有 {len(代码列表)} 家千亿美金公司，开始分析盘中最高价回撤...")

    for index, row in df.iterrows():
        代码 = row['symbol']
        try:
            股票 = yf.Ticker(代码)
            # auto_adjust=True 确保 High 和 Close 都是前复权后的价格
            历史数据 = 股票.history(period="max", auto_adjust=True)
            
            if 历史数据.empty: continue
            
            # --- 核心修改点 ---
            盘中历史最高价 = 历史数据['High'].max() 
            当前价 = 历史数据['Close'].iloc[-1] 
            
            # 计算回撤：(盘中最高 - 当前收盘) / 盘中最高
            回撤幅度 = (盘中历史最高价 - 当前价) / 盘中历史最高价
            
            结果列表.append({
                '股票代码': 代码,
                '公司名称': row['name'],
                '市值(亿美元)': round(row['marketCap'] / 10**8, 2),
                '当前收盘价(前复权)': round(当前价, 2),
                '盘中历史最高价(前复权)': round(盘中历史最高价, 2),
                '距盘中最高回撤幅度': 回撤幅度
            })
        except Exception as e:
            print(f"跳过 {代码}: {e}")
            
    结果表格 = pd.DataFrame(结果列表)
    结果表格 = 结果表格.sort_values(by='距盘中最高回撤幅度', ascending=False)
    结果表格['距盘中最高回撤幅度'] = 结果表格['距盘中最高回撤幅度'].apply(lambda x: f"{round(x * 100, 2)}%")
    
    return 结果表格

if __name__ == "__main__":
    原始数据 = 获取全量市场数据()
    最终表格 = 计算前复权盘中回撤(原始数据)
    
    日期 = datetime.now().strftime('%Y年%m月%d日')
    文件名 = f"美股千亿市值盘中回撤报告_{日期}.xlsx"
    
    最终表格.to_excel(文件名, index=False)
    print(f"成功生成：{文件名}")
