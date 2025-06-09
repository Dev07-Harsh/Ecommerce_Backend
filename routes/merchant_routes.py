# routes/merchant_routes.py
from flask import Blueprint, request, jsonify, current_app
from http import HTTPStatus
from auth.utils import merchant_role_required, super_admin_role_required
from common.database import db
import cloudinary
import cloudinary.uploader
from werkzeug.exceptions import NotFound
from models.product import Product
from models.product_stock import ProductStock
from controllers.merchant.brand_request_controller import MerchantBrandRequestController
from controllers.merchant.brand_controller         import MerchantBrandController
from controllers.merchant.category_controller      import MerchantCategoryController
from controllers.merchant.category_attribute_controller import MerchantCategoryAttributeController
from controllers.merchant.product_controller       import MerchantProductController
from controllers.merchant.product_meta_controller  import MerchantProductMetaController
from controllers.merchant.product_tax_controller   import MerchantProductTaxController
from controllers.merchant.product_shipping_controller import MerchantProductShippingController
from controllers.merchant.product_media_controller import MerchantProductMediaController
from controllers.merchant.product_attribute_controller import MerchantProductAttributeController
from controllers.merchant.product_placement_controller import MerchantProductPlacementController
from controllers.merchant.tax_category_controller  import MerchantTaxCategoryController
from controllers.merchant.product_stock_controller import MerchantProductStockController
from controllers.merchant.merchant_profile_controller import MerchantProfileController
from flask_jwt_extended import get_jwt_identity, jwt_required
from controllers.merchant.order_controller import MerchantOrderController
from auth.models.models import MerchantProfile


ALLOWED_MEDIA_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'avi'} 

def allowed_media_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_MEDIA_EXTENSIONS

def calculate_discount_percentage(cost_price, selling_price):
    """Calculate discount percentage based on cost and selling price."""
    if not cost_price or not selling_price or cost_price <= 0:
        return 0
    return round(((cost_price - selling_price) / cost_price) * 100, 2)

merchant_dashboard_bp = Blueprint('merchant_dashboard_bp', __name__)

# ── BRAND REQUESTS ───────────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/brand-requests', methods=['GET'])
@merchant_role_required
def list_brand_requests():
    items = MerchantBrandRequestController.list_all()
    return jsonify([i.serialize() for i in items]), 200

@merchant_dashboard_bp.route('/brand-requests', methods=['POST'])
@merchant_role_required
def create_brand_request():
    data = request.get_json()
    br = MerchantBrandRequestController.create(data)
    return jsonify(br.serialize()), 201

# ── BRANDS ────────────────────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/brands', methods=['GET'])
@merchant_role_required
def list_brands():
    items = MerchantBrandController.list_all()
    return jsonify([i.serialize() for i in items]), 200

# ── CATEGORIES ───────────────────────────────────────────────────────────────────

