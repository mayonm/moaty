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

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <span>Loading company data...</span>
      </div>
    )
  }
  
  if (error) {
    return (
      <div>
        <Link to="/" className="back-link">← Back to Leaderboard</Link>
        <div className="error">
          <p>Error: {error}</p>
        </div>
      </div>
    )
  }
  
  if (!data) return null

  // Prepare chart data with fitted curve
  const minYear = Math.min(...data.roic_series.map(p => p.year))
  
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

  chartData.sort((a, b) => a.year - b.year)

  const formatPercent = (n: number | null) => {
    if (n === null || n === undefined) return '—'
    return `${(n * 100).toFixed(1)}%`
  }

  const formatNumber = (n: number | null, decimals = 4) => {
    if (n === null || n === undefined) return '—'
    return n.toFixed(decimals)
  }

  const tickerDisplay = data.ticker || data.cik.slice(0, 6)

  return (
    <div>
      <Link to="/" className="back-link">← Back to Leaderboard</Link>
      
      <div className="card">
        <div className="company-header">
          <div className="company-title">
            <div className="company-logo">
              {tickerDisplay.slice(0, 2)}
            </div>
            <div className="company-info">
              <h1>
                <span className="ticker">{data.ticker || 'N/A'}</span>
                {' '}{data.company_name || ''}
              </h1>
              <div className="company-meta">
                {data.sector && <span className="badge badge-sector">{data.sector}</span>}
                <span className="badge badge-lambda">λ = {formatNumber(data.lambda)}</span>
                {data.p_value && data.p_value < 0.05 && (
                  <span className="badge badge-success">Significant</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Decay Rate (λ)</div>
          <div className="value purple">{formatNumber(data.lambda)}</div>
          <div className="subtext">per year</div>
        </div>
        <div className="stat-card">
          <div className="label">Initial ROIC</div>
          <div className="value">{formatPercent(data.roic_0)}</div>
          <div className="subtext">ROIC₀</div>
        </div>
        <div className="stat-card">
          <div className="label">Terminal ROIC</div>
          <div className="value">{formatPercent(data.roic_terminal)}</div>
          <div className="subtext">ROIC∞ (long-run)</div>
        </div>
        <div className="stat-card">
          <div className="label">Fit Quality (R²)</div>
          <div className="value">{formatNumber(data.r_squared, 3)}</div>
          <div className="subtext">coefficient of determination</div>
        </div>
        <div className="stat-card">
          <div className="label">P-value</div>
          <div className={`value ${data.p_value && data.p_value < 0.05 ? 'positive' : ''}`}>
            {formatNumber(data.p_value, 4)}
          </div>
          <div className="subtext">λ significance</div>
        </div>
        <div className="stat-card">
          <div className="label">Periods Used</div>
          <div className="value">{data.n_periods}</div>
          <div className="subtext">annual observations</div>
        </div>
      </div>

      <div className="two-column">
        <div className="card">
          <div className="card-header">
            <h2>ROIC Time Series</h2>
            <span className="card-badge">Training + Holdout</span>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis 
                  dataKey="year" 
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                />
                <YAxis 
                  tickFormatter={(v) => `${v.toFixed(0)}%`} 
                  domain={['auto', 'auto']}
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(value) => `${Number(value).toFixed(1)}%`}
                  contentStyle={{ 
                    background: 'white', 
                    border: '1px solid #e4e4e7',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                  }}
                />
                <Legend />
                <ReferenceLine y={0} stroke="#a1a1aa" strokeDasharray="3 3" />
                <Line 
                  type="monotone" 
                  dataKey="actual" 
                  stroke="#9333ea" 
                  strokeWidth={2}
                  dot={{ r: 5, fill: '#9333ea' }}
                  name="Actual ROIC"
                />
                <Line 
                  type="monotone" 
                  dataKey="fitted" 
                  stroke="#c084fc" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Fitted Decay"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="formula">
            ROIC(t) = {formatPercent(data.roic_terminal)} + ({formatPercent(data.roic_0)} − {formatPercent(data.roic_terminal)}) × e<sup>−{formatNumber(data.lambda)}t</sup>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>Forecasts</h2>
          </div>
          <div className="table-container">
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
                      <td><strong>{horizon} years</strong></td>
                      <td className="number-cell">{base ? formatPercent(base.forecast_roic) : '—'}</td>
                      <td className="number-cell">{disruption ? formatPercent(disruption.forecast_roic) : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '2rem' }}>
            <div className="card-header">
              <h2>Validation Metrics</h2>
            </div>
            <div className="table-container">
              <table>
                <tbody>
                  <tr>
                    <td>λ Confidence Interval (95%)</td>
                    <td className="number-cell">[{formatNumber(data.ci_low)}, {formatNumber(data.ci_high)}]</td>
                  </tr>
                  <tr>
                    <td>Holdout RMSE (Model)</td>
                    <td className="number-cell">{formatNumber(data.holdout_rmse_model)}</td>
                  </tr>
                  <tr>
                    <td>Holdout RMSE (Naive)</td>
                    <td className="number-cell">{formatNumber(data.holdout_rmse_naive)}</td>
                  </tr>
                  <tr>
                    <td>Holdout Winner</td>
                    <td>
                      {data.holdout_rmse_model && data.holdout_rmse_naive ? (
                        data.holdout_rmse_model < data.holdout_rmse_naive ? (
                          <span className="badge badge-success">Model wins</span>
                        ) : (
                          <span className="badge badge-warning">Naive wins</span>
                        )
                      ) : '—'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
