"""
Compute ROIC (Return on Invested Capital) from fundamental data.

ROIC = NOPAT / Invested Capital
NOPAT = Operating Income × (1 - Effective Tax Rate)
Invested Capital = Stockholders Equity + Total Debt - Cash
"""

import pandas as pd
import numpy as np
from typing import Optional


def compute_effective_tax_rate(row: pd.Series) -> Optional[float]:
    """
    Compute effective tax rate from pretax income and tax expense.
    
    Returns None if tax rate cannot be computed or is unreasonable.
    """
    pretax = row.get("pretax_income")
    tax = row.get("tax_expense")
    
    if pd.isna(pretax) or pd.isna(tax):
        return None
    
    if pretax <= 0:
        return None
    
    rate = tax / pretax
    
    if rate < 0 or rate > 0.5:
        return None
    
    return rate


def compute_nopat(row: pd.Series) -> Optional[float]:
    """
    Compute Net Operating Profit After Tax.
    
    NOPAT = Operating Income × (1 - Effective Tax Rate)
    Falls back to statutory 21% rate if effective rate unavailable.
    """
    op_income = row.get("operating_income")
    
    if pd.isna(op_income):
        return None
    
    eff_tax_rate = compute_effective_tax_rate(row)
    
    if eff_tax_rate is None:
        eff_tax_rate = 0.21
    
    return op_income * (1 - eff_tax_rate)


def compute_invested_capital(row: pd.Series) -> Optional[float]:
    """
    Compute Invested Capital.
    
    IC = Stockholders Equity + Long-Term Debt + Short-Term Debt - Cash
    """
    equity = row.get("stockholders_equity")
    lt_debt = row.get("long_term_debt", 0) or 0
    st_debt = row.get("short_term_debt", 0) or 0
    cash = row.get("cash", 0) or 0
    
    if pd.isna(equity):
        return None
    
    invested_capital = equity + lt_debt + st_debt - cash
    
    if invested_capital <= 0:
        return None
    
    return invested_capital


def compute_roic(row: pd.Series) -> Optional[float]:
    """
    Compute Return on Invested Capital.
    
    ROIC = NOPAT / Invested Capital
    """
    nopat = row.get("nopat")
    ic = row.get("invested_capital")
    
    if pd.isna(nopat) or pd.isna(ic) or ic <= 0:
        return None
    
    roic = nopat / ic
    
    if roic < -1.0 or roic > 2.0:
        return None
    
    return roic


def add_roic_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add NOPAT, Invested Capital, and ROIC columns to fundamentals DataFrame.
    """
    df = df.copy()
    
    df["nopat"] = df.apply(compute_nopat, axis=1)
    df["invested_capital"] = df.apply(compute_invested_capital, axis=1)
    df["roic"] = df.apply(compute_roic, axis=1)
    
    df["effective_tax_rate"] = df.apply(compute_effective_tax_rate, axis=1)
    
    return df


def compute_roic_for_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full pipeline: compute ROIC for a fundamentals dataset.
    
    Returns DataFrame with ROIC computed and summary stats printed.
    """
    print(f"Input: {len(df)} company-year records")
    
    df = add_roic_columns(df)
    
    roic_valid = df["roic"].notna().sum()
    print(f"Records with valid ROIC: {roic_valid} ({roic_valid/len(df)*100:.1f}%)")
    
    if roic_valid > 0:
        print(f"ROIC distribution:")
        print(f"  Min:    {df['roic'].min():.3f}")
        print(f"  25%:    {df['roic'].quantile(0.25):.3f}")
        print(f"  Median: {df['roic'].median():.3f}")
        print(f"  75%:    {df['roic'].quantile(0.75):.3f}")
        print(f"  Max:    {df['roic'].max():.3f}")
    
    return df


if __name__ == "__main__":
    from extract_fundamentals import extract_all_fundamentals
    
    print("Extracting fundamentals...")
    fundamentals = extract_all_fundamentals()
    
    print("\nComputing ROIC...")
    with_roic = compute_roic_for_dataset(fundamentals)
    
    print("\nSample with ROIC:")
    sample = with_roic[with_roic["roic"].notna()].head(10)
    print(sample[["cik", "company_name", "fiscal_year", "operating_income", "nopat", "invested_capital", "roic"]])
