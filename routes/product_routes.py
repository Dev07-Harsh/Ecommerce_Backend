from flask import Blueprint, request, jsonify, current_app
from controllers.product_controller import ProductController # Assuming this controller exists and handles some logic
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_cors import cross_origin
from models.recently_viewed import RecentlyViewed
from models.product import Product # Import Product model
from models.variant import Variant # Import Variant model
# Ensure related models for Variant are imported if accessed directly (VariantStock, VariantMedia)
# from models.variant_stock import VariantStock (already implicitly accessed via variant_instance.stock)
# from models.variant_media import VariantMedia (already implicitly accessed via variant_instance.media)
from common.database import db
from datetime import datetime
from sqlalchemy import desc
from http import HTTPStatus # For using standard HTTP status codes

product_bp = Blueprint('product', __name__)

@product_bp.route('/api/products', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_products():
    """
    Get all products with pagination and filtering
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 10, max: 50)
    - sort_by: Field to sort by (default: created_at)
    - order: Sort order (asc/desc, default: desc)
    - category_id: Filter by category
    - brand_id: Filter by brand
    - min_price: Minimum price filter
    - max_price: Maximum price filter
    - search: Search term for product name/description
    """
    if request.method == 'OPTIONS':
        return '', HTTPStatus.OK # Use HTTPStatus
    # Delegate to controller, assuming it handles query params
    return ProductController.get_all_products()

@product_bp.route('/api/products/<int:product_id>', methods=['GET'])
@cross_origin()
def get_product(product_id):
    """Get a single product by ID"""
    return ProductController.get_product(product_id)

@product_bp.route('/api/products/recently-viewed', methods=['GET'])
@jwt_required()
@cross_origin()
def get_recently_viewed():
    """Get recently viewed products for the current user"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            # Although @jwt_required should handle this, good to be explicit
            return jsonify({'message': 'User identity not found in token'}), HTTPStatus.UNAUTHORIZED
            
        # Get the 6 most recently viewed products
        recent_views = RecentlyViewed.query.filter_by(
            user_id=user_id
        ).order_by(
            desc(RecentlyViewed.viewed_at)
        ).limit(6).all()
        
        products_list = [] # Renamed to avoid conflict with Product model
        for view in recent_views:
            # Ensure product exists, is active, and not soft-deleted
            if view.product and view.product.active_flag and not view.product.deleted_at:
                product_dict = view.product.serialize() # Base product serialization

                # Add/Override fields for frontend consistency if needed
                # Note: Your Product.serialize() might already provide most of these.
                # This section might be redundant if Product.serialize() is comprehensive.
                product_dict.update({
                    'id': str(view.product.product_id), # Ensure 'id' is string for consistency
                    'name': view.product.product_name,
                    'price': float(view.product.selling_price),
                    'originalPrice': float(view.product.cost_price),
                    'currency': 'INR', # Consider making currency configurable or from product
                    'stock': 100, # This is placeholder stock, ideally get actual stock
                    'isNew': True, # This should be determined by logic (e.g., creation date)
                    'isBuiltIn': False, # Example field
                    'rating': 0, # Placeholder, should come from reviews aggregation
                    'reviews': [], # Placeholder
                    'sku': view.product.sku # SKU from base product
                })
                
                # Get primary media (assuming ProductController has this helper)
                # If Product.serialize() includes media, this might be redundant
                primary_media = ProductController.get_product_media(view.product.product_id)
                if primary_media and primary_media.get('url'):
                    product_dict['primary_image'] = primary_media['url']
                    product_dict['image'] = primary_media['url'] # Common field name for image
                elif view.product.media: # Fallback to first media from relationship
                    first_media = next((m.url for m in sorted(view.product.media, key=lambda x: x.sort_order) if m.url), None)
                    if first_media:
                        product_dict['primary_image'] = first_media
                        product_dict['image'] = first_media

                products_list.append(product_dict)
        
        return jsonify(products_list), HTTPStatus.OK
        
    except Exception as e:
        current_app.logger.error(f"Error in get_recently_viewed: {str(e)}")
        return jsonify({
            "error": "Failed to fetch recently viewed products",
            "message": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@product_bp.route('/api/products/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Get all product categories"""
    return ProductController.get_categories()

@product_bp.route('/api/products/brands', methods=['GET'])
@cross_origin()
def get_brands():
    """Get all product brands"""
    return ProductController.get_brands()

@product_bp.route('/api/products/<int:product_id>/details', methods=['GET'])
@cross_origin()
def get_product_details(product_id):
    """
    Get detailed product information including media and meta data.
    Also tracks the product view for authenticated users.
    """
    try:
        user_id = None
        try:
            # verify_jwt_in_request is useful if you want to raise an error if token is invalid.
            # If it's truly optional, get_jwt_identity() might return None if no token or invalid.
            verify_jwt_in_request(optional=True) # Ensures token is valid if present
            user_id = get_jwt_identity()
        except Exception as e:
            # Log if there's an issue with token verification itself, but proceed
            current_app.logger.info(f"Optional JWT verification note for product details view: {str(e)}")
            pass # Continue as an anonymous user
        
        if user_id:
            # Using a session for DB operations
            with db.session.begin_nested(): # Or manage session at a higher level
                existing_view = RecentlyViewed.query.filter_by(
                    user_id=user_id,
                    product_id=product_id
                ).first()
                
                if existing_view:
                    existing_view.viewed_at = datetime.utcnow()
                else:
                    new_view = RecentlyViewed(
                        user_id=user_id,
                        product_id=product_id,
                        viewed_at=datetime.utcnow()
                    )
                    db.session.add(new_view)
                db.session.commit() # Commit this specific transaction part
        
        return ProductController.get_product_details(product_id)
        
    except Exception as e:
        db.session.rollback() # Rollback in case of error during DB operations
        current_app.logger.error(f"Error in get_product_details route for product {product_id}: {str(e)}")
        return jsonify({
            "error": "Failed to fetch product details",
            "message": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@product_bp.route('/api/products/<int:product_id>/variants', methods=['GET'])
@cross_origin()
def get_product_variants(product_id):
    """Get all active variants for a specific product, formatted for the frontend."""
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'message': 'Product not found'}), HTTPStatus.NOT_FOUND
        if not product.active_flag or product.deleted_at:
            return jsonify({'message': 'Product is not available'}), HTTPStatus.NOT_FOUND

        variants_data = []
        # Eager load related data if performance becomes an issue with many variants
        # product_variants = Variant.query.options(
        #     db.joinedload(Variant.stock), 
        #     db.joinedload(Variant.media)
        # ).filter_by(product_id=product_id, deleted_at=None).all()

        for variant_instance in product.variants: # Accessing via product.variants relationship
            if variant_instance.deleted_at is not None: # Skip soft-deleted variants
                continue

            # --- Attribute Parsing Logic ---
            # This is crucial. Your Variant.attribute is a single string.
            # We need to parse it into a list of {"name": "...", "value": "..."} objects.
            # Example: If Variant.attribute = "Color:Red,Size:M"
            # Output: [{"name": "Color", "value": "Red"}, {"name": "Size", "value": "M"}]
            # Example: If Variant.attribute = "Red" (and you know it's a color)
            # Output: [{"name": "Color", "value": "Red"}] (frontend might need to know 'Color' is the name)
            # For a robust system, you might have a predefined primary variant attribute name for the category.
            
            parsed_attributes = []
            if variant_instance.attribute:
                try:
                    # Attempt to parse "Name1:Value1,Name2:Value2"
                    attribute_pairs = variant_instance.attribute.split(',')
                    for pair_str in attribute_pairs:
                        if ':' in pair_str:
                            name, value = pair_str.split(':', 1)
                            parsed_attributes.append({'name': name.strip(), 'value': value.strip()})
                        else:
                            # If no colon, assume it's a single value for a default attribute name
                            # You might get this default name from category or product settings.
                            # For now, using a generic name.
                            parsed_attributes.append({'name': 'Variant Type', 'value': pair_str.strip()})
                except Exception as e:
                    current_app.logger.warning(f"Could not parse variant attribute string '{variant_instance.attribute}' for variant {variant_instance.variant_id}. Error: {e}")
                    # Fallback: treat the whole string as a single attribute value
                    parsed_attributes.append({'name': 'Detail', 'value': variant_instance.attribute})
            # --- End Attribute Parsing Logic ---

            variant_info = {
                'variant_id': variant_instance.variant_id,
                'product_id': variant_instance.product_id,
                'sku': variant_instance.sku,
                # Use variant price; fallback to product's selling price if variant price is somehow None
                'price': float(variant_instance.price) if variant_instance.price is not None else float(product.selling_price),
                'attributes': parsed_attributes,
                'stock': 0,  # Default stock
                'media': []  # Default media list
            }

            # Get stock for the variant
            # The Variant.stock relationship is a backref from VariantStock
            if variant_instance.stock: # This accesses the VariantStock instance
                variant_info['stock'] = variant_instance.stock.stock_qty
            
            # Get media for the variant, sorted by primary and display order
            # The Variant.media relationship is a backref from VariantMedia
            if variant_instance.media: # This accesses the list of VariantMedia instances
                variant_media_data = []
                # Sort: primary first, then by display_order
                sorted_media = sorted(
                    [m for m in variant_instance.media if m.deleted_at is None], 
                    key=lambda m: (not m.is_primary, m.display_order)
                )
                for media_item in sorted_media:
                    variant_media_data.append({
                        'media_id': media_item.media_id,
                        'media_url': media_item.media_url,
                        'media_type': media_item.media_type.upper() if isinstance(media_item.media_type, str) else media_item.media_type, # Ensure uppercase string
                        'is_primary': media_item.is_primary,
                        'display_order': media_item.display_order
                    })
                variant_info['media'] = variant_media_data
            
            variants_data.append(variant_info)

        return jsonify(variants_data), HTTPStatus.OK

    except Exception as e:
        current_app.logger.error(f"Error fetching variants for product {product_id}: {str(e)}", exc_info=True)
        return jsonify({'message': 'Failed to retrieve product variants', 'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR