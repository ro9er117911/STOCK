import requests
import pandas as pd
from datetime import datetime, timedelta

class FinMindAdapter:
    """
    Adapter for FinMind API to fetch Taiwan stock fundamental and institutional data.
    """
    BASE_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _fetch_data(self, dataset: str, ticker: str, start_date: str):
        params = {
            "dataset": dataset,
            "data_id": ticker,
            "start_date": start_date,
        }
        if self.api_key:
            params["token"] = self.api_key
        
        response = requests.get(self.BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json().get("data", [])
            return pd.DataFrame(data)
        return pd.DataFrame()

    def get_roe(self, ticker: str):
        """
        Fetch ROE by merging TaiwanStockFinancialStatements (IncomeAfterTaxes)
        and TaiwanStockBalanceSheet (Equity).
        Calculates ROE = (IncomeAfterTaxes / Equity) * 100.
        """
        start_date = (datetime.now() - timedelta(days=1000)).strftime("%Y-%m-%d")
        
        # 1. Fetch Income After Taxes
        is_df = self._fetch_data("TaiwanStockFinancialStatements", ticker, start_date)
        if is_df.empty:
            return pd.DataFrame()
        income_df = is_df[is_df['type'] == 'IncomeAfterTaxes'][['date', 'value']]
        income_df.rename(columns={'value': 'net_income'}, inplace=True)
        
        # 2. Fetch Equity
        bs_df = self._fetch_data("TaiwanStockBalanceSheet", ticker, start_date)
        if bs_df.empty:
            return pd.DataFrame()
        equity_df = bs_df[bs_df['type'] == 'Equity'][['date', 'value']]
        equity_df.rename(columns={'value': 'equity'}, inplace=True)
        
        # 3. Merge and Calculate
        merged = pd.merge(income_df, equity_df, on='date')
        if not merged.empty:
            merged['ROE'] = (merged['net_income'] / merged['equity']) * 100
            return merged[['date', 'ROE']].sort_values('date', ascending=False)
        
        return pd.DataFrame()

    def get_institutional_investors(self, ticker: str):
        """
        Fetch TaiwanStockInstitutionalInvestorsBuySell (三大法人買賣超).
        """
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        df = self._fetch_data("TaiwanStockInstitutionalInvestorsBuySell", ticker, start_date)
        if not df.empty:
            # Calculate net buy/sell if 'diff' is missing
            if 'diff' not in df.columns and 'buy' in df.columns and 'sell' in df.columns:
                df['diff'] = df['buy'] - df['sell']
            
            if 'diff' in df.columns:
                summary = df.groupby('date')['diff'].sum().reset_index()
                return summary.sort_values('date', ascending=False)
        return pd.DataFrame()

if __name__ == "__main__":
    # Quick test for 2330
    adapter = FinMindAdapter()
    print("Testing FinMind ROE for 2330...")
    roe = adapter.get_roe("2330")
    if not roe.empty:
        print(roe.head())
    else:
        print("⚠️ No ROE data found for 2330.")
    
    print("\nTesting Institutional Flows for 2330...")
    flows = adapter.get_institutional_investors("2330")
    if not flows.empty:
        print(flows.head())
    else:
        print("⚠️ No institutional flow data found for 2330.")