@merchant_dashboard_bp.route('/categories', methods=['GET'])
@merchant_role_required
def list_merchant_categories():
    try:
        cats = MerchantCategoryController.list_all()
       
        return jsonify([c.serialize() for c in cats]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error listing categories: {e}")
        return jsonify({'message': 'Failed to retrieve categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/attributes/<int:aid>/values', methods=['GET'])
@merchant_role_required
def list_attribute_values(aid):
    """
    Get all values for a specific attribute
    ---
    tags:
      - Merchant - Attributes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: aid
        type: integer
        required: true
        description: Attribute ID
    responses:
      200:
        description: List of attribute values retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              value_code:
                type: string
              value_label:
                type: string
      404:
        description: Attribute not found
      500:
        description: Internal server error
    """
    try:
        from controllers.merchant.attribute_controller import MerchantAttributeController
        values = MerchantAttributeController.get_values(aid)
        return jsonify([v.serialize() for v in values]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error fetching values for attribute {aid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': 'An error occurred while retrieving attribute values.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/categories/<int:cid>/attributes', methods=['GET'])
@merchant_role_required
def list_attributes_for_merchant_category_view(cid):
    """
    Get all attributes associated with a specific category
    ---
    tags:
      - Merchant - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
    responses:
      200:
        description: List of attributes retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              attribute_id:
                type: integer
              name:
                type: string
              type:
                type: string
              options:
                type: array
                items:
                  type: string
              help_text:
                type: string
              required:
                type: boolean
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        attributes = MerchantCategoryAttributeController.get_attributes_for_category(cid)
        return jsonify(attributes), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error fetching attributes for category {cid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': 'An error occurred while retrieving category attributes.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/categories/<int:cid>', methods=['GET'])
@merchant_role_required
def get_category(cid):
    """
    Get category details by ID
    ---
    tags:
      - Merchant - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
    responses:
      200:
        description: Category details retrieved successfully
        schema:
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
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        category = MerchantCategoryController.get(cid)
        return jsonify(category), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting category {cid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': 'Failed to retrieve category details.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── PRODUCTS ─────────────────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/products', methods=['GET'])
@merchant_role_required
def list_products():
    ps = MerchantProductController.list_all()
    return jsonify([p.serialize() for p in ps]), 200

@merchant_dashboard_bp.route('/products', methods=['POST'])
@merchant_role_required
def create_product():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
        
        # Calculate discount percentage if cost_price and selling_price are provided
        if 'cost_price' in data and 'selling_price' in data:
            cost_price = float(data['cost_price'])
            selling_price = float(data['selling_price'])
            data['discount_pct'] = calculate_discount_percentage(cost_price, selling_price)
        
        p = MerchantProductController.create(data)
        return jsonify(p.serialize()), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error creating product: {e}")
        return jsonify({'message': 'Failed to create product'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/variants', methods=['POST'])
@merchant_role_required
def create_product_variant(pid):
    """
    Create a variant for a parent product
    ---
    tags:
      - Merchant - Products
    security:
      - Bearer: []
    parameters:
      - name: pid
        in: path
        type: integer
        required: true
        description: Parent product ID
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - sku
              - stock_qty
              - selling_price
            properties:
              sku:
                type: string
                description: Unique SKU for the variant
              stock_qty:
                type: integer
                minimum: 0
                description: Initial stock quantity
              selling_price:
                type: number
                minimum: 0
                description: Variant's selling price
              cost_price:
                type: number
                minimum: 0
                description: Optional variant's cost price (defaults to parent's cost price)
              attributes:
                type: object
                description: Dictionary of attribute values for the variant
                additionalProperties:
                  type: string
    responses:
      201:
        description: Variant created successfully
        schema:
          type: object
          properties:
            product_id:
              type: integer
            parent_product_id:
              type: integer
            sku:
              type: string
            stock_qty:
              type: integer
            selling_price:
              type: number
            attributes:
              type: object
      400:
        description: Invalid request data
      404:
        description: Parent product not found
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST

        # Validate required fields
        required_fields = ['sku', 'stock_qty', 'selling_price']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'error': 'MISSING_FIELDS'
            }), HTTPStatus.BAD_REQUEST

        # Validate numeric fields
        try:
            data['stock_qty'] = int(data['stock_qty'])
            data['selling_price'] = float(data['selling_price'])
            if 'cost_price' in data:
                data['cost_price'] = float(data['cost_price'])
        except ValueError as e:
            return jsonify({
                'message': f'Invalid numeric value: {str(e)}',
                'error': 'INVALID_NUMERIC'
            }), HTTPStatus.BAD_REQUEST

        # Validate minimum values
        if data['stock_qty'] < 0:
            return jsonify({
                'message': 'Stock quantity cannot be negative',
                'error': 'INVALID_STOCK'
            }), HTTPStatus.BAD_REQUEST
        if data['selling_price'] < 0:
            return jsonify({
                'message': 'Selling price cannot be negative',
                'error': 'INVALID_PRICE'
            }), HTTPStatus.BAD_REQUEST

        # Validate attributes if provided
        if 'attributes' in data:
            if not isinstance(data['attributes'], dict):
                return jsonify({
                    'message': 'Attributes must be a dictionary',
                    'error': 'INVALID_ATTRIBUTES'
                }), HTTPStatus.BAD_REQUEST

        variant = MerchantProductController.create_variant(pid, data)
        return jsonify(variant.serialize()), HTTPStatus.CREATED

    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error creating variant for product {pid}: {e}")
        return jsonify({'message': 'Failed to create product variant'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>', methods=['GET'])
@merchant_role_required
def get_product(pid):
    p = MerchantProductController.get(pid)
    return jsonify(p.serialize()), 200

@merchant_dashboard_bp.route('/products/<int:pid>', methods=['PUT'])
@merchant_role_required
def update_product(pid):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
        
        # Calculate discount percentage if cost_price and selling_price are provided
        if 'cost_price' in data and 'selling_price' in data:
            cost_price = float(data['cost_price'])
            selling_price = float(data['selling_price'])
            data['discount_pct'] = calculate_discount_percentage(cost_price, selling_price)
        
        p = MerchantProductController.update(pid, data)
        return jsonify(p.serialize()), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error updating product {pid}: {e}")
        return jsonify({'message': 'Failed to update product'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>', methods=['DELETE'])
@merchant_role_required
def delete_product(pid):
    p = MerchantProductController.delete(pid)
    return jsonify(p.serialize()), 200



# PRODUCT META
@merchant_dashboard_bp.route('/products/<int:pid>/meta', methods=['GET'])
@merchant_role_required
def get_product_meta(pid):
    pm = MerchantProductMetaController.get(pid)
    return jsonify(pm.serialize()), 200

@merchant_dashboard_bp.route('/products/<int:pid>/meta', methods=['POST','PUT'])
@merchant_role_required
def upsert_product_meta(pid):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST

        # Validate required fields
        required_fields = ['short_desc', 'full_desc']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'error': 'MISSING_FIELDS'
            }), HTTPStatus.BAD_REQUEST

        # Ensure fields are not empty strings
        for field in required_fields:
            if not data[field].strip():
                return jsonify({
                    'message': f'{field} cannot be empty',
                    'error': 'EMPTY_FIELD'
                }), HTTPStatus.BAD_REQUEST

        pm = MerchantProductMetaController.upsert(pid, data)
        return jsonify(pm.serialize()), 200
    except Exception as e:
        current_app.logger.error(f"Error updating product meta for product {pid}: {e}")
        return jsonify({
            'message': 'Failed to update product meta data',
            'error': str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

# PRODUCT TAX
@merchant_dashboard_bp.route('/products/<int:pid>/tax', methods=['GET'])
@merchant_role_required
def get_product_tax(pid):
    t = MerchantProductTaxController.get(pid)
    return jsonify({'product_id': t.product_id, 'tax_rate': str(t.tax_rate)}), 200

@merchant_dashboard_bp.route('/products/<int:pid>/tax', methods=['POST','PUT'])
@merchant_role_required
def upsert_product_tax(pid):
    data = request.get_json()
    t = MerchantProductTaxController.upsert(pid, data)
    return jsonify({'product_id': t.product_id, 'tax_rate': str(t.tax_rate)}), 200

# PRODUCT SHIPPING
@merchant_dashboard_bp.route('/products/<int:pid>/shipping', methods=['GET'])
@merchant_role_required
def get_product_shipping(pid):
    s = MerchantProductShippingController.get(pid)
    return jsonify(s.serialize()), 200

@merchant_dashboard_bp.route('/products/<int:pid>/shipping', methods=['POST','PUT'])
@merchant_role_required
def upsert_product_shipping(pid):
    data = request.get_json()
    s = MerchantProductShippingController.upsert(pid, data)
    return jsonify(s.serialize()), 200

# PRODUCT MEDIA
@merchant_dashboard_bp.route('/products/<int:pid>/media', methods=['GET'])
@merchant_role_required
def list_product_media(pid):
    try:
        m = MerchantProductMediaController.list(pid)
        return jsonify([x.serialize() for x in m]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error listing media for product {pid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': "Failed to retrieve product media."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/media/stats', methods=['GET'])
@merchant_role_required
def get_product_media_stats(pid):
    try:
        media_list = MerchantProductMediaController.list(pid)
        stats = {
            'total_count': len(media_list),
            'image_count': len([m for m in media_list if m.type == 'IMAGE']),
            'video_count': len([m for m in media_list if m.type == 'VIDEO']),
            'max_allowed': 5,  # This should match the frontend maxFiles
            'remaining_slots': 5 - len(media_list)
        }
        return jsonify(stats), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting media stats for product {pid}: {e}")
        return jsonify({'message': "Failed to retrieve product media statistics."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/media', methods=['POST'])
@merchant_role_required
def create_product_media(pid):
   
    
    if 'media_file' not in request.files:
        return jsonify({'message': 'No media file part in the request'}), HTTPStatus.BAD_REQUEST
    
    file = request.files['media_file']

    if file.filename == '':
        return jsonify({'message': 'No selected file'}), HTTPStatus.BAD_REQUEST

    
    if not allowed_media_file(file.filename):
        return jsonify({'message': f"Invalid file type. Allowed types: {', '.join(ALLOWED_MEDIA_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST

  
    file_mimetype = file.mimetype.lower()
    media_type_str = "IMAGE" 
    if file_mimetype.startswith('video/'):
        media_type_str = "VIDEO"
    elif not file_mimetype.startswith('image/'):
       
        return jsonify({'message': f"Unsupported file content type: {file.mimetype}"}), HTTPStatus.BAD_REQUEST

   
    media_type_from_form = request.form.get('type', media_type_str).upper()


    sort_order_str = request.form.get('sort_order', '0')
    try:
        sort_order = int(sort_order_str)
    except ValueError:
        return jsonify({'message': 'Invalid sort_order format, must be an integer.'}), HTTPStatus.BAD_REQUEST
    
   
   
    cloudinary_url = None
    cloudinary_public_id = None 
    resource_type_for_cloudinary = "image" if media_type_from_form == "IMAGE" else "video"

    try:
        
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"product_media/{pid}",  
            resource_type=resource_type_for_cloudinary
        )
        cloudinary_url = upload_result.get('secure_url')
        cloudinary_public_id = upload_result.get('public_id') 

        if not cloudinary_url:
            current_app.logger.error("Cloudinary upload for product media succeeded but no secure_url was returned.")
            return jsonify({'message': 'Cloudinary upload succeeded but did not return a URL.'}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    except cloudinary.exceptions.Error as e:
        current_app.logger.error(f"Cloudinary upload failed for product media (product {pid}): {e}")
        return jsonify({'message': f"Cloudinary media upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        current_app.logger.error(f"Error during product media file upload (product {pid}): {e}")
        return jsonify({'message': f"An error occurred during media file upload: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

   
    media_data = {
        'url': cloudinary_url,
        'type': media_type_from_form, 
        'sort_order': sort_order,
       
    }

   
    try:
       
        new_media = MerchantProductMediaController.create(pid, media_data)
        return jsonify(new_media.serialize()), HTTPStatus.CREATED
    except ValueError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback() 
        current_app.logger.error(f"Error saving product media to DB for product {pid}: {e}")
       
        return jsonify({'message': 'Failed to save product media information.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@merchant_dashboard_bp.route('/products/media/<int:mid>', methods=['DELETE'])
@merchant_role_required
def delete_product_media(mid):
    try:
       
        m = MerchantProductMediaController.delete(mid)
        return jsonify(m.serialize()), HTTPStatus.OK 
    except Exception as e:
      
        current_app.logger.error(f"Merchant: Error deleting media {mid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': "Failed to delete product media."}), HTTPStatus.INTERNAL_SERVER_ERROR

# PRODUCT ATTRIBUTES
@merchant_dashboard_bp.route('/products/<int:pid>/attributes', methods=['GET'])
@merchant_role_required
def list_product_attributes(pid):
    try:
        pas = MerchantProductAttributeController.list(pid)
        return jsonify([p.serialize() for p in pas]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing product attributes for product {pid}: {e}")
        return jsonify({'message': 'Failed to retrieve product attributes.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/attributes/values', methods=['POST'])
@merchant_role_required
def set_product_attribute_values(pid):
    try:
        data = request.get_json()
        current_app.logger.info(f"Received attribute values request for product {pid}: {data}")
        
        if not data or not isinstance(data, dict):
            return jsonify({
                'message': 'Invalid data format. Expected a dictionary of attribute values.',
                'error': 'INVALID_FORMAT'
            }), HTTPStatus.BAD_REQUEST

        # Format: { attribute_id: value }
        # value can be string, string[], or null
        for attribute_id, value in data.items():
            try:
                attribute_id = int(attribute_id)
                
                # Skip if value is null or empty
                if value is None or (isinstance(value, list) and len(value) == 0):
                    continue
                    
                # Create or update the attribute value
                MerchantProductAttributeController.upsert(pid, attribute_id, value)
            except ValueError as e:
                current_app.logger.error(f"Invalid attribute value for product {pid}, attribute {attribute_id}: {e}")
                return jsonify({
                    'message': str(e),
                    'error': 'INVALID_VALUE',
                    'attribute_id': attribute_id
                }), HTTPStatus.BAD_REQUEST
            except Exception as e:
                current_app.logger.error(f"Error setting attribute value for product {pid}, attribute {attribute_id}: {e}")
                return jsonify({
                    'message': f'Failed to set attribute value: {str(e)}',
                    'error': 'SERVER_ERROR',
                    'attribute_id': attribute_id
                }), HTTPStatus.INTERNAL_SERVER_ERROR

        # Return updated attributes
        updated_attributes = MerchantProductAttributeController.list(pid)
        return jsonify({
            'message': 'Attribute values updated successfully',
            'attributes': [p.serialize() for p in updated_attributes]
        }), HTTPStatus.OK

    except Exception as e:
        current_app.logger.error(f"Error setting product attribute values for product {pid}: {e}")
        return jsonify({
            'message': 'Failed to set product attribute values.',
            'error': 'SERVER_ERROR'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/attributes/<int:aid>/<value_code>', methods=['PUT'])
@merchant_role_required
def update_product_attribute(pid, aid, value_code):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided for update.'}), HTTPStatus.BAD_REQUEST
            
        pa = MerchantProductAttributeController.update(pid, aid, value_code, data)
        return jsonify(pa.serialize()), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error updating product attribute for product {pid}, attribute {aid}: {e}")
        return jsonify({'message': 'Failed to update product attribute.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/attributes/<int:aid>/<value_code>', methods=['DELETE'])
@merchant_role_required
def delete_product_attribute(pid, aid, value_code):
    try:
        MerchantProductAttributeController.delete(pid, aid, value_code)
        return '', HTTPStatus.NO_CONTENT
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error deleting product attribute for product {pid}, attribute {aid}: {e}")
        return jsonify({'message': 'Failed to delete product attribute.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# TAX CATEGORIES
@merchant_dashboard_bp.route('/tax-categories', methods=['GET'])
@merchant_role_required
def list_tax_categories():
    try:
        categories = MerchantTaxCategoryController.list_all()
        return jsonify(categories), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error listing tax categories: {e}")
        return jsonify({'message': 'Failed to retrieve tax categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── BRAND CATEGORIES ────────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/brands/categories/<int:cid>', methods=['GET'])
@merchant_role_required
def get_brands_for_category(cid):
    """
    Get all brands associated with a specific category.
    ---
    tags:
      - Merchant - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
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
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        brands = MerchantBrandController.get_brands_for_category(cid)
        return jsonify([b.serialize() for b in brands]), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error getting brands for category {cid}: {e}")
        return jsonify({'message': f'Could not get brands for category: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

# PRODUCT STOCK
@merchant_dashboard_bp.route('/products/<int:pid>/stock', methods=['GET'])
@merchant_role_required
def get_product_stock(pid):
    """
    Get stock information for a specific product
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    parameters:
      - name: pid
        in: path
        type: integer
        required: true
        description: Product ID
    responses:
      200:
        description: Stock information retrieved successfully
      404:
        description: Product not found
      500:
        description: Internal server error
    """
    try:
        stock = MerchantProductStockController.get(pid)
        return jsonify(stock.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error getting stock for product {pid}: {str(e)}")
        return jsonify({'message': 'Failed to retrieve product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/stock', methods=['PUT'])
@merchant_role_required
def update_product_stock(pid):
    """
    Update stock information for a specific product
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    parameters:
      - name: pid
        in: path
        type: integer
        required: true
        description: Product ID
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              stock_qty:
                type: integer
                minimum: 0
              low_stock_threshold:
                type: integer
                minimum: 0
    responses:
      200:
        description: Stock information updated successfully
      400:
        description: Invalid request data
      404:
        description: Product not found
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST

        result = MerchantProductStockController.update(pid, data)
        return jsonify(result), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error updating stock for product {pid}: {str(e)}")
        return jsonify({'message': 'Failed to update product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/stock/bulk-update', methods=['POST'])
@merchant_role_required
def bulk_update_product_stock(pid):
    """
    Bulk update stock information for multiple variants of a product
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    parameters:
      - name: pid
        in: path
        type: integer
        required: true
        description: Product ID
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: array
            items:
              type: object
              properties:
                variant_id:
                  type: integer
                stock_qty:
                  type: integer
                  minimum: 0
                low_stock_threshold:
                  type: integer
                  minimum: 0
    responses:
      200:
        description: Stock information updated successfully
      400:
        description: Invalid request data
      404:
        description: Product not found
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'message': 'Invalid data format'}), HTTPStatus.BAD_REQUEST

        results = MerchantProductStockController.bulk_update(pid, data)
        return jsonify([stock.serialize() for stock in results]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error bulk updating stock for product {pid}: {str(e)}")
        return jsonify({'message': 'Failed to bulk update product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/stock/low-stock', methods=['GET'])
@merchant_role_required
def get_low_stock_products():
    """
    Get all products with stock below their threshold
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    responses:
      200:
        description: List of low stock products retrieved successfully
      500:
        description: Internal server error
    """
    try:
        low_stock = MerchantProductStockController.get_low_stock()
        return jsonify([stock.serialize() for stock in low_stock]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error getting low stock products: {str(e)}")
        return jsonify({'message': 'Failed to retrieve low stock products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── PRODUCT APPROVAL ───────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/products/pending', methods=['GET'])
@super_admin_role_required
def list_pending_products():
    """Get all products pending approval."""
    try:
        products = MerchantProductController.get_pending_products()
        return jsonify([p.serialize() for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing pending products: {e}")
        return jsonify({'message': 'Failed to retrieve pending products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/approved', methods=['GET'])
@super_admin_role_required
def list_approved_products():
    """Get all approved products."""
    try:
        products = MerchantProductController.get_approved_products()
        return jsonify([p.serialize() for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing approved products: {e}")
        return jsonify({'message': 'Failed to retrieve approved products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/rejected', methods=['GET'])
@super_admin_role_required
def list_rejected_products():
    """Get all rejected products."""
    try:
        products = MerchantProductController.get_rejected_products()
        return jsonify([p.serialize() for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing rejected products: {e}")
        return jsonify({'message': 'Failed to retrieve rejected products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/approve', methods=['POST'])
@super_admin_role_required
def approve_product(pid):
    """Approve a product."""
    try:
        admin_id = get_jwt_identity()
        product = MerchantProductController.approve(pid, admin_id)
        return jsonify(product.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error approving product {pid}: {e}")
        return jsonify({'message': 'Failed to approve product.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/reject', methods=['POST'])
@super_admin_role_required
def reject_product(pid):
    """Reject a product."""
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({'message': 'Rejection reason is required.'}), HTTPStatus.BAD_REQUEST

        admin_id = get_jwt_identity()
        product = MerchantProductController.reject(pid, admin_id, data['reason'])
        return jsonify(product.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error rejecting product {pid}: {e}")
        return jsonify({'message': 'Failed to reject product.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── MERCHANT ORDERS ───────────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_merchant_orders():
    """
    Get all orders for a merchant's products
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        default: 50
        description: Number of items per page
      - name: status
        in: query
        type: string
        description: Filter by order status (PENDING_PAYMENT, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
      - name: payment_status
        in: query
        type: string
        description: Filter by payment status (PENDING, COMPLETED, FAILED, REFUNDED)
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter by start date (ISO format)
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter by end date (ISO format)
    responses:
      200:
        description: List of orders
      400:
        description: Invalid parameters
      500:
        description: Internal server error
    """
    try:
        # Get the current user's ID from the JWT token
        current_user_id = get_jwt_identity()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status = request.args.get('status')
        payment_status = request.args.get('payment_status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = MerchantOrderController.get_merchant_orders(
            user_id=current_user_id,
            page=page,
            per_page=per_page,
            status=status,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting merchant orders: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@merchant_dashboard_bp.route('/orders/<order_id>', methods=['GET'])
@jwt_required()
def get_merchant_order_details(order_id):
    """
    Get detailed information about a specific order
    ---
    parameters:
      - name: order_id
        in: path
        type: string
        required: true
        description: Order ID
    responses:
      200:
        description: Order details
      404:
        description: Order not found
      500:
        description: Internal server error
    """
    try:
        # Get the current user's ID from the JWT token
        current_user_id = get_jwt_identity()
        
        result = MerchantOrderController.get_merchant_order_details(
            user_id=current_user_id,
            order_id=order_id
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting merchant order details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@merchant_dashboard_bp.route('/orders/stats', methods=['GET'])
@jwt_required()
def get_merchant_order_stats():
    """
    Get order statistics for a merchant
    ---
    parameters:
      - name: days
        in: query
        type: integer
        default: 30
        description: Number of days to include in statistics
    responses:
      200:
        description: Order statistics
      500:
        description: Internal server error
    """
    try:
        # Get the current user's ID from the JWT token
        current_user_id = get_jwt_identity()
        
        days = request.args.get('days', 30, type=int)
        result = MerchantOrderController.get_merchant_order_stats(
            user_id=current_user_id,
            days=days
        )
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error getting merchant order stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ── INVENTORY MANAGEMENT ─────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/inventory/stats', methods=['GET'])
@merchant_role_required
def get_inventory_stats():
    """
    Get inventory statistics for a merchant
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    responses:
      200:
        description: Inventory statistics retrieved successfully
        schema:
          type: object
          properties:
            total_products:
              type: integer
            low_stock_products:
              type: integer
            out_of_stock_products:
              type: integer
            inventory_value:
              type: number
      500:
        description: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        stats = MerchantProductStockController.get_inventory_stats(current_user_id)
        return jsonify(stats), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error getting inventory stats: {str(e)}")
        return jsonify({'message': 'Failed to retrieve inventory statistics.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/inventory/products', methods=['GET'])
@merchant_role_required
def list_inventory_products():
    """
    Get all products with their inventory information
    ---
    tags:
      - Merchant - Inventory
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        default: 50
        description: Number of items per page
      - name: search
        in: query
        type: string
        description: Search term for product name or SKU
      - name: category
        in: query
        type: string
        description: Filter by category (ID or slug)
      - name: brand
        in: query
        type: string
        description: Filter by brand (ID or slug)
      - name: stock_status
        in: query
        type: string
        enum: [in_stock, low_stock, out_of_stock]
        description: Filter by stock status
    responses:
      200:
        description: List of products with inventory information
        schema:
          type: object
          properties:
            products:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  name:
                    type: string
                  sku:
                    type: string
                  category:
                    type: object
                    properties:
                      id:
                        type: integer
                      name:
                        type: string
                      slug:
                        type: string
                  brand:
                    type: object
                    properties:
                      id:
                        type: integer
                      name:
                        type: string
                      slug:
                        type: string
                  stock_qty:
                    type: integer
                  low_stock_threshold:
                    type: integer
                  available:
                    type: integer
                  image_url:
                    type: string
            pagination:
              type: object
              properties:
                total:
                  type: integer
                current_page:
                  type: integer
                per_page:
                  type: integer
                pages:
                  type: integer
      500:
        description: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category')
        brand = request.args.get('brand')
        stock_status = request.args.get('stock_status')

        result = MerchantProductStockController.get_products(
            user_id=current_user_id,
            page=page,
            per_page=per_page,
            search=search,
            category=category,
            brand=brand,
            stock_status=stock_status
        )
        
        return jsonify(result), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error listing inventory products: {str(e)}")
        return jsonify({'message': 'Failed to retrieve inventory products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/brands/<int:bid>', methods=['GET'])
@merchant_role_required
def get_brand(bid):
    """
    Get brand details by ID
    ---
    tags:
      - Merchant - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: bid
        type: integer
        required: true
        description: Brand ID
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
              nullable: true
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    try:
        brand = MerchantBrandController.get(bid)
        return jsonify(brand), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting brand {bid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': 'Failed to retrieve brand details.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── MERCHANT SUBSCRIPTION ─────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/subscription/plans', methods=['GET'])
@merchant_role_required
def list_subscription_plans():
    """
    Get all available subscription plans
    ---
    tags:
      - Merchant - Subscription
    security:
      - Bearer: []
    responses:
      200:
        description: List of subscription plans retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              plan_id:
                type: integer
              name:
                type: string
              description:
                type: string
              featured_limit:
                type: integer
              promo_limit:
                type: integer
              duration_days:
                type: integer
              price:
                type: number
              can_place_premium:
                type: boolean
      500:
        description: Internal server error
    """
    try:
        from models.subscription import SubscriptionPlan
        plans = SubscriptionPlan.query.filter_by(active_flag=True).all()
        return jsonify([plan.serialize() for plan in plans]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing subscription plans: {str(e)}")
        return jsonify({'message': 'Failed to retrieve subscription plans.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/subscription/current', methods=['GET'])
@merchant_role_required
def get_current_subscription():
    """
    Get merchant's current subscription details
    ---
    tags:
      - Merchant - Subscription
    security:
      - Bearer: []
    responses:
      200:
        description: Current subscription details retrieved successfully
        schema:
          type: object
          properties:
            is_subscribed:
              type: boolean
            can_place_premium:
              type: boolean
            subscription_started_at:
              type: string
              format: date-time
            subscription_expires_at:
              type: string
              format: date-time
            plan:
              type: object
              properties:
                plan_id:
                  type: integer
                name:
                  type: string
                description:
                  type: string
                featured_limit:
                  type: integer
                promo_limit:
                  type: integer
                can_place_premium:
                  type: boolean
      404:
        description: Merchant profile not found
      500:
        description: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        status = MerchantProfileController.get_subscription_status(current_user_id)
        
        # Ensure can_place_premium is set correctly based on subscription status
        if status['is_subscribed'] and not status['can_place_premium']:
            profile = MerchantProfile.get_by_user_id(current_user_id)
            if profile:
                profile.can_place_premium = True
                db.session.commit()
                status['can_place_premium'] = True
        
        return jsonify(status), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error getting subscription status: {str(e)}")
        return jsonify({'message': 'Failed to retrieve subscription status.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/subscription/subscribe', methods=['POST'])
@merchant_role_required
def subscribe_to_plan():
    """
    Subscribe to a subscription plan
    ---
    tags:
      - Merchant - Subscription
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - plan_id
            properties:
              plan_id:
                type: integer
                description: ID of the subscription plan to subscribe to
    responses:
      200:
        description: Successfully subscribed to plan
        schema:
          type: object
          properties:
            message:
              type: string
            subscription:
              type: object
              properties:
                is_subscribed:
                  type: boolean
                can_place_premium:
                  type: boolean
                subscription_started_at:
                  type: string
                  format: date-time
                subscription_expires_at:
                  type: string
                  format: date-time
                plan:
                  type: object
      400:
        description: Invalid request data
      404:
        description: Plan or merchant profile not found
      500:
        description: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'plan_id' not in data:
            return jsonify({
                'message': 'Missing required field: plan_id',
                'error': 'MISSING_FIELD'
            }), HTTPStatus.BAD_REQUEST

        profile = MerchantProfileController.subscribe_to_plan(
            current_user_id,
            data['plan_id']
        )
        
        # Ensure can_place_premium is set to True for subscribed users
        if profile.is_subscribed and not profile.can_place_premium:
            profile.can_place_premium = True
            db.session.commit()
        
        return jsonify({
            'message': 'Successfully subscribed to plan',
            'subscription': {
                'is_subscribed': profile.is_subscribed,
                'can_place_premium': profile.can_place_premium,
                'subscription_started_at': profile.subscription_started_at.isoformat(),
                'subscription_expires_at': profile.subscription_expires_at.isoformat(),
                'plan': profile.subscription_plan.serialize() if profile.subscription_plan else None
            }
        }), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error subscribing to plan: {str(e)}")
        return jsonify({'message': 'Failed to subscribe to plan.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/subscription/cancel', methods=['POST'])
@merchant_role_required
def cancel_subscription():
    """
    Cancel current subscription
    ---
    tags:
      - Merchant - Subscription
    security:
      - Bearer: []
    responses:
      200:
        description: Successfully cancelled subscription
        schema:
          type: object
          properties:
            message:
              type: string
            subscription:
              type: object
              properties:
                is_subscribed:
                  type: boolean
                can_place_premium:
                  type: boolean
      404:
        description: Merchant profile not found
      500:
        description: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        profile = MerchantProfileController.cancel_subscription(current_user_id)
        
        # Ensure can_place_premium is set to False when subscription is cancelled
        if not profile.is_subscribed and profile.can_place_premium:
            profile.can_place_premium = False
            db.session.commit()
        
        return jsonify({
            'message': 'Successfully cancelled subscription',
            'subscription': {
                'is_subscribed': profile.is_subscribed,
                'can_place_premium': profile.can_place_premium
            }
        }), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error cancelling subscription: {str(e)}")
        return jsonify({'message': 'Failed to cancel subscription.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── PRODUCT PLACEMENTS ─────────────────────────────────────────────────────
@merchant_dashboard_bp.route('/product-placements', methods=['GET'])
@merchant_role_required
def list_product_placements():
    """
    Get all product placements for the merchant
    ---
    tags:
      - Merchant - Product Placements
    security:
      - Bearer: []
    parameters:
      - name: placement_type
        in: query
        type: string
        enum: [FEATURED, PROMOTED]
        description: Optional filter by placement type
    responses:
      200:
        description: List of product placements retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              placement_id:
                type: integer
              product_id:
                type: integer
              merchant_id:
                type: integer
              placement_type:
                type: string
                enum: [featured, promoted]
              sort_order:
                type: integer
              is_active:
                type: boolean
              expires_at:
                type: string
                format: date-time
                nullable: true
              added_at:
                type: string
                format: date-time
              product_details:
                type: object
                properties:
                  product_id:
                    type: integer
                  product_name:
                    type: string
      500:
        description: Internal server error
    """
    try:
        placement_type = request.args.get('placement_type')
        placements = MerchantProductPlacementController.list_placements(placement_type)
        return jsonify([p.serialize() for p in placements]), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error listing product placements: {str(e)}")
        return jsonify({'message': 'Failed to retrieve product placements.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements', methods=['POST'])
@merchant_role_required
def create_product_placement():
    """
    Create a new product placement
    ---
    tags:
      - Merchant - Product Placements
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - product_id
              - placement_type
            properties:
              product_id:
                type: integer
                description: ID of the product to place
              placement_type:
                type: string
                enum: [FEATURED, PROMOTED]
                description: Type of placement
              sort_order:
                type: integer
                description: Order in which the placement should appear
              promotional_price:
                type: number
                description: Special promotional price for PROMOTED placements
              special_start:
                type: string
                format: date
                description: Start date for the promotion (YYYY-MM-DD)
              special_end:
                type: string
                format: date
                description: End date for the promotion (YYYY-MM-DD)
    responses:
      201:
        description: Product placement created successfully
      400:
        description: Invalid request data
      403:
        description: Subscription does not allow premium placements
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST

        # Validate required fields
        required_fields = ['product_id', 'placement_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'error': 'MISSING_FIELDS'
            }), HTTPStatus.BAD_REQUEST

        # Validate promotional data for PROMOTED placements
        if data['placement_type'].upper() == 'PROMOTED':
            promo_fields = ['promotional_price', 'special_start', 'special_end']
            missing_promo_fields = [field for field in promo_fields if field not in data]
            if missing_promo_fields:
                return jsonify({
                    'message': f'Missing required fields for promoted placement: {", ".join(missing_promo_fields)}',
                    'error': 'MISSING_PROMO_FIELDS'
                }), HTTPStatus.BAD_REQUEST

        placement = MerchantProductPlacementController.add_product_to_placement(
            product_id=data['product_id'],
            placement_type_str=data['placement_type'],
            sort_order=data.get('sort_order', 0),
            promotional_price=data.get('promotional_price'),
            special_start=data.get('special_start'),
            special_end=data.get('special_end')
        )
        return jsonify(placement.serialize()), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except PermissionError as e:
        return jsonify({'message': str(e)}), HTTPStatus.FORBIDDEN
    except Exception as e:
        current_app.logger.error(f"Error creating product placement: {str(e)}")
        return jsonify({'message': 'Failed to create product placement.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements/<int:placement_id>', methods=['DELETE'])
@merchant_role_required
def delete_product_placement(placement_id):
    """
    Delete a product placement
    ---
    tags:
      - Merchant - Product Placements
    security:
      - Bearer: []
    parameters:
      - name: placement_id
        in: path
        type: integer
        required: true
        description: ID of the placement to delete
    responses:
      204:
        description: Product placement deleted successfully
      404:
        description: Placement not found
      500:
        description: Internal server error
    """
    try:
        MerchantProductPlacementController.remove_product_from_placement(placement_id)
        return '', HTTPStatus.NO_CONTENT
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error deleting product placement {placement_id}: {str(e)}")
        return jsonify({'message': 'Failed to delete product placement.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements/<int:placement_id>/sort-order', methods=['PUT'])
@merchant_role_required
def update_placement_sort_order(placement_id):
    """
    Update the sort order of a product placement
    ---
    tags:
      - Merchant - Product Placements
    security:
      - Bearer: []
    parameters:
      - name: placement_id
        in: path
        type: integer
        required: true
        description: ID of the placement to update
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - sort_order
            properties:
              sort_order:
                type: integer
                description: New sort order value
    responses:
      200:
        description: Sort order updated successfully
      400:
        description: Invalid request data
      404:
        description: Placement not found
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data or 'sort_order' not in data:
            return jsonify({'message': 'Sort order is required'}), HTTPStatus.BAD_REQUEST

        placement = MerchantProductPlacementController.update_placement_sort_order(
            placement_id,
            data['sort_order']
        )
        return jsonify(placement.serialize()), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error updating placement sort order: {str(e)}")
        return jsonify({'message': 'Failed to update placement sort order.'}), HTTPStatus.INTERNAL_SERVER_ERROR