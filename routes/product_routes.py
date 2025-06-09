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
    ---
    tags:
      - Products
    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Items per page (max 50)
      - in: query
        name: sort_by
        type: string
        required: false
        default: created_at
        description: Field to sort by
      - in: query
        name: order
        type: string
        required: false
        default: desc
        enum: [asc, desc]
        description: Sort order
      - in: query
        name: category_id
        type: integer
        required: false
        description: Filter by category
      - in: query
        name: brand_id
        type: integer
        required: false
        description: Filter by brand
      - in: query
        name: min_price
        type: number
        required: false
        description: Minimum price filter
      - in: query
        name: max_price
        type: number
        required: false
        description: Maximum price filter
      - in: query
        name: search
        type: string
        required: false
        description: Search term for product name/description
    responses:
      200:
        description: List of products retrieved successfully
        schema:
          type: object
          properties:
            items:
              type: array
              items:
                type: object
                properties:
                  product_id:
                    type: integer
                  product_name:
                    type: string
                  sku:
                    type: string
                  cost_price:
                    type: number
                    format: float
                  selling_price:
                    type: number
                    format: float
                  media:
                    type: array
                    items:
                      type: object
                      properties:
                        url:
                          type: string
                        type:
                          type: string
            total:
              type: integer
            page:
              type: integer
            per_page:
              type: integer
            pages:
              type: integer
      500:
        description: Internal server error
    """
    if request.method == 'OPTIONS':
        return '', HTTPStatus.OK # Use HTTPStatus
    # Delegate to controller, assuming it handles query params
    return ProductController.get_all_products()

@product_bp.route('/api/products/<int:product_id>', methods=['GET'])
@cross_origin()
def get_product(product_id):
    """
    Get a single product by ID
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: ID of the product to retrieve
    responses:
      200:
        description: Product details retrieved successfully
        schema:
          type: object
          properties:
            product_id:
              type: integer
            product_name:
              type: string
            sku:
              type: string
            cost_price:
              type: number
              format: float
            selling_price:
              type: number
              format: float
            media:
              type: array
              items:
                type: object
                properties:
                  url:
                    type: string
                  type:
                    type: string
            brand:
              type: object
              properties:
                brand_id:
                  type: integer
                name:
                  type: string
            category:
              type: object
              properties:
                category_id:
                  type: integer
                name:
                  type: string
      404:
        description: Product not found
      500:
        description: Internal server error
    """
    return ProductController.get_product(product_id)

@product_bp.route('/api/products/recently-viewed', methods=['GET'])
@jwt_required()
@cross_origin()
def get_recently_viewed():
    """
    Get recently viewed products for the current user
    ---
    tags:
      - Products
    security:
      - Bearer: []
    responses:
      200:
        description: List of recently viewed products retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              name:
                type: string
              price:
                type: number
                format: float
              originalPrice:
                type: number
                format: float
              currency:
                type: string
              stock:
                type: integer
              isNew:
                type: boolean
              isBuiltIn:
                type: boolean
              rating:
                type: number
                format: float
              reviews:
                type: array
                items:
                  type: object
              sku:
                type: string
              primary_image:
                type: string
              image:
                type: string
      401:
        description: Unauthorized - JWT token missing or invalid
      500:
        description: Internal server error
    """
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
                    'currency': 'INR',
                    'stock': 100,
                    'isNew': True,
                    'isBuiltIn': False,
                    'rating': 0,
                    'reviews': [],
                    'sku': view.product.sku if hasattr(view.product, 'sku') else None
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
    """
    Get all product categories
    ---
    tags:
      - Products
    responses:
      200:
        description: List of categories retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              category_id:
                type: integer
              name:
                type: string
              slug:
                type: string
              parent_id:
                type: integer
                nullable: true
      500:
        description: Internal server error
    """
    return ProductController.get_categories()

@product_bp.route('/api/products/brands', methods=['GET'])
@cross_origin()
def get_brands():
    """
    Get all product brands
    ---
    tags:
      - Products
    responses:
      200:
        description: List of brands retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              brand_id:
                type: integer
              name:
                type: string
              slug:
                type: string
              icon_url:
                type: string
      500:
        description: Internal server error
    """
    return ProductController.get_brands()

@product_bp.route('/api/products/<int:product_id>/details', methods=['GET'])
@cross_origin()
def get_product_details(product_id):
    """
    Get detailed product information including media and meta data
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: ID of the product to retrieve
    responses:
      200:
        description: Detailed product information retrieved successfully
        schema:
          type: object
          properties:
            product_id:
              type: integer
            product_name:
              type: string
            sku:
              type: string
            cost_price:
              type: number
              format: float
            selling_price:
              type: number
              format: float
            media:
              type: array
              items:
                type: object
                properties:
                  url:
                    type: string
                  type:
                    type: string
            meta:
              type: object
              properties:
                short_desc:
                  type: string
                full_desc:
                  type: string
            brand:
              type: object
              properties:
                brand_id:
                  type: integer
                name:
                  type: string
            category:
              type: object
              properties:
                category_id:
                  type: integer
                name:
                  type: string
      404:
        description: Product not found
      500:
        description: Internal server error
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
        }), 500

