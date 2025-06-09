from flask import current_app
from common.database import db
from models.product import Product
from models.product_stock import ProductStock
from sqlalchemy import or_, desc
import logging
from auth.models.models import MerchantProfile
from models.category import Category
from models.brand import Brand

logger = logging.getLogger(__name__)

class MerchantProductStockController:
    @staticmethod
    def get(pid):
        try:
            # Get product with all its details
            product = Product.query.get_or_404(pid)
            
            # Get stock information through the relationship
            stock = product.stock
            
            if not stock:
                stock = ProductStock(product_id=pid)
                db.session.add(stock)
                db.session.commit()
            
            return {
                'product': product.serialize(),
                'stock': stock.serialize(),
                'available': stock.stock_qty > 0,
                'low_stock': stock.stock_qty <= stock.low_stock_threshold
            }
        except Exception as e:
            logger.error(f"Error getting product stock: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def update(pid, data):
        try:
            product = Product.query.get_or_404(pid)
            stock = product.stock
            if not stock:
                stock = ProductStock(product_id=pid)
                db.session.add(stock)
            
            if 'stock_qty' in data:
                stock.stock_qty = data['stock_qty']
            if 'low_stock_threshold' in data:
                stock.low_stock_threshold = data['low_stock_threshold']
            
            db.session.commit()
            
            return {
                'id': product.product_id,
                'name': product.product_name,
                'sku': product.sku,
                'category': product.category.name if product.category else None,
                'brand': product.brand.name if product.brand else None,
                'stock_qty': stock.stock_qty,
                'low_stock_threshold': stock.low_stock_threshold,
                'available': stock.stock_qty > 0,
                'low_stock': stock.stock_qty <= stock.low_stock_threshold,
                'image_url': product.media[0].url if product.media else None
            }
        except Exception as e:
            logger.error(f"Error updating product stock: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def bulk_update(pid, data):
        try:
            if not isinstance(data, list):
                raise ValueError("Data must be a list of stock updates")
            
            product = Product.query.get_or_404(pid)
            results = []
            
            for item in data:
                if not isinstance(item, dict) or 'variant_id' not in item:
                    raise ValueError("Each item must be a dictionary with 'variant_id'")
                
                variant_id = item['variant_id']
                stock_qty = item.get('stock_qty', 0)
                low_stock_threshold = item.get('low_stock_threshold', 0)
                
                # Update variant stock
                variant_stock = ProductStock.query.filter_by(product_id=pid, variant_id=variant_id).first()
                if not variant_stock:
                    variant_stock = ProductStock(product_id=pid, variant_id=variant_id)
                    db.session.add(variant_stock)
                
                variant_stock.stock_qty = stock_qty
                variant_stock.low_stock_threshold = low_stock_threshold
                
                results.append({
                    'variant_id': variant_id,
                    'stock': variant_stock.serialize(),
                    'available': stock_qty > 0,
                    'low_stock': stock_qty <= low_stock_threshold
                })
            
            db.session.commit()
            return results
        except Exception as e:
            logger.error(f"Error bulk updating product stock: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def get_low_stock():
        try:
            low_stock_products = db.session.query(Product, ProductStock).\
                join(ProductStock).\
                filter(ProductStock.stock_qty <= ProductStock.low_stock_threshold).\
                filter(ProductStock.stock_qty > 0).\
                all()
            
            return [{
                'product': product.serialize(),
                'stock': stock.serialize(),
                'available': stock.stock_qty > 0,
                'low_stock': True
            } for product, stock in low_stock_products]
        except Exception as e:
            logger.error(f"Error getting low stock products: {e}")
            raise

    @staticmethod
    def get_inventory_stats(user_id):
        try:
            # First get the merchant profile from user_id
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if not merchant:
                raise ValueError(f"No merchant profile found for user ID {user_id}")

            merchant_id = merchant.id
            logger.info(f"Fetching inventory stats for merchant: {merchant.business_name} (ID: {merchant_id})")

            total_products = Product.query.filter_by(
                merchant_id=merchant_id,
                deleted_at=None,
                approval_status='approved'
            ).count()

            total_stock = db.session.query(db.func.sum(ProductStock.stock_qty)).\
                join(Product).\
                filter(Product.merchant_id == merchant_id).\
                filter(Product.deleted_at == None).\
                filter(Product.approval_status == 'approved').\
                scalar() or 0
            
            low_stock_count = db.session.query(Product).\
                join(ProductStock).\
                filter(Product.merchant_id == merchant_id).\
                filter(Product.deleted_at == None).\
                filter(Product.approval_status == 'approved').\
                filter(ProductStock.stock_qty <= ProductStock.low_stock_threshold).\
                filter(ProductStock.stock_qty > 0).\
                count()
            
            out_of_stock_count = db.session.query(Product).\
                join(ProductStock).\
                filter(Product.merchant_id == merchant_id).\
                filter(Product.deleted_at == None).\
                filter(Product.approval_status == 'approved').\
                filter(ProductStock.stock_qty == 0).\
                count()
            
            return {
                'total_products': total_products,
                'total_stock': total_stock,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count
            }
        except Exception as e:
            logger.error(f"Error getting inventory stats: {e}")
            raise

    @staticmethod
    def get_products(user_id, page=1, per_page=10, search=None, category=None, brand=None, stock_status=None):
        try:
            # First get the merchant profile from user_id
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if not merchant:
                raise ValueError(f"No merchant profile found for user ID {user_id}")

            merchant_id = merchant.id
            logger.info(f"Fetching products for merchant: {merchant.business_name} (ID: {merchant_id})")

            query = Product.query.filter_by(
                merchant_id=merchant_id, 
                deleted_at=None,
                approval_status='approved'
            )
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(or_(
                    Product.product_name.ilike(search_term),
                    Product.sku.ilike(search_term)
                ))
            
            if category:
                # Handle both category ID and slug
                try:
                    category_id = int(category)
                    query = query.filter(Product.category_id == category_id)
                except ValueError:
                    # If category is not a number, treat it as a slug
                    category_obj = Category.query.filter_by(slug=category).first()
                    if category_obj:
                        query = query.filter(Product.category_id == category_obj.category_id)
            
            if brand:
                # Handle both brand ID and slug
                try:
                    brand_id = int(brand)
                    query = query.filter(Product.brand_id == brand_id)
                except ValueError:
                    # If brand is not a number, treat it as a slug
                    brand_obj = Brand.query.filter_by(slug=brand).first()
                    if brand_obj:
                        query = query.filter(Product.brand_id == brand_obj.brand_id)
            
            if stock_status:
                query = query.join(ProductStock)
                if stock_status == 'in_stock':
                    query = query.filter(ProductStock.stock_qty > 0)
                elif stock_status == 'low_stock':
                    query = query.filter(ProductStock.stock_qty <= ProductStock.low_stock_threshold)
                    query = query.filter(ProductStock.stock_qty > 0)
                elif stock_status == 'out_of_stock':
                    query = query.filter(ProductStock.stock_qty == 0)
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination
            products = query.order_by(desc(Product.created_at)).\
                offset((page - 1) * per_page).\
                limit(per_page).\
                all()
            
            # Format products for frontend
            formatted_products = []
            for product in products:
                stock = product.stock
                if not stock:
                    stock = ProductStock(product_id=product.product_id)
                    db.session.add(stock)
                    db.session.commit()
                
                formatted_products.append({
                    'id': product.product_id,
                    'name': product.product_name,
                    'sku': product.sku,
                    'category': {
                        'id': product.category.category_id if product.category else None,
                        'name': product.category.name if product.category else None,
                        'slug': product.category.slug if product.category else None
                    },
                    'brand': {
                        'id': product.brand.brand_id if product.brand else None,
                        'name': product.brand.name if product.brand else None,
                        'slug': product.brand.slug if product.brand else None
                    },
                    'stock_qty': stock.stock_qty if stock else 0,
                    'low_stock_threshold': stock.low_stock_threshold if stock else 0,
                    'available': stock.stock_qty if stock else 0,
                    'image_url': product.media[0].url if product.media else None
                })
            
            return {
                'products': formatted_products,
                'pagination': {
                    'total': total,
                    'current_page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        except Exception as e:
            logger.error(f"Error listing inventory products: {e}")
            db.session.rollback()
            raise 