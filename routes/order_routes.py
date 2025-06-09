from flask import Blueprint, request, jsonify
from controllers.order_controller import OrderController
from models.enums import OrderStatusEnum, PaymentStatusEnum, PaymentMethodEnum
from auth.utils import role_required
from auth.models.models import UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.order import Order, OrderItem
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from common.database import db
from flask_cors import cross_origin
import logging

logger = logging.getLogger(__name__)

order_bp = Blueprint('order', __name__, url_prefix='/api/orders')

@order_bp.route('', methods=['POST'])
@order_bp.route('/', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value])
def create_order():
    """
    Create a new order.
    
    Request Body:
    {
        "items": [
            {
                "product_id": 1,
                "merchant_id": 1,
                "product_name_at_purchase": "Product Name",
                "sku_at_purchase": "SKU123",
                "quantity": 2,
                "unit_price_at_purchase": "10.00",
                "item_subtotal_amount": "20.00",
                "final_price_for_item": "20.00"
            }
        ],
        "subtotal_amount": "20.00",
        "discount_amount": "0.00",
        "tax_amount": "2.00",
        "shipping_amount": "5.00",
        "total_amount": "27.00",
        "currency": "USD",
        "payment_method": "credit_card",  # Must be one of: credit_card, debit_card, cash_on_delivery
        "payment_card_id": 1,  # Required if payment_method is credit_card or debit_card
        "shipping_address_id": 1,
        "billing_address_id": 1,
        "shipping_method_name": "Standard Shipping",
        "customer_notes": "Please deliver in the evening",
        "internal_notes": "Handle with care"
    }
    
    Response:
    {
        "status": "success",
        "data": {
            "order_id": "123",
            "user_id": 1,
            "order_status": "processing",
            "payment_status": "paid",
            "total_amount": "27.00",
            "items": [...],
            "status_history": [...]
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        order_data = request.get_json()
        
        if not order_data:
            return jsonify({
                'status': 'error',
                'message': 'No order data provided'
            }), 400

        # Validate payment method
        payment_method = order_data.get('payment_method')
        if not payment_method:
            return jsonify({
                'status': 'error',
                'message': 'Payment method is required'
            }), 400

        try:
            # Validate that the payment method is a valid enum value
            payment_method_enum = PaymentMethodEnum(payment_method)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f'Invalid payment method. Must be one of: {[method.value for method in PaymentMethodEnum]}'
            }), 400

        # Validate payment card for card payments
        if payment_method_enum in [PaymentMethodEnum.CREDIT_CARD, PaymentMethodEnum.DEBIT_CARD]:
            if not order_data.get('payment_card_id'):
                return jsonify({
                    'status': 'error',
                    'message': 'Payment card ID is required for card payments'
                }), 400
            
        result = OrderController.create_order(user_id, order_data)
        return jsonify({
            'status': 'success',
            'data': result
        }), 201
        
    except ValueError as ve:
        logger.error(f"Validation error creating order: {str(ve)}")
        return jsonify({
            'status': 'error',
            'message': str(ve)
        }), 400
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@order_bp.route('/<string:order_id>', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value, UserRole.ADMIN.value, UserRole.MERCHANT.value])
def get_order(order_id):
    try:
        user_id = get_jwt_identity()
        order = OrderController.get_order(order_id)
        
        if not order:
            return jsonify({
                'status': 'error',
                'message': 'Order not found'
            }), 404
            
        # Check if user has permission to view this order
        if user_id != order['user_id'] and not request.user.is_admin and not request.user.is_merchant:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized access'
            }), 403
            
        return jsonify({
            'status': 'success',
            'data': order
        })
        
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@order_bp.route('/user', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_user_orders():
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        result = OrderController.get_user_orders(user_id, page, per_page, status)
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@order_bp.route('/<string:order_id>/status', methods=['PUT'])
@jwt_required()
@role_required([UserRole.USER.value, UserRole.ADMIN.value, UserRole.MERCHANT.value])
def update_order_status(order_id):
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Status is required'
            }), 400
            
        try:
            new_status = OrderStatusEnum(data['status'])
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid order status'
            }), 400
            
        result = OrderController.update_order_status(
            order_id,
            new_status,
            get_jwt_identity(),
            data.get('notes')
        )
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Order not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@order_bp.route('/<string:order_id>/payment', methods=['PUT'])
@jwt_required()
@role_required([UserRole.USER.value, UserRole.ADMIN.value])
def update_payment_status(order_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Validate required fields
        if 'payment_status' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Payment status is required'
            }), 400

        # Validate payment status
        try:
            payment_status = PaymentStatusEnum(data['payment_status'])
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f'Invalid payment status. Must be one of: {[status.value for status in PaymentStatusEnum]}'
            }), 400

        # Get the current user
        user_id = get_jwt_identity()
        
        # Get the order to check ownership
        order = OrderController.get_order(order_id)
        if not order:
            return jsonify({
                'status': 'error',
                'message': f'Order not found with ID: {order_id}'
            }), 404

        # Check if user has permission to update this order
        if str(order['user_id']) != str(user_id) and not request.user.is_admin:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized to update this order'
            }), 403

        # Update payment status
        try:
            result = OrderController.update_payment_status(
                order_id,
                payment_status,
                data.get('transaction_id'),
                data.get('gateway_name')
            )
            
            return jsonify({
                'status': 'success',
                'data': result
            })
            
        except ValueError as ve:
            return jsonify({
                'status': 'error',
                'message': str(ve)
            }), 404
        except Exception as e:
            logger.error(f"Error updating payment status: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"Error in update_payment_status route: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500

@order_bp.route('/<string:order_id>/cancel', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value, UserRole.ADMIN.value])
def cancel_order(order_id):
    try:
        data = request.get_json()
        result = OrderController.cancel_order(
            order_id,
            get_jwt_identity(),
            data.get('notes') if data else None
        )
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Order not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except ValueError as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Admin and Merchant routes
@order_bp.route('/admin', methods=['GET'])
@jwt_required()
@role_required([UserRole.ADMIN.value, UserRole.MERCHANT.value])
def get_all_orders():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        merchant_id = request.args.get('merchant_id')
        
        # If user is merchant, only show their orders
        if request.user.is_merchant:
            merchant_id = request.user.merchant_profile.id
        
        result = OrderController.get_all_orders(page, per_page, status, merchant_id)
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Error getting all orders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@order_bp.route('/statistics/trendy-products', methods=['GET'])
@cross_origin()
def get_trendy_products():
    """
    Get statistics for trendy products based on order history
    ---
    tags:
      - Orders
    parameters:
      - in: query
        name: days
        type: integer
        required: false
        default: 30
        description: Number of days to look back for orders
      - in: query
        name: limit
        type: integer
        required: false
        default: 10
        description: Maximum number of products to return
    responses:
      200:
        description: List of trendy products with their order statistics
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                  total_ordered:
                    type: integer
                  order_count:
                    type: integer
      500:
        description: Internal server error
    """
    try:
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        # Calculate the date to look back from
        lookback_date = datetime.utcnow() - timedelta(days=days)
        
        # Query to get product statistics
        product_stats = db.session.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_ordered'),
            func.count(OrderItem.order_id).label('order_count')
        ).join(
            OrderItem.order
        ).filter(
            OrderItem.product_id.isnot(None),
            Order.order_status == 'completed',
            Order.order_date >= lookback_date
        ).group_by(
            OrderItem.product_id
        ).order_by(
            desc('total_ordered')
        ).limit(limit).all()
        
        # Format the response
        result = [{
            'product_id': stat[0],
            'total_ordered': stat[1],
            'order_count': stat[2]
        } for stat in product_stats]
        
        return jsonify({
            'status': 'success',
            'data': {
                'products': result,
                'period_days': days,
                'total_products': len(result)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting trendy products statistics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 