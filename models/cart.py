from datetime import datetime
from common.database import db, BaseModel
from models.product import Product
from models.product_stock import ProductStock
from models.product_shipping import ProductShipping
from models.product_media import ProductMedia
from sqlalchemy.orm import foreign
from decimal import Decimal

class Cart(BaseModel):
    __tablename__ = 'carts'

    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    items = db.relationship('CartItem', backref='cart', cascade='all, delete-orphan')
    user = db.relationship('User', back_populates='cart', overlaps="carts")

    def serialize(self):
        return {
            'cart_id': self.cart_id,
            'user_id': self.user_id,
            'items': [item.serialize() for item in self.items if not item.is_deleted],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }

class CartItem(BaseModel):
    __tablename__ = 'cart_items'

    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.cart_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    
    # Store product details at time of adding to cart
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(50), nullable=False)
    product_price = db.Column(db.Numeric(10, 2), nullable=False)  # Store the price at time of adding
    product_discount_pct = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    product_special_price = db.Column(db.Numeric(10, 2), nullable=True)
    product_image_url = db.Column(db.String(255), nullable=True)
    product_stock_qty = db.Column(db.Integer, nullable=False)
    
    # Shipping details
    shipping_weight_kg = db.Column(db.Numeric(10, 2), nullable=True)
    shipping_length_cm = db.Column(db.Numeric(10, 2), nullable=True)
    shipping_width_cm = db.Column(db.Numeric(10, 2), nullable=True)
    shipping_height_cm = db.Column(db.Numeric(10, 2), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships - keep these for reference but we'll use stored values
    product = db.relationship('Product', back_populates='cart_items')
    product_stock = db.relationship(
        'ProductStock',
        primaryjoin="and_(foreign(CartItem.product_id)==ProductStock.product_id)",
        uselist=False,
        overlaps="cart_items,product",
        viewonly=True
    )
    product_shipping = db.relationship(
        'ProductShipping',
        primaryjoin="and_(foreign(CartItem.product_id)==ProductShipping.product_id)",
        uselist=False,
        overlaps="cart_items,product,product_stock",
        viewonly=True
    )

    @classmethod
    def create_from_product(cls, cart_id, product, quantity):
        """Create a cart item from a product, storing all relevant details"""
        # Get the first product image
        main_image = next((media.url for media in product.media if media.type.value == 'image'), None) if product.media else None
        
        # Get stock quantity
        stock = ProductStock.query.filter_by(product_id=product.product_id).first()
        stock_qty = stock.stock_qty if stock else 0
        
        # Get shipping details
        shipping = ProductShipping.query.filter_by(product_id=product.product_id).first()
        
        return cls(
            cart_id=cart_id,
            product_id=product.product_id,
            quantity=quantity,
            product_name=product.product_name,
            product_sku=product.sku,
            product_price=product.selling_price,
            product_discount_pct=product.discount_pct,
            product_special_price=product.special_price,
            product_image_url=main_image,
            product_stock_qty=stock_qty,
            shipping_weight_kg=shipping.weight_kg if shipping else None,
            shipping_length_cm=shipping.length_cm if shipping else None,
            shipping_width_cm=shipping.width_cm if shipping else None,
            shipping_height_cm=shipping.height_cm if shipping else None
        )

    def serialize(self):
        return {
            'cart_item_id': self.cart_item_id,
            'cart_id': self.cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'product': {
                'name': self.product_name,
                'sku': self.product_sku,
                'price': float(self.product_price),
                'discount_pct': float(self.product_discount_pct),
                'special_price': float(self.product_special_price) if self.product_special_price else None,
                'image_url': self.product_image_url,
                'stock': self.product_stock_qty,
                'shipping': {
                    'weight_kg': str(self.shipping_weight_kg) if self.shipping_weight_kg else None,
                    'dimensions': {
                        'length_cm': str(self.shipping_length_cm) if self.shipping_length_cm else None,
                        'width_cm': str(self.shipping_width_cm) if self.shipping_width_cm else None,
                        'height_cm': str(self.shipping_height_cm) if self.shipping_height_cm else None
                    }
                } if self.shipping_weight_kg else None
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        } 