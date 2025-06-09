from models.category_attribute import CategoryAttribute
from models.category import Category 
from models.attribute import Attribute 
from common.database import db
from sqlalchemy.exc import IntegrityError 

class CategoryAttributeController:
    @staticmethod
    def list_attributes_for_category(cat_id): 
        """Lists all attributes associated with a specific category."""
        
        # Check if category exists and is not deleted
        category = Category.query.filter_by(category_id=cat_id).first()
        if not category:
            raise ValueError(f"Category with ID {cat_id} not found.")
        if category.deleted_at is not None:
            raise ValueError(f"Category with ID {cat_id} has been deleted.")

        # Get all attributes for the category with their details
        category_attributes = db.session.query(
            CategoryAttribute,
            Attribute
        ).join(
            Attribute,
            CategoryAttribute.attribute_id == Attribute.attribute_id
        ).filter(
            CategoryAttribute.category_id == cat_id
        ).all()
        
        # Format the response
        result = []
        for ca, attr in category_attributes:
            result.append({
                'category_id': ca.category_id,
                'attribute_id': ca.attribute_id,
                'required_flag': ca.required_flag,
                'attribute_details': {
                    'attribute_id': attr.attribute_id,
                    'name': attr.name,
                    'code': attr.code
                }
            })
        
        return result

    @staticmethod
    def add_attribute_to_category(cat_id, data):
        """Adds an attribute to a category."""
        Category.query.filter_by(category_id=cat_id).first_or_404(
            description=f"Category with ID {cat_id} not found."
        )
        
        attr_id = data.get('attribute_id') 
        if attr_id is None: 
            raise ValueError("attribute_id is required.")
        try:
            attr_id = int(attr_id)
        except ValueError:
            raise ValueError("attribute_id must be an integer.")


        Attribute.query.filter_by(attribute_id=attr_id).first_or_404(
            description=f"Attribute with ID {attr_id} not found."
        )

        required_flag = data.get('required_flag', False)
        if not isinstance(required_flag, bool):
            
            if isinstance(required_flag, str):
                if required_flag.lower() == 'true':
                    required_flag = True
                elif required_flag.lower() == 'false':
                    required_flag = False
                else:
                    raise ValueError("required_flag must be a boolean (true, false, 'true', or 'false').")
            else:
                raise ValueError("required_flag must be a boolean (true or false).")

        existing_association = CategoryAttribute.query.filter_by(
            category_id=cat_id,
            attribute_id=attr_id
        ).first()

        if existing_association:
            raise IntegrityError(f"Attribute ID {attr_id} is already associated with Category ID {cat_id}.", [], '')


        category_attribute = CategoryAttribute(
            category_id=cat_id,
            attribute_id=attr_id,
            required_flag=required_flag
        )
        db.session.add(category_attribute)
        db.session.commit()
        return category_attribute

    @staticmethod
    def update_category_attribute(cat_id, attr_id, data):
        """Updates the required_flag for an attribute associated with a category."""
        category_attribute = CategoryAttribute.query.filter_by(
            category_id=cat_id,
            attribute_id=attr_id
        ).first_or_404(
            description=f"No association found for Category ID {cat_id} and Attribute ID {attr_id}."
        )

        if 'required_flag' not in data:
            raise ValueError("required_flag is required for update.")
        
        required_flag = data.get('required_flag')
        if not isinstance(required_flag, bool):
            if isinstance(required_flag, str):
                if required_flag.lower() == 'true':
                    required_flag = True
                elif required_flag.lower() == 'false':
                    required_flag = False
                else:
                    raise ValueError("required_flag must be a boolean (true, false, 'true', or 'false').")
            else:
                raise ValueError("required_flag must be a boolean (true or false).")


        category_attribute.required_flag = required_flag
        db.session.commit()
        return category_attribute

    @staticmethod
    def remove_attribute_from_category(cat_id, attr_id):
        """Removes an attribute association from a category."""
        category_attribute = CategoryAttribute.query.filter_by(
            category_id=cat_id,
            attribute_id=attr_id
        ).first_or_404(
            description=f"No association found for Category ID {cat_id} and Attribute ID {attr_id} to delete."
        )
        db.session.delete(category_attribute)
        db.session.commit()
        