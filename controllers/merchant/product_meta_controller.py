from flask import abort
from common.database import db
from models.product_meta import ProductMeta
from models.product import Product
from auth.models.models import MerchantProfile
from flask_jwt_extended import get_jwt_identity

class MerchantProductMetaController:
    @staticmethod
    def get(pid):
        """Get meta data for a product."""
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        # Check if product exists and belongs to merchant
        product = Product.query.filter_by(
            product_id=pid,
            merchant_id=merchant.id,
            deleted_at=None
        ).first_or_404()

        # Get or create meta data
        meta = ProductMeta.query.get(pid)
        if not meta:
            meta = ProductMeta(product_id=pid)
            db.session.add(meta)
            db.session.commit()

        return meta

    @staticmethod
    def upsert(pid, data):
        """Create or update meta data for a product."""
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        # Check if product exists and belongs to merchant
        product = Product.query.filter_by(
            product_id=pid,
            merchant_id=merchant.id,
            deleted_at=None
        ).first_or_404()

        # Get or create meta data
        meta = ProductMeta.query.get(pid)
        if not meta:
            meta = ProductMeta(product_id=pid)
            db.session.add(meta)

        # Update meta data
        meta.short_desc = data.get('short_desc', meta.short_desc)
        meta.full_desc = data.get('full_desc', meta.full_desc)
        meta.meta_title = data.get('meta_title', meta.meta_title)
        meta.meta_desc = data.get('meta_desc', meta.meta_desc)
        meta.meta_keywords = data.get('meta_keywords', meta.meta_keywords)

        db.session.commit()
        return meta
