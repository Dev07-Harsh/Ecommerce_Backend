from flask import jsonify, request
from common.database import db
from models.wishlist_item import WishlistItem
from models.product import Product
from models.product_stock import ProductStock
from models.product_media import ProductMedia
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

class WishlistController:
    @staticmethod
    def get_wishlist(user_id: int):
        """Get all wishlist items for the user"""
        wishlist_items = WishlistItem.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).order_by(WishlistItem.added_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'data': [item.serialize() for item in wishlist_items]
        })

    @staticmethod
    def add_to_wishlist(user_id: int):
        """Add a product to user's wishlist"""
        data = request.get_json()
        
        if not data or 'product_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Product ID is required'
            }), 400

        product_id = data['product_id']
        
        # Check if product exists and is active
        product = Product.query.filter(
            Product.product_id == product_id,
            Product.active_flag == True,
            Product.deleted_at.is_(None)
        ).first()
        
        if not product:
            return jsonify({
                'status': 'error',
                'message': 'Product not found or not available'
            }), 404

        # Check if product is already in wishlist (including previously deleted items)
        existing_item = WishlistItem.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()
        
        try:
            if existing_item:
                if not existing_item.is_deleted:
                    return jsonify({
                        'status': 'error',
                        'message': 'Product is already in your wishlist'
                    }), 400
                else:
                    # Reactivate previously deleted wishlist item
                    existing_item.is_deleted = False
                    existing_item.added_at = datetime.now(timezone.utc)
                    db.session.commit()
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Product added back to wishlist',
                        'data': existing_item.serialize()
                    }), 200
            else:
                # Create new wishlist item
                wishlist_item = WishlistItem.create_from_product(
                    user_id=user_id,
                    product=product
                )
                
                db.session.add(wishlist_item)
                db.session.commit()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Product added to wishlist',
                    'data': wishlist_item.serialize()
                }), 201
            
        except IntegrityError:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Failed to add product to wishlist'
            }), 500

    @staticmethod
    def remove_from_wishlist(user_id: int, wishlist_item_id: int):
        """Remove a product from user's wishlist"""
        wishlist_item = WishlistItem.query.filter_by(
            wishlist_item_id=wishlist_item_id,
            user_id=user_id,
            is_deleted=False
        ).first()
        
        if not wishlist_item:
            return jsonify({
                'status': 'error',
                'message': 'Wishlist item not found'
            }), 404

        try:
            wishlist_item.is_deleted = True
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Product removed from wishlist'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Failed to remove product from wishlist'
            }), 500

    @staticmethod
    def clear_wishlist(user_id: int):
        """Remove all products from user's wishlist"""
        try:
            WishlistItem.query.filter_by(
                user_id=user_id,
                is_deleted=False
            ).update({'is_deleted': True})
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Wishlist cleared successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': 'Failed to clear wishlist'
            }), 500 