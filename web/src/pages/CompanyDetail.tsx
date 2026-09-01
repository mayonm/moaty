import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'

interface RoicPoint {
  year: number
  roic: number
  is_holdout: boolean
}

interface Forecast {
  horizon_years: number
  scenario: string
  forecast_roic: number
}

interface CompanyData {
  cik: string
  ticker: string | null
  company_name: string | null
  lambda: number
  roic_0: number
  roic_terminal: number
  r_squared: number
  converged: boolean
  n_periods: number
  sector: string | null
  p_value: number | null
  ci_low: number | null
  ci_high: number | null
  holdout_rmse_model: number | null
  holdout_rmse_naive: number | null
  roic_series: RoicPoint[]
  forecasts: Forecast[]
}

const API_BASE = ''

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<CompanyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    
    fetch(`${API_BASE}/api/company/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Company not found')
        return res.json()
      })
      .then(json => {
        setData(json)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">Error: {error}</div>
  if (!data) return null

  // Prepare chart data with fitted curve
  const minYear = Math.min(...data.roic_series.map(p => p.year))
  const maxYear = Math.max(...data.roic_series.map(p => p.year))
  
  const chartData = data.roic_series.map(p => {
    const t = p.year - minYear
    const fitted = data.roic_terminal + (data.roic_0 - data.roic_terminal) * Math.exp(-data.lambda * t)
    return {
      year: p.year,
      actual: p.roic * 100,
      fitted: fitted * 100,
      isHoldout: p.is_holdout
    }
  })

  // Add forecast points
  const lastYear = maxYear
  data.forecasts.forEach(f => {
    const forecastYear = lastYear + f.horizon_years
    const existing = chartData.find(d => d.year === forecastYear)
    if (!existing) {
      chartData.push({
        year: forecastYear,
        actual: null as any,
        fitted: null as any,
        isHoldout: true,
        [`forecast_${f.scenario}`]: f.forecast_roic * 100
      } as any)
    } else {
      (existing as any)[`forecast_${f.scenario}`] = f.forecast_roic * 100
    }
  })

  chartData.sort((a, b) => a.year - b.year)

  const formatPercent = (n: number | null) => {
    if (n === null || n === undefined) return '-'
    return `${(n * 100).toFixed(1)}%`
  }

  const formatNumber = (n: number | null, decimals = 4) => {
    if (n === null || n === undefined) return '-'
    return n.toFixed(decimals)
  }

  return (
    <div>
      <Link to="/" className="back-link">← Back to Leaderboard</Link>
      
      <div className="card">
        <div className="company-header">
          <div className="company-title">
            <h1>
              <span className="ticker">{data.ticker || 'N/A'}</span>
              {' '}{data.company_name || ''}
            </h1>
          </div>
          <div className="company-meta">
            {data.sector && <span className="badge badge-sector">{data.sector}</span>}
            <span className="badge badge-lambda">λ = {formatNumber(data.lambda)}</span>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Decay Rate (λ)</div>
          <div className="value">{formatNumber(data.lambda)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Initial ROIC</div>
          <div className="value">{formatPercent(data.roic_0)}</div>
        </div>
        <div className="stat-card">
          <div className="label">Terminal ROIC</div>
          <div className="value">{formatPercent(data.roic_terminal)}</div>
        </div>
        <div className="stat-card">
          <div className="label">R² (fit quality)</div>
          <div className="value">{formatNumber(data.r_squared, 3)}</div>
        </div>
        <div className="stat-card">
          <div className="label">P-value (λ significance)</div>
          <div className="value" style={{ color: data.p_value && data.p_value < 0.05 ? '#00b894' : '#666' }}>
            {formatNumber(data.p_value, 4)}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Periods Used</div>
          <div className="value">{data.n_periods}</div>
        </div>
      </div>

      <div className="two-column">
        <div className="card">
          <h2>ROIC Time Series & Fitted Decay Curve</h2>
          <div className="chart-container" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis tickFormatter={(v) => `${v.toFixed(0)}%`} domain={['auto', 'auto']} />
                <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
                <Legend />
                <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />
                <Line 
                  type="monotone" 
                  dataKey="actual" 
                  stroke="#e94560" 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  name="Actual ROIC"
                />
                <Line 
                  type="monotone" 
                  dataKey="fitted" 
                  stroke="#0984e3" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Fitted Curve"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            ROIC(t) = {formatPercent(data.roic_terminal)} + ({formatPercent(data.roic_0)} - {formatPercent(data.roic_terminal)}) × e^(-{formatNumber(data.lambda)}×t)
          </p>
        </div>

        <div className="card">
          <h2>Forecasts</h2>
          <table>
            <thead>
              <tr>
                <th>Horizon</th>
                <th>Base Case</th>
                <th>Disruption (λ×1.5)</th>
              </tr>
            </thead>
            <tbody>
              {[5, 10].map(horizon => {
                const base = data.forecasts.find(f => f.horizon_years === horizon && f.scenario === 'base')
                const disruption = data.forecasts.find(f => f.horizon_years === horizon && f.scenario === 'disruption')
                return (
                  <tr key={horizon}>
                    <td>{horizon} years</td>
                    <td>{base ? formatPercent(base.forecast_roic) : '-'}</td>
                    <td>{disruption ? formatPercent(disruption.forecast_roic) : '-'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <h2 style={{ marginTop: '2rem' }}>Validation Metrics</h2>
          <table>
            <tbody>
              <tr>
                <td>λ Confidence Interval (95%)</td>
                <td>[{formatNumber(data.ci_low)}, {formatNumber(data.ci_high)}]</td>
              </tr>
              <tr>
                <td>Holdout RMSE (Model)</td>
                <td>{formatNumber(data.holdout_rmse_model)}</td>
              </tr>
              <tr>
                <td>Holdout RMSE (Naive)</td>
                <td>{formatNumber(data.holdout_rmse_naive)}</td>
              </tr>
              <tr>
                <td>Model vs Naive</td>
                <td style={{ 
                  color: data.holdout_rmse_model && data.holdout_rmse_naive && 
                         data.holdout_rmse_model < data.holdout_rmse_naive ? '#00b894' : '#e94560'
                }}>
                  {data.holdout_rmse_model && data.holdout_rmse_naive 
                    ? (data.holdout_rmse_model < data.holdout_rmse_naive ? 'Model wins' : 'Naive wins')
                    : '-'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
