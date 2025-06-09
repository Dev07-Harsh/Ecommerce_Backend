# controllers/merchant/product_controller.py

from flask_jwt_extended import get_jwt_identity
from flask import abort
from common.database import db
from models.product import Product
from auth.models.models import MerchantProfile
from datetime import datetime, timezone

class MerchantProductController:
    @staticmethod
    def list_all():
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")
        return Product.query.filter_by(
            merchant_id=merchant.id,
            deleted_at=None
        ).all()

    @staticmethod
    def get(pid):
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")
        return Product.query.filter_by(
            product_id=pid,
            merchant_id=merchant.id
        ).first_or_404()

    @staticmethod
    def create(data):
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        p = Product(
            merchant_id=merchant.id,
            category_id=data['category_id'],
            brand_id=data['brand_id'],
            sku=data['sku'],
            product_name=data['product_name'],
            product_description=data['product_description'],
            cost_price=data['cost_price'],
            selling_price=data['selling_price'],
            discount_pct=data.get('discount_pct', 0),
            special_price=data.get('special_price'),
            special_start=data.get('special_start'),
            special_end=data.get('special_end'),
            approval_status='pending'  # Set initial approval status
        )
        p.save()
        return p

    @staticmethod
    def update(pid, data):
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        p = Product.query.filter_by(
            product_id=pid,
            merchant_id=merchant.id
        ).first_or_404()

        # If product is approved, changing certain fields will require re-approval
        if p.approval_status == 'approved':
            fields_requiring_reapproval = {
                'product_name', 'product_description', 'cost_price', 
                'selling_price', 'special_price', 'special_start', 'special_end'
            }
            if any(field in data for field in fields_requiring_reapproval):
                p.approval_status = 'pending'
                p.approved_at = None
                p.approved_by = None
                p.rejection_reason = None

        for field in (
            'category_id','brand_id','sku','product_name','product_description',
            'cost_price','selling_price','discount_pct','special_price',
            'special_start','special_end','active_flag'
        ):
            if field in data:
                setattr(p, field, data[field])
        db.session.commit()
        return p

    @staticmethod
    def delete(pid):
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        p = Product.query.filter_by(
            product_id=pid,
            merchant_id=merchant.id
        ).first_or_404()

        p.deleted_at = db.func.current_timestamp()
        db.session.commit()
        return p

    @staticmethod
    def approve(pid, admin_id):
        """Approve a product by superadmin."""
        p = Product.query.get_or_404(pid)
        p.approval_status = 'approved'
        p.approved_at = datetime.now(timezone.utc)
        p.approved_by = admin_id
        p.rejection_reason = None
        db.session.commit()
        return p

    @staticmethod
    def reject(pid, admin_id, reason):
        """Reject a product by superadmin."""
        p = Product.query.get_or_404(pid)
        p.approval_status = 'rejected'
        p.approved_at = None
        p.approved_by = None
        p.rejection_reason = reason
        db.session.commit()
        return p

    @staticmethod
    def get_pending_products():
        """Get all products pending approval."""
        return Product.query.filter_by(
            approval_status='pending',
            deleted_at=None
        ).all()

    @staticmethod
    def get_approved_products():
        """Get all approved products."""
        return Product.query.filter_by(
            approval_status='approved',
            deleted_at=None
        ).all()

    @staticmethod
    def get_rejected_products():
        """Get all rejected products."""
        return Product.query.filter_by(
            approval_status='rejected',
            deleted_at=None
        ).all()

    @staticmethod
    def create_variant(parent_id, data):
        """
        Create a variant product from a parent product.
        Required fields in data:
        - sku: unique SKU for the variant
        - stock_qty: initial stock quantity
        - selling_price: variant's selling price
        Optional fields:
        - cost_price: variant's cost price (defaults to parent's cost_price)
        - attributes: dictionary of attribute values
        """
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, "Merchant profile not found")

        # Get parent product
        parent_product = Product.query.filter_by(
            product_id=parent_id,
            merchant_id=merchant.id,
            deleted_at=None
        ).first_or_404()

        # Get parent's stock info for low stock threshold
        parent_stock = parent_product.stock
        if not parent_stock:
            abort(400, "Parent product stock information not found")

        # Check if SKU is unique
        if Product.query.filter_by(sku=data['sku']).first():
            abort(400, "SKU already exists")

        try:
            # Start a transaction
            db.session.begin_nested()

            # Create variant product inheriting most fields from parent
            variant = Product(
                merchant_id=merchant.id,
                category_id=parent_product.category_id,
                brand_id=parent_product.brand_id,
                parent_product_id=parent_id,
                sku=data['sku'],
                product_name=parent_product.product_name,
                product_description=parent_product.product_description,
                cost_price=data.get('cost_price', parent_product.cost_price),
                selling_price=data['selling_price'],
                discount_pct=parent_product.discount_pct,
                special_price=parent_product.special_price,
                special_start=parent_product.special_start,
                special_end=parent_product.special_end,
                active_flag=parent_product.active_flag,
                approval_status='pending'  # Variants need approval like new products
            )

            # Save the variant to get its ID
            db.session.add(variant)
            db.session.flush()

            # Create product stock record
            from models.product_stock import ProductStock
            stock = ProductStock(
                product_id=variant.product_id,
                stock_qty=data['stock_qty'],
                low_stock_threshold=parent_stock.low_stock_threshold  # Use parent's threshold
            )
            db.session.add(stock)

            # Copy product meta from parent product
            if parent_product.meta:
                from models.product_meta import ProductMeta
                variant_meta = ProductMeta(
                    product_id=variant.product_id,
                    short_desc=parent_product.meta.short_desc,
                    full_desc=parent_product.meta.full_desc,
                    meta_title=parent_product.meta.meta_title,
                    meta_desc=parent_product.meta.meta_desc,
                    meta_keywords=parent_product.meta.meta_keywords
                )
                db.session.add(variant_meta)

            # Copy product shipping from parent product
            if parent_product.shipping:
                from models.product_shipping import ProductShipping
                variant_shipping = ProductShipping(
                    product_id=variant.product_id,
                    length_cm=parent_product.shipping.length_cm,
                    width_cm=parent_product.shipping.width_cm,
                    height_cm=parent_product.shipping.height_cm,
                    weight_kg=parent_product.shipping.weight_kg
                )
                db.session.add(variant_shipping)

            # Handle attributes if provided
            if 'attributes' in data and isinstance(data['attributes'], dict):
                from models.product_attribute import ProductAttribute
                from models.attribute import Attribute

                for attr_id, attr_value in data['attributes'].items():
                    # Get the attribute
                    attribute = Attribute.query.get(attr_id)
                    if not attribute:
                        continue

                    # Create product attribute
                    product_attr = ProductAttribute(
                        product_id=variant.product_id,
                        attribute_id=attribute.attribute_id
                    )

                    # Set the appropriate value based on attribute type
                    if attribute.input_type in ['select', 'multiselect']:
                        product_attr.value_code = str(attr_value)
                    elif attribute.input_type == 'number':
                        product_attr.value_number = float(attr_value)
                    else:  # text or other types
                        product_attr.value_text = str(attr_value)

                    db.session.add(product_attr)

            # Commit the transaction
            db.session.commit()
            return variant

        except Exception as e:
            db.session.rollback()
            abort(500, f"Failed to create variant: {str(e)}")
