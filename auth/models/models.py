import bcrypt
import uuid
from datetime import datetime
from enum import Enum
import re

from common.database import db, BaseModel
from auth.models.merchant_document import VerificationStatus, DocumentType
from .country_config import CountryConfig, CountryCode
from flask import current_app

class UserRole(Enum):
    USER = 'user'
    MERCHANT = 'merchant'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'

class AuthProvider(Enum):
    LOCAL = 'local'
    GOOGLE = 'google'
    # Can add other providers later (Facebook, Apple, etc.)

class User(BaseModel):
    """User model for all types of users (customers, merchants, admins)."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    auth_provider = db.Column(db.Enum(AuthProvider), default=AuthProvider.LOCAL, nullable=False)
    provider_user_id = db.Column(db.String(255), nullable=True)  # For OAuth provider user ID
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    merchant_profile = db.relationship('MerchantProfile', back_populates='user', uselist=False)
    refresh_tokens = db.relationship('RefreshToken', back_populates='user', cascade='all, delete-orphan')
    
    # For UserProfile 
    customer_specific_profile = db.relationship(
        'CustomerProfile', 
        back_populates='user', 
        uselist=False, 
        cascade='all, delete-orphan'
    )

    
    addresses = db.relationship(
        'UserAddress', 
        back_populates='user', 
        lazy='dynamic', 
        cascade='all, delete-orphan',
        order_by='UserAddress.is_default_shipping.desc(), UserAddress.is_default_billing.desc(), UserAddress.address_id' # Example ordering
    )

    
    wishlist_items = db.relationship(
        'WishlistItem', 
        back_populates='user', 
        lazy='dynamic', 
        cascade='all, delete-orphan'
    )

  
    cart = db.relationship(
        'Cart', 
        back_populates='user', 
        uselist=False, 
        cascade='all, delete-orphan'
    )

   
    orders = db.relationship(
        'Order', 
        back_populates='user', 
        lazy='dynamic',
        order_by='Order.order_date.desc()' 
    )

    # For OrderStatusHistory (changed_by_user_id, one-to-many, 'changed_by_user' is defined in OrderStatusHistory)
    
    order_status_changes_made = db.relationship(
        'OrderStatusHistory',
        foreign_keys='OrderStatusHistory.changed_by_user_id', 
        back_populates='changed_by_user',
        lazy='dynamic'
    )

    payment_cards = db.relationship(
        'PaymentCard', 
        back_populates='user', 
        lazy='dynamic', 
        cascade='all, delete-orphan'
    )

    def set_password(self, password):
        """Hash password."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify password."""
        if self.password_hash is None:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, id):
        """Get user by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email."""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def get_by_provider_id(cls, provider, provider_user_id):
        """Get user by OAuth provider ID."""
        return cls.query.filter_by(
            auth_provider=provider,
            provider_user_id=provider_user_id
        ).first()

