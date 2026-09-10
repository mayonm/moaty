"""
Research Service

Orchestrates data gathering from multiple sources and AI analysis.
Combines Kalshi prediction markets, database fundamentals, and Gemini AI.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import uuid

from .kalshi_client import get_kalshi_client, KalshiMarket
from .gemini_client import get_gemini_client, GeminiClient


DB_PATH = Path(__file__).parent.parent / "moaty.db"


@dataclass
class ResearchResult:
    """Result of a company research query."""
    session_id: str
    company_name: str
    ticker: Optional[str] = None
    
    # Data sources
    fundamentals: Optional[Dict] = None
    kalshi_markets: List[KalshiMarket] = field(default_factory=list)
    
    # AI analysis
    analysis: str = ""
    
    # Metadata
    data_sources_used: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ResearchService:
    """Service for conducting company research."""
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the research service.
        
        Args:
            gemini_api_key: Optional API key for Gemini (can be set later)
        """
        self.kalshi = get_kalshi_client()
        self.gemini = get_gemini_client()
        
        if gemini_api_key:
            self.gemini.set_api_key(gemini_api_key)
        
        # Store research sessions for follow-up chat
        self.sessions: Dict[str, ResearchResult] = {}
    
    def set_api_key(self, api_key: str):
        """Set the Gemini API key."""
        self.gemini.set_api_key(api_key)
    
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self.gemini.is_configured()
    
    def _get_db_fundamentals(self, identifier: str) -> Optional[Dict]:
        """
        Fetch company fundamentals from the database.
        
        Args:
            identifier: Company ticker or CIK
            
        Returns:
            Dictionary with fundamentals data, or None if not found
        """
        if not DB_PATH.exists():
            return None
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            
            # Find company by ticker or name pattern
            fit = conn.execute("""
                SELECT * FROM decay_fits 
                WHERE ticker = ? OR company_name LIKE ? OR cik = ?
                LIMIT 1
            """, [identifier, f"%{identifier}%", identifier]).fetchone()
            
            if not fit:
                conn.close()
                return None
            
            cik = fit["cik"]
            
            # Get ROIC history
            roic_rows = conn.execute("""
                SELECT fiscal_year, roic
                FROM fundamentals
                WHERE cik = ? AND roic IS NOT NULL
                ORDER BY fiscal_year
            """, [cik]).fetchall()
            
            # Get sector
            sector_row = conn.execute("""
                SELECT sector FROM fundamentals WHERE cik = ? AND sector IS NOT NULL LIMIT 1
            """, [cik]).fetchone()
            
            # Get validation data
            validation = conn.execute("""
                SELECT p_value, ci_low, ci_high FROM validation WHERE cik = ?
            """, [cik]).fetchone()
            
            conn.close()
            
            return {
                "cik": fit["cik"],
                "ticker": fit["ticker"],
                "company_name": fit["company_name"],
                "sector": sector_row["sector"] if sector_row else None,
                "roic_history": [(r["fiscal_year"], r["roic"]) for r in roic_rows],
                "decay_params": {
                    "lambda": fit["lambda"],
                    "roic_0": fit["roic_0"],
                    "roic_terminal": fit["roic_terminal"],
                    "r_squared": fit["r_squared"],
                    "converged": bool(fit["converged"]),
                    "n_periods": fit["n_periods"]
                },
                "validation": {
                    "p_value": validation["p_value"] if validation else None,
                    "ci_low": validation["ci_low"] if validation else None,
                    "ci_high": validation["ci_high"] if validation else None,
                } if validation else None
            }
            
        except Exception as e:
            print(f"Database error: {e}")
            return None
    
    def research(
        self,
        company_name: str,
        ticker: Optional[str] = None,
        include_kalshi: bool = True,
        include_fundamentals: bool = True,
        include_economic_context: bool = True
    ) -> ResearchResult:
        """
        Conduct research on a company.
        
        Args:
            company_name: Name of the company to research
            ticker: Optional stock ticker (helps with data matching)
            include_kalshi: Whether to fetch Kalshi prediction markets
            include_fundamentals: Whether to fetch database fundamentals
            include_economic_context: Whether to include general economic markets
            
        Returns:
            ResearchResult with gathered data and AI analysis
        """
        session_id = str(uuid.uuid4())
        result = ResearchResult(
            session_id=session_id,
            company_name=company_name,
            ticker=ticker
        )
        
        # Determine search terms
        search_term = ticker or company_name
        
        # 1. Fetch database fundamentals
        if include_fundamentals:
            try:
                fundamentals = self._get_db_fundamentals(search_term)
                if fundamentals:
                    result.fundamentals = fundamentals
                    result.data_sources_used.append("moaty_database")
                    
                    # Use ticker from database if we found it
                    if not ticker and fundamentals.get("ticker"):
                        result.ticker = fundamentals["ticker"]
                        search_term = fundamentals["ticker"]
            except Exception as e:
                result.errors.append(f"Database lookup failed: {str(e)}")
        
        # 2. Fetch Kalshi markets
        kalshi_markets = []
        if include_kalshi:
            try:
                # Search for company-specific markets
                company_markets = self.kalshi.search_markets(search_term, limit=5)
                kalshi_markets.extend(company_markets)
                
                # Also search by ticker if different
                if ticker and ticker.lower() != company_name.lower():
                    ticker_markets = self.kalshi.get_stock_markets(ticker)
                    for m in ticker_markets:
                        if m not in kalshi_markets:
                            kalshi_markets.append(m)
                
                if kalshi_markets:
                    result.data_sources_used.append("kalshi_markets")
                
            except Exception as e:
                result.errors.append(f"Kalshi lookup failed: {str(e)}")
        
        # 3. Add economic context markets
        if include_economic_context:
            try:
                econ_markets = self.kalshi.get_economic_markets(limit=5)
                kalshi_markets.extend(econ_markets)
            except Exception as e:
                result.errors.append(f"Economic markets lookup failed: {str(e)}")
        
        result.kalshi_markets = kalshi_markets
        
        # 4. Generate AI analysis
        if self.gemini.is_configured():
            try:
                # Format Kalshi data for prompt
                kalshi_text = self.kalshi.format_markets_for_prompt(kalshi_markets)
                
                # Generate analysis
                analysis = self.gemini.analyze_company_sync(
                    company_name=company_name,
                    ticker=result.ticker,
                    fundamentals=result.fundamentals,
                    kalshi_markets=kalshi_text if kalshi_markets else None
                )
                
                result.analysis = analysis
                result.data_sources_used.append("gemini_ai")
                
            except Exception as e:
                result.errors.append(f"AI analysis failed: {str(e)}")
                result.analysis = f"Error generating analysis: {str(e)}"
        else:
            result.analysis = "Gemini API key not configured. Please provide your API key to enable AI analysis."
        
        # Store session for follow-up
        self.sessions[session_id] = result
        
        return result
    
    def chat(self, session_id: str, message: str) -> str:
        """
        Continue a chat conversation about a researched company.
        
        Args:
            session_id: The session ID from a previous research() call
            message: User's follow-up question
            
        Returns:
            AI response
        """
        if not self.gemini.is_configured():
            return "Error: Gemini API key not configured."
        
        # Get session context
        session = self.sessions.get(session_id)
        
        context = None
        if session:
            # Build context from session data
            context_parts = [f"Company: {session.company_name}"]
            if session.ticker:
                context_parts.append(f"Ticker: {session.ticker}")
            if session.fundamentals:
                context_parts.append(f"Sector: {session.fundamentals.get('sector', 'Unknown')}")
                if session.fundamentals.get('decay_params'):
                    params = session.fundamentals['decay_params']
                    context_parts.append(f"Decay Rate (λ): {params.get('lambda', 'N/A')}")
            context = "\n".join(context_parts)
        
        return self.gemini.chat(session_id, message, context)
    
    def clear_session(self, session_id: str):
        """Clear a research session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
        self.gemini.clear_chat(session_id)
    
    def get_session(self, session_id: str) -> Optional[ResearchResult]:
        """Get a stored research session."""
        return self.sessions.get(session_id)
    
    def search_companies(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for companies in the database.
        
        Args:
            query: Search term (ticker, name, or partial match)
            limit: Maximum results to return
            
        Returns:
            List of matching companies
        """
        if not DB_PATH.exists():
            return []
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            
            results = conn.execute("""
                SELECT DISTINCT 
                    d.ticker, 
                    d.company_name, 
                    d.lambda,
                    d.r_squared,
                    f.sector
                FROM decay_fits d
                LEFT JOIN (SELECT cik, sector FROM fundamentals GROUP BY cik) f ON d.cik = f.cik
                WHERE d.converged = 1 AND (
                    d.ticker LIKE ? OR 
                    d.company_name LIKE ?
                )
                ORDER BY d.r_squared DESC
                LIMIT ?
            """, [f"%{query}%", f"%{query}%", limit]).fetchall()
            
            conn.close()
            
            return [
                {
                    "ticker": r["ticker"],
                    "company_name": r["company_name"],
                    "lambda": r["lambda"],
                    "r_squared": r["r_squared"],
                    "sector": r["sector"]
                }
                for r in results
            ]
            
        except Exception as e:
            print(f"Search error: {e}")
            return []


