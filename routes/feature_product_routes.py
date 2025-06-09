from flask import Blueprint, request, jsonify
from controllers.feature_product_controller import FeatureProductController
from flask_cors import cross_origin
from common.cache import cached
from common.response import success_response

feature_product_bp = Blueprint('feature_product', __name__, url_prefix='/api/featured-products')

@feature_product_bp.route('/', methods=['GET', 'OPTIONS'])
@cross_origin()
@cached(timeout=300, key_prefix='featured_products')  # Cache for 5 minutes
def get_featured_products():
    """
    Get all featured products with pagination
    ---
    tags:
      - Featured Products
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
        default: 12
        description: Items per page (max 50)
    responses:
      200:
        description: List of featured products retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                products:
                  type: array
                  items:
                    type: object
                    properties:
                      product_id:
                        type: integer
                        example: 1
                      product_name:
                        type: string
                        example: "Sample Product"
                      selling_price:
                        type: number
                        format: float
                        example: 99.99
                      special_price:
                        type: number
                        format: float
                        nullable: true
                        example: 79.99
                      discount_pct:
                        type: number
                        format: float
                        example: 20
                      product_description:
                        type: string
                        example: "Product description"
                      images:
                        type: array
                        items:
                          type: string
                          example: "https://example.com/image.jpg"
                      category:
                        type: object
                        properties:
                          category_id:
                            type: integer
                            example: 1
                          name:
                            type: string
                            example: "Electronics"
                      brand:
                        type: object
                        properties:
                          brand_id:
                            type: integer
                            example: 1
                          name:
                            type: string
                            example: "Brand Name"
                      placement:
                        type: object
                        properties:
                          placement_id:
                            type: integer
                            example: 1
                          sort_order:
                            type: integer
                            example: 0
                          added_at:
                            type: string
                            format: date-time
                            example: "2024-03-20T10:00:00Z"
                          expires_at:
                            type: string
                            format: date-time
                            nullable: true
                            example: "2024-04-20T10:00:00Z"
                pagination:
                  type: object
                  properties:
                    total:
                      type: integer
                      example: 100
                    pages:
                      type: integer
                      example: 9
                    current_page:
                      type: integer
                      example: 1
                    per_page:
                      type: integer
                      example: 12
      400:
        description: Invalid request parameters
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Invalid page number"
            data:
              type: null
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Internal server error"
            data:
              type: null
    """
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        # Validate pagination parameters
        if page < 1:
            return jsonify({
                'success': False,
                'message': 'Page number must be greater than 0',
                'data': None
            }), 400
            
        if per_page < 1 or per_page > 50:  # Limit maximum items per page
            return jsonify({
                'success': False,
                'message': 'Items per page must be between 1 and 50',
                'data': None
            }), 400
        
        result = FeatureProductController.get_featured_products(page, per_page)
        return success_response(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': None
        }), 500

@feature_product_bp.route('/<int:product_id>/', methods=['GET', 'OPTIONS'])
@cross_origin()
@cached(timeout=300, key_prefix='featured_product_details')  # Cache for 5 minutes
def get_featured_product_details(product_id):
    """
    Get detailed information about a specific featured product
    ---
    tags:
      - Featured Products
    parameters:
      - in: path
        name: product_id
        type: integer
        required: true
        description: ID of the featured product to retrieve
    responses:
      200:
        description: Featured product details retrieved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                product_id:
                  type: integer
                  example: 1
                product_name:
                  type: string
                  example: "Sample Product"
                selling_price:
                  type: number
                  format: float
                  example: 99.99
                special_price:
                  type: number
                  format: float
                  nullable: true
                  example: 79.99
                discount_pct:
                  type: number
                  format: float
                  example: 20
                product_description:
                  type: string
                  example: "Product description"
                images:
                  type: array
                  items:
                    type: string
                    example: "https://example.com/image.jpg"
                category:
                  type: object
                  properties:
                    category_id:
                      type: integer
                      example: 1
                    name:
                      type: string
                      example: "Electronics"
                brand:
                  type: object
                  properties:
                    brand_id:
                      type: integer
                      example: 1
                    name:
                      type: string
                      example: "Brand Name"
                placement:
                  type: object
                  properties:
                    placement_id:
                      type: integer
                      example: 1
                    sort_order:
                      type: integer
                      example: 0
                    added_at:
                      type: string
                      format: date-time
                      example: "2024-03-20T10:00:00Z"
                    expires_at:
                      type: string
                      format: date-time
                      nullable: true
                      example: "2024-04-20T10:00:00Z"
      404:
        description: Featured product not found
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Featured product not found"
            data:
              type: null
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            message:
              type: string
              example: "Internal server error"
            data:
              type: null
    """
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        result = FeatureProductController.get_featured_product_details(product_id)
        return success_response(result)
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': None
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': None
        }), 500 