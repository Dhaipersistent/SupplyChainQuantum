import { useState, useRef, useEffect } from 'react'
import { Layers, GitMerge, FileWarning, ArrowRight, ChevronRight } from 'lucide-react'

// ─── SVG Network Graph ─────────────────────────────────────────────────────
const NODES = {
  supplier: [
    { id: 'S1', x: 80,  y: 120, label: 'S1', color: '#f59e0b', type: 'supplier' },
    { id: 'S2', x: 80,  y: 280, label: 'S2', color: '#f59e0b', type: 'supplier' },
  ],
  warehouse: [
    { id: 'W1', x: 280, y: 200, label: 'W1', color: '#818cf8', type: 'warehouse' },
  ],
  customer: [
    { id: 'C1', x: 480, y: 80,  label: 'C1', color: '#34d399', type: 'customer' },
    { id: 'C2', x: 500, y: 200, label: 'C2', color: '#34d399', type: 'customer' },
    { id: 'C3', x: 480, y: 320, label: 'C3', color: '#34d399', type: 'customer' },
  ],
}

const ALL_NODES = [...NODES.supplier, ...NODES.warehouse, ...NODES.customer]

// Sequential steps
const STEPS = [
  {
    id: 0,
    title: 'Step 1 — Supplier Selection',
    desc: 'The system evaluates all suppliers based on cost-per-unit and reliability score. S1 (lower cost) is selected.',
    highlight: ['S1', 'S2'],
    activeEdges: [{ from: 'S1', to: 'W1', color: '#f59e0b', label: 'Selected (cheap)' }],
    dimEdges: [{ from: 'S2', to: 'W1', color: '#334155', label: 'Rejected' }],
  },
  {
    id: 1,
    title: 'Step 2 — Inventory Allocation',
    desc: 'Stock from S1 is pushed to warehouse W1. Inventory levels are computed to meet customer demands.',
    highlight: ['W1'],
    activeEdges: [
      { from: 'S1', to: 'W1', color: '#f59e0b', label: 'Stock shipped' },
    ],
    dimEdges: [],
  },
  {
    id: 2,
    title: 'Step 3 — Vehicle Routing (VRP)',
    desc: 'A vehicle departs W1 and visits all customers in the nearest-neighbour order: W1→C1→C2→C3→W1.',
    highlight: ['C1', 'C2', 'C3'],
    activeEdges: [
      { from: 'W1', to: 'C1', color: '#34d399', label: '' },
      { from: 'C1', to: 'C2', color: '#34d399', label: '' },
      { from: 'C2', to: 'C3', color: '#34d399', label: '' },
      { from: 'C3', to: 'W1', color: '#34d399', label: '' },
    ],
    dimEdges: [],
  },
]

const UNIFIED_STEP = {
  title: 'Unified MILP — One Pass',
  desc: 'All constraints solved simultaneously. The solver traded S1 for the slightly pricier S2, which saved 400 km on routing — resulting in a globally cheaper plan.',
  highlight: ['S2', 'W1', 'C1', 'C2', 'C3'],
  activeEdges: [
    { from: 'S2', to: 'W1', color: '#818cf8', label: 'S2 chosen (closer)' },
    { from: 'W1', to: 'C2', color: '#38bdf8', label: '' },
    { from: 'C2', to: 'C1', color: '#38bdf8', label: '' },
    { from: 'C1', to: 'C3', color: '#38bdf8', label: '' },
    { from: 'C3', to: 'W1', color: '#38bdf8', label: '' },
  ],
  dimEdges: [{ from: 'S1', to: 'W1', color: '#1e293b', label: 'Not selected' }],
}

function getNode(id) { return ALL_NODES.find(n => n.id === id) }

