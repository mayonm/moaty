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

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const formatNumber = (n: number, decimals = 4) => {
    if (n === null || n === undefined) return '-'
    return n.toFixed(decimals)
  }

  const formatPercent = (n: number) => {
    if (n === null || n === undefined) return '-'
    return `${(n * 100).toFixed(1)}%`
  }

  if (loading) return <div className="loading">Loading...</div>
  if (error) return <div className="error">Error: {error}</div>
  if (!data) return null

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Companies</div>
          <div className="value">{data.total.toLocaleString()}</div>
        </div>
        <div className="stat-card">
          <div className="label">Avg λ (decay rate)</div>
          <div className="value">
            {data.companies.length > 0 
              ? (data.companies.reduce((a, c) => a + c.lambda, 0) / data.companies.length).toFixed(3)
              : '-'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Sectors</div>
          <div className="value">{data.sectors.length}</div>
        </div>
      </div>

      <div className="card">
        <h2>Moat Decay Leaderboard</h2>
        
        <div className="filters">
          <select value={sector} onChange={e => setSector(e.target.value)}>
            <option value="">All Sectors</option>
            {data.sectors.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="lambda">Sort by: λ (decay rate)</option>
            <option value="r_squared">Sort by: R²</option>
            <option value="roic_0">Sort by: Initial ROIC</option>
            <option value="roic_terminal">Sort by: Terminal ROIC</option>
          </select>
          
          <select value={sortOrder} onChange={e => setSortOrder(e.target.value)}>
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('ticker')}>Ticker</th>
                <th>Company</th>
                <th onClick={() => handleSort('sector')}>Sector</th>
                <th onClick={() => handleSort('lambda')}>λ (decay)</th>
                <th onClick={() => handleSort('roic_0')}>ROIC₀</th>
                <th onClick={() => handleSort('roic_terminal')}>ROIC∞</th>
                <th onClick={() => handleSort('r_squared')}>R²</th>
                <th onClick={() => handleSort('n_periods')}>Periods</th>
              </tr>
            </thead>
            <tbody>
              {data.companies.map((c, i) => (
                <tr 
                  key={c.cik} 
                  className="clickable-row"
                  onClick={() => navigate(`/company/${c.ticker || c.cik}`)}
                >
                  <td><strong>{c.ticker || c.cik.slice(0, 8)}</strong></td>
                  <td>{c.company_name || '-'}</td>
                  <td>{c.sector || '-'}</td>
                  <td>{formatNumber(c.lambda)}</td>
                  <td>{formatPercent(c.roic_0)}</td>
                  <td>{formatPercent(c.roic_terminal)}</td>
                  <td>{formatNumber(c.r_squared, 3)}</td>
                  <td>{c.n_periods}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <p style={{ marginTop: '1rem', color: '#666', fontSize: '0.85rem' }}>
          Lower λ = more durable moat (slower decay). Higher λ = faster erosion.
        </p>
      </div>
    </div>
  )
}
