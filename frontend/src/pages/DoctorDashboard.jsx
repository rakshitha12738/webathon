import { useState, useEffect } from 'react'
import { api } from '../api'
import { STATIC_PATIENTS, STATIC_PATIENT_DETAIL } from '../demoData'

/* ─── helpers ─────────────────────────── */
const riskClass = (s) => `risk-${s}` || 'risk-stable'
const riskLabel = { stable: 'Stable', monitor: 'Monitor', needs_review: 'Needs Review', high_risk: 'High Risk' }

function RiskBadge({ status }) {
    return <span className={`risk-badge ${riskClass(status || 'stable')}`}>⬤ {riskLabel[status] || 'Stable'}</span>
}

function StatCard({ label, value, sub, icon }) {
    return (
        <div className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span className="stat-label">{label}</span>
                {icon && <span style={{ fontSize: 22 }}>{icon}</span>}
            </div>
            <div className="stat-value">{value ?? '—'}</div>
            {sub && <div className="stat-sub">{sub}</div>}
        </div>
    )
}

const TABS = [
    { id: 'roster', icon: '👥', label: 'Patient Roster' },
    { id: 'detail', icon: '🔍', label: 'Patient Detail' },
    { id: 'upload', icon: '📄', label: 'Upload Documents' },
]

export default function DoctorDashboard() {
    const [tab, setTab] = useState('roster')
    const [patients, setPatients] = useState([])
    const [loading, setLoading] = useState(true)
    const [selected, setSelected] = useState(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [uploadFile, setUploadFile] = useState(null)
    const [uploading, setUploading] = useState(false)
    const [uploadResult, setUploadResult] = useState(null)

    useEffect(() => { loadPatients() }, [])

    const loadPatients = async () => {
        setLoading(true)
        try {
            const d = await api.getPatients()
            const list = d.patients || []
            // Use static demo data if backend returns nothing
            setPatients(list.length > 0 ? list : STATIC_PATIENTS)
        } catch (e) {
            console.error(e)
            setPatients(STATIC_PATIENTS)
        } finally { setLoading(false) }
    }

    const handleSelectPatient = async (p) => {
        setTab('detail')
        setSelected(null)
        setDetailLoading(true)
        try {
            const d = await api.getPatientDetails(p.id)
            setSelected(d)
        } catch (e) {
            console.warn('API error, using demo detail data:', e.message)
            // Merge real patient basic info with static detail structure
            setSelected({ ...STATIC_PATIENT_DETAIL, patient: { id: p.id, name: p.name, email: p.email } })
        } finally { setDetailLoading(false) }
    }

    const handleUpload = async (e) => {
        e.preventDefault()
        if (!uploadFile) return
        setUploading(true); setUploadResult(null)
        const formData = new FormData()
        formData.append('file', uploadFile)
        // Attach patient_id if we have a selected patient
        if (selected?.patient?.id) formData.append('patient_id', selected.patient.id)
        try {
            const r = await api.uploadDischarge(formData)
            setUploadResult({ success: true, ...r })
        } catch (e) {
            setUploadResult({ success: false, msg: e.message })
        } finally { setUploading(false) }
    }

    // Compute summary stats from patient roster
    const totalPatients = patients.length
    const highRiskCount = patients.filter(p => p.latest_risk_status === 'high_risk').length
    const monitorCount = patients.filter(p => ['monitor', 'needs_review'].includes(p.latest_risk_status)).length
    const deviationCount = patients.filter(p => p.deviation_flag).length

    return (
        <div className="dashboard-layout">
            {/* ── Sidebar ── */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <h2>RECOVER.AI</h2>
                    <p>Clinician Portal</p>
                </div>
                <div className="sidebar-section">Navigation</div>
                {TABS.filter(t => t.id !== 'detail' || selected).map(t => (
                    <button key={t.id} className={`nav-item ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
                        <span className="nav-icon">{t.icon}</span>{t.label}
                    </button>
                ))}
                {selected && (
                    <button className={`nav-item ${tab === 'detail' ? 'active' : ''}`} onClick={() => setTab('detail')}>
                        <span className="nav-icon">🔍</span>
                        <div style={{ flex: 1, textAlign: 'left' }}>
                            <div>Patient Detail</div>
                            <div style={{ fontSize: 11, opacity: .7 }}>{selected?.patient?.name}</div>
                        </div>
                    </button>
                )}
                <div style={{ flex: 1 }} />
                <div style={{ borderTop: '1px solid rgba(255,255,255,.1)', paddingTop: 12 }}>
                    <div style={{ padding: '8px 12px', fontSize: 13 }}>
                        <p style={{ color: 'rgba(255,255,255,.5)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.06em' }}>Signed in as</p>
                        <p style={{ color: '#fff', fontWeight: 600, marginTop: 2 }}>{localStorage.getItem('name') || 'Doctor'}</p>
                    </div>
                    <button className="nav-item" style={{ color: 'rgba(255,255,255,.5)' }}
                        onClick={() => { localStorage.clear(); window.location.href = '/login' }}>
                        <span className="nav-icon">🚪</span>Log Out
                    </button>
                </div>
            </aside>

            {/* ── Main ── */}
            <main className="main-content">

                {/* ═══ ROSTER ═══ */}
                {tab === 'roster' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>Patient Roster</h1>
                                <p className="page-header-sub">Monitoring {totalPatients} active recovery cases</p>
                            </div>
                            <button className="btn btn-secondary" onClick={loadPatients}>🔄 Refresh</button>
                        </div>

                        {/* Summary Stats */}
                        <div className="grid-4 mb-6">
                            <StatCard label="Total Patients" value={totalPatients} sub="Active cases" icon="👥" />
                            <StatCard label="High Risk" value={highRiskCount} sub="Immediate attention" icon="🚨" />
                            <StatCard label="Monitor / Review" value={monitorCount} sub="Elevated risk" icon="⚠️" />
                            <StatCard label="Deviation Flags" value={deviationCount} sub="Outside range" icon="🚩" />
                        </div>

                        {loading ? (
                            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-faint)' }}>Loading patients…</div>
                        ) : patients.length === 0 ? (
                            <div className="card empty-state">
                                <span>👥</span>
                                <p>No patients assigned to you yet. Patients must add your User ID when registering.</p>
                                <div style={{ marginTop: 16, background: 'var(--bg-2)', padding: '12px 20px', borderRadius: 10, display: 'inline-block' }}>
                                    <p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>Your Doctor ID</p>
                                    <code style={{ fontWeight: 700, color: 'var(--primary)' }}>{localStorage.getItem('user_id')}</code>
                                </div>
                            </div>
                        ) : (
                            <div className="card animate-in">
                                <div className="table-wrap">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Patient</th>
                                                <th>Risk Status</th>
                                                <th>Risk Score</th>
                                                <th>Deviation Flag</th>
                                                <th>Complication Index</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {patients.map(p => (
                                                <tr key={p.id} style={{ cursor: 'pointer' }} onClick={() => handleSelectPatient(p)}>
                                                    <td>
                                                        <div style={{ fontWeight: 700 }}>{p.name}</div>
                                                        <div style={{ fontSize: 12, color: 'var(--text-faint)' }}>{p.email}</div>
                                                    </td>
                                                    <td><RiskBadge status={p.latest_risk_status} /></td>
                                                    <td>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                            <div style={{ width: 60, height: 6, background: 'var(--bg-2)', borderRadius: 99, overflow: 'hidden' }}>
                                                                <div style={{
                                                                    width: `${p.latest_risk_score}%`, height: '100%',
                                                                    background: p.latest_risk_score >= 70 ? 'var(--risk-high)' : p.latest_risk_score >= 40 ? 'var(--accent-dark)' : 'var(--primary)',
                                                                    borderRadius: 99
                                                                }} />
                                                            </div>
                                                            <span style={{ fontWeight: 700 }}>{p.latest_risk_score}</span>
                                                        </div>
                                                    </td>
                                                    <td>
                                                        {p.deviation_flag
                                                            ? <span className="chip chip-amber">⚠️ Flagged</span>
                                                            : <span className="chip chip-green">✅ Normal</span>}
                                                    </td>
                                                    <td>
                                                        <span style={{ fontWeight: 700, color: p.complication_index > 0 ? 'var(--risk-review)' : 'var(--risk-stable)' }}>
                                                            {p.complication_index}%
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <button className="btn btn-secondary" style={{ fontSize: 12, padding: '6px 14px' }}>
                                                            View Details →
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ═══ DETAIL ═══ */}
                {tab === 'detail' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>{selected?.patient?.name || 'Patient Detail'}</h1>
                                <p className="page-header-sub">{selected?.patient?.email}</p>
                            </div>
                            <button className="btn btn-secondary" onClick={() => setTab('roster')}>← Back to Roster</button>
                        </div>

                        {detailLoading ? (
                            <div style={{ textAlign: 'center', padding: 60 }}>Loading patient data…</div>
                        ) : selected ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                                {/* Top stats */}
                                <div className="grid-4 animate-in">
                                    <StatCard label="Risk Status" value={riskLabel[selected.latest_risk_score?.status] || 'Stable'} icon="🛡️" />
                                    <StatCard label="Risk Score" value={selected.latest_risk_score?.score ?? '—'} sub="Latest" icon="📊" />
                                    <StatCard label="Complication Index" value={`${selected.complication_index}%`} sub={selected.complication_index > 0 ? '⚠️ Elevated' : '✅ Normal'} icon="🔬" />
                                    <StatCard label="Log Count" value={selected.log_count} sub="Entries total" icon="📝" />
                                </div>

                                <div className="animate-in-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                                    {/* Recovery Profile */}
                                    <div className="card">
                                        <h3 className="mb-4">Recovery Profile</h3>
                                        {selected.recovery_profile ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                                {[
                                                    { label: 'Condition', value: selected.recovery_profile.condition_type },
                                                    { label: 'Expected Duration', value: `${selected.recovery_profile.expected_duration_days} days` },
                                                    { label: 'Start Date', value: selected.recovery_profile.start_date?.split('T')[0] || '—' },
                                                    { label: 'Acceptable Pain Wk1', value: `0–${selected.recovery_profile.acceptable_pain_week_1}` },
                                                    { label: 'Acceptable Pain Wk3', value: `0–${selected.recovery_profile.acceptable_pain_week_3}` },
                                                ].map(({ label, value }) => (
                                                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                                                        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{label}</span>
                                                        <span style={{ fontWeight: 600, fontSize: 13 }}>{value || '—'}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="empty-state" style={{ padding: '24px 0' }}>
                                                <span style={{ fontSize: 28 }}>📋</span>
                                                <p style={{ fontSize: 13 }}>No recovery profile found. Create one in Firestore.</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Risk Assessment */}
                                    <div className="card">
                                        <h3 className="mb-4">Latest Risk Assessment</h3>
                                        {selected.latest_risk_score ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                                <div style={{ padding: '16px', borderRadius: 12, background: 'var(--bg)' }}>
                                                    <RiskBadge status={selected.latest_risk_score.status} />
                                                    <p style={{ fontWeight: 800, fontSize: 36, color: 'var(--primary)', margin: '8px 0' }}>{selected.latest_risk_score.score}</p>
                                                    <p style={{ fontSize: 13, color: 'var(--text-faint)' }}>Risk score (0–100)</p>
                                                </div>
                                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                                    <div style={{ padding: '12px', borderRadius: 10, background: 'var(--bg)' }}>
                                                        <p style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-faint)' }}>Deviation Flag</p>
                                                        <p style={{ fontWeight: 700, marginTop: 4 }}>
                                                            {selected.latest_risk_score.deviation_flag ? '⚠️ Flagged' : '✅ Normal'}
                                                        </p>
                                                    </div>
                                                    <div style={{ padding: '12px', borderRadius: 10, background: 'var(--bg)' }}>
                                                        <p style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-faint)' }}>Complication %</p>
                                                        <p style={{ fontWeight: 700, marginTop: 4, color: selected.complication_index > 0 ? 'var(--risk-review)' : 'var(--risk-stable)' }}>
                                                            {selected.complication_index}%
                                                        </p>
                                                    </div>
                                                </div>

                                                <div>
                                                    <h4 className="mb-2" style={{ marginTop: 4 }}>Recent Risk Scores (last 10)</h4>
                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                                        {(selected.recent_risk_scores || []).slice(0, 5).map((rs, i) => (
                                                            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 10px', background: 'var(--bg)', borderRadius: 8 }}>
                                                                <div style={{ width: 50, height: 5, background: 'var(--bg-2)', borderRadius: 99, overflow: 'hidden' }}>
                                                                    <div style={{ width: `${rs.score}%`, height: '100%', background: 'var(--primary)', borderRadius: 99 }} />
                                                                </div>
                                                                <span style={{ fontSize: 12, fontWeight: 600 }}>{rs.score}</span>
                                                                <RiskBadge status={rs.status} />
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="empty-state" style={{ padding: '24px 0' }}><span style={{ fontSize: 28 }}>📊</span><p>No risk scores yet.</p></div>
                                        )}
                                    </div>
                                </div>

                                {/* Logs Table */}
                                <div className="card animate-in-3">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3>Daily Log History ({selected.log_count} entries)</h3>
                                        <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={() => setTab('upload')}>
                                            📤 Upload Discharge Docs
                                        </button>
                                    </div>
                                    {selected.daily_logs?.length === 0 ? (
                                        <div className="empty-state"><span>📋</span><p>No logs submitted yet.</p></div>
                                    ) : (
                                        <div className="table-wrap">
                                            <table>
                                                <thead>
                                                    <tr><th>Date</th><th>Pain</th><th>Mood</th><th>Sleep</th><th>Appetite</th><th>Swelling</th><th>Body Part</th><th>Risk</th><th>Notes</th></tr>
                                                </thead>
                                                <tbody>
                                                    {(selected.daily_logs || []).map((log, i) => (
                                                        <tr key={i}>
                                                            <td style={{ fontWeight: 600 }}>{log.date}</td>
                                                            <td>
                                                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                                    <div style={{ width: 32, height: 5, background: 'var(--bg-2)', borderRadius: 99, overflow: 'hidden' }}>
                                                                        <div style={{ width: `${log.pain_level * 10}%`, height: '100%', background: log.pain_level >= 8 ? 'var(--risk-high)' : log.pain_level >= 5 ? 'var(--accent-dark)' : 'var(--primary)', borderRadius: 99 }} />
                                                                    </div>
                                                                    <span style={{ fontWeight: 700 }}>{log.pain_level}/10</span>
                                                                </div>
                                                            </td>
                                                            <td>{log.mood_level}/5</td>
                                                            <td>{log.sleep_hours}h</td>
                                                            <td style={{ textTransform: 'capitalize' }}>{log.appetite}</td>
                                                            <td>{log.swelling ? <span className="chip chip-amber">⚠️ Yes</span> : <span className="chip chip-green">No</span>}</td>
                                                            <td style={{ fontSize: 13 }}>{log.body_part || '—'}</td>
                                                            <td><RiskBadge status={log.risk_status} /></td>
                                                            <td style={{ fontSize: 12, maxWidth: 180, color: 'var(--text-muted)' }}>{log.note_text || '—'}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : null}
                    </div>
                )}

                {/* ═══ UPLOAD ═══ */}
                {tab === 'upload' && (
                    <div>
                        <div className="page-header">
                            <div>
                                <h1>📄 Upload Discharge Documents</h1>
                                <p className="page-header-sub">PDF discharge summaries are processed and stored in Qdrant for patient AI Q&A</p>
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, maxWidth: 900 }}>
                            <div className="card animate-in">
                                <h3 className="mb-4">Upload PDF Document</h3>
                                <form onSubmit={handleUpload}>
                                    <div className="mb-4">
                                        <label>Select Discharge PDF</label>
                                        <div style={{ border: '2px dashed var(--border-strong)', borderRadius: 12, padding: '32px', textAlign: 'center', cursor: 'pointer', background: uploadFile ? 'rgba(96,108,56,.06)' : 'transparent', transition: 'all .18s' }}
                                            onClick={() => document.getElementById('pdf-upload').click()}>
                                            <span style={{ fontSize: 36 }}>{uploadFile ? '✅' : '📂'}</span>
                                            <p style={{ fontWeight: 600, marginTop: 8 }}>{uploadFile ? uploadFile.name : 'Click to select PDF'}</p>
                                            <p style={{ fontSize: 12, color: 'var(--text-faint)', marginTop: 4 }}>Discharge summary, post-op instructions, medication sheets…</p>
                                            <input id="pdf-upload" type="file" accept=".pdf" style={{ display: 'none' }} onChange={e => { setUploadFile(e.target.files[0]); setUploadResult(null); }} />
                                        </div>
                                    </div>

                                    <button type="submit" className="btn btn-primary w-full" disabled={!uploadFile || uploading} style={{ padding: 14 }}>
                                        {uploading ? <span className="animate-pulse">Processing PDF chunks…</span> : '📤 Upload & Index Document'}
                                    </button>
                                </form>

                                {uploadResult && (
                                    <div className="mt-4" style={{ padding: '16px', borderRadius: 12, background: uploadResult.success ? 'var(--risk-stable-bg)' : 'var(--risk-high-bg)', border: `1px solid ${uploadResult.success ? 'var(--risk-stable)' : 'var(--risk-high)'}` }}>
                                        {uploadResult.success ? (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                                <p style={{ fontWeight: 700, color: 'var(--risk-stable)' }}>✅ Document processed successfully</p>
                                                <p style={{ fontSize: 13 }}>Chunks indexed: <strong>{uploadResult.chunks_processed}</strong></p>
                                                <p style={{ fontSize: 12, color: 'var(--text-muted)', wordBreak: 'break-all' }}>{uploadResult.file_url}</p>
                                            </div>
                                        ) : (
                                            <p style={{ color: 'var(--risk-high)', fontWeight: 600 }}>❌ {uploadResult.msg}</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-col gap-4">
                                <div className="card animate-in-2">
                                    <h4 className="mb-4">How RAG works</h4>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                        {[
                                            { step: '1', title: 'Upload PDF', desc: 'Discharge summary is uploaded to Firebase Storage' },
                                            { step: '2', title: 'Text Extraction', desc: 'PyPDF2 extracts text and splits into chunks' },
                                            { step: '3', title: 'Embedding', desc: 'Sentence Transformers convert chunks to vectors' },
                                            { step: '4', title: 'Qdrant Index', desc: 'Vectors + text stored in Qdrant collection' },
                                            { step: '5', title: 'Patient Q&A', desc: 'Relevant chunks retrieved and answered by Gemini 1.5 Flash' },
                                        ].map(({ step, title, desc }) => (
                                            <div key={step} style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                                                <div style={{ width: 28, height: 28, borderRadius: 99, background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, flexShrink: 0 }}>{step}</div>
                                                <div>
                                                    <p style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>{title}</p>
                                                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{desc}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="card animate-in-3" style={{ background: 'var(--bg-2)' }}>
                                    <h4 className="mb-2">Supported Formats</h4>
                                    <p style={{ fontSize: 13 }}>Currently PDF files only. The patient AI Assistant will automatically use these documents when answering questions.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    )
}
