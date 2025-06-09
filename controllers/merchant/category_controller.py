from flask import current_app 
from models.category import Category
from models.category_attribute import CategoryAttribute 
from models.attribute import Attribute 

class MerchantCategoryController:
    @staticmethod
    def get(category_id):
        """Get category details by ID."""
        try:
            category = Category.query.filter_by(category_id=category_id).first_or_404(
                description=f"Category with ID {category_id} not found."
            )
            return {
                "category_id": category.category_id,
                "name": category.name,
                "slug": category.slug,
                "parent_id": category.parent_id
            }
        except Exception as e:
            current_app.logger.error(f"Merchant: Error getting category {category_id}: {e}")
            raise

    @staticmethod
    def list_all():
        """Lists all active categories available to merchants."""
        try:
            return Category.query.order_by(Category.name).all()
        except Exception as e:
            current_app.logger.error(f"Merchant: Error listing categories: {e}")
            raise

    @staticmethod
    def list_attributes_for_category(category_id):
        """
        Lists attributes (and their required flag) associated with a specific category,
        intended for merchant viewing.
        """
        try:
            category = Category.query.filter_by(category_id=category_id).first_or_404(
                description=f"Category with ID {category_id} not found."
            )

            associations = CategoryAttribute.query.filter_by(category_id=category.category_id).all()
            
            # Prepare the data for the merchant
            attributes_data = []
            for assoc in associations:
                if assoc.attribute: 
                    defined_values_data = []
                    
                    if hasattr(assoc.attribute, 'defined_values') and assoc.attribute.defined_values:
                        for val in assoc.attribute.defined_values:
                            defined_values_data.append({
                                "value_code": val.value_code,
                                "value_label": val.value_label
                            })
                    
                    attributes_data.append({
                        "attribute_id": assoc.attribute.attribute_id, 
                        "attribute_name": assoc.attribute.name, 
                        "attribute_code": assoc.attribute.code, 
                        "attribute_type": assoc.attribute.input_type.value if hasattr(assoc.attribute.input_type, 'value') else str(assoc.attribute.input_type), 
                        "required_flag": assoc.required_flag,
                        "defined_values": defined_values_data if defined_values_data else None 
                    })
            
            return attributes_data
        except Exception as e:
            current_app.logger.error(f"Merchant: Error fetching attributes for category {category_id}: {e}")
            raise