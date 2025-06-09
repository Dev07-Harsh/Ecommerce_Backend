from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from controllers.wishlist_controller import WishlistController
from auth.utils import role_required
from auth.models.models import UserRole
import logging

logger = logging.getLogger(__name__)

wishlist_bp = Blueprint('wishlist', __name__, url_prefix='/api/wishlist')

# Get user's wishlist
@wishlist_bp.route('', methods=['GET'])
@wishlist_bp.route('/', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_wishlist():
    try:
        user_id = get_jwt_identity()
        return WishlistController.get_wishlist(user_id)
    except Exception as e:
        logger.error(f"Error getting wishlist: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# Add product to wishlist
@wishlist_bp.route('', methods=['POST'])
@wishlist_bp.route('/', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value])
def add_to_wishlist():
    try:
        user_id = get_jwt_identity()
        return WishlistController.add_to_wishlist(user_id)
    except Exception as e:
        logger.error(f"Error adding to wishlist: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# Remove product from wishlist
@wishlist_bp.route('/<int:wishlist_item_id>', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.USER.value])
def remove_from_wishlist(wishlist_item_id):
    try:
        user_id = get_jwt_identity()
        return WishlistController.remove_from_wishlist(user_id, wishlist_item_id)
    except Exception as e:
        logger.error(f"Error removing from wishlist: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# Clear entire wishlist
@wishlist_bp.route('/clear', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.USER.value])
def clear_wishlist():
    try:
        user_id = get_jwt_identity()
        return WishlistController.clear_wishlist(user_id)
    except Exception as e:
        logger.error(f"Error clearing wishlist: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400 