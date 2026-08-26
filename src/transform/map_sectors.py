"""
Map SEC SIC codes to Damodaran industry categories.
"""

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

_SIC_MAPPING: Optional[dict] = None


def load_sic_mapping() -> dict:
    """Load SIC to Damodaran industry mapping."""
    global _SIC_MAPPING
    if _SIC_MAPPING is None:
        mapping_file = CONFIG_DIR / "sic_to_damodaran.json"
        with open(mapping_file) as f:
            _SIC_MAPPING = json.load(f)
        _SIC_MAPPING.pop("_comment", None)
    return _SIC_MAPPING


def sic_to_damodaran(sic_code: str) -> Optional[str]:
    """
    Map a 4-digit SIC code to Damodaran industry.
    
    Uses first 2 digits (major group) for mapping.
    Returns None if no mapping found.
    """
    if not sic_code or len(str(sic_code)) < 2:
        return None
    
    mapping = load_sic_mapping()
    sic_2digit = str(sic_code)[:2].zfill(2)
    
    return mapping.get(sic_2digit)


def is_financial_sector(sic_code: str) -> bool:
    """Check if SIC code is in the financial sector (6000-6999)."""
    if not sic_code:
        return False
    try:
        sic_int = int(sic_code)
        return 6000 <= sic_int <= 6999
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    mapping = load_sic_mapping()
    print(f"Loaded {len(mapping)} SIC-to-Damodaran mappings")
    print("\nSample mappings:")
    for sic, industry in list(mapping.items())[:10]:
        print(f"  SIC {sic}: {industry}")
