from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from marshmallow import Schema, fields, validate, ValidationError, validates_schema

from auth.controllers import (
    register_user, register_merchant, login_user, refresh_access_token,
    logout_user, verify_email, google_auth, get_current_user,
    request_password_reset, reset_password,
    resend_verification_email_controller
)
from auth.utils import user_role_required, merchant_role_required, admin_role_required
from auth.models import User, MerchantProfile
from auth.models.merchant_document import MerchantDocument
from auth.models.country_config import CountryConfig, CountryCode

# Schema definitions
class RegisterUserSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    phone = fields.Str()

class RegisterMerchantSchema(Schema):
    password = fields.Str(required=True, validate=validate.Length(min=8))
    first_name = fields.Str(required=True)
    last_name = fields.Str(required=True)
    phone = fields.Str()
    business_name = fields.Str(required=True)
    business_description = fields.Str()
    business_email = fields.Email(required=True)
    business_phone = fields.Str()
    business_address = fields.Str()
    country_code = fields.Str(required=True, validate=validate.OneOf([c.value for c in CountryCode]))
    state_province = fields.Str(required=True)
    city = fields.Str(required=True)
    postal_code = fields.Str(required=True)
    role = fields.Str(load_only=True)

class LoginSchema(Schema):
    email = fields.Email(required=False)
    business_email = fields.Email(required=False)
    password = fields.Str(required=True, validate=validate.Length(min=8))

    @validates_schema
    def validate_email_or_business_email(self, data, **kwargs):
        if not data.get('email') and not data.get('business_email'):
            raise ValidationError("Either email or business_email is required")

class RefreshTokenSchema(Schema):
    refresh_token = fields.Str(required=True)

class GoogleAuthSchema(Schema):
    id_token = fields.Str(required=True)

class PasswordResetRequestSchema(Schema):
    email = fields.Email(required=True)

class PasswordResetSchema(Schema):
    token = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8))

