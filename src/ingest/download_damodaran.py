"""
Download Damodaran sector data from NYU Stern.

Downloads wacc.xls and roc.xls files containing sector-level benchmarks.
Source: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html
"""

import requests
from pathlib import Path

DAMODARAN_URLS = {
    "wacc.xls": "https://www.stern.nyu.edu/~adamodar/pc/datasets/wacc.xls",
    "roc.xls": "https://www.stern.nyu.edu/~adamodar/pc/datasets/roc.xls",
}

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "damodaran"


def download_damodaran_files() -> dict:
    """Download Damodaran wacc.xls and roc.xls files."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {"success": [], "failed": []}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    for filename, url in DAMODARAN_URLS.items():
        filepath = RAW_DIR / filename
        
        if filepath.exists():
            print(f"{filename}: already exists, skipping")
            results["success"].append(filename)
            continue
        
        try:
            print(f"Downloading {filename}...")
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            print(f"  Saved to {filepath} ({len(response.content) / 1024:.1f} KB)")
            results["success"].append(filename)
            
        except Exception as e:
            print(f"  Error downloading {filename}: {e}")
            results["failed"].append((filename, str(e)))
    
    return results


if __name__ == "__main__":
    download_damodaran_files()
