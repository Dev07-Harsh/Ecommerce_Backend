from flask import Blueprint
from controllers.brand_controller import BrandController
from flask_cors import cross_origin

brand_bp = Blueprint('brand', __name__)

@brand_bp.route('/', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_all_brands():
    """
    Get all brands with optional search
    ---
    tags:
      - Brands
    parameters:
      - in: query
        name: search
        type: string
        required: false
        description: Search term for brand name
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
    return BrandController.get_all_brands()

@brand_bp.route('/<int:brand_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_brand(brand_id):
    """
    Get a single brand by ID
    ---
    tags:
      - Brands
    parameters:
      - in: path
        name: brand_id
        type: integer
        required: true
        description: ID of the brand to retrieve
    responses:
      200:
        description: Brand details retrieved successfully
        schema:
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
    return BrandController.get_brand(brand_id)

@brand_bp.route('/icons', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_brand_icons():
    """
    Get only brand icons and basic info
    ---
    tags:
      - Brands
    responses:
      200:
        description: List of brand icons retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              brand_id:
                type: integer
              name:
                type: string
              icon_url:
                type: string
      500:
        description: Internal server error
    """
    return BrandController.get_brand_icons()
