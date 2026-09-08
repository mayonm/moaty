import { useState, useEffect } from 'react'

const API_BASE = ''

export default function Methodology() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/methodology`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch methodology')
        return res.text()
      })
      .then(html => {
        // Extract just the body content
        const bodyMatch = html.match(/<body>([\s\S]*)<\/body>/)
        setContent(bodyMatch ? bodyMatch[1] : html)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <span>Loading methodology...</span>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="card">
        <div className="page-header">
          <h1>Methodology</h1>
        </div>
        <div className="error" style={{ padding: '2rem' }}>
          <p>Could not load methodology document.</p>
          <p style={{ fontSize: '0.875rem', marginTop: '0.5rem', color: 'var(--gray-500)' }}>
            Make sure METHODOLOGY.md exists and the API is running.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card methodology-content">
      <div dangerouslySetInnerHTML={{ __html: content }} />
    </div>
  )
}
