"""
Parse Damodaran sector benchmark data.

Extracts WACC and ROIC by industry from Damodaran Excel files.
"""

import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "damodaran"


def parse_wacc() -> pd.DataFrame:
    """Parse WACC data from Damodaran wacc.xls."""
    filepath = RAW_DIR / "wacc.xls"
    
    df = pd.read_excel(
        filepath, 
        sheet_name="Industry Averages", 
        engine="xlrd", 
        skiprows=18, 
        header=0
    )
    
    df = df[["Industry Name", "Number of Firms", "Cost of Capital"]].copy()
    df.columns = ["industry", "num_firms", "wacc"]
    
    df = df.dropna(subset=["industry"])
    df = df[df["industry"] != "Total Market"]
    df = df[df["industry"] != "Total Market (without financials)"]
    
    df["industry"] = df["industry"].str.strip()
    df["wacc"] = pd.to_numeric(df["wacc"], errors="coerce")
    
    return df.reset_index(drop=True)


def parse_roc() -> pd.DataFrame:
    """Parse ROC data from Damodaran roc.xls."""
    filepath = RAW_DIR / "roc.xls"
    
    df = pd.read_excel(
        filepath, 
        sheet_name="Industry Averages", 
        engine="xlrd", 
        skiprows=7, 
        header=0
    )
    
    df = df[["Industry Name", "Number of firms", "Unadjusted after-tax ROIC", "Normalized ROIC (last 10 years)"]].copy()
    df.columns = ["industry", "num_firms", "roic_current", "roic_normalized"]
    
    df = df.dropna(subset=["industry"])
    df = df[df["industry"] != "Total Market"]
    df = df[df["industry"] != "Total Market (without financials)"]
    
    df["industry"] = df["industry"].str.strip()
    df["roic_current"] = pd.to_numeric(df["roic_current"], errors="coerce")
    df["roic_normalized"] = pd.to_numeric(df["roic_normalized"], errors="coerce")
    
    return df.reset_index(drop=True)


def get_damodaran_benchmarks() -> pd.DataFrame:
    """Get combined WACC and ROIC benchmarks by industry."""
    wacc_df = parse_wacc()
    roc_df = parse_roc()
    
    merged = pd.merge(
        wacc_df[["industry", "wacc"]],
        roc_df[["industry", "roic_current", "roic_normalized"]],
        on="industry",
        how="outer"
    )
    
    merged = merged.rename(columns={
        "roic_current": "sector_roic",
        "roic_normalized": "sector_roic_normalized",
        "wacc": "sector_wacc"
    })
    
    return merged


if __name__ == "__main__":
    benchmarks = get_damodaran_benchmarks()
    print(f"Damodaran benchmarks: {len(benchmarks)} industries")
    print(benchmarks.head(10))
    print(f"\nIndustries: {sorted(benchmarks['industry'].unique())[:20]}...")
