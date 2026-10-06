"""
Demo company database.

Used when moaty.db has not been built by the full SEC pipeline.
The rows are internally consistent with the decay model so search,
historical metrics, and the research page all have something to show.
"""

import math
import sqlite3
from pathlib import Path

from .load_sqlite import create_schema

DB_PATH = Path(__file__).parent.parent / "moaty.db"

# cik, ticker, name, sector, lambda, roic_0, roic_terminal, r_squared
COMPANIES = [
    ("0000320193", "AAPL", "Apple", "Technology", 0.09, 0.46, 0.28, 0.93),
    ("0000789019", "MSFT", "Microsoft", "Technology", 0.11, 0.34, 0.22, 0.90),
    ("0001652044", "GOOGL", "Alphabet", "Technology", 0.14, 0.29, 0.16, 0.86),
    ("0001018724", "AMZN", "Amazon", "Consumer Discretionary", 0.18, 0.22, 0.12, 0.81),
    ("0001326801", "META", "Meta Platforms", "Technology", 0.16, 0.31, 0.17, 0.84),
    ("0001045810", "NVDA", "NVIDIA", "Technology", 0.06, 0.52, 0.34, 0.88),
    ("0001318605", "TSLA", "Tesla", "Consumer Discretionary", 0.32, 0.24, 0.08, 0.73),
    ("0000019617", "JPM", "JPMorgan Chase", "Financials", 0.13, 0.16, 0.11, 0.85),
    ("0000200406", "JNJ", "Johnson & Johnson", "Healthcare", 0.08, 0.21, 0.14, 0.91),
    ("0000104169", "WMT", "Walmart", "Consumer Staples", 0.10, 0.15, 0.10, 0.87),
    ("0000021344", "KO", "Coca-Cola", "Consumer Staples", 0.07, 0.23, 0.16, 0.94),
    ("0001744489", "DIS", "Walt Disney", "Communication Services", 0.21, 0.14, 0.08, 0.76),
    ("0001065280", "NFLX", "Netflix", "Communication Services", 0.19, 0.20, 0.11, 0.80),
    ("0000002488", "AMD", "AMD", "Technology", 0.17, 0.27, 0.13, 0.78),
    ("0000050863", "INTC", "Intel", "Technology", 0.28, 0.18, 0.06, 0.72),
    ("0001108524", "CRM", "Salesforce", "Technology", 0.15, 0.12, 0.08, 0.83),
    ("0001403161", "V", "Visa", "Financials", 0.07, 0.38, 0.26, 0.92),
    ("0000731766", "UNH", "UnitedHealth", "Healthcare", 0.12, 0.19, 0.12, 0.86),
    ("0000354950", "HD", "Home Depot", "Consumer Discretionary", 0.11, 0.33, 0.20, 0.89),
    ("0000080424", "PG", "Procter & Gamble", "Consumer Staples", 0.08, 0.20, 0.14, 0.91),
    ("0000909832", "COST", "Costco", "Consumer Staples", 0.09, 0.22, 0.15, 0.90),
    ("0000320187", "NKE", "Nike", "Consumer Discretionary", 0.18, 0.28, 0.14, 0.82),
    ("0000034088", "XOM", "Exxon Mobil", "Energy", 0.20, 0.18, 0.09, 0.75),
    ("0000078003", "PFE", "Pfizer", "Healthcare", 0.26, 0.17, 0.07, 0.71),
    ("0000012927", "BA", "Boeing", "Industrials", 0.30, 0.11, 0.05, 0.69),
    ("0000829224", "SBUX", "Starbucks", "Consumer Discretionary", 0.14, 0.26, 0.15, 0.84),
]

YEARS = list(range(2016, 2025))


def _roic(roic_0: float, terminal: float, lam: float, t: int) -> float:
    base = terminal + (roic_0 - terminal) * math.exp(-lam * t)
    wobble = 0.008 * math.sin(t * 1.7)
    return round(base + wobble, 4)


def ensure_demo_database(db_path: Path = DB_PATH) -> None:
    """Create moaty.db with sample companies when no real pipeline output exists."""
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM decay_fits").fetchone()[0]
            if count:
                conn.close()
                return
        except sqlite3.OperationalError:
            pass
        conn.close()

    conn = sqlite3.connect(db_path)
    create_schema(conn)

    for cik, ticker, name, sector, lam, roic_0, terminal, r2 in COMPANIES:
        for t, year in enumerate(YEARS):
            conn.execute(
                """
                INSERT INTO fundamentals
                    (cik, ticker, company_name, fiscal_year, roic, sector, is_holdout)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (cik, ticker, name, year, _roic(roic_0, terminal, lam, t), sector, 0),
            )
        conn.execute(
            """
            INSERT INTO decay_fits
                (cik, ticker, company_name, lambda, roic_0, roic_terminal,
                 r_squared, converged, n_periods, fit_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, date('now'))
            """,
            (cik, ticker, name, lam, roic_0, terminal, r2, len(YEARS)),
        )

    conn.commit()
    conn.close()
    print(f"Demo database ready with {len(COMPANIES)} companies at {db_path}")
