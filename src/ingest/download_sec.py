"""
Download SEC EDGAR Financial Statement Data Sets.

Downloads quarterly ZIP files from SEC and extracts sub.txt, num.txt files.
Source: https://www.sec.gov/dera/data/financial-statement-data-sets
"""

import os
import zipfile
import requests
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm

SEC_BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "sec"


def get_quarters(start_year: int = 2017, end_year: int = 2026) -> List[str]:
    """Generate list of quarters from start_year Q1 to end_year Q2."""
    quarters = []
    for year in range(start_year, end_year + 1):
        for q in range(1, 5):
            if year == end_year and q > 2:
                break
            quarters.append(f"{year}q{q}")
    return quarters


def download_quarter(quarter: str, output_dir: Path) -> Tuple[bool, str]:
    """Download and extract a single quarter's data."""
    zip_url = f"{SEC_BASE_URL}/{quarter}.zip"
    quarter_dir = output_dir / quarter
    
    if quarter_dir.exists() and (quarter_dir / "sub.txt").exists():
        return True, f"{quarter}: already exists"
    
    quarter_dir.mkdir(parents=True, exist_ok=True)
    zip_path = quarter_dir / f"{quarter}.zip"
    
    try:
        headers = {
            "User-Agent": "Moaty Research Project contact@example.com",
            "Accept-Encoding": "gzip, deflate",
        }
        response = requests.get(zip_url, headers=headers, timeout=120)
        response.raise_for_status()
        
        with open(zip_path, "wb") as f:
            f.write(response.content)
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            for filename in ["sub.txt", "num.txt", "tag.txt", "pre.txt"]:
                if filename in zf.namelist():
                    zf.extract(filename, quarter_dir)
        
        zip_path.unlink()
        return True, f"{quarter}: downloaded and extracted"
        
    except requests.exceptions.HTTPError as e:
        return False, f"{quarter}: HTTP error {e.response.status_code}"
    except Exception as e:
        return False, f"{quarter}: error - {str(e)}"


def download_all_quarters(start_year: int = 2017, end_year: int = 2026) -> dict:
    """Download all quarters and return summary."""
    quarters = get_quarters(start_year, end_year)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": [], "skipped": []}
    
    print(f"Downloading {len(quarters)} quarters of SEC data...")
    for quarter in tqdm(quarters, desc="Downloading"):
        success, msg = download_quarter(quarter, RAW_DIR)
        if success:
            if "already exists" in msg:
                results["skipped"].append(quarter)
            else:
                results["success"].append(quarter)
        else:
            results["failed"].append((quarter, msg))
            print(f"\n  Warning: {msg}")
    
    print(f"\nDownload complete:")
    print(f"  New downloads: {len(results['success'])}")
    print(f"  Already existed: {len(results['skipped'])}")
    print(f"  Failed: {len(results['failed'])}")
    
    return results


if __name__ == "__main__":
    download_all_quarters()
