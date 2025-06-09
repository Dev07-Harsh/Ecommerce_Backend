from flask import Blueprint, request, jsonify
from controllers.payment_card_controller import PaymentCardController
from models.enums import CardTypeEnum, CardStatusEnum
from auth.utils import role_required
from auth.models.models import UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

logger = logging.getLogger(__name__)

payment_card_bp = Blueprint('payment_card', __name__, url_prefix='/api/payment-cards')

@payment_card_bp.route('', methods=['POST'])
@payment_card_bp.route('/', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value])
def add_card():
    """
    Add a new payment card.
    
    Request Body:
    {
        "card_number": "4111111111111111",
        "cvv": "123",
        "expiry_month": "12",
        "expiry_year": "2025",
        "card_holder_name": "John Doe",
        "card_type": "credit",
        "billing_address_id": 1,
        "is_default": false
    }
    
    Response:
    {
        "status": "success",
        "message": "Card added successfully",
        "data": {
            "card_id": 1,
            "user_id": 1,
            "card_type": "credit",
            "last_four_digits": "1111",
            "card_holder_name": "John Doe",
            "card_brand": "Visa",
            "status": "active",
            "is_default": true,
            "billing_address": {...},
            "last_used_at": null,
            "created_at": "2024-03-14T12:00:00",
            "updated_at": "2024-03-14T12:00:00"
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.add_card(user_id)
    except Exception as e:
        logger.error(f"Error adding card: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@payment_card_bp.route('', methods=['GET'])
@payment_card_bp.route('/', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_user_cards():
    """
    Get all payment cards for the current user.
    
    Response:
    {
        "status": "success",
        "data": [
            {
                "card_id": 1,
                "user_id": 1,
                "card_type": "credit",
                "last_four_digits": "1111",
                "card_holder_name": "John Doe",
                "card_brand": "Visa",
                "status": "active",
                "is_default": true,
                "billing_address": {...},
                "last_used_at": null,
                "created_at": "2024-03-14T12:00:00",
                "updated_at": "2024-03-14T12:00:00"
            }
        ]
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.get_user_cards(user_id)
    except Exception as e:
        logger.error(f"Error getting user cards: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@payment_card_bp.route('/<int:card_id>', methods=['GET'])
@jwt_required()
@role_required([UserRole.USER.value])
def get_card(card_id):
    """
    Get a specific payment card by ID.
    
    Response:
    {
        "status": "success",
        "data": {
            "card_id": 1,
            "user_id": 1,
            "card_type": "credit",
            "last_four_digits": "1111",
            "card_holder_name": "John Doe",
            "card_brand": "Visa",
            "status": "active",
            "is_default": true,
            "billing_address": {...},
            "last_used_at": null,
            "created_at": "2024-03-14T12:00:00",
            "updated_at": "2024-03-14T12:00:00"
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.get_card(user_id, card_id)
    except Exception as e:
        logger.error(f"Error getting card: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@payment_card_bp.route('/<int:card_id>', methods=['PUT'])
@jwt_required()
@role_required([UserRole.USER.value])
def update_card(card_id):
    """
    Update a payment card.
    
    Request Body:
    {
        "card_holder_name": "John Doe",
        "billing_address_id": 1,
        "card_number": "4111111111111111",
        "cvv": "123",
        "expiry_month": "12",
        "expiry_year": "2025",
        "is_default": true
    }
    
    Response:
    {
        "status": "success",
        "message": "Card updated successfully",
        "data": {
            "card_id": 1,
            "user_id": 1,
            "card_type": "credit",
            "last_four_digits": "1111",
            "card_holder_name": "John Doe",
            "card_brand": "Visa",
            "status": "active",
            "is_default": true,
            "billing_address": {...},
            "last_used_at": null,
            "created_at": "2024-03-14T12:00:00",
            "updated_at": "2024-03-14T12:00:00"
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.update_card(user_id, card_id)
    except Exception as e:
        logger.error(f"Error updating card: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@payment_card_bp.route('/<int:card_id>', methods=['DELETE'])
@jwt_required()
@role_required([UserRole.USER.value])
def delete_card(card_id):
    """
    Delete a payment card.
    
    Response:
    {
        "status": "success",
        "message": "Card deleted successfully"
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.delete_card(user_id, card_id)
    except Exception as e:
        logger.error(f"Error deleting card: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@payment_card_bp.route('/<int:card_id>/default', methods=['POST'])
@jwt_required()
@role_required([UserRole.USER.value])
def set_default_card(card_id):
    """
    Set a card as the default payment method.
    
    Response:
    {
        "status": "success",
        "message": "Default card updated successfully",
        "data": {
            "card_id": 1,
            "user_id": 1,
            "card_type": "credit",
            "last_four_digits": "1111",
            "card_holder_name": "John Doe",
            "card_brand": "Visa",
            "status": "active",
            "is_default": true,
            "billing_address": {...},
            "last_used_at": null,
            "created_at": "2024-03-14T12:00:00",
            "updated_at": "2024-03-14T12:00:00"
        }
    }
    """
    try:
        user_id = get_jwt_identity()
        return PaymentCardController.set_default_card(user_id, card_id)
    except Exception as e:
        logger.error(f"Error setting default card: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 