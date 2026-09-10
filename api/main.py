"""
Moaty API Server

FastAPI backend for AI-powered company research.
Combines Kalshi prediction markets, company fundamentals, and Gemini AI analysis.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import markdown

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.research_service import get_research_service, ResearchResult
from src.kalshi_client import get_kalshi_client

# Configuration
DB_PATH = Path(__file__).parent.parent / "moaty.db"
METHODOLOGY_PATH = Path(__file__).parent.parent / "METHODOLOGY.md"

app = FastAPI(
    title="Moaty API",
    description="AI-Powered Company Research Tool - Analyze competitive moats with prediction markets and AI",
    version="2.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    """Database connection context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ===================
# Request/Response Models
# ===================

# Research API models
class ResearchRequest(BaseModel):
    company_name: str
    ticker: Optional[str] = None
    api_key: Optional[str] = None
    include_kalshi: bool = True
    include_fundamentals: bool = True
    include_economic_context: bool = True


class ChatRequest(BaseModel):
    session_id: str
    message: str
    api_key: Optional[str] = None


class KalshiMarketResponse(BaseModel):
    ticker: str
    title: str
    subtitle: Optional[str]
    yes_price: float
    no_price: float
    volume: int
    close_time: Optional[str]
    url: str


class ResearchResponse(BaseModel):
    session_id: str
    company_name: str
    ticker: Optional[str]
    analysis: str
    kalshi_markets: List[KalshiMarketResponse]
    has_fundamentals: bool
    fundamentals_summary: Optional[dict]
    data_sources: List[str]
    errors: List[str]


class ChatResponse(BaseModel):
    response: str
    session_id: str


class SearchResult(BaseModel):
    ticker: Optional[str]
    company_name: Optional[str]
    lambda_: Optional[float]
    r_squared: Optional[float]
    sector: Optional[str]


# Legacy models (kept for backward compatibility)
class CompanySummary(BaseModel):
    cik: str
    ticker: Optional[str]
    company_name: Optional[str]
    lambda_: float
    roic_0: float
    roic_terminal: float
    r_squared: float
    converged: bool
    n_periods: int
    sector: Optional[str] = None

    class Config:
        populate_by_name = True


class CompanyDetail(BaseModel):
    cik: str
    ticker: Optional[str]
    company_name: Optional[str]
    lambda_: float
    roic_0: float
    roic_terminal: float
    r_squared: float
    converged: bool
    n_periods: int
    sector: Optional[str]
    p_value: Optional[float]
    ci_low: Optional[float]
    ci_high: Optional[float]
    holdout_rmse_model: Optional[float]
    holdout_rmse_naive: Optional[float]
    roic_series: List[dict]
    forecasts: List[dict]


class ValidationSummary(BaseModel):
    total_companies: int
    significant_lambda: int
    model_beats_naive: int
    lambda_price_correlation: Optional[float]
    mean_holdout_rmse_model: Optional[float]
    mean_holdout_rmse_naive: Optional[float]
    companies: List[dict]


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Moaty API",
        "version": "2.0.0",
        "description": "AI-Powered Company Research Tool",
        "endpoints": {
            "research": "/api/research (POST) - Analyze a company with AI",
            "chat": "/api/chat (POST) - Follow-up questions",
            "search": "/api/search - Search companies in database",
            "kalshi": "/api/kalshi/{query} - Get prediction markets",
            "leaderboard": "/api/leaderboard - Company rankings (legacy)",
            "company": "/api/company/{ticker} - Company details (legacy)",
            "validation": "/api/validation - Validation stats (legacy)",
            "methodology": "/api/methodology - Methodology docs"
        }
    }


# ===================
# Research API Endpoints
# ===================

