import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api'

export default function CommunityPost() {
    const { id } = useParams()
    const [post, setPost] = useState(null)
    const [loading, setLoading] = useState(true)
    const [comment, setComment] = useState('')
    const [adding, setAdding] = useState(false)

    useEffect(() => { load() }, [id])

    const load = async () => {
        setLoading(true)
        try {
            const res = await api.getCommunityPostById(id)
            setPost(res.post)
        } catch (e) {
            console.warn('Failed to load post', e)
            setPost(null)
        } finally { setLoading(false) }
    }

    const handleAddComment = async (e) => {
        e.preventDefault()
        if (!comment.trim()) return
        setAdding(true)
        try {
            await api.addCommunityComment(id, { content: comment })
            setComment('')
            load()
        } catch (err) {
            alert(err.message || 'Failed to add comment')
        } finally { setAdding(false) }
    }

    const handleLike = async () => {
        try {
            await api.likeCommunityPost(id)
            load()
        } catch (e) {
            console.warn('Like failed', e)
        }
    }

    if (loading) return <div className="card">Loading post…</div>
    if (!post) return <div className="card empty-state">Post not found.</div>

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1>{post.title}</h1>
                    <p className="page-header-sub">Posted by {post.author_role} • {new Date(post.created_at).toLocaleString()}</p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
                <div>
                    <div className="card">
                        <p style={{ whiteSpace: 'pre-wrap' }}>{post.content}</p>
                        <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
                            <button className="btn btn-secondary" onClick={handleLike}>👍 Like ({post.likes_count || 0})</button>
                        </div>
                    </div>

                    <div style={{ marginTop: 16 }}>
                        <h3>Comments ({(post.comments || []).length})</h3>
                        {(post.comments || []).map(c => (
                            <div key={c.comment_id} className="card" style={{ marginBottom: 10 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <div style={{ fontWeight: 700 }}>{c.author_role}{c.is_verified_doctor ? ' (Verified Doctor)' : ''}</div>
                                    <div style={{ fontSize: 12, color: 'var(--text-faint)' }}>{new Date(c.created_at).toLocaleString()}</div>
                                </div>
                                <p style={{ marginTop: 8 }}>{c.content}</p>
                            </div>
                        ))}

                        <form onSubmit={handleAddComment} style={{ marginTop: 12 }}>
                            <textarea placeholder="Add a comment…" value={comment} onChange={e => setComment(e.target.value)} />
                            <button className="btn btn-primary" disabled={adding}>{adding ? 'Adding…' : 'Add Comment'}</button>
                        </form>
                    </div>
                </div>

                <aside>
                    <div className="card">
                        <h4>Post Details</h4>
                        <p style={{ color: 'var(--text-faint)' }}>Category: {post.category}</p>
                        <p style={{ color: 'var(--text-faint)' }}>Comments: {post.comments_count}</p>
                    </div>
                </aside>
            </div>
        </div>
    )
}
