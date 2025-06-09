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
from flask_cors import cross_origin

from controllers.superadmin.category_controller import CategoryController
from controllers.superadmin.attribute_controller import AttributeController
from controllers.superadmin.brand_controller import BrandController
from controllers.superadmin.brand_request_controller import BrandRequestController
from controllers.superadmin.promotion_controller import PromotionController
from controllers.superadmin.review_controller import ReviewController
from controllers.superadmin.category_attribute_controller import CategoryAttributeController 
from controllers.superadmin.homepage_controller import HomepageController
from controllers.superadmin.product_monitoring_controller import ProductMonitoringController
from controllers.superadmin.product_controller import ProductController
from controllers.superadmin.carousel_controller import CarouselController


superadmin_bp = Blueprint('superadmin_bp', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}  # removed extension type .svg and .gif 

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── CATEGORY ─────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/categories', methods=['GET'])
@super_admin_role_required
def list_categories():
    
    try:
        cats = CategoryController.list_all()
        return jsonify([c.serialize() for c in cats]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing categories: {e}")
        return jsonify({'message': 'Failed to retrieve categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/categories', methods=['POST'])
@super_admin_role_required
def create_category():
    
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
    # Determine content type
    content_type = request.content_type or ''
    update_data = {}

    # --- 1) JSON path ---
    if content_type.startswith('application/json'):
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'message': 'No JSON body provided'}), HTTPStatus.BAD_REQUEST
        update_data = data

    # --- 2) multipart/form-data path ---
    elif content_type.startswith('multipart/form-data'):
        # text fields
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        if name:
            update_data['name'] = name
        if slug:
            update_data['slug'] = slug

        # Handle parent_id
        parent_id = request.form.get('parent_id')
        if parent_id is not None:
            if parent_id == '':
                update_data['parent_id'] = None
            else:
                try:
                    update_data['parent_id'] = int(parent_id)
                except (ValueError, TypeError):
                    return jsonify({'message': 'Invalid parent_id format. Must be an integer or null.'}), HTTPStatus.BAD_REQUEST

        # file field
        file = request.files.get('icon_file')
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({'message': f'Invalid icon file type. Allowed: {ALLOWED_EXTENSIONS}'}), HTTPStatus.BAD_REQUEST

            try:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder="category_icons",
                    public_id=f"category_{cid}_{file.filename.rsplit('.', 1)[0]}",
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

    try:
        cat = CategoryController.update(cid, update_data)
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
    
    try:
        requests = BrandRequestController.list_pending()
        return jsonify([r.serialize() for r in requests]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing brand requests: {e}")
        return jsonify({'message': 'Failed to retrieve brand requests.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brand-requests/<int:rid>/approve', methods=['POST'])
@super_admin_role_required
def approve_brand_request(rid):
    
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

    try:
        brand = BrandRequestController.approve(rid, user_id, icon_url=icon_url_from_cloudinary)
        return jsonify(brand.serialize()), HTTPStatus.CREATED
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Data conflict approving brand request {rid}: {e}")
        return jsonify({'message': 'A brand with this name or slug already exists.'}), HTTPStatus.CONFLICT
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving brand request {rid}: {e}")
        return jsonify({'message': f'Could not approve brand request: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brand-requests/<int:rid>/reject', methods=['POST'])
@super_admin_role_required
def reject_brand_request(rid):
    
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Rejection notes are required in JSON body.'}), HTTPStatus.BAD_REQUEST
    
    notes = data.get('notes')
    if notes is None:
        return jsonify({'message': 'Rejection notes (`notes` field) are required.'}), HTTPStatus.BAD_REQUEST

    try:
        request = BrandRequestController.reject(rid, user_id, notes)
        return jsonify(request.serialize()), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting brand request {rid}: {e}")
        return jsonify({'message': f'Could not reject brand request: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── BRANDS ────────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/brands', methods=['GET'])
@super_admin_role_required
def list_brands():
    
    try:
        brands_list = BrandController.list_all()
        
        return jsonify([b.serialize() for b in brands_list]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing brands: {e}")
        return jsonify({'message': 'Failed to retrieve brands.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/brands', methods=['POST'])
@super_admin_role_required
def create_brand_directly():
     
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
    
    try:
        BrandController.delete(bid)
        return '', HTTPStatus.NO_CONTENT
    except Exception as e:
        current_app.logger.error(f"Error hard-deleting brand {bid}: {e}")
        return jsonify({'message': f'Could not delete brand: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/brands/<int:bid>/restore', methods=['POST']) # Or PUT
@super_admin_role_required
def restore_brand(bid):
    
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
    
    ps = PromotionController.list_all()
    return jsonify([p.serialize() for p in ps]), 200

@superadmin_bp.route('/promotions', methods=['POST'])
@super_admin_role_required
def create_promotion():
    
    data = request.get_json()
    p = PromotionController.create(data)
    return jsonify(p.serialize()), 201

@superadmin_bp.route('/promotions/<int:pid>', methods=['PUT'])
@super_admin_role_required
def update_promotion(pid):
    
    data = request.get_json()
    p = PromotionController.update(pid, data)
    return jsonify(p.serialize()), 200

@superadmin_bp.route('/promotions/<int:pid>', methods=['DELETE'])
@super_admin_role_required
def delete_promotion(pid):
    
    p = PromotionController.soft_delete(pid)
    return jsonify(p.serialize()), 200

# ── REVIEWS ──────────────────────────────────────────────────────────────────────
@superadmin_bp.route('/reviews', methods=['GET'])
@super_admin_role_required
def list_reviews():
    
    rs = ReviewController.list_recent()
    return jsonify([r.serialize() for r in rs]), 200

@superadmin_bp.route('/reviews/<int:rid>', methods=['DELETE'])
@super_admin_role_required
def delete_review(rid):
    
    r = ReviewController.delete(rid)
    return jsonify(r.serialize()), 200


# ── ATTRIBUTE VALUES ─────────────────────────────────────────────────────────────
from controllers.superadmin.attribute_value_controller import AttributeValueController

@superadmin_bp.route('/attribute-values', methods=['GET'])
@super_admin_role_required
def list_attribute_values():
    
    avs = AttributeValueController.list_all()
    return jsonify([ {
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    } for av in avs]), 200

@superadmin_bp.route('/attribute-values/<int:aid>', methods=['GET'])
@super_admin_role_required
def list_values_for_attribute(aid):
    
    avs = AttributeValueController.list_for_attribute(aid)
    return jsonify([ {
        'attribute_id': av.attribute_id,
        'value_code': av.value_code,
        'value_label': av.value_label
    } for av in avs]), 200

@superadmin_bp.route('/attribute-values', methods=['POST'])
@super_admin_role_required
def create_attribute_value():
    
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
    
    AttributeValueController.delete(aid, value_code)
    return '', 204


# ── ATTRIBUTES ───────────────────────────────────────────────────────────────────
@superadmin_bp.route('/attributes', methods=['GET'])
@super_admin_role_required
def list_attributes():
    
    try:
        attrs = AttributeController.list_all()
        return jsonify([a.serialize() for a in attrs]), HTTPStatus.OK

    except Exception as e:
        current_app.logger.error(f"Error listing attributes: {e}")
        return jsonify({'message': 'Failed to retrieve attributes.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/attributes', methods=['POST'])
@super_admin_role_required
def create_attribute():
    
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
    try:
        associations = CategoryAttributeController.list_attributes_for_category(cid)
        return jsonify(associations), HTTPStatus.OK
    except FileNotFoundError as e:
        return jsonify({'message': str(e)}), HTTPStatus.NOT_FOUND
    except Exception as e:
        current_app.logger.error(f"Error listing attributes for category {cid}: {e}")
        return jsonify({'message': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/attributes', methods=['POST'])
@super_admin_role_required
def add_attribute_to_category(cid):
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
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is missing or not JSON.'}), HTTPStatus.BAD_REQUEST
    
    try:
        association = CategoryAttributeController.update_attribute_for_category(cid, aid, data)
        return jsonify(association.serialize()), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error updating attribute for category: {e}")
        return jsonify({'message': 'Failed to update attribute for category.'}), HTTPStatus.INTERNAL_SERVER_ERROR


@superadmin_bp.route('/categories/<int:cid>/attributes/<int:aid>', methods=['DELETE'])
@super_admin_role_required
def remove_attribute_from_category(cid, aid):
    try:
        CategoryAttributeController.remove_attribute_from_category(cid, aid)
        return '', HTTPStatus.NO_CONTENT
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error removing attribute from category: {e}")
        return jsonify({'message': 'Failed to remove attribute from category.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── CATEGORY ATTRIBUTES ─────────────────────────────────────────────────────────
@superadmin_bp.route('/categories/<int:cid>/assign-attribute', methods=['POST'])
@super_admin_role_required
def assign_attribute_to_category(cid):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body is missing or not JSON.'}), HTTPStatus.BAD_REQUEST
    
    try:
        association = CategoryAttributeController.add_attribute_to_category(cid, data)
        return jsonify(association.serialize()), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error assigning attribute to category: {e}")
        return jsonify({'message': 'Failed to assign attribute to category.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── BRAND CATEGORIES ────────────────────────────────────────────────────────────
@superadmin_bp.route('/brands/<int:bid>/categories/<int:cid>', methods=['POST'])
@super_admin_role_required
def add_category_to_brand(bid, cid):
    try:
        brand = BrandController.add_category(bid, cid)
        return jsonify(brand.serialize()), 200
    except Exception as e:
        current_app.logger.error(f"Error adding category to brand: {str(e)}")
        return jsonify({"error": str(e)}), 500

@superadmin_bp.route('/brands/<int:bid>/categories/<int:cid>', methods=['DELETE'])
@super_admin_role_required
def remove_category_from_brand(bid, cid):
    try:
        brand = BrandController.remove_category(bid, cid)
        return jsonify(brand.serialize()), 200
    except Exception as e:
        current_app.logger.error(f"Error removing category from brand: {str(e)}")
        return jsonify({"error": str(e)}), 500

@superadmin_bp.route('/brands/<int:bid>/categories', methods=['GET'])
@super_admin_role_required
def get_brand_categories(bid):
    try:
        categories = BrandCategoryController.get_categories_for_brand(bid)
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error getting categories for brand: {e}")
        return jsonify({'message': 'Failed to get categories for brand.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/categories/main', methods=['GET'])
@super_admin_role_required
def list_main_categories():
    try:
        cats = CategoryController.get_main_categories()
        return jsonify([c.serialize() for c in cats]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing main categories: {e}")
        return jsonify({'message': 'Failed to retrieve main categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/homepage/categories', methods=['GET'])
@super_admin_role_required
def get_featured_categories():
    try:
        categories = HomepageController.get_featured_categories()
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error getting featured categories: {e}")
        return jsonify({'message': 'Failed to retrieve featured categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/homepage/categories', methods=['POST'])
@super_admin_role_required
def update_featured_categories():
    try:
        data = request.get_json()
        if not data or 'category_ids' not in data:
            return jsonify({'message': 'category_ids is required'}), HTTPStatus.BAD_REQUEST

        categories = HomepageController.update_featured_categories(data['category_ids'])
        return jsonify([c.serialize() for c in categories]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error updating featured categories: {e}")
        return jsonify({'message': 'Failed to update featured categories.'}), HTTPStatus.INTERNAL_SERVER_ERROR

# ── PRODUCT MONITORING ───────────────────────────────────────────────────────────
@superadmin_bp.route('/products/pending', methods=['GET'])
@super_admin_role_required
def list_pending_products():
    try:
        products = ProductMonitoringController.get_pending_products()
        return jsonify([{
            'product_id': p.product_id,
            'product_name': p.product_name,
            'sku': p.sku,
            'status': p.approval_status,
            'cost_price': float(p.cost_price),
            'selling_price': float(p.selling_price),
            'media': [m.serialize() for m in p.media] if p.media else [],
            'meta': p.meta.serialize() if p.meta else None,
            'brand': p.brand.serialize() if p.brand else None,
            'category': p.category.serialize() if p.category else None
        } for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing pending products: {e}")
        return jsonify({'message': 'Failed to retrieve pending products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products/approved', methods=['GET'])
@super_admin_role_required
def list_approved_products():
    
    try:
        products = ProductMonitoringController.get_approved_products()
        return jsonify([{
            'product_id': p.product_id,
            'product_name': p.product_name,
            'sku': p.sku,
            'status': p.approval_status,
            'cost_price': float(p.cost_price),
            'selling_price': float(p.selling_price),
            'media': [m.serialize() for m in p.media] if p.media else [],
            'meta': p.meta.serialize() if p.meta else None,
            'brand': p.brand.serialize() if p.brand else None,
            'category': p.category.serialize() if p.category else None
        } for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing approved products: {e}")
        return jsonify({'message': 'Failed to retrieve approved products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products/rejected', methods=['GET'])
@super_admin_role_required
def list_rejected_products():
    
    try:
        products = ProductMonitoringController.get_rejected_products()
        return jsonify([{
            'product_id': p.product_id,
            'product_name': p.product_name,
            'sku': p.sku,
            'status': p.approval_status,
            'cost_price': float(p.cost_price),
            'selling_price': float(p.selling_price),
            'rejection_reason': p.rejection_reason,
            'media': [m.serialize() for m in p.media] if p.media else [],
            'meta': p.meta.serialize() if p.meta else None,
            'brand': p.brand.serialize() if p.brand else None,
            'category': p.category.serialize() if p.category else None
        } for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing rejected products: {e}")
        return jsonify({'message': 'Failed to retrieve rejected products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products/<int:product_id>/approve', methods=['POST'])
@super_admin_role_required
def approve_product(product_id):
    try:
        admin_id = get_jwt_identity()
        product = ProductMonitoringController.approve_product(product_id, admin_id)
        return jsonify({
            'product_id': product.product_id,
            'product_name': product.product_name,
            'status': product.approval_status,
            'approved_at': product.approved_at.isoformat(),
            'approved_by': product.approved_by
        }), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error approving product {product_id}: {e}")
        return jsonify({'message': 'Failed to approve product.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products/<int:product_id>/reject', methods=['POST'])
@super_admin_role_required
def reject_product(product_id):
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({'message': 'Rejection reason is required'}), HTTPStatus.BAD_REQUEST

        admin_id = get_jwt_identity()
        product = ProductMonitoringController.reject_product(product_id, admin_id, data['reason'])
        return jsonify({
            'product_id': product.product_id,
            'product_name': product.product_name,
            'status': product.approval_status,
            'rejection_reason': product.rejection_reason,
            'approved_at': product.approved_at.isoformat(),
            'approved_by': product.approved_by
        }), HTTPStatus.OK
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        current_app.logger.error(f"Error rejecting product {product_id}: {e}")
        return jsonify({'message': 'Failed to reject product.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products/<int:product_id>', methods=['GET'])
@super_admin_role_required
def get_product_details(product_id):
    
    try:
        product_details = ProductMonitoringController.get_product_details(product_id)
        return jsonify(product_details), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error getting product details for {product_id}: {e}")
        return jsonify({'message': 'Failed to retrieve product details.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/products', methods=['GET', 'OPTIONS'])
@cross_origin()
@super_admin_role_required
def list_products():
    
    if request.method == 'OPTIONS':
        return '', HTTPStatus.OK
        
    try:
        products = ProductController.list_all()
        return jsonify([{
            'product_id': p.product_id,
            'product_name': p.product_name
        } for p in products]), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error listing products: {e}")
        return jsonify({'message': 'Failed to retrieve products.'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/carousels', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin()
@super_admin_role_required
def carousels_handler():
    """
    GET: List all carousel items.
    POST: Create a new carousel item (with image upload and shareable_link).
    OPTIONS: CORS preflight.
    """
    from controllers.superadmin.carousel_controller import CarouselController
    from flask import request, jsonify, current_app
    from http import HTTPStatus
    if request.method == 'OPTIONS':
        return '', HTTPStatus.OK
    if request.method == 'GET':
        try:
            carousels = CarouselController.list_all()
            return jsonify([
                {
                    'id': c.id,
                    'type': c.type,
                    'image_url': c.image_url,
                    'target_id': c.target_id,
                    'display_order': c.display_order,
                    'is_active': c.is_active,
                    'shareable_link': c.shareable_link
                } for c in carousels
            ]), HTTPStatus.OK
        except Exception as e:
            current_app.logger.error(f"Error listing carousels: {e}")
            return jsonify({'message': 'Failed to retrieve carousels.'}), HTTPStatus.INTERNAL_SERVER_ERROR
    if request.method == 'POST':
        try:
            # Accept multipart/form-data
            type_ = request.form.get('type')
            target_id = request.form.get('target_id')
            shareable_link = request.form.get('shareable_link')
            display_order = request.form.get('display_order', 0)
            is_active = request.form.get('is_active', 'true').lower() == 'true'
            image_file = request.files.get('image')
            if not type_ or not target_id or not image_file:
                return jsonify({'message': 'type, target_id, and image are required.'}), HTTPStatus.BAD_REQUEST
            data = {
                'type': type_,
                'target_id': int(target_id),
                'display_order': int(display_order),
                'is_active': is_active,
                'shareable_link': shareable_link
            }
            carousel = CarouselController.create(data, image_file=image_file)
            return jsonify(carousel.serialize()), HTTPStatus.CREATED
        except Exception as e:
            current_app.logger.error(f"Error creating carousel: {e}")
            return jsonify({'message': f'Failed to create carousel: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/carousels/<int:carousel_id>', methods=['DELETE'])
@cross_origin()
@super_admin_role_required
def delete_carousel(carousel_id):
    """
    Soft delete a carousel item.
    """
    from controllers.superadmin.carousel_controller import CarouselController
    from flask import jsonify, current_app
    from http import HTTPStatus
    try:
        carousel = CarouselController.delete(carousel_id)
        return jsonify({'message': 'Carousel deleted successfully', 'id': carousel.id}), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error deleting carousel {carousel_id}: {e}")
        return jsonify({'message': f'Failed to delete carousel: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR

@superadmin_bp.route('/carousels/order', methods=['PUT'])
@cross_origin()
@super_admin_role_required
def update_carousel_order():
    """
    Update display order for carousel items.
    """
    from controllers.superadmin.carousel_controller import CarouselController
    from flask import request, jsonify, current_app
    from http import HTTPStatus
    try:
        data = request.get_json()
        if not data or 'order' not in data:
            return jsonify({'message': 'Missing order data'}), HTTPStatus.BAD_REQUEST
        updated = CarouselController.update_display_orders(data['order'])
        return jsonify({'message': f'Updated {updated} carousel items'}), HTTPStatus.OK
    except Exception as e:
        current_app.logger.error(f"Error updating carousel order: {e}")
        return jsonify({'message': f'Failed to update carousel order: {str(e)}'}), HTTPStatus.INTERNAL_SERVER_ERROR