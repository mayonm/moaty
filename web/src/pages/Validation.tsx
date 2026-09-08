import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'

interface ValidationCompany {
  cik: string
  ticker: string | null
  lambda: number
  r_squared: number
  p_value: number | null
  ci_low: number | null
  ci_high: number | null
  holdout_rmse_model: number | null
  holdout_rmse_naive: number | null
}

interface ValidationData {
  total_companies: number
  significant_lambda: number
  model_beats_naive: number
  lambda_price_correlation: number | null
  mean_holdout_rmse_model: number | null
  mean_holdout_rmse_naive: number | null
  companies: ValidationCompany[]
}

const API_BASE = ''

export default function Validation() {
  const navigate = useNavigate()
  const [data, setData] = useState<ValidationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/validation`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch validation data')
        return res.json()
      })
      .then(json => {
        setData(json)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <span>Loading validation data...</span>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="error">
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
        <p>Error loading data: {error}</p>
      </div>
    )
  }
  
  if (!data) return null

  // Prepare scatter plot data
  const scatterData = data.companies
    .filter(c => c.holdout_rmse_model !== null && c.lambda !== null)
    .slice(0, 200)
    .map(c => ({
      lambda: c.lambda,
      rmse: c.holdout_rmse_model,
      ticker: c.ticker || c.cik.slice(0, 6)
    }))

  // Prepare comparison bar data
  const barData = [
    { name: 'Model', value: data.mean_holdout_rmse_model || 0 },
    { name: 'Naive', value: data.mean_holdout_rmse_naive || 0 }
  ]

  const formatNumber = (n: number | null, decimals = 4) => {
    if (n === null || n === undefined) return '—'
    return n.toFixed(decimals)
  }

  const sigPct = data.total_companies > 0 
    ? ((data.significant_lambda / data.total_companies) * 100).toFixed(1)
    : '0'

  const modelWinPct = data.total_companies > 0
    ? ((data.model_beats_naive / data.total_companies) * 100).toFixed(1)
    : '0'

  return (
    <div>
      <div className="page-header">
        <h1>Model Validation</h1>
        <p>Statistical validation of decay fits using holdout data (2025-2026).</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Companies Validated</div>
          <div className="value purple">{data.total_companies.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="label">Significant λ (p &lt; 0.05)</div>
          <div className="value positive">{data.significant_lambda}</div>
          <div className="subtext">{sigPct}% of total</div>
        </div>
        <div className="stat-card">
          <div className="label">Model Beats Naive</div>
          <div className="value positive">{data.model_beats_naive}</div>
          <div className="subtext">{modelWinPct}% win rate</div>
        </div>
        <div className="stat-card">
          <div className="label">λ–Price Correlation</div>
          <div className="value">{formatNumber(data.lambda_price_correlation)}</div>
          <div className="subtext">decay vs returns</div>
        </div>
      </div>

      <div className="two-column">
        <div className="card">
          <div className="card-header">
            <h2>RMSE Comparison</h2>
            <span className="card-badge">Mean Holdout Error</span>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis 
                  dataKey="name" 
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                />
                <YAxis 
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(v) => Number(v).toFixed(4)}
                  contentStyle={{ 
                    background: 'white', 
                    border: '1px solid #e4e4e7',
                    borderRadius: '8px'
                  }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  <Cell fill="#9333ea" />
                  <Cell fill="#d4d4d8" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginTop: '0.5rem' }}>
            Model RMSE: {formatNumber(data.mean_holdout_rmse_model)} | 
            Naive RMSE: {formatNumber(data.mean_holdout_rmse_naive)}
          </p>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>Decay Rate vs Holdout Error</h2>
          </div>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis 
                  type="number" 
                  dataKey="lambda" 
                  name="λ" 
                  domain={[0, 'auto']}
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  label={{ value: 'λ (decay rate)', position: 'bottom', fill: '#71717a', fontSize: 12 }}
                />
                <YAxis 
                  type="number" 
                  dataKey="rmse" 
                  name="RMSE"
                  domain={[0, 'auto']}
                  stroke="#71717a"
                  tick={{ fill: '#71717a', fontSize: 12 }}
                  label={{ value: 'Holdout RMSE', angle: -90, position: 'insideLeft', fill: '#71717a', fontSize: 12 }}
                />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  formatter={(v) => Number(v).toFixed(4)}
                  contentStyle={{ 
                    background: 'white', 
                    border: '1px solid #e4e4e7',
                    borderRadius: '8px'
                  }}
                />
                <Scatter 
                  data={scatterData} 
                  fill="#9333ea"
                  fillOpacity={0.6}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Validation Details</h2>
          <span className="card-badge">{Math.min(100, data.companies.length)} companies</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>λ</th>
                <th>R²</th>
                <th>P-value</th>
                <th>95% CI</th>
                <th>RMSE (Model)</th>
                <th>RMSE (Naive)</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>
              {data.companies.slice(0, 100).map((c) => (
                <tr 
                  key={c.cik}
                  className="clickable-row"
                  onClick={() => navigate(`/company/${c.ticker || c.cik}`)}
                >
                  <td className="ticker-cell">{c.ticker || c.cik.slice(0, 8)}</td>
                  <td className="number-cell">{formatNumber(c.lambda)}</td>
                  <td className="number-cell">{formatNumber(c.r_squared, 3)}</td>
                  <td className="number-cell" style={{ 
                    color: c.p_value && c.p_value < 0.05 ? 'var(--success)' : 'inherit'
                  }}>
                    {formatNumber(c.p_value)}
                  </td>
                  <td className="number-cell">[{formatNumber(c.ci_low, 3)}, {formatNumber(c.ci_high, 3)}]</td>
                  <td className="number-cell">{formatNumber(c.holdout_rmse_model)}</td>
                  <td className="number-cell">{formatNumber(c.holdout_rmse_naive)}</td>
                  <td>
                    {c.holdout_rmse_model && c.holdout_rmse_naive ? (
                      c.holdout_rmse_model < c.holdout_rmse_naive ? (
                        <span className="winner-model">Model</span>
                      ) : (
                        <span className="winner-naive">Naive</span>
                      )
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
