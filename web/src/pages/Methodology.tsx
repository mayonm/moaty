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

  if (loading) return <div className="loading">Loading methodology...</div>
  if (error) return (
    <div className="card">
      <h2>Methodology</h2>
      <p className="error">Could not load methodology document: {error}</p>
      <p>Please ensure METHODOLOGY.md exists in the project root.</p>
    </div>
  )

  return (
    <div className="card methodology-content">
      <div dangerouslySetInnerHTML={{ __html: content }} />
    </div>
  )
}
