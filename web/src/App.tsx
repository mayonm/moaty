import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Research from './pages/Research'
import Methodology from './pages/Methodology'
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
          <NavLink to="/">Research</NavLink>
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
            <Route path="/" element={<Research />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </main>
        
        <footer className="footer">
          Moaty — AI-Powered Company Research Tool
        </footer>
      </div>
    </Router>
  )
}

export default App
