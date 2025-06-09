from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import cloudinary
import cloudinary.uploader
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from http import HTTPStatus
import logging

from common.database import db
from auth.models.merchant_document import MerchantDocument, DocumentType, DocumentStatus
from auth.models.models import User, UserRole
from auth.models.models import MerchantProfile, VerificationStatus

document_bp = Blueprint('document', __name__, url_prefix='/api/merchant/documents')

# Configure allowed file types and size limit
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv'
}

# Map MIME types to Cloudinary resource types
CLOUDINARY_RESOURCE_TYPES = {
    'application/pdf': 'raw',
    'image/jpeg': 'image',
    'image/png': 'image',
    'application/vnd.ms-excel': 'raw',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'raw',
    'text/csv': 'raw'
}

# Map MIME types to Cloudinary formats
CLOUDINARY_FORMATS = {
    'application/pdf': 'pdf',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'text/csv': 'csv'
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file):
    """Validate uploaded file type and size."""
    if not file:
        return False, "No file provided"
    
    if file.mimetype not in ALLOWED_MIME_TYPES:
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
    
    # Check file size (read content length or stream)
    file.seek(0, 2)  # Move to end to get size
    file_size = file.tell()
    file.seek(0)  # Reset to start
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024)}MB"
    
    return True, None

def get_cloudinary_resource_type(mime_type):
    """Get the appropriate Cloudinary resource type for a given MIME type."""
    return CLOUDINARY_RESOURCE_TYPES.get(mime_type, 'raw')

def get_cloudinary_format(mime_type):
    """Get the appropriate Cloudinary format for a given MIME type."""
    return CLOUDINARY_FORMATS.get(mime_type)

