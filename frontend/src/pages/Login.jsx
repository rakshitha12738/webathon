import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleLogin = async (e) => {
        e.preventDefault()
        setLoading(true); setError('')
        try {
            const data = await api.login({ email, password })
            localStorage.setItem('token', data.token)
            localStorage.setItem('role', data.role)
            localStorage.setItem('user_id', data.user_id)
            localStorage.setItem('name', data.name)
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
                    <h1 style={{ color: '#fff', fontSize: 42, lineHeight: 1.15, marginBottom: 16 }}>
                        Intelligent<br />Post-Discharge<br />Recovery
                    </h1>
                    <p style={{ color: 'rgba(255,255,255,.7)', fontSize: 17, maxWidth: 400, lineHeight: 1.6 }}>
                        AI-powered monitoring for patients and clinicians — real-time risk assessment, adaptive guidance, and RAG-based Q&amp;A.
                    </p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, maxWidth: 400 }}>
                    {[['🔒', 'Firebase Authentication'], ['📊', 'Community Healing'], ['🤖', 'AI Assistant'], ['📄', 'Retrieval Augmented Generation']].map(([icon, label]) => (
                        <div key={`${icon}-${label}`} style={{ background: 'rgba(255,255,255,.1)', padding: '14px 18px', borderRadius: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontSize: 22 }}>{icon}</span>
                            <span style={{ color: 'rgba(255,255,255,.85)', fontWeight: 600, fontSize: 14 }}>{label}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="auth-right">
                <div className="auth-form-wrap animate-in">
                    <h2 className="mb-2">Welcome back</h2>
                    <p className="mb-6" style={{ fontSize: 14 }}>Sign in to your RECOVER.AI account</p>

                    <form onSubmit={handleLogin}>
                        <div className="mb-4">
                            <label>Email Address</label>
                            <input type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
                        </div>
                        <div className="mb-4">
                            <label>Password</label>
                            <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
                        </div>

                        {error && (
                            <div style={{ background: 'var(--risk-high-bg)', color: 'var(--risk-high)', padding: '10px 14px', borderRadius: 8, fontSize: 13, marginBottom: 16, fontWeight: 500 }}>
                                ⚠️ {error}
                            </div>
                        )}

                        <button type="submit" className="btn btn-primary w-full" disabled={loading} style={{ padding: '12px 0' }}>
                            {loading ? <span className="animate-pulse">Authenticating…</span> : 'Sign In →'}
                        </button>
                    </form>

                    <div className="divider" />
                    <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
                        No account?{' '}
                        <Link to="/register" style={{ color: 'var(--primary)', fontWeight: 700, textDecoration: 'none' }}>Register here</Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
