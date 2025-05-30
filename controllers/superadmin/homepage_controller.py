from models.homepage import HomepageCategory
from common.database import db

class HomepageController:
    @staticmethod
    def get_featured_categories():
        """Get all active featured categories"""
        return HomepageCategory.get_active_categories()

    @staticmethod
    def update_featured_categories(category_ids):
        """
        Update the featured categories on the homepage
        Args:
            category_ids (list): List of category IDs to feature
        Returns:
            list: Updated list of featured categories
        """
        try:
            return HomepageCategory.update_categories(category_ids)
        except Exception as e:
            db.session.rollback()
            raise e 