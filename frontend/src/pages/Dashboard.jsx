import { useEffect, useState } from 'react'
import axios from 'axios'
import { Activity, Target, Atom, Database } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts'

const PRIORITY_COLOR = { High: '#f43f5e', Medium: '#f59e0b', Low: '#34d399' }

export default function Dashboard() {
  const [scalingData, setScalingData] = useState([])
  const [dataset, setDataset] = useState(null)
  const [dataTab, setDataTab] = useState('suppliers')

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/scaling_data').then(res => setScalingData(res.data)).catch(() => {})
    axios.get('http://127.0.0.1:5000/api/dataset_overview').then(res => setDataset(res.data)).catch(() => {})
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* Problem Statement */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className="panel">
          <h3 className="panel-title"><Target size={20} /> The Problem</h3>
          <p style={{ color: '#94a3b8', lineHeight: 1.8, margin: 0 }}>
            Optimize the key parameters of an <strong style={{ color: '#f8fafc' }}>end-to-end supply chain</strong> —
            namely <strong style={{ color: '#f43f5e' }}>Supplier Selection</strong>, <strong style={{ color: '#f59e0b' }}>Inventory Allocation</strong>,
            and <strong style={{ color: '#34d399' }}>Vehicle Routing</strong> — simultaneously as a single unified problem.
            <br /><br />
            Jointly optimizing all three is an <strong style={{ color: '#f43f5e' }}>NP-Hard</strong> combinatorial problem: the solution space
            grows factorially with the number of nodes, making it computationally intractable for
            classical exact solvers beyond ~30 nodes.
          </p>
        </div>
        <div className="panel">
          <h3 className="panel-title"><Atom size={20} /> Our Goal</h3>
          <p style={{ color: '#94a3b8', lineHeight: 1.8, margin: 0 }}>
            We first optimize each supply chain sub-problem <strong style={{ color: '#f8fafc' }}>independently</strong> —
            Supplier Selection, Inventory Allocation, and Vehicle Routing — using classical methods to
            establish individual baselines.
            <br /><br />
            We then build a <strong style={{ color: '#38bdf8' }}>Global Unified Optimizer</strong> (MILP) that
            incorporates the <em>correlated constraints</em> across all three sub-problems simultaneously,
            capturing interdependencies that sequential solvers miss.
            <br /><br />
            Finally, we encode the <strong style={{ color: '#818cf8' }}>Vehicle Routing sub-problem as a QUBO</strong> and
            execute it on IBM's 156-qubit <code style={{ color: '#818cf8' }}>ibm_fez</code> processor via QAOA —
            establishing a <strong style={{ color: '#f8fafc' }}>quantum vs. classical benchmark</strong> on real hardware.
          </p>
        </div>
      </div>

      {/* Dataset Overview */}
      <div className="panel">
        <h3 className="panel-title"><Database size={20} /> Dataset Overview</h3>

        {/* Count pills */}
        {dataset && (
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
            {[
              { label: 'Suppliers',  value: dataset.counts.suppliers,  color: '#f59e0b' },
              { label: 'Warehouses', value: dataset.counts.warehouses, color: '#818cf8' },
              { label: 'Customers',  value: dataset.counts.customers,  color: '#34d399' },
              { label: 'Vehicles',   value: dataset.counts.vehicles,   color: '#38bdf8' },
              { label: 'Routes',     value: dataset.counts.routes,     color: '#c084fc' },
            ].map(s => (
              <div key={s.label} style={{
                padding: '0.5rem 1.25rem', borderRadius: 999,
                background: `${s.color}12`, border: `1px solid ${s.color}30`,
                display: 'flex', gap: '0.5rem', alignItems: 'center',
              }}>
                <span style={{ fontSize: '1.2rem', fontWeight: 800, color: s.color }}>{s.value}</span>
                <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{s.label}</span>
              </div>
            ))}
          </div>
        )}

        {/* Tab selector */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {['suppliers', 'warehouses', 'customers'].map(t => (
            <button
              key={t}
              className={`btn-tab ${dataTab === t ? 'active' : ''}`}
              onClick={() => setDataTab(t)}
              style={dataTab === t ? {
                borderColor: t === 'suppliers' ? '#f59e0b' : t === 'warehouses' ? '#818cf8' : '#34d399',
                color:       t === 'suppliers' ? '#f59e0b' : t === 'warehouses' ? '#818cf8' : '#34d399',
                background:  t === 'suppliers' ? '#f59e0b18' : t === 'warehouses' ? '#818cf818' : '#34d39918',
              } : {}}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* Tables */}
        {dataset ? (
          <div className="fade-in" key={dataTab} style={{ overflowX: 'auto' }}>

            {dataTab === 'suppliers' && (
              <table>
                <thead><tr>
                  <th>ID</th><th>Capacity (units)</th><th>Cost / Unit ($)</th><th>Lead Time</th><th>Reliability</th>
                </tr></thead>
                <tbody>
                  {dataset.suppliers.map(s => (
                    <tr key={s.id}>
                      <td><span className="badge" style={{ background: '#f59e0b18', color: '#f59e0b' }}>{s.id}</span></td>
                      <td>{s.capacity.toLocaleString()}</td>
                      <td>${s.cost_per_unit.toFixed(2)}</td>
                      <td>{s.lead_time_days}d</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#1e293b' }}>
                            <div style={{ width: `${s.reliability * 100}%`, height: '100%', borderRadius: 3, background: s.reliability >= 0.9 ? '#34d399' : s.reliability >= 0.75 ? '#f59e0b' : '#f43f5e' }} />
                          </div>
                          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{(s.reliability * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {dataTab === 'warehouses' && (
              <table>
                <thead><tr>
                  <th>ID</th><th>Storage Capacity (units)</th><th>Holding Cost ($/unit)</th>
                </tr></thead>
                <tbody>
                  {dataset.warehouses.map(w => (
                    <tr key={w.id}>
                      <td><span className="badge" style={{ background: '#818cf818', color: '#818cf8' }}>{w.id}</span></td>
                      <td>{w.storage_capacity.toLocaleString()}</td>
                      <td>${w.holding_cost.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {dataTab === 'customers' && (
              <table>
                <thead><tr>
                  <th>ID</th><th>Demand (units)</th><th>Deadline</th>
                </tr></thead>
                <tbody>
                  {dataset.customers.map(c => (
                    <tr key={c.id}>
                      <td><span className="badge" style={{ background: '#34d39918', color: '#34d399' }}>{c.id}</span></td>
                      <td>{c.demand_units}</td>
                      <td>{c.deadline_days}d</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="loading">Loading dataset...</div>
        )}
      </div>

      {/* Scaling Graph */}
      <div className="panel">
        <h3 className="panel-title"><Activity size={20} /> Execution Time Scaling: Classical vs QAOA</h3>
        <p style={{ color: '#64748b', fontSize: '0.9rem', margin: '0 0 0.5rem' }}>
          Modeled execution time (seconds) as the number of VRP nodes grows. The classical exact solver scales exponentially,
          while QAOA execution on the QPU grows sub-exponentially based on circuit depth.
        </p>

        {/* Legend chips */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
          {[
            { color: '#f43f5e', label: 'Classical Exact CPU Time', complexity: 'O(2ᴺ · N²)' },
            { color: '#38bdf8', label: 'QAOA QPU Execution Time', complexity: 'Sub-exponential (Circuit Depth)' },
          ].map(l => (
            <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.3rem 0.75rem', borderRadius: 999, background: `${l.color}10`, border: `1px solid ${l.color}30` }}>
              <span style={{ width: 10, height: 3, borderRadius: 2, background: l.color, display: 'inline-block' }} />
              <span style={{ color: '#94a3b8', fontSize: '0.78rem' }}>{l.label}</span>
              <code style={{ color: l.color, fontSize: '0.75rem' }}>{l.complexity}</code>
            </div>
          ))}
        </div>

        <div style={{ height: 380 }}>
          {scalingData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={scalingData} margin={{ top: 5, right: 40, left: 20, bottom: 35 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                <XAxis
                  dataKey="nodes"
                  stroke="#475569"
                  label={{ value: 'Problem Size (N nodes)', position: 'insideBottom', offset: -20, fill: '#64748b', fontSize: 12 }}
                />
                <YAxis
                  scale="log"
                  domain={[1e-6, 1e6]}
                  stroke="#475569"
                  tickFormatter={val => val >= 1 ? val.toLocaleString() : val.toExponential()}
                  label={{ value: 'Execution Time (seconds) — Log Scale', angle: -90, position: 'insideLeft', offset: 0, fill: '#64748b', fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '0.75rem' }}
                  itemStyle={{ color: '#f8fafc' }}
                  labelFormatter={v => `N = ${v} nodes`}
                  formatter={(val, name) => [`${val >= 1000000 ? '> 1,000,000' : val.toLocaleString()} s`, name]}
                />
                <ReferenceLine x="28" stroke="#f59e0b" strokeDasharray="6 3" label={{ value: 'Crossover ~28 nodes', fill: '#f59e0b', fontSize: 11, position: 'top' }} />
                <Line type="monotone" dataKey="classical_time" name="Classical CPU" stroke="#f43f5e" strokeWidth={3} dot={{ r: 5, fill: '#f43f5e' }} activeDot={{ r: 8 }} />
                <Line type="monotone" dataKey="qaoa_time"      name="QAOA QPU"      stroke="#38bdf8" strokeWidth={3} dot={{ r: 5, fill: '#38bdf8' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="loading">Loading data...</div>
          )}
        </div>

        {/* Methodology */}
        <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {[
            {
              color: '#f43f5e',
              title: 'Classical Exact Baseline',
              complexity: 'O(2ᴺ · N²)',
              desc: 'Time modelled for the best-known exact algorithm (Held-Karp). At N=28, classical execution surpasses realistic thresholds. At N=40, it would take years, proving the "Classical Wall".',
            },
            {
              color: '#38bdf8',
              title: 'QAOA Hardware Execution',
              complexity: 'QPU Overhead + Depth Scaling',
              desc: 'Time modelled as base hardware overhead (~5s) plus pulse execution time which scales with QAOA circuit depth O(N^2.5). Avoids the exponential blowup.',
            },
          ].map(c => (
            <div key={c.title} style={{ padding: '0.875rem', background: `${c.color}08`, border: `1px solid ${c.color}25`, borderRadius: 8 }}>
              <code style={{ color: c.color, fontSize: '0.75rem', fontWeight: 700 }}>{c.complexity}</code>
              <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '0.8rem', margin: '0.3rem 0' }}>{c.title}</div>
              <p style={{ color: '#64748b', fontSize: '0.78rem', lineHeight: 1.55, margin: 0 }}>{c.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
