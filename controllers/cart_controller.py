from flask import jsonify, current_app, request
from models.cart import Cart, CartItem
from models.product import Product
from models.product_stock import ProductStock
from models.product_media import ProductMedia
from common.database import db
from sqlalchemy import and_
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CartController:
    @staticmethod
    def get_cart_items(user_id: int):
        """
        Get all cart items for a user
        """
        try:
            # Get the user's cart
            cart = Cart.query.filter_by(user_id=user_id).first()
            
            if not cart:
                # Create a new cart if it doesn't exist
                cart = Cart(user_id=user_id)
                db.session.add(cart)
                db.session.commit()
                return []

            # Get all cart items with their associated products
            cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
            
            return cart_items
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_cart(user_id: int):
        """
        Get or create a cart for a user
        """
        try:
            cart = Cart.query.filter_by(user_id=user_id).first()
            
            if not cart:
                cart = Cart(user_id=user_id)
                db.session.add(cart)
                db.session.commit()
            
            return cart
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def add_to_cart(user_id: int, product_id: int, quantity: int):
        """
        Add a product to the user's cart
        """
        try:
            cart = CartController.get_cart(user_id)
            product = Product.query.get(product_id)
            
            if not product:
                raise ValueError("Product not found")
            
            # Get product stock first
            product_stock = ProductStock.query.filter_by(product_id=product_id).first()
            
            if not product_stock or product_stock.stock_qty < quantity:
                raise ValueError("Insufficient stock")
            
            # Get product image URL
            product_image = ProductMedia.query.filter_by(
                product_id=product_id,
                type='image'
            ).first()
            
            # Check if product already exists in cart
            cart_item = CartItem.query.filter_by(
                cart_id=cart.cart_id,
                product_id=product_id
            ).first()
            
            if cart_item:
                # Update quantity if product exists
                cart_item.quantity += quantity
            else:
                # Create new cart item if product doesn't exist
                cart_item = CartItem(
                    cart_id=cart.cart_id,
                    product_id=product_id,
                    quantity=quantity,
                    product_name=product.product_name,
                    product_sku=product.sku,
                    product_price=product.selling_price,
                    product_discount_pct=product.discount_pct,
                    product_special_price=product.special_price,
                    product_image_url=product_image.url if product_image else None,
                    product_stock_qty=product_stock.stock_qty if product_stock else 0
                )
                db.session.add(cart_item)
            
            db.session.commit()
            return cart
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_cart_item(cart_item_id: int, quantity: int):
        """
        Update the quantity of a cart item
        """
        try:
            cart_item = CartItem.query.get(cart_item_id)
            
            if not cart_item:
                raise ValueError("Cart item not found")
            
            if quantity <= 0:
                db.session.delete(cart_item)
            else:
                cart_item.quantity = quantity
            
            db.session.commit()
            return cart_item
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def remove_from_cart(cart_item_id: int):
        """
        Remove an item from the cart
        """
        try:
            cart_item = CartItem.query.get(cart_item_id)
            
            if not cart_item:
                raise ValueError("Cart item not found")
            
            db.session.delete(cart_item)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def clear_cart(user_id: int):
        """
        Clear all items from the user's cart
        """
        try:
            cart = Cart.query.filter_by(user_id=user_id).first()
            
            if not cart:
                return
            
            CartItem.query.filter_by(cart_id=cart.cart_id).delete()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_cart_details(user_id):
        """Get detailed cart information"""
        try:
            cart = CartController.get_cart(user_id)
            return True, cart.serialize()

        except Exception as e:
            logger.error(f"Error getting cart details: {str(e)}")
            raise 