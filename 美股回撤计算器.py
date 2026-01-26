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
    # Nasdaq 官方接口
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    response = requests.get(url, headers=headers, timeout=30)
    data = response.json()['data']['rows']
    df_all = pd.DataFrame(data)

    # 清理格式并转换为数值
    df_all['marketCap'] = df_all['marketCap'].str.replace('$', '').str.replace(',', '').replace('', '0').astype(float)
    df_all['lastsale'] = df_all['lastsale'].str.replace('$', '').str.replace(',', '').replace('', '0').astype(float)

    # 1. 筛选市值 > 1000 亿美元
    门槛 = 1000 * 10**8
    筛选后的数据 = df_all[df_all['marketCap'] >= 门槛].copy()
    return 筛选后的数据

def 计算前复权回撤(df):
    结果列表 = []
    代码列表 = df['symbol'].tolist()
    print(f"共有 {len(代码列表)} 家千亿美金公司，开始分析...")

    for index, row in df.iterrows():
        代码 = row['symbol']
        try:
            # 2. auto_adjust=True 实现前复权计算
            股票 = yf.Ticker(代码)
            历史数据 = 股票.history(period="max", auto_adjust=True)
            
            if 历史数据.empty: continue
            
            历史最高价 = 历史数据['Close'].max() 
            当前价 = 历史数据['Close'].iloc[-1] 
            
            # 3. 回撤公式
            回撤幅度 = (历史最高价 - 当前价) / 历史最高价
            
            结果列表.append({
                '股票代码': 代码,
                '公司名称': row['name'],
                '市值(亿美元)': round(row['marketCap'] / 10**8, 2),
                '当前价(前复权)': round(当前价, 2),
                '历史最高价(前复权)': round(历史最高价, 2),
                '距最高点回撤幅度': 回撤幅度
            })
        except Exception as e:
            print(f"跳过 {代码}: {e}")
            
    # 4. 按回撤幅度降序排列
    结果表格 = pd.DataFrame(结果列表)
    结果表格 = 结果表格.sort_values(by='距最高点回撤幅度', ascending=False)
    
    # 转换为百分比格式
    结果表格['距最高点回撤幅度'] = 结果表格['距最高点回撤幅度'].apply(lambda x: f"{round(x * 100, 2)}%")
    
    return 结果表格

if __name__ == "__main__":
    原始数据 = 获取全量市场数据()
    最终表格 = 计算前复权回撤(原始数据)
    
    # 中文文件名保存
    日期 = datetime.now().strftime('%Y年%m月%d日')
    文件名 = f"美股千亿市值回撤报告_{日期}.xlsx"
    
    最终表格.to_excel(文件名, index=False)
    print(f"成功生成：{文件名}")
