"""
Community service for managing posts and comments (Firestore + in-memory fallback).
"""
from datetime import datetime
import uuid
from firebase_admin import firestore
from app.services.firebase_service import FirebaseService


class CommunityService:
    """Service layer for community posts and comments."""

    def __init__(self):
        self.firebase = FirebaseService()
        # ensure in-memory collections exist
        if getattr(self.firebase, '_in_memory', False):
            self.firebase._store.setdefault('community_posts', {})
            self.firebase._store.setdefault('community_comments', {})

    def create_post(self, author_id: str, author_role: str, title: str, content: str, category: str) -> dict:
        """Create a community post and return the created post data."""
        post = {
            'author_id': author_id,
            'author_role': author_role,
            'title': title,
            'content': content,
            'category': category,
            'created_at': datetime.utcnow().isoformat(),
            'likes_count': 0,
            'comments_count': 0,
        }

        if getattr(self.firebase, '_in_memory', False):
            post_id = str(uuid.uuid4())
            self.firebase._store['community_posts'][post_id] = dict(post)
            out = dict(post)
            out['post_id'] = post_id
            return out

        doc_ref = self.firebase._db.collection('community_posts').document()
        doc_ref.set(post)
        post['post_id'] = doc_ref.id
        return post

    def get_posts(self, category: str = None) -> list:
        """Return list of posts, optionally filtered by category (most recent first)."""
        if getattr(self.firebase, '_in_memory', False):
            posts = []
            for pid, data in self.firebase._store['community_posts'].items():
                out = dict(data)
                out['post_id'] = pid
                posts.append(out)
            if category:
                posts = [p for p in posts if p.get('category') == category]
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return posts

        ref = self.firebase._db.collection('community_posts')
        query = ref
        if category:
            query = query.where('category', '==', category)

        posts = []
        for doc in query.stream():
            d = doc.to_dict()
            d['post_id'] = doc.id
            posts.append(d)

        posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return posts

    def get_post_by_id(self, post_id: str) -> dict:
        """Return a single post with its comments or None if not found."""
        if getattr(self.firebase, '_in_memory', False):
            post = self.firebase._store['community_posts'].get(post_id)
            if not post:
                return None
            out = dict(post)
            out['post_id'] = post_id
            comments = []
            for cid, c in self.firebase._store['community_comments'].items():
                if c.get('post_id') == post_id:
                    cc = dict(c)
                    cc['comment_id'] = cid
                    comments.append(cc)
            comments.sort(key=lambda x: x.get('created_at', ''))
            out['comments'] = comments
            return out

        doc_ref = self.firebase._db.collection('community_posts').document(post_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        post = doc.to_dict()
        post['post_id'] = doc.id

        comments = []
        comments_ref = self.firebase._db.collection('community_comments')
        query = comments_ref.where('post_id', '==', post_id)
        for cdoc in query.stream():
            cd = cdoc.to_dict()
            cd['comment_id'] = cdoc.id
            comments.append(cd)

        comments.sort(key=lambda x: x.get('created_at', ''))
        post['comments'] = comments
        return post

    def add_comment(self, post_id: str, author_id: str, author_role: str, content: str, is_verified_doctor: bool = False) -> dict:
        """Add a comment to a post. Only users with role=='doctor' can be marked verified."""
        # Ensure only doctors can be marked as verified
        if is_verified_doctor and author_role != 'doctor':
            is_verified_doctor = False

        comment = {
            'post_id': post_id,
            'author_id': author_id,
            'author_role': author_role,
            'is_verified_doctor': bool(is_verified_doctor),
            'content': content,
            'created_at': datetime.utcnow().isoformat(),
        }

        if getattr(self.firebase, '_in_memory', False):
            comment_id = str(uuid.uuid4())
            self.firebase._store['community_comments'][comment_id] = dict(comment)
            # increment comments_count on post if present
            post = self.firebase._store['community_posts'].get(post_id)
            if post is not None:
                post['comments_count'] = post.get('comments_count', 0) + 1
            out = dict(comment)
            out['comment_id'] = comment_id
            return out

        # Firestore path: add comment and increment post comments_count
        comments_ref = self.firebase._db.collection('community_comments').document()
        comments_ref.set(comment)

        post_ref = self.firebase._db.collection('community_posts').document(post_id)
        try:
            post_ref.update({'comments_count': firestore.Increment(1)})
        except Exception:
            # best-effort fallback (non-atomic)
            post_doc = post_ref.get()
            if post_doc.exists:
                data = post_doc.to_dict()
                post_ref.update({'comments_count': data.get('comments_count', 0) + 1})

        comment['comment_id'] = comments_ref.id
        return comment

    def like_post(self, post_id: str) -> dict:
        """Increment likes_count for a post and return updated count (or None if not found)."""
        if getattr(self.firebase, '_in_memory', False):
            post = self.firebase._store['community_posts'].get(post_id)
            if not post:
                return None
            post['likes_count'] = post.get('likes_count', 0) + 1
            return {'post_id': post_id, 'likes_count': post['likes_count']}

        post_ref = self.firebase._db.collection('community_posts').document(post_id)
        try:
            post_ref.update({'likes_count': firestore.Increment(1)})
        except Exception:
            post_doc = post_ref.get()
            if not post_doc.exists:
                return None
            data = post_doc.to_dict()
            post_ref.update({'likes_count': data.get('likes_count', 0) + 1})

        # return updated document
        updated = post_ref.get().to_dict()
        updated['post_id'] = post_id
        return {'post_id': post_id, 'likes_count': updated.get('likes_count', 0)}
