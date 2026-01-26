import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
import time

def 获取全量并合并特定标的():
    print("正在拉取全量美股名单及特定标的...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=0&download=true"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()['data']['rows']
        df_all = pd.DataFrame(data)
        df_all['marketCap'] = df_all['marketCap'].str.replace('$', '', regex=False).str.replace(',', '', regex=False).replace('', '0').astype(float)
        门槛 = 1000 * 10**8
        api_symbols = df_all[df_all['marketCap'] >= 门槛]['symbol'].tolist()
    except Exception as e:
        print(f"Nasdaq API 访问受限: {e}")
        api_symbols = []

    指定标的字符串 = "AAPL, ABNB, ADBE, ADI, ADP, ADSK, AEP, ALNY, AMAT, AMD, AMGN, AMZN, APP, ARM, ASML, AVGO, AXON, BKNG, BKR, CCEP, CDNS, CEG, CHTR, CMCSA, COST, CPRT, CRWD, CSCO, CSGP, CSX, CTAS, CTSH, DASH, DDOG, DXCM, EA, EXC, FANG, FAST, FER, FTNT, GEHC, GILD, GOOG, GOOGL, HON, IDXX, INSM, INTC, INTU, ISRG, KDP, KHC, KLAC, LIN, LRCX, MAR, MCHP, MDLZ, MELI, META, MNST, MPWR, MRVL, MSFT, MSTR, MU, NFLX, NVDA, NXPI, ODFL, ORLY, PANW, PAYX, PCAR, PDD, PEP, PLTR, PYPL, QCOM, REGN, ROP, ROST, SBUX, SHOP, SNPS, STX, TEAM, TMUS, TRI, TSLA, TTWO, TXN, VRSK, VRTX, WBD, WDAY, WDC, WMT, XEL, ZS"
    custom_symbols = [s.strip() for s in 指定标的字符串.split(',')]
    
    新面孔列表 = ["ALNY", "FER", "INSM", "MPWR", "STX", "WDC", "PLTR", "MSTR", "AXON"]
    最终名单 = list(set(api_symbols + custom_symbols))
    return 最终名单, 新面孔列表

def 计算分析(代码列表, 新面孔列表):
    结果列表 = []
    print(f"总计分析 {len(代码列表)} 个标的...")

    for 代码 in 代码列表:
        try:
            股票 = yf.Ticker(代码)
            # 获取最大历史数据
            历史数据 = 股票.history(period="max", auto_adjust=True)
            if 历史数据.empty: continue
            
            info = 股票.info
            盘中最高 = 历史数据['High'].max()
            当前价 = 历史数据['Close'].iloc[-1]
            回撤 = (盘中最高 - 当前价) / 盘中最高
            
            # 组织数据，调整字段顺序，将“距最高回撤”前置
            结果列表.append({
                '距最高回撤': 回撤,  # 移动到第一列
                '股票代码': 代码,
                '状态': "新纳入" if 代码 in 新面孔列表 else "常规",
                '公司名称': info.get('longName', 代码),
                '市值(亿美元)': round(info.get('marketCap', 0) / 10**8, 2) if info.get('marketCap') else 0,
                '当前价': round(当前价, 2),
                '历史最高': round(盘中最高, 2)
            })
            # 稍微休眠防止被 Yahoo 封禁
            time.sleep(0.1) 
        except Exception as e:
            print(f"分析失败 {代码}: {e}")
            
    df = pd.DataFrame(结果列表).sort_values(by='距最高回撤', ascending=False)
    return df

def 导出Excel(df, 文件名):
    # 使用 Styler 格式化百分比并添加高亮
    def highlight_new(row):
        return ['background-color: #FFFF00' if row['状态'] == '新纳入' else '' for _ in row]

    # 导出
    with pd.ExcelWriter(文件名, engine='openpyxl') as writer:
        df.style.apply(highlight_new, axis=1)\
                .format({'距最高回撤': '{:.2%}'})\
                .to_excel(writer, index=False)
    print(f"报告已生成: {文件名}")

if __name__ == "__main__":
    名单, 新面孔 = 获取全量并合并特定标的()
    最终数据 = 计算分析(名单, 新面孔)
    
    # 文件名建议固定或带日期，方便 GitHub 提交
    文件名 = "US_Stock_Drawdown_Report.xlsx"
    导出Excel(最终数据, 文件名)
