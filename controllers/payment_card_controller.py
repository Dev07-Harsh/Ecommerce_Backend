from flask import jsonify, request
from models.payment_card import PaymentCard
from models.enums import CardTypeEnum, CardStatusEnum
from common.database import db
from datetime import datetime, timezone
from sqlalchemy import desc

class PaymentCardController:
    @staticmethod
    def add_card(user_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400

            # Validate required fields
            required_fields = ['card_number', 'cvv', 'expiry_month', 'expiry_year', 'card_holder_name', 'card_type']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'status': 'error',
                        'message': f'Missing required field: {field}'
                    }), 400

            # Create new card with only the non-sensitive fields first
            new_card = PaymentCard(
                user_id=user_id,
                card_holder_name=data['card_holder_name'],
                card_type=CardTypeEnum(data['card_type']),
                billing_address_id=data.get('billing_address_id'),
                is_default=data.get('is_default', False),
                status=CardStatusEnum.ACTIVE
            )

            # Set sensitive fields using the model's setter methods
            new_card.set_card_number(data['card_number'])
            new_card.set_cvv(data['cvv'])
            new_card.set_expiry_month(data['expiry_month'])
            new_card.set_expiry_year(data['expiry_year'])

            # If this is the first card or marked as default, update other cards
            if new_card.is_default:
                PaymentCard.query.filter_by(user_id=user_id).update({'is_default': False})

            db.session.add(new_card)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Card added successfully',
                'data': new_card.serialize()
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @staticmethod
    def get_user_cards(user_id):
        try:
            cards = PaymentCard.query.filter_by(
                user_id=user_id,
                status=CardStatusEnum.ACTIVE
            ).order_by(desc(PaymentCard.is_default), desc(PaymentCard.created_at)).all()

            return jsonify({
                'status': 'success',
                'data': [card.serialize() for card in cards]
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @staticmethod
    def get_card(user_id, card_id):
        try:
            card = PaymentCard.query.filter_by(
                user_id=user_id,
                card_id=card_id,
                status=CardStatusEnum.ACTIVE
            ).first()

            if not card:
                return jsonify({
                    'status': 'error',
                    'message': 'Card not found'
                }), 404

            return jsonify({
                'status': 'success',
                'data': card.serialize()
            }), 200

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @staticmethod
    def update_card(user_id, card_id):
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400

            card = PaymentCard.query.filter_by(
                user_id=user_id,
                card_id=card_id,
                status=CardStatusEnum.ACTIVE
            ).first()

            if not card:
                return jsonify({
                    'status': 'error',
                    'message': 'Card not found'
                }), 404

            # Update card details
            if 'card_holder_name' in data:
                card.card_holder_name = data['card_holder_name']
            if 'billing_address_id' in data:
                card.billing_address_id = data['billing_address_id']
            if 'card_number' in data:
                card.card_number = data['card_number']
            if 'cvv' in data:
                card.cvv = data['cvv']
            if 'expiry_month' in data:
                card.expiry_month = data['expiry_month']
            if 'expiry_year' in data:
                card.expiry_year = data['expiry_year']
            if 'is_default' in data:
                if data['is_default']:
                    # Update other cards to not default
                    PaymentCard.query.filter_by(user_id=user_id).update({'is_default': False})
                card.is_default = data['is_default']

            card.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Card updated successfully',
                'data': card.serialize()
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @staticmethod
    def delete_card(user_id, card_id):
        try:
            card = PaymentCard.query.filter_by(
                user_id=user_id,
                card_id=card_id,
                status=CardStatusEnum.ACTIVE
            ).first()

            if not card:
                return jsonify({
                    'status': 'error',
                    'message': 'Card not found'
                }), 404

            # Soft delete
            card.status = CardStatusEnum.DELETED
            card.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Card deleted successfully'
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400

    @staticmethod
    def set_default_card(user_id, card_id):
        try:
            card = PaymentCard.query.filter_by(
                user_id=user_id,
                card_id=card_id,
                status=CardStatusEnum.ACTIVE
            ).first()

            if not card:
                return jsonify({
                    'status': 'error',
                    'message': 'Card not found'
                }), 404

            # Update all cards to not default
            PaymentCard.query.filter_by(user_id=user_id).update({'is_default': False})
            
            # Set selected card as default
            card.is_default = True
            card.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Default card updated successfully',
                'data': card.serialize()
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400 