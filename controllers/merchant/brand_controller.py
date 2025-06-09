from models.brand import Brand
from models.category import Category
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

class MerchantBrandController:
    @staticmethod
    def get(brand_id):
        """Get brand details by ID."""
        try:
            brand = Brand.query.filter_by(
                brand_id=brand_id,
                deleted_at=None
            ).first_or_404(
                description=f"Brand with ID {brand_id} not found."
            )
            return {
                "brand_id": brand.brand_id,
                "name": brand.name,
                "slug": brand.slug,
                "icon_url": brand.icon_url
            }
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Database error while fetching brand: {str(e)}")

    @staticmethod
    def list_all():
        """Get all active brands"""
        return Brand.query.filter_by(deleted_at=None).all()

    @staticmethod
    def get_brands_for_category(category_id):
        """
        Get all active brands associated with a specific category
        Args:
            category_id (int): The ID of the category to filter brands by
        Returns:
            list: List of Brand objects associated with the category
        Raises:
            FileNotFoundError: If category doesn't exist
            SQLAlchemyError: If database error occurs
        """
        try:
            # First verify category exists
            category = Category.query.get(category_id)
            if not category:
                raise FileNotFoundError(f"Category with ID {category_id} not found")

            return Brand.query.join(
                Brand.categories
            ).filter(
                and_(
                    Brand.deleted_at.is_(None),
                    Category.category_id == category_id
                )
            ).all()
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Database error while fetching brands: {str(e)}")

    @staticmethod
    def get_brands_by_categories(category_id, parent_category_id=None):
        """
        Get all active brands associated with a category and optionally its parent category
        Args:
            category_id (int): The ID of the category to filter brands by
            parent_category_id (int, optional): The ID of the parent category
        Returns:
            list: List of Brand objects associated with the categories
        """
        try:
            # First verify category exists
            category = Category.query.get(category_id)
            if not category:
                raise FileNotFoundError(f"Category with ID {category_id} not found")

            query = Brand.query.join(
                Brand.categories
            ).filter(
                and_(
                    Brand.deleted_at.is_(None),
                    Category.category_id == category_id
                )
            )

            if parent_category_id:
                # Verify parent category exists
                parent_category = Category.query.get(parent_category_id)
                if not parent_category:
                    raise FileNotFoundError(f"Parent category with ID {parent_category_id} not found")

                query = query.join(
                    Brand.categories
                ).filter(
                    Category.category_id == parent_category_id
                )

            return query.all()
        except SQLAlchemyError as e:
            raise SQLAlchemyError(f"Database error while fetching brands: {str(e)}")
