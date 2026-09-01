# Moaty — Economic Moat Decay Prediction System

Moaty models how long a company's economic moat (competitive advantage) lasts by fitting an exponential decay curve to historical Return on Invested Capital (ROIC):

```
ROIC(t) = ROIC_terminal + (ROIC_0 − ROIC_terminal) × e^(-λt)
```

## Quick Start

### Prerequisites

- Python 3.10+
- Julia 1.9+
- R 4.0+
- Node.js 18+

### Installation

```bash
# Python dependencies
pip install -r requirements.txt

# Julia packages (run once)
julia -e 'using Pkg; Pkg.add(["LsqFit", "CSV", "DataFrames", "SQLite", "JSON"])'

# R packages (run once)
Rscript R/install.R

# Frontend dependencies
cd web && npm install && cd ..
```

### Run the Full Pipeline

```bash
python run_pipeline.py
```

This downloads SEC EDGAR data, computes ROIC, fits decay models, runs validation, and generates forecasts. Takes ~10-15 minutes on first run.

To skip downloads if data already exists:
```bash
python run_pipeline.py --skip-download --skip-prices
```

### Start the Local Website

Terminal 1 (API server):
```bash
cd api && uvicorn main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd web && npm run dev
```

Open http://localhost:3000 in your browser.

## Project Structure

```
moaty/
├── run_pipeline.py          # Main orchestrator (run this)
├── moaty.db                  # SQLite database
├── METHODOLOGY.md            # Detailed methodology documentation
├── requirements.txt          # Python dependencies
│
├── src/                      # Python pipeline scripts
│   ├── download_edgar.py     # SEC EDGAR data downloader
│   ├── parse_fundamentals.py # ROIC computation
│   ├── download_prices.py    # Stock price downloader
│   ├── load_sqlite.py        # SQLite loader
│   └── forecasts.py          # Forecast generator
│
├── julia/                    # Julia fitting engine
│   ├── Project.toml
│   └── fit_decay.jl          # Exponential decay fitting
│
├── R/                        # R validation scripts
│   ├── install.R
│   └── validate_fits.R       # Statistical validation
│
├── api/                      # FastAPI backend
│   └── main.py
│
├── web/                      # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Leaderboard.tsx
│   │   │   ├── CompanyDetail.tsx
│   │   │   ├── Validation.tsx
│   │   │   └── Methodology.tsx
│   │   └── App.tsx
│   └── package.json
│
└── data/                     # Data files (gitignored)
    ├── quarter_reports/      # SEC EDGAR raw data
    ├── fundamentals.csv
    ├── prices.csv
    └── decay_fits.csv
```

## Database Schema

The SQLite database (`moaty.db`) contains these tables:

| Table | Description |
|-------|-------------|
| `fundamentals` | Company-year ROIC observations |
| `prices` | Daily stock prices |
| `decay_fits` | Fitted decay parameters (λ, ROIC_0, ROIC_terminal) |
| `validation` | Statistical validation metrics |
| `forecasts` | 5yr and 10yr ROIC forecasts |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/leaderboard` | Ranked list of companies by λ |
| `GET /api/company/{ticker}` | Company detail with ROIC series |
| `GET /api/validation` | Holdout validation metrics |
| `GET /api/methodology` | Methodology documentation |
| `GET /api/stats` | Database statistics |

## Website Pages

1. **Leaderboard** — Sortable table of companies ranked by decay rate
2. **Company Detail** — ROIC chart, fitted curve, forecasts, validation metrics
3. **Validation** — Model vs naive comparison, price correlation
4. **Methodology** — Full methodology documentation

## Key Configuration

Edit these in the source files:

| Setting | Location | Default |
|---------|----------|---------|
| Holdout years | `src/load_sqlite.py` | 2025, 2026 |
| Min years for fitting | `src/parse_fundamentals.py` | 7 |
| Disruption multiplier | `src/forecasts.py` | 1.5 |
| Bootstrap iterations | `R/validate_fits.R` | 100 |

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for detailed documentation of:
- ROIC calculation formula
- Decay model specification
- Statistical validation approach
- Forecast methodology
- Data sources and limitations

## License

MIT License
