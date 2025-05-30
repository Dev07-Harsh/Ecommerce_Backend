from flask import Blueprint, request, jsonify, current_app
from auth.utils import super_admin_role_required
from flask_jwt_extended import get_jwt_identity
import cloudinary
import cloudinary.uploader
from common.database import db
from models.brand import Brand
from models.category import Category
from models.attribute import Attribute
from models.category_attribute import CategoryAttribute
from sqlalchemy.exc import IntegrityError
from http import HTTPStatus
from datetime import datetime, timezone 
import re

from controllers.superadmin.category_controller import CategoryController
from controllers.superadmin.attribute_controller import AttributeController
from controllers.superadmin.brand_controller import BrandController
from controllers.superadmin.brand_request_controller import BrandRequestController
from controllers.superadmin.promotion_controller import PromotionController
from controllers.superadmin.review_controller import ReviewController
from controllers.superadmin.category_attribute_controller import CategoryAttributeController 
from controllers.superadmin.homepage_controller import HomepageController


superadmin_bp = Blueprint('superadmin_bp', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}  # removed extension type .svg and .gif 

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── CATEGORY ─────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/categories', methods=['GET'])
@super_admin_role_required
def list_categories():
    """
    Get list of all categories.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    responses:
      200:
        description: List of categories retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              slug:
                type: string
              parent_id:
                type: integer
              icon_url:
                type: string
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
      500:
        description: Internal server error
    """
    try:
        cats = CategoryController.list_all()
        return jsonify([c.serialize() for c in cats]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing categories: {e}")
        return jsonify({'message': 'Failed to retrieve categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/categories', methods=['POST'])
@super_admin_role_required
def create_category():
    """
    Create a new category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: formData
        name: name
        type: string
        required: true
        description: Category name
      - in: formData
        name: slug
        type: string
        required: true
        description: Category slug (URL-friendly identifier)
      - in: formData
        name: parent_id
        type: integer
        required: false
        description: ID of parent category (if this is a subcategory)
      - in: formData
        name: icon_url
        type: string
        required: false
        description: URL to category icon (if not uploading a file)
      - in: formData
        name: icon_file
        type: file
        required: false
        description: Icon file to upload (PNG, JPG, JPEG, GIF, SVG, WEBP)
    responses:
      201:
        description: Category created successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            slug:
              type: string
            parent_id:
              type: integer
            icon_url:
              type: string
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid input data
      409:
        description: Conflict - Category with this slug already exists
      500:
        description: Internal server error
    """
   
    name = request.form.get('name')
    slug = request.form.get('slug')

    if not name or not name.strip():
        return jsonify({'message': 'Name is required'}), HTTPStatus.BAD_REQUEST
    if not slug or not slug.strip():
        return jsonify({'message': 'Slug is required'}), HTTPStatus.BAD_REQUEST

    category_data = {
        'name': name.strip(),
        'slug': slug.strip()
    }

    
    raw_parent_id = request.form.get('parent_id')
    if raw_parent_id and raw_parent_id.strip():
        try:
            category_data['parent_id'] = int(raw_parent_id)
        except ValueError:
            return jsonify({'message': 'Invalid parent_id format. Must be an integer.'}), HTTPStatus.BAD_REQUEST
    else:
        category_data['parent_id'] = None

    
    category_data['icon_url'] = request.form.get('icon_url', None)
    if category_data['icon_url'] == '':
        category_data['icon_url'] = None


    
    icon_url_from_cloudinary = None
    if 'icon_file' in request.files:
        file = request.files['icon_file']
        
        
        if file and file.filename and file.filename.strip() != '':
            if not allowed_file(file.filename):
                return jsonify({'message': f"Invalid icon file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST
            
            try:
                
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="category_icons",  
                    resource_type="image"
                )
                
                icon_url_from_cloudinary = upload_result.get('secure_url')
                
                if not icon_url_from_cloudinary:
                   
                    current_app.logger.error("Cloudinary upload succeeded but no secure_url was returned.")
                    return jsonify({'message': 'Cloudinary upload succeeded but did not return a URL.'}), HTTPStatus.INTERNAL_SERVER_ERROR
                
                
                category_data['icon_url'] = icon_url_from_cloudinary

            except cloudinary.exceptions.Error as e:
                current_app.logger.error(f"Cloudinary upload failed: {e}")
                return jsonify({'message': f"Cloudinary icon upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
            except Exception as e: 
                current_app.logger.error(f"An error occurred during icon file upload: {e}")
                return jsonify({'message': f"An error occurred during icon file upload: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
        elif file.filename == '' and 'icon_file' in request.files:
           
            pass

   
    try:
        cat = CategoryController.create(category_data) 
        return jsonify(cat.serialize()), HTTPStatus.CREATED
    except IntegrityError as e:
        db.session.rollback()
       
        current_app.logger.error(f"IntegrityError creating category: {e}")
        if "unique constraint" in str(e.orig).lower() or (hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505'):
             return jsonify({'message': 'A category with this slug already exists.'}), HTTPStatus.CONFLICT
        return jsonify({'message': 'Failed to create category due to a data conflict (e.g., duplicate slug or invalid parent_id).'}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating category: {e}")
        return jsonify({'message': f'Could not create category: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>', methods=['PUT'])
@super_admin_role_required
def update_category(cid):
    """
    Update an existing category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Category name
            slug:
              type: string
              description: Category slug (URL-friendly identifier)
            parent_id:
              type: integer
              description: ID of parent category (if this is a subcategory)
            icon_url:
              type: string
              description: URL to category icon
    responses:
      200:
        description: Category updated successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            slug:
              type: string
            parent_id:
              type: integer
            icon_url:
              type: string
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid input data
      404:
        description: Category not found
      409:
        description: Conflict - Category with this slug already exists
      500:
        description: Internal server error
    """
   
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided for update'}), HTTPStatus.BAD_REQUEST
    
   
    if 'parent_id' in data and data['parent_id'] is not None:
        if data['parent_id'] == '': 
            data['parent_id'] = None
        else:
            try:
                data['parent_id'] = int(data['parent_id'])
            except (ValueError, TypeError):
                 return jsonify({'message': 'Invalid parent_id format. Must be an integer or null.'}), HTTPStatus.BAD_REQUEST

    try:
        
        cat = CategoryController.update(cid, data)
        return jsonify(cat.serialize()), HTTPStatus.OK
    except IntegrityError as e: 
        db.session.rollback()
        current_app.logger.error(f"IntegrityError updating category {cid}: {e}")
        if "unique constraint" in str(e.orig).lower() or (hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505'):
            return jsonify({'message': 'Update failed. A category with the new slug might already exist.'}), HTTPStatus.CONFLICT
        return jsonify({'message': 'Update failed due to a data conflict (e.g., duplicate slug or invalid parent_id).'}), HTTPStatus.CONFLICT
    except FileNotFoundError: 
        return jsonify({'message': 'Category not found'}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating category {cid}: {e}")
        return jsonify({'message': f'Could not update category: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>', methods=['DELETE'])
@super_admin_role_required
def delete_category(cid):
    """
    Delete a category from the database.
    ---
    tags:
      - SuperAdmin - Categories
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
        description: Category deleted successfully
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
            icon_url:
              type: string
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        cat = CategoryController.delete(cid)
        return jsonify(cat.serialize()), HTTPStatus.OK
    except FileNotFoundError: 
        return jsonify({'message': 'Category not found'}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category {cid}: {e}")
        return jsonify({'message': f'Could not delete category: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/upload_icon', methods=['POST'])
@super_admin_role_required
def upload_category_icon(cid):
    """
    Upload an icon for a category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: formData
        name: file
        type: file
        required: true
        description: Icon file to upload (PNG, JPG, JPEG, WEBP)
    responses:
      200:
        description: Icon uploaded successfully
        schema:
          type: object
          properties:
            message:
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
                parent_id:
                  type: integer
                icon_url:
                  type: string
                created_at:
                  type: string
                  format: date-time
                updated_at:
                  type: string
                  format: date-time
      400:
        description: Bad request - Invalid file or missing file
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        
        category = Category.query.filter_by(id=cid).first()
        if not category:
            return jsonify({'message': 'Category not found or has been deleted'}), HTTPStatus.NOT_FOUND

        if 'file' not in request.files:
            return jsonify({'message': 'No file part in the request'}), HTTPStatus.BAD_REQUEST
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), HTTPStatus.BAD_REQUEST

        if not allowed_file(file.filename):
            return jsonify({'message': f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST

        public_id_for_cloudinary = f"category_icons/category_{cid}_{file.filename.rsplit('.', 1)[0]}"

        upload_result = cloudinary.uploader.upload(
            file,
            folder="category_icons",
            public_id=public_id_for_cloudinary,
            overwrite=True,
            resource_type="image"
        )
        
        icon_url = upload_result.get('secure_url')
        if not icon_url:
            current_app.logger.error(f"Cloudinary upload for category {cid} succeeded but no secure_url.")
            return jsonify({'message': 'Cloudinary did not return a URL'}), HTTPStatus.INTERNAL_SERVER_ERROR

        category.icon_url = icon_url
       
        db.session.commit()

        return jsonify({
            'message': 'Icon uploaded and category updated successfully',
            'category': category.serialize()
        }), HTTPStatus.OK

    except cloudinary.exceptions.Error as e:
        current_app.logger.error(f"Cloudinary upload failed for category {cid}: {e}")
        return jsonify({'message': f"Cloudinary upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
   
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading icon for category {cid}: {e}")
        return jsonify({'message': f"An unexpected error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR



# ── BRAND REQUESTS ────────────────────────────────────────────────────────────────
@superadmin_bp.route('/brand-requests', methods=['GET'])
@super_admin_role_required
def list_brand_requests():
    """
    Get list of pending brand requests.
    ---
    tags:
      - SuperAdmin - Brand Requests
    security:
      - Bearer: []
    responses:
      200:
        description: List of pending brand requests retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              merchant_id:
                type: integer
              brand_name:
                type: string
              brand_description:
                type: string
              status:
                type: string
                enum: [PENDING, APPROVED, REJECTED]
              submitted_at:
                type: string
                format: date-time
              processed_at:
                type: string
                format: date-time
              processed_by:
                type: integer
              notes:
                type: string
      500:
        description: Internal server error
    """
    try:
        reqs = BrandRequestController.list_pending()
        
        return jsonify([r.serialize() for r in reqs]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing brand requests: {e}")
        return jsonify({'message': 'Failed to retrieve brand requests.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brand-requests/<int:rid>/approve', methods=['POST'])
@super_admin_role_required
def approve_brand_request(rid):
    """
    Approve a brand request and create a new brand.
    ---
    tags:
      - SuperAdmin - Brand Requests
    security:
      - Bearer: []
    parameters:
      - in: path
        name: rid
        type: integer
        required: true
        description: Brand request ID
      - in: formData
        name: brand_icon_file
        type: file
        required: false
        description: Brand icon file to upload (PNG, JPG, JPEG, GIF, SVG, WEBP)
    responses:
      201:
        description: Brand request approved and brand created successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            slug:
              type: string
            icon_url:
              type: string
            approved_by:
              type: integer
            approved_at:
              type: string
              format: date-time
            created_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid file
      404:
        description: Brand request not found
      409:
        description: Conflict - Brand with this name or slug already exists
      500:
        description: Internal server error
    """
    user_id = get_jwt_identity()
    icon_url_from_cloudinary = None

    if 'brand_icon_file' in request.files:
        file = request.files['brand_icon_file']
        if file and file.filename and file.filename.strip() != '':
            if not allowed_file(file.filename):
                return jsonify({'message': f"Invalid brand icon file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST
            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="brand_icons",
                    resource_type="image"
                )
                icon_url_from_cloudinary = upload_result.get('secure_url')
                if not icon_url_from_cloudinary:
                    current_app.logger.error(f"Cloudinary upload for brand request {rid} succeeded but no secure_url.")
                    return jsonify({'message': 'Cloudinary upload succeeded but did not return a URL.'}), HTTPStatus.INTERNAL_SERVER_ERROR
            except cloudinary.exceptions.Error as e:
                current_app.logger.error(f"Cloudinary upload failed for brand request {rid}: {e}")
                return jsonify({'message': f"Cloudinary icon upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
            except Exception as e:
                current_app.logger.error(f"Error during brand icon file upload for request {rid}: {e}")
                return jsonify({'message': f"An error occurred during brand icon file upload: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
        elif file.filename == '' and 'brand_icon_file' in request.files:
            pass # No file chosen

    try:
        
        created_brand = BrandRequestController.approve(rid, user_id, icon_url=icon_url_from_cloudinary)
        # Ensure Brand.serialize() includes icon_url
        return jsonify(created_brand.serialize()), HTTPStatus.CREATED 
    except FileNotFoundError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except IntegrityError as e:
        db.session.rollback()
        error_message = e.args[0] if e.args else "Data conflict during brand approval."
        current_app.logger.error(f"Data conflict approving brand request {rid}: {error_message}")
        return jsonify({'message': error_message}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving brand request {rid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int): 
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': f'Could not approve brand request: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brand-requests/<int:rid>/reject', methods=['POST'])
@super_admin_role_required
def reject_brand_request(rid):
    """
    Reject a brand request.
    ---
    tags:
      - SuperAdmin - Brand Requests
    security:
      - Bearer: []
    parameters:
      - in: path
        name: rid
        type: integer
        required: true
        description: Brand request ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - notes
          properties:
            notes:
              type: string
              description: Reason for rejection
    responses:
      200:
        description: Brand request rejected successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            merchant_id:
              type: integer
            brand_name:
              type: string
            brand_description:
              type: string
            status:
              type: string
              enum: [REJECTED]
            submitted_at:
              type: string
              format: date-time
            processed_at:
              type: string
              format: date-time
            processed_by:
              type: integer
            notes:
              type: string
      400:
        description: Bad request - Missing rejection notes
      404:
        description: Brand request not found
      500:
        description: Internal server error
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Rejection notes are required in JSON body.'}), HTTPStatus.BAD_REQUEST
    
    notes = data.get('notes')
    if notes is None:
        return jsonify({'message': 'Rejection notes (`notes` field) are required.'}), HTTPStatus.BAD_REQUEST

    try:
        br = BrandRequestController.reject(rid, user_id, notes)
        return jsonify(br.serialize()), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting brand request {rid}: {e}")
        if hasattr(e, 'code') and isinstance(e.code, int):
            return jsonify({'message': getattr(e, 'description', str(e))}), e.code
        return jsonify({'message': f'Could not reject brand request: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── BRANDS ────────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/brands', methods=['GET'])
@super_admin_role_required
def list_brands():
    """
    Get list of all brands.
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
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
              approved_by:
                type: integer
              approved_at:
                type: string
                format: date-time
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
              deleted_at:
                type: string
                format: date-time
      500:
        description: Internal server error
    """
    try:
        brands_list = BrandController.list_all()
        
        return jsonify([b.serialize() for b in brands_list]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing brands: {e}")
        return jsonify({'message': 'Failed to retrieve brands.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands', methods=['POST'])
@super_admin_role_required
def create_brand_directly():
    """
    Create a new brand directly (not from a brand request).
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
    parameters:
      - in: formData
        name: name
        type: string
        required: true
        description: Brand name
      - in: formData
        name: slug
        type: string
        required: false
        description: Brand slug (URL-friendly identifier). If not provided, will be generated from name.
      - in: formData
        name: icon_url
        type: string
        required: false
        description: URL to brand icon (if not uploading a file)
      - in: formData
        name: icon_file
        type: file
        required: false
        description: Icon file to upload (PNG, JPG, JPEG, GIF, SVG, WEBP)
    responses:
      201:
        description: Brand created successfully
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
            approved_by:
              type: integer
            approved_at:
              type: string
              format: date-time
            created_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid input data
      409:
        description: Conflict - Brand with this name or slug already exists
      500:
        description: Internal server error
    """ 
    name = request.form.get('name', '').strip()
    slug_provided = request.form.get('slug', '').strip()

    if not name:
        return jsonify({'message': 'Brand name is required'}), HTTPStatus.BAD_REQUEST

    slug = ""
    if slug_provided:
        slug = slug_provided
        if Brand.query.filter_by(slug=slug, deleted_at=None).first():
            return jsonify({'message': f"A brand with the provided slug '{slug}' already exists."}), HTTPStatus.CONFLICT
    else:
        base_slug = name.lower()
        base_slug = re.sub(r'\s+', '-', base_slug)
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
        base_slug = re.sub(r'-+', '-', base_slug).strip('-')
        if not base_slug:
            temp_brand_check = Brand.query.order_by(Brand.brand_id.desc()).first()
            next_id = (temp_brand_check.brand_id + 1) if temp_brand_check else 1
            base_slug = f"brand-{next_id}"

        temp_slug = base_slug
        counter = 1
        while Brand.query.filter_by(slug=temp_slug, deleted_at=None).first():
            temp_slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > 100:
                 current_app.logger.error(f"Could not generate a unique slug for direct brand creation: {name}")
                 return jsonify({'message': f"Could not generate a unique slug for brand: {name}. Try providing a unique slug manually."}), HTTPStatus.INTERNAL_SERVER_ERROR
        slug = temp_slug
    
    brand_data = {
        'name': name,
        'slug': slug,
        'approved_by': get_jwt_identity(),
        'approved_at': datetime.now(timezone.utc),
        'icon_url': None 
    }

    icon_url_from_text = request.form.get('icon_url', None)
    if icon_url_from_text and icon_url_from_text.strip():
        brand_data['icon_url'] = icon_url_from_text.strip()

    if 'icon_file' in request.files:
        file = request.files['icon_file']
        if file and file.filename and file.filename.strip() != '':
            if not allowed_file(file.filename):
                return jsonify({'message': f"Invalid icon file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST
            try:
                upload_result = cloudinary.uploader.upload(file, folder="brand_icons", resource_type="image")
                icon_url_from_cloudinary = upload_result.get('secure_url')
                if not icon_url_from_cloudinary:
                    current_app.logger.error("Cloudinary brand icon upload (direct create) succeeded but no secure_url.")
                    return jsonify({'message': 'Cloudinary upload did not return a URL.'}), HTTPStatus.INTERNAL_SERVER_ERROR
                brand_data['icon_url'] = icon_url_from_cloudinary 
            except cloudinary.exceptions.Error as e:
                current_app.logger.error(f"Cloudinary icon upload failed (direct brand create): {e}")
                return jsonify({'message': f"Cloudinary icon upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
            except Exception as e:
                current_app.logger.error(f"An error occurred during icon file upload (direct brand create): {e}")
                return jsonify({'message': f"An error occurred during icon file upload: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
    try:
        new_brand = BrandController.create(brand_data)
        return jsonify(new_brand.serialize()), HTTPStatus.CREATED
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"IntegrityError creating brand directly: {e}")
        if "unique constraint" in str(e.orig).lower() or (hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505'):
             return jsonify({'message': f"A brand with this name or slug already exists: {name} / {slug}"}), HTTPStatus.CONFLICT
        return jsonify({'message': 'Failed to create brand due to a data conflict.'}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating brand directly: {e}")
        return jsonify({'message': f'Could not create brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands/<int:bid>/upload_icon', methods=['POST'])
@super_admin_role_required
def upload_brand_icon(bid):
    """
    Upload an icon for a brand.
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: bid
        type: integer
        required: true
        description: Brand ID
      - in: formData
        name: file
        type: file
        required: true
        description: Icon file to upload (PNG, JPG, JPEG, WEBP)
    responses:
      200:
        description: Icon uploaded successfully
        schema:
          type: object
          properties:
            message:
              type: string
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
                approved_by:
                  type: integer
                approved_at:
                  type: string
                  format: date-time
                created_at:
                  type: string
                  format: date-time
      400:
        description: Bad request - Invalid file or missing file
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    try:
        
        brand = Brand.query.filter_by(brand_id=bid).first()
        if not brand:
            return jsonify({'message': 'Brand not found or has been deleted'}), HTTPStatus.NOT_FOUND

        if 'file' not in request.files:
            return jsonify({'message': 'No file part in the request'}), HTTPStatus.BAD_REQUEST
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), HTTPStatus.BAD_REQUEST

        if not allowed_file(file.filename):
            return jsonify({'message': f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), HTTPStatus.BAD_REQUEST

        public_id_for_cloudinary = f"brand_icons/brand_{bid}_{file.filename.rsplit('.', 1)[0]}"

        upload_result = cloudinary.uploader.upload(
            file,
            folder="brand_icons",
            public_id=public_id_for_cloudinary,
            overwrite=True,
            resource_type="image"
        )
        
        icon_url = upload_result.get('secure_url')
        if not icon_url:
            current_app.logger.error(f"Cloudinary upload for brand {bid} succeeded but no secure_url.")
            return jsonify({'message': 'Cloudinary did not return a URL'}), HTTPStatus.INTERNAL_SERVER_ERROR

        brand.icon_url = icon_url
        db.session.add(brand)
        db.session.commit()

        return jsonify({
            'message': 'Brand icon uploaded and updated successfully',
            'brand': brand.serialize()
        }), HTTPStatus.OK

    except cloudinary.exceptions.Error as e:
        current_app.logger.error(f"Cloudinary upload failed for brand {bid}: {e}")
        return jsonify({'message': f"Cloudinary upload failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading icon for brand {bid}: {e}")
        return jsonify({'message': f"An unexpected error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands/<int:bid>', methods=['PUT'])
@super_admin_role_required
def update_brand(bid):
    """
    Update an existing brand.
    Now supports both:
      - application/json  (just name/slug)
      - multipart/form-data (name/slug + icon_file)
    """
    # Determine content type
    content_type = request.content_type or ''
    update_data = {}

    # --- 1) JSON path ---
    if content_type.startswith('application/json'):
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'message': 'No JSON body provided'}), HTTPStatus.BAD_REQUEST
        if 'name' in data and data['name'].strip():
            update_data['name'] = data['name'].strip()
        if 'slug' in data and data['slug'].strip():
            update_data['slug'] = data['slug'].strip()

    # --- 2) multipart/form-data path ---
    elif content_type.startswith('multipart/form-data'):
        # text fields
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        if name:
            update_data['name'] = name
        if slug:
            update_data['slug'] = slug

        # file field
        file = request.files.get('icon_file')
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({'message': f'Invalid icon file type. Allowed: {ALLOWED_EXTENSIONS}'}), HTTPStatus.BAD_REQUEST

            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="brand_icons",
                    public_id=f"brand_{bid}_{file.filename.rsplit('.', 1)[0]}",
                    overwrite=True,
                    resource_type="image"
                )
                new_url = upload_result.get('secure_url')
                if not new_url:
                    raise ValueError("No secure_url from Cloudinary")
                update_data['icon_url'] = new_url
            except Exception as e:
                current_app.logger.error(f"Cloudinary upload failed in update: {e}")
                return jsonify({'message': f'Icon upload failed: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return jsonify({'message': 'Unsupported Content-Type. Use JSON or multipart/form-data.'}), HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    # must have at least one field to update
    if not update_data:
        return jsonify({'message': 'No updatable fields provided.'}), HTTPStatus.BAD_REQUEST

    # Perform update
    try:
        updated_brand = BrandController.update(bid, update_data)
        return jsonify(updated_brand.serialize()), HTTPStatus.OK

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"IntegrityError updating brand {bid}: {e}")
        return jsonify({'message': 'A brand with that name or slug already exists.'}), HTTPStatus.CONFLICT

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating brand {bid}: {e}")
        return jsonify({'message': f'Could not update brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/brands/<int:bid>', methods=['DELETE'])
@super_admin_role_required
def delete_brand(bid):
    """
    Hard-delete a brand (remove it completely).
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: bid
        type: integer
        required: true
        description: Brand ID
    responses:
      204:
        description: Brand deleted successfully (no content)
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    try:
        BrandController.delete(bid)
        return '', HTTPStatus.NO_CONTENT
    except Exception as e:
        current_app.logger.error(f"Error hard-deleting brand {bid}: {e}")
        return jsonify({'message': f'Could not delete brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/brands/<int:bid>/restore', methods=['POST']) # Or PUT
@super_admin_role_required
def restore_brand(bid):
    """
    Restore a previously deleted brand.
    ---
    tags:
      - SuperAdmin - Brands
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
        description: Brand restored successfully
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
            approved_by:
              type: integer
            approved_at:
              type: string
              format: date-time
            created_at:
              type: string
              format: date-time
            updated_at:
              type: string
              format: date-time
            deleted_at:
              type: null
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    try:
        restored_brand = BrandController.undelete(bid)
        return jsonify(restored_brand.serialize()), HTTPStatus.OK
    except FileNotFoundError: 
        return jsonify({'message': 'Brand not found, cannot restore.'}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback() 
        current_app.logger.error(f"Error restoring brand {bid}: {e}")
        return jsonify({'message': f'Could not restore brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


# ── PROMOTIONS ────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/promotions', methods=['GET'])
@super_admin_role_required
def list_promotions():
    """
    Get list of all promotions.
    ---
    tags:
      - SuperAdmin - Promotions
    security:
      - Bearer: []
    responses:
      200:
        description: List of promotions retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              description:
                type: string
              discount_type:
                type: string
                enum: [PERCENTAGE, FIXED_AMOUNT]
              discount_value:
                type: number
              start_date:
                type: string
                format: date-time
              end_date:
                type: string
                format: date-time
              active:
                type: boolean
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
    """
    ps = PromotionController.list_all()
    return jsonify([p.serialize() for p in ps]), 200

@superadmin_bp.route('/promotions', methods=['POST'])
@super_admin_role_required
def create_promotion():
    """
    Create a new promotion.
    ---
    tags:
      - SuperAdmin - Promotions
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - discount_type
            - discount_value
          properties:
            name:
              type: string
              description: Promotion name
            description:
              type: string
              description: Promotion description
            discount_type:
              type: string
              enum: [PERCENTAGE, FIXED_AMOUNT]
              description: Type of discount
            discount_value:
              type: number
              description: Value of discount (percentage or fixed amount)
            start_date:
              type: string
              format: date-time
              description: Start date of promotion
            end_date:
              type: string
              format: date-time
              description: End date of promotion
            active:
              type: boolean
              description: Whether the promotion is active
    responses:
      201:
        description: Promotion created successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            description:
              type: string
            discount_type:
              type: string
            discount_value:
              type: number
            start_date:
              type: string
              format: date-time
            end_date:
              type: string
              format: date-time
            active:
              type: boolean
            created_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid input data
      500:
        description: Internal server error
    """
    data = request.get_json()
    p = PromotionController.create(data)
    return jsonify(p.serialize()), 201

@superadmin_bp.route('/promotions/<int:pid>', methods=['PUT'])
@super_admin_role_required
def update_promotion(pid):
    """
    Update an existing promotion.
    ---
    tags:
      - SuperAdmin - Promotions
    security:
      - Bearer: []
    parameters:
      - in: path
        name: pid
        type: integer
        required: true
        description: Promotion ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: Promotion name
            description:
              type: string
              description: Promotion description
            discount_type:
              type: string
              enum: [PERCENTAGE, FIXED_AMOUNT]
              description: Type of discount
            discount_value:
              type: number
              description: Value of discount (percentage or fixed amount)
            start_date:
              type: string
              format: date-time
              description: Start date of promotion
            end_date:
              type: string
              format: date-time
              description: End date of promotion
            active:
              type: boolean
              description: Whether the promotion is active
    responses:
      200:
        description: Promotion updated successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            description:
              type: string
            discount_type:
              type: string
            discount_value:
              type: number
            start_date:
              type: string
              format: date-time
            end_date:
              type: string
              format: date-time
            active:
              type: boolean
            updated_at:
              type: string
              format: date-time
      404:
        description: Promotion not found
      400:
        description: Bad request - Invalid input data
      500:
        description: Internal server error
    """
    data = request.get_json()
    p = PromotionController.update(pid, data)
    return jsonify(p.serialize()), 200

@superadmin_bp.route('/promotions/<int:pid>', methods=['DELETE'])
@super_admin_role_required
def delete_promotion(pid):
    """
    Delete (soft delete) a promotion.
    ---
    tags:
      - SuperAdmin - Promotions
    security:
      - Bearer: []
    parameters:
      - in: path
        name: pid
        type: integer
        required: true
        description: Promotion ID
    responses:
      200:
        description: Promotion deleted successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            active:
              type: boolean
            deleted_at:
              type: string
              format: date-time
      404:
        description: Promotion not found
      500:
        description: Internal server error
    """
    p = PromotionController.soft_delete(pid)
    return jsonify(p.serialize()), 200

# ── REVIEWS ──────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/reviews', methods=['GET'])
@super_admin_role_required
def list_reviews():
    """
    Get list of recent reviews.
    ---
    tags:
      - SuperAdmin - Reviews
    security:
      - Bearer: []
    responses:
      200:
        description: List of recent reviews retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              product_id:
                type: integer
              user_id:
                type: integer
              rating:
                type: integer
              comment:
                type: string
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
    """
    rs = ReviewController.list_recent()
    return jsonify([r.serialize() for r in rs]), 200

@superadmin_bp.route('/reviews/<int:rid>', methods=['DELETE'])
@super_admin_role_required
def delete_review(rid):
    """
    Delete a review.
    ---
    tags:
      - SuperAdmin - Reviews
    security:
      - Bearer: []
    parameters:
      - in: path
        name: rid
        type: integer
        required: true
        description: Review ID
    responses:
      200:
        description: Review deleted successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            product_id:
              type: integer
            user_id:
              type: integer
            rating:
              type: integer
            comment:
              type: string
            deleted_at:
              type: string
              format: date-time
      404:
        description: Review not found
      500:
        description: Internal server error
    """
    r = ReviewController.delete(rid)
    return jsonify(r.serialize()), 200


# ── ATTRIBUTE VALUES ─────────────────────────────────────────────────────────────
from controllers.superadmin.attribute_value_controller import AttributeValueController

@superadmin_bp.route('/attribute-values', methods=['GET'])
@super_admin_role_required
def list_attribute_values():
    """
    Get list of all attribute values.
    ---
    tags:
      - SuperAdmin - Attribute Values
    security:
      - Bearer: []
    responses:
      200:
        description: List of attribute values retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              attribute_id:
                type: integer
              value_code:
                type: string
              value_label:
                type: string
    """
    avs = AttributeValueController.list_all()
    return jsonify([ {
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    } for av in avs]), 200

@superadmin_bp.route('/attribute-values/<int:aid>', methods=['GET'])
@super_admin_role_required
def list_values_for_attribute(aid):
    """
    Get list of attribute values for a specific attribute.
    ---
    tags:
      - SuperAdmin - Attribute Values
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
        description: List of attribute values for the specified attribute retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              attribute_id:
                type: integer
              value_code:
                type: string
              value_label:
                type: string
      404:
        description: Attribute not found
    """
    avs = AttributeValueController.list_for_attribute(aid)
    return jsonify([ {
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    } for av in avs]), 200

@superadmin_bp.route('/attribute-values', methods=['POST'])
@super_admin_role_required
def create_attribute_value():
    """
    Create a new attribute value.
    ---
    tags:
      - SuperAdmin - Attribute Values
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - attribute_id
            - value_code
            - value_label
          properties:
            attribute_id:
              type: integer
              description: ID of the attribute
            value_code:
              type: string
              description: Code for the attribute value (unique identifier)
            value_label:
              type: string
              description: Display label for the attribute value
    responses:
      201:
        description: Attribute value created successfully
        schema:
          type: object
          properties:
            attribute_id:
              type: integer
            value_code:
              type: string
            value_label:
              type: string
      400:
        description: Bad request - Invalid input data
      409:
        description: Conflict - Attribute value with this code already exists
      500:
        description: Internal server error
    """
    data = request.get_json()
    av = AttributeValueController.create(data)
    return jsonify({
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    }), 201

@superadmin_bp.route('/attribute-values/<int:aid>/<value_code>', methods=['PUT'])
@super_admin_role_required
def update_attribute_value(aid, value_code):
    """
    Update an existing attribute value.
    ---
    tags:
      - SuperAdmin - Attribute Values
    security:
      - Bearer: []
    parameters:
      - in: path
        name: aid
        type: integer
        required: true
        description: Attribute ID
      - in: path
        name: value_code
        type: string
        required: true
        description: Value code to update
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            value_label:
              type: string
              description: New display label for the attribute value
    responses:
      200:
        description: Attribute value updated successfully
        schema:
          type: object
          properties:
            attribute_id:
              type: integer
            value_code:
              type: string
            value_label:
              type: string
      400:
        description: Bad request - Invalid input data
      404:
        description: Attribute value not found
      500:
        description: Internal server error
    """
    data = request.get_json()
    av = AttributeValueController.update(aid, value_code, data)
    return jsonify({
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    }), 200

@superadmin_bp.route('/attribute-values/<int:aid>/<value_code>', methods=['DELETE'])
@super_admin_role_required
def delete_attribute_value(aid, value_code):
    """
    Delete an attribute value.
    ---
    tags:
      - SuperAdmin - Attribute Values
    security:
      - Bearer: []
    parameters:
      - in: path
        name: aid
        type: integer
        required: true
        description: Attribute ID
      - in: path
        name: value_code
        type: string
        required: true
        description: Value code to delete
    responses:
      204:
        description: Attribute value deleted successfully
      404:
        description: Attribute value not found
      500:
        description: Internal server error
    """
    AttributeValueController.delete(aid, value_code)
    return '', 204


# ── ATTRIBUTES ───────────────────────────────────────────────────────────────────
@superadmin_bp.route('/attributes', methods=['GET'])
@super_admin_role_required
def list_attributes():
    """
    Get list of all attributes.
    ---
    tags:
      - SuperAdmin - Attributes
    security:
      - Bearer: []
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
              code:
                type: string
              name:
                type: string
              input_type:
                type: string
                enum: [text, number, select, multiselect, boolean]
              created_at:
                type: string
                format: date-time
    """
    try:
        attrs = AttributeController.list_all()
        return jsonify([a.serialize() for a in attrs]), HTTPStatus.OK

    except Exception as e:
        current_app.logger.error(f"Error listing attributes: {e}")
        return jsonify({'message': 'Failed to retrieve attributes.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/attributes', methods=['POST'])
@super_admin_role_required
def create_attribute():
    """
    Create a new attribute.
    ---
    tags:
      - SuperAdmin - Attributes
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - code
            - name
            - input_type
          properties:
            code:
              type: string
              description: Unique code for the attribute
            name:
              type: string
              description: Display name for the attribute
            input_type:
              type: string
              enum: [text, number, select, multiselect, boolean]
              description: Type of input for this attribute
    responses:
      201:
        description: Attribute created successfully
        schema:
          type: object
          properties:
            attribute_id:
              type: integer
            code:
              type: string
            name:
              type: string
            input_type:
              type: string
            created_at:
              type: string
              format: date-time
      400:
        description: Bad request - Invalid input data
      409:
        description: Conflict - Attribute with this code already exists
      500:
        description: Internal server error
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), HTTPStatus.BAD_REQUEST

    # Validate required fields
    required_fields = ['code', 'name', 'input_type']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    if missing_fields:
        return jsonify({
            'message': f'Missing required fields: {", ".join(missing_fields)}'
        }), HTTPStatus.BAD_REQUEST

    # Validate input_type
    valid_input_types = ['text', 'number', 'select', 'multiselect', 'boolean']
    if data['input_type'] not in valid_input_types:
        return jsonify({
            'message': f'Invalid input type. Must be one of: {", ".join(valid_input_types)}'
        }), HTTPStatus.BAD_REQUEST

    try:
        attr = AttributeController.create(data)
        return jsonify(attr.serialize()), HTTPStatus.CREATED

    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"IntegrityError creating attribute: {e}")
        if "unique constraint" in str(e.orig).lower() or \
           (hasattr(e.orig, 'pgcode') and e.orig.pgcode == '23505'):
            return jsonify({'message': 'An attribute with this code already exists.'}), HTTPStatus.CONFLICT
       

        return jsonify({'message': 'Failed to create attribute due to a data conflict.'}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating attribute: {e}")
        return jsonify({'message': f'Could not create attribute: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR
@superadmin_bp.route('/attributes/<int:attribute_id>', methods=['GET'])
@super_admin_role_required
def get_attribute(attribute_id):
    """
    Get an attribute by ID.
    ---
    tags:
      - SuperAdmin - Attributes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: attribute_id
        type: integer
        required: true
        description: Attribute ID
    responses:
      200:
        description: Attribute retrieved successfully
      404:
        description: Attribute not found
      500:
        description: Internal server error
    """
    try:
        from models.attribute import Attribute 
        attr = Attribute.query.get_or_404(attribute_id)
        return jsonify(attr.serialize()), HTTPStatus.OK
    except FileNotFoundError: 
        return jsonify({'message': 'Attribute not found'}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error fetching attribute {attribute_id}: {e}")
        return jsonify({'message': 'Could not retrieve attribute.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/attributes/<int:attribute_id>', methods=['PUT'])
@super_admin_role_required
def update_attribute(attribute_id):
    """
    Update an attribute.
    ---
    tags:
      - SuperAdmin - Attributes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: attribute_id
        type: integer
        required: true
        description: Attribute ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            input_type:
              type: string
    responses:
      200:
        description: Attribute updated successfully
      400:
        description: Bad request - Invalid input data
      404:
        description: Attribute not found
      500:
        description: Internal server error
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided for update'}), HTTPStatus.BAD_REQUEST

    if not data.get('name') and not data.get('input_type'):
        return jsonify({'message': 'No fields to update provided (name, input_type).'}), HTTPStatus.BAD_REQUEST

    try:
        attribute = AttributeController.update(attribute_id, data)
        return jsonify(attribute.serialize()), HTTPStatus.OK
    except FileNotFoundError: 
        return jsonify({'message': 'Attribute not found'}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating attribute {attribute_id}: {e}")
        return jsonify({'message': f'Could not update attribute: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/attributes/<int:attribute_id>', methods=['DELETE'])
@super_admin_role_required
def delete_attribute(attribute_id):
    """
    Delete an attribute.
    ---
    tags:
      - SuperAdmin - Attributes
    security:
      - Bearer: []
    parameters:
      - in: path
        name: attribute_id
        type: integer
        required: true
        description: Attribute ID
     responses:
      200:
        description: Attribute deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
      404:
        description: Attribute not found
      409:
        description: Conflict - Attribute is in use
      500:
        description: Internal server error
    """
    try:
        AttributeController.delete(attribute_id)
        return jsonify({'message': f'Attribute with ID {attribute_id} deleted successfully.'}), HTTPStatus.OK
    # except from_werkzeug.exceptions.NotFound:
    #     return jsonify({'message': 'Attribute not found'}), HTTPStatus.NOT_FOUND
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.warning(f"IntegrityError deleting attribute {attribute_id}: {e}")
        if "foreign key constraint" in str(e.orig).lower():
            return jsonify({'message': 'Cannot delete attribute. It is currently in use by other records.'}), HTTPStatus.CONFLICT
        return jsonify({'message': f'Database conflict: {str(e)}'}), HTTPStatus.CONFLICT
    except Exception as e: 
        db.session.rollback()
        current_app.logger.error(f"Error deleting attribute {attribute_id}: {e}")
        return jsonify({'message': f'Could not delete attribute: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── CATEGORY ATTRIBUTES (Associations) ───────────────────────────────────────────
@superadmin_bp.route('/categories/<int:cid>/attributes', methods=['GET'])
@super_admin_role_required
def list_category_attributes_for_category(cid):
    """
    Lists attributes associated with a specific category.
    ---
    tags:
      - SuperAdmin - Categories
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
        description: List of attributes associated with the category
      404:
        description: Category not found
      500:
        description: Internal server error
    """
    try:
        associations = CategoryAttributeController.list_attributes_for_category(cid)
       
        result = []
        for assoc in associations:
            
            attribute_data = None
            if assoc.attribute: 
                 attribute_data = {
                     'attribute_id': assoc.attribute.attribute_id, 
                     'name': assoc.attribute.name, 
                     'code': assoc.attribute.code
                 }

            result.append({
                'category_id': assoc.category_id,
                'attribute_id': assoc.attribute_id,
                'required_flag': assoc.required_flag,
                'attribute_details': attribute_data 
            })
        return jsonify(result), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error listing attributes for category {cid}: {e}")
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/attributes', methods=['POST'])
@super_admin_role_required
def add_attribute_to_category(cid):
    """
    Assign an attribute to a category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - attribute_id
          properties:
            attribute_id:
              type: integer
              description: ID of the attribute to assign
            required_flag:
              type: boolean
              description: Whether this attribute is required for the category
    responses:
      201:
        description: Attribute assigned to category successfully
      400:
        description: Bad request - Invalid input data
      404:
        description: Category or attribute not found
      409:
        description: Conflict - Attribute already assigned to category
      500:
        description: Internal server error
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is missing or not JSON.'}), HTTPStatus.BAD_REQUEST
    
    try:
        association = CategoryAttributeController.add_attribute_to_category(cid, data)
       
        attribute_data = None
        if association.attribute:
             attribute_data = {
                 'attribute_id': association.attribute.attribute_id,
                 'name': association.attribute.name,
                 'code': association.attribute.code
             }
        return jsonify({
            'category_id': association.category_id,
            'attribute_id': association.attribute_id,
            'required_flag': association.required_flag,
            'attribute_details': attribute_data
        }), HTTPStatus.CREATED
    except FileNotFoundError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except ValueError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except IntegrityError as e: 
        db.session.rollback()
       
        msg = e.args[0] if e.args and isinstance(e.args[0], str) else str(e.orig) if hasattr(e, 'orig') else "Data integrity conflict (e.g., association already exists)."
        return jsonify({'message': msg}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding attribute to category {cid}: {e}")
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/attributes/<int:aid>', methods=['PUT'])
@super_admin_role_required
def update_attribute_for_category(cid, aid):
    """
    Updates the required_flag of an attribute for a category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: path
        name: aid
        type: integer
        required: true
        description: Attribute ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            required_flag:
              type: boolean
              description: Whether this attribute is required for the category
    responses:
      200:
        description: Category attribute updated successfully
      400:
        description: Bad request - Invalid input data
      404:
        description: Category attribute association not found
      500:
        description: Internal server error
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is missing or not JSON.'}), HTTPStatus.BAD_REQUEST

    try:
        association = CategoryAttributeController.update_category_attribute(cid, aid, data)
        attribute_data = None
        if association.attribute:
             attribute_data = {
                 'attribute_id': association.attribute.attribute_id,
                 'name': association.attribute.name,
                 'code': association.attribute.code
             }
        return jsonify({
            'category_id': association.category_id,
            'attribute_id': association.attribute_id,
            'required_flag': association.required_flag,
            'attribute_details': attribute_data
        }), HTTPStatus.OK
    except FileNotFoundError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except ValueError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating attribute {aid} for category {cid}: {e}")
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/attributes/<int:aid>', methods=['DELETE'])
@super_admin_role_required
def remove_attribute_from_category(cid, aid):
    """
    Removes an attribute from a category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: path
        name: aid
        type: integer
        required: true
        description: Attribute ID
    responses:
      204:
        description: Attribute removed from category successfully
      404:
        description: Category attribute association not found
      500:
        description: Internal server error
    """
    try:
        CategoryAttributeController.remove_attribute_from_category(cid, aid)
        return '', HTTPStatus.NO_CONTENT
    except FileNotFoundError as e: 
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing attribute {aid} from category {cid}: {e}")
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── CATEGORY ATTRIBUTES ─────────────────────────────────────────────────────────
@superadmin_bp.route('/categories/<int:cid>/assign-attribute', methods=['POST'])
@super_admin_role_required
def assign_attribute_to_category(cid):
    """
    Assign an attribute to a category.
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    parameters:
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - attribute_id
          properties:
            attribute_id:
              type: integer
              description: ID of the attribute to assign
            required_flag:
              type: boolean
              description: Whether this attribute is required for the category
    responses:
      200:
        description: Attribute assigned to category successfully
        schema:
          type: object
          properties:
            category_id:
              type: integer
            attribute_id:
              type: integer
            required_flag:
              type: boolean
      400:
        description: Bad request - Invalid input data
      404:
        description: Category or attribute not found
      409:
        description: Conflict - Attribute already assigned to category
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data or 'attribute_id' not in data:
            return jsonify({'message': 'Attribute ID is required'}), HTTPStatus.BAD_REQUEST

        attribute_id = data.get('attribute_id')
        required_flag = data.get('required_flag', False)

        # Get the category - removed deleted_at filter
        category = Category.query.filter_by(category_id=cid).first()
        if not category:
            return jsonify({'message': 'Category not found'}), HTTPStatus.NOT_FOUND

        # Get the attribute - removed deleted_at filter
        attribute = Attribute.query.filter_by(attribute_id=attribute_id).first()
        if not attribute:
            return jsonify({'message': 'Attribute not found'}), HTTPStatus.NOT_FOUND

        # Check if attribute is already assigned to category
        existing = CategoryAttribute.query.filter_by(
            category_id=cid,
            attribute_id=attribute_id
        ).first()

        if existing:
            return jsonify({'message': 'Attribute is already assigned to this category'}), HTTPStatus.CONFLICT

        # Create new category attribute
        category_attribute = CategoryAttribute(
            category_id=cid,
            attribute_id=attribute_id,
            required_flag=required_flag
        )

        db.session.add(category_attribute)
        db.session.commit()

        return jsonify({
            'category_id': category_attribute.category_id,
            'attribute_id': category_attribute.attribute_id,
            'required_flag': category_attribute.required_flag
        }), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error assigning attribute to category: {e}")
        return jsonify({'message': f'Could not assign attribute to category: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── BRAND CATEGORIES ────────────────────────────────────────────────────────────
@superadmin_bp.route('/brands/<int:bid>/categories/<int:cid>', methods=['POST'])
@super_admin_role_required
def add_category_to_brand(bid, cid):
    """
    Add a category to a brand.
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: bid
        type: integer
        required: true
        description: Brand ID
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
    responses:
      200:
        description: Category added to brand successfully
        schema:
          type: object
          properties:
            brand_id:
              type: integer
            name:
              type: string
            categories:
              type: array
              items:
                type: object
                properties:
                  category_id:
                    type: integer
                  name:
                    type: string
      404:
        description: Brand or category not found
      500:
        description: Internal server error
    """
    try:
        brand = BrandController.add_category(bid, cid)
        return jsonify(brand.serialize()), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding category {cid} to brand {bid}: {e}")
        return jsonify({'message': f'Could not add category to brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands/<int:bid>/categories/<int:cid>', methods=['DELETE'])
@super_admin_role_required
def remove_category_from_brand(bid, cid):
    """
    Remove a category from a brand.
    ---
    tags:
      - SuperAdmin - Brands
    security:
      - Bearer: []
    parameters:
      - in: path
        name: bid
        type: integer
        required: true
        description: Brand ID
      - in: path
        name: cid
        type: integer
        required: true
        description: Category ID
    responses:
      200:
        description: Category removed from brand successfully
        schema:
          type: object
          properties:
            brand_id:
              type: integer
            name:
              type: string
            categories:
              type: array
              items:
                type: object
                properties:
                  category_id:
                    type: integer
                  name:
                    type: string
      404:
        description: Brand or category not found
      500:
        description: Internal server error
    """
    try:
        brand = BrandController.remove_category(bid, cid)
        return jsonify(brand.serialize()), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing category {cid} from brand {bid}: {e}")
        return jsonify({'message': f'Could not remove category from brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands/<int:bid>/categories', methods=['GET'])
@super_admin_role_required
def get_brand_categories(bid):
    """
    Get all categories associated with a brand.
    ---
    tags:
      - SuperAdmin - Brands
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
              icon_url:
                type: string
      404:
        description: Brand not found
      500:
        description: Internal server error
    """
    try:
        categories = BrandController.get_categories(bid)
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error getting categories for brand {bid}: {e}")
        return jsonify({'message': f'Could not get brand categories: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/categories/main', methods=['GET'])
@super_admin_role_required
def list_main_categories():
    """
    Get list of main categories (categories without parent).
    ---
    tags:
      - SuperAdmin - Categories
    security:
      - Bearer: []
    responses:
      200:
        description: List of main categories retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              slug:
                type: string
              parent_id:
                type: integer
              icon_url:
                type: string
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
      500:
        description: Internal server error
    """
    try:
        cats = CategoryController.get_main_categories()
        return jsonify([c.serialize() for c in cats]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing main categories: {e}")
        return jsonify({'message': 'Failed to retrieve main categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/homepage/categories', methods=['GET'])
@super_admin_role_required
def get_featured_categories():
    """
    Get list of featured categories for homepage.
    ---
    tags:
      - SuperAdmin - Homepage
    security:
      - Bearer: []
    responses:
      200:
        description: List of featured categories retrieved successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              category_id:
                type: integer
              display_order:
                type: integer
              is_active:
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
              created_at:
                type: string
                format: date-time
              updated_at:
                type: string
                format: date-time
      500:
        description: Internal server error
    """
    try:
        categories = HomepageController.get_featured_categories()
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error getting featured categories: {e}")
        return jsonify({'message': 'Failed to retrieve featured categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/homepage/categories', methods=['POST'])
@super_admin_role_required
def update_featured_categories():
    """
    Update the featured categories for homepage.
    ---
    tags:
      - SuperAdmin - Homepage
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - category_ids
          properties:
            category_ids:
              type: array
              items:
                type: integer
              description: List of category IDs to feature on homepage
    responses:
      200:
        description: Featured categories updated successfully
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              category_id:
                type: integer
              display_order:
                type: integer
              is_active:
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
      400:
        description: Bad request - Invalid input data
      500:
        description: Internal server error
    """
    try:
        data = request.get_json()
        if not data or 'category_ids' not in data:
            return jsonify({'message': 'category_ids is required'}), HTTPStatus.BAD_REQUEST

        categories = HomepageController.update_featured_categories(data['category_ids'])
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error updating featured categories: {e}")
        return jsonify({'message': 'Failed to update featured categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

