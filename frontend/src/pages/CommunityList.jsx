import { useEffect, useState } from 'react'
import { api } from '../api'

export default function CommunityList() {
    const [posts, setPosts] = useState([])
    const [loading, setLoading] = useState(true)
    const [title, setTitle] = useState('')
    const [content, setContent] = useState('')
    const [category, setCategory] = useState('general')
    const [creating, setCreating] = useState(false)
    const [selectedPostId, setSelectedPostId] = useState(null)
    const [selectedPost, setSelectedPost] = useState(null)
    const [postLoading, setPostLoading] = useState(false)
    const [newComment, setNewComment] = useState('')
    const [addingComment, setAddingComment] = useState(false)

    useEffect(() => { load() }, [])

    const load = async () => {
        setLoading(true)
        try {
            const res = await api.getCommunityPosts()
            setPosts(res.posts || [])
        } catch (e) {
            console.warn('Failed to load posts', e)
            setPosts([])
        } finally { setLoading(false) }
    }

    const loadPost = async (postId) => {
        setPostLoading(true)
        try {
            const res = await api.getCommunityPostById(postId)
            setSelectedPost(res.post)
            setSelectedPostId(postId)
        } catch (e) {
            console.warn('Failed to load post', e)
            alert('Could not load post')
        } finally { setPostLoading(false) }
    }

    const handleCreate = async (e) => {
        e.preventDefault()
        if (!title.trim() || !content.trim()) return
        setCreating(true)
        try {
            await api.createCommunityPost({ title, content, category })
            setTitle(''); setContent(''); setCategory('general')
            load()
        } catch (err) {
            alert(err.message || 'Failed to create post')
        } finally { setCreating(false) }
    }

    const handleAddComment = async (e) => {
        e.preventDefault()
        if (!newComment.trim() || !selectedPostId) return
        setAddingComment(true)
        try {
            await api.addCommunityComment(selectedPostId, { content: newComment })
            setNewComment('')
            loadPost(selectedPostId)
        } catch (err) {
            alert(err.message || 'Failed to add comment')
        } finally { setAddingComment(false) }
    }

    const handleLike = async () => {
        if (!selectedPostId) return
        try {
            await api.likeCommunityPost(selectedPostId)
            loadPost(selectedPostId)
        } catch (e) {
            console.warn('Like failed', e)
        }
    }

    // Show post detail if selected
    if (selectedPost && selectedPostId) {
        return (
            <div>
                <div className="page-header">
                    <div>
                        <button style={{ marginBottom: 12, background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: 14, fontWeight: 600 }} onClick={() => { setSelectedPostId(null); setSelectedPost(null); }}>← Back to Posts</button>
                        <h1>{selectedPost.title}</h1>
                        <p className="page-header-sub">Posted by {selectedPost.author_role} • {new Date(selectedPost.created_at).toLocaleString()}</p>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
                    <div>
                        <div className="card">
                            <p style={{ whiteSpace: 'pre-wrap' }}>{selectedPost.content}</p>
                            <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
                                <button className="btn btn-secondary" onClick={handleLike}>👍 Like ({selectedPost.likes_count || 0})</button>
                            </div>
                        </div>

                        <div style={{ marginTop: 16 }}>
                            <h3>Comments ({(selectedPost.comments || []).length})</h3>
                            {(selectedPost.comments || []).map(c => (
                                <div key={c.comment_id} className="card" style={{ marginBottom: 10 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <div style={{ fontWeight: 700 }}>{c.author_role}{c.is_verified_doctor ? ' (Verified Doctor)' : ''}</div>
                                        <div style={{ fontSize: 12, color: 'var(--text-faint)' }}>{new Date(c.created_at).toLocaleString()}</div>
                                    </div>
                                    <p style={{ marginTop: 8 }}>{c.content}</p>
                                </div>
                            ))}

                            <form onSubmit={handleAddComment} style={{ marginTop: 12 }}>
                                <textarea placeholder="Add a comment…" value={newComment} onChange={e => setNewComment(e.target.value)} />
                                <button className="btn btn-primary" disabled={addingComment}>{addingComment ? 'Adding…' : 'Add Comment'}</button>
                            </form>
                        </div>
                    </div>

                    <aside>
                        <div className="card">
                            <h4>Post Details</h4>
                            <p style={{ color: 'var(--text-faint)' }}>Category: {selectedPost.category}</p>
                            <p style={{ color: 'var(--text-faint)' }}>Comments: {selectedPost.comments_count}</p>
                        </div>
                    </aside>
                </div>
            </div>
        )
    }

    // Show posts list
    return (
        <div>
            <div className="page-header">
                <div>
                    <h1>Community</h1>
                    <p className="page-header-sub">Share experiences, ask questions, and support each other.</p>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>
                <div>
                    <div className="card">
                        <h3>Create a Post</h3>
                        <form onSubmit={handleCreate}>
                            <div className="mb-3">
                                <input placeholder="Title" value={title} onChange={e => setTitle(e.target.value)} />
                            </div>
                            <div className="mb-3">
                                <select value={category} onChange={e => setCategory(e.target.value)}>
                                    <option value="general">General</option>
                                    <option value="trauma">Trauma</option>
                                    <option value="inspiration">Inspiration</option>
                                    <option value="medical_question">Medical Question</option>
                                </select>
                            </div>
                            <div className="mb-3">
                                <textarea placeholder="Share your experience..." value={content} onChange={e => setContent(e.target.value)} />
                            </div>
                            <button className="btn btn-primary" disabled={creating}>{creating ? 'Posting…' : 'Post'}</button>
                        </form>
                    </div>

                    <div style={{ marginTop: 16 }}>
                        {loading ? <div className="card">Loading posts…</div> : (
                            posts.length === 0 ? <div className="card empty-state">No posts yet.</div> : (
                                posts.map(p => (
                                    <div className="card" key={p.post_id} style={{ marginBottom: 12 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <h4 style={{ margin: 0 }}>{p.title}</h4>
                                            <span style={{ fontSize: 12, color: 'var(--text-faint)' }}>{new Date(p.created_at).toLocaleString()}</span>
                                        </div>
                                        <p style={{ color: 'var(--text-muted)' }}>{p.content.slice(0, 240)}{p.content.length > 240 ? '…' : ''}</p>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div style={{ fontSize: 13, color: 'var(--text-faint)' }}>{p.author_role} • {p.category}</div>
                                            <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={() => loadPost(p.post_id)}>View</button>
                                        </div>
                                    </div>
                                ))
                            )
                        )}
                    </div>
                </div>

                <aside>
                    <div className="card">
                        <h4>About the Community</h4>
                        <p style={{ color: 'var(--text-faint)' }}>Be respectful. Do not share personal health identifiers. Medical advice from doctors is clearly marked.</p>
                    </div>
                </aside>
            </div>
        </div>
    )
}
