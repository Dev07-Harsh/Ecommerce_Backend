from flask import Blueprint, request, jsonify
from controllers.product_controller import ProductController
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from flask_cors import cross_origin
from models.recently_viewed import RecentlyViewed
from common.database import db
from datetime import datetime
from sqlalchemy import desc

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
        return '', 200
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
            return jsonify([]), 200
            
        # Get the 6 most recently viewed products
        recent_views = RecentlyViewed.query.filter_by(
            user_id=user_id
        ).order_by(
            desc(RecentlyViewed.viewed_at)
        ).limit(6).all()
        
        # Get the product details for each view
        products = []
        for view in recent_views:
            if view.product and view.product.active_flag and not view.product.deleted_at:
                product_dict = view.product.serialize()
                # Add frontend-specific fields
                product_dict.update({
                    'id': str(view.product.product_id),
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
                
                # Get primary media
                media = ProductController.get_product_media(view.product.product_id)
                if media:
                    product_dict['primary_image'] = media['url']
                    product_dict['image'] = media['url']
                
                products.append(product_dict)
        
        return jsonify(products), 200
        
    except Exception as e:
        print(f"Error in get_recently_viewed: {str(e)}")
        return jsonify({
            "error": "Failed to fetch recently viewed products",
            "message": str(e)
        }), 500

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
        # Try to get the current user ID if authenticated
        user_id = None
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
        except Exception:
            # If JWT verification fails, continue without user tracking
            pass
        
        # If user is authenticated, track the view
        if user_id:
            # Check if there's an existing view record
            existing_view = RecentlyViewed.query.filter_by(
                user_id=user_id,
                product_id=product_id
            ).first()
            
            if existing_view:
                # Update the viewed_at timestamp
                existing_view.viewed_at = datetime.utcnow()
            else:
                # Create a new view record
                new_view = RecentlyViewed(
                    user_id=user_id,
                    product_id=product_id,
                    viewed_at=datetime.utcnow()
                )
                db.session.add(new_view)
            
            # Commit the changes
            db.session.commit()
        
        # Get and return the product details
        return ProductController.get_product_details(product_id)
        
    except Exception as e:
        print(f"Error in get_product_details route: {str(e)}")
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
        }), 500 