"""
Moaty API Server

FastAPI backend serving decay fit data from SQLite database.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import markdown

# Configuration
DB_PATH = Path(__file__).parent.parent / "moaty.db"
METHODOLOGY_PATH = Path(__file__).parent.parent / "METHODOLOGY.md"

app = FastAPI(
    title="Moaty API",
    description="Economic Moat Decay Prediction System API",
    version="1.0.0"
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


# Response models
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
        "version": "1.0.0",
        "endpoints": {
            "leaderboard": "/api/leaderboard",
            "company": "/api/company/{ticker}",
            "validation": "/api/validation",
            "methodology": "/api/methodology"
        }
    }


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
