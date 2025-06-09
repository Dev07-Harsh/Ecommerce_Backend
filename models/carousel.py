from common.database import db
from datetime import datetime

class Carousel(db.Model):
    __tablename__ = 'carousels'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'brand' or 'product'
    image_url = db.Column(db.String(255), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)  # brand_id or product_id
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    shareable_link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Carousel {self.id}: {self.type} - {self.target_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'type': self.type,
            'image_url': self.image_url,
            'target_id': self.target_id,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'shareable_link': self.shareable_link,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 