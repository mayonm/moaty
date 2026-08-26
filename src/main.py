"""
Moaty Data Pipeline - Main Entry Point

Orchestrates the full data cleaning pipeline:
1. Download SEC EDGAR data (if not present)
2. Download Damodaran benchmarks (if not present)
3. Extract fundamentals from XBRL
4. Compute ROIC
5. Build company universe
6. Download prices
7. Export datasets
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.download_sec import download_all_quarters
from src.ingest.download_damodaran import download_damodaran_files
from src.ingest.download_prices import download_prices_for_universe
from src.transform.extract_fundamentals import extract_all_fundamentals
from src.transform.build_universe import build_universe
from src.output.export_datasets import export_fundamentals, export_prices, generate_quality_report


def run_pipeline(
    skip_download: bool = False,
    min_consecutive_years: int = 5,
    target_companies: int = 100
):
    """
    Run the complete Moaty data pipeline.
    
    Args:
        skip_download: Skip downloading if data already exists
        min_consecutive_years: Minimum years of ROIC data required
        target_companies: Target number of companies in final dataset
    """
    print("=" * 60)
    print("MOATY DATA PIPELINE")
    print("=" * 60)
    
    if not skip_download:
        print("\n[1/7] Downloading SEC EDGAR data...")
        download_all_quarters()
        
        print("\n[2/7] Downloading Damodaran benchmarks...")
        download_damodaran_files()
    else:
        print("\n[1/7] Skipping SEC download (skip_download=True)")
        print("[2/7] Skipping Damodaran download (skip_download=True)")
    
    print("\n[3/7] Extracting fundamentals from SEC filings...")
    fundamentals = extract_all_fundamentals()
    print(f"  Extracted {len(fundamentals)} company-year records")
    
    print("\n[4/7] Building company universe (computing ROIC, filtering)...")
    universe, stats = build_universe(
        fundamentals,
        min_consecutive_years=min_consecutive_years,
        exclude_financial=True,
        target_company_count=target_companies
    )
    print(f"  Universe: {universe['cik'].nunique()} companies, {len(universe)} records")
    
    print("\n[5/7] Downloading stock prices...")
    prices = download_prices_for_universe(universe, start_date="2016-01-01")
    print(f"  Downloaded {len(prices)} price records")
    
    print("\n[6/7] Exporting datasets...")
    fund_path = export_fundamentals(universe)
    price_path = export_prices(prices)
    
    print("\n[7/7] Generating quality report...")
    
    fund_df = __import__("pandas").read_parquet(fund_path)
    price_df = __import__("pandas").read_parquet(price_path)
    report_path = generate_quality_report(stats, fund_df, price_df)
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\nOutput files:")
    print(f"  - {fund_path}")
    print(f"  - {price_path}")
    print(f"  - {report_path}")
    
    print(f"\nFinal dataset:")
    print(f"  - Companies: {fund_df['ticker'].nunique()}")
    print(f"  - Fundamentals records: {len(fund_df)}")
    print(f"  - Price records: {len(price_df)}")
    print(f"  - Year range: {int(fund_df['year'].min())} - {int(fund_df['year'].max())}")
    
    return fund_df, price_df, stats


if __name__ == "__main__":
    run_pipeline(skip_download=True)