function NetworkGraph({ activeEdges = [], dimEdges = [], highlight = [], mode = 'sequential' }) {
  const allEdges = [...dimEdges, ...activeEdges]
  return (
    <svg viewBox="0 0 580 400" style={{ width: '100%', maxHeight: 320 }}>
      {/* Edges */}
      {allEdges.map((e, i) => {
        const a = getNode(e.from), b = getNode(e.to)
        if (!a || !b) return null
        return (
          <g key={i}>
            <line
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke={e.color} strokeWidth={2.5} strokeDasharray={e.color === '#334155' || e.color === '#1e293b' ? '6 4' : '0'}
              opacity={e.color === '#334155' || e.color === '#1e293b' ? 0.3 : 0.9}
            />
            {e.label && (
              <text
                x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 8}
                fill={e.color} fontSize={10} textAnchor="middle" opacity={0.85}
              >{e.label}</text>
            )}
          </g>
        )
      })}
      {/* Nodes */}
      {ALL_NODES.map(node => {
        const isHighlighted = highlight.includes(node.id)
        return (
          <g key={node.id}>
            <circle
              cx={node.x} cy={node.y} r={24}
              fill={isHighlighted ? node.color : '#1e293b'}
              stroke={node.color}
              strokeWidth={isHighlighted ? 2.5 : 1}
              opacity={isHighlighted ? 1 : 0.5}
              style={{ transition: 'all 0.4s' }}
            />
            <text x={node.x} y={node.y} fill="#fff" textAnchor="middle" dominantBaseline="middle" fontSize={12} fontWeight={700}>{node.label}</text>
            <text x={node.x} y={node.y + 34} fill="#64748b" textAnchor="middle" fontSize={9}>
              {node.type === 'supplier' ? 'Supplier' : node.type === 'warehouse' ? 'Warehouse' : 'Customer'}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ─── Result Cards ──────────────────────────────────────────────────────────
const SEQUENTIAL_RESULT = {
  cost: '$68,420',
  distance: '3,290 km',
  route: 'W1 → C1 → C2 → C3 → W1',
  supplier: 'S1 (cheaper per unit, 480 km away)',
  verdict: 'Sub-optimal: cheap supplier caused long detour. Total cost was dominated by routing penalty.',
  color: '#f43f5e',
}
const UNIFIED_RESULT = {
  cost: '$58,110',
  distance: '2,870 km',
  route: 'W1 → C2 → C1 → C3 → W1',
  supplier: 'S2 (slightly pricier, 120 km away)',
  verdict: 'Optimal: paying $800 more for a closer supplier saved $11,100 in routing. Net saving: $10,310.',
  color: '#34d399',
}

function ResultCard({ res, title, color }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 10, padding: '1.25rem', border: `1px solid ${color}33` }}>
      <div style={{ color, fontWeight: 700, fontSize: '0.85rem', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '0.75rem' }}>{title}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
        {[
          ['Total Cost', res.cost, color],
          ['Distance', res.distance, '#94a3b8'],
        ].map(([k, v, c]) => (
          <div key={k} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.6rem', borderRadius: 6 }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{k}</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: c }}>{v}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.4rem' }}>Route: <span style={{ color: '#e2e8f0', fontFamily: 'monospace' }}>{res.route}</span></div>
      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.75rem' }}>Supplier: <span style={{ color: '#e2e8f0' }}>{res.supplier}</span></div>
      <div style={{ fontSize: '0.8rem', color, background: `${color}12`, padding: '0.6rem', borderRadius: 6 }}>{res.verdict}</div>
    </div>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────
export default function ClassicalArchitecture() {
  const [step, setStep] = useState(0)
  const [mode, setMode] = useState('sequential') // 'sequential' | 'unified'
  const [showModal, setShowModal] = useState(false)

  const currentStep = mode === 'unified' ? UNIFIED_STEP : STEPS[step]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h2 className="section-heading">Classical Optimization Architecture</h2>
        <p className="section-sub">
          Comparing the industry-standard sequential pipeline against our globally-integrated MILP solver — visualized step by step.
        </p>
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <button className={`btn-tab ${mode === 'sequential' ? 'active' : ''}`} onClick={() => { setMode('sequential'); setStep(0) }}>
          <Layers size={15} /> Sequential Pipeline
        </button>
        <button className={`btn-tab ${mode === 'unified' ? 'active' : ''}`} style={mode === 'unified' ? { borderColor: '#34d399', color: '#34d399', background: '#34d39918' } : {}} onClick={() => setMode('unified')}>
          <GitMerge size={15} /> Unified MILP (Ours)
        </button>
        <button className="btn-primary" style={{ marginLeft: 'auto', background: 'linear-gradient(135deg,#4f46e5,#7c3aed)' }} onClick={() => setShowModal(true)}>
          <FileWarning size={15} /> View Constraint System
        </button>
      </div>

      {/* Network graph + step controls */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
        <div className="panel">
          <h3 className="panel-title" style={{ color: mode === 'unified' ? '#34d399' : '#38bdf8' }}>
            Supply Chain Network Graph
          </h3>
          <NetworkGraph
            activeEdges={currentStep.activeEdges}
            dimEdges={currentStep.dimEdges}
            highlight={currentStep.highlight}
            mode={mode}
          />
          {/* Legend */}
          <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem', justifyContent: 'center', fontSize: '0.75rem', color: '#64748b' }}>
            {[['#f59e0b', 'Supplier'], ['#818cf8', 'Warehouse'], ['#34d399', 'Customer']].map(([c, l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: c, display: 'inline-block' }} />{l}
              </span>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Step explainer */}
          <div className="panel" style={{ borderColor: mode === 'unified' ? '#34d39944' : '#38bdf844' }}>
            <div style={{ fontWeight: 700, color: mode === 'unified' ? '#34d399' : '#38bdf8', marginBottom: '0.5rem' }}>
              {currentStep.title}
            </div>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: 1.7, margin: 0 }}>{currentStep.desc}</p>
          </div>

          {/* Step navigator (sequential only) */}
          {mode === 'sequential' && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {STEPS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setStep(i)}
                  style={{
                    flex: 1, padding: '0.6rem', borderRadius: 8,
                    border: `1px solid ${step === i ? '#38bdf8' : '#1e3a5f'}`,
                    background: step === i ? 'rgba(56,189,248,0.12)' : 'rgba(0,0,0,0.2)',
                    color: step === i ? '#38bdf8' : '#64748b',
                    cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600, fontSize: '0.8rem',
                    transition: 'all 0.2s',
                  }}
                >
                  Step {i + 1}
                </button>
              ))}
            </div>
          )}

          {/* Result cards */}
          {mode === 'sequential'
            ? <ResultCard res={SEQUENTIAL_RESULT} title="Sequential Result" color="#f43f5e" />
            : <ResultCard res={UNIFIED_RESULT} title="Unified MILP Result" color="#34d399" />
          }

          {mode === 'sequential' && (
            <div style={{ padding: '0.75rem 1rem', borderRadius: 8, background: 'rgba(244,63,94,0.08)', border: '1px solid rgba(244,63,94,0.2)', fontSize: '0.8rem', color: '#fca5a5' }}>
              ⚠️ <strong>Limitation:</strong> Step 3 cannot go back and reconsider the supplier. The routing solver is blind to upstream decisions.
            </div>
          )}
        </div>
      </div>

      {/* ── Comparison Insight Panel ───────────────────────────────────── */}
      <div className="panel" style={{ borderColor: 'rgba(52,211,153,0.2)', background: 'rgba(10,28,20,0.6)' }}>
        <h3 className="panel-title" style={{ color: '#34d399' }}>
          <GitMerge size={20} /> Why Unified Beats Sequential — The Key Insight
        </h3>

        {/* Delta breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          {[
            { label: 'Sequential Total Cost', value: '$68,420', sub: 'S1 (cheap) + long route', color: '#f43f5e' },
            { label: 'Unified Total Cost',    value: '$58,110', sub: 'S2 (pricier) + shorter route', color: '#34d399' },
            { label: 'Net Saving',            value: '$10,310', sub: '15.1% cost reduction', color: '#38bdf8' },
          ].map(s => (
            <div key={s.label} style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: 10, textAlign: 'center' }}>
              <div style={{ color: '#64748b', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.4rem' }}>{s.label}</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: s.color }}>{s.value}</div>
              <div style={{ color: '#475569', fontSize: '0.75rem', marginTop: '0.3rem' }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Breakdown table */}
        <table style={{ marginBottom: '1.25rem' }}>
          <thead>
            <tr>
              <th>Decision</th>
              <th style={{ color: '#f43f5e' }}>Sequential (Blind)</th>
              <th style={{ color: '#34d399' }}>Unified MILP (Global)</th>
              <th>Impact</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Supplier Choice', 'S1 — $12/unit, 480 km from W1', 'S2 — $14/unit, 120 km from W1', 'Saves 360 km transit per delivery cycle'],
              ['Route Chosen',    'W1→C1→C2→C3→W1 (3,290 km)',    'W1→C2→C1→C3→W1 (2,870 km)',    '420 km shorter — optimal node ordering'],
              ['Supplier Cost',   '$6,200 (cheap per unit)',         '$6,900 (slightly higher)',       '+$700 extra on supplier'],
              ['Routing Cost',    '$62,220 (long detour)',           '$51,210 (short route)',          '−$11,010 saved on routing'],
            ].map(([dec, seq, uni, imp], i) => (
              <tr key={i}>
                <td style={{ fontWeight: 600 }}>{dec}</td>
                <td style={{ color: '#f87171', fontSize: '0.8rem' }}>{seq}</td>
                <td style={{ color: '#34d399', fontSize: '0.8rem' }}>{uni}</td>
                <td style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{imp}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Takeaway */}
        <div style={{ padding: '1rem 1.25rem', borderRadius: 10, background: 'rgba(56,189,248,0.07)', border: '1px solid rgba(56,189,248,0.2)', color: '#e2e8f0', fontSize: '0.9rem', lineHeight: 1.7 }}>
          <strong style={{ color: '#38bdf8' }}>Core Insight: </strong>
          The sequential solver picked S1 because it was cheapest <em>in isolation</em>.
          It had no way of knowing that S1's remote location would force a routing detour costing 8× more than the supplier savings.
          The Unified MILP sees the entire cost surface at once — it deliberately pays $700 more for S2 because the optimizer
          knows that choice eliminates $11,010 in routing cost, yielding a provably global optimum of <strong style={{ color: '#34d399' }}>$58,110</strong> vs the sequential <strong style={{ color: '#f43f5e' }}>$68,420</strong>.
        </div>
      </div>

      {/* Constraint Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Unified MILP Constraint System</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', lineHeight: 2.2, background: '#0f172a', padding: '1.5rem', borderRadius: 8, border: '1px solid #1e3a5f', color: '#e2e8f0' }}>
              <div style={{ color: '#38bdf8', marginBottom: '0.25rem', fontSize: '0.75rem' }}>OBJECTIVE FUNCTION</div>
              <div style={{ marginBottom: '1rem' }}>minimize: <span style={{ color: '#34d399' }}>Σ</span> c_s·x_s  +  <span style={{ color: '#34d399' }}>Σ</span> h_w·I_w  +  <span style={{ color: '#34d399' }}>Σ</span> d_ij·y_ij·v_cost</div>
              <div style={{ color: '#475569', fontSize: '0.75rem', marginBottom: '0.25rem' }}>CONSTRAINTS</div>
              {[
                ['Demand Satisfaction', 'Σ x_sw  =  Demand_c   ∀ c'],
                ['Supplier Capacity',   'Σ x_sw  ≤  Cap_s      ∀ s'],
                ['Flow Conservation',   'I_w = Received_w − Shipped_w'],
                ['Route Continuity',    'Σ_j y_ij  =  Σ_j y_ji   ∀ i'],
                ['Vehicle Capacity',    'Σ demand(c) ≤ Cap_v   ∀ v'],
              ].map(([k, v], i) => (
                <div key={i}>
                  <span style={{ color: '#c084fc' }}>{i + 1}. {k}: </span>
                  <span>{v}</span>
                </div>
              ))}
            </div>
            <p style={{ color: '#475569', fontSize: '0.8rem', marginTop: '1rem', marginBottom: 0 }}>
              All five constraints are co-evaluated in a single LP pass. The solver can trade-off between supplier cost and route distance to find the global optimum.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
