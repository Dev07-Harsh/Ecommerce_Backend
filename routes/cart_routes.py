from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from controllers.cart_controller import CartController
from auth.utils import role_required
from auth.models.models import UserRole
import logging

logger = logging.getLogger(__name__)

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_cart():
    try:
        user_id = get_jwt_identity()
        cart = CartController.get_cart(user_id)
        return jsonify({
            'status': 'success',
            'data': cart.serialize()
        })
    except Exception as e:
        logger.error(f"Error getting cart: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@cart_bp.route('/add', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value])
def add_to_cart():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'product_id' not in data or 'quantity' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400
        
        product_id = data['product_id']
        quantity = data['quantity']
        
        cart = CartController.add_to_cart(user_id, product_id, quantity)
        return jsonify({
            'status': 'success',
            'data': cart.serialize()
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error adding item to cart: {str(e)}'
        }), 500

@cart_bp.route('/update/<int:cart_item_id>', methods=['PUT'])
@jwt_required()
@role_required([UserRole.USER.value])
def update_cart_item(cart_item_id):
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'quantity' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing quantity field'
            }), 400
        
        quantity = data['quantity']
        cart_item = CartController.update_cart_item(cart_item_id, quantity)
        return jsonify({
            'status': 'success',
            'data': cart_item.serialize()
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error updating cart item: {str(e)}'
        }), 500

@cart_bp.route('/remove/<int:cart_item_id>', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.USER.value])
def remove_from_cart(cart_item_id):
    try:
        user_id = get_jwt_identity()
        CartController.remove_from_cart(cart_item_id)
        return jsonify({
            'status': 'success',
            'message': 'Item removed from cart successfully'
        })
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error removing from cart: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error removing item from cart: {str(e)}'
        }), 500

@cart_bp.route('/clear', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.USER.value])
def clear_cart():
    try:
        user_id = get_jwt_identity()
        CartController.clear_cart(user_id)
        return jsonify({
            'status': 'success',
            'message': 'Cart cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing cart: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error clearing cart: {str(e)}'
        }), 500

@cart_bp.route('/items', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_cart_items():
    try:
        user_id = get_jwt_identity()
        cart_items = CartController.get_cart_items(user_id)
        
        # Format the response to match frontend expectations
        formatted_items = [{
            'cart_item_id': item.cart_item_id,
            'product_id': item.product_id,
            'merchant_id': item.product.merchant_id,
            'quantity': item.quantity,
            'product': {
                'name': item.product.product_name,
                'price': float(item.product.selling_price),
                'image_url': item.product_image_url,
                'stock': item.product_stock_qty,
                'is_deleted': item.product.is_deleted if hasattr(item.product, 'is_deleted') else False
            }
        } for item in cart_items]

        return jsonify({
            'status': 'success',
            'data': formatted_items
        }), 200
    except Exception as e:
        logger.error(f"Error getting cart items: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve cart items: {str(e)}'
        }), 500 