import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import CommunityList from './CommunityList'

/* ─── helpers ───────────────────────────── */
const riskClass = (s) => `risk-${s}` || 'risk-stable'
const riskLabel = { stable: 'Stable', monitor: 'Monitor', needs_review: 'Needs Review', high_risk: 'High Risk' }
const moodEmoji = { 1: '😔', 2: '😕', 3: '😐', 4: '🙂', 5: '😊' }
const appetiteIcon = { good: '✅', fair: '⚠️', poor: '❌' }

function RiskBadge({ status }) {
    return <span className={`risk-badge ${riskClass(status || 'stable')}`}>⬤ {riskLabel[status] || 'Stable'}</span>
}

function StatCard({ label, value, sub, icon }) {
    return (
        <div className="stat-card animate-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span className="stat-label">{label}</span>
                {icon && <span style={{ fontSize: 22 }}>{icon}</span>}
            </div>
            <div className="stat-value">{value ?? '—'}</div>
            {sub && <div className="stat-sub">{sub}</div>}
        </div>
    )
}

/* ─── Sidebar items ─────────────────────── */
const TABS = [
    { id: 'overview', icon: '📊', label: 'Overview' },
    { id: 'log', icon: '📝', label: 'Daily Log' },
    { id: 'history', icon: '📅', label: 'Log History' },
    { id: 'guidance', icon: '🧭', label: 'Recovery Guidance' },
    { id: 'chat', icon: '🤖', label: 'AI Assistant' },
    { id: 'community', icon: '💬', label: 'Community' },
]

export default function PatientDashboard() {
    const [tab, setTab] = useState('overview')
    const [guidance, setGuidance] = useState(null)
    const [logs, setLogs] = useState([])
    const [loading, setLoading] = useState(true)

    // Daily log form
    const [logForm, setLogForm] = useState({
        pain_level: 3, mood_level: 3, sleep_hours: 7, appetite: 'good',
        swelling: false, body_part: '', note_text: '', date: new Date().toISOString().split('T')[0]
    })
    const [logResult, setLogResult] = useState(null)
    const [logLoading, setLogLoading] = useState(false)

    // Chat
    const [question, setQuestion] = useState('')
    const [chat, setChat] = useState([])
    const [isAsking, setIsAsking] = useState(false)
    const chatEndRef = useRef(null)

    useEffect(() => { loadAll() }, [])
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chat])

    const loadAll = async () => {
        setLoading(true)
        try {
            const [g, l] = await Promise.all([
                api.getGuidance().catch(() => null),
                api.getLogs().catch(() => ({ logs: [] }))
            ])
            setGuidance(g && Object.keys(g).length > 0 ? g : null)
            setLogs(l?.logs || [])
        } catch {
            setGuidance(null)
            setLogs([])
        } finally { setLoading(false) }
    }

    const handleLogSubmit = async (e) => {
        e.preventDefault()
        setLogLoading(true); setLogResult(null)
        try {
            const res = await api.createLog({ ...logForm, pain_level: Number(logForm.pain_level), mood_level: Number(logForm.mood_level), sleep_hours: Number(logForm.sleep_hours) })
            setLogResult({ success: true, ...res })
            loadAll()
        } catch (err) {
            setLogResult({ success: false, msg: err.message })
        } finally { setLogLoading(false) }
    }

    const handleAsk = async (e) => {
        e.preventDefault()
        if (!question.trim()) return
        const q = question; setQuestion(''); setIsAsking(true)
        setChat(c => [...c, { type: 'user', text: q }])
        try {
            const res = await api.askRAG(q)
            setChat(c => [...c, { type: 'ai', text: res.answer, alert: res.alert_flag, source: res.source }])
        } catch (err) {
            setChat(c => [...c, { type: 'ai', text: 'Sorry, I could not reach the AI assistant. Check that the backend is running.', alert: true }])
        } finally { setIsAsking(false) }
    }

    const latestLog = logs[0]

    return (
        <div className="dashboard-layout">
            {/* ── Sidebar ── */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <h2>RECOVER.AI</h2>
                    <p>Patient Portal</p>
                </div>
                <div className="sidebar-section">Navigation</div>
                {TABS.map(t => (
                    <button key={t.id} className={`nav-item ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
                        <span className="nav-icon">{t.icon}</span>{t.label}
                    </button>
                ))}
                <div style={{ flex: 1 }} />
                <div style={{ borderTop: '1px solid rgba(255,255,255,.1)', paddingTop: 12, marginTop: 12 }}>
                    <div style={{ padding: '8px 12px', fontSize: 13 }}>
                        <p style={{ color: 'rgba(255,255,255,.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em' }}>Signed in as</p>
                        <p style={{ color: '#fff', fontWeight: 600, marginTop: 2 }}>{localStorage.getItem('name') || 'Patient'}</p>
                    </div>
                    <button className="nav-item" style={{ color: 'rgba(255,255,255,.5)' }}
                        onClick={() => { localStorage.clear(); window.location.href = '/login' }}>
                        <span className="nav-icon">🚪</span>Log Out
                    </button>
                </div>
            </aside>

            {/* ── Main ── */}
            <main className="main-content">
                {loading && <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-faint)' }}>Loading your data…</div>}

                {/* ═══ OVERVIEW ═══ */}
                {!loading && tab === 'overview' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>Good evening, {localStorage.getItem('name')?.split(' ')[0] || 'there'} 👋</h1>
                                <p className="page-header-sub">Here's your recovery snapshot</p>
                            </div>
                            {guidance && <RiskBadge status={guidance.current_risk_status} />}
                        </div>

                        {/* Stats */}
                        <div className="grid-4 mb-6">
                            <StatCard label="Risk Status" value={riskLabel[guidance?.current_risk_status] || 'Stable'} sub="Current assessment" icon="🛡️" />
                            <StatCard label="Risk Score" value={guidance?.risk_score != null ? `${guidance.risk_score}` : '—'} sub="Out of 100" icon="📈" />
                            <StatCard label="Recovery Stage" value={guidance?.stage || '—'} sub={`Day ${guidance?.days_since_start ?? '?'}`} icon="🗓️" />
                            <StatCard label="Total Logs" value={logs.length} sub="Entries submitted" icon="📝" />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
                            {/* Latest log */}
                            <div className="card animate-in-2">
                                <h3 className="mb-4">Latest Log Entry</h3>
                                {latestLog ? (
                                    <div>
                                        <div className="flex justify-between items-center mb-4">
                                            <span style={{ fontWeight: 700, fontSize: 20 }}>{latestLog.date}</span>
                                            <RiskBadge status={latestLog.risk_status} />
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 16 }}>
                                            {[
                                                { label: 'Pain Level', value: `${latestLog.pain_level}/10` },
                                                { label: 'Mood', value: `${moodEmoji[latestLog.mood_level] || ''} ${latestLog.mood_level}/5` },
                                                { label: 'Sleep', value: `${latestLog.sleep_hours}h` },
                                                { label: 'Appetite', value: `${appetiteIcon[latestLog.appetite] || ''} ${latestLog.appetite}` },
                                                { label: 'Body Part', value: latestLog.body_part || '—' },
                                                { label: 'Swelling', value: latestLog.swelling ? '⚠️ Yes' : '✅ No' },
                                            ].map(({ label, value }) => (
                                                <div key={label} style={{ background: 'var(--bg)', padding: '12px 14px', borderRadius: 10 }}>
                                                    <p style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-faint)', marginBottom: 4 }}>{label}</p>
                                                    <p style={{ fontWeight: 600, color: 'var(--text)' }}>{value}</p>
                                                </div>
                                            ))}
                                        </div>
                                        {latestLog.note_text && (
                                            <div style={{ background: 'var(--bg)', padding: '12px 16px', borderRadius: 10, borderLeft: '4px solid var(--primary)' }}>
                                                <p style={{ fontSize: 13, fontStyle: 'italic', color: 'var(--text-muted)' }}>"{latestLog.note_text}"</p>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="empty-state">
                                        <span>📋</span>
                                        <p>No logs yet. Submit your first daily log to begin tracking.</p>
                                        <button className="btn btn-primary mt-4" onClick={() => setTab('log')}>Submit First Log →</button>
                                    </div>
                                )}
                            </div>

                            {/* Warning Signs */}
                            <div className="flex flex-col gap-4">
                                <div className="card animate-in-2" style={{ background: 'var(--primary-dark)', border: 'none' }}>
                                    <h3 style={{ color: '#fff', marginBottom: 12 }}>⚠️ Warning Signs</h3>
                                    <p style={{ color: 'rgba(255,255,255,.6)', fontSize: 13, marginBottom: 16 }}>Contact your doctor immediately if you experience:</p>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {(guidance?.warning_signs || ['Severe pain (8+)', 'Infection signs', 'Excessive swelling']).map((s, i) => (
                                            <div key={i} style={{ background: 'rgba(255,255,255,.1)', padding: '8px 14px', borderRadius: 8, fontSize: 13, color: 'rgba(255,255,255,.85)', display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <span style={{ fontSize: 10 }}>🔴</span>{s}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="card animate-in-3">
                                    <h4 className="mb-4">Acceptable Pain Range</h4>
                                    <p style={{ fontSize: 28, fontWeight: 800, color: 'var(--primary)' }}>{guidance?.acceptable_pain_range || '0-5'}</p>
                                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>For {guidance?.stage || 'current stage'}</p>
                                    <div className="progress-track mt-4">
                                        <div className="progress-fill" style={{ width: `${(guidance?.risk_score || 0)}%` }} />
                                    </div>
                                    <p className="tooltip-hint mt-4">Risk score: {guidance?.risk_score || 0}/100</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ═══ DAILY LOG ═══ */}
                {!loading && tab === 'log' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>📝 Daily Log</h1>
                                <p className="page-header-sub">Track your recovery metrics — submitted logs are analysed by the risk engine in real-time</p>
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
                            <div className="card animate-in">
                                <form onSubmit={handleLogSubmit}>
                                    <div className="grid-2 mb-4">
                                        <div>
                                            <label>Log Date</label>
                                            <input type="date" value={logForm.date} onChange={e => setLogForm(f => ({ ...f, date: e.target.value }))} />
                                        </div>
                                        <div>
                                            <label>Body Part</label>
                                            <input placeholder="e.g. Knee, Shoulder, Hip" value={logForm.body_part} onChange={e => setLogForm(f => ({ ...f, body_part: e.target.value }))} />
                                        </div>
                                    </div>

                                    <div className="mb-4">
                                        <label>Pain Level — <strong style={{ color: logForm.pain_level >= 8 ? 'var(--risk-high)' : logForm.pain_level >= 5 ? 'var(--risk-monitor)' : 'var(--risk-stable)' }}>{logForm.pain_level}/10</strong></label>
                                        <input type="range" min="0" max="10" value={logForm.pain_level} onChange={e => setLogForm(f => ({ ...f, pain_level: e.target.value }))} />
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-faint)', marginTop: 4 }}>
                                            <span>No pain</span><span>Moderate</span><span>Severe</span>
                                        </div>
                                    </div>

                                    <div className="mb-4">
                                        <label>Mood Level — <strong>{moodEmoji[logForm.mood_level]} {logForm.mood_level}/5</strong></label>
                                        <input type="range" min="1" max="5" value={logForm.mood_level} onChange={e => setLogForm(f => ({ ...f, mood_level: e.target.value }))} />
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-faint)', marginTop: 4 }}>
                                            <span>Distressed</span><span>Neutral</span><span>Great</span>
                                        </div>
                                    </div>

                                    <div className="grid-2 mb-4">
                                        <div>
                                            <label>Sleep Hours</label>
                                            <input type="number" min="0" max="24" step="0.5" value={logForm.sleep_hours} onChange={e => setLogForm(f => ({ ...f, sleep_hours: e.target.value }))} />
                                        </div>
                                        <div>
                                            <label>Appetite</label>
                                            <select value={logForm.appetite} onChange={e => setLogForm(f => ({ ...f, appetite: e.target.value }))}>
                                                <option value="good">✅ Good</option>
                                                <option value="fair">⚠️ Fair</option>
                                                <option value="poor">❌ Poor</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="mb-4">
                                        <label>Swelling Present?</label>
                                        <div style={{ display: 'flex', gap: 12 }}>
                                            {[{ v: false, label: 'No swelling', icon: '✅' }, { v: true, label: 'Swelling present', icon: '⚠️' }].map(({ v, label, icon }) => (
                                                <button type="button" key={String(v)} onClick={() => setLogForm(f => ({ ...f, swelling: v }))}
                                                    style={{
                                                        flex: 1, padding: '12px', borderRadius: 10, border: `2px solid ${logForm.swelling === v ? (v ? 'var(--accent-dark)' : 'var(--primary)') : 'var(--border)'}`,
                                                        background: logForm.swelling === v ? (v ? 'var(--risk-review-bg)' : 'var(--risk-stable-bg)') : 'transparent',
                                                        fontWeight: 600, fontSize: 13, cursor: 'pointer'
                                                    }}>
                                                    {icon} {label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="mb-4">
                                        <label>Notes / Observations</label>
                                        <textarea placeholder="Describe how you feel today, any specific sensations, activities done, concerns…" value={logForm.note_text} onChange={e => setLogForm(f => ({ ...f, note_text: e.target.value }))} />
                                    </div>

                                    <button type="submit" className="btn btn-primary w-full" disabled={logLoading} style={{ padding: 14 }}>
                                        {logLoading ? <span className="animate-pulse">Submitting & Analysing…</span> : '📤 Submit Daily Report'}
                                    </button>
                                </form>
                            </div>

                            <div className="flex flex-col gap-4">
                                {logResult && (
                                    <div className={`card animate-in`} style={{ background: logResult.success ? 'var(--risk-stable-bg)' : 'var(--risk-high-bg)', border: `1px solid ${logResult.success ? 'var(--risk-stable)' : 'var(--risk-high)'}` }}>
                                        <h3 style={{ color: logResult.success ? 'var(--risk-stable)' : 'var(--risk-high)', marginBottom: 12 }}>
                                            {logResult.success ? '✅ Log Submitted' : '❌ Error'}
                                        </h3>
                                        {logResult.success ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                                <p style={{ fontSize: 13, color: 'var(--risk-stable)', fontWeight: 600 }}>Saved to database. Your doctor will see this entry on their dashboard.</p>
                                                <div><p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase' }}>Risk Status</p><RiskBadge status={logResult.risk_status} /></div>
                                                <div><p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase' }}>Risk Score</p><p style={{ fontWeight: 700, fontSize: 22 }}>{logResult.risk_score}</p></div>
                                                <div><p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase' }}>Deviation Flag</p><p style={{ fontWeight: 700 }}>{logResult.deviation_flag ? '⚠️ Yes' : '✅ No'}</p></div>
                                                <div><p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase' }}>Complication Index</p><p style={{ fontWeight: 700 }}>{logResult.complication_index}%</p></div>
                                            </div>
                                        ) : (
                                            <p style={{ fontSize: 13 }}>{logResult.msg}</p>
                                        )}
                                    </div>
                                )}

                                <div className="card animate-in-2">
                                    <h4 className="mb-4">Risk Engine Logic</h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                        {[
                                            { condition: 'Pain ≥ 8', result: 'needs_review', color: 'var(--risk-review)' },
                                            { condition: 'Swelling + Pain ≥ 7', result: 'high_risk', color: 'var(--risk-high)' },
                                            { condition: 'Pain rising 3 days', result: 'monitor', color: 'var(--risk-monitor)' },
                                            { condition: 'Deviation from range', result: 'deviation_flag', color: 'var(--accent-dark)' },
                                        ].map(({ condition, result, color }) => (
                                            <div key={condition} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bg)', borderRadius: 8, fontSize: 13 }}>
                                                <span style={{ color: 'var(--text-muted)' }}>{condition}</span>
                                                <span style={{ fontWeight: 700, color, fontSize: 11, textTransform: 'uppercase' }}>{result}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* ═══ HISTORY ═══ */}
                {!loading && tab === 'history' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>📅 Log History</h1>
                                <p className="page-header-sub">{logs.length} total entries</p>
                            </div>
                        </div>
                        {logs.length === 0 ? (
                            <div className="card empty-state"><span>📋</span><p>No logs yet.</p></div>
                        ) : (
                            <div className="card animate-in">
                                <div className="table-wrap">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Date</th><th>Pain</th><th>Mood</th><th>Sleep</th><th>Appetite</th><th>Swelling</th><th>Body Part</th><th>Risk</th><th>Notes</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {logs.map((log, i) => (
                                                <tr key={i}>
                                                    <td style={{ fontWeight: 600 }}>{log.date}</td>
                                                    <td>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                            <div style={{ width: 36, height: 6, background: 'var(--bg-2)', borderRadius: 99, overflow: 'hidden' }}>
                                                                <div style={{ width: `${log.pain_level * 10}%`, height: '100%', background: log.pain_level >= 8 ? 'var(--risk-high)' : log.pain_level >= 5 ? 'var(--accent-dark)' : 'var(--primary)', borderRadius: 99 }} />
                                                            </div>
                                                            <span style={{ fontWeight: 600 }}>{log.pain_level}/10</span>
                                                        </div>
                                                    </td>
                                                    <td>{moodEmoji[log.mood_level]} {log.mood_level}/5</td>
                                                    <td>{log.sleep_hours}h</td>
                                                    <td>{appetiteIcon[log.appetite]} {log.appetite}</td>
                                                    <td>{log.swelling ? <span className="chip chip-amber">⚠️ Yes</span> : <span className="chip chip-green">No</span>}</td>
                                                    <td>{log.body_part || <span style={{ color: 'var(--text-faint)' }}>—</span>}</td>
                                                    <td><RiskBadge status={log.risk_status} /></td>
                                                    <td style={{ maxWidth: 200, fontSize: 13, color: 'var(--text-muted)' }}>{log.note_text || <span style={{ color: 'var(--text-faint)' }}>—</span>}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ═══ COMMUNITY ═══ */}
                {!loading && tab === 'community' && (
                    <CommunityList />
                )}

                {/* ═══ GUIDANCE ═══ */}
                {!loading && tab === 'guidance' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>🧭 Recovery Guidance</h1>
                                <p className="page-header-sub">Stage-based adaptive recommendations tailored to your recovery progress</p>
                            </div>
                            {guidance && <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--primary)' }}>Day {guidance.days_since_start}</span>}
                        </div>

                        {guidance ? (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                                <div className="flex flex-col gap-4">
                                    <div className="card animate-in" style={{ border: '2px solid var(--primary)' }}>
                                        <h4 className="mb-2">Current Stage</h4>
                                        <h2 style={{ fontSize: 32, marginBottom: 8 }}>{guidance.stage}</h2>
                                        <p style={{ marginBottom: 16 }}><strong>Focus:</strong> {guidance.focus}</p>
                                        <div style={{ display: 'flex', gap: 12 }}>
                                            <div style={{ flex: 1, background: 'var(--bg)', padding: '12px', borderRadius: 10 }}>
                                                <p style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-faint)' }}>Acceptable Pain</p>
                                                <p style={{ fontWeight: 800, fontSize: 22, color: 'var(--primary)' }}>{guidance.acceptable_pain_range}</p>
                                            </div>
                                            <div style={{ flex: 1, background: 'var(--bg)', padding: '12px', borderRadius: 10 }}>
                                                <p style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-faint)' }}>Risk Score</p>
                                                <p style={{ fontWeight: 800, fontSize: 22, color: 'var(--primary)' }}>{guidance.risk_score ?? '—'}</p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="card animate-in-2">
                                        <h3 className="mb-4">✅ Recommendations</h3>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                            {guidance.recommendations?.map((r, i) => (
                                                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 14px', background: 'var(--bg)', borderRadius: 10 }}>
                                                    <span style={{ fontSize: 16, marginTop: 1 }}>✔️</span>
                                                    <p style={{ fontSize: 14, color: 'var(--text)' }}>{r}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-4">
                                    <div className="card animate-in" style={{ background: 'var(--primary-dark)', border: 'none' }}>
                                        <h3 style={{ color: '#fff', marginBottom: 16 }}>🚨 Warning Signs</h3>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                            {guidance.warning_signs?.map((w, i) => (
                                                <div key={i} style={{ padding: '12px 16px', background: 'rgba(255,255,255,.1)', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 12 }}>
                                                    <span style={{ fontSize: 16 }}>⚠️</span>
                                                    <p style={{ color: 'rgba(255,255,255,.85)', fontSize: 14, margin: 0 }}>{w}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="card animate-in-2">
                                        <h4 className="mb-4">Your Progress</h4>
                                        <div style={{ marginBottom: 12 }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                                                <span>Day {guidance.days_since_start}</span>
                                                <span style={{ color: 'var(--text-faint)' }}>stage-based</span>
                                            </div>
                                            <div className="progress-track">
                                                <div className="progress-fill" style={{ width: `${Math.min(100, (guidance.days_since_start / 42) * 100)}%` }} />
                                            </div>
                                        </div>
                                        <RiskBadge status={guidance.current_risk_status} />
                                    </div>

                                    <div className="card animate-in-3">
                                        <h4 className="mb-4">Not sure what to do?</h4>
                                        <p style={{ fontSize: 14, marginBottom: 16 }}>Use the AI Assistant to ask questions about your discharge instructions or general recovery guidance.</p>
                                        <button className="btn btn-primary" onClick={() => setTab('chat')}>Open AI Assistant →</button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="card empty-state">
                                <span>🧭</span>
                                <p>No recovery profile found. Ask your doctor to create one for you in Firestore.</p>
                            </div>
                        )}
                    </div>
                )}

                {/* ═══ AI CHAT ═══ */}
                {!loading && tab === 'chat' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>🤖 AI Recovery Assistant</h1>
                                <p className="page-header-sub">Ask questions about your discharge instructions, recovery exercises, or medications</p>
                            </div>
                            <span className="chip chip-green">RAG-Powered</span>
                        </div>

                        <div className="card animate-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 240px)' }}>
                            {/* Chat messages */}
                            <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0', display: 'flex', flexDirection: 'column', gap: 16 }}>
                                {chat.length === 0 && (
                                    <div className="empty-state" style={{ paddingTop: 60 }}>
                                        <span>💬</span>
                                        <p style={{ maxWidth: 360, margin: '0 auto' }}>Ask me anything about your recovery. I'll search your discharge documents and provide personalized guidance.</p>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 24, maxWidth: 500, width: '100%' }}>
                                            {['When can I start exercising?', 'What are my medication instructions?', 'When is my follow-up appointment?', 'What should I avoid doing?'].map(q => (
                                                <button key={q} className="btn btn-secondary" style={{ fontSize: 13, textAlign: 'left', justifyContent: 'flex-start' }} onClick={() => setQuestion(q)}>
                                                    "{q}"
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {chat.map((msg, i) => (
                                    <div key={i} className={`chat-bubble ${msg.type === 'user' ? 'chat-user' : `chat-ai${msg.alert ? ' chat-alert' : ''}`}`}>
                                        {msg.type === 'ai' && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--text-faint)' }}>
                                                    🤖 AI · {msg.source || 'fallback'}
                                                </span>
                                                {msg.alert && <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--risk-high)' }}>⚠️ ALERT</span>}
                                            </div>
                                        )}
                                        {msg.text}
                                    </div>
                                ))}
                                {isAsking && (
                                    <div className="chat-bubble chat-ai">
                                        <span className="animate-pulse" style={{ fontSize: 20, letterSpacing: 4 }}>•••</span>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            <div className="divider" style={{ margin: '16px 0' }} />

                            <form onSubmit={handleAsk} style={{ display: 'flex', gap: 12 }}>
                                <input
                                    placeholder="e.g. Can I start walking today? What is my pain limit?"
                                    value={question}
                                    onChange={e => setQuestion(e.target.value)}
                                    disabled={isAsking}
                                />
                                <button type="submit" className="btn btn-primary" disabled={isAsking || !question.trim()}>
                                    {isAsking ? '…' : 'Send →'}
                                </button>
                            </form>
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}