# Create auth blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/merchant/profile', methods=['GET'])
@jwt_required()
@merchant_role_required
def get_merchant_profile():
    """
    Get merchant profile details including bank details.
    ---
    tags:
      - Merchant
    security:
      - Bearer: []
    responses:
      200:
        description: Merchant profile retrieved successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            business_name:
              type: string
            business_description:
              type: string
            business_email:
              type: string
            business_phone:
              type: string
            business_address:
              type: string
            country_code:
              type: string
            state_province:
              type: string
            city:
              type: string
            postal_code:
              type: string
            verification_status:
              type: string
            is_verified:
              type: boolean
      401:
        description: Unauthorized
      404:
        description: Merchant profile not found
      500:
        description: Internal server error
    """
    try:
        # Get current user ID from JWT token
        current_user_id = get_jwt_identity()
        user = User.get_by_id(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Get merchant profile
        merchant_profile = MerchantProfile.get_by_user_id(current_user_id)
        
        if not merchant_profile:
            return jsonify({"error": "Merchant profile not found"}), 404
            
        # Get documents
        documents = MerchantDocument.query.filter_by(merchant_id=merchant_profile.id).all()
        
        # Get country configuration
        country_config = {
            'required_documents': [doc.value for doc in CountryConfig.get_required_documents(merchant_profile.country_code)],
            'field_validations': CountryConfig.get_field_validations(merchant_profile.country_code),
            'bank_fields': CountryConfig.get_bank_fields(merchant_profile.country_code),
            'tax_fields': CountryConfig.get_tax_fields(merchant_profile.country_code),
            'country_name': CountryConfig.get_country_name(merchant_profile.country_code)
        }
        
        # Format document data
        documents_data = {}
        for doc in documents:
            documents_data[doc.document_type.value] = {
                "id": doc.id,
                "type": doc.document_type.value,
                "status": doc.status.value,
                "submitted": True,
                "imageUrl": doc.file_url,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "admin_notes": doc.admin_notes,
                "verified_at": doc.verified_at.isoformat() if doc.verified_at else None
            }
            
        # Format merchant data
        merchant_data = {
            "id": merchant_profile.id,
            "business_name": merchant_profile.business_name,
            "business_description": merchant_profile.business_description,
            "business_email": merchant_profile.business_email,
            "business_phone": merchant_profile.business_phone,
            "business_address": merchant_profile.business_address,
            "country_code": merchant_profile.country_code,
            "country_name": country_config['country_name'],
            "state_province": merchant_profile.state_province,
            "city": merchant_profile.city,
            "postal_code": merchant_profile.postal_code,
            "gstin": merchant_profile.gstin,
            "pan_number": merchant_profile.pan_number,
            "tax_id": merchant_profile.tax_id,
            "vat_number": merchant_profile.vat_number,
            "bank_account_number": merchant_profile.bank_account_number,
            "bank_name": merchant_profile.bank_name,
            "bank_branch": merchant_profile.bank_branch,
            "bank_ifsc_code": merchant_profile.bank_ifsc_code,
            "bank_swift_code": merchant_profile.bank_swift_code,
            "bank_iban": merchant_profile.bank_iban,
            "verification_status": merchant_profile.verification_status.value,
            "is_verified": merchant_profile.is_verified,
            "verification_notes": merchant_profile.verification_notes,
            "verification_submitted_at": merchant_profile.verification_submitted_at.isoformat() if merchant_profile.verification_submitted_at else None,
            "verification_completed_at": merchant_profile.verification_completed_at.isoformat() if merchant_profile.verification_completed_at else None,
            "created_at": merchant_profile.created_at.isoformat(),
            "updated_at": merchant_profile.updated_at.isoformat(),
            "can_place_premium": merchant_profile.can_place_premium,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "documents": documents_data,
            "country_config": country_config
        }
        
        return jsonify(merchant_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/countries', methods=['GET'])
def get_supported_countries():
    """
    Get list of supported countries with their configurations.
    ---
    tags:
      - Countries
    responses:
      200:
        description: List of supported countries
        schema:
          type: object
          properties:
            countries:
              type: array
              items:
                type: object
                properties:
                  code:
                    type: string
                  name:
                    type: string
                  required_documents:
                    type: array
                    items:
                      type: string
      500:
        description: Internal server error
    """
    try:
        countries = CountryConfig.get_supported_countries()
        return jsonify({
            'countries': countries
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - email
            - password
            - first_name
            - last_name
          properties:
            email:
              type: string
              format: email
            password:
              type: string
              minLength: 8
            first_name:
              type: string
            last_name:
              type: string
            phone:
              type: string
    responses:
      201:
        description: User registered successfully
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = RegisterUserSchema()
        data = schema.load(request.json)
        
        # Register user
        response, status_code = register_user(data)
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400

@auth_bp.route('/register/merchant', methods=['POST'])
def register_merchant_route():
    """
    Register a new merchant.
    ---
    tags:
      - Merchant
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - password
            - first_name
            - last_name
            - business_name
            - business_email
            - country_code
            - state_province
            - city
            - postal_code
          properties:
            password:
              type: string
              minLength: 8
            first_name:
              type: string
            last_name:
              type: string
            phone:
              type: string
            business_name:
              type: string
            business_description:
              type: string
            business_email:
              type: string
              format: email
            business_phone:
              type: string
            business_address:
              type: string
            country_code:
              type: string
            state_province:
              type: string
            city:
              type: string
            postal_code:
              type: string
    responses:
      201:
        description: Merchant registered successfully
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    try:
        # Log incoming request data (excluding password)
        request_data = request.json.copy() if request.json else {}
        if 'password' in request_data:
            request_data['password'] = '[REDACTED]'
        current_app.logger.debug(f"Received merchant registration request: {request_data}")

        # Validate request data
        schema = RegisterMerchantSchema()
        try:
            data = schema.load(request.json)
            current_app.logger.debug("Request data validation successful")
        except ValidationError as e:
            current_app.logger.error(f"Validation error in merchant registration: {str(e.messages)}")
            return jsonify({
                "error": "Validation error",
                "details": e.messages,
                "validation_errors": e.messages
            }), 400
        
        # Register merchant
        response, status_code = register_merchant(data)
        
        if status_code == 201:
            current_app.logger.info(f"Merchant registered successfully: {data.get('business_email')}")
        else:
            current_app.logger.error(f"Failed to register merchant: {response.get('error')}")
            
        return jsonify(response), status_code
    except ValidationError as e:
        current_app.logger.error(f"Validation error in merchant registration: {str(e.messages)}")
        return jsonify({
            "error": "Validation error",
            "details": e.messages,
            "validation_errors": e.messages
        }), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in merchant registration: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login a user.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - password
          properties:
            email:
              type: string
              format: email
            business_email:
              type: string
              format: email
            password:
              type: string
              minLength: 8
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                first_name:
                  type: string
                last_name:
                  type: string
      400:
        description: Validation error
      401:
        description: Invalid credentials
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = LoginSchema()
        data = schema.load(request.json)
        
        # Check if this is a business email or regular email login
        if data.get('business_email'):
            data['email'] = data.get('business_email')
            # Flag to indicate this is a business email login
            data['business_email'] = True
        
        # Login user
        response, status_code = login_user(data)
        
        if status_code == 200:
            # Get merchant profile if user is a merchant
            user_id = response.get('user', {}).get('id')
            if user_id:
                merchant = MerchantProfile.get_by_user_id(user_id)
                if merchant:
                    response['merchant'] = {
                        'id': merchant.id,
                        'user_id': merchant.user_id,
                        'business_name': merchant.business_name,
                        'business_description': merchant.business_description,
                        'business_email': merchant.business_email,
                        'business_phone': merchant.business_phone,
                        'business_address': merchant.business_address,
                        'gstin': merchant.gstin,
                        'pan_number': merchant.pan_number,
                        'bank_account_number': merchant.bank_account_number,
                        'bank_ifsc_code': merchant.bank_ifsc_code,
                        'verification_status': merchant.verification_status.value if merchant.verification_status else None,
                        'verification_submitted_at': merchant.verification_submitted_at.isoformat() if merchant.verification_submitted_at else None,
                        'verification_completed_at': merchant.verification_completed_at.isoformat() if merchant.verification_completed_at else None,
                        'verification_notes': merchant.verification_notes,
                        'is_verified': merchant.is_verified,
                        'created_at': merchant.created_at.isoformat(),
                        'updated_at': merchant.updated_at.isoformat(),
                        'can_place_premium': merchant.can_place_premium 
                    }
        
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400
    
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh access token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - refresh_token
          properties:
            refresh_token:
              type: string
    responses:
      200:
        description: Token refreshed successfully
        schema:
          type: object
          properties:
            access_token:
              type: string
      400:
        description: Validation error
      401:
        description: Invalid refresh token
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = RefreshTokenSchema()
        data = schema.load(request.json)
        
        # Refresh token
        response, status_code = refresh_access_token(data['refresh_token'])
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout a user.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - refresh_token
          properties:
            refresh_token:
              type: string
    responses:
      200:
        description: Logout successful
      400:
        description: Validation error
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = RefreshTokenSchema()
        data = schema.load(request.json)
        
        # Logout user
        response, status_code = logout_user(data['refresh_token'])
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email_route(token):
    """
    Verify user email and return tokens for automatic login.
    ---
    tags:
      - Authentication
    parameters:
      - name: token
        in: path
        type: string
        required: true
        description: Email verification token
    responses:
      200:
        description: Email verified successfully
        schema:
          type: object
          properties:
            message:
              type: string
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                first_name:
                  type: string
                last_name:
                  type: string
                is_verified:
                  type: boolean
      400:
        description: Invalid token
      404:
        description: User not found
    """
    try:
        # Verify email and get response
        response, status_code = verify_email(token)
        
        if status_code != 200:
            return jsonify(response), status_code
            
        # Get user from database
        user_id = response.get('user_id')
        if not user_id:
            return jsonify({"error": "User ID not found in verification response"}), 400
            
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        # after
        access_token = create_access_token(identity=str(user.id))

        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            "message": "Email verified successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_verified": True
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@auth_bp.route('/google', methods=['POST'])
def google_auth_route():
    """
    Authenticate with Google OAuth.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - id_token
          properties:
            id_token:
              type: string
    responses:
      200:
        description: Google authentication successful
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                email:
                  type: string
                first_name:
                  type: string
                last_name:
                  type: string
      400:
        description: Validation error
      401:
        description: Invalid Google token
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = GoogleAuthSchema()
        data = schema.load(request.json)
        
        # Authenticate with Google
        response, status_code = google_auth(data)
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """
    Get current user information.
    ---
    tags:
      - User
    security:
      - Bearer: []
    responses:
      200:
        description: User information retrieved successfully
        schema:
          type: object
          properties:
            id:
              type: integer
            email:
              type: string
            first_name:
              type: string
            last_name:
              type: string
            phone:
              type: string
            is_verified:
              type: boolean
      401:
        description: Invalid or expired token
      500:
        description: Internal server error
    """
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"error": "Invalid token identity"}), 401
            
        response, status_code = get_current_user(user_id)
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"Error in /me endpoint: {str(e)}")
        if "Invalid token" in str(e):
            return jsonify({"error": "Invalid or expired token"}), 401
        return jsonify({"error": "Failed to get user information"}), 500

@auth_bp.route('/password/reset-request', methods=['POST'])
def password_reset_request():
    """
    Request password reset.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
    responses:
      200:
        description: Password reset email sent
      400:
        description: Validation error
      404:
        description: User not found
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = PasswordResetRequestSchema()
        data = schema.load(request.json)
        
        # Request password reset
        response, status_code = request_password_reset(data['email'])
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400

@auth_bp.route('/password/reset', methods=['POST'])
def password_reset():
    """
    Reset password with token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - token
            - new_password
          properties:
            token:
              type: string
            new_password:
              type: string
              minLength: 8
    responses:
      200:
        description: Password reset successful
      400:
        description: Validation error or invalid token
      404:
        description: User not found
      500:
        description: Internal server error
    """
    try:
        # Validate request data
        schema = PasswordResetSchema()
        data = schema.load(request.json)
        
        # Reset password
        response, status_code = reset_password(data['token'], data['new_password'])
        return jsonify(response), status_code
    except ValidationError as e:
        return jsonify({"error": "Validation error", "details": e.messages}), 400
    

class ResendVerificationSchema(Schema):
    email = fields.Email(required=True)


@auth_bp.route('/verify-email/resend', methods=['POST'])
def resend_verification_email_route():
    """
    Resend the email‐verification link (rate limited).
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
    responses:
      200:
        description: “If your email is registered and unverified, a new link was sent.”
      400:
        description: Validation error
      429:
        description: Rate limit exceeded
      500:
        description: Internal server error
    """
    try:
        # validate
        schema = ResendVerificationSchema()
        data = schema.load(request.json)

        # hand off to your controller
        response, status_code = resend_verification_email_controller(data['email'])
        return jsonify(response), status_code

    except ValidationError as err:
        return jsonify({"error": "Validation error", "details": err.messages}), 400