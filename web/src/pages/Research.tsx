import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface KalshiMarket {
  ticker: string
  title: string
  subtitle: string | null
  yes_price: number
  no_price: number
  volume: number
  close_time: string | null
  url: string
}

interface FundamentalsSummary {
  ticker: string | null
  company_name: string | null
  sector: string | null
  decay_rate: number | null
  initial_roic: number | null
  terminal_roic: number | null
  r_squared: number | null
  roic_periods: number
}

interface ResearchResponse {
  session_id: string
  company_name: string
  ticker: string | null
  analysis: string
  kalshi_markets: KalshiMarket[]
  has_fundamentals: boolean
  fundamentals_summary: FundamentalsSummary | null
  data_sources: string[]
  errors: string[]
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface SearchSuggestion {
  ticker: string | null
  company_name: string | null
  sector: string | null
}

export default function Research() {
  const [apiKey, setApiKey] = useState('')
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [showApiKeyInput, setShowApiKeyInput] = useState(true)
  
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ResearchResponse | null>(null)
  
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  
  const chatEndRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem('moaty_api_key')
    if (saved) {
      setApiKey(saved)
      setShowApiKeyInput(false)
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const saveApiKey = () => {
    if (apiKeyInput.trim()) {
      setApiKey(apiKeyInput.trim())
      localStorage.setItem('moaty_api_key', apiKeyInput.trim())
      setShowApiKeyInput(false)
    }
  }

  const clearApiKey = () => {
    setApiKey('')
    setApiKeyInput('')
    localStorage.removeItem('moaty_api_key')
    setShowApiKeyInput(true)
  }

  const fetchSuggestions = async (query: string) => {
    if (query.length < 2) {
      setSuggestions([])
      return
    }
    
    try {
      const res = await fetch(`${API_URL}/api/search?q=${encodeURIComponent(query)}`)
      if (res.ok) {
        const data = await res.json()
        setSuggestions(data.results || [])
      }
    } catch {
      setSuggestions([])
    }
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setSearchQuery(value)
    fetchSuggestions(value)
    setShowSuggestions(true)
  }

  const selectSuggestion = (suggestion: SearchSuggestion) => {
    setSearchQuery(suggestion.company_name || suggestion.ticker || '')
    setShowSuggestions(false)
    setSuggestions([])
  }

  const handleResearch = async (e?: React.FormEvent) => {
    e?.preventDefault()
    
    if (!searchQuery.trim()) return
    if (!apiKey) {
      setShowApiKeyInput(true)
      return
    }
    
    setIsLoading(true)
    setResult(null)
    setChatMessages([])
    setShowSuggestions(false)
    
    try {
      const res = await fetch(`${API_URL}/api/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: searchQuery,
          api_key: apiKey,
          include_kalshi: true,
          include_fundamentals: true,
          include_economic_context: true
        })
      })
      
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Research failed')
      }
      
      const data: ResearchResponse = await res.json()
      setResult(data)
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Research failed'
      setResult({
        session_id: '',
        company_name: searchQuery,
        ticker: null,
        analysis: `Error: ${message}`,
        kalshi_markets: [],
        has_fundamentals: false,
        fundamentals_summary: null,
        data_sources: [],
        errors: [message]
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleChat = async (e?: React.FormEvent) => {
    e?.preventDefault()
    
    if (!chatInput.trim() || !result?.session_id) return
    
    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsChatLoading(true)
    
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: result.session_id,
          message: userMessage,
          api_key: apiKey
        })
      })
      
      if (!res.ok) {
        throw new Error('Chat failed')
      }
      
      const data = await res.json()
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      
    } catch {
      setChatMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      }])
    } finally {
      setIsChatLoading(false)
    }
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A'
    return `${(value * 100).toFixed(1)}%`
  }

  const formatDecimal = (value: number | null | undefined, decimals = 4) => {
    if (value === null || value === undefined) return 'N/A'
    return value.toFixed(decimals)
  }

  return (
    <div className="research-page">
      {/* API Key Section */}
      {showApiKeyInput ? (
        <div className="api-key-card">
          <div className="api-key-header">
            <span className="api-key-icon">🔑</span>
            <div>
              <h3>Gemini API Key Required</h3>
              <p>Enter your free Google Gemini API key to enable AI analysis</p>
            </div>
          </div>
          <div className="api-key-input-group">
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="Enter your Gemini API key..."
              className="api-key-input"
              onKeyDown={(e) => e.key === 'Enter' && saveApiKey()}
            />
            <button onClick={saveApiKey} className="btn btn-primary">
              Save Key
            </button>
          </div>
          <a 
            href="https://aistudio.google.com/app/apikey" 
            target="_blank" 
            rel="noopener noreferrer"
            className="api-key-link"
          >
            Get a free API key from Google AI Studio →
          </a>
        </div>
      ) : (
        <div className="api-key-saved">
          <span>✓ API key saved</span>
          <button onClick={clearApiKey} className="btn-link">Change</button>
        </div>
      )}

      {/* Search Section */}
      <div className="search-section">
        <h1 className="search-title">Research Any Company</h1>
        <p className="search-subtitle">
          Get AI-powered moat analysis with prediction market insights
        </p>
        
        <form onSubmit={handleResearch} className="search-form">
          <div className="search-input-wrapper">
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Enter company name or ticker (e.g., Apple, AAPL)..."
              className="search-input"
              disabled={isLoading}
            />
            <button 
              type="submit" 
              className="btn btn-primary search-btn"
              disabled={isLoading || !searchQuery.trim()}
            >
              {isLoading ? (
                <span className="btn-loading">Analyzing...</span>
              ) : (
                'Research'
              )}
            </button>
            
            {showSuggestions && suggestions.length > 0 && (
              <div className="suggestions-dropdown">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    className="suggestion-item"
                    onClick={() => selectSuggestion(s)}
                  >
                    <span className="suggestion-ticker">{s.ticker || '—'}</span>
                    <span className="suggestion-name">{s.company_name}</span>
                    {s.sector && <span className="suggestion-sector">{s.sector}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Results Section */}
      {result && (
        <div className="results-section">
          {/* Company Header */}
          <div className="result-header">
            <div className="result-company">
              <div className="company-avatar">
                {(result.ticker || result.company_name)[0].toUpperCase()}
              </div>
              <div>
                <h2>{result.company_name}</h2>
                {result.ticker && <span className="ticker-badge">{result.ticker}</span>}
              </div>
            </div>
            <div className="data-sources">
              {result.data_sources.map((source, i) => (
                <span key={i} className="source-badge">
                  {source === 'gemini_ai' && '🤖 AI'}
                  {source === 'kalshi_markets' && '📊 Kalshi'}
                  {source === 'moaty_database' && '💾 Database'}
                </span>
              ))}
            </div>
          </div>

          <div className="results-grid">
            {/* Main Analysis */}
            <div className="analysis-panel">
              <div className="panel-header">
                <h3>AI Moat Analysis</h3>
              </div>
              <div className="analysis-content">
                <ReactMarkdown>{result.analysis}</ReactMarkdown>
              </div>
            </div>

            {/* Sidebar */}
            <div className="sidebar-panels">
              {/* Fundamentals */}
              {result.has_fundamentals && result.fundamentals_summary && (
                <div className="sidebar-card">
                  <h4>Historical Data</h4>
                  <div className="metric-grid">
                    <div className="metric">
                      <span className="metric-label">Sector</span>
                      <span className="metric-value">{result.fundamentals_summary.sector || 'N/A'}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Decay Rate (λ)</span>
                      <span className="metric-value">{formatDecimal(result.fundamentals_summary.decay_rate)}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Initial ROIC</span>
                      <span className="metric-value">{formatPercent(result.fundamentals_summary.initial_roic)}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Terminal ROIC</span>
                      <span className="metric-value">{formatPercent(result.fundamentals_summary.terminal_roic)}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Fit Quality (R²)</span>
                      <span className="metric-value">{formatDecimal(result.fundamentals_summary.r_squared, 3)}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Data Periods</span>
                      <span className="metric-value">{result.fundamentals_summary.roic_periods}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Kalshi Markets */}
              {result.kalshi_markets.length > 0 && (
                <div className="sidebar-card">
                  <h4>Prediction Markets</h4>
                  <div className="kalshi-list">
                    {result.kalshi_markets.slice(0, 5).map((market, i) => (
                      <a 
                        key={i} 
                        href={market.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="kalshi-item"
                      >
                        <div className="kalshi-title">{market.title}</div>
                        <div className="kalshi-meta">
                          <span className="kalshi-prob">{market.yes_price}% YES</span>
                          {market.volume > 0 && (
                            <span className="kalshi-volume">${market.volume.toLocaleString()} vol</span>
                          )}
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Errors */}
              {result.errors.length > 0 && (
                <div className="sidebar-card warning-card">
                  <h4>Notices</h4>
                  <ul className="error-list">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Chat Section */}
          <div className="chat-section">
            <div className="chat-header">
              <h3>Ask Follow-up Questions</h3>
              <span className="chat-hint">Ask anything about {result.company_name}</span>
            </div>
            
            {chatMessages.length > 0 && (
              <div className="chat-messages">
                {chatMessages.map((msg, i) => (
                  <div key={i} className={`chat-message ${msg.role}`}>
                    <div className="message-avatar">
                      {msg.role === 'user' ? '👤' : '🤖'}
                    </div>
                    <div className="message-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="chat-message assistant">
                    <div className="message-avatar">🤖</div>
                    <div className="message-content typing">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
            
            <form onSubmit={handleChat} className="chat-input-form">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask a question about this company..."
                className="chat-input"
                disabled={isChatLoading || !result.session_id}
              />
              <button 
                type="submit" 
                className="btn btn-secondary"
                disabled={isChatLoading || !chatInput.trim() || !result.session_id}
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !isLoading && (
        <div className="empty-state-research">
          <div className="feature-grid">
            <div className="feature-card">
              <span className="feature-icon">🤖</span>
              <h4>AI Analysis</h4>
              <p>Get comprehensive moat analysis powered by Google Gemini</p>
            </div>
            <div className="feature-card">
              <span className="feature-icon">📊</span>
              <h4>Prediction Markets</h4>
              <p>See what Kalshi traders expect for company events</p>
            </div>
            <div className="feature-card">
              <span className="feature-icon">💬</span>
              <h4>Interactive Chat</h4>
              <p>Ask follow-up questions to dive deeper into analysis</p>
            </div>
            <div className="feature-card">
              <span className="feature-icon">📈</span>
              <h4>Historical Data</h4>
              <p>Access ROIC decay metrics from our database</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
