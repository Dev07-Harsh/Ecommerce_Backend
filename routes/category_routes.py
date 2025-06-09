from flask import Blueprint, redirect, url_for
from controllers.categories_controller import CategoriesController
from flask_cors import cross_origin

category_bp = Blueprint('category', __name__)

@category_bp.route('/with-icons', methods=['GET', 'OPTIONS'])
@category_bp.route('/with-icons/', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_categories_with_icons():
    """
    Get all categories that have icons
    ---
    tags:
      - Categories
    responses:
      200:
        description: List of categories with icons retrieved successfully
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
              icon_url:
                type: string
              parent_id:
                type: integer
                nullable: true
      500:
        description: Internal server error
    """
    return CategoriesController.get_categories_with_icons()

@category_bp.route('/all', methods=['GET', 'OPTIONS'])
@category_bp.route('/all/', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_all_categories():
    """
    Get all categories with their hierarchical structure
    ---
    tags:
      - Categories
    responses:
      200:
        description: List of all categories with hierarchy retrieved successfully
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
              children:
                type: array
                items:
                  $ref: '#/definitions/Category'
      500:
        description: Internal server error
    """
    return CategoriesController.get_all_categories()

@category_bp.route('', methods=['GET', 'OPTIONS'])
@category_bp.route('/', methods=['GET', 'OPTIONS'])
@cross_origin()
def search_categories():
    """
    Search categories by name or slug
    ---
    tags:
      - Categories
    parameters:
      - in: query
        name: search
        type: string
        required: false
        description: Search term for category name or slug
    responses:
      200:
        description: List of matching categories retrieved successfully
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
    return CategoriesController.get_all_categories() 