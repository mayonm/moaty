import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import blobUrl from '../assets/moaty-blob.png'
import gptMarkUrl from '../assets/gpt-mark.png'
import gptMicUrl from '../assets/gpt-mic.png'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TRY_COMPANIES = ['Apple', 'NVIDIA', 'Costco', 'Microsoft']

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

const BAR_HEIGHTS = ['69%', '100%', '44%', '100%', '69%']
const BAR_TONES = ['sage', 'blue', 'lilac', 'blue', 'sage']

function MiniBars({ live = false }: { live?: boolean }) {
  return (
    <div className={`bars${live ? ' bars-live' : ''}`} aria-hidden="true">
      {BAR_HEIGHTS.map((height, index) => (
        <span key={index} className={`bar ${BAR_TONES[index]}`} style={{ height }} />
      ))}
    </div>
  )
}

function SearchIcon() {
  return (
    <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M16.1 16.4L20.2 20.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.5 12h13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M13 6.5L19.2 12 13 17.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function sourceLabel(source: string) {
  if (source.endsWith('_ai')) return 'Local model'
  if (source === 'kalshi_markets') return 'Kalshi'
  if (source === 'moaty_database') return 'Database'
  return source.replaceAll('_', ' ')
}

export default function Research() {
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
  const findingsRef = useRef<HTMLElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isChatLoading])

  useEffect(() => {
    if (result) {
      findingsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [result])

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
    searchInputRef.current?.focus()
  }

  const runResearch = async (rawQuery: string) => {
    const query = rawQuery.trim()
    if (!query || isLoading) return

    setSearchQuery(query)
    setIsLoading(true)
    setResult(null)
    setChatMessages([])
    setShowSuggestions(false)
    setSuggestions([])

    try {
      const res = await fetch(`${API_URL}/api/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: query,
          include_kalshi: true,
          include_fundamentals: true,
          include_economic_context: true,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Research failed')
      }

      const data: ResearchResponse = await res.json()
      setResult(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Research failed'
      setResult({
        session_id: '',
        company_name: query,
        ticker: null,
        analysis: `Error: ${message}`,
        kalshi_markets: [],
        has_fundamentals: false,
        fundamentals_summary: null,
        data_sources: [],
        errors: [message],
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleResearch = (e?: React.FormEvent) => {
    e?.preventDefault()
    void runResearch(searchQuery)
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
        }),
      })

      if (!res.ok) {
        throw new Error('Chat failed')
      }

      const data = await res.json()
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
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

  const focusSearch = () => searchInputRef.current?.focus()
  const showHomeCards = !result && !isLoading

  return (
    <div className="stage">
      <img className="blob" src={blobUrl} alt="" />

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">YOUR RESEARCH WORKSPACE</p>
          <h1>Understand the business.</h1>
          <p className="lede">
            Enter a company to explore its advantage, financial durability, and competitive risks.
          </p>

          <form onSubmit={handleResearch} className="search-form">
            <div className="search-wrap">
              <div className="search-field">
                <SearchIcon />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 180)}
                  placeholder="Company name or ticker"
                  className="search-input"
                  aria-label="Company name or ticker"
                  autoComplete="off"
                  spellCheck={false}
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  className="search-go"
                  disabled={isLoading || !searchQuery.trim()}
                >
                  {isLoading ? 'Researching' : 'Research'}
                  <ArrowIcon />
                </button>
              </div>

              {showSuggestions && suggestions.length > 0 && (
                <div className="suggestions" role="listbox">
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={`${suggestion.ticker}-${index}`}
                      type="button"
                      className="suggestion"
                      onMouseDown={(event) => {
                        event.preventDefault()
                        selectSuggestion(suggestion)
                      }}
                    >
                      <span className="suggestion-ticker">{suggestion.ticker || '—'}</span>
                      <span className="suggestion-name">{suggestion.company_name}</span>
                      {suggestion.sector && <span className="suggestion-sector">{suggestion.sector}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </form>

          <div className="try-row">
            <span className="try-label">Try</span>
            {TRY_COMPANIES.map((name) => (
              <button
                key={name}
                type="button"
                className="chip"
                onClick={() => { void runResearch(name) }}
                disabled={isLoading}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {showHomeCards && (
        <section className="card-row" aria-label="Research paths">
          <article className="research-card">
            <p className="kicker">01 / RESEARCH</p>
            <h2>The advantage</h2>
            <MiniBars />
            <div className="card-foot">
              <button type="button" className="text-btn" onClick={focusSearch}>Look closer</button>
              <button type="button" className="text-btn plus" onClick={focusSearch} aria-label="Look closer">+</button>
            </div>
          </article>

          <article className="research-card signals">
            <p className="kicker">02 / RESEARCH</p>
            <h2>The signals</h2>
            <MiniBars />
            <div className="gpt-pill">
              <img src={gptMarkUrl} alt="" className="pill-icon" />
              <span>Work with ChatGPT</span>
              <img src={gptMicUrl} alt="" className="pill-icon" />
            </div>
          </article>

          <article className="research-card">
            <p className="kicker">03 / RESEARCH</p>
            <h2>The questions</h2>
            <MiniBars />
            <div className="card-foot">
              <button type="button" className="text-btn" onClick={focusSearch}>Look closer</button>
              <button type="button" className="text-btn plus" onClick={focusSearch} aria-label="Look closer">+</button>
            </div>
          </article>
        </section>
      )}

      {isLoading && (
        <section className="status-panel" aria-live="polite">
          <p className="eyebrow">RESEARCH</p>
          <h2>Reading {searchQuery}.</h2>
          <p className="lede">
            The local model is working through the advantage, the numbers, and the risks. This usually takes about half a minute.
          </p>
          <MiniBars live />
        </section>
      )}

      {result && (
        <section className="findings" ref={findingsRef}>
          <header className="findings-head">
            <p className="eyebrow">COMPANY RESEARCH</p>
            <h2>{result.company_name}</h2>
            <div className="findings-meta">
              {result.ticker && <span className="ticker-pill">{result.ticker}</span>}
              {result.fundamentals_summary?.sector && (
                <span className="ticker-pill">{result.fundamentals_summary.sector}</span>
              )}
              {result.data_sources.map((source) => (
                <span key={source} className="ticker-pill quiet">{sourceLabel(source)}</span>
              ))}
            </div>
          </header>

          <div className="findings-grid">
            <article className="sheet">
              <p className="kicker">THE WRITEUP</p>
              <h3>The advantage</h3>
              <div className="analysis-content">
                <ReactMarkdown>{result.analysis}</ReactMarkdown>
              </div>
            </article>

            <div className="findings-side">
              {result.has_fundamentals && result.fundamentals_summary && (
                <article className="sheet">
                  <p className="kicker">THE NUMBERS</p>
                  <h3>Historical metrics</h3>
                  <p className="sheet-note">Illustrative decay fit for the live demo.</p>
                  <dl className="metric-list">
                    <div>
                      <dt>Sector</dt>
                      <dd>{result.fundamentals_summary.sector || 'N/A'}</dd>
                    </div>
                    <div>
                      <dt>Decay rate (λ)</dt>
                      <dd>{formatDecimal(result.fundamentals_summary.decay_rate)}</dd>
                    </div>
                    <div>
                      <dt>Initial ROIC</dt>
                      <dd>{formatPercent(result.fundamentals_summary.initial_roic)}</dd>
                    </div>
                    <div>
                      <dt>Terminal ROIC</dt>
                      <dd>{formatPercent(result.fundamentals_summary.terminal_roic)}</dd>
                    </div>
                    <div>
                      <dt>Fit quality (R²)</dt>
                      <dd>{formatDecimal(result.fundamentals_summary.r_squared, 3)}</dd>
                    </div>
                    <div>
                      <dt>Data periods</dt>
                      <dd>{result.fundamentals_summary.roic_periods}</dd>
                    </div>
                  </dl>
                </article>
              )}

              {result.kalshi_markets.length > 0 && (
                <article className="sheet">
                  <p className="kicker">THE MARKET</p>
                  <h3>Kalshi markets</h3>
                  <div className="market-list">
                    {result.kalshi_markets.slice(0, 5).map((market) => (
                      <a
                        key={market.ticker}
                        href={market.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="market-row"
                      >
                        <span className="market-title">{market.title}</span>
                        <span className="market-meta">
                          <span>{Math.round(market.yes_price)}% yes</span>
                          {market.volume > 0 && <span>${market.volume.toLocaleString()} vol</span>}
                        </span>
                      </a>
                    ))}
                  </div>
                </article>
              )}

              {result.errors.length > 0 && (
                <article className="sheet notice-sheet">
                  <p className="kicker">NOTICES</p>
                  <ul className="notice-list">
                    {result.errors.map((err) => (
                      <li key={err}>{err}</li>
                    ))}
                  </ul>
                </article>
              )}
            </div>
          </div>

          <article className="sheet chat-sheet">
            <p className="kicker">FOLLOW UP</p>
            <h3>Ask about {result.company_name}</h3>

            {chatMessages.length > 0 && (
              <div className="chat-log">
                {chatMessages.map((message, index) => (
                  <div key={index} className={`chat-line ${message.role}`}>
                    <span className="chat-who">{message.role === 'user' ? 'You' : 'Moaty'}</span>
                    <div className="chat-body">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="chat-line assistant">
                    <span className="chat-who">Moaty</span>
                    <div className="chat-body typing" aria-label="Writing">
                      <span /><span /><span />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}

            <form onSubmit={handleChat} className="chat-form">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={`Ask a question about ${result.company_name}`}
                className="chat-input"
                disabled={isChatLoading || !result.session_id}
                aria-label="Follow-up question"
              />
              <button
                type="submit"
                className="search-go chat-go"
                disabled={isChatLoading || !chatInput.trim() || !result.session_id}
              >
                Send
                <ArrowIcon />
              </button>
            </form>
          </article>
        </section>
      )}
    </div>
  )
}
