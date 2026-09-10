"""
Kalshi API Client

Fetches prediction market data from Kalshi's public API.
No authentication required for market data endpoints.
"""

import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Common company tickers and their variations for search
TICKER_VARIATIONS = {
    "AAPL": ["apple", "aapl"],
    "GOOGL": ["google", "alphabet", "googl", "goog"],
    "MSFT": ["microsoft", "msft"],
    "AMZN": ["amazon", "amzn"],
    "TSLA": ["tesla", "tsla"],
    "META": ["meta", "facebook", "fb"],
    "NVDA": ["nvidia", "nvda"],
    "JPM": ["jpmorgan", "jp morgan", "jpm"],
    "V": ["visa"],
    "JNJ": ["johnson", "jnj"],
    "WMT": ["walmart", "wmt"],
    "PG": ["procter", "gamble", "pg"],
    "UNH": ["unitedhealth", "unh"],
    "HD": ["home depot", "hd"],
    "DIS": ["disney", "dis"],
    "NFLX": ["netflix", "nflx"],
    "INTC": ["intel", "intc"],
    "AMD": ["amd"],
    "CRM": ["salesforce", "crm"],
}


@dataclass
class KalshiMarket:
    """Represents a Kalshi prediction market."""
    ticker: str
    title: str
    subtitle: Optional[str]
    yes_price: float  # 0-100 (cents), represents probability
    no_price: float
    volume: int
    open_interest: int
    close_time: Optional[datetime]
    status: str
    category: str
    url: str


