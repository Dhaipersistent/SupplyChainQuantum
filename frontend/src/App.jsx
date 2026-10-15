import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { LayoutDashboard, Network, Cpu, Home, GitCompare, FlaskConical } from 'lucide-react'
import HomePage from './pages/Home'
import Dashboard from './pages/Dashboard'
import ClassicalArchitecture from './pages/ClassicalArchitecture'
import QuantumAdvantage from './pages/QuantumAdvantage'
import Comparison from './pages/Comparison'
import ResearchPipeline from './pages/ResearchPipeline'
import './index.css'

function Navbar() {
  return (
    <nav className="navbar">
      <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <Home size={15} /> Home
      </NavLink>
      <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <LayoutDashboard size={15} /> Dashboard
      </NavLink>
      <NavLink to="/classical" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <Network size={15} /> Classical
      </NavLink>
      <NavLink to="/quantum" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <Cpu size={15} /> Quantum Theory
      </NavLink>
      <NavLink to="/research" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <FlaskConical size={15} /> Research Pipeline
      </NavLink>
      <NavLink to="/comparison" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
        <GitCompare size={15} /> Comparison
      </NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard"  element={<div className="page-wrapper"><Dashboard /></div>} />
        <Route path="/classical"  element={<div className="page-wrapper"><ClassicalArchitecture /></div>} />
        <Route path="/quantum"    element={<div className="page-wrapper"><QuantumAdvantage /></div>} />
        <Route path="/research"   element={<div className="page-wrapper"><ResearchPipeline /></div>} />
        <Route path="/comparison" element={<div className="page-wrapper"><Comparison /></div>} />
      </Routes>
    </Router>
  )
}
