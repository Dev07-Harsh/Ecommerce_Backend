from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from common.database import db, BaseModel
from auth.models.models import MerchantProfile, User, UserRole
from models.product import Product
import enum

class StreamStatus(str, enum.Enum):
    SCHEDULED = 'scheduled'
    LIVE = 'live'
    ENDED = 'ended'
    CANCELLED = 'cancelled'

class LiveStream(BaseModel):
    __tablename__ = 'live_streams'

    stream_id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey('merchant_profiles.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(255), nullable=True)
    thumbnail_public_id = Column(String(255), nullable=True)
    
    scheduled_time = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    
    is_live = Column(Boolean, default=False, nullable=False)
    status = Column(SQLAlchemyEnum(StreamStatus), default=StreamStatus.SCHEDULED, nullable=False)
    
    viewers_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    
    stream_key = Column(String(255), unique=True, nullable=False)  # Unique key for stream access
    stream_url = Column(String(255), nullable=True)  # RTMP URL for streaming
    
    # YouTube Integration fields
    youtube_event_id = Column(String(255), nullable=True)  # YouTube Live event ID
    youtube_broadcast_url = Column(String(500), nullable=True)  # YouTube broadcast URL
    youtube_stream_url = Column(String(500), nullable=True)  # YouTube stream URL for embedding
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    merchant = relationship('MerchantProfile', backref=db.backref('live_streams', lazy='dynamic'))
    product = relationship('Product', backref=db.backref('live_streams', lazy='dynamic'))
    comments = relationship('LiveStreamComment', back_populates='stream', lazy='dynamic', cascade='all, delete-orphan')
    viewers = relationship('LiveStreamViewer', back_populates='stream', lazy='dynamic', cascade='all, delete-orphan')

    def serialize(self):
        return {
            "stream_id": self.stream_id,
            "merchant_id": self.merchant_id,
            "product_id": self.product_id,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_live": self.is_live,
            "status": self.status.value,
            "viewers_count": self.viewers_count,
            "likes_count": self.likes_count,
            "stream_key": self.stream_key,
            "stream_url": self.stream_url,
            "youtube_event_id": self.youtube_event_id,
            "youtube_broadcast_url": self.youtube_broadcast_url,
            "youtube_stream_url": self.youtube_stream_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "merchant": {
                "id": self.merchant.id,
                "business_name": self.merchant.business_name,
                "business_email": self.merchant.business_email,
                "user": {
                    "id": self.merchant.user.id,
                    "first_name": self.merchant.user.first_name,
                    "last_name": self.merchant.user.last_name,
                    "email": self.merchant.user.email
                }
            } if self.merchant else None,
            "product": self.product.serialize() if self.product else None,
            "comments": [comment.serialize() for comment in self.comments],
            "viewers": [viewer.serialize() for viewer in self.viewers]
        }

    @classmethod
    def get_by_id(cls, stream_id):
        """Get stream by ID."""
        return cls.query.filter_by(stream_id=stream_id).first()

    @classmethod
    def get_by_merchant(cls, merchant_id):
        """Get all streams for a merchant."""
        return cls.query.filter_by(merchant_id=merchant_id).all()

    @classmethod
    def get_active_streams(cls):
        """Get all active streams."""
        return cls.query.filter_by(is_live=True).all()

    @classmethod
    def is_slot_available(cls, product_id, scheduled_time):
        # Check for any stream for this product that overlaps the requested slot
        slot_end = scheduled_time + timedelta(hours=1)
        conflict = cls.query.filter(
            cls.product_id == product_id,
            cls.deleted_at == None,
            cls.scheduled_time < slot_end,
            (cls.scheduled_time + timedelta(hours=1)) > scheduled_time
        ).first()
        return conflict is None

class LiveStreamComment(BaseModel):
    __tablename__ = 'live_stream_comments'

    comment_id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('live_streams.stream_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    stream = relationship('LiveStream', back_populates='comments')
    user = relationship('User', backref=db.backref('stream_comments', lazy='dynamic'))

    def serialize(self):
        return {
            "comment_id": self.comment_id,
            "stream_id": self.stream_id,
            "user_id": self.user_id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "user": {
                "id": self.user.id,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": self.user.email,
                "role": self.user.role.value
            } if self.user else None
        }

class LiveStreamViewer(BaseModel):
    __tablename__ = 'live_stream_viewers'

    viewer_id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey('live_streams.stream_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)

    # Relationships
    stream = relationship('LiveStream', back_populates='viewers')
    user = relationship('User', backref=db.backref('viewed_streams', lazy='dynamic'))

    def serialize(self):
        return {
            "viewer_id": self.viewer_id,
            "stream_id": self.stream_id,
            "user_id": self.user_id,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "left_at": self.left_at.isoformat() if self.left_at else None,
            "user": {
                "id": self.user.id,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": self.user.email,
                "role": self.user.role.value
            } if self.user else None
        }

    @classmethod
    def get_active_viewers(cls, stream_id):
        """Get all active viewers for a stream."""
        return cls.query.filter_by(stream_id=stream_id, left_at=None).all()

    @classmethod
    def get_viewer_history(cls, stream_id):
        """Get viewer history for a stream."""
        return cls.query.filter_by(stream_id=stream_id).all() 