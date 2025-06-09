import enum
from datetime import datetime

from common.database import db, BaseModel
from flask import current_app 

class DocumentType(enum.Enum):
    """Types of documents required for merchant verification."""
    # Business Registration Documents
    BUSINESS_REGISTRATION_IN = 'business_registration_in'  # Shop & Establishment Certificate
    BUSINESS_REGISTRATION_GLOBAL = 'business_registration_global'  # Business License/Incorporation Certificate
    
    # Tax Identification Documents
    PAN_CARD = 'pan_card'  # Indian PAN
    TAX_ID_GLOBAL = 'tax_id_global'  # TIN/EIN/VAT ID
    
    # GST Related
    GSTIN = 'gstin'  # Indian GSTIN
    VAT_ID = 'vat_id'  # Global VAT ID
    SALES_TAX_REG = 'sales_tax_reg'  # Sales Tax Registration
    IMPORT_EXPORT_LICENSE = 'import_export_license'
    
    # Identity & Address Proof
    AADHAR = 'aadhar'  # Indian Aadhar
    VOTER_ID = 'voter_id'  # Indian Voter ID
    PASSPORT = 'passport'  # Global Passport
    NATIONAL_ID = 'national_id'  # Global National ID
    DRIVING_LICENSE = 'driving_license'  # Global Driver's License
    
    # Business Address Proof
    BUSINESS_ADDRESS_PROOF_IN = 'business_address_proof_in'  # Indian Business Address Proof
    BUSINESS_ADDRESS_PROOF_GLOBAL = 'business_address_proof_global'  # Utility Bill/Lease Agreement/Bank Statement
    
    # Bank Account Details
    CANCELLED_CHEQUE = 'cancelled_cheque'  # Indian Cancelled Cheque
    BANK_STATEMENT = 'bank_statement'  # Global Bank Statement
    VOID_CHEQUE = 'void_cheque'  # Global Void Cheque
    BANK_LETTER = 'bank_letter'  # Letter from Bank
    
    # Bank Account Information
    BANK_ACCOUNT_IN = 'bank_account_in'  # Indian Bank Account (with IFSC)
    BANK_ACCOUNT_GLOBAL = 'bank_account_global'  # Global Bank Account (with SWIFT/IBAN)
    
    # Tax Compliance
    GST_CERTIFICATE = 'gst_certificate'  # Indian GST Certificate
    VAT_CERTIFICATE = 'vat_certificate'  # Global VAT Certificate
    SALES_TAX_PERMIT = 'sales_tax_permit'  # Sales Tax Permit
    
    # Business Certification
    MSME_CERTIFICATE = 'msme_certificate'  # Indian MSME Certificate
    SMALL_BUSINESS_CERT = 'small_business_cert'  # Global Small Business Certification
    
    # Digital Signatures
    DSC = 'dsc'  # Indian Digital Signature Certificate
    ESIGN_CERTIFICATE = 'esign_certificate'  # Global eSign Certificate
    
    # Required Business Documents
    RETURN_POLICY = 'return_policy'  # Required for all merchants
    SHIPPING_DETAILS = 'shipping_details'  # Required for all merchants
    
    # Product and Category Documents
    PRODUCT_LIST = 'product_list'  # List of products to be sold
    CATEGORY_LIST = 'category_list'  # List of product categories
    BRAND_APPROVAL = 'brand_approval'  # Brand authorization and approval documents
    
    # Other Documents
    BRAND_AUTHORIZATION = 'brand_authorization'
    OTHER = 'other'

class VerificationStatus(enum.Enum):
    """Status of merchant verification."""
    PENDING = 'pending'
    EMAIL_VERIFIED = 'email_verified'
    DOCUMENTS_SUBMITTED = 'documents_submitted'
    UNDER_REVIEW = 'under_review'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class DocumentStatus(enum.Enum):
    """Status of merchant document verification."""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class MerchantDocument(BaseModel):
    """Merchant document model for storing verification documents."""
    __tablename__ = 'merchant_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchant_profiles.id'), nullable=False, index=True)
    document_type = db.Column(db.Enum(DocumentType), nullable=False)
    public_id = db.Column(db.String(255), nullable=False)  # Cloudinary public ID
    file_url = db.Column(db.String(255), nullable=False)  # Cloudinary secure URL
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    admin_notes = db.Column(db.Text, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    merchant = db.relationship('MerchantProfile', back_populates='documents')
    verified_by_user = db.relationship('User', foreign_keys=[verified_by])
    
    @classmethod
    def get_by_id(cls, id):
        """Get a document by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def get_by_merchant_id(cls, merchant_id):
        """Get all documents for a merchant."""
        return cls.query.filter_by(merchant_id=merchant_id).all()
    
    @classmethod
    def get_by_merchant_and_type(cls, merchant_id, document_type):
        """Get a specific document type for a merchant."""
        return cls.query.filter_by(
            merchant_id=merchant_id,
            document_type=document_type
        ).first()
    
    def approve(self, admin_id, notes=None):
        """Approve document."""
        self.status = DocumentStatus.APPROVED
        self.verified_at = datetime.utcnow()
        self.verified_by = admin_id
        if notes:
            self.admin_notes = notes
        db.session.commit()
    
    def reject(self, admin_id, notes=None):
        """Reject document and notify merchant."""
        from auth.email_utils import send_merchant_document_rejection_email
        from auth.models.models import User
        self.status = DocumentStatus.REJECTED
        self.verified_at = datetime.utcnow()
        self.verified_by = admin_id
        if notes:
            self.admin_notes = notes
        
        
        merchant_profile = self.merchant
        if not merchant_profile:
            
            current_app.logger.error(f"MerchantDocument ID {self.id} has no associated merchant profile. Cannot send email.")
            db.session.commit() # Commit status change even if email fails
            return

        merchant_user = merchant_profile.user
        if not merchant_user:
            merchant_user = User.get_by_id(merchant_profile.user_id)
            if not merchant_user:
                current_app.logger.error(f"MerchantProfile ID {merchant_profile.id} has no associated user. Cannot send email for document rejection.")
                db.session.commit() 
                return
        
        try:
            send_merchant_document_rejection_email(merchant_user, merchant_profile, self, notes)
        except Exception as e:
            current_app.logger.error(f"Failed to send document rejection email to merchant {merchant_user.email} for document {self.document_type.value}: {str(e)}")
            
        db.session.commit()
    
    def delete(self):
        """Delete document and its associated Cloudinary file."""
        from auth.utils import delete_from_cloudinary
        if self.public_id:
            delete_from_cloudinary(self.public_id)
        db.session.delete(self)
        db.session.commit()