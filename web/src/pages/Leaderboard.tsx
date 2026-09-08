import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface Company {
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
}

interface LeaderboardData {
  total: number
  companies: Company[]
  sectors: string[]
}

const API_BASE = ''

export default function Leaderboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<LeaderboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState('lambda')
  const [sortOrder, setSortOrder] = useState('asc')
  const [sector, setSector] = useState('')

  useEffect(() => {
    fetchData()
  }, [sortBy, sortOrder, sector])

  const fetchData = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: '100'
      })
      if (sector) params.append('sector', sector)
      
      const res = await fetch(`${API_BASE}/api/leaderboard?${params}`)
      if (!res.ok) throw new Error('Failed to fetch data')
      const json = await res.json()
      setData(json)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (n: number, decimals = 4) => {
    if (n === null || n === undefined) return '—'
    return n.toFixed(decimals)
  }

  const formatPercent = (n: number) => {
    if (n === null || n === undefined) return '—'
    return `${(n * 100).toFixed(1)}%`
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <span>Loading companies...</span>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="error">
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
        <p>Error loading data: {error}</p>
        <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
          Make sure the API server is running on port 8000
        </p>
      </div>
    )
  }
  
  if (!data) return null

  const avgLambda = data.companies.length > 0 
    ? data.companies.reduce((a, c) => a + c.lambda, 0) / data.companies.length
    : 0

  return (
    <div>
      <div className="page-header">
        <h1>Moat Decay Leaderboard</h1>
        <p>Companies ranked by economic moat durability. Lower λ = more durable competitive advantage.</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Companies</div>
          <div className="value purple">{data.total.toLocaleString()}</div>
          <div className="subtext">with converged fits</div>
        </div>
        <div className="stat-card">
          <div className="label">Average λ</div>
          <div className="value">{avgLambda.toFixed(4)}</div>
          <div className="subtext">decay rate</div>
        </div>
        <div className="stat-card">
          <div className="label">Sectors</div>
          <div className="value">{data.sectors.length}</div>
          <div className="subtext">industry groups</div>
        </div>
        <div className="stat-card">
          <div className="label">Data Period</div>
          <div className="value">9 yrs</div>
          <div className="subtext">2017–2026</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Companies</h2>
          <span className="card-badge">
            {data.companies.length} shown
          </span>
        </div>
        
        <div className="filters">
          <select 
            className="filter-select"
            value={sector} 
            onChange={e => setSector(e.target.value)}
          >
            <option value="">All Sectors</option>
            {data.sectors.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          
          <select 
            className="filter-select"
            value={sortBy} 
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="lambda">Sort by: λ (decay rate)</option>
            <option value="r_squared">Sort by: R² (fit quality)</option>
            <option value="roic_0">Sort by: Initial ROIC</option>
            <option value="roic_terminal">Sort by: Terminal ROIC</option>
          </select>
          
          <select 
            className="filter-select"
            value={sortOrder} 
            onChange={e => setSortOrder(e.target.value)}
          >
            <option value="asc">Ascending ↑</option>
            <option value="desc">Descending ↓</option>
          </select>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Sector</th>
                <th>λ (decay)</th>
                <th>ROIC₀</th>
                <th>ROIC∞</th>
                <th>R²</th>
                <th>Periods</th>
              </tr>
            </thead>
            <tbody>
              {data.companies.map((c) => (
                <tr 
                  key={c.cik} 
                  className="clickable-row"
                  onClick={() => navigate(`/company/${c.ticker || c.cik}`)}
                >
                  <td className="ticker-cell">{c.ticker || c.cik.slice(0, 8)}</td>
                  <td className="company-cell">{c.company_name || '—'}</td>
                  <td>
                    {c.sector && <span className="badge badge-sector">{c.sector}</span>}
                  </td>
                  <td className="number-cell">{formatNumber(c.lambda)}</td>
                  <td className="number-cell">{formatPercent(c.roic_0)}</td>
                  <td className="number-cell">{formatPercent(c.roic_terminal)}</td>
                  <td className="number-cell">{formatNumber(c.r_squared, 3)}</td>
                  <td className="number-cell">{c.n_periods}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
