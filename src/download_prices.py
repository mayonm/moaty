"""
Stock Price Data Downloader

Downloads historical stock prices for companies in our fundamentals dataset
using yfinance API. Uses batch downloading with rate limiting.
"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from typing import List, Optional
import time

DATA_DIR = Path(__file__).parent.parent / "data"


def get_tickers_from_fundamentals() -> List[str]:
    """Get list of tickers from fundamentals data."""
    fundamentals_path = DATA_DIR / "fundamentals.csv"
    if not fundamentals_path.exists():
        raise FileNotFoundError("fundamentals.csv not found. Run parse_fundamentals.py first.")
    
    df = pd.read_csv(fundamentals_path)
    tickers = df['ticker'].dropna().unique().tolist()
    # Filter out empty strings and invalid tickers
    tickers = [t for t in tickers if t and len(t) <= 5 and t.replace('.', '').isalpha()]
    return sorted(set(tickers))


def download_batch_prices(tickers: List[str], start_date: str = "2017-01-01", 
                          end_date: str = "2026-12-31") -> pd.DataFrame:
    """
    Download price data for a batch of tickers using yfinance batch API.
    This is more efficient and rate-limit friendly.
    """
    try:
        # yfinance can download multiple tickers at once
        ticker_str = " ".join(tickers)
        data = yf.download(ticker_str, start=start_date, end=end_date, 
                           auto_adjust=True, progress=False, threads=True)
        
        if data.empty:
            return pd.DataFrame()
        
        # Handle single vs multiple ticker response format
        if len(tickers) == 1:
            df = data[['Close']].reset_index()
            df.columns = ['date', 'close_price']
            df['ticker'] = tickers[0]
        else:
            # Multi-ticker format has MultiIndex columns
            close_prices = data['Close']
            df = close_prices.reset_index().melt(
                id_vars=['Date'], 
                var_name='ticker', 
                value_name='close_price'
            )
            df.columns = ['date', 'ticker', 'close_price']
        
        # Clean up
        df = df.dropna(subset=['close_price'])
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        return df
        
    except Exception as e:
        print(f"  Error in batch download: {e}")
        return pd.DataFrame()


def download_all_prices(tickers: List[str], batch_size: int = 20) -> pd.DataFrame:
    """
    Download price data for all tickers in batches.
    """
    all_prices = []
    successful_tickers = set()
    
    print(f"Downloading prices for {len(tickers)} tickers in batches of {batch_size}...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tickers) - 1) // batch_size + 1
        
        print(f"  Batch {batch_num}/{total_batches}: {len(batch)} tickers...")
        
        # Retry logic
        for attempt in range(3):
            try:
                df = download_batch_prices(batch)
                if not df.empty:
                    all_prices.append(df)
                    successful_tickers.update(df['ticker'].unique())
                break
            except Exception as e:
                if attempt < 2:
                    print(f"    Retry {attempt + 1} after error: {e}")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"    Failed batch after 3 attempts: {e}")
        
        # Rate limiting pause between batches
        time.sleep(2)
    
    if not all_prices:
        raise ValueError("No price data downloaded")
    
    combined = pd.concat(all_prices, ignore_index=True)
    
    print(f"\nDownloaded prices for {len(successful_tickers)} tickers")
    print(f"Total price observations: {len(combined)}")
    if len(combined) > 0:
        print(f"Date range: {combined['date'].min()} to {combined['date'].max()}")
    
    return combined


def download_sp500_prices(start_date: str = "2017-01-01", 
                          end_date: str = "2026-12-31") -> pd.DataFrame:
    """Download S&P 500 index prices for benchmark comparison."""
    print("Downloading S&P 500 index prices...")
    
    data = yf.download("SPY", start=start_date, end=end_date, 
                       auto_adjust=True, progress=False)
    
    if data.empty:
        raise ValueError("Could not download S&P 500 data")
    
    df = data[['Close']].reset_index()
    df.columns = ['date', 'close_price']
    df['ticker'] = 'SPY'
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    print(f"Downloaded {len(df)} days of S&P 500 data")
    return df


if __name__ == "__main__":
    # Get tickers from fundamentals
    tickers = get_tickers_from_fundamentals()
    print(f"Found {len(tickers)} tickers in fundamentals data")
    
    # Limit to reasonable number for demo
    # Full dataset would be all tickers
    if len(tickers) > 500:
        print(f"Limiting to first 500 tickers for efficiency...")
        tickers = tickers[:500]
    
    # Download prices
    prices = download_all_prices(tickers)
    
    # Add S&P 500 benchmark
    sp500 = download_sp500_prices()
    prices = pd.concat([prices, sp500], ignore_index=True)
    
    # Save to CSV
    output_path = DATA_DIR / "prices.csv"
    prices.to_csv(output_path, index=False)
    print(f"\nSaved prices to {output_path}")