@document_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """
    Upload a document for merchant verification.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Document file (PDF, JPEG, PNG, Excel, or CSV)
      - in: formData
        name: document_type
        type: string
        required: true
        description: Type of document being uploaded
    responses:
      201:
        description: Document uploaded successfully
      400:
        description: Invalid request or file
      401:
        description: Unauthorized
      403:
        description: Forbidden - User is not a merchant
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user or current_user.role != UserRole.MERCHANT:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        merchant = MerchantProfile.get_by_user_id(current_user.id)
        if not merchant:
            return jsonify({'message': 'Merchant profile not found'}), HTTPStatus.NOT_FOUND
        
        # Validate form data
        if 'file' not in request.files or 'document_type' not in request.form:
            return jsonify({'message': 'File and document type are required'}), HTTPStatus.BAD_REQUEST
        
        file = request.files['file']
        document_type_str = request.form['document_type']
        
        # Validate document type
        try:
            document_type = DocumentType(document_type_str)
        except ValueError:
            return jsonify({'message': f"Invalid document type. Allowed types: {[t.value for t in DocumentType]}"}), HTTPStatus.BAD_REQUEST
        
        # Validate file
        is_valid, error_message = validate_file(file)
        if not is_valid:
            return jsonify({'message': error_message}), HTTPStatus.BAD_REQUEST
        
        # Check if document type already exists for merchant
        existing_doc = MerchantDocument.get_by_merchant_and_type(merchant.id, document_type)
        
        try:
            # Determine resource type and format based on file type
            resource_type = get_cloudinary_resource_type(file.mimetype)
            format = get_cloudinary_format(file.mimetype)
            
            # Prepare upload options
            upload_options = {
                'folder': f"merchant_documents/{merchant.id}",
                'resource_type': resource_type,
                'use_filename': True,
                'unique_filename': True
            }
            
            # Add format for PDFs and other raw files
            if format:
                upload_options['format'] = format
            
            # Add specific options for PDFs
            if file.mimetype == 'application/pdf':
                upload_options.update({
                    'resource_type': 'raw',
                    'format': 'pdf',
                    'type': 'upload'  # Explicitly set as public
                })
                current_app.logger.debug(f"PDF upload options: {upload_options}")
            
            # Upload to Cloudinary with appropriate options
            upload_result = cloudinary.uploader.upload(
                file,
                **upload_options
            )
            current_app.logger.debug(f"Cloudinary upload result: {upload_result}")
            
            if existing_doc:
                # Delete old file from Cloudinary
                try:
                    cloudinary.uploader.destroy(existing_doc.public_id)
                except cloudinary.exceptions.Error as e:
                    current_app.logger.warning(f"Failed to delete old file from Cloudinary: {str(e)}")
                
                # Update existing document
                existing_doc.public_id = upload_result['public_id']
                existing_doc.file_url = upload_result['secure_url']
                existing_doc.file_name = file.filename
                existing_doc.file_size = upload_result['bytes']
                existing_doc.mime_type = file.mimetype
                existing_doc.status = DocumentStatus.PENDING
                existing_doc.admin_notes = None
                existing_doc.verified_at = None
                existing_doc.verified_by = None
                
                db.session.commit()
                
                return jsonify({
                    'message': 'Document updated successfully',
                    'document': {
                        'id': existing_doc.id,
                        'document_type': existing_doc.document_type.value,
                        'file_url': existing_doc.file_url,
                        'status': existing_doc.status.value
                    }
                }), HTTPStatus.OK
            else:
                # Create new document record
                document = MerchantDocument(
                    merchant_id=merchant.id,
                    document_type=document_type,
                    public_id=upload_result['public_id'],
                    file_url=upload_result['secure_url'],
                    file_name=file.filename,
                    file_size=upload_result['bytes'],
                    mime_type=file.mimetype,
                    status=DocumentStatus.PENDING
                )
                db.session.add(document)
                
                # Update merchant verification status if necessary
                if merchant.verification_status == VerificationStatus.EMAIL_VERIFIED:
                    merchant.submit_for_verification()
                
                db.session.commit()
                
                return jsonify({
                    'message': 'Document uploaded successfully',
                    'document': {
                        'id': document.id,
                        'document_type': document.document_type.value,
                        'file_url': document.file_url,
                        'status': document.status.value
                    }
                }), HTTPStatus.CREATED
                
        except cloudinary.exceptions.Error as e:
            current_app.logger.error(f"Cloudinary upload error: {str(e)}")
            db.session.rollback()
            return jsonify({
                'message': 'Failed to upload file to storage',
                'error': str(e)
            }), HTTPStatus.INTERNAL_SERVER_ERROR
            
    except IntegrityError as e:
        current_app.logger.error(f"Database integrity error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': 'Failed to save document'}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        db.session.rollback()
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@document_bp.route('', methods=['GET'])
@jwt_required()
def get_documents():
    """
    Get all documents for a merchant.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: query
        name: merchant_id
        type: integer
        description: Merchant ID (required for admin users)
    responses:
      200:
        description: List of documents retrieved successfully
        schema:
          type: object
          properties:
            documents:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  document_type:
                    type: string
                  file_url:
                    type: string
                  file_name:
                    type: string
                  file_size:
                    type: integer
                  mime_type:
                    type: string
                  status:
                    type: string
                  admin_notes:
                    type: string
                  verified_at:
                    type: string
                    format: date-time
      401:
        description: Unauthorized
      403:
        description: Forbidden
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        merchant = MerchantProfile.get_by_user_id(current_user.id)
        if not merchant and current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({'message': 'Merchant profile not found or unauthorized'}), HTTPStatus.FORBIDDEN
        
        # Admins can specify merchant_id in query params
        merchant_id = merchant.id if merchant else request.args.get('merchant_id', type=int)
        if not merchant_id:
            return jsonify({'message': 'Merchant ID required for admins'}), HTTPStatus.BAD_REQUEST
        
        documents = MerchantDocument.get_by_merchant_id(merchant_id)
        return jsonify({
            'documents': [{
                'id': doc.id,
                'document_type': doc.document_type.value,
                'file_url': doc.file_url,
                'file_name': doc.file_name,
                'file_size': doc.file_size,
                'mime_type': doc.mime_type,
                'status': doc.status.value,
                'admin_notes': doc.admin_notes,
                'verified_at': doc.verified_at.isoformat() if doc.verified_at else None
            } for doc in documents]
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@document_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_document(id):
    """
    Get a specific document by ID.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: Document ID
    responses:
      200:
        description: Document retrieved successfully
        schema:
          type: object
          properties:
            document:
              type: object
              properties:
                id:
                  type: integer
                document_type:
                  type: string
                file_url:
                  type: string
                file_name:
                  type: string
                file_size:
                  type: integer
                mime_type:
                  type: string
                status:
                  type: string
                admin_notes:
                  type: string
                verified_at:
                  type: string
                  format: date-time
      401:
        description: Unauthorized
      403:
        description: Forbidden
      404:
        description: Document not found
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        document = MerchantDocument.get_by_id(id)
        if not document:
            return jsonify({'message': 'Document not found'}), HTTPStatus.NOT_FOUND
        
        merchant = MerchantProfile.get_by_user_id(current_user.id)
        if (merchant and document.merchant_id != merchant.id) and \
           current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        return jsonify({
            'document': {
                'id': document.id,
                'document_type': document.document_type.value,
                'file_url': document.file_url,
                'file_name': document.file_name,
                'file_size': document.file_size,
                'mime_type': document.mime_type,
                'status': document.status.value,
                'admin_notes': document.admin_notes,
                'verified_at': document.verified_at.isoformat() if document.verified_at else None
            }
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@document_bp.route('/<int:id>/approve', methods=['POST'])
@jwt_required()
def approve_document(id):
    """
    Approve a document.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: Document ID
      - in: body
        name: body
        schema:
          type: object
          properties:
            notes:
              type: string
              description: Optional notes for the approval
    responses:
      200:
        description: Document approved successfully
        schema:
          type: object
          properties:
            message:
              type: string
            document:
              type: object
              properties:
                id:
                  type: integer
                status:
                  type: string
      401:
        description: Unauthorized
      403:
        description: Forbidden - User is not an admin
      404:
        description: Document not found
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user or current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        document = MerchantDocument.get_by_id(id)
        if not document:
            return jsonify({'message': 'Document not found'}), HTTPStatus.NOT_FOUND
        
        # Allow approving documents regardless of current status
        notes = request.json.get('notes') if request.is_json else None
        
        # Record previous status for response message
        previous_status = document.status
        
        # Approve the document
        document.approve(current_user.id, notes)
        
        # Check if all documents are approved to update merchant status
        merchant = MerchantProfile.get_by_id(document.merchant_id)
        documents = MerchantDocument.get_by_merchant_id(document.merchant_id)
        if all(doc.status == DocumentStatus.APPROVED for doc in documents):
            merchant.update_verification_status(VerificationStatus.APPROVED)
        
        # Customize message based on previous status
        message = 'Document approved successfully'
        if previous_status == DocumentStatus.REJECTED:
            message = 'Document re-approved successfully'
        elif previous_status == DocumentStatus.APPROVED:
            message = 'Document approval updated successfully'
        
        return jsonify({
            'message': message,
            'document': {
                'id': document.id,
                'status': document.status.value
            }
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@document_bp.route('/<int:id>/reject', methods=['POST'])
@jwt_required()
def reject_document(id):
    """
    Reject a document.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: Document ID
      - in: body
        name: body
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
        description: Document rejected successfully
        schema:
          type: object
          properties:
            message:
              type: string
            document:
              type: object
              properties:
                id:
                  type: integer
                status:
                  type: string
      400:
        description: Missing rejection reason
      401:
        description: Unauthorized
      403:
        description: Forbidden - User is not an admin
      404:
        description: Document not found
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user or current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        document = MerchantDocument.get_by_id(id)
        if not document:
            return jsonify({'message': 'Document not found'}), HTTPStatus.NOT_FOUND
        
        # Allow rejecting documents regardless of current status
        notes = request.json.get('notes') if request.is_json else None
        if not notes:
            return jsonify({'message': 'Rejection reason is required'}), HTTPStatus.BAD_REQUEST
        
        # Record previous status for response message
        previous_status = document.status
        
        # Reject the document
        document.reject(current_user.id, notes)
        
        # Update merchant status to rejected if any document is rejected
        merchant = MerchantProfile.get_by_id(document.merchant_id)
        merchant.update_verification_status(VerificationStatus.REJECTED, notes)
        
        # Customize message based on previous status
        message = 'Document rejected successfully'
        if previous_status == DocumentStatus.APPROVED:
            message = 'Document status changed from approved to rejected'
        elif previous_status == DocumentStatus.REJECTED:
            message = 'Rejection reason updated successfully'
        
        return jsonify({
            'message': message,
            'document': {
                'id': document.id,
                'status': document.status.value
            }
        }), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@document_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_document(id):
    """
    Delete a document.
    ---
    tags:
      - Documents
    security:
      - Bearer: []
    parameters:
      - in: path
        name: id
        type: integer
        required: true
        description: Document ID
    responses:
      200:
        description: Document deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
      401:
        description: Unauthorized
      403:
        description: Forbidden
      404:
        description: Document not found
      500:
        description: Internal server error
    """
    try:
        current_user = User.get_by_id(get_jwt_identity())
        if not current_user:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        document = MerchantDocument.get_by_id(id)
        if not document:
            return jsonify({'message': 'Document not found'}), HTTPStatus.NOT_FOUND
        
        merchant = MerchantProfile.get_by_user_id(current_user.id)
        if (merchant and document.merchant_id != merchant.id) and \
           current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({'message': 'Unauthorized'}), HTTPStatus.FORBIDDEN
        
        # Delete from Cloudinary first
        try:
            cloudinary.uploader.destroy(document.public_id)
        except cloudinary.exceptions.Error as e:
            return jsonify({'message': f"Failed to delete file from storage: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
        
        # Delete from database
        document.delete()
        
        return jsonify({'message': 'Document deleted successfully'}), HTTPStatus.OK
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f"An error occurred: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
