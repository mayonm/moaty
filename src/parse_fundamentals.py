"""
SEC EDGAR Fundamentals Parser

Parses SEC quarterly data to extract financial metrics needed for ROIC calculation.
Computes ROIC using: NOPAT / Invested Capital
where:
  - NOPAT = Operating Income × (1 - Effective Tax Rate)
  - Invested Capital = Total Assets - Current Liabilities

See METHODOLOGY.md for detailed rationale.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import warnings

warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

DATA_DIR = Path(__file__).parent.parent / "data" / "quarter_reports"

# XBRL tags we need for ROIC calculation
REQUIRED_TAGS = {
    'OperatingIncomeLoss': 'operating_income',
    'IncomeTaxExpenseBenefit': 'income_tax',
    'Assets': 'total_assets',
    'LiabilitiesCurrent': 'current_liabilities',
    'NetIncomeLoss': 'net_income',
    'Revenues': 'revenues',
    'StockholdersEquity': 'stockholders_equity',
}

# SIC code to sector mapping (simplified - major categories)
SIC_TO_SECTOR = {
    range(100, 1000): 'Agriculture',
    range(1000, 1500): 'Mining',
    range(1500, 1800): 'Construction',
    range(2000, 4000): 'Manufacturing',
    range(4000, 5000): 'Transportation & Utilities',
    range(5000, 5200): 'Wholesale Trade',
    range(5200, 6000): 'Retail Trade',
    range(6000, 6800): 'Finance & Insurance',
    range(7000, 9000): 'Services',
    range(9000, 10000): 'Public Administration',
}


def get_sector_from_sic(sic_code: str) -> str:
    """Map SIC code to sector."""
    try:
        sic = int(sic_code)
        for sic_range, sector in SIC_TO_SECTOR.items():
            if sic in sic_range:
                return sector
        return 'Other'
    except (ValueError, TypeError):
        return 'Unknown'


def parse_quarter(year: int, quarter: int) -> Optional[pd.DataFrame]:
    """
    Parse a single quarter's SEC data.
    Returns DataFrame with company fundamentals.
    """
    quarter_dir = DATA_DIR / f"{year}q{quarter}"
    sub_file = quarter_dir / "sub.txt"
    num_file = quarter_dir / "num.txt"
    
    if not sub_file.exists() or not num_file.exists():
        return None
    
    # Load submissions (company info)
    sub = pd.read_csv(sub_file, sep='\t', dtype=str, low_memory=False)
    
    # Load numeric values
    num = pd.read_csv(num_file, sep='\t', dtype=str, low_memory=False)
    
    # Filter to annual reports (10-K) and quarterly (10-Q)
    sub = sub[sub['form'].isin(['10-K', '10-Q'])]
    
    # Filter num to tags we need
    num = num[num['tag'].isin(REQUIRED_TAGS.keys())]
    
    # Convert value to numeric
    num['value'] = pd.to_numeric(num['value'], errors='coerce')
    
    # Filter to point-in-time values (qtrs=0 for balance sheet) or annual (qtrs=4)
    # For income statement items, use quarterly values (qtrs=1 for 10-Q, qtrs=4 for 10-K)
    
    # Merge with company info
    merged = num.merge(
        sub[['adsh', 'cik', 'name', 'sic', 'form', 'fy', 'fp', 'period']],
        on='adsh',
        how='inner'
    )
    
    return merged


def aggregate_company_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate quarterly data to annual company-level metrics.
    For balance sheet items, take year-end values.
    For income statement items, sum quarters or take annual report value.
    """
    results = []
    
    # Group by company and fiscal year
    for (cik, fy), group in df.groupby(['cik', 'fy']):
        company_name = group['name'].iloc[0]
        sic_code = group['sic'].iloc[0]
        
        # Get the most recent filing for each tag
        metrics = {}
        for tag, col_name in REQUIRED_TAGS.items():
            tag_data = group[group['tag'] == tag]
            if len(tag_data) > 0:
                # For balance sheet items (Assets, Liabilities), take latest value
                if tag in ['Assets', 'LiabilitiesCurrent', 'StockholdersEquity']:
                    # Take point-in-time value (qtrs=0) if available
                    pit = tag_data[tag_data['qtrs'] == '0']
                    if len(pit) > 0:
                        metrics[col_name] = pit['value'].iloc[-1]
                    else:
                        metrics[col_name] = tag_data['value'].iloc[-1]
                else:
                    # For income statement items, prefer annual (qtrs=4) from 10-K
                    annual = tag_data[(tag_data['qtrs'] == '4') | (tag_data['form'] == '10-K')]
                    if len(annual) > 0:
                        metrics[col_name] = annual['value'].iloc[-1]
                    else:
                        # Sum quarterly values
                        quarterly = tag_data[tag_data['qtrs'] == '1']
                        if len(quarterly) >= 4:
                            metrics[col_name] = quarterly['value'].sum()
                        elif len(tag_data) > 0:
                            metrics[col_name] = tag_data['value'].iloc[-1]
        
        results.append({
            'cik': cik,
            'company_name': company_name,
            'sic_code': sic_code,
            'fiscal_year': int(fy) if fy else None,
            **metrics
        })
    
    return pd.DataFrame(results)


