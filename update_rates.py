import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
import os

# 設定：今天的日期 (由系統自動抓取，確保是 2026-01-06 或當下日期)
end_date = datetime.now()
start_date = end_date - timedelta(days=1825) # 五年歷史

# 定義需要的基礎貨幣對 (Yahoo Finance 代號)
# 邏輯：所有交叉匯率都可以透過 USD 推算
tickers = {
    "USDTWD": "TWD=X",  # 美金 -> 台幣
    "USDLKR": "LKR=X",  # 美金 -> 斯里蘭卡盧比
    "USDCNY": "CNY=X",  # 美金 -> 人民幣
    "USDJPY": "JPY=X"   # 美金 -> 日幣
}

def get_data():
    print(f"正在抓取數據... ({start_date.date()} ~ {end_date.date()})")
    data_store = {}
    
    # 1. 下載基礎數據
    raw_data = {}
    for key, symbol in tickers.items():
        try:
            # 下載歷史數據
            ticker = yf.Ticker(symbol)
            # auto_adjust=False 確保獲取原始收盤價
            df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
            df.reset_index(inplace=True)
            # 統一日期格式
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
            # 只留日期和收盤價，並重新命名
            raw_data[key] = df[['Date', 'Close']].set_index('Date')
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            return None

    # 確保所有數據的日期對齊 (取交集)
    common_index = raw_data["USDTWD"].index
    for key in raw_data:
        common_index = common_index.intersection(raw_data[key].index)
    
    # 對齊數據
    aligned_data = {k: v.loc[common_index] for k, v in raw_data.items()}
    
    # 2. 計算使用者指定的交叉匯率
    # 將 DataFrame 轉為數值便於計算
    usd_twd = aligned_data["USDTWD"]['Close']
    usd_lkr = aligned_data["USDLKR"]['Close']
    usd_cny = aligned_data["USDCNY"]['Close']
    usd_jpy = aligned_data["USDJPY"]['Close']

    # 定義輸出格式的函數
    def format_pair_history(series, name):
        history = []
        for date, price in series.items():
            history.append({"date": date, "value": round(float(price), 4)})
        return {
            "name": name,
            "current_rate": round(float(series.iloc[-1]), 4),
            "history": history
        }

    pairs_data = []

    # --- Group 1: 美金相關 ---
    pairs_data.append(format_pair_history(usd_twd, "美金 / 台幣 (USD/TWD)"))
    pairs_data.append(format_pair_history(usd_lkr, "美金 / 斯里蘭卡盧比 (USD/LKR)"))
    
    # --- Group 2: 美金/台幣 兌 人民幣 ---
    pairs_data.append(format_pair_history(usd_cny, "美金 / 人民幣 (USD/CNY)"))
    # 台幣兌人民幣 = (USD/CNY) / (USD/TWD) -> 1台幣換多少人民幣
    # 這裡依照慣例，通常顯示 TWD/CNY (1台幣換多少CNY) 或 CNY/TWD (1人民幣換多少台幣)
    # 根據您的描述「台幣兌人民幣」，計算 TWD -> CNY
    twd_to_cny = usd_cny / usd_twd
    pairs_data.append(format_pair_history(twd_to_cny, "台幣 / 人民幣 (TWD/CNY)"))

    # --- Group 3: 人民幣 兌 美金/台幣 ---
    # 人民幣兌美金 = 1 / (USD/CNY)
    cny_to_usd = 1 / usd_cny
    pairs_data.append(format_pair_history(cny_to_usd, "人民幣 / 美金 (CNY/USD)"))
    # 人民幣兌台幣 = (USD/TWD) / (USD/CNY)
    cny_to_twd = usd_twd / usd_cny
    pairs_data.append(format_pair_history(cny_to_twd, "人民幣 / 台幣 (CNY/TWD)"))

    # --- Group 4: 美金/台幣 兌 日幣 ---
    pairs_data.append(format_pair_history(usd_jpy, "美金 / 日幣 (USD/JPY)"))
    # 台幣兌日幣 = (USD/JPY) / (USD/TWD)
    twd_to_jpy = usd_jpy / usd_twd
    pairs_data.append(format_pair_history(twd_to_jpy, "台幣 / 日幣 (TWD/JPY)"))

    # 3. 生成最終 JSON
    output = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": pairs_data
    }
    
    return output

if __name__ == "__main__":
    data = get_data()
    if data:
        with open("rates_data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("成功生成 rates_data.json")


