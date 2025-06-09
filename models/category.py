from common.database import db, BaseModel

class Category(BaseModel):
    __tablename__ = 'categories'

    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id   = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=True)
    name        = db.Column(db.String(100), nullable=False, unique=True)
    slug        = db.Column(db.String(100), nullable=False, unique=True)
    icon_url    = db.Column(db.String(255), nullable=True)  
    created_at  = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at  = db.Column(db.DateTime, nullable=False,
                            default=db.func.current_timestamp(),
                            onupdate=db.func.current_timestamp())
    deleted_at  = db.Column(db.DateTime, nullable=True)

    # ←— Association to CategoryAttribute
    attributes = db.relationship(
        'CategoryAttribute',
        back_populates='category',
        cascade='all, delete-orphan'
    )

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'category_id': self.category_id,
            'parent_id': self.parent_id,
            'name': self.name,
            'slug': self.slug,
            'icon_url': self.icon_url,  
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'deleted_at': self.deleted_at
        }