def compute_roic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute ROIC for each company-year.
    
    ROIC = NOPAT / Invested Capital
    where:
      - NOPAT = Operating Income × (1 - Effective Tax Rate)
      - Invested Capital = Total Assets - Current Liabilities
      
    If Operating Income is not available, falls back to:
      NOPAT ≈ Net Income + Interest Expense × (1 - Tax Rate)
    """
    df = df.copy()
    
    # Compute effective tax rate (capped between 0 and 0.5)
    df['effective_tax_rate'] = np.where(
        (df['operating_income'].notna()) & (df['operating_income'] > 0),
        np.clip(df['income_tax'] / df['operating_income'], 0, 0.5),
        0.21  # Default to corporate rate if can't compute
    )
    
    # Compute NOPAT
    df['nopat'] = df['operating_income'] * (1 - df['effective_tax_rate'])
    
    # Compute Invested Capital
    df['invested_capital'] = df['total_assets'] - df['current_liabilities']
    
    # Compute ROIC
    df['roic'] = np.where(
        df['invested_capital'] > 0,
        df['nopat'] / df['invested_capital'],
        np.nan
    )
    
    # Cap ROIC to reasonable range (-1 to 1)
    df['roic'] = np.clip(df['roic'], -1, 1)
    
    return df


def parse_all_quarters() -> pd.DataFrame:
    """Parse all available quarters and aggregate to annual data."""
    all_data = []
    
    quarters = sorted(DATA_DIR.iterdir())
    print(f"Parsing {len(quarters)} quarters...")
    
    for i, quarter_dir in enumerate(quarters):
        if not quarter_dir.is_dir() or 'q' not in quarter_dir.name:
            continue
        
        try:
            year = int(quarter_dir.name[:4])
            q = int(quarter_dir.name[5])
        except (ValueError, IndexError):
            continue
        
        if (i + 1) % 10 == 0:
            print(f"  Processing {year}q{q} ({i+1}/{len(quarters)})...")
        
        df = parse_quarter(year, q)
        if df is not None and len(df) > 0:
            all_data.append(df)
    
    if not all_data:
        raise ValueError("No data found in any quarter")
    
    # Combine all quarters
    print("Combining quarterly data...")
    combined = pd.concat(all_data, ignore_index=True)
    
    # Aggregate to annual company metrics
    print("Aggregating to annual company metrics...")
    annual = aggregate_company_year(combined)
    
    # Compute ROIC
    print("Computing ROIC...")
    annual = compute_roic(annual)
    
    # Add sector
    annual['sector'] = annual['sic_code'].apply(get_sector_from_sic)
    
    # Filter to valid ROIC values
    valid = annual[annual['roic'].notna() & annual['fiscal_year'].notna()]
    
    print(f"Parsed {len(valid)} company-year observations with valid ROIC")
    print(f"Unique companies: {valid['cik'].nunique()}")
    print(f"Year range: {valid['fiscal_year'].min()} - {valid['fiscal_year'].max()}")
    
    return valid


def get_ticker_mapping() -> Dict[str, str]:
    """
    Create a CIK to ticker mapping.
    Uses SEC's company tickers JSON endpoint.
    """
    import requests
    
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "Moaty Research Tool contact@example.com"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Map CIK (padded to 10 digits) to ticker
        mapping = {}
        for item in data.values():
            cik = str(item['cik_str']).zfill(10)
            ticker = item['ticker']
            mapping[cik] = ticker
        
        return mapping
    except Exception as e:
        print(f"Warning: Could not fetch ticker mapping: {e}")
        return {}


def filter_quality_companies(df: pd.DataFrame, min_years: int = 7) -> pd.DataFrame:
    """
    Filter to companies with enough data for reliable fitting.
    
    Criteria:
    - At least min_years of ROIC observations
    - Not more than 20% missing years in their range
    - ROIC values in reasonable range
    """
    # Count observations per company
    company_counts = df.groupby('cik').agg({
        'fiscal_year': ['count', 'min', 'max'],
        'roic': 'mean'
    })
    company_counts.columns = ['n_years', 'min_year', 'max_year', 'avg_roic']
    company_counts['year_range'] = company_counts['max_year'] - company_counts['min_year'] + 1
    company_counts['coverage'] = company_counts['n_years'] / company_counts['year_range']
    
    # Filter
    quality_companies = company_counts[
        (company_counts['n_years'] >= min_years) &
        (company_counts['coverage'] >= 0.8)
    ].index
    
    filtered = df[df['cik'].isin(quality_companies)]
    
    print(f"Filtered to {len(quality_companies)} quality companies with {min_years}+ years of data")
    
    return filtered


if __name__ == "__main__":
    # Parse all data
    df = parse_all_quarters()
    
    # Filter to quality companies
    df = filter_quality_companies(df, min_years=7)
    
    # Add ticker mapping
    print("Fetching ticker mapping...")
    ticker_map = get_ticker_mapping()
    df['ticker'] = df['cik'].apply(lambda x: ticker_map.get(str(x).zfill(10), ''))
    
    # Save to CSV
    output_path = Path(__file__).parent.parent / "data" / "fundamentals.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved fundamentals to {output_path}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Companies: {df['cik'].nunique()}")
    print(f"Total observations: {len(df)}")
    print(f"Year range: {df['fiscal_year'].min()} - {df['fiscal_year'].max()}")
    print(f"\nROIC distribution:")
    print(df['roic'].describe())
