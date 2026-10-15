import { useState } from 'react'
import { Cpu, Zap, Globe2, FlaskConical, Atom } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend
} from 'recharts'

// ─── Energy Landscape SVG (corrected: minima are valleys, y-axis up = high energy) ───
// In SVG: y increases downward, so HIGH y = LOW energy (valley = minimum)
// Landscape: starts high (left plateau), two local minima (valleys), global minimum deepest on right
function EnergyLandscape({ showQuantum }) {
  // Peaks are LOW y (high energy). Valleys are HIGH y (low energy).
  // Left local min ≈ y=115, middle local min ≈ y=108, global min ≈ y=138 (deepest valley, right side)
  const path = "M 20 50 C 40 48, 55 115, 80 115 C 100 115, 110 55, 140 52 C 160 50, 175 108, 200 108 C 220 108, 235 58, 260 55 C 285 52, 300 138, 330 138 C 355 138, 370 60, 400 58 C 430 56, 450 90, 480 92 C 505 94, 530 85, 560 88"

  // Classical gets stuck at left local min (y=115, x≈80)
  // Quantum tunnels through the barrier (x≈140, y≈52) and reaches global min (x≈315, y=138)

  return (
    <svg viewBox="0 0 580 190" style={{ width: '100%', maxHeight: 200, display: 'block' }}>
      <defs>
        <linearGradient id="landscape2" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0f172a" stopOpacity={0.1} />
          <stop offset="100%" stopColor="#1e3a5f" stopOpacity={0.5} />
        </linearGradient>
        <marker id="arrowQ" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#38bdf8" />
        </marker>
      </defs>

      {/* Energy axis label */}
      <text x={8} y={20} fill="#475569" fontSize={9} transform="rotate(-90, 8, 90)" textAnchor="middle">Energy ↑</text>

      {/* Landscape fill */}
      <path d={path + ' L 560 190 L 20 190 Z'} fill="url(#landscape2)" opacity={0.7} />
      <path d={path} fill="none" stroke="#38bdf8" strokeWidth={2.5} />

      {/* Barrier walls (local maxima = high energy = low y) */}
      <line x1={140} y1={52} x2={140} y2={115} stroke="#f59e0b" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />
      <line x1={260} y1={55} x2={260} y2={108} stroke="#f59e0b" strokeWidth={1} strokeDasharray="3 3" opacity={0.5} />

      {/* Labels for minima */}
      <text x={80}  y={132} fill="#f59e0b" fontSize={9} textAnchor="middle">Local Min</text>
      <text x={200} y={125} fill="#f59e0b" fontSize={9} textAnchor="middle">Local Min</text>
      <text x={315} y={155} fill="#34d399" fontSize={10} fontWeight={700} textAnchor="middle">Global Min ✓</text>

      {/* Energy barrier labels */}
      <text x={140} y={44} fill="#f59e0b" fontSize={8} textAnchor="middle">Barrier</text>
      <text x={260} y={47} fill="#f59e0b" fontSize={8} textAnchor="middle">Barrier</text>

      {/* Classical ball — stuck in first local minimum (valley at y=115) */}
      <circle cx={80} cy={113} r={7} fill="#f43f5e" />
      <text x={80} y={100} fill="#f43f5e" fontSize={9} textAnchor="middle">Classical</text>
      <text x={80} y={90} fill="#f43f5e" fontSize={9} textAnchor="middle">(Stuck)</text>

      {/* Quantum tunneling — dashed arc going THROUGH the barrier to global min */}
      {showQuantum && (
        <>
          {/* Tunneling arc: from local min (80,113), through barrier (140,52) UNDERGROUND, to global min (315,136) */}
          <path
            d="M 90 113 Q 200 175 305 136"
            fill="none" stroke="#38bdf8" strokeWidth={2.5} strokeDasharray="6 4"
            markerEnd="url(#arrowQ)"
          />
          {/* "Tunnel" label under barrier */}
          <text x={195} y={182} fill="#38bdf8" fontSize={9} textAnchor="middle">← Quantum tunnels through barrier →</text>
          {/* Quantum ball at global min */}
          <circle cx={315} cy={136} r={7} fill="#38bdf8" />
          <text x={315} y={122} fill="#38bdf8" fontSize={9} textAnchor="middle">Quantum</text>
          <text x={315} y={112} fill="#38bdf8" fontSize={9} textAnchor="middle">(Global Min)</text>
        </>
      )}
    </svg>
  )
}

// ─── QUBO Explainer ───────────────────────────────────────────────────────
function QuboExplainer() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ padding: '1rem', background: 'rgba(0,0,0,0.25)', borderRadius: 8, borderLeft: '3px solid #38bdf8' }}>
        <div style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          QUBO — Quadratic Unconstrained Binary Optimization
        </div>
        <p style={{ color: '#94a3b8', fontSize: '0.875rem', lineHeight: 1.7, margin: 0 }}>
          Any combinatorial optimization problem can be reformulated as minimizing a quadratic polynomial
          over binary variables <code style={{ color: '#38bdf8' }}>x ∈ {'{0,1}'}ⁿ</code>. For VRP, each binary
          variable encodes whether a vehicle visits customer <em>j</em> at position <em>k</em> in its route.
        </p>
      </div>

      {/* QUBO matrix equation */}
      <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', background: '#0f172a', padding: '1.25rem', borderRadius: 8, border: '1px solid #1e3a5f', color: '#e2e8f0', lineHeight: 2 }}>
        <div style={{ color: '#64748b', fontSize: '0.7rem', marginBottom: '0.25rem' }}>QUBO OBJECTIVE FUNCTION</div>
        <div>minimize: <span style={{ color: '#38bdf8' }}>xᵀ Q x</span>   where x ∈ {'{'}<span style={{ color: '#f59e0b' }}>0,1</span>{'}'}<sup>n</sup></div>
        <div style={{ color: '#64748b', fontSize: '0.7rem', marginTop: '0.75rem', marginBottom: '0.25rem' }}>EXPANDED FORM</div>
        <div>= <span style={{ color: '#34d399' }}>Σᵢ Qᵢᵢ xᵢ</span>  +  <span style={{ color: '#818cf8' }}>Σᵢ﹤ⱼ Qᵢⱼ xᵢxⱼ</span></div>
        <div style={{ color: '#64748b', fontSize: '0.75rem', marginTop: '0.25rem' }}>
          Linear terms (diagonal Q) + Quadratic interactions (off-diagonal Q)
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        {[
          { label: 'Route Feasibility', desc: 'Penalty terms enforce each customer visited exactly once and vehicle returns to depot.', color: '#f59e0b' },
          { label: 'Distance Cost', desc: 'Off-diagonal Q entries encode pairwise travel distances between consecutive stops.', color: '#818cf8' },
          { label: 'Capacity Constraint', desc: 'Quadratic penalties prevent vehicle load from exceeding maximum capacity.', color: '#f43f5e' },
          { label: 'Ising Mapping', desc: 'Q matrix maps directly to a quantum Ising Hamiltonian: xᵢ = (1 - σᵢᶻ)/2.', color: '#38bdf8' },
        ].map((c, i) => (
          <div key={i} style={{ padding: '0.75rem', background: 'rgba(0,0,0,0.2)', borderRadius: 8, borderLeft: `2px solid ${c.color}` }}>
            <div style={{ color: c.color, fontWeight: 600, fontSize: '0.8rem', marginBottom: '0.3rem' }}>{c.label}</div>
            <div style={{ color: '#64748b', fontSize: '0.78rem', lineHeight: 1.5 }}>{c.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── QAOA Pipeline SVG ────────────────────────────────────────────────────
function QAOAPipeline() {
  const steps = [
    { label: '|+⟩⁰ Initial State', sub: 'Equal superposition of all 2ⁿ routes', color: '#94a3b8', x: 50 },
    { label: 'Cost Hamiltonian Hc', sub: 'e^{-iγHc} — encodes QUBO objective', color: '#f43f5e', x: 175 },
    { label: 'Mixer Hamiltonian Hm', sub: 'e^{-iβHm} — explores solution space', color: '#818cf8', x: 300 },
    { label: 'Repeat p layers', sub: '(Hc → Hm) × p', color: '#f59e0b', x: 410 },
    { label: 'Measure', sub: 'Sample bitstring from |ψ(γ,β)⟩', color: '#38bdf8', x: 510 },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Circuit flow */}
      <svg viewBox="0 0 580 100" style={{ width: '100%', maxHeight: 100, display: 'block' }}>
        {/* Connecting line */}
        <line x1={50} y1={45} x2={530} y2={45} stroke="#1e3a5f" strokeWidth={2} />
        {steps.map((s, i) => (
          <g key={i}>
            <circle cx={s.x} cy={45} r={18} fill={`${s.color}22`} stroke={s.color} strokeWidth={2} />
            <text x={s.x} y={49} fill={s.color} fontSize={10} textAnchor="middle" fontWeight={700}>{i + 1}</text>
            <text x={s.x} y={74} fill={s.color} fontSize={8} textAnchor="middle">{s.label.split(' ')[0]}</text>
            <text x={s.x} y={84} fill={s.color} fontSize={8} textAnchor="middle">{s.label.split(' ').slice(1).join(' ')}</text>
          </g>
        ))}
        {/* Arrows */}
        {[100, 225, 355, 460].map((x, i) => (
          <text key={i} x={x} y={42} fill="#334155" fontSize={14} textAnchor="middle">→</text>
        ))}
      </svg>

      {/* Alternating Hamiltonian detail */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '0.82rem', background: '#0f172a', padding: '1rem', borderRadius: 8, border: '1px solid rgba(244,63,94,0.3)', lineHeight: 2 }}>
          <div style={{ color: '#f43f5e', fontWeight: 700, marginBottom: '0.25rem', fontFamily: 'inherit' }}>Cost Hamiltonian H_C</div>
          <div style={{ color: '#64748b', fontSize: '0.7rem', marginBottom: '0.5rem' }}>Encodes the QUBO energy landscape</div>
          <div style={{ color: '#e2e8f0' }}>H_C = <span style={{ color: '#34d399' }}>Σᵢⱼ Qᵢⱼ σᵢᶻσⱼᶻ</span></div>
          <div style={{ color: '#e2e8f0' }}>U(γ) = e<sup>−iγH_C</sup></div>
          <div style={{ color: '#64748b', fontSize: '0.7rem', marginTop: '0.5rem' }}>γ ∈ [0, 2π] — phase parameter</div>
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '0.82rem', background: '#0f172a', padding: '1rem', borderRadius: 8, border: '1px solid rgba(129,140,248,0.3)', lineHeight: 2 }}>
          <div style={{ color: '#818cf8', fontWeight: 700, marginBottom: '0.25rem', fontFamily: 'inherit' }}>Mixer Hamiltonian H_M</div>
          <div style={{ color: '#64748b', fontSize: '0.7rem', marginBottom: '0.5rem' }}>Drives transitions between states</div>
          <div style={{ color: '#e2e8f0' }}>H_M = <span style={{ color: '#818cf8' }}>Σᵢ σᵢˣ</span></div>
          <div style={{ color: '#e2e8f0' }}>U(β) = e<sup>−iβH_M</sup></div>
          <div style={{ color: '#64748b', fontSize: '0.7rem', marginTop: '0.5rem' }}>β ∈ [0, π] — mixing parameter</div>
        </div>
      </div>

      {/* Classical optimizer loop */}
      <div style={{ padding: '1rem', background: 'rgba(52,211,153,0.06)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: 8 }}>
        <div style={{ color: '#34d399', fontWeight: 700, fontSize: '0.875rem', marginBottom: '0.5rem' }}>Classical Outer Loop — Parameter Optimization</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {[
            'Initialize γ, β randomly',
            '→ Run QAOA circuit on QPU',
            '→ Measure ⟨H_C⟩ expectation',
            '→ Classical optimizer (COBYLA / SPSA)',
            '→ Update γ, β',
            '→ Repeat until convergence',
          ].map((s, i) => (
            <span key={i} style={{
              padding: '0.25rem 0.65rem', borderRadius: 6, fontSize: '0.78rem',
              background: i === 3 ? 'rgba(52,211,153,0.15)' : 'rgba(0,0,0,0.2)',
              color: i === 3 ? '#34d399' : '#94a3b8',
              border: i === 3 ? '1px solid rgba(52,211,153,0.3)' : '1px solid #1e293b',
            }}>{s}</span>
          ))}
        </div>
        <div style={{ color: '#475569', fontSize: '0.78rem', marginTop: '0.75rem' }}>
          The classical optimizer minimizes <code style={{ color: '#34d399' }}>F(γ,β) = ⟨ψ(γ,β)| H_C |ψ(γ,β)⟩</code> — the expected route cost over all quantum samples.
          Optimal parameters γ*, β* encode the probability distribution peaked at the minimum-cost route.
        </div>
      </div>
    </div>
  )
}


// ─── Qubit State Visualization ─────────────────────────────────────────────
function QubitSuperposition({ n = 4 }) {
  const states = Array.from({ length: Math.min(2 ** n, 16) }, (_, i) =>
    i.toString(2).padStart(n, '0')
  )
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.75rem' }}>
      {states.map((s, i) => (
        <div key={i} style={{
          padding: '0.25rem 0.5rem', borderRadius: 6,
          background: `rgba(56,189,248,${0.08 + (i % 5) * 0.04})`,
          border: '1px solid rgba(56,189,248,0.2)',
          fontFamily: 'monospace', fontSize: '0.7rem', color: '#38bdf8',
        }}>{s}</div>
      ))}
      {2 ** n > 16 && (
        <div style={{ padding: '0.25rem 0.5rem', color: '#475569', fontSize: '0.7rem' }}>
          + {(2 ** n - 16).toLocaleString()} more…
        </div>
      )}
    </div>
  )
}

// ─── Tab definitions ──────────────────────────────────────────────────────
const TABS = [
  { id: 'nisq',   label: 'NISQ Era — Today',         icon: <FlaskConical size={15} />, accent: '#f59e0b' },
  { id: 'ftqc',   label: 'Fault-Tolerant — 2029+',   icon: <Zap size={15} />,          accent: '#34d399' },
  { id: 'impact', label: 'Real-World Impact',         icon: <Globe2 size={15} />,       accent: '#c084fc' },
]

// ─── Main Page ────────────────────────────────────────────────────────────
const CIRCUIT_IMGS = [
  {
    src: '/ibm-circuit/circuit-diagram.png',
    label: 'Circuit Diagram',
    desc: 'The QAOA ansatz transpiled for ibm_fez. Pink gates are RZ rotations (single-qubit); blue circles are CNOT-equivalent CX gates (two-qubit entanglers). Qubits q[85]–q[129] are the 16 logical qubits mapped to physical superconducting loops.',
  },
  {
    src: '/ibm-circuit/circuit-qiskit.png',
    label: 'Qiskit Code',
    desc: 'The equivalent Qiskit Python code reconstructed from the transpiled circuit. This is the exact representation dispatched to IBM\'s backend API. The circuit.rz() and circuit.sx() calls correspond to the native gate set of the Eagle r3 processor.',
  },
]

export default function QuantumAdvantage() {
  const [tab, setTab] = useState('nisq')
  const [showQuantum, setShowQuantum] = useState(false)
  const [qubits, setQubits] = useState(4)
  const [circuitImg, setCircuitImg] = useState(0)
  const [lightbox, setLightbox] = useState(false)
  const acc = TABS.find(t => t.id === tab).accent

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h2 className="section-heading">Quantum Advantage: Theory & Roadmap</h2>
        <p className="section-sub">
          An interactive scientific journey — from the quantum energy landscape and superposition, to enterprise-scale global optima.
        </p>
      </div>

      {/* ── Interactive: Energy Landscape ─────────────────────────────── */}
      <div className="panel">
        <h3 className="panel-title"><Atom size={20} /> The QUBO Energy Landscape</h3>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1rem' }}>
          VRP is encoded as a <strong style={{ color: '#f8fafc' }}>QUBO Hamiltonian</strong> — a bumpy energy landscape
          where the lowest valley is the cheapest valid route. Classical solvers descend greedily and
          get stuck in <em>local minima</em>. Quantum hardware uses <em>tunneling</em> to reach the true global minimum.
        </p>
        <EnergyLandscape showQuantum={showQuantum} />
        <button
          className="btn-primary"
          style={{ marginTop: '1rem', background: showQuantum ? 'linear-gradient(135deg,#059669,#0d9488)' : 'linear-gradient(135deg,#0284c7,#2563eb)' }}
          onClick={() => setShowQuantum(v => !v)}
        >
          <Atom size={15} /> {showQuantum ? 'Hide Quantum Tunneling' : 'Show Quantum Tunneling'}
        </button>
      </div>

      {/* ── QUBO Explainer ────────────────────────────────────────────── */}
      <div className="panel">
        <h3 className="panel-title" style={{ color: '#38bdf8' }}><Atom size={20} /> QUBO: Quadratic Unconstrained Binary Optimization</h3>
        <QuboExplainer />
      </div>

      {/* ── QAOA Pipeline ─────────────────────────────────────────────── */}
      <div className="panel">
        <h3 className="panel-title" style={{ color: '#c084fc' }}><Zap size={20} /> QAOA: Alternating Hamiltonian Circuit</h3>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1.25rem' }}>
          QAOA applies alternating layers of the <strong style={{ color: '#f43f5e' }}>Cost Hamiltonian H_C</strong> (which imprints the QUBO energy) and
          the <strong style={{ color: '#818cf8' }}>Mixer Hamiltonian H_M</strong> (which drives quantum exploration). Parameters γ and β are
          tuned by a classical outer-loop optimizer to maximally amplify the probability of sampling the lowest-cost route.
        </p>
        <QAOAPipeline />
      </div>

      {/* ── Interactive: Superposition Explorer ───────────────────────── */}
      <div className="panel">
        <h3 className="panel-title"><Cpu size={20} /> Quantum Superposition Explorer</h3>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1rem' }}>
          When a quantum register of <strong style={{ color: '#38bdf8' }}>{qubits} qubits</strong> is
          initialized, it simultaneously represents <strong style={{ color: '#38bdf8' }}>2<sup>{qubits}</sup> = {(2 ** qubits).toLocaleString()}</strong> possible
          routing combinations in a single quantum state. A classical CPU must check each one sequentially.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
          <label style={{ color: '#94a3b8', fontSize: '0.875rem', whiteSpace: 'nowrap' }}>Qubits: {qubits}</label>
          <input
            type="range" min={2} max={10} value={qubits}
            onChange={e => setQubits(Number(e.target.value))}
            style={{ flex: 1, accentColor: '#38bdf8' }}
          />
          <div style={{ color: '#38bdf8', fontWeight: 700, fontSize: '1rem', minWidth: '80px', textAlign: 'right' }}>
            {(2 ** qubits).toLocaleString()} states
          </div>
        </div>
        <p style={{ color: '#475569', fontSize: '0.8rem', margin: '0 0 0.5rem' }}>
          {qubits <= 5 ? 'All states shown:' : `Showing first 16 of ${(2**qubits).toLocaleString()} states:`}
        </p>
        <QubitSuperposition n={qubits} />
      </div>

      {/* ── Theory Tabs ───────────────────────────────────────────────── */}
      <div>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
          {TABS.map(t => (
            <button
              key={t.id}
              className={`btn-tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
              style={tab === t.id ? { borderColor: t.accent, color: t.accent, background: `${t.accent}18` } : {}}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        <div className="panel fade-in" key={tab}>
          {tab === 'nisq' && (
            <div>
              <div style={{ color: '#f59e0b', fontWeight: 700, marginBottom: '1rem', fontSize: '1.1rem' }}>
                Why Classical Still Wins Today
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: '1rem' }}>
                {[
                  { title: 'Decoherence', text: 'NISQ-era qubits have very short coherence times — they lose their quantum state before deep circuits can fully execute. High gate-depth circuits, like our QAOA ansatz, accumulate enough noise that the output collapses toward random noise rather than the true optimum.' },
                  { title: 'QAOA Depth Constraint', text: 'Finding the global minimum requires many circuit layers (high p). Short coherence times force us to run at p=1 — equivalent to taking only one step downhill on the energy landscape, almost certainly stopping at a local minimum rather than the true global minimum.' },
                  { title: 'Small-Scale Regime', text: 'For N<30 nodes, a CPU evaluates 2^N combinations in milliseconds. NISQ hardware cannot beat this.' },
                ].map((c, i) => (
                  <div key={i} className="theory-card" style={{ borderLeftColor: '#f59e0b' }}>
                    <div style={{ color: '#f59e0b', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.35rem' }}>0{i + 1}</div>
                    <h4>{c.title}</h4>
                    <p>{c.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === 'ftqc' && (
            <div>
              <div style={{ color: '#34d399', fontWeight: 700, marginBottom: '1rem', fontSize: '1.1rem' }}>
                The Inevitable Quantum Crossover
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: '1rem' }}>
                {[
                  { title: 'Error-Corrected Logical Qubits', text: 'Surface Code encodes one logical qubit across ~1,000 physical qubits. Coherence extends from microseconds to minutes. IBM roadmap: 10,000 logical qubits by 2033.' },
                  { title: 'Deep QAOA (p ≥ 20)', text: 'With long coherence time, QAOA at p=20+ provably converges to the true ground state of the QUBO Hamiltonian — the absolute global minimum route.' },
                  { title: 'Complexity Class Separation', text: 'VRP is NP-Hard (O(N!) classical). Deep QAOA provides conjectured super-polynomial speedup. Every doubling of customers adds only a fixed number of layers — not an exponential blowup.' },
                ].map((c, i) => (
                  <div key={i} className="theory-card" style={{ borderLeftColor: '#34d399' }}>
                    <div style={{ color: '#34d399', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.35rem' }}>0{i + 1}</div>
                    <h4>{c.title}</h4>
                    <p>{c.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === 'impact' && (
            <div>
              <div style={{ color: '#c084fc', fontWeight: 700, marginBottom: '1rem', fontSize: '1.1rem' }}>
                Scientific & Commercial Significance
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: '1rem' }}>
                {[
                  { title: 'The Enterprise Pain Point', text: 'Amazon, FedEx, Maersk waste billions on sub-optimal routing. Classical heuristics get stuck in local optima on networks with real-time traffic, multi-modal fleets, and complex delivery windows.' },
                  { title: 'Quantum Tunneling Advantage', text: 'QUBO maps the supply chain onto quantum Hamiltonian energy levels. Hardware physically finds the lowest energy state via quantum tunneling — bypassing barriers that trap classical hill-climbing.' },
                  { title: 'Hardware-Ready Pipeline', text: 'Our QUBO formulation is deployed on ibm_fez today. When fault-tolerant hardware arrives, zero re-engineering is needed — the same code delivers true global optima at enterprise scale.' },
                ].map((c, i) => (
                  <div key={i} className="theory-card" style={{ borderLeftColor: '#c084fc' }}>
                    <div style={{ color: '#c084fc', fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.35rem' }}>0{i + 1}</div>
                    <h4>{c.title}</h4>
                    <p>{c.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* IBM Hardware Stats */}
      <div className="panel" style={{ borderColor: 'rgba(56,189,248,0.15)' }}>
        <h3 className="panel-title"><FlaskConical size={20} /> Our IBM Hardware Run — ibm_fez (156 Qubits)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '1rem' }}>
          {[
            { label: 'Problem Size', value: '16 Qubits', sub: '4 customers × 4 positions' },
            { label: 'State Space', value: '65,536', sub: 'Combinations in superposition' },
            { label: 'Circuit Depth', value: '681 Gates', sub: 'Transpiled for superconducting' },
            { label: 'Shots Executed', value: '4,096', sub: 'Physical executions on QPU' },
          ].map((s, i) => (
            <div key={i} style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: 8, textAlign: 'center' }}>
              <div style={{ color: '#94a3b8', fontSize: '0.7rem', marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{s.label}</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8' }}>{s.value}</div>
              <div style={{ color: '#475569', fontSize: '0.7rem', marginTop: '0.3rem' }}>{s.sub}</div>
            </div>
          ))}
        </div>
      </div>
      {/* ── IBM Circuit Gallery ────────────────────────────────────────── */}
      <div className="panel" style={{ borderColor: 'rgba(129,140,248,0.2)' }}>
        <h3 className="panel-title" style={{ color: '#818cf8' }}>
          <FlaskConical size={20} /> Live IBM Dashboard — Transpiled Circuit Screenshots
        </h3>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1.25rem' }}>
          These screenshots were captured directly from the IBM Quantum dashboard for Job ID <code style={{ color: '#818cf8', background: 'rgba(129,140,248,0.1)', padding: '0.1rem 0.4rem', borderRadius: 4 }}>d84c4k80bvlc73d4dg9g</code> running on <strong style={{ color: '#f8fafc' }}>ibm_fez</strong>. Click any image to enlarge.
        </p>

        {/* Tab selector */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {CIRCUIT_IMGS.map((img, i) => (
            <button
              key={i}
              className={`btn-tab ${circuitImg === i ? 'active' : ''}`}
              onClick={() => setCircuitImg(i)}
              style={circuitImg === i ? { borderColor: '#818cf8', color: '#818cf8', background: 'rgba(129,140,248,0.1)' } : {}}
            >
              {img.label}
            </button>
          ))}
        </div>

        {/* Image display */}
        <div
          className="fade-in"
          key={circuitImg}
          style={{ position: 'relative', cursor: 'zoom-in' }}
          onClick={() => setLightbox(true)}
        >
          <img
            src={CIRCUIT_IMGS[circuitImg].src}
            alt={CIRCUIT_IMGS[circuitImg].label}
            style={{
              width: '100%', borderRadius: 10,
              border: '1px solid rgba(129,140,248,0.25)',
              display: 'block',
              transition: 'opacity 0.2s',
            }}
          />
          <div style={{
            position: 'absolute', top: '0.75rem', right: '0.75rem',
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            padding: '0.3rem 0.6rem', borderRadius: 6,
            color: '#94a3b8', fontSize: '0.75rem',
          }}>
            Click to expand
          </div>
        </div>

        {/* Caption */}
        <div style={{ marginTop: '1rem', padding: '0.875rem 1rem', background: 'rgba(0,0,0,0.2)', borderRadius: 8, color: '#94a3b8', fontSize: '0.875rem', lineHeight: 1.6 }}>
          <span style={{ color: '#818cf8', fontWeight: 600 }}>{CIRCUIT_IMGS[circuitImg].label}: </span>
          {CIRCUIT_IMGS[circuitImg].desc}
        </div>
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="modal-overlay"
          onClick={() => setLightbox(false)}
          style={{ cursor: 'zoom-out' }}
        >
          <div style={{ maxWidth: '95vw', maxHeight: '90vh', position: 'relative' }}>
            <img
              src={CIRCUIT_IMGS[circuitImg].src}
              alt={CIRCUIT_IMGS[circuitImg].label}
              style={{ width: '100%', height: '100%', objectFit: 'contain', borderRadius: 12, display: 'block' }}
            />
            <button
              className="close-btn"
              onClick={() => setLightbox(false)}
              style={{ position: 'absolute', top: '0.75rem', right: '0.75rem', background: 'rgba(0,0,0,0.6)', padding: '0.4rem 0.7rem', borderRadius: 8, fontSize: '1rem' }}
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
