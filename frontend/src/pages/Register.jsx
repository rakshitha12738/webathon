import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

export default function Register() {
    const [form, setForm] = useState({ name: '', email: '', password: '', role: 'patient', assigned_doctor_id: '' })
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

    const handleRegister = async (e) => {
        e.preventDefault()
        setLoading(true); setError('')
        try {
            const payload = { ...form }
            if (form.role === 'doctor') delete payload.assigned_doctor_id
            const data = await api.register(payload)
            localStorage.setItem('token', data.token)
            localStorage.setItem('role', data.role)
            localStorage.setItem('user_id', data.user_id)
            localStorage.setItem('name', payload.name)
            navigate(data.role === 'doctor' ? '/doctor' : '/patient')
        } catch (err) {
            setError(err.message)
        } finally { setLoading(false) }
    }

    return (
        <div className="auth-page">
            <div className="auth-left">
                <div style={{ marginBottom: 48 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
                        <div style={{ width: 48, height: 48, borderRadius: 14, background: 'rgba(255,255,255,.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>🩺</div>
                        <h2 style={{ color: '#fff', fontSize: 28 }}>RECOVER.AI</h2>
                    </div>
                    <h1 style={{ color: '#fff', fontSize: 38, lineHeight: 1.2, marginBottom: 16 }}>Join the future<br />of recovery care</h1>
                    <p style={{ color: 'rgba(255,255,255,.7)', fontSize: 16, maxWidth: 380 }}>
                        Whether you're a patient on the road to recovery or a physician monitoring outcomes — RECOVER.AI has you covered.
                    </p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 360 }}>
                    {['Personalised adaptive recovery guidance', 'Real-time AI risk assessment engine', 'RAG-powered discharge document Q&A', 'Secure role-based access control'].map(t => (
                        <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'rgba(255,255,255,.85)', fontSize: 14 }}>
                            <span style={{ fontSize: 16 }}>✅</span> {t}
                        </div>
                    ))}
                </div>
            </div>

            <div className="auth-right">
                <div className="auth-form-wrap animate-in">
                    <h2 className="mb-2">Create your account</h2>
                    <p className="mb-6" style={{ fontSize: 14 }}>Start your personalised recovery journey today</p>

                    <form onSubmit={handleRegister}>
                        <div className="mb-4">
                            <label>Full Name</label>
                            <input placeholder="Dr. Jane Smith" value={form.name} onChange={e => set('name', e.target.value)} required />
                        </div>
                        <div className="mb-4">
                            <label>Email Address</label>
                            <input type="email" placeholder="jane@hospital.com" value={form.email} onChange={e => set('email', e.target.value)} required />
                        </div>
                        <div className="mb-4">
                            <label>Password</label>
                            <input type="password" placeholder="Min. 8 characters" value={form.password} onChange={e => set('password', e.target.value)} required />
                        </div>

                        <div className="mb-4">
                            <label>I am a…</label>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                {[{ v: 'patient', icon: '🧑‍🦽', label: 'Patient' }, { v: 'doctor', icon: '👨‍⚕️', label: 'Doctor / Clinician' }].map(({ v, icon, label }) => (
                                    <button type="button" key={v} onClick={() => set('role', v)}
                                        style={{
                                            padding: '14px', borderRadius: 10, border: `2px solid ${form.role === v ? 'var(--primary)' : 'var(--border)'}`,
                                            background: form.role === v ? 'rgba(96,108,56,.08)' : 'transparent',
                                            fontSize: 14, fontWeight: 600, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, cursor: 'pointer'
                                        }}>
                                        <span style={{ fontSize: 22 }}>{icon}</span>
                                        <span style={{ color: form.role === v ? 'var(--primary)' : 'var(--text-muted)' }}>{label}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {form.role === 'patient' && (
                            <div className="mb-4">
                                <label>Assigned Doctor ID <span style={{ fontWeight: 400, color: 'var(--text-faint)' }}>(optional)</span></label>
                                <input placeholder="Paste doctor's user ID" value={form.assigned_doctor_id} onChange={e => set('assigned_doctor_id', e.target.value)} />
                                <p className="tooltip-hint">Ask your doctor to share their User ID from their dashboard.</p>
                            </div>
                        )}

                        {error && (
                            <div style={{ background: 'var(--risk-high-bg)', color: 'var(--risk-high)', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
                                ⚠️ {error}
                            </div>
                        )}

                        <button type="submit" className="btn btn-primary w-full" disabled={loading} style={{ padding: '12px 0' }}>
                            {loading ? <span className="animate-pulse">Creating account…</span> : 'Create Account →'}
                        </button>
                    </form>

                    <div className="divider" />
                    <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                        Already have an account?{' '}
                        <Link to="/login" style={{ color: 'var(--primary)', fontWeight: 700, textDecoration: 'none' }}>Sign in</Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
