import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import CompanyDetail from './pages/CompanyDetail'
import Methodology from './pages/Methodology'
import Validation from './pages/Validation'
import './App.css'

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  const location = useLocation()
  const isActive = location.pathname === to || 
    (to === '/' && location.pathname === '/') ||
    (to !== '/' && location.pathname.startsWith(to))
  
  return (
    <Link to={to} className={isActive ? 'active' : ''}>
      {children}
    </Link>
  )
}

function Navigation() {
  return (
    <header className="header">
      <div className="header-content">
        <Link to="/" className="logo">
          <div className="logo-icon">M</div>
          <span className="logo-text">Moaty</span>
        </Link>
        
        <nav className="nav">
          <NavLink to="/">Leaderboard</NavLink>
          <NavLink to="/validation">Validation</NavLink>
          <NavLink to="/methodology">Methodology</NavLink>
        </nav>
      </div>
    </header>
  )
}

function App() {
  return (
    <Router>
      <div className="app">
        <Navigation />
        
        <main className="main">
          <Routes>
            <Route path="/" element={<Leaderboard />} />
            <Route path="/company/:id" element={<CompanyDetail />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="/validation" element={<Validation />} />
          </Routes>
        </main>
        
        <footer className="footer">
          Moaty — Economic Moat Decay Prediction System
        </footer>
      </div>
    </Router>
  )
}

export default App