@product_bp.route('/api/products/brand/<string:brand_slug>', methods=['GET'])
@cross_origin()
def get_products_by_brand(brand_slug):
    """
    Get parent products filtered by brand slug (excludes product variants)
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: brand_slug
        type: string
        required: true
        description: Slug of the brand to filter by
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Items per page (max 50)
      - in: query
        name: sort_by
        type: string
        required: false
        default: created_at
        description: Field to sort by
      - in: query
        name: order
        type: string
        required: false
        default: desc
        enum: [asc, desc]
        description: Sort order
      - in: query
        name: min_price
        type: number
        required: false
        description: Minimum price filter
      - in: query
        name: max_price
        type: number
        required: false
        description: Maximum price filter
      - in: query
        name: search
        type: string
        required: false
        description: Search term for product name/description
    responses:
      200:
        description: List of parent products for the brand retrieved successfully (excludes variants)
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  price:
                    type: number
                    format: float
                  originalPrice:
                    type: number
                    format: float
                  primary_image:
                    type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                pages:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                has_next:
                  type: boolean
                has_prev:
                  type: boolean
            brand:
              type: object
              properties:
                brand_id:
                  type: integer
                name:
                  type: string
                slug:
                  type: string
                icon_url:
                  type: string
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    return ProductController.get_products_by_brand(brand_slug)

@product_bp.route('/api/products/category/<int:category_id>', methods=['GET'])
@cross_origin()
def get_products_by_category(category_id):
    """
    Get parent products filtered by category ID (excludes product variants)
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: category_id
        type: integer
        required: true
        description: ID of the category to filter by
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Items per page (max 50)
      - in: query
        name: sort_by
        type: string
        required: false
        default: created_at
        description: Field to sort by
      - in: query
        name: order
        type: string
        required: false
        default: desc
        enum: [asc, desc]
        description: Sort order
      - in: query
        name: min_price
        type: number
        required: false
        description: Minimum price filter
      - in: query
        name: max_price
        type: number
        required: false
        description: Maximum price filter
      - in: query
        name: search
        type: string
        required: false
        description: Search term for product name/description
      - in: query
        name: include_children
        type: boolean
        required: false
        default: true
        description: Whether to include products from child categories
    responses:
      200:
        description: List of parent products for the category retrieved successfully (excludes variants)
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  price:
                    type: number
                    format: float
                  originalPrice:
                    type: number
                    format: float
                  primary_image:
                    type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                pages:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                has_next:
                  type: boolean
                has_prev:
                  type: boolean
            category:
              type: object
              properties:
                category_id:
                  type: integer
                name:
                  type: string
                slug:
                  type: string
                icon_url:
                  type: string
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    return ProductController.get_products_by_category(category_id)

@product_bp.route('/api/products/<int:product_id>/variants', methods=['GET'])
@cross_origin()
def get_product_variants(product_id):
    """
    Get all variants for a parent product
    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: ID of the parent product
    responses:
      200:
        description: List of product variants retrieved successfully
        schema:
          type: object
          properties:
            variants:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  price:
                    type: number
                    format: float
                  originalPrice:
                    type: number
                    format: float
                  primary_image:
                    type: string
                  isVariant:
                    type: boolean
                  parentProductId:
                    type: string
            total:
              type: integer
      404:
        description: Parent product not found
      500:
        description: Internal server error
    """
    return ProductController.get_product_variants(product_id)

@product_bp.route('/api/products/new', methods=['GET'])
@cross_origin()
def get_new_products():
    """
    Get products that were added within the last week (excluding variants)
    ---
    tags:
      - Products
    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Items per page (max 50)
    responses:
      200:
        description: List of new products retrieved successfully (excluding variants)
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  description:
                    type: string
                  price:
                    type: number
                    format: float
                  originalPrice:
                    type: number
                    format: float
                  stock:
                    type: integer
                  isNew:
                    type: boolean
                  isBuiltIn:
                    type: boolean
                  primary_image:
                    type: string
                  image:
                    type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                pages:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                has_next:
                  type: boolean
                has_prev:
                  type: boolean
      500:
        description: Internal server error
    """
    return ProductController.get_new_products()

@product_bp.route('/api/products/trendy-deals', methods=['GET'])
@cross_origin()
def get_trendy_deals():
    """
    Get products that have been ordered the most (trendy deals)
    ---
    tags:
      - Products
    parameters:
      - in: query
        name: page
        type: integer
        required: false
        default: 1
        description: Page number
      - in: query
        name: per_page
        type: integer
        required: false
        default: 10
        description: Items per page (max 50)
    responses:
      200:
        description: List of trendy products retrieved successfully
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  description:
                    type: string
                  price:
                    type: number
                    format: float
                  originalPrice:
                    type: number
                    format: float
                  stock:
                    type: integer
                  isNew:
                    type: boolean
                  isBuiltIn:
                    type: boolean
                  orderCount:
                    type: integer
                  primary_image:
                    type: string
                  image:
                    type: string
                  currency:
                    type: string
                  category:
                    type: object
                    properties:
                      category_id:
                        type: integer
                      name:
                        type: string
                  brand:
                    type: object
                    properties:
                      brand_id:
                        type: integer
                      name:
                        type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                pages:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                has_next:
                  type: boolean
                has_prev:
                  type: boolean
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
            products:
              type: array
              items: {}
            pagination:
              type: object
              properties:
                total:
                  type: integer
                pages:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                has_next:
                  type: boolean
                has_prev:
                  type: boolean
    """
    try:
        return ProductController.get_trendy_deals()
    except Exception as e:
        print(f"Error in get_trendy_deals route: {str(e)}")
        return jsonify({
            "error": "Failed to fetch trendy deals",
            "message": str(e),
            "products": [],
            "pagination": {
                "total": 0,
                "pages": 0,
                "current_page": 1,
                "per_page": 10,
                "has_next": False,
                "has_prev": False
            }
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