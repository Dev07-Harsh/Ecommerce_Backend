from datetime import datetime, timezone
from common.database import db, BaseModel
from models.product import Product
from models.product_stock import ProductStock
from models.product_media import ProductMedia
from decimal import Decimal

class WishlistItem(BaseModel):
    __tablename__ = 'wishlist_items'

    wishlist_item_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id', ondelete='CASCADE'), nullable=False)
    
    # Store product details at time of adding to wishlist
    product_name = db.Column(db.String(255), nullable=False)
    product_sku = db.Column(db.String(50), nullable=False)
    product_price = db.Column(db.Numeric(10, 2), nullable=False)
    product_discount_pct = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    product_special_price = db.Column(db.Numeric(10, 2), nullable=True)
    product_image_url = db.Column(db.String(255), nullable=True)
    product_stock_qty = db.Column(db.Integer, nullable=False)
    
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships - keep these for reference but we'll use stored values
    user = db.relationship('User', back_populates='wishlist_items')
    product = db.relationship('Product', back_populates='wishlist_items')
    product_stock = db.relationship(
        'ProductStock',
        primaryjoin="and_(foreign(WishlistItem.product_id)==ProductStock.product_id)",
        uselist=False,
        overlaps="wishlist_items,product",
        viewonly=True
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_user_product_wishlist'),
    )

    @classmethod
    def create_from_product(cls, user_id, product):
        """Create a wishlist item from a product, storing all relevant details"""
        # Get the first product image
        main_image = next((media.url for media in product.media if media.type.value == 'image'), None) if product.media else None
        
        # Get stock quantity
        stock = ProductStock.query.filter_by(product_id=product.product_id).first()
        stock_qty = stock.stock_qty if stock else 0
        
        return cls(
            user_id=user_id,
            product_id=product.product_id,
            product_name=product.product_name,
            product_sku=product.sku,
            product_price=product.selling_price,
            product_discount_pct=product.discount_pct,
            product_special_price=product.special_price,
            product_image_url=main_image,
            product_stock_qty=stock_qty
        )

    def __repr__(self):
        return f"<WishlistItem id={self.wishlist_item_id} user={self.user_id} product={self.product_id}>"

    def serialize(self):
        return {
            "wishlist_item_id": self.wishlist_item_id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product": {
                "name": self.product_name,
                "sku": self.product_sku,
                "price": float(self.product_price),
                "discount_pct": float(self.product_discount_pct),
                "special_price": float(self.product_special_price) if self.product_special_price else None,
                "image_url": self.product_image_url,
                "stock": self.product_stock_qty
            },
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted
        }