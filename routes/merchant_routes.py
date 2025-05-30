# routes/merchant_routes.py
from flask import Blueprint, request, jsonify, current_app
from http import HTTPStatus
from auth.utils import merchant_role_required
from common.database import db
import cloudinary
import cloudinary.uploader
from werkzeug.exceptions import NotFound
from controllers.merchant.brand_request_controller import MerchantBrandRequestController
from controllers.merchant.brand_controller         import MerchantBrandController
from controllers.merchant.category_controller      import MerchantCategoryController
from controllers.merchant.category_attribute_controller import MerchantCategoryAttributeController
from controllers.merchant.product_controller       import MerchantProductController
from controllers.merchant.product_meta_controller  import MerchantProductMetaController
from controllers.merchant.product_tax_controller   import MerchantProductTaxController
from controllers.merchant.product_shipping_controller import MerchantProductShippingController
from controllers.merchant.product_media_controller import MerchantProductMediaController
from controllers.merchant.variant_controller       import MerchantVariantController
from controllers.merchant.variant_stock_controller import MerchantVariantStockController
from controllers.merchant.variant_media_controller import MerchantVariantMediaController
from controllers.merchant.product_attribute_controller import MerchantProductAttributeController

from controllers.merchant.product_placement_controller import MerchantProductPlacementController

from controllers.merchant.tax_category_controller  import MerchantTaxCategoryController
from controllers.merchant.product_stock_controller import MerchantProductStockController


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

# VARIANTS
@merchant_dashboard_bp.route('/products/<int:pid>/variants', methods=['GET'])
@merchant_role_required
def list_variants(pid):
    vs = MerchantVariantController.list(pid)
    return jsonify([v.serialize() for v in vs]), HTTPStatus.OK 

@merchant_dashboard_bp.route('/products/<int:pid>/variants', methods=['POST'])
@merchant_role_required
def create_variant(pid):
    data = request.get_json()
    if not data: 
        return jsonify({"message": "Request body cannot be empty."}), HTTPStatus.BAD_REQUEST
    try:
        v = MerchantVariantController.create(pid, data)
        return jsonify(v.serialize()), HTTPStatus.CREATED 
    except ValueError as e: 
        return jsonify({"message": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e: 
        
        return jsonify({"message": "An error occurred while creating the variant."}), HTTPStatus.INTERNAL_SERVER_ERROR


@merchant_dashboard_bp.route('/products/variants/<int:vid>', methods=['PUT'])
@merchant_role_required
def update_variant(vid):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body cannot be empty for update."}), HTTPStatus.BAD_REQUEST
    try:
        v = MerchantVariantController.update(vid, data)
        return jsonify(v.serialize()), HTTPStatus.OK
    except ValueError as e: 
        return jsonify({"message": str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        if hasattr(e, 'code') and e.code == 404: 
            return jsonify({"message": getattr(e, 'description', "Variant not found.")}), HTTPStatus.NOT_FOUND
        current_app.logger.error(f"Error updating variant {vid}: {e}")
        return jsonify({"message": "An error occurred while updating the variant."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/variants/<int:vid>', methods=['DELETE'])
@merchant_role_required
def delete_variant(vid):
    try:
        v = MerchantVariantController.delete(vid)
        return jsonify(v.serialize()), HTTPStatus.OK 
    except Exception as e: 
        if hasattr(e, 'code') and e.code == 404:
            return jsonify({"message": getattr(e, 'description', "Variant not found.")}), HTTPStatus.NOT_FOUND
        return jsonify({"message": "An error occurred while deleting the variant."}), HTTPStatus.INTERNAL_SERVER_ERROR

# VARIANT STOCK
@merchant_dashboard_bp.route('/products/variants/<int:vid>/stock', methods=['GET'])
@merchant_role_required
def get_variant_stock(vid):
    vs = MerchantVariantStockController.get(vid)
    return jsonify(vs.serialize()), 200

@merchant_dashboard_bp.route('/products/variants/<int:vid>/stock', methods=['POST','PUT'])
@merchant_role_required
def upsert_variant_stock(vid):
    data = request.get_json()
    vs = MerchantVariantStockController.upsert(vid, data)
    return jsonify(vs.serialize()), 200

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
    try:
        stock = MerchantProductStockController.get(pid)
        return jsonify(stock.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting stock for product {pid}: {e}")
        return jsonify({'message': 'Failed to retrieve product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/stock', methods=['PUT'])
@merchant_role_required
def update_product_stock(pid):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), HTTPStatus.BAD_REQUEST
        
        stock = MerchantProductStockController.update(pid, data)
        return jsonify(stock.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error updating stock for product {pid}: {e}")
        return jsonify({'message': 'Failed to update product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/<int:pid>/stock/bulk-update', methods=['POST'])
@merchant_role_required
def bulk_update_product_stock(pid):
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'message': 'Invalid data format'}), HTTPStatus.BAD_REQUEST
        
        results = MerchantProductStockController.bulk_update(pid, data)
        return jsonify([stock.serialize() for stock in results]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error bulk updating stock for product {pid}: {e}")
        return jsonify({'message': 'Failed to bulk update product stock.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/stock/low-stock', methods=['GET'])
@merchant_role_required
def get_low_stock_products():
    try:
        low_stock = MerchantProductStockController.get_low_stock()
        return jsonify([stock.serialize() for stock in low_stock]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting low stock products: {e}")
        return jsonify({'message': 'Failed to retrieve low stock products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# VARIANT MEDIA
@merchant_dashboard_bp.route('/products/variants/<int:vid>/media', methods=['GET'])
@merchant_role_required
def list_variant_media(vid):
    try:
        m = MerchantVariantMediaController.list(vid)
        return jsonify([x.serialize() for x in m]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error listing media for variant {vid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': "Failed to retrieve variant media."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/variants/<int:vid>/media/stats', methods=['GET'])
@merchant_role_required
def get_variant_media_stats(vid):
    try:
        media_list = MerchantVariantMediaController.list(vid)
        stats = {
            'total_count': len(media_list),
            'image_count': len([m for m in media_list if m.media_type == 'IMAGE']),
            'video_count': len([m for m in media_list if m.media_type == 'VIDEO']),
            'max_allowed': 5,  # This should match the frontend maxFiles
            'remaining_slots': 5 - len(media_list)
        }
        return jsonify(stats), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error getting media stats for variant {vid}: {e}")
        return jsonify({'message': "Failed to retrieve variant media statistics."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/variants/<int:vid>/media', methods=['POST'])
@merchant_role_required
def create_variant_media(vid):
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
    display_order_str = request.form.get('display_order', '0')
    try:
        display_order = int(display_order_str)
    except ValueError:
        return jsonify({'message': 'Invalid display_order format, must be an integer.'}), HTTPStatus.BAD_REQUEST
    
    is_primary = request.form.get('is_primary', 'false').lower() == 'true'
    
    cloudinary_url = None
    cloudinary_public_id = None 
    resource_type_for_cloudinary = "image" if media_type_from_form == "IMAGE" else "video"

    try:
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"variant_media/{vid}",
            resource_type=resource_type_for_cloudinary
        )
        cloudinary_url = upload_result.get('secure_url')
        cloudinary_public_id = upload_result.get('public_id') 

        if not cloudinary_url:
            current_app.logger.error("Cloudinary upload for variant media succeeded but no secure_url was returned.")
            return jsonify({'message': 'Cloudinary upload succeeded but did not return a URL.'}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    except cloudinary.exceptions.Error as e:
        current_app.logger.error(f"Cloudinary upload failed for variant media (variant {vid}): {e}")
        return jsonify({'message': f"Cloudinary media upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        current_app.logger.error(f"Error during variant media file upload (variant {vid}): {e}")
        return jsonify({'message': f"An error occurred during media file upload: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

    media_data = {
        'media_url': cloudinary_url,
        'media_type': media_type_from_form,
        'display_order': display_order,
        'is_primary': is_primary,
        'public_id': cloudinary_public_id
    }

    try:
        new_media = MerchantVariantMediaController.create(vid, media_data)
        return jsonify(new_media.serialize()), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as e:
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving variant media to DB for variant {vid}: {e}")
        return jsonify({'message': 'Failed to save variant media information.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/products/variants/media/<int:mid>', methods=['DELETE'])
@merchant_role_required
def delete_variant_media(mid):
    try:
        m = MerchantVariantMediaController.delete(mid)
        return jsonify(m.serialize()), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Merchant: Error deleting variant media {mid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': "Failed to delete variant media."}), HTTPStatus.INTERNAL_SERVER_ERROR




# ── MERCHANT PRODUCT PLACEMENTS (Featured/Promoted Products) ──────────────────
@merchant_dashboard_bp.route('/product-placements', methods=['GET'])
@merchant_role_required
def list_merchant_product_placements():
    """Lists all product placements (active and inactive) for the current merchant."""
    try:
        # Optionally allow filtering by placement_type via query parameter
        placement_type_filter = request.args.get('type', None)
        placements = MerchantProductPlacementController.list_placements(placement_type_filter)
        return jsonify([p.serialize() for p in placements]), HTTPStatus.OK
    except ValueError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except NotFound as e:
        return jsonify({'message': getattr(e, 'description', str(e))}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Merchant: Error listing product placements: {e}")
        return jsonify({'message': "Failed to retrieve product placements."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements/<int:placement_id>', methods=['GET'])
@merchant_role_required
def get_merchant_product_placement(placement_id):
    """Gets details of a specific product placement owned by the current merchant."""
    try:
        placement = MerchantProductPlacementController.get_placement_details(placement_id)
        return jsonify(placement.serialize()), HTTPStatus.OK
    except NotFound as e: 
        return jsonify({'message': getattr(e, 'description', str(e))}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Merchant: Error retrieving product placement {placement_id}: {e}")
        return jsonify({'message': "Failed to retrieve product placement details."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements', methods=['POST'])
@merchant_role_required
def add_merchant_product_to_placement():
    """Adds one of the merchant's products to a specified placement type."""
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is missing or not JSON.'}), HTTPStatus.BAD_REQUEST

    product_id = data.get('product_id')
    placement_type_str = data.get('placement_type') #  "FEATURED" or "PROMOTED"
    sort_order = data.get('sort_order', 0) 
    
    

    if not product_id or not placement_type_str:
        return jsonify({'message': 'product_id and placement_type are required.'}), HTTPStatus.BAD_REQUEST

    try:
        new_placement = MerchantProductPlacementController.add_product_to_placement(
            product_id=int(product_id),
            placement_type_str=placement_type_str,
            sort_order=sort_order
           
        )
        return jsonify(new_placement.serialize()), HTTPStatus.CREATED
    except PermissionError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.FORBIDDEN
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except NotFound as e: 
        return jsonify({'message': getattr(e, 'description', str(e))}), HTTPStatus.NOT_FOUND
    except RuntimeError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback() 
        current_app.logger.error(f"Merchant: Error adding product to placement: {e}")
        return jsonify({'message': "An unexpected error occurred."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements/<int:placement_id>/sort-order', methods=['PUT'])
@merchant_role_required
def update_merchant_product_placement_sort_order(placement_id):
    """Updates the sort order of a specific product placement."""
    data = request.get_json()
    if not data or 'sort_order' not in data:
        return jsonify({'message': 'Missing sort_order in request body.'}), HTTPStatus.BAD_REQUEST

    try:
        new_sort_order = int(data['sort_order'])
        updated_placement = MerchantProductPlacementController.update_placement_sort_order(
            placement_id=placement_id,
            new_sort_order=new_sort_order
        )
        return jsonify(updated_placement.serialize()), HTTPStatus.OK
    except ValueError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except NotFound as e: 
        return jsonify({'message': getattr(e, 'description', str(e))}), HTTPStatus.NOT_FOUND
    except RuntimeError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Merchant: Error updating sort order for placement {placement_id}: {e}")
        return jsonify({'message': "An unexpected error occurred."}), HTTPStatus.INTERNAL_SERVER_ERROR

@merchant_dashboard_bp.route('/product-placements/<int:placement_id>', methods=['DELETE'])
@merchant_role_required
def remove_merchant_product_from_placement(placement_id):
    """Hard deletes a product placement, freeing up a slot for the merchant."""
    try:
        MerchantProductPlacementController.remove_product_from_placement(placement_id)
        return '', HTTPStatus.NO_CONTENT 
    except NotFound as e: 
        return jsonify({'message': getattr(e, 'description', str(e))}), HTTPStatus.NOT_FOUND
    except RuntimeError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Merchant: Error removing product placement {placement_id}: {e}")
        return jsonify({'message': "An unexpected error occurred."}), HTTPStatus.INTERNAL_SERVER_ERROR