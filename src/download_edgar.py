"""
SEC EDGAR Financial Statement Data Sets Downloader

Downloads quarterly bulk data files from SEC EDGAR for 2017q1 through 2026q1.
Each quarter contains: sub.txt, num.txt, tag.txt, pre.txt
"""

import os
import zipfile
import requests
from pathlib import Path
from typing import List, Tuple
import time

# SEC requires a User-Agent header
HEADERS = {
    "User-Agent": "Moaty Research Tool contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}

BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
DATA_DIR = Path(__file__).parent.parent / "data" / "quarter_reports"


def get_quarters_to_download(start_year: int = 2017, start_q: int = 1,
                              end_year: int = 2026, end_q: int = 1) -> List[Tuple[int, int]]:
    """Generate list of (year, quarter) tuples to download."""
    quarters = []
    for year in range(start_year, end_year + 1):
        for q in range(1, 5):
            if year == start_year and q < start_q:
                continue
            if year == end_year and q > end_q:
                continue
            quarters.append((year, q))
    return quarters


def download_quarter(year: int, quarter: int, force: bool = False) -> bool:
    """
    Download and extract a single quarter's data.
    Returns True if successful, False otherwise.
    """
    quarter_dir = DATA_DIR / f"{year}q{quarter}"
    
    # Check if already downloaded
    if not force and quarter_dir.exists():
        required_files = ["sub.txt", "num.txt"]
        if all((quarter_dir / f).exists() for f in required_files):
            print(f"  {year}q{quarter}: Already exists, skipping")
            return True
    
    # Construct URL
    url = f"{BASE_URL}/{year}q{quarter}.zip"
    
    try:
        print(f"  {year}q{quarter}: Downloading from {url}")
        response = requests.get(url, headers=HEADERS, timeout=60)
        
        if response.status_code == 404:
            print(f"  {year}q{quarter}: Not found (404), may not be available yet")
            return False
        
        response.raise_for_status()
        
        # Create directory and extract
        quarter_dir.mkdir(parents=True, exist_ok=True)
        zip_path = quarter_dir / "temp.zip"
        
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(quarter_dir)
        
        zip_path.unlink()
        print(f"  {year}q{quarter}: Downloaded and extracted successfully")
        
        # Be nice to SEC servers
        time.sleep(0.5)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"  {year}q{quarter}: Error downloading - {e}")
        return False
    except zipfile.BadZipFile as e:
        print(f"  {year}q{quarter}: Error extracting - {e}")
        return False


def download_all_quarters(start_year: int = 2017, start_q: int = 1,
                          end_year: int = 2026, end_q: int = 1,
                          force: bool = False) -> dict:
    """
    Download all quarters in the specified range.
    Returns dict with success/failure counts.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    quarters = get_quarters_to_download(start_year, start_q, end_year, end_q)
    
    print(f"Downloading SEC EDGAR data for {len(quarters)} quarters...")
    
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    for year, quarter in quarters:
        success = download_quarter(year, quarter, force=force)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
    
    print(f"\nDownload complete: {results['success']} success, {results['failed']} failed")
    return results


def get_available_quarters() -> List[Tuple[int, int]]:
    """Return list of quarters that have been downloaded."""
    if not DATA_DIR.exists():
        return []
    
    quarters = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and "q" in d.name:
            try:
                year = int(d.name[:4])
                q = int(d.name[5])
                if (d / "sub.txt").exists() and (d / "num.txt").exists():
                    quarters.append((year, q))
            except (ValueError, IndexError):
                continue
    return quarters


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download SEC EDGAR quarterly data")
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--start-q", type=int, default=1)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--end-q", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="Re-download even if exists")
    args = parser.parse_args()
    
    download_all_quarters(
        start_year=args.start_year,
        start_q=args.start_q,
        end_year=args.end_year,
        end_q=args.end_q,
        force=args.force
    )