class KalshiClient:
    """Client for interacting with Kalshi's public API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Moaty Research Tool"
        })
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the Kalshi API."""
        url = f"{BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Kalshi API error: {e}")
            return {}
    
    def get_markets(
        self,
        status: str = "open",
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict:
        """Get all markets with optional filters."""
        params = {
            "status": status,
            "limit": limit
        }
        if cursor:
            params["cursor"] = cursor
        
        return self._get("/markets", params)
    
    def search_markets(self, query: str, limit: int = 20) -> List[KalshiMarket]:
        """
        Search for markets related to a company or topic.
        
        Since Kalshi doesn't have a direct search endpoint, we:
        1. Fetch open markets
        2. Filter by keyword matching in title/subtitle
        """
        markets = []
        query_lower = query.lower()
        
        # Build search terms from query
        search_terms = [query_lower]
        
        # Add variations if query matches a known ticker
        for ticker, variations in TICKER_VARIATIONS.items():
            if query_lower in variations or query_lower == ticker.lower():
                search_terms.extend(variations)
                search_terms.append(ticker.lower())
                break
        
        search_terms = list(set(search_terms))
        
        # Fetch markets and filter
        try:
            result = self.get_markets(status="open", limit=200)
            raw_markets = result.get("markets", [])
            
            for m in raw_markets:
                title = m.get("title", "").lower()
                subtitle = (m.get("subtitle") or "").lower()
                
                # Check if any search term matches
                if any(term in title or term in subtitle for term in search_terms):
                    market = self._parse_market(m)
                    if market:
                        markets.append(market)
                
                if len(markets) >= limit:
                    break
            
        except Exception as e:
            print(f"Error searching Kalshi markets: {e}")
        
        return markets
    
    def get_markets_by_category(self, category: str, limit: int = 20) -> List[KalshiMarket]:
        """Get markets filtered by category (e.g., 'Economics', 'Tech')."""
        markets = []
        
        try:
            result = self.get_markets(status="open", limit=200)
            raw_markets = result.get("markets", [])
            
            for m in raw_markets:
                if m.get("category", "").lower() == category.lower():
                    market = self._parse_market(m)
                    if market:
                        markets.append(market)
                
                if len(markets) >= limit:
                    break
        
        except Exception as e:
            print(f"Error fetching category markets: {e}")
        
        return markets
    
    def get_stock_markets(self, ticker: str) -> List[KalshiMarket]:
        """
        Get prediction markets specifically about a stock.
        Searches for price targets, earnings, etc.
        """
        search_terms = [
            ticker.upper(),
            ticker.lower(),
        ]
        
        # Add company name variations
        if ticker.upper() in TICKER_VARIATIONS:
            search_terms.extend(TICKER_VARIATIONS[ticker.upper()])
        
        markets = []
        
        try:
            result = self.get_markets(status="open", limit=500)
            raw_markets = result.get("markets", [])
            
            for m in raw_markets:
                title = m.get("title", "").lower()
                subtitle = (m.get("subtitle") or "").lower()
                full_text = f"{title} {subtitle}"
                
                # Look for stock-related keywords
                is_stock_related = any(
                    term in full_text for term in search_terms
                )
                
                # Also match common patterns
                has_stock_pattern = any([
                    "stock" in full_text and any(t in full_text for t in search_terms),
                    "share" in full_text and any(t in full_text for t in search_terms),
                    "earnings" in full_text and any(t in full_text for t in search_terms),
                    "$" in title and any(t in full_text for t in search_terms),
                ])
                
                if is_stock_related or has_stock_pattern:
                    market = self._parse_market(m)
                    if market:
                        markets.append(market)
            
        except Exception as e:
            print(f"Error fetching stock markets: {e}")
        
        return markets
    
    def get_economic_markets(self, limit: int = 10) -> List[KalshiMarket]:
        """Get markets related to economic indicators (Fed, inflation, GDP, etc.)."""
        economic_terms = [
            "fed", "federal reserve", "interest rate",
            "inflation", "cpi", "gdp", "recession",
            "unemployment", "jobs", "economy"
        ]
        
        markets = []
        
        try:
            result = self.get_markets(status="open", limit=300)
            raw_markets = result.get("markets", [])
            
            for m in raw_markets:
                title = m.get("title", "").lower()
                subtitle = (m.get("subtitle") or "").lower()
                full_text = f"{title} {subtitle}"
                
                if any(term in full_text for term in economic_terms):
                    market = self._parse_market(m)
                    if market:
                        markets.append(market)
                
                if len(markets) >= limit:
                    break
        
        except Exception as e:
            print(f"Error fetching economic markets: {e}")
        
        return markets
    
    def _parse_market(self, data: Dict) -> Optional[KalshiMarket]:
        """Parse raw market data into KalshiMarket object."""
        try:
            # Get prices (in cents, 0-100)
            yes_price = data.get("yes_bid", 0) or data.get("last_price", 50) or 50
            no_price = 100 - yes_price
            
            # Parse close time
            close_time = None
            if data.get("close_time"):
                try:
                    close_time = datetime.fromisoformat(
                        data["close_time"].replace("Z", "+00:00")
                    )
                except:
                    pass
            
            return KalshiMarket(
                ticker=data.get("ticker", ""),
                title=data.get("title", "Unknown Market"),
                subtitle=data.get("subtitle"),
                yes_price=yes_price,
                no_price=no_price,
                volume=data.get("volume", 0) or 0,
                open_interest=data.get("open_interest", 0) or 0,
                close_time=close_time,
                status=data.get("status", "unknown"),
                category=data.get("category", ""),
                url=f"https://kalshi.com/markets/{data.get('ticker', '')}"
            )
        except Exception as e:
            print(f"Error parsing market: {e}")
            return None
    
    def format_markets_for_prompt(self, markets: List[KalshiMarket]) -> str:
        """Format markets for inclusion in AI prompt."""
        if not markets:
            return "No relevant prediction markets found."
        
        lines = ["Relevant Kalshi Prediction Markets:"]
        
        for m in markets[:10]:  # Limit to 10 for prompt size
            prob = m.yes_price
            close_str = ""
            if m.close_time:
                close_str = f" (closes {m.close_time.strftime('%Y-%m-%d')})"
            
            lines.append(
                f"- {m.title}: {prob}% YES probability{close_str}"
            )
            if m.subtitle:
                lines.append(f"  Context: {m.subtitle}")
        
        return "\n".join(lines)


# Singleton instance
_client: Optional[KalshiClient] = None

def get_kalshi_client() -> KalshiClient:
    """Get or create the Kalshi client singleton."""
    global _client
    if _client is None:
        _client = KalshiClient()
    return _client


if __name__ == "__main__":
    # Test the client
    client = get_kalshi_client()
    
    print("Testing Kalshi client...")
    
    # Test market search
    markets = client.search_markets("Apple")
    print(f"\nFound {len(markets)} markets for 'Apple':")
    for m in markets[:5]:
        print(f"  - {m.title} ({m.yes_price}% YES)")
    
    # Test economic markets
    econ = client.get_economic_markets(5)
    print(f"\nFound {len(econ)} economic markets:")
    for m in econ:
        print(f"  - {m.title} ({m.yes_price}% YES)")
