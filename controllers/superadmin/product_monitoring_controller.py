from datetime import datetime
from common.database import db
from models.product import Product
from models.product_media import ProductMedia
from models.product_meta import ProductMeta
from models.brand import Brand
from models.category import Category
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

class ProductMonitoringController:
    @staticmethod
    def get_pending_products():
        """Get all pending products with their related data"""
        products = Product.query.filter(
            and_(
                Product.approval_status == 'pending',
                Product.deleted_at.is_(None)
            )
        ).options(
            joinedload(Product.media),
            joinedload(Product.meta),
            joinedload(Product.brand),
            joinedload(Product.category)
        ).all()
        return products

    @staticmethod
    def get_approved_products():
        """Get all approved products with their related data"""
        products = Product.query.filter(
            and_(
                Product.approval_status == 'approved',
                Product.deleted_at.is_(None)
            )
        ).options(
            joinedload(Product.media),
            joinedload(Product.meta),
            joinedload(Product.brand),
            joinedload(Product.category)
        ).all()
        return products

    @staticmethod
    def get_rejected_products():
        """Get all rejected products with their related data"""
        products = Product.query.filter(
            and_(
                Product.approval_status == 'rejected',
                Product.deleted_at.is_(None)
            )
        ).options(
            joinedload(Product.media),
            joinedload(Product.meta),
            joinedload(Product.brand),
            joinedload(Product.category)
        ).all()
        return products

    @staticmethod
    def approve_product(product_id, admin_id):
        """Approve a product"""
        product = Product.query.get_or_404(product_id)
        product.approval_status = 'approved'
        product.approved_at = datetime.utcnow()
        product.approved_by = admin_id
        product.rejection_reason = None

        db.session.commit()
        return product

    @staticmethod
    def reject_product(product_id, admin_id, reason):
        """Reject a product with a reason"""
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is required")

        product = Product.query.get_or_404(product_id)
        product.approval_status = 'rejected'
        product.approved_at = datetime.utcnow()
        product.approved_by = admin_id
        product.rejection_reason = reason.strip()

        db.session.commit()
        return product

    @staticmethod
    def get_product_details(product_id):
        """Get detailed information about a specific product"""
        product = Product.query.options(
            joinedload(Product.media),
            joinedload(Product.meta),
            joinedload(Product.brand),
            joinedload(Product.category)
        ).get_or_404(product_id)

        return {
            'product': {
                **product.serialize(),
                'cost_price': float(product.cost_price),
                'selling_price': float(product.selling_price)
            },
            'media': [media.serialize() for media in product.media] if product.media else [],
            'meta': product.meta.serialize() if product.meta else None,
            'brand': product.brand.serialize() if product.brand else None,
            'category': product.category.serialize() if product.category else None
        } 