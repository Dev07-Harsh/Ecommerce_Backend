from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from common.database import db, BaseModel

class YouTubeToken(BaseModel):
    """Model for storing YouTube OAuth tokens."""
    __tablename__ = 'youtube_tokens'

    id = Column(Integer, primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default='Bearer', nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_by = Column(Integer, nullable=False)  # User ID of superadmin who created
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def serialize(self):
        """Serialize token data (excluding sensitive information)."""
        return {
            "id": self.id,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "days_until_expiry": self.get_days_until_expiry()
        }

    def get_days_until_expiry(self):
        """Get number of days until token expires."""
        if not self.expires_at:
            return None
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def is_expiring_soon(self, days_threshold=7):
        """Check if token is expiring within the threshold."""
        days_left = self.get_days_until_expiry()
        return days_left is not None and days_left <= days_threshold

    def is_expired(self):
        """Check if token has expired."""
        return self.expires_at and datetime.utcnow() >= self.expires_at

    @classmethod
    def get_active_token(cls):
        """Get the current active YouTube token."""
        return cls.query.filter_by(is_active=True).first()

    @classmethod
    def deactivate_all_tokens(cls):
        """Deactivate all existing tokens."""
        cls.query.update({'is_active': False})
        db.session.commit()

    def refresh_token_if_needed(self):
        """Check if token needs refresh and return status."""
        # Token should be refreshed if it expires within 1 hour
        if self.expires_at and (self.expires_at - datetime.utcnow()).total_seconds() < 3600:
            return True
        return False