@app.post("/api/research", response_model=ResearchResponse)
async def research_company(request: ResearchRequest):
    """
    Research a company using AI and prediction markets.
    
    Combines data from:
    - Kalshi prediction markets
    - Moaty database (ROIC history, decay parameters)
    - Gemini AI analysis
    
    Returns analysis and a session_id for follow-up chat.
    """
    service = get_research_service()
    
    # Set API key if provided
    if request.api_key:
        service.set_api_key(request.api_key)
    
    if not service.is_configured() and not request.api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key required. Provide it in the request or set GEMINI_API_KEY environment variable."
        )
    
    # Conduct research
    result = service.research(
        company_name=request.company_name,
        ticker=request.ticker,
        include_kalshi=request.include_kalshi,
        include_fundamentals=request.include_fundamentals,
        include_economic_context=request.include_economic_context
    )
    
    # Format Kalshi markets for response
    markets = []
    for m in result.kalshi_markets:
        markets.append(KalshiMarketResponse(
            ticker=m.ticker,
            title=m.title,
            subtitle=m.subtitle,
            yes_price=m.yes_price,
            no_price=m.no_price,
            volume=m.volume,
            close_time=m.close_time.isoformat() if m.close_time else None,
            url=m.url
        ))
    
    # Summarize fundamentals for response
    fundamentals_summary = None
    if result.fundamentals:
        decay = result.fundamentals.get("decay_params", {})
        fundamentals_summary = {
            "ticker": result.fundamentals.get("ticker"),
            "company_name": result.fundamentals.get("company_name"),
            "sector": result.fundamentals.get("sector"),
            "decay_rate": decay.get("lambda"),
            "initial_roic": decay.get("roic_0"),
            "terminal_roic": decay.get("roic_terminal"),
            "r_squared": decay.get("r_squared"),
            "roic_periods": len(result.fundamentals.get("roic_history", []))
        }
    
    return ResearchResponse(
        session_id=result.session_id,
        company_name=result.company_name,
        ticker=result.ticker,
        analysis=result.analysis,
        kalshi_markets=markets,
        has_fundamentals=result.fundamentals is not None,
        fundamentals_summary=fundamentals_summary,
        data_sources=result.data_sources_used,
        errors=result.errors
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_followup(request: ChatRequest):
    """
    Continue a conversation about a researched company.
    
    Requires a session_id from a previous /api/research call.
    """
    service = get_research_service()
    
    # Set API key if provided
    if request.api_key:
        service.set_api_key(request.api_key)
    
    if not service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Gemini API key required."
        )
    
    # Get chat response
    response = service.chat(request.session_id, request.message)
    
    return ChatResponse(
        response=response,
        session_id=request.session_id
    )


@app.get("/api/search")
async def search_companies(q: str = Query(..., min_length=1, description="Search query")):
    """
    Search for companies in the database.
    
    Matches against ticker and company name.
    """
    service = get_research_service()
    results = service.search_companies(q, limit=20)
    
    return {
        "query": q,
        "results": results
    }


@app.get("/api/kalshi/{query}")
async def get_kalshi_markets(query: str, limit: int = Query(10, ge=1, le=50)):
    """
    Get Kalshi prediction markets related to a query.
    
    Searches for company-specific and economic markets.
    """
    kalshi = get_kalshi_client()
    
    # Search for markets
    markets = kalshi.search_markets(query, limit=limit)
    
    # Also get economic context
    econ_markets = kalshi.get_economic_markets(limit=5)
    
    return {
        "query": query,
        "company_markets": [
            {
                "ticker": m.ticker,
                "title": m.title,
                "subtitle": m.subtitle,
                "yes_price": m.yes_price,
                "volume": m.volume,
                "url": m.url
            }
            for m in markets
        ],
        "economic_markets": [
            {
                "ticker": m.ticker,
                "title": m.title,
                "yes_price": m.yes_price,
                "url": m.url
            }
            for m in econ_markets
        ]
    }


# ===================
# Legacy API Endpoints (kept for backward compatibility)
# ===================


