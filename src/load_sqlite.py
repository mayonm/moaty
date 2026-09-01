"""
SQLite Database Loader

Loads fundamentals and prices data into SQLite database.
Schema designed to be Supabase-compatible for future migration.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = Path(__file__).parent.parent / "moaty.db"

# Configuration constants
HOLDOUT_YEARS = [2025, 2026]  # Years held out for validation


def create_schema(conn: sqlite3.Connection):
    """Create database schema."""
    cursor = conn.cursor()
    
    # Fundamentals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik TEXT NOT NULL,
            ticker TEXT,
            company_name TEXT,
            fiscal_year INTEGER NOT NULL,
            roic REAL,
            operating_income REAL,
            total_assets REAL,
            current_liabilities REAL,
            invested_capital REAL,
            nopat REAL,
            effective_tax_rate REAL,
            sector TEXT,
            sic_code TEXT,
            is_holdout BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            close_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Decay fits table (populated by Julia)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decay_fits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik TEXT NOT NULL,
            ticker TEXT,
            company_name TEXT,
            lambda REAL,
            roic_0 REAL,
            roic_terminal REAL,
            r_squared REAL,
            converged BOOLEAN,
            n_periods INTEGER,
            fit_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Validation table (populated by R)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS validation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik TEXT NOT NULL,
            ticker TEXT,
            p_value REAL,
            ci_low REAL,
            ci_high REAL,
            holdout_rmse_model REAL,
            holdout_rmse_naive REAL,
            price_return_holdout REAL,
            lambda_price_corr REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Forecasts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik TEXT NOT NULL,
            ticker TEXT,
            horizon_years INTEGER NOT NULL,
            scenario TEXT NOT NULL,
            forecast_roic REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamentals_cik ON fundamentals(cik)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamentals_ticker ON fundamentals(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamentals_year ON fundamentals(fiscal_year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decay_fits_cik ON decay_fits(cik)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_decay_fits_lambda ON decay_fits(lambda)")
    
    conn.commit()
    print("Schema created successfully")


def load_fundamentals(conn: sqlite3.Connection, csv_path: Optional[Path] = None):
    """Load fundamentals data into SQLite."""
    if csv_path is None:
        csv_path = DATA_DIR / "fundamentals.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Fundamentals CSV not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Mark holdout years
    df['is_holdout'] = df['fiscal_year'].isin(HOLDOUT_YEARS).astype(int)
    
    # Rename columns to match schema
    column_mapping = {
        'cik': 'cik',
        'ticker': 'ticker',
        'company_name': 'company_name',
        'fiscal_year': 'fiscal_year',
        'roic': 'roic',
        'operating_income': 'operating_income',
        'total_assets': 'total_assets',
        'current_liabilities': 'current_liabilities',
        'invested_capital': 'invested_capital',
        'nopat': 'nopat',
        'effective_tax_rate': 'effective_tax_rate',
        'sector': 'sector',
        'sic_code': 'sic_code',
        'is_holdout': 'is_holdout'
    }
    
    # Select only columns that exist
    cols_to_use = [c for c in column_mapping.keys() if c in df.columns]
    df = df[cols_to_use].rename(columns=column_mapping)
    
    # Clear existing data
    conn.execute("DELETE FROM fundamentals")
    
    # Insert new data
    df.to_sql('fundamentals', conn, if_exists='append', index=False)
    
    print(f"Loaded {len(df)} fundamentals records")
    print(f"  Training data (is_holdout=0): {(df['is_holdout'] == 0).sum()}")
    print(f"  Holdout data (is_holdout=1): {(df['is_holdout'] == 1).sum()}")
    
    return df


def load_prices(conn: sqlite3.Connection, csv_path: Optional[Path] = None):
    """Load price data into SQLite."""
    if csv_path is None:
        csv_path = DATA_DIR / "prices.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Prices CSV not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Clear existing data
    conn.execute("DELETE FROM prices")
    
    # Insert new data
    df.to_sql('prices', conn, if_exists='append', index=False)
    
    print(f"Loaded {len(df)} price records")
    print(f"  Unique tickers: {df['ticker'].nunique()}")
    
    return df


def get_training_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Get training data (non-holdout) for fitting."""
    query = """
        SELECT cik, ticker, company_name, fiscal_year, roic, sector
        FROM fundamentals
        WHERE is_holdout = 0 AND roic IS NOT NULL
        ORDER BY cik, fiscal_year
    """
    return pd.read_sql_query(query, conn)


def get_holdout_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Get holdout data for validation."""
    query = """
        SELECT cik, ticker, company_name, fiscal_year, roic, sector
        FROM fundamentals
        WHERE is_holdout = 1 AND roic IS NOT NULL
        ORDER BY cik, fiscal_year
    """
    return pd.read_sql_query(query, conn)


def export_for_julia(conn: sqlite3.Connection, output_path: Optional[Path] = None):
    """Export training data to CSV for Julia processing."""
    if output_path is None:
        output_path = DATA_DIR / "training_data.csv"
    
    df = get_training_data(conn)
    df.to_csv(output_path, index=False)
    
    print(f"Exported {len(df)} training records to {output_path}")
    print(f"  Unique companies: {df['cik'].nunique()}")
    
    return output_path


def load_database():
    """Main function to load all data into SQLite."""
    print(f"Creating database at {DB_PATH}")
    
    # Remove existing database for fresh start
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        create_schema(conn)
        load_fundamentals(conn)
        load_prices(conn)
        export_for_julia(conn)
        
        # Print summary
        cursor = conn.cursor()
        
        print("\n=== Database Summary ===")
        for table in ['fundamentals', 'prices', 'decay_fits', 'validation', 'forecasts']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
        
        conn.commit()
        
    finally:
        conn.close()
    
    print(f"\nDatabase created successfully at {DB_PATH}")


if __name__ == "__main__":
    load_database()
