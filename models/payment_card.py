from datetime import datetime
from common.database import db, BaseModel
from models.enums import CardTypeEnum, CardStatusEnum
from cryptography.fernet import Fernet
from flask import current_app
import re

class PaymentCard(BaseModel):
    """Model for storing encrypted payment card details."""
    __tablename__ = 'payment_cards'

    card_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Card Type (Credit/Debit)
    card_type = db.Column(db.Enum(CardTypeEnum), nullable=False)
    
    # Encrypted Card Details
    encrypted_card_number = db.Column(db.String(255), nullable=False)
    encrypted_cvv = db.Column(db.String(255), nullable=False)
    encrypted_expiry_month = db.Column(db.String(255), nullable=False)
    encrypted_expiry_year = db.Column(db.String(255), nullable=False)
    
    # Non-sensitive Card Details (for display)
    last_four_digits = db.Column(db.String(4), nullable=False)
    card_holder_name = db.Column(db.String(100), nullable=False)
    card_brand = db.Column(db.String(50), nullable=False)  # Visa, Mastercard, etc.
    
    # Card Status
    status = db.Column(db.Enum(CardStatusEnum), default=CardStatusEnum.ACTIVE, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False, server_default=db.false())
    
    # Billing Address Reference
    billing_address_id = db.Column(db.Integer, db.ForeignKey('user_addresses.address_id'), nullable=True)
    
    # Timestamps
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='payment_cards')
    billing_address = db.relationship('UserAddress', foreign_keys=[billing_address_id])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'card_number' in kwargs:
            self.set_card_number(kwargs['card_number'])
        if 'cvv' in kwargs:
            self.set_cvv(kwargs['cvv'])
        if 'expiry_month' in kwargs:
            self.set_expiry_month(kwargs['expiry_month'])
        if 'expiry_year' in kwargs:
            self.set_expiry_year(kwargs['expiry_year'])

    @staticmethod
    def get_encryption_key():
        """Get the encryption key from app config."""
        key = current_app.config.get('CARD_ENCRYPTION_KEY')
        if not key:
            raise ValueError("Card encryption key not configured")
        return key

    def encrypt_value(self, value):
        """Encrypt a value using Fernet."""
        key = self.get_encryption_key()
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()

    def decrypt_value(self, encrypted_value):
        """Decrypt a value using Fernet."""
        key = self.get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()

    def set_card_number(self, card_number):
        """Set and encrypt card number."""
        if not self.validate_card_number(card_number):
            raise ValueError("Invalid card number")
        self.encrypted_card_number = self.encrypt_value(card_number)
        self.last_four_digits = card_number[-4:]
        self.card_brand = self.detect_card_brand(card_number)

    def set_cvv(self, cvv):
        """Set and encrypt CVV."""
        if not self.validate_cvv(cvv):
            raise ValueError("Invalid CVV")
        self.encrypted_cvv = self.encrypt_value(cvv)

    def set_expiry_month(self, month):
        """Set and encrypt expiry month."""
        if not self.validate_expiry_month(month):
            raise ValueError("Invalid expiry month")
        self.encrypted_expiry_month = self.encrypt_value(str(month))

    def set_expiry_year(self, year):
        """Set and encrypt expiry year."""
        if not self.validate_expiry_year(year):
            raise ValueError("Invalid expiry year")
        self.encrypted_expiry_year = self.encrypt_value(str(year))

    def get_card_number(self):
        """Get decrypted card number."""
        return self.decrypt_value(self.encrypted_card_number)

    def get_cvv(self):
        """Get decrypted CVV."""
        return self.decrypt_value(self.encrypted_cvv)

    def get_expiry_month(self):
        """Get decrypted expiry month."""
        return self.decrypt_value(self.encrypted_expiry_month)

    def get_expiry_year(self):
        """Get decrypted expiry year."""
        return self.decrypt_value(self.encrypted_expiry_year)

    @staticmethod
    def validate_card_number(card_number):
        """Validate card number using Luhn algorithm."""
        if not card_number or not card_number.isdigit():
            return False
        
        # Remove any spaces or dashes
        card_number = card_number.replace(" ", "").replace("-", "")
        
        # Check length
        if len(card_number) < 13 or len(card_number) > 19:
            return False
        
        # Luhn algorithm
        total = 0
        is_even = False
        
        for digit in reversed(card_number):
            digit = int(digit)
            if is_even:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
            is_even = not is_even
        
        return total % 10 == 0

    @staticmethod
    def validate_cvv(cvv):
        """Validate CVV."""
        if not cvv or not cvv.isdigit():
            return False
        return 3 <= len(cvv) <= 4

    @staticmethod
    def validate_expiry_month(month):
        """Validate expiry month."""
        try:
            month = int(month)
            return 1 <= month <= 12
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_expiry_year(year):
        """Validate expiry year."""
        try:
            year = int(year)
            current_year = datetime.now().year
            return current_year <= year <= current_year + 10
        except (ValueError, TypeError):
            return False

    @staticmethod
    def detect_card_brand(card_number):
        """Detect card brand based on card number."""
        # Remove any spaces or dashes
        card_number = card_number.replace(" ", "").replace("-", "")
        
        # Visa
        if re.match(r'^4[0-9]{12}(?:[0-9]{3})?$', card_number):
            return 'Visa'
        
        # Mastercard
        if re.match(r'^5[1-5][0-9]{14}$', card_number):
            return 'Mastercard'
        
        # American Express
        if re.match(r'^3[47][0-9]{13}$', card_number):
            return 'American Express'
        
        # Discover
        if re.match(r'^6(?:011|5[0-9]{2})[0-9]{12}$', card_number):
            return 'Discover'
        
        # RuPay
        if re.match(r'^6[0-9]{15}$', card_number):
            return 'RuPay'
        
        return 'Unknown'

    def set_as_default(self):
        """Set this card as the default payment method."""
        # Remove default status from other cards
        PaymentCard.query.filter_by(
            user_id=self.user_id,
            is_default=True
        ).update({'is_default': False})
        
        self.is_default = True
        db.session.commit()

    def update_last_used(self):
        """Update the last used timestamp."""
        self.last_used_at = datetime.utcnow()
        db.session.commit()

    def serialize(self):
        """Serialize card details for API response."""
        return {
            "card_id": self.card_id,
            "user_id": self.user_id,
            "card_type": self.card_type.value,
            "last_four_digits": self.last_four_digits,
            "card_holder_name": self.card_holder_name,
            "card_brand": self.card_brand,
            "status": self.status.value,
            "is_default": self.is_default,
            "billing_address": self.billing_address.serialize() if self.billing_address else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<PaymentCard id={self.card_id} user_id={self.user_id} type='{self.card_type.value}'>" 