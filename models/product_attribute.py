from datetime import datetime
from common.database import db, BaseModel
from auth.models.models import MerchantProfile
from models.category import Category
from models.brand import Brand

class ProductAttribute(BaseModel):
    __tablename__ = 'product_attributes'
    
    # Surrogate primary key
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Natural keys / fks
    product_id    = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    attribute_id  = db.Column(db.Integer, db.ForeignKey('attributes.attribute_id'), nullable=False)
    
    # Three “value” columns, only one used per-input_type
    value_code    = db.Column(db.String(50), nullable=True)   # for SELECT / MULTISELECT
    value_text    = db.Column(db.String(255), nullable=True)  # for TEXT
    value_number  = db.Column(db.Float,   nullable=True)      # for NUMBER

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enforce that (product,attribute,code) is unique when code is present
    __table_args__ = (
        db.UniqueConstraint('product_id', 'attribute_id', 'value_code', name='uq_product_attribute_code'),
        db.ForeignKeyConstraint(
            ['attribute_id', 'value_code'],
            ['attribute_values.attribute_id', 'attribute_values.value_code'],
            name='fk_attrvalue',
            ondelete='CASCADE'
        ),
    )
    
    # Relationships
    attribute = db.relationship('Attribute', foreign_keys=[attribute_id])
    attribute_value = db.relationship('AttributeValue',
        primaryjoin="and_(ProductAttribute.attribute_id==AttributeValue.attribute_id, "
                    "ProductAttribute.value_code==AttributeValue.value_code)",
        foreign_keys=[attribute_id, value_code],
        overlaps="attribute"
    )
    
    def serialize(self):
        # Make it easy for the front-end
        val = None
        if self.attribute.input_type == 'select' or self.attribute.input_type == 'multiselect':
            val = self.value_code
        elif self.attribute.input_type == 'number':
            val = self.value_number
        else:
            val = self.value_text
        
        return {
            "id": self.id,
            "product_id": self.product_id,
            "attribute_id": self.attribute_id,
            "value": val,
            "attribute": self.attribute.serialize() if self.attribute else None,
            "attribute_value": self.attribute_value.serialize() if self.attribute_value else None,
        }