# Singleton instance
_service: Optional[ResearchService] = None


def get_research_service() -> ResearchService:
    """Get or create the research service singleton."""
    global _service
    if _service is None:
        _service = ResearchService()
    return _service


if __name__ == "__main__":
    # Test the service
    import os
    
    service = get_research_service()
    
    # Check if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        service.set_api_key(api_key)
        print("Testing research service with Gemini API...")
    else:
        print("Testing research service without Gemini API (data gathering only)...")
    
    # Test research
    result = service.research("Apple", ticker="AAPL")
    
    print(f"\nSession ID: {result.session_id}")
    print(f"Company: {result.company_name}")
    print(f"Ticker: {result.ticker}")
    print(f"Data sources: {result.data_sources_used}")
    print(f"Errors: {result.errors}")
    
    if result.fundamentals:
        print(f"\nFundamentals found:")
        print(f"  Sector: {result.fundamentals.get('sector')}")
        print(f"  ROIC periods: {len(result.fundamentals.get('roic_history', []))}")
    
    if result.kalshi_markets:
        print(f"\nKalshi markets: {len(result.kalshi_markets)}")
        for m in result.kalshi_markets[:3]:
            print(f"  - {m.title} ({m.yes_price}% YES)")
    
    print(f"\nAnalysis preview:")
    print(result.analysis[:500] if len(result.analysis) > 500 else result.analysis)
