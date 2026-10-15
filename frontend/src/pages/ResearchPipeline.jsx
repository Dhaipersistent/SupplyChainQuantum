import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import {
  Activity,
  ArrowDown,
  ArrowRight,
  CircleAlert,
  Cpu,
  Database,
  FlaskConical,
  GitBranch,
  Layers3,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Warehouse,
} from 'lucide-react'
import {
  CartesianGrid,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './ResearchPipeline.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'
const EMPTY_RESULTS = {
  available: false,
  results: [],
  assignments: [],
  reduction_history: [],
  qaoa_history: [],
  experiment_log: [],
}

function formatNumber(value, digits = 2) {
  if (!Number.isFinite(Number(value))) return '—'
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits })
}

function unpackResults(payload) {
  if (Array.isArray(payload)) return { results: payload }
  if (payload && typeof payload === 'object') return payload
  return EMPTY_RESULTS
}

function isAerPipelineResult(result) {
  return ['rqaoa', 'qiro'].includes(result.reduction_method)
    && Number.isFinite(Number(result.qaoa_call_count))
    && Number.isFinite(Number(result.aer_circuit_runs))
}

function StepCard({ icon: Icon, eyebrow, title, detail, accent = 'blue' }) {
  return (
    <div className={`research-step research-step-${accent}`}>
      <span className="research-step-icon"><Icon size={19} /></span>
      <span className="research-step-copy">
        <span className="research-eyebrow">{eyebrow}</span>
        <strong>{title}</strong>
        {detail && <span className="research-step-detail">{detail}</span>}
      </span>
    </div>
  )
}

function MetricCard({ label, value, detail, icon: Icon, accent = 'blue' }) {
  return (
    <article className={`research-metric research-metric-${accent}`}>
      <div className="research-metric-top">
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </article>
  )
}

