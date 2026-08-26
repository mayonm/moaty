"""
Download historical stock prices for the company universe.

Uses yfinance to download daily adjusted close prices.
"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timedelta
import time


def download_prices_batch(
    tickers: List[str],
    start_date: str = "2016-01-01",
    end_date: str = None,
    batch_size: int = 50
) -> pd.DataFrame:
    """
    Download prices for a list of tickers in batches.
    
    Returns DataFrame with columns: ticker, date, close
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    all_prices = []
    failed_tickers = []
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_str = " ".join(batch)
        
        print(f"Downloading batch {i // batch_size + 1}/{(len(tickers) + batch_size - 1) // batch_size}: {len(batch)} tickers")
        
        try:
            data = yf.download(
                batch_str,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                progress=False,
                threads=True
            )
            
            if len(batch) == 1:
                if "Close" in data.columns:
                    df = data[["Close"]].copy()
                    df = df.reset_index()
                    df.columns = ["date", "close"]
                    df["ticker"] = batch[0]
                    all_prices.append(df)
            else:
                if "Close" in data.columns:
                    close_data = data["Close"]
                    
                    for ticker in batch:
                        if ticker in close_data.columns:
                            ticker_data = close_data[[ticker]].dropna().reset_index()
                            ticker_data.columns = ["date", "close"]
                            ticker_data["ticker"] = ticker
                            all_prices.append(ticker_data)
                        else:
                            failed_tickers.append(ticker)
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error downloading batch: {e}")
            failed_tickers.extend(batch)
    
    if failed_tickers:
        print(f"\nFailed to download: {len(failed_tickers)} tickers")
        print(f"  {failed_tickers[:10]}{'...' if len(failed_tickers) > 10 else ''}")
    
    if all_prices:
        prices_df = pd.concat(all_prices, ignore_index=True)
        prices_df["date"] = pd.to_datetime(prices_df["date"])
        prices_df = prices_df[["ticker", "date", "close"]]
        return prices_df
    
    return pd.DataFrame(columns=["ticker", "date", "close"])


def download_prices_for_universe(
    universe_df: pd.DataFrame,
    start_date: str = "2016-01-01"
) -> pd.DataFrame:
    """
    Download prices for all companies in the universe DataFrame.
    
    Expects universe_df to have a 'ticker' column.
    """
    tickers = universe_df["ticker"].dropna().unique().tolist()
    tickers = [t for t in tickers if not t.startswith("CIK")]
    
    print(f"Downloading prices for {len(tickers)} tickers...")
    
    prices = download_prices_batch(tickers, start_date=start_date)
    
    print(f"\nDownloaded {len(prices)} price records for {prices['ticker'].nunique()} tickers")
    
    return prices


if __name__ == "__main__":
    sample_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    prices = download_prices_batch(sample_tickers, start_date="2020-01-01")
    print(f"\nDownloaded {len(prices)} records")
    print(prices.head())
