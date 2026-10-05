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
import time

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
SEARCH_URL = "https://api.elections.kalshi.com/v1/search/series"

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
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 120
    
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

        Uses Kalshi's series search, which returns event titles and prices.
        The open-markets feed is mostly parlays and is not useful for company search.
        """
        query = (query or "").strip()
        if not query:
            return []

        cache_key = f"{query.lower()}::{limit}"
        cached = self._cache.get(cache_key)
        now = time.time()
        if cached and now - cached[0] < self._cache_ttl:
            return cached[1]

        markets = self._search_series(query, limit)
        if not markets:
            markets = self._search_open_markets(query, limit)

        matched = [m for m in markets if self._title_matches(m.title, query)]
        if matched:
            markets = matched[:limit]

        self._cache[cache_key] = (now, markets)
        return markets

    def _title_matches(self, title: str, query: str) -> bool:
        """Keep markets that actually mention the company, not a loose neighbor."""
        title_l = (title or "").lower()
        query_l = query.lower().strip()
        if len(query_l) >= 3 and query_l in title_l:
            return True

        aliases = []
        for ticker, variations in TICKER_VARIATIONS.items():
            names = [ticker.lower(), *variations]
            if query_l == ticker.lower() or query_l in variations:
                aliases = [name for name in names if len(name) >= 4]
                break
        return any(alias in title_l for alias in aliases)

    def _search_series(self, query: str, limit: int) -> List[KalshiMarket]:
        """Search series and keep the strongest market from each event."""
        try:
            response = self.session.get(
                SEARCH_URL,
                params={"query": query, "page_size": max(limit, 8)},
                timeout=12,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Kalshi search error: {e}")
            return []

        markets: List[KalshiMarket] = []
        seen = set()
        for event in payload.get("current_page") or []:
            nested = event.get("markets") or []
            if not nested:
                continue
            best = max(nested, key=lambda item: item.get("score") or 0)
            market = self._parse_market(
                best,
                series_ticker=event.get("series_ticker"),
                fallback_title=event.get("event_title") or event.get("series_title"),
            )
            if market and market.ticker not in seen:
                seen.add(market.ticker)
                markets.append(market)
            if len(markets) >= limit:
                break
        return markets

    def _search_open_markets(self, query: str, limit: int) -> List[KalshiMarket]:
        """Keyword fallback against a page of open markets."""
        markets = []
        query_lower = query.lower()
        search_terms = [query_lower]

        for ticker, variations in TICKER_VARIATIONS.items():
            if query_lower in variations or query_lower == ticker.lower():
                search_terms.extend(variations)
                search_terms.append(ticker.lower())
                break

        search_terms = list(set(search_terms))

        try:
            result = self.get_markets(status="open", limit=200)
            raw_markets = result.get("markets", [])

            for raw in raw_markets:
                title = raw.get("title", "").lower()
                subtitle = (raw.get("subtitle") or "").lower()
                if any(term in title or term in subtitle for term in search_terms):
                    market = self._parse_market(raw)
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
        query = ticker
        if ticker.upper() in TICKER_VARIATIONS:
            query = TICKER_VARIATIONS[ticker.upper()][0]
        return self.search_markets(query, limit=5)
    
    def get_economic_markets(self, limit: int = 10) -> List[KalshiMarket]:
        """Get markets related to economic indicators (Fed, inflation, GDP, etc.)."""
        markets = self._search_series("federal reserve", limit=limit)
        return markets or self.search_markets("inflation", limit=limit)
    
    def _yes_price(self, data: Dict) -> float:
        """Normalize a market price to a 0-100 YES probability."""
        if data.get("last_price") is not None:
            price = float(data["last_price"])
            if price <= 1:
                price *= 100
            return max(0.0, min(100.0, price))

        for key in ("last_price_dollars", "yes_bid_dollars", "yes_ask_dollars"):
            if data.get(key) not in (None, ""):
                return max(0.0, min(100.0, float(data[key]) * 100))

        if data.get("yes_bid") is not None:
            price = float(data["yes_bid"])
            if price <= 1:
                price *= 100
            return max(0.0, min(100.0, price))

        return 50.0

    def _parse_market(
        self,
        data: Dict,
        series_ticker: Optional[str] = None,
        fallback_title: Optional[str] = None,
    ) -> Optional[KalshiMarket]:
        """Parse raw market data into KalshiMarket object."""
        try:
            yes_price = self._yes_price(data)
            no_price = max(0.0, 100 - yes_price)

            close_time = None
            close_raw = data.get("close_time") or data.get("close_ts")
            if close_raw:
                try:
                    close_time = datetime.fromisoformat(str(close_raw).replace("Z", "+00:00"))
                except Exception:
                    close_time = None

            volume_raw = data.get("volume") or data.get("volume_fp") or 0
            try:
                volume = int(float(volume_raw))
            except (TypeError, ValueError):
                volume = 0

            ticker = data.get("ticker", "") or ""
            series = series_ticker or data.get("series_ticker") or ticker
            title = data.get("title") or fallback_title or "Unknown Market"
            subtitle = data.get("subtitle") or data.get("yes_subtitle")

            return KalshiMarket(
                ticker=ticker,
                title=title,
                subtitle=subtitle,
                yes_price=yes_price,
                no_price=no_price,
                volume=volume,
                open_interest=data.get("open_interest", 0) or 0,
                close_time=close_time,
                status=data.get("status", "open"),
                category=data.get("category", ""),
                url=f"https://kalshi.com/markets/{str(series).lower()}"
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
