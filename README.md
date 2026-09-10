# Moaty — AI-Powered Company Research Tool

Moaty is an interactive research tool that combines AI analysis with prediction market data to help you understand a company's competitive moat.

## Features

- **AI Moat Analysis** — Get comprehensive competitive advantage analysis powered by Google Gemini
- **Prediction Markets** — See what Kalshi traders expect for company and economic events
- **Interactive Chat** — Ask follow-up questions to dive deeper into any analysis
- **Historical Data** — Access ROIC decay metrics from our database of 2,000+ companies

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Gemini API Key (free from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Installation

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd web && npm install && cd ..
```

### Run the Application

Terminal 1 (API server):
```bash
cd api && uvicorn main:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
cd web && npm run dev
```

Open http://localhost:5173 in your browser.

## How It Works

1. **Enter a company name or ticker** (e.g., "Apple", "AAPL")
2. **Get AI-powered analysis** covering:
   - Moat assessment (Wide/Narrow/None)
   - Competitive advantages
   - Threats and risks
   - Prediction market sentiment
3. **Ask follow-up questions** in the chat interface

## Project Structure

```
moaty/
├── api/                      # FastAPI backend
│   └── main.py               # API endpoints
│
├── src/                      # Python services
│   ├── gemini_client.py      # Gemini AI integration
│   ├── kalshi_client.py      # Kalshi prediction markets
│   └── research_service.py   # Research orchestrator
│
├── web/                      # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Research.tsx  # Main research page
│   │   │   └── Methodology.tsx
│   │   └── App.tsx
│   └── package.json
│
├── moaty.db                  # SQLite database (optional, for historical data)
├── METHODOLOGY.md            # Methodology documentation
└── requirements.txt          # Python dependencies
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research` | POST | Analyze a company with AI |
| `/api/chat` | POST | Follow-up questions |
| `/api/search` | GET | Search companies in database |
| `/api/kalshi/{query}` | GET | Get prediction markets |
| `/api/methodology` | GET | Methodology documentation |

### Research Request Example

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Apple",
    "ticker": "AAPL",
    "api_key": "your-gemini-api-key"
  }'
```

## Data Sources

1. **Kalshi** — Real-time prediction market data (no auth required)
2. **Google Gemini** — AI analysis (free API key required)
3. **Moaty Database** — Historical ROIC and decay parameters (optional)

## Historical Data Pipeline (Optional)

The original Moaty system includes a data pipeline for computing ROIC decay metrics:

```bash
# Run full pipeline (downloads SEC data, fits decay models)
python run_pipeline.py
```

This creates `moaty.db` with historical ROIC data and fitted decay parameters using the model:

```
ROIC(t) = ROIC_terminal + (ROIC_0 − ROIC_terminal) × e^(-λt)
```

See [METHODOLOGY.md](METHODOLOGY.md) for detailed documentation.

### Pipeline Requirements

- Julia 1.9+ with LsqFit.jl
- R 4.0+ for statistical validation

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key (optional, can be provided in UI) |

## License

MIT License
