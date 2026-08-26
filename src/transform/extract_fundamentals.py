"""
Extract fundamental financial data from SEC EDGAR num.txt files.

Extracts the XBRL tags needed for ROIC calculation.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Set
from tqdm import tqdm

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "sec"

ROIC_TAGS = {
    "operating_income": [
        "OperatingIncomeLoss",
        "OperatingIncome",
        "IncomeLossFromOperations",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
        "IncomeLossBeforeIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
    ],
    "tax_expense": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxExpense",
        "IncomeTaxesPaidNet",
    ],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "TotalStockholdersEquity",
        "CommonStockholdersEquity",
    ],
    "long_term_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtCurrent",
    ],
    "short_term_debt": [
        "ShortTermBorrowings",
        "DebtCurrent",
        "ShortTermDebt",
        "CommercialPaper",
        "ShortTermBankLoansAndNotesPayable",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "Cash",
        "CashCashEquivalentsAndShortTermInvestments",
        "CashAndCashEquivalents",
    ],
}

ALL_TAGS = set()
for tags in ROIC_TAGS.values():
    ALL_TAGS.update(tags)


def get_available_quarters() -> List[str]:
    """Get list of available quarter directories."""
    quarters = []
    if RAW_DIR.exists():
        for d in sorted(RAW_DIR.iterdir()):
            if d.is_dir() and (d / "num.txt").exists():
                quarters.append(d.name)
    return quarters


def load_sub_data(quarter: str) -> pd.DataFrame:
    """Load submission metadata for a quarter."""
    sub_file = RAW_DIR / quarter / "sub.txt"
    df = pd.read_csv(sub_file, sep="\t", dtype=str, low_memory=False)
    
    cols_to_keep = ["adsh", "cik", "name", "sic", "form", "fy", "fp", "filed"]
    df = df[[c for c in cols_to_keep if c in df.columns]]
    
    return df


def load_num_data(quarter: str, tags_filter: Optional[Set[str]] = None) -> pd.DataFrame:
    """Load numeric data for a quarter, optionally filtered to specific tags."""
    num_file = RAW_DIR / quarter / "num.txt"
    df = pd.read_csv(num_file, sep="\t", dtype=str, low_memory=False)
    
    if tags_filter:
        df = df[df["tag"].isin(tags_filter)]
    
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["qtrs"] = pd.to_numeric(df["qtrs"], errors="coerce").fillna(0).astype(int)
    df["ddate"] = pd.to_datetime(df["ddate"], format="%Y%m%d", errors="coerce")
    
    return df


def extract_quarter_fundamentals(quarter: str) -> pd.DataFrame:
    """
    Extract fundamental data for a single quarter.
    
    Returns DataFrame with one row per company-fiscal-year with extracted tags.
    """
    sub_df = load_sub_data(quarter)
    
    sub_df = sub_df[sub_df["form"].isin(["10-K", "10-K/A", "20-F", "20-F/A"])]
    if len(sub_df) == 0:
        return pd.DataFrame()
    
    num_df = load_num_data(quarter, ALL_TAGS)
    if len(num_df) == 0:
        return pd.DataFrame()
    
    merged = num_df.merge(
        sub_df[["adsh", "cik", "name", "sic", "fy", "fp"]], 
        on="adsh", 
        how="inner"
    )
    
    merged = merged[merged["coreg"].isna() | (merged["coreg"] == "")]
    
    results = []
    for (cik, fy), group in merged.groupby(["cik", "fy"]):
        if pd.isna(fy):
            continue
            
        row = {
            "cik": cik,
            "fiscal_year": int(fy) if fy else None,
            "company_name": group["name"].iloc[0],
            "sic": group["sic"].iloc[0],
            "quarter_source": quarter,
        }
        
        for component, tag_list in ROIC_TAGS.items():
            value = None
            
            if component in ["stockholders_equity", "cash", "long_term_debt", "short_term_debt"]:
                subset = group[(group["tag"].isin(tag_list)) & (group["qtrs"] == 0)]
            else:
                subset = group[(group["tag"].isin(tag_list)) & (group["qtrs"] == 4)]
                if len(subset) == 0:
                    subset = group[(group["tag"].isin(tag_list)) & (group["qtrs"] == 0)]
            
            if len(subset) > 0:
                for tag in tag_list:
                    tag_subset = subset[subset["tag"] == tag]
                    if len(tag_subset) > 0:
                        usd_subset = tag_subset[tag_subset["uom"] == "USD"]
                        if len(usd_subset) > 0:
                            value = usd_subset["value"].iloc[0]
                        else:
                            value = tag_subset["value"].iloc[0]
                        break
            
            row[component] = value
        
        results.append(row)
    
    return pd.DataFrame(results)


def extract_all_fundamentals() -> pd.DataFrame:
    """Extract fundamentals from all available quarters."""
    quarters = get_available_quarters()
    print(f"Found {len(quarters)} quarters to process")
    
    all_dfs = []
    for quarter in tqdm(quarters, desc="Extracting fundamentals"):
        df = extract_quarter_fundamentals(quarter)
        if len(df) > 0:
            all_dfs.append(df)
    
    if not all_dfs:
        return pd.DataFrame()
    
    combined = pd.concat(all_dfs, ignore_index=True)
    
    combined = combined.sort_values(["cik", "fiscal_year", "quarter_source"])
    combined = combined.drop_duplicates(subset=["cik", "fiscal_year"], keep="last")
    
    return combined.reset_index(drop=True)


if __name__ == "__main__":
    print("Extracting fundamentals from SEC data...")
    df = extract_all_fundamentals()
    print(f"\nExtracted {len(df)} company-year records")
    print(f"Unique companies: {df['cik'].nunique()}")
    print(f"Fiscal years: {sorted(df['fiscal_year'].dropna().unique())}")
    print("\nSample data:")
    print(df.head(10))
    print("\nMissing value counts:")
    for col in ROIC_TAGS.keys():
        missing = df[col].isna().sum()
        pct = missing / len(df) * 100
        print(f"  {col}: {missing} ({pct:.1f}%)")
