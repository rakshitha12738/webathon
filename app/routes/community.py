"""
Community routes for posting, commenting and liking posts.
"""
from flask import Blueprint, request, jsonify
from app.services.community_service import CommunityService
from app.utils.auth_utils import token_required

community_bp = Blueprint('community', __name__)
service = CommunityService()


@community_bp.route('/posts', methods=['POST'])
@token_required
def create_post():
    """Create a new community post. Only patients may create posts."""
    try:
        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        content = (data.get('content') or '').strip()
        category = (data.get('category') or 'general').strip()

        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400

        current = request.current_user
        if current.get('role') != 'patient':
            return jsonify({'error': 'Only patients may create posts'}), 403

        post = service.create_post(
            author_id=current.get('user_id'),
            author_role=current.get('role'),
            title=title,
            content=content,
            category=category,
        )

        return jsonify({'message': 'Post created', 'post': post}), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create post: {str(e)}'}), 500


@community_bp.route('/posts', methods=['GET'])
def list_posts():
    """List community posts. Optional query param `category` filters results."""
    try:
        category = request.args.get('category')
        posts = service.get_posts(category=category)
        return jsonify({'posts': posts, 'count': len(posts)}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch posts: {str(e)}'}), 500


@community_bp.route('/posts/<post_id>', methods=['GET'])
def get_post(post_id):
    """Get post details and its comments."""
    try:
        post = service.get_post_by_id(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify({'post': post}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch post: {str(e)}'}), 500


@community_bp.route('/posts/<post_id>/comments', methods=['POST'])
@token_required
def add_comment(post_id):
    """Add a comment to a post. Doctors may set `is_verified_doctor` flag."""
    try:
        data = request.get_json() or {}
        content = (data.get('content') or '').strip()
        is_verified_doctor = bool(data.get('is_verified_doctor', False))

        if not content:
            return jsonify({'error': 'Comment content is required'}), 400

        current = request.current_user

        # Prevent patients from marking themselves verified
        if is_verified_doctor and current.get('role') != 'doctor':
            is_verified_doctor = False

        # ensure post exists
        existing = service.get_post_by_id(post_id)
        if not existing:
            return jsonify({'error': 'Post not found'}), 404

        comment = service.add_comment(
            post_id=post_id,
            author_id=current.get('user_id'),
            author_role=current.get('role'),
            content=content,
            is_verified_doctor=is_verified_doctor,
        )

        return jsonify({'message': 'Comment added', 'comment': comment}), 201
    except Exception as e:
        return jsonify({'error': f'Failed to add comment: {str(e)}'}), 500


@community_bp.route('/posts/<post_id>/like', methods=['POST'])
@token_required
def like_post(post_id):
    """Increment a post's like count."""
    try:
        # ensure post exists
        existing = service.get_post_by_id(post_id)
        if not existing:
            return jsonify({'error': 'Post not found'}), 404

        result = service.like_post(post_id)
        if result is None:
            return jsonify({'error': 'Post not found'}), 404
        return jsonify({'message': 'Post liked', 'likes_count': result.get('likes_count')}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to like post: {str(e)}'}), 500