class MerchantProfile(BaseModel):
    """Merchant profile model."""
    __tablename__ = 'merchant_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    business_name = db.Column(db.String(200), nullable=False)
    business_description = db.Column(db.Text, nullable=True)
    business_email = db.Column(db.String(120), nullable=False)
    business_phone = db.Column(db.String(20), nullable=False)
    business_address = db.Column(db.Text, nullable=False)
    
    # Country and Region Information
    country_code = db.Column(db.String(10), nullable=False, default=CountryCode.INDIA.value)
    state_province = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    
    # Tax Information
    tax_id = db.Column(db.String(50), nullable=True)  # For GLOBAL: TIN/EIN/VAT ID
    gstin = db.Column(db.String(15), nullable=True)  # For IN: GSTIN
    pan_number = db.Column(db.String(10), nullable=True)  # For IN: PAN
    vat_number = db.Column(db.String(50), nullable=True)  # For GLOBAL: VAT Number
    sales_tax_number = db.Column(db.String(50), nullable=True)  # For GLOBAL: Sales Tax Number
    
    
    # Bank Account Information
    bank_account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_branch = db.Column(db.String(100), nullable=True)
    bank_ifsc_code = db.Column(db.String(11), nullable=True)  # For IN: IFSC Code
    bank_swift_code = db.Column(db.String(11), nullable=True)  # For GLOBAL: SWIFT Code
    bank_iban = db.Column(db.String(34), nullable=True)  # For GLOBAL: IBAN
    bank_routing_number = db.Column(db.String(20), nullable=True)  # For GLOBAL: Routing Number
    
    # Verification Status
    verification_status = db.Column(db.Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False)
    verification_submitted_at = db.Column(db.DateTime, nullable=True)
    verification_completed_at = db.Column(db.DateTime, nullable=True)
    verification_notes = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Document Verification Tracking
    required_documents = db.Column(db.JSON, nullable=True)  # List of required document types based on country
    submitted_documents = db.Column(db.JSON, nullable=True)  # List of submitted document types
    
    # Subscription Information
    is_subscribed = db.Column(db.Boolean, default=False, nullable=False, server_default=db.false())
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.plan_id'), nullable=True)
    subscription_started_at = db.Column(db.DateTime, nullable=True)
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    can_place_premium = db.Column(db.Boolean, default=False, nullable=False, server_default=db.false())

    # Relationships
    user = db.relationship('User', back_populates='merchant_profile')
    documents = db.relationship('MerchantDocument', back_populates='merchant', cascade='all, delete-orphan')
    subscription_plan = db.relationship('SubscriptionPlan', back_populates='merchant_profiles')
    subscription_histories = db.relationship('SubscriptionHistory', back_populates='merchant', cascade='all, delete-orphan')
    product_placements = db.relationship('ProductPlacement', back_populates='merchant', lazy='dynamic', cascade='all, delete-orphan')
    
    
    sold_order_items = db.relationship(
        'OrderItem', 
        foreign_keys='OrderItem.merchant_id',
        back_populates='merchant', 
        lazy='dynamic'
    )
    
    shipments_handled = db.relationship(
        'Shipment', 
        foreign_keys='Shipment.merchant_id', 
        back_populates='merchant', 
        lazy='dynamic'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_required_documents()
    
    def update_required_documents(self):
        """Update required documents based on country code."""
        self.required_documents = [
            doc.value for doc in CountryConfig.get_required_documents(self.country_code)
        ]
    
    def get_required_documents(self):
        """Get list of required documents based on country."""
        return CountryConfig.get_required_documents(self.country_code)
    
    def get_field_validations(self):
        """Get field validation rules based on country."""
        return CountryConfig.get_field_validations(self.country_code)
    
    def get_required_bank_fields(self):
        """Get required bank fields based on country."""
        return CountryConfig.get_bank_fields(self.country_code)
    
    def get_required_tax_fields(self):
        """Get required tax fields based on country."""
        return CountryConfig.get_tax_fields(self.country_code)
    
    def get_country_name(self):
        """Get full country name."""
        return CountryConfig.get_country_name(self.country_code)
    
    def is_indian_merchant(self):
        """Check if merchant is from India."""
        return self.country_code == CountryCode.INDIA.value
    
    def validate_country_specific_fields(self):
        """Validate country-specific fields."""
        validations = self.get_field_validations()
        errors = {}
        
        for field, rules in validations.items():
            value = getattr(self, field)
            if value and not re.match(rules['pattern'], value):
                errors[field] = rules['message']
        
        return errors
    def approve(self):
        """Mark merchant profile as approved."""
        self.update_verification_status(VerificationStatus.APPROVED)

    def reject(self, notes=None):
        """Mark merchant profile as rejected."""
        self.update_verification_status(VerificationStatus.REJECTED, notes=notes)
    
    @classmethod
    def get_by_id(cls, id):
        """Get merchant profile by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def get_by_user_id(cls, user_id):
        """Get merchant profile by user ID."""
        return cls.query.filter_by(user_id=user_id).first()
    
    @classmethod
    def get_by_business_name(cls, business_name):
        """Get merchant profile by business name."""
        return cls.query.filter_by(business_name=business_name).first()
    
    def update_verification_status(self, status, notes=None):
        """Update verification status and send notifications."""
        from auth.email_utils import (
            send_merchant_profile_approval_email,
            send_merchant_profile_rejection_email
        )
        old_status = self.verification_status
        self.verification_status = status
        user = self.user # Assumes self.user is eagerly loaded or available

        if not user:
            current_app.logger.error(f"MerchantProfile ID {self.id} has no associated user. Cannot send email.")
            # Potentially load user if not available: user = User.get_by_id(self.user_id)
            # Fallback to prevent error, but ideal is to ensure user is available
            user = User.get_by_id(self.user_id) 
            if not user:
                db.session.commit() 
                return


        if status == VerificationStatus.APPROVED and old_status != VerificationStatus.APPROVED:
            self.is_verified = True
            self.verification_completed_at = datetime.utcnow()
            try:
                send_merchant_profile_approval_email(user, self)
            except Exception as e:
                current_app.logger.error(f"Failed to send approval email to merchant {user.email}: {str(e)}")

        elif status == VerificationStatus.REJECTED and old_status != VerificationStatus.REJECTED:
            self.is_verified = False
            self.verification_completed_at = datetime.utcnow()
            try:
                send_merchant_profile_rejection_email(user, self, notes)
            except Exception as e:
                current_app.logger.error(f"Failed to send rejection email to merchant {user.email}: {str(e)}")
        
        if notes:
            self.verification_notes = notes
            
        db.session.commit()
    
    def submit_for_verification(self):
        """Submit profile for verification and notify admins."""
        from auth.email_utils import send_merchant_docs_submitted_to_admin
        from auth.utils import get_super_admin_emails
        self.verification_status = VerificationStatus.DOCUMENTS_SUBMITTED 
        self.verification_submitted_at = datetime.utcnow()
        db.session.commit() 

        try:
            admin_emails = get_super_admin_emails()
            if admin_emails:
                send_merchant_docs_submitted_to_admin(self, admin_emails)
            else:
                current_app.logger.warning("No super admin emails configured to send submission notification.")
        except Exception as e:
            current_app.logger.error(f"Failed to send submission notice to admins for merchant {self.business_name}: {str(e)}")
        

class RefreshToken(BaseModel):
    """Refresh token model for JWT authentication."""
    __tablename__ = 'refresh_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_revoked = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='refresh_tokens')
    
    @classmethod
    def get_by_id(cls, id):
        """Get refresh token by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def create_token(cls, user_id, expires_at):
        """Create a new refresh token."""
        token = str(uuid.uuid4())
        refresh_token = cls(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        refresh_token.save()
        return token
    
    @classmethod
    def get_by_token(cls, token):
        """Get refresh token by token string."""
        return cls.query.filter_by(token=token, is_revoked=False).first()
    
    def revoke(self):
        """Revoke refresh token."""
        self.is_revoked = True
        db.session.commit()
    
    @classmethod
    def revoke_all_for_user(cls, user_id):
        """Revoke all refresh tokens for a user."""
        tokens = cls.query.filter_by(user_id=user_id, is_revoked=False).all()
        for token in tokens:
            token.is_revoked = True
        db.session.commit()

class EmailVerification(BaseModel):
    """Email verification token model."""
    __tablename__ = 'email_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    @classmethod
    def get_by_id(cls, id):
        """Get verification by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def create_token(cls, user_id, expires_at):
        """Create a new verification token."""
        token = str(uuid.uuid4())
        verification = cls(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        verification.save()
        return token
    
    @classmethod
    def get_by_token(cls, token):
        """Get verification by token."""
        return cls.query.filter_by(token=token, is_used=False).first()
    
    def use(self):
        """Mark verification token as used."""
        self.is_used = True
        db.session.commit()

class PhoneVerification(BaseModel):
    """Phone verification OTP model."""
    __tablename__ = 'phone_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    
    @classmethod
    def get_by_id(cls, id):
        """Get verification by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def create_otp(cls, user_id, phone, expires_at):
        """Create a new OTP."""
        import random
        otp = ''.join(random.choices('0123456789', k=6))
        verification = cls(
            user_id=user_id,
            phone=phone,
            otp=otp,
            expires_at=expires_at
        )
        verification.save()
        return otp
    
    @classmethod
    def verify_otp(cls, user_id, otp):
        """Verify OTP for user."""
        verification = cls.query.filter_by(
            user_id=user_id,
            otp=otp,
            is_used=False
        ).first()
        
        if not verification:
            return False
        
        if verification.expires_at < datetime.utcnow():
            return False
        
        verification.is_used = True
        db.session.commit()
        
        # Update user's phone verification status
        user = User.get_by_id(user_id)
        if user:
            user.is_phone_verified = True
            db.session.commit()
            
            
            if user.role == UserRole.MERCHANT:
                merchant = MerchantProfile.get_by_user_id(user_id)
                if merchant and merchant.verification_status == VerificationStatus.EMAIL_VERIFIED:
                    merchant.verification_status = VerificationStatus.PHONE_VERIFIED
                    db.session.commit()
        
        return True