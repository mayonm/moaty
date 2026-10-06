import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Research from './pages/Research'
import Methodology from './pages/Methodology'
import './App.css'

function App() {
  return (
    <Router>
      <div className="app">
        <header className="topbar">
          <Link to="/" className="product-link">Product</Link>
          <Link to="/" className="wordmark">Moaty</Link>
        </header>

        <main className="main">
          <Routes>
            <Route path="/" element={<Research />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
