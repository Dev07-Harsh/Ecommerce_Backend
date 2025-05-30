from common.database import db, BaseModel
from models.category import Category

class HomepageCategory(BaseModel):
    __tablename__ = 'homepage_categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False,
                          default=db.func.current_timestamp(),
                          onupdate=db.func.current_timestamp())

    # Relationship with Category
    category = db.relationship('Category', backref=db.backref('homepage_entries', lazy='dynamic'))

    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'category_id': self.category_id,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'category': self.category.serialize() if self.category else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def get_active_categories(cls):
        """Get all active categories ordered by display_order"""
        return cls.query.filter_by(is_active=True).order_by(cls.display_order).all()

    @classmethod
    def get_all_categories(cls):
        """Get all categories ordered by display_order"""
        return cls.query.order_by(cls.display_order).all()

    @classmethod
    def update_categories(cls, category_ids):
        """
        Update the homepage categories with a new list of category IDs.
        This will:
        1. Deactivate all existing entries
        2. Create new entries for the provided category IDs
        3. Update existing entries if they're in the new list
        """
        # Deactivate all existing entries
        cls.query.update({'is_active': False})
        
        # Create or update entries for the new category IDs
        for index, category_id in enumerate(category_ids):
            entry = cls.query.filter_by(category_id=category_id).first()
            if entry:
                # Update existing entry
                entry.is_active = True
                entry.display_order = index
            else:
                # Create new entry
                entry = cls(
                    category_id=category_id,
                    display_order=index,
                    is_active=True
                )
                db.session.add(entry)
        
        db.session.commit()
        return cls.get_active_categories() 