"""
Week 0 — Base Environment Test
Validates that Python can read all core data sources in the MOATY project.
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def show(df: pd.DataFrame, name: str):
    print(f"\n[{name}]  shape={df.shape}")
    print(f"  columns: {list(df.columns[:8])}{'...' if len(df.columns) > 8 else ''}")
    print(df.head(3).to_string(max_cols=6))


#  Financial Indicators CSV 
section("Financial Indicators (2014_Financial_Data.csv)")
fin = pd.read_csv(DATA / "financial_indicators" / "2014_Financial_Data.csv")
show(fin, "2014_Financial_Data")

#  XBRL Quarter Reports (2017 Q1) 
section("XBRL Quarter Reports — 2017q1")

q1 = DATA / "quarter_reports" / "2017q1"

sub = pd.read_csv(q1 / "sub.txt", sep="\t", dtype=str, low_memory=False)
show(sub, "sub.txt  [submissions]")

num = pd.read_csv(q1 / "num.txt", sep="\t", dtype=str, low_memory=False)
show(num, "num.txt  [numeric values]")

tag = pd.read_csv(q1 / "tag.txt", sep="\t", dtype=str, low_memory=False)
show(tag, "tag.txt  [tag taxonomy]")

#  Damodaran XLS Models 
section("Damodaran XLS Models")

wacc = pd.read_excel(DATA / "wacc.xls", sheet_name=0, engine="xlrd")
show(wacc, "wacc.xls")

roc = pd.read_excel(DATA / "roc.xls", sheet_name=0, engine="xlrd")
show(roc, "roc.xls")

print("\n\nAll data sources loaded successfully.")
