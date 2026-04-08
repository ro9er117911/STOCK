import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def run_screener():
    print("🚀 啟動 Long-only Factor & Liquidity MVP 篩選器...")
    
    # 測試標的: 台股 ETF, 美股大盤 ETF, 與做為對照的個股
    # yfinance 台股代碼需加上 .TW
    tickers = ["VTI", "QQQ", "SPY", "0050.TW", "0056.TW", "2330.TW", "00878.TW"]
    
    results = []
    
    # 計算日期區間 (抓取 7 個月的資料以確保有足夠的 6 個月營業日)
    end_date = datetime.today()
    start_date = end_date - timedelta(days=210)
    
    print(f"📡 正在從 yfinance 抓取股票資料 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})...")
    
    for ticker in tickers:
        try:
            # 獲取資料
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < 130:
                print(f"⚠️ {ticker} 資料不足 (需要至少 ~126 個交易日來計算半年動能)")
                continue

            # 使用一維的數據（因新版 yfinance 可能回傳 MultiIndex）
            if isinstance(data.columns, pd.MultiIndex):
                close_prices = data['Close'][ticker]
                volumes = data['Volume'][ticker]
            else:
                close_prices = data['Close']
                volumes = data['Volume']

            # 計算當前最後一個交易日的價格
            current_price = close_prices.iloc[-1]
            
            # 計算 6 個月前 (約 126 個交易日) 的價格
            price_6m_ago = close_prices.iloc[-126]
            
            # 因子 1: 6 個月動能 (Absolute Momentum)
            momentum_6m = (current_price - price_6m_ago) / price_6m_ago
            
            # 過濾器: 近 20 日均均成交量 (Average Daily Volume)
            avg_volume_20d = volumes.tail(20).mean()
            
            # 設定最低流動性門檻：日均成交 500,000 股 (這個標準根據市場不同應動態調整，MVP 先 hardcode)
            # 為了避免台股與美股股數差異過大導致全部過濾，我們先計算 "日均成交金額 (Dollar Volume)" 作為更公平的比較基準
            # 簡易日均成交金額 (以各自幣別計價，MVP 先不考慮匯率轉換，僅用來展示邏輯)
            avg_dollar_volume = avg_volume_20d * current_price
            
            # 流動性檢查邏輯 (Threshold: 一日成交額至少要超過 1000 萬當地貨幣)
            liquidity_pass = "PASS" if avg_dollar_volume > 10_000_000 else "FAIL"

            results.append({
                "Ticker": ticker,
                "Current Price": round(current_price, 2),
                "6-Month Momentum (%)": round(momentum_6m * 100, 2),
                "20-Day Avg Volume": int(avg_volume_20d),
                "Daily Dollar VOL (Est)": int(avg_dollar_volume),
                "Liquidity Risk": liquidity_pass
            })
            
        except Exception as e:
            print(f"❌ 處理 {ticker} 時發生錯誤: {e}")

    # 轉成 DataFrame 並根據 6 個月動能排序
    df = pd.DataFrame(results)
    df = df.sort_values(by="6-Month Momentum (%)", ascending=False).reset_index(drop=True)
    
    print("\n✅ === MVP 選股篩選報告 ===")
    print("過濾條件: 近 20 日均成交金額 > 10,000,000 (當地貨幣)")
    print("排序基準: 6 個月動能因子 (6-Month Absolute Momentum)\n")
    print(df.to_string())
    print("\n===========================")

if __name__ == "__main__":
    run_screener()
