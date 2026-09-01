"""
Moaty Forecasts Generator

Generates 5-year and 10-year ROIC forecasts using fitted decay parameters.
- Base case: Pure extrapolation of fitted decay curve
- Disruption scenario: λ × 1.5 stress multiplier (faster erosion)
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "moaty.db"

# Configuration
DISRUPTION_MULTIPLIER = 1.5  # Stress factor for λ
FORECAST_HORIZONS = [5, 10]  # Years to forecast


def decay_model(t: float, roic_0: float, lambda_: float, roic_terminal: float) -> float:
    """
    Exponential decay model for ROIC.
    ROIC(t) = ROIC_terminal + (ROIC_0 - ROIC_terminal) × e^(-λt)
    """
    return roic_terminal + (roic_0 - roic_terminal) * np.exp(-lambda_ * t)


def generate_forecasts():
    """Generate forecasts for all companies with valid fits."""
    print(f"Generating forecasts from {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get decay fits
    fits = pd.read_sql_query("""
        SELECT cik, ticker, lambda, roic_0, roic_terminal, n_periods
        FROM decay_fits
        WHERE converged = 1 AND lambda IS NOT NULL
    """, conn)
    
    print(f"Generating forecasts for {len(fits)} companies...")
    
    forecasts = []
    
    for _, row in fits.iterrows():
        cik = row['cik']
        ticker = row['ticker']
        lambda_ = row['lambda']
        roic_0 = row['roic_0']
        roic_terminal = row['roic_terminal']
        n_periods = row['n_periods']
        
        # Start time for forecast (end of training period)
        t_start = n_periods
        
        for horizon in FORECAST_HORIZONS:
            t_forecast = t_start + horizon
            
            # Base case forecast
            base_roic = decay_model(t_forecast, roic_0, lambda_, roic_terminal)
            forecasts.append({
                'cik': cik,
                'ticker': ticker,
                'horizon_years': horizon,
                'scenario': 'base',
                'forecast_roic': float(base_roic)
            })
            
            # Disruption scenario (faster decay)
            disrupted_lambda = lambda_ * DISRUPTION_MULTIPLIER
            disrupted_roic = decay_model(t_forecast, roic_0, disrupted_lambda, roic_terminal)
            forecasts.append({
                'cik': cik,
                'ticker': ticker,
                'horizon_years': horizon,
                'scenario': 'disruption',
                'forecast_roic': float(disrupted_roic)
            })
    
    forecasts_df = pd.DataFrame(forecasts)
    
    # Clear and insert forecasts
    conn.execute("DELETE FROM forecasts")
    forecasts_df.to_sql('forecasts', conn, if_exists='append', index=False)
    
    print(f"Generated {len(forecasts_df)} forecasts")
    
    # Summary statistics
    print("\n=== Forecast Summary ===")
    
    summary = forecasts_df.groupby(['horizon_years', 'scenario'])['forecast_roic'].agg(['mean', 'std', 'min', 'max'])
    print(summary.round(4))
    
    # Sample forecasts
    print("\n=== Sample Forecasts (first 5 companies) ===")
    sample = forecasts_df[forecasts_df['cik'].isin(forecasts_df['cik'].unique()[:5])]
    print(sample.pivot_table(
        index=['ticker', 'cik'], 
        columns=['horizon_years', 'scenario'], 
        values='forecast_roic'
    ).round(4))
    
    conn.close()
    
    # Save to CSV as well
    csv_path = Path(__file__).parent.parent / "data" / "forecasts.csv"
    forecasts_df.to_csv(csv_path, index=False)
    print(f"\nForecasts saved to {csv_path}")
    
    return forecasts_df


if __name__ == "__main__":
    generate_forecasts()
