from common.database import db, BaseModel

class CategoryAttribute(BaseModel):
    __tablename__ = 'category_attributes'

    category_id   = db.Column(db.Integer, db.ForeignKey('categories.category_id'), primary_key=True)
    attribute_id  = db.Column(db.Integer, db.ForeignKey('attributes.attribute_id'), primary_key=True)
    required_flag = db.Column(db.Boolean, default=False, nullable=False)

    # ←— Two sides of the association:
    category  = db.relationship('Category',  back_populates='attributes')
    attribute = db.relationship('Attribute', back_populates='categories')

    def serialize(self):
        """Convert the CategoryAttribute instance to a dictionary."""
        return {
            'category_id': self.category_id,
            'attribute_id': self.attribute_id,
            'required_flag': self.required_flag,
            'attribute_details': {
                'attribute_id': self.attribute.attribute_id,
                'name': self.attribute.name,
                'code': self.attribute.code
            } if self.attribute else None
        }
