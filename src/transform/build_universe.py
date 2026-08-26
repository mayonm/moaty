"""
Build the final company universe for the Moaty dataset.

Filters companies to those with sufficient consecutive years of ROIC data,
joins with sector benchmarks, and exports the final dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict

from .map_sectors import sic_to_damodaran, is_financial_sector
from .parse_damodaran import get_damodaran_benchmarks
from .compute_roic import add_roic_columns


def get_ticker_from_cik(cik: str) -> str:
    """
    Placeholder for CIK-to-ticker mapping.
    In production, this would use SEC's company_tickers.json.
    """
    return f"CIK{cik}"


def filter_to_annual_reports(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only companies with annual (10-K) filings."""
    return df.dropna(subset=["fiscal_year"])


def exclude_financials(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Exclude financial sector companies (SIC 6000-6999)."""
    original_count = len(df)
    
    mask = df["sic"].apply(lambda x: not is_financial_sector(x))
    filtered = df[mask]
    
    excluded = original_count - len(filtered)
    return filtered, excluded


def add_sector_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Add Damodaran industry mapping based on SIC code."""
    df = df.copy()
    df["sector"] = df["sic"].apply(sic_to_damodaran)
    return df


def join_sector_benchmarks(df: pd.DataFrame) -> pd.DataFrame:
    """Join with Damodaran WACC/ROIC sector benchmarks."""
    benchmarks = get_damodaran_benchmarks()
    
    merged = df.merge(
        benchmarks[["industry", "sector_wacc", "sector_roic"]],
        left_on="sector",
        right_on="industry",
        how="left"
    )
    
    merged = merged.drop(columns=["industry"], errors="ignore")
    
    return merged


def find_consecutive_years(years: List[int], min_consecutive: int = 5) -> Tuple[bool, int]:
    """
    Check if a company has enough consecutive years of data.
    
    Returns (has_enough, max_consecutive_count)
    """
    if len(years) < min_consecutive:
        return False, len(years)
    
    years = sorted(years)
    max_consecutive = 1
    current_consecutive = 1
    
    for i in range(1, len(years)):
        if years[i] == years[i-1] + 1:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 1
    
    return max_consecutive >= min_consecutive, max_consecutive


def filter_by_data_completeness(
    df: pd.DataFrame, 
    min_consecutive_years: int = 5
) -> Tuple[pd.DataFrame, Dict]:
    """
    Filter to companies with sufficient consecutive years of ROIC data.
    
    Returns filtered DataFrame and statistics about dropped companies.
    """
    df_valid = df[df["roic"].notna()].copy()
    
    company_stats = df_valid.groupby("cik").agg({
        "fiscal_year": list,
        "company_name": "first",
        "roic": "count"
    }).reset_index()
    
    company_stats["has_enough"], company_stats["max_consecutive"] = zip(
        *company_stats["fiscal_year"].apply(
            lambda x: find_consecutive_years(x, min_consecutive_years)
        )
    )
    
    valid_ciks = company_stats[company_stats["has_enough"]]["cik"].tolist()
    
    stats = {
        "total_companies_with_roic": len(company_stats),
        "companies_meeting_criteria": len(valid_ciks),
        "companies_dropped": len(company_stats) - len(valid_ciks),
        "min_consecutive_required": min_consecutive_years,
    }
    
    df_filtered = df[df["cik"].isin(valid_ciks)].copy()
    
    return df_filtered, stats


def get_cik_ticker_mapping() -> pd.DataFrame:
    """
    Get CIK to ticker mapping from SEC.
    
    Downloads the current SEC company tickers file.
    """
    import requests
    
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "Moaty Research Project contact@example.com"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        records = []
        for _, company in data.items():
            records.append({
                "cik": str(company["cik_str"]).zfill(10),
                "ticker": company["ticker"],
                "title": company["title"]
            })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        print(f"Warning: Could not fetch ticker mapping: {e}")
        return pd.DataFrame(columns=["cik", "ticker", "title"])


def add_tickers(df: pd.DataFrame) -> pd.DataFrame:
    """Add ticker symbols to the dataset."""
    ticker_map = get_cik_ticker_mapping()
    
    if len(ticker_map) == 0:
        df["ticker"] = df["cik"].apply(lambda x: f"CIK{x}")
        return df
    
    df = df.copy()
    df["cik_padded"] = df["cik"].apply(lambda x: str(x).zfill(10))
    
    merged = df.merge(
        ticker_map[["cik", "ticker"]],
        left_on="cik_padded",
        right_on="cik",
        how="left",
        suffixes=("", "_map")
    )
    
    merged["ticker"] = merged["ticker"].fillna(merged["cik_padded"].apply(lambda x: f"CIK{x}"))
    merged = merged.drop(columns=["cik_padded", "cik_map"], errors="ignore")
    
    return merged


def build_universe(
    fundamentals_df: pd.DataFrame,
    min_consecutive_years: int = 5,
    exclude_financial: bool = True,
    target_company_count: int = 100
) -> Tuple[pd.DataFrame, Dict]:
    """
    Build the final company universe.
    
    Returns:
        - Final DataFrame with ROIC and sector benchmarks
        - Statistics dictionary for the quality report
    """
    stats = {
        "input_records": len(fundamentals_df),
        "input_companies": fundamentals_df["cik"].nunique(),
    }
    
    print("Computing ROIC...")
    df = add_roic_columns(fundamentals_df)
    stats["records_with_roic"] = df["roic"].notna().sum()
    
    if exclude_financial:
        print("Excluding financial sector...")
        df, excluded = exclude_financials(df)
        stats["financials_excluded"] = excluded
    
    print("Adding sector mapping...")
    df = add_sector_mapping(df)
    stats["records_with_sector"] = df["sector"].notna().sum()
    
    print("Joining sector benchmarks...")
    df = join_sector_benchmarks(df)
    
    print(f"Filtering by data completeness (min {min_consecutive_years} consecutive years)...")
    df, filter_stats = filter_by_data_completeness(df, min_consecutive_years)
    stats.update(filter_stats)
    
    print("Adding ticker symbols...")
    df = add_tickers(df)
    
    if df["cik"].nunique() > target_company_count:
        print(f"Sampling to {target_company_count} companies...")
        
        company_coverage = df.groupby("cik").agg({
            "fiscal_year": lambda x: len(x),
            "roic": lambda x: x.notna().sum()
        }).reset_index()
        company_coverage.columns = ["cik", "total_years", "roic_years"]
        company_coverage = company_coverage.sort_values("roic_years", ascending=False)
        
        top_ciks = company_coverage.head(target_company_count)["cik"].tolist()
        df = df[df["cik"].isin(top_ciks)]
    
    stats["final_companies"] = df["cik"].nunique()
    stats["final_records"] = len(df)
    
    years = df["fiscal_year"].dropna()
    stats["year_range"] = (int(years.min()), int(years.max()))
    stats["median_years_per_company"] = df.groupby("cik")["fiscal_year"].count().median()
    
    return df, stats


if __name__ == "__main__":
    from extract_fundamentals import extract_all_fundamentals
    
    print("Extracting fundamentals...")
    fundamentals = extract_all_fundamentals()
    
    print("\nBuilding universe...")
    universe, stats = build_universe(fundamentals)
    
    print("\n=== Universe Statistics ===")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSample data:")
    cols = ["ticker", "cik", "company_name", "fiscal_year", "roic", "sector", "sector_wacc", "sector_roic"]
    print(universe[cols].head(20))
