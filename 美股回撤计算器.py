import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import time
import os

def 获取全量并合并特定标的():
    print("正在拉取全量美股名单及特定标的...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    
    api_symbols = []
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()['data']['rows']
        df_all = pd.DataFrame(data)
        # 清洗市值数据
        df_all['marketCap'] = df_all['marketCap'].str.replace('$', '', regex=False).str.replace(',', '', regex=False).replace('', '0').astype(float)
        # 筛选千亿美金市值
        门槛 = 1000 * 10**8
        api_symbols = df_all[df_all['marketCap'] >= 门槛]['symbol'].tolist()
        print(f"Nasdaq API 扫描到 {len(api_symbols)} 家千亿市值公司")
    except Exception as e:
        print(f"Nasdaq API 获取失败（通常是触发了反爬），仅使用内置列表。错误: {e}")

    # 特定标的（主要为纳指100成分股）
    指定标的字符串 = "AAPL, ABNB, ADBE, ADI, ADP, ADSK, AEP, ALNY, AMAT, AMD, AMGN, AMZN, APP, ARM, ASML, AVGO, AXON, BKNG, BKR, CCEP, CDNS, CEG, CHTR, CMCSA, COST, CPRT, CRWD, CSCO, CSGP, CSX, CTAS, CTSH, DASH, DDOG, DXCM, EA, EXC, FANG, FAST, FER, FTNT, GEHC, GILD, GOOG, GOOGL, HON, IDXX, INSM, INTC, INTU, ISRG, KDP, KHC, KLAC, LIN, LRCX, MAR, MCHP, MDLZ, MELI, META, MNST, MPWR, MRVL, MSFT, MSTR, MU, NFLX, NVDA, NXPI, ODFL, ORLY, PANW, PAYX, PCAR, PDD, PEP, PLTR, PYPL, QCOM, REGN, ROP, ROST, SBUX, SHOP, SNPS, STX, TEAM, TMUS, TRI, TSLA, TTWO, TXN, VRSK, VRTX, WBD, WDAY, WDC, WMT, XEL, ZS"
    custom_symbols = [s.strip() for s in 指定标的字符串.split(',')]
    
    # 定义“新面孔” (2024-2025新纳入成分股)
    新面孔列表 = ["ALNY", "FER", "INSM", "MPWR", "STX", "WDC", "PLTR", "MSTR", "AXON"]
    
    最终名单 = list(set(api_symbols + custom_symbols))
    return 最终名单, 新面孔列表

def 计算分析(代码列表, 新面孔列表):
    结果列表 = []
    total = len(代码列表)
    print(f"开始分析共 {total} 个标的的价格回撤...")

    for i, 代码 in enumerate(代码列表):
        try:
            print(f"[{i+1}/{total}] 正在抓取: {代码}")
            股票 = yf.Ticker(代码)
            # 抓取所有历史数据
            历史数据 = 股票.history(
