# Moaty — AI-Powered Company Research Tool

Moaty is an interactive research tool that combines AI analysis with prediction market data to help you understand a company's competitive moat.

## Features

- **AI Moat Analysis** — Competitive advantage analysis from a local AI engine (no API key)
- **Prediction Markets** — See what Kalshi traders expect for company and economic events
- **Interactive Chat** — Ask follow-up questions to dive deeper into any analysis
- **Historical Data** — ROIC decay metrics for the companies in the database. If you have not run the full pipeline, the app creates a 26-company demo set so search still works.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- About 2 GB of free RAM for the local model

No API key is required. The search feature runs **Qwen2.5-1.5B-Instruct** locally through llama.cpp. The model file downloads automatically the first time the API starts (about 1 GB).

### Installation

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd web && npm install && cd ..
```

### Run the Application

Terminal 1 (API server), from the project root:
```bash
python -m uvicorn api.main:app --port 8000
```

The first start downloads the local model if it is not already in `models/`. Leave this terminal open.

Terminal 2 (Frontend):
```bash
cd web && npm run dev
```

Open http://localhost:3000 in your browser.

A company search usually finishes in about 20–30 seconds on a laptop CPU. The page shows a status line while the local engine is writing the analysis.

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
2. **Local AI engine** — Qwen2.5-1.5B-Instruct running on this machine
3. **Moaty Database** — Historical ROIC and decay parameters (a small demo set is created automatically if you have not run the full pipeline)

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
| `MOATY_MODEL_PATH` | Optional path to a different GGUF model |
| `MOATY_DISABLE_LOCAL` | Set to `1` to skip the local engine and use a cloud key instead |
| `GROQ_API_KEY` | Optional Groq fallback, only used when local AI is disabled |
| `GEMINI_API_KEY` | Optional Gemini fallback, only used when local AI is disabled |

**Note:** Leave these unset for the presentation demo. The local engine starts on its own.

## License

MIT License