function ChartPanel({
  title,
  subtitle,
  data,
  dataKey,
  color,
  valueSuffix = '',
  xAxisDataKey = 'iteration',
  xAxisLabel = 'Reduction iteration',
}) {
  const chartRef = useRef(null)
  const [chartWidth, setChartWidth] = useState(0)

  useEffect(() => {
    const element = chartRef.current
    if (!element) return undefined
    const observer = new ResizeObserver((entries) => {
      setChartWidth(Math.max(0, Math.floor(entries[0].contentRect.width)))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <article className="research-panel research-chart-panel">
      <div className="research-panel-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>
      {data.length ? (
        <div className="research-chart" ref={chartRef}>
          {chartWidth > 0 && (
            <LineChart width={chartWidth} height={220} data={data} margin={{ top: 12, right: 18, left: -12, bottom: 4 }}>
              <CartesianGrid stroke="rgba(148,163,184,.12)" strokeDasharray="3 5" />
              <XAxis
                dataKey={xAxisDataKey}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: 'rgba(148,163,184,.18)' }}
                label={{ value: xAxisLabel, position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 10 }}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={48}
                tickFormatter={(value) => `${formatNumber(value, 0)}${valueSuffix}`}
              />
              <Tooltip
                contentStyle={{
                  background: '#101b2d',
                  border: '1px solid rgba(148,163,184,.2)',
                  borderRadius: 10,
                  color: '#f8fafc',
                }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(value) => [`${formatNumber(value)}${valueSuffix}`, title]}
                labelFormatter={(value) => (
                  xAxisDataKey === 'iteration'
                    ? `Iteration ${value}`
                    : `${xAxisLabel}: ${value}`
                )}
              />
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2.5}
                dot={{ r: 3, fill: color, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          )}
        </div>
      ) : (
        <div className="research-chart-empty">
          Run the pipeline to populate this chart with experiment data.
        </div>
      )}
    </article>
  )
}

export default function ResearchPipeline() {
  const [dataset, setDataset] = useState(null)
  const [runData, setRunData] = useState(EMPTY_RESULTS)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [reductionMethod, setReductionMethod] = useState('rqaoa')
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
      const [datasetResponse, resultResponse] = await Promise.all([
        axios.get(`${API_BASE}/api/dataset_overview`),
        axios.get(`${API_BASE}/api/research/results`),
      ])
      return {
        dataset: datasetResponse.data,
        runData: unpackResults(resultResponse.data),
      }
  }, [])

  useEffect(() => {
    let active = true
    fetchData()
      .then(({ dataset: nextDataset, runData: nextRunData }) => {
        if (!active) return
        setDataset(nextDataset)
        setRunData(nextRunData)
        const savedMethod = nextRunData.results?.find(isAerPipelineResult)?.reduction_method
        if (savedMethod) setReductionMethod(savedMethod)
      })
      .catch((requestError) => {
        if (!active) return
        setError(
          requestError.response?.data?.error
            || 'Could not load research data. Check that the Flask backend is running.',
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [fetchData])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const { dataset: nextDataset, runData: nextRunData } = await fetchData()
      setDataset(nextDataset)
      setRunData(nextRunData)
      const savedMethod = nextRunData.results?.find(isAerPipelineResult)?.reduction_method
      if (savedMethod) setReductionMethod(savedMethod)
    } catch (requestError) {
      setError(
        requestError.response?.data?.error
          || 'Could not load research data. Check that the Flask backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  const runPipeline = async () => {
    setRunning(true)
    setError('')
    try {
      const response = await axios.post(`${API_BASE}/api/research/run`, {
        n_clusters: 4,
        target_variables: 20,
        reduction_method: reductionMethod,
        shots: 2048,
        run_hardware: false,
      })
      setRunData(unpackResults({ ...response.data, available: true }))
      await loadData()
    } catch (requestError) {
      setError(
        requestError.response?.data?.error
          || requestError.message
          || 'The research run failed.',
      )
    } finally {
      setRunning(false)
    }
  }

  const storedResults = Array.isArray(runData.results) ? runData.results : EMPTY_RESULTS.results
  const results = storedResults.filter(isAerPipelineResult)
  const hasAerRun = results.length > 0
  const reductionHistory = hasAerRun && Array.isArray(runData.reduction_history)
    ? runData.reduction_history.filter((entry) => (
      ['rqaoa', 'qiro'].includes(entry.algorithm)
      && entry.simulator_backend === 'aer_matrix_product_state'
      && Number.isFinite(Number(entry.correlation_value ?? entry.expectation_value))
    ))
    : EMPTY_RESULTS.reduction_history
  const experimentLog = hasAerRun && Array.isArray(runData.experiment_log)
    ? runData.experiment_log
    : EMPTY_RESULTS.experiment_log
  const qaoaHistory = hasAerRun && Array.isArray(runData.qaoa_history)
    ? runData.qaoa_history.filter((entry) => (
      ['rqaoa', 'qiro', 'warm_start_qaoa'].includes(entry.algorithm)
    ))
    : EMPTY_RESULTS.qaoa_history
  const clusterCustomers = hasAerRun && Array.isArray(runData.clusters)
    ? runData.clusters
    : EMPTY_RESULTS.results
  const clusterGroups = useMemo(() => {
    if (clusterCustomers.length || results.length) {
      const groups = new Map()
      clusterCustomers.forEach((customer) => {
        const id = customer.cluster_id
        if (!groups.has(id)) groups.set(id, [])
        groups.get(id).push(customer)
      })
      results.forEach((result) => {
        const id = result.cluster_id
        if (!groups.has(id)) {
          groups.set(id, (result.customer_ids || []).map((customer_id) => ({ customer_id })))
        }
      })
      return [...groups.entries()]
        .sort(([left], [right]) => Number(left) - Number(right))
        .map(([id, members]) => ({ id, members }))
    }
    return []
  }, [clusterCustomers, results])

  const primaryResult = useMemo(
    () => results.reduce((largest, result) => (
      Number(result.original_qubo_size ?? result.variable_count) >
        Number(largest?.original_qubo_size ?? largest?.variable_count ?? 0)
        ? result
        : largest
    ), null),
    [results],
  )
  const primaryReductionHistory = useMemo(
    () => reductionHistory.filter(
      (entry) => String(entry.cluster_id) === String(primaryResult?.cluster_id),
    ),
    [reductionHistory, primaryResult],
  )
  const primaryQaoaHistory = useMemo(
    () => qaoaHistory.filter(
      (entry) => String(entry.cluster_id) === String(primaryResult?.cluster_id)
        && entry.algorithm !== 'warm_start_qaoa',
    ),
    [qaoaHistory, primaryResult],
  )
  const latestCorrelationMatrix = primaryQaoaHistory.at(-1)
  const summary = useMemo(() => {
    const original = Number(
      primaryReductionHistory[0]?.variable_count
      ?? primaryResult?.original_qubo_size
      ?? primaryResult?.variable_count
      ?? 0,
    )
    const reduced = Number(
      primaryReductionHistory.at(-1)?.reduced_variable_count
      ?? primaryResult?.reduced_qubo_size
      ?? primaryResult?.reduced_variable_count
      ?? 0,
    )
    const clusterIds = new Set([
      ...clusterCustomers.map((customer) => String(customer.cluster_id)),
      ...results.map((result) => String(result.cluster_id)),
    ].filter((id) => id !== 'undefined' && id !== 'null'))
    const energy = Number(primaryResult?.solver?.energy)
    const eligible = results.length > 0 && results.every(
      (result) => result.hardware_eligible === true
        && Number(result.reduced_qubo_size ?? result.reduced_variable_count) <= 20,
    )
    const solverNames = [...new Set(results.map((item) => item.solver?.name).filter(Boolean))]
    const warehouseCount = Number(
      primaryResult?.warehouse_count ?? primaryResult?.candidate_warehouses?.length ?? 0,
    )
    const positionCount = Number(
      primaryResult?.position_count ?? primaryResult?.customer_ids?.length ?? 0,
    )
    return {
      clusters: clusterIds.size || clusterGroups.length,
      original,
      reduced,
      removed: Math.max(0, original - reduced),
      reduction: original ? (Math.max(0, original - reduced) / original) * 100 : 0,
      warehouseCount,
      positionCount,
      originalQuboSize: Number(primaryResult?.original_qubo_size ?? original),
      reducedQuboSize: Number(primaryResult?.reduced_qubo_size ?? reduced),
      energy: Number.isFinite(energy) ? energy : null,
      solver: solverNames.length === 1 ? solverNames[0] : solverNames.join(', '),
      eligible,
      qaoaCalls: qaoaHistory.filter(
        (entry) => String(entry.cluster_id) === String(primaryResult?.cluster_id),
      ).length || Number(primaryReductionHistory.at(-1)?.qaoa_call_count || 0),
      aerCircuitRuns: qaoaHistory
        .filter((entry) => String(entry.cluster_id) === String(primaryResult?.cluster_id))
        .reduce((count, entry) => count + Number(entry.circuit_runs || 0), 0)
        || Number(primaryReductionHistory.at(-1)?.aer_circuit_runs || 0),
      latestCorrelation: Number(
        primaryReductionHistory.at(-1)?.correlation_value
        ?? primaryReductionHistory.at(-1)?.expectation_value,
      ),
    }
  }, [primaryReductionHistory, primaryResult, clusterCustomers, results, clusterGroups, qaoaHistory])

  const reductionChart = useMemo(() => {
    const initialTotal = results.reduce((total, result) => total + (Number(result.variable_count) || 0), 0)
    const initialVariables = initialTotal || Math.max(
      ...reductionHistory.map((entry) => Number(entry.variable_count) || 0),
      0,
    )
    return reductionHistory.map((entry, index) => {
      const latestForCluster = reductionHistory
        .slice(0, index + 1)
        .filter((prior) => String(prior.cluster_id) === String(entry.cluster_id))
        .at(-1)
      const remainingForCluster = Number(latestForCluster?.reduced_variable_count)
      const remaining = results.length
        ? results.reduce((total, result) => {
            const clusterStep = reductionHistory
              .slice(0, index + 1)
              .filter((prior) => String(prior.cluster_id) === String(result.cluster_id))
              .at(-1)
            return total + (Number(clusterStep?.reduced_variable_count) || Number(result.variable_count) || 0)
          }, 0)
        : (remainingForCluster || initialVariables)
      const point = {
        iteration: index + 1,
        variables: remaining,
        removedPercent: initialVariables
          ? ((initialVariables - remaining) / initialVariables) * 100
          : 0,
        method: entry.solver_name,
      }
      return point
    })
  }, [reductionHistory, results])

  const energyChart = useMemo(() => {
    // These records are Warm Start QAOA best-feasible incumbent energies, distinct from reduction energies.
    const qaoaEntries = experimentLog.filter((entry) => (
      String(entry.solver_name || '').includes('warm_start_qaoa')
      && Number.isFinite(Number(entry.energy))
    ))
    return qaoaEntries.map((entry, index) => ({
      iteration: index + 1,
      energy: Number(entry.energy),
    }))
  }, [experimentLog])

  const reducedEnergyChart = useMemo(
    () => primaryReductionHistory
      .filter((entry) => (
        entry.reduced_qubo_energy != null
        && Number.isFinite(Number(entry.reduced_qubo_energy))
      ))
      .map((entry) => ({
        remainingVariables: Number(entry.variables_after ?? entry.remaining_variables),
        energy: Number(entry.reduced_qubo_energy),
      })),
    [primaryReductionHistory],
  )

  const bestResult = primaryResult
  const exampleCustomerCount = bestResult?.customer_ids?.length || 4
  const exampleVariables = summary.originalQuboSize || 32
  const latestReduction = primaryReductionHistory.at(-1)

  return (
    <main className="research-page fade-in">
      <section className="research-hero">
        <div className="research-hero-glow" />
        <div className="research-hero-content">
          <div className="research-kicker"><FlaskConical size={15} /> RESEARCH PROTOTYPE</div>
          <h1>Research <span>Pipeline</span></h1>
          <p>
            A clustered supply-chain optimization workflow: reduce each customer
            cluster to a target-sized QUBO, then run Warm Start QAOA locally.
          </p>
          <div className="research-hero-actions">
            <label className="research-method-picker">
              Reduction algorithm
              <select
                value={reductionMethod}
                onChange={(event) => setReductionMethod(event.target.value)}
                disabled={running || loading}
              >
                <option value="rqaoa">RQAOA</option>
                <option value="qiro">QIRO</option>
              </select>
            </label>
            <button className="research-run-button" type="button" onClick={runPipeline} disabled={running || loading}>
              {running ? <LoaderCircle className="research-spin" size={17} /> : <Play size={16} />}
              {running ? 'Running latest Aer experiment…' : 'Run Latest Research Experiment'}
            </button>
            <button className="research-refresh-button" type="button" onClick={loadData} disabled={loading || running}>
              <RefreshCw size={15} className={loading ? 'research-spin' : ''} />
              Refresh results
            </button>
            <span className="research-safe-label"><ShieldCheck size={14} /> IBM hardware execution is disabled</span>
          </div>
        </div>
        <div className="research-hero-mark" aria-hidden="true">
          <div className="research-orbit research-orbit-one" />
          <div className="research-orbit research-orbit-two" />
          <div className="research-orbit-core"><Cpu size={34} /></div>
        </div>
      </section>

      {error && (
        <div className="research-alert" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button>
        </div>
      )}

      {loading ? (
        <div className="research-loading"><LoaderCircle className="research-spin" size={22} /> Loading research data…</div>
      ) : (
        <>
          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">01</span>
              <div><h2>Project overview</h2><p>From customer locations to a reduced problem solved on a local simulator.</p></div>
            </div>
            <div className="research-flow">
              <StepCard icon={Database} eyebrow="INPUT" title="Customers" detail={`${dataset?.counts?.customers ?? '—'} loaded`} />
              <ArrowRight className="research-flow-arrow" />
              <StepCard icon={GitBranch} eyebrow="OUTER LAYER" title="Clustering" detail="Geographic KMeans" />
              <ArrowRight className="research-flow-arrow" />
              <StepCard icon={Layers3} eyebrow="INNER LAYER" title={reductionMethod.toUpperCase()} detail="Shot-estimated Z and ZZ correlations" accent="violet" />
              <ArrowRight className="research-flow-arrow" />
              <StepCard icon={Activity} eyebrow="SIMULATOR" title="Warm Start QAOA" detail="Feasibility checked" accent="cyan" />
              <ArrowRight className="research-flow-arrow" />
              <StepCard icon={Cpu} eyebrow="RECONSTRUCTION" title="Original Assignment" detail="32-bit solution restored" accent="green" />
            </div>
            <div className="research-note">
              <CircleAlert size={15} />
              <span>Reduction decisions use QAOA measurement expectations sampled on Aer; IBM hardware is disabled.</span>
            </div>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">02</span>
              <div><h2>Outer layer · customer clustering</h2><p>Cluster customers geographically before constructing route decision variables.</p></div>
            </div>
            <div className="research-outer-grid">
              <article className="research-panel research-clustering-panel">
                <div className="research-mini-flow">
                  <div className="research-mini-node"><strong>{dataset?.counts?.customers ?? '—'}</strong><span>Loaded customers</span></div>
                  <ArrowDown size={17} />
                  <div className="research-mini-node research-mini-kmeans"><strong>KMeans</strong><span>Geographic features</span></div>
                  <ArrowDown size={17} />
                  <div className="research-mini-node research-mini-clusters">                  <strong>{clusterGroups.length || 4}</strong><span>{clusterGroups.length ? 'Customer clusters' : 'Target clusters'}</span></div>
                </div>
                <div className="research-cluster-cards">
                  {(clusterGroups.length ? clusterGroups : [0, 1, 2, 3].map((id) => ({ id, members: [] }))).map((cluster) => (
                    <div className="research-cluster-card" key={cluster.id}>
                      <span>Cluster {Number(cluster.id) + 1}</span>
                      <strong>{cluster.members.length || '—'}</strong>
                      <small>{cluster.members.length === 1 ? 'customer' : 'customers'}</small>
                      {cluster.members.length > 0 && (
                        <small className="research-customer-list">
                          {cluster.members.map((customer) => customer.customer_id).join(' · ')}
                        </small>
                      )}
                    </div>
                  ))}
                </div>
              </article>
              <div className="research-side-metrics">
                <MetricCard label="Cluster count" value={summary.clusters || '4 target'} detail="KMeans target: 4" icon={GitBranch} />
                <MetricCard label="Customer count" value={dataset?.counts?.customers ?? '—'} detail="Loaded from dataset API" icon={Database} accent="cyan" />
                <MetricCard
                  label="Cluster sizes"
                  value={clusterGroups.filter((group) => group.id !== '—').length
                    ? clusterGroups.map((group) => group.members.length).join(' / ')
                    : 'Waiting for run'}
                  detail="Customers per cluster"
                  icon={Layers3}
                  accent="violet"
                />
              </div>
            </div>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">03</span>
              <div><h2>Position-encoded QUBO</h2><p>Each customer occupies exactly one route position for one candidate warehouse.</p></div>
            </div>
            <div className="research-qubo-grid">
              <article className="research-panel research-encoding-panel">
                <div className="research-encoding-facts">
                  <div><Warehouse size={17} /><strong>2</strong><span>Candidate warehouses</span></div>
                  <div><Database size={17} /><strong>{bestResult ? exampleCustomerCount : 4}</strong><span>Customers / example cluster</span></div>
                  <div><Activity size={17} /><strong>{bestResult ? exampleCustomerCount : 4}</strong><span>Route positions</span></div>
                </div>
                <div className="research-equation">
                  <span className="research-eyebrow">BINARY DECISION VARIABLE</span>
                  <code>z(warehouse, customer, position)</code>
                  <div className="research-equation-calc">
                    <span>2 × {bestResult ? exampleCustomerCount : 4} × {bestResult ? exampleCustomerCount : 4}</span>
                    <ArrowRight size={19} />
                    <strong>{exampleVariables} variables</strong>
                  </div>
                </div>
              </article>
              <article className="research-panel research-variable-panel">
                <span className="research-eyebrow">REFERENCE FORMULATION</span>
                <strong className="research-big-number">{summary.originalQuboSize || 32}</strong>
                <span>Original variables</span>
                <small>{bestResult ? 'Measured from current experiment' : '2 warehouses × 4 customers × 4 positions'}</small>
              </article>
            </div>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">04</span>
              <div><h2>Quantum reduction pipeline</h2><p>Each elimination is selected from shot-estimated QAOA spin expectations.</p></div>
            </div>
            <article className="research-panel research-reduction-panel">
              <div className="research-reduction-flow">
                <div className="research-reduction-node"><strong>{summary.originalQuboSize || 32}</strong><span>Original variables</span></div>
                <ArrowRight />
                <div className="research-reduction-node research-reduction-step"><strong>{reductionMethod.toUpperCase()}</strong><span>{reductionMethod === 'rqaoa' ? 'Largest |<ZiZj>| relation' : 'Spin bias / pair inference'}</span></div>
                <ArrowRight />
                <div className="research-reduction-node research-reduction-final"><strong>{summary.reducedQuboSize || '≤20'}</strong><span>Reduced variables</span></div>
              </div>
              <div className="research-reduction-summary">
                <div><span>Reduction percentage</span><strong>{summary.original ? `${formatNumber(summary.reduction)}%` : '—'}</strong></div>
                <div><span>Variables removed</span><strong>{summary.original ? summary.original - summary.reduced : '—'}</strong></div>
                <div><span>Reduction iterations</span><strong>{primaryReductionHistory.length || '—'}</strong></div>
                <div><span>QAOA calls</span><strong>{summary.qaoaCalls || '—'}</strong></div>
                <div><span>Aer circuit runs</span><strong>{summary.aerCircuitRuns || '—'}</strong></div>
                <div><span>Latest relation</span><strong>{latestReduction?.relation || '—'}</strong></div>
                <div><span>Latest correlation value</span><strong>{Number.isFinite(summary.latestCorrelation) ? formatNumber(summary.latestCorrelation, 4) : '—'}</strong></div>
              </div>
              <div className="research-table-wrap">
                <table className="research-history-table">
                  <thead><tr><th>Step</th><th>Cluster</th><th>Variables Before</th><th>Correlation &lt;ZiZj&gt; / &lt;Zi&gt;</th><th>Removed</th><th>Relation</th><th>Variables After</th><th>Reduced QUBO Energy</th><th>QAOA Calls</th><th>Aer Circuit Runs</th></tr></thead>
                  <tbody>
                    {reductionHistory.length ? reductionHistory.map((entry, index) => (
                      <tr key={`${entry.cluster_id}-${index}`}>
                        <td>{entry.iteration ?? index + 1}</td>
                        <td>{Number(entry.cluster_id) + 1}</td>
                        <td>{entry.variables_before ?? entry.variable_count ?? '—'}</td>
                        <td>{formatNumber(entry.correlation_value ?? entry.expectation_value, 4)}</td>
                        <td>{entry.removed_variable ?? entry.eliminated_variable ?? entry.fixed_variables?.[0]?.variable ?? '—'}</td>
                        <td>{entry.relation || '—'}</td>
                        <td>{entry.variables_after ?? entry.remaining_variables ?? entry.reduced_variable_count ?? '—'}</td>
                        <td>{entry.reduced_qubo_energy == null ? '—' : formatNumber(entry.reduced_qubo_energy)}</td>
                        <td>{entry.qaoa_call_count ?? '—'}</td>
                        <td>{entry.aer_circuit_runs ?? '—'}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan="10" className="research-empty-row">Run the latest research experiment to load Aer reduction measurements.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {latestCorrelationMatrix?.correlation_matrix && (
                <details className="research-correlation-details">
                  <summary>
                    Measured correlation matrix · iteration {latestCorrelationMatrix.iteration}
                    {' '}· {latestCorrelationMatrix.shots} Aer shots
                  </summary>
                  <div className="research-table-wrap research-correlation-wrap">
                    <table className="research-correlation-table">
                      <thead>
                        <tr>
                          <th>&lt;ZiZj&gt;</th>
                          {latestCorrelationMatrix.variable_ids.map((id) => <th key={id}>{id}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {latestCorrelationMatrix.correlation_matrix.map((row, rowIndex) => (
                          <tr key={latestCorrelationMatrix.variable_ids[rowIndex]}>
                            <th>{latestCorrelationMatrix.variable_ids[rowIndex]}</th>
                            {row.map((value, columnIndex) => (
                              <td key={`${rowIndex}-${columnIndex}`}>{formatNumber(value, 3)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}
              {bestResult?.reduced_qubo && (
                <details className="research-reduced-qubo-details">
                  <summary>Final reduced QUBO · {bestResult.reduced_qubo_size} × {bestResult.reduced_qubo_size}</summary>
                  <pre>{JSON.stringify(bestResult.reduced_qubo, null, 2)}</pre>
                </details>
              )}
            </article>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">05</span>
              <div><h2>Inner layer · Warm Start QAOA</h2><p>Warm Start QAOA runs only after the measured reduction reaches the target variable count.</p></div>
            </div>
            <div className="research-inner-grid">
              {[
                ['Reduced QUBO', bestResult ? `${summary.reducedQuboSize} active variables` : '≤20 active variables'],
                ['Warm Start QAOA', bestResult?.solver?.name || 'Awaiting simulator run'],
                ['Bitstring', bestResult?.result?.bitstring
                  ? `${bestResult.result.bitstring.slice(0, 18)}${bestResult.result.bitstring.length > 18 ? '…' : ''}`
                  : 'Awaiting feasible sample'],
                ['Energy', bestResult ? formatNumber(bestResult.solver?.energy) : '—'],
                ['Decoded assignment', bestResult?.result?.feasible ? `${bestResult.result.warehouse_id} · ${bestResult.result.route.join(' → ')}` : 'Awaiting solution'],
              ].map(([title, detail], index) => (
                <div className="research-inner-step" key={title}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <strong>{title}</strong>
                  <small title={title === 'Bitstring' ? bestResult?.result?.bitstring : undefined}>{detail}</small>
                  {index < 4 && <ArrowRight className="research-inner-arrow" size={16} />}
                </div>
              ))}
            </div>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">06</span>
              <div><h2>Local simulator status</h2><p>The full workflow is run locally; IBM Quantum hardware is not used.</p></div>
            </div>
            <article className={`research-hardware-panel ${summary.eligible ? 'is-eligible' : ''}`}>
              <div className="research-hardware-icon"><Cpu size={23} /></div>
              <div className="research-hardware-main">
                <span className="research-eyebrow">AER SIMULATOR WORKFLOW</span>
                <h3>{summary.eligible ? 'Warm Start QAOA completed locally' : 'Waiting for a reconstructed assignment'}</h3>
                <p>{summary.eligible
                  ? 'Every cluster is at or below the target variable count and produced a feasible reconstructed solution.'
                  : 'Run the local reduction and Warm Start QAOA workflow to generate a feasible reconstructed solution.'}</p>
              </div>
              <div className="research-hardware-checks">
                <div><span>Original QUBO size</span><strong>{summary.originalQuboSize || '—'}</strong></div>
                <div><span>Reduced QUBO size</span><strong>{summary.reducedQuboSize || '—'}</strong></div>
                <div><span>Reduced size ≤ 20?</span><strong>{summary.reducedQuboSize ? (summary.reducedQuboSize <= 20 ? 'YES' : 'NO') : '—'}</strong></div>
                <div><span>IBM hardware</span><strong>DISABLED</strong></div>
              </div>
            </article>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">07</span>
              <div><h2>Experiment results</h2><p>Live metrics from the latest saved research run.</p></div>
            </div>
            <div className="research-results-grid">
              <MetricCard label="Cluster count" value={summary.clusters || '—'} detail="Clusters in this run" icon={GitBranch} />
              <MetricCard label="Original variable count" value={summary.original || '—'} detail="Selected cluster · reduction history" icon={Layers3} accent="violet" />
              <MetricCard label="Reduced variable count" value={summary.reduced || '—'} detail="Final remaining variables" icon={Activity} accent="cyan" />
              <MetricCard label="Variables removed" value={summary.original ? summary.removed : '—'} detail="Original minus reduced" icon={ArrowDown} accent="green" />
              <MetricCard label="Reduction percentage" value={summary.original ? `${formatNumber(summary.reduction)}%` : '—'} detail="Variables removed / original" icon={ArrowDown} accent="green" />
              <MetricCard label="Warehouse count" value={summary.warehouseCount || '—'} detail="Candidate warehouses in selected QUBO" icon={Warehouse} />
              <MetricCard label="Position count" value={summary.positionCount || '—'} detail="Route positions in selected cluster" icon={Activity} accent="cyan" />
              <MetricCard label="Original QUBO size" value={summary.originalQuboSize || '—'} detail="Before reduction" icon={Layers3} accent="violet" />
              <MetricCard label="Reduced QUBO size" value={summary.reducedQuboSize || '—'} detail="After reduction" icon={Layers3} accent="cyan" />
              <MetricCard label="QAOA energy" value={summary.energy === null ? '—' : formatNumber(summary.energy)} icon={Cpu} accent="violet" />
              <MetricCard label="Best solver" value={summary.solver || '—'} icon={FlaskConical} accent="cyan" />
              <MetricCard label="QAOA calls" value={summary.qaoaCalls || '—'} detail="Reduction + warm-start calls" icon={Cpu} accent="green" />
            </div>
          </section>

          <section className="research-section">
            <div className="research-section-title">
              <span className="research-section-index">08</span>
              <div><h2>Reduction & energy charts</h2><p>Iteration-by-iteration metrics from the recorded experiment history.</p></div>
            </div>
            <div className="research-charts-grid">
              <ChartPanel
                title="Variable count vs iteration"
                subtitle="Active variables after each logged elimination"
                data={reductionChart}
                dataKey="variables"
                color="#38bdf8"
              />
              <ChartPanel
                title="Energy vs QAOA iteration"
                subtitle="Recorded feasible incumbent energy across feedback rounds"
                data={energyChart}
                dataKey="energy"
                color="#a78bfa"
                xAxisLabel="QAOA feedback iteration"
              />
              <ChartPanel
                title="Reduction percentage"
                subtitle="Share of original variables eliminated"
                data={reductionChart}
                dataKey="removedPercent"
                color="#34d399"
                valueSuffix="%"
              />
              <ChartPanel
                title="Energy Preservation During Reduction"
                subtitle="Reduced QUBO energy at the projected original seed"
                data={reducedEnergyChart}
                dataKey="energy"
                color="#fbbf24"
                xAxisDataKey="remainingVariables"
                xAxisLabel="Remaining Variables"
              />
            </div>
          </section>

          <section className="research-section research-architecture-section">
            <div className="research-section-title">
              <span className="research-section-index">09</span>
              <div><h2>End-to-end architecture</h2><p>Separate responsibilities across the Outer Layer and Inner Layer.</p></div>
            </div>
            <div className="research-architecture">
              <div className="research-architecture-layer outer">
                <div className="research-layer-heading"><span>OUTER LAYER</span><small>Problem shaping & orchestration</small></div>
                <div className="research-architecture-flow">
                  {['Customers', 'KMeans', 'Clusters', 'Distance Matrix', 'Position QUBO'].map((label, index) => (
                    <div className="research-architecture-node" key={label}>
                      <span>{String(index + 1).padStart(2, '0')}</span><strong>{label}</strong>
                      {index < 4 && <ArrowRight size={16} />}
                    </div>
                  ))}
                </div>
              </div>
              <div className="research-layer-bridge"><ArrowDown size={17} /><span>Reduced problem passed to solver layer</span><ArrowDown size={17} /></div>
              <div className="research-architecture-layer inner">
                <div className="research-layer-heading"><span>INNER LAYER</span><small>Measured reduction and local optimization</small></div>
                <div className="research-architecture-flow">
                  {[`${reductionMethod.toUpperCase()} via Aer`, '≤20 Variable QUBO', 'Warm Start QAOA', 'Original Bitstring', 'Warehouse + Route'].map((label, index) => (
                    <div className="research-architecture-node" key={label}>
                      <span>{String(index + 1).padStart(2, '0')}</span><strong>{label}</strong>
                      {index < 4 && <ArrowRight size={16} />}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
          <footer className="research-footer">
            <span>{hasAerRun ? 'Latest Aer run loaded' : 'Run the latest experiment to load Aer results'}</span>
            <span>{experimentLog.length ? `${experimentLog.length} experiment records` : 'No saved run yet'}</span>
          </footer>
        </>
      )}
    </main>
  )
}
