import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
        const bodyMatch = html.match(/<body>([\s\S]*)<\/body>/)
        setContent(bodyMatch ? bodyMatch[1] : html)
        setError(null)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="stage">
        <section className="status-panel">
          <p className="eyebrow">METHODOLOGY</p>
          <h2>Loading the notes.</h2>
        </section>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stage">
        <section className="status-panel">
          <p className="eyebrow">METHODOLOGY</p>
          <h2>The notes did not load.</h2>
          <p className="lede">Make sure METHODOLOGY.md exists and the API is running.</p>
        </section>
      </div>
    )
  }

  return (
    <div className="stage methodology-stage">
      <article className="sheet methodology-content" dangerouslySetInnerHTML={{ __html: content }} />
    </div>
  )
}
