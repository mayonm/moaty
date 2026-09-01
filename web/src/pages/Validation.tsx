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

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">Error: {error}</div>
  if (!data) return null

  // Prepare scatter plot data (lambda vs holdout RMSE)
  const scatterData = data.companies
    .filter(c => c.holdout_rmse_model !== null && c.lambda !== null)
    .map(c => ({
      lambda: c.lambda,
      rmse: c.holdout_rmse_model,
      ticker: c.ticker || c.cik.slice(0, 6)
    }))

  // Prepare comparison bar data
  const barData = [
    { name: 'Model RMSE', value: data.mean_holdout_rmse_model || 0, fill: '#0984e3' },
    { name: 'Naive RMSE', value: data.mean_holdout_rmse_naive || 0, fill: '#e94560' }
  ]

  const formatNumber = (n: number | null, decimals = 4) => {
    if (n === null || n === undefined) return '-'
    return n.toFixed(decimals)
  }

  const sigPct = data.total_companies > 0 
    ? ((data.significant_lambda / data.total_companies) * 100).toFixed(1)
    : 0

  const modelWinPct = data.total_companies > 0
    ? ((data.model_beats_naive / data.total_companies) * 100).toFixed(1)
    : 0

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Companies Validated</div>
          <div className="value">{data.total_companies.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="label">Significant λ (p &lt; 0.05)</div>
          <div className="value positive">{data.significant_lambda} ({sigPct}%)</div>
        </div>
        <div className="stat-card">
          <div className="label">Model Beats Naive</div>
          <div className="value positive">{data.model_beats_naive} ({modelWinPct}%)</div>
        </div>
        <div className="stat-card">
          <div className="label">λ-Price Correlation</div>
          <div className="value">{formatNumber(data.lambda_price_correlation)}</div>
        </div>
      </div>

      <div className="two-column">
        <div className="card">
          <h2>Model vs Naive RMSE Comparison</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip formatter={(v: number) => v.toFixed(4)} />
                <Bar dataKey="value">
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            Mean Holdout RMSE: Model = {formatNumber(data.mean_holdout_rmse_model)}, 
            Naive = {formatNumber(data.mean_holdout_rmse_naive)}
          </p>
        </div>

        <div className="card">
          <h2>Decay Rate vs Holdout RMSE</h2>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  type="number" 
                  dataKey="lambda" 
                  name="λ (decay rate)" 
                  domain={[0, 'auto']}
                />
                <YAxis 
                  type="number" 
                  dataKey="rmse" 
                  name="Holdout RMSE"
                  domain={[0, 'auto']}
                />
                <Tooltip 
                  cursor={{ strokeDasharray: '3 3' }}
                  formatter={(v: number, name: string) => [v.toFixed(4), name]}
                  labelFormatter={(v) => `λ = ${Number(v).toFixed(4)}`}
                />
                <Scatter 
                  data={scatterData} 
                  fill="#0984e3"
                  fillOpacity={0.6}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Validation Details by Company</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>λ</th>
                <th>R²</th>
                <th>P-value</th>
                <th>CI (95%)</th>
                <th>RMSE (Model)</th>
                <th>RMSE (Naive)</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>
              {data.companies.slice(0, 100).map((c, i) => (
                <tr 
                  key={c.cik}
                  className="clickable-row"
                  onClick={() => navigate(`/company/${c.ticker || c.cik}`)}
                >
                  <td><strong>{c.ticker || c.cik.slice(0, 8)}</strong></td>
                  <td>{formatNumber(c.lambda)}</td>
                  <td>{formatNumber(c.r_squared, 3)}</td>
                  <td style={{ color: c.p_value && c.p_value < 0.05 ? '#00b894' : '#666' }}>
                    {formatNumber(c.p_value)}
                  </td>
                  <td>[{formatNumber(c.ci_low)}, {formatNumber(c.ci_high)}]</td>
                  <td>{formatNumber(c.holdout_rmse_model)}</td>
                  <td>{formatNumber(c.holdout_rmse_naive)}</td>
                  <td style={{ 
                    color: c.holdout_rmse_model && c.holdout_rmse_naive && 
                           c.holdout_rmse_model < c.holdout_rmse_naive ? '#00b894' : '#e94560'
                  }}>
                    {c.holdout_rmse_model && c.holdout_rmse_naive 
                      ? (c.holdout_rmse_model < c.holdout_rmse_naive ? 'Model' : 'Naive')
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: '1rem', color: '#666', fontSize: '0.85rem' }}>
          Showing first 100 companies sorted by holdout RMSE. Click a row for full details.
        </p>
      </div>
    </div>
  )
}