@app.get("/api/leaderboard")
async def get_leaderboard(
    sort_by: str = Query("lambda", description="Sort field: lambda, r_squared, roic_0"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get leaderboard of companies ranked by decay parameters."""
    
    valid_sort_fields = ["lambda", "r_squared", "roic_0", "roic_terminal", "n_periods"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(400, f"Invalid sort field. Must be one of: {valid_sort_fields}")
    
    order = "ASC" if sort_order == "asc" else "DESC"
    
    with get_db() as conn:
        # Base query
        query = """
            SELECT d.cik, d.ticker, d.company_name, d.lambda, d.roic_0, 
                   d.roic_terminal, d.r_squared, d.converged, d.n_periods,
                   f.sector
            FROM decay_fits d
            LEFT JOIN (
                SELECT cik, sector FROM fundamentals GROUP BY cik
            ) f ON d.cik = f.cik
            WHERE d.converged = 1
        """
        params = []
        
        if sector:
            query += " AND f.sector = ?"
            params.append(sector)
        
        query += f" ORDER BY d.{sort_by} {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count
        count_query = """
            SELECT COUNT(*) FROM decay_fits d
            LEFT JOIN (SELECT cik, sector FROM fundamentals GROUP BY cik) f ON d.cik = f.cik
            WHERE d.converged = 1
        """
        if sector:
            count_query += " AND f.sector = ?"
            total = conn.execute(count_query, [sector]).fetchone()[0]
        else:
            total = conn.execute(count_query).fetchone()[0]
        
        # Get available sectors
        sectors = conn.execute("""
            SELECT DISTINCT f.sector FROM decay_fits d
            JOIN (SELECT cik, sector FROM fundamentals GROUP BY cik) f ON d.cik = f.cik
            WHERE d.converged = 1 AND f.sector IS NOT NULL
            ORDER BY f.sector
        """).fetchall()
        
    companies = []
    for row in rows:
        companies.append({
            "cik": row["cik"],
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "lambda": row["lambda"],
            "roic_0": row["roic_0"],
            "roic_terminal": row["roic_terminal"],
            "r_squared": row["r_squared"],
            "converged": bool(row["converged"]),
            "n_periods": row["n_periods"],
            "sector": row["sector"]
        })
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "sectors": [s["sector"] for s in sectors],
        "companies": companies
    }


@app.get("/api/company/{identifier}")
async def get_company(identifier: str):
    """Get detailed company data including ROIC series and forecasts."""
    
    with get_db() as conn:
        # Find by ticker or CIK
        fit = conn.execute("""
            SELECT * FROM decay_fits 
            WHERE ticker = ? OR cik = ?
            LIMIT 1
        """, [identifier, identifier]).fetchone()
        
        if not fit:
            raise HTTPException(404, f"Company not found: {identifier}")
        
        cik = fit["cik"]
        
        # Get validation data
        validation = conn.execute("""
            SELECT * FROM validation WHERE cik = ?
        """, [cik]).fetchone()
        
        # Get ROIC time series
        roic_series = conn.execute("""
            SELECT fiscal_year, roic, is_holdout
            FROM fundamentals
            WHERE cik = ? AND roic IS NOT NULL
            ORDER BY fiscal_year
        """, [cik]).fetchall()
        
        # Get sector
        sector_row = conn.execute("""
            SELECT sector FROM fundamentals WHERE cik = ? LIMIT 1
        """, [cik]).fetchone()
        
        # Get forecasts
        forecasts = conn.execute("""
            SELECT horizon_years, scenario, forecast_roic
            FROM forecasts
            WHERE cik = ?
            ORDER BY horizon_years, scenario
        """, [cik]).fetchall()
    
    return {
        "cik": fit["cik"],
        "ticker": fit["ticker"],
        "company_name": fit["company_name"],
        "lambda": fit["lambda"],
        "roic_0": fit["roic_0"],
        "roic_terminal": fit["roic_terminal"],
        "r_squared": fit["r_squared"],
        "converged": bool(fit["converged"]),
        "n_periods": fit["n_periods"],
        "sector": sector_row["sector"] if sector_row else None,
        "p_value": validation["p_value"] if validation else None,
        "ci_low": validation["ci_low"] if validation else None,
        "ci_high": validation["ci_high"] if validation else None,
        "holdout_rmse_model": validation["holdout_rmse_model"] if validation else None,
        "holdout_rmse_naive": validation["holdout_rmse_naive"] if validation else None,
        "roic_series": [
            {
                "year": r["fiscal_year"],
                "roic": r["roic"],
                "is_holdout": bool(r["is_holdout"])
            }
            for r in roic_series
        ],
        "forecasts": [
            {
                "horizon_years": f["horizon_years"],
                "scenario": f["scenario"],
                "forecast_roic": f["forecast_roic"]
            }
            for f in forecasts
        ]
    }


@app.get("/api/validation")
async def get_validation():
    """Get validation summary and per-company metrics."""
    
    with get_db() as conn:
        # Get summary stats
        summary = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN p_value < 0.05 THEN 1 ELSE 0 END) as significant,
                SUM(CASE WHEN holdout_rmse_model < holdout_rmse_naive THEN 1 ELSE 0 END) as model_better,
                AVG(lambda_price_corr) as price_corr,
                AVG(holdout_rmse_model) as avg_rmse_model,
                AVG(holdout_rmse_naive) as avg_rmse_naive
            FROM validation
        """).fetchone()
        
        # Get per-company validation data
        companies = conn.execute("""
            SELECT v.*, d.ticker, d.lambda, d.r_squared
            FROM validation v
            JOIN decay_fits d ON v.cik = d.cik
            WHERE d.converged = 1
            ORDER BY v.holdout_rmse_model
            LIMIT 500
        """).fetchall()
    
    return {
        "total_companies": summary["total"],
        "significant_lambda": summary["significant"],
        "model_beats_naive": summary["model_better"],
        "lambda_price_correlation": summary["price_corr"],
        "mean_holdout_rmse_model": summary["avg_rmse_model"],
        "mean_holdout_rmse_naive": summary["avg_rmse_naive"],
        "companies": [
            {
                "cik": c["cik"],
                "ticker": c["ticker"],
                "lambda": c["lambda"],
                "r_squared": c["r_squared"],
                "p_value": c["p_value"],
                "ci_low": c["ci_low"],
                "ci_high": c["ci_high"],
                "holdout_rmse_model": c["holdout_rmse_model"],
                "holdout_rmse_naive": c["holdout_rmse_naive"]
            }
            for c in companies
        ]
    }


@app.get("/api/methodology", response_class=HTMLResponse)
async def get_methodology():
    """Get methodology documentation as HTML."""
    
    if not METHODOLOGY_PATH.exists():
        raise HTTPException(404, "Methodology document not found")
    
    with open(METHODOLOGY_PATH, "r") as f:
        md_content = f.read()
    
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'toc']
    )
    
    # Wrap in basic HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Moaty Methodology</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                   max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
            code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
            pre {{ background: #f4f4f4; padding: 16px; border-radius: 6px; overflow-x: auto; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background: #f4f4f4; }}
            h1, h2, h3 {{ color: #333; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    return html


@app.get("/api/stats")
async def get_stats():
    """Get database statistics."""
    
    with get_db() as conn:
        stats = {}
        
        for table in ['fundamentals', 'prices', 'decay_fits', 'validation', 'forecasts']:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            stats[table] = count
        
        # Additional metrics
        stats["unique_companies"] = conn.execute(
            "SELECT COUNT(DISTINCT cik) FROM fundamentals"
        ).fetchone()[0]
        
        stats["converged_fits"] = conn.execute(
            "SELECT COUNT(*) FROM decay_fits WHERE converged = 1"
        ).fetchone()[0]
        
        stats["year_range"] = conn.execute(
            "SELECT MIN(fiscal_year), MAX(fiscal_year) FROM fundamentals"
        ).fetchone()
    
    return stats


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
