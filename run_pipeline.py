#!/usr/bin/env python3
"""
Moaty Pipeline Orchestrator

Runs the complete Moaty pipeline from data download to forecast generation.
This is the single entry point for rebuilding the entire system.

Usage:
    python run_pipeline.py [--skip-download] [--force-download]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).parent
SRC_DIR = WORKSPACE / "src"
JULIA_DIR = WORKSPACE / "julia"
R_DIR = WORKSPACE / "R"
DATA_DIR = WORKSPACE / "data"
DB_PATH = WORKSPACE / "moaty.db"


def run_step(name: str, cmd: list, cwd: Path = WORKSPACE) -> bool:
    """Run a pipeline step and return success status."""
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=False,
            text=True,
            env={**subprocess.os.environ, "WORKSPACE": str(WORKSPACE)}
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"\n✓ {name} completed successfully ({elapsed:.1f}s)")
            return True
        else:
            print(f"\n✗ {name} failed with exit code {result.returncode} ({elapsed:.1f}s)")
            return False
            
    except Exception as e:
        print(f"\n✗ {name} failed with exception: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Moaty pipeline")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip SEC EDGAR download (use existing data)")
    parser.add_argument("--force-download", action="store_true",
                        help="Force re-download of SEC EDGAR data")
    parser.add_argument("--skip-prices", action="store_true",
                        help="Skip price download (use existing data)")
    args = parser.parse_args()
    
    print("="*60)
    print("MOATY PIPELINE")
    print("Economic Moat Decay Prediction System")
    print("="*60)
    
    start_time = time.time()
    steps_completed = 0
    steps_failed = 0
    
    # Step 1: Download SEC EDGAR data
    if args.skip_download:
        print("\n[Skipping SEC EDGAR download]")
    else:
        download_cmd = [sys.executable, str(SRC_DIR / "download_edgar.py")]
        if args.force_download:
            download_cmd.append("--force")
        
        if run_step("SEC EDGAR Download", download_cmd):
            steps_completed += 1
        else:
            steps_failed += 1
            print("WARNING: Download failed, continuing with existing data...")
    
    # Step 2: Parse fundamentals and compute ROIC
    if run_step("Parse Fundamentals", [sys.executable, str(SRC_DIR / "parse_fundamentals.py")]):
        steps_completed += 1
    else:
        steps_failed += 1
        print("ERROR: Fundamentals parsing failed. Cannot continue.")
        return 1
    
    # Step 3: Download price data
    if args.skip_prices:
        print("\n[Skipping price download]")
    else:
        if run_step("Download Prices", [sys.executable, str(SRC_DIR / "download_prices.py")]):
            steps_completed += 1
        else:
            steps_failed += 1
            print("WARNING: Price download failed, continuing...")
    
    # Step 4: Load into SQLite
    if run_step("Load SQLite", [sys.executable, str(SRC_DIR / "load_sqlite.py")]):
        steps_completed += 1
    else:
        steps_failed += 1
        print("ERROR: SQLite load failed. Cannot continue.")
        return 1
    
    # Step 5: Julia decay fitting
    julia_cmd = ["julia", str(JULIA_DIR / "fit_decay.jl")]
    if run_step("Julia Decay Fitting", julia_cmd):
        steps_completed += 1
        
        # Load Julia results into SQLite
        print("\nLoading decay fits into SQLite...")
        import sqlite3
        import pandas as pd
        
        fits_csv = DATA_DIR / "decay_fits.csv"
        if fits_csv.exists():
            df = pd.read_csv(fits_csv)
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM decay_fits")
            df.to_sql('decay_fits', conn, if_exists='append', index=False)
            conn.close()
            print(f"Loaded {len(df)} decay fits")
    else:
        steps_failed += 1
        print("ERROR: Julia fitting failed. Cannot continue.")
        return 1
    
    # Step 6: R validation
    r_cmd = ["Rscript", str(R_DIR / "validate_fits.R")]
    r_env = {**subprocess.os.environ, "WORKSPACE": str(WORKSPACE), "R_LIBS_USER": str(Path.home() / "R" / "library")}
    
    try:
        result = subprocess.run(r_cmd, cwd=WORKSPACE, env=r_env, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
            steps_completed += 1
            print("✓ R Validation completed successfully")
        else:
            print(result.stderr)
            steps_failed += 1
            print("WARNING: R validation failed, continuing...")
    except Exception as e:
        print(f"WARNING: R validation error: {e}")
        steps_failed += 1
    
    # Step 7: Generate forecasts
    if run_step("Generate Forecasts", [sys.executable, str(SRC_DIR / "forecasts.py")]):
        steps_completed += 1
    else:
        steps_failed += 1
        print("WARNING: Forecast generation failed")
    
    # Final summary
    total_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"Steps completed: {steps_completed}")
    print(f"Steps failed: {steps_failed}")
    print(f"Total time: {total_time/60:.1f} minutes")
    
    # Database summary
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n=== Database Summary ===")
        for table in ['fundamentals', 'prices', 'decay_fits', 'validation', 'forecasts']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count:,} rows")
        
        # Company counts
        cursor.execute("SELECT COUNT(DISTINCT cik) FROM fundamentals")
        n_companies = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM decay_fits WHERE converged = 1")
        n_converged = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM validation WHERE p_value < 0.05")
        n_significant = cursor.fetchone()[0]
        
        print(f"\n=== Key Metrics ===")
        print(f"  Total companies: {n_companies:,}")
        print(f"  Converged fits: {n_converged:,}")
        print(f"  Significant λ (p<0.05): {n_significant:,}")
        
        conn.close()
    
    print("\n" + "="*60)
    print("To start the local website:")
    print("  1. Backend: cd api && uvicorn main:app --reload")
    print("  2. Frontend: cd web && npm run dev")
    print("="*60)
    
    return 0 if steps_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
