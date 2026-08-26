"""
Export final datasets to Parquet format.
"""

import pandas as pd
from pathlib import Path
from typing import Dict
from datetime import datetime


OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "output"


def export_fundamentals(df: pd.DataFrame, filename: str = "fundamentals.parquet") -> Path:
    """
    Export fundamentals dataset to Parquet.
    
    Output columns: ticker, cik, company_name, year, roic, wacc_benchmark, roic_benchmark, sector, sic
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    export_df = df[["ticker", "cik", "company_name", "fiscal_year", "roic", 
                    "sector_wacc", "sector_roic", "sector", "sic"]].copy()
    
    export_df = export_df.rename(columns={
        "fiscal_year": "year",
        "sector_wacc": "wacc_benchmark",
        "sector_roic": "roic_benchmark"
    })
    
    export_df = export_df[export_df["roic"].notna()]
    
    export_df = export_df.sort_values(["ticker", "year"])
    
    filepath = OUTPUT_DIR / filename
    export_df.to_parquet(filepath, index=False)
    
    print(f"Exported fundamentals: {len(export_df)} records, {export_df['ticker'].nunique()} companies")
    print(f"  File: {filepath}")
    
    return filepath


def export_prices(df: pd.DataFrame, filename: str = "prices.parquet") -> Path:
    """
    Export prices dataset to Parquet.
    
    Output columns: ticker, date, close
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    export_df = df[["ticker", "date", "close"]].copy()
    export_df = export_df.dropna()
    export_df = export_df.sort_values(["ticker", "date"])
    
    filepath = OUTPUT_DIR / filename
    export_df.to_parquet(filepath, index=False)
    
    print(f"Exported prices: {len(export_df)} records, {export_df['ticker'].nunique()} tickers")
    print(f"  File: {filepath}")
    
    return filepath


def generate_quality_report(
    stats: Dict,
    fundamentals_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    filename: str = "data_quality_report.md"
) -> Path:
    """
    Generate a markdown quality report.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    year_coverage = fundamentals_df.groupby("ticker")["year"].agg(["min", "max", "count"])
    
    report = f"""# Moaty Data Quality Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

| Metric | Value |
|--------|-------|
| Companies in universe | {fundamentals_df['ticker'].nunique()} |
| Total fundamentals records | {len(fundamentals_df)} |
| Total price records | {len(prices_df)} |
| Year range | {int(fundamentals_df['year'].min())} - {int(fundamentals_df['year'].max())} |

## Fundamentals Dataset

**File:** `fundamentals.parquet`

**Columns:**
- `ticker` - Stock ticker symbol
- `cik` - SEC Central Index Key
- `company_name` - Company name
- `year` - Fiscal year
- `roic` - Return on Invested Capital
- `wacc_benchmark` - Sector WACC from Damodaran
- `roic_benchmark` - Sector ROIC from Damodaran  
- `sector` - Damodaran industry name
- `sic` - SEC SIC code

**Coverage Statistics:**

| Metric | Value |
|--------|-------|
| Min years per company | {int(year_coverage['count'].min())} |
| Max years per company | {int(year_coverage['count'].max())} |
| Median years per company | {year_coverage['count'].median():.1f} |
| Companies with 5+ years | {(year_coverage['count'] >= 5).sum()} |

**ROIC Distribution:**

| Percentile | ROIC |
|------------|------|
| Min | {fundamentals_df['roic'].min():.3f} |
| 25% | {fundamentals_df['roic'].quantile(0.25):.3f} |
| Median | {fundamentals_df['roic'].median():.3f} |
| 75% | {fundamentals_df['roic'].quantile(0.75):.3f} |
| Max | {fundamentals_df['roic'].max():.3f} |

## Price Dataset

**File:** `prices.parquet`

**Columns:**
- `ticker` - Stock ticker symbol
- `date` - Trading date
- `close` - Adjusted closing price

**Coverage:**
- Tickers with price data: {prices_df['ticker'].nunique()}
- Date range: {prices_df['date'].min().strftime('%Y-%m-%d')} to {prices_df['date'].max().strftime('%Y-%m-%d')}
- Total trading days (avg): {len(prices_df) / prices_df['ticker'].nunique():.0f}

## Processing Statistics

| Stage | Value |
|-------|-------|
| Input SEC records | {stats.get('input_records', 'N/A')} |
| Input companies | {stats.get('input_companies', 'N/A')} |
| Records with ROIC | {stats.get('records_with_roic', 'N/A')} |
| Financials excluded | {stats.get('financials_excluded', 'N/A')} |
| Records with sector | {stats.get('records_with_sector', 'N/A')} |
| Companies meeting criteria | {stats.get('companies_meeting_criteria', 'N/A')} |
| Final companies | {stats.get('final_companies', 'N/A')} |

## Methodology Notes

### ROIC Calculation

```
ROIC = NOPAT / Invested Capital
NOPAT = Operating Income × (1 - Effective Tax Rate)
Invested Capital = Stockholders Equity + Total Debt - Cash
```

- Effective tax rate computed from reported tax expense / pretax income
- Falls back to 21% statutory rate when effective rate unavailable or unreasonable
- Financial sector (SIC 6000-6999) excluded as ROIC not meaningful for banks

### Data Sources

- **SEC EDGAR Financial Statement Data Sets** (2017q1 - 2026q2)
- **Damodaran Online** (January 2026 update)
  - wacc.xls - Sector cost of capital
  - roc.xls - Sector return on capital
- **Yahoo Finance** via yfinance - Daily adjusted close prices

### Sector Mapping

SIC codes mapped to Damodaran's ~94 industry categories using 2-digit SIC major groups.

### Company Selection Criteria

1. Filed 10-K annual reports in SEC EDGAR
2. Non-financial sector (excludes SIC 6000-6999)
3. At least 5 consecutive years of computable ROIC
4. Required XBRL tags present: Operating Income, Stockholders Equity, Cash
5. ROIC within reasonable bounds (-100% to +200%)
"""
    
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w") as f:
        f.write(report)
    
    print(f"Generated quality report: {filepath}")
    
    return filepath
