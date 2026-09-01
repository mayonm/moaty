import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import CompanyDetail from './pages/CompanyDetail'
import Methodology from './pages/Methodology'
import Validation from './pages/Validation'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <header className="header">
          <h1>Moaty</h1>
          <p className="subtitle">Economic Moat Decay Prediction System</p>
          <nav className="nav">
            <Link to="/">Leaderboard</Link>
            <Link to="/validation">Validation</Link>
            <Link to="/methodology">Methodology</Link>
          </nav>
        </header>
        
        <main className="main">
          <Routes>
            <Route path="/" element={<Leaderboard />} />
            <Route path="/company/:id" element={<CompanyDetail />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="/validation" element={<Validation />} />
          </Routes>
        </main>
        
        <footer className="footer">
          <p>Moaty v1.0 — Exponential decay model for ROIC prediction</p>
        </footer>
      </div>
    </Router>
  )
}

export default App
