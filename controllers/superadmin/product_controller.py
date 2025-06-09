from models.product import Product
from common.database import db

class ProductController:
    @staticmethod
    def list_all():
        """
        Get all active products.
        Returns:
            List[Product]: List of all active products
        """
        return Product.query.filter_by(deleted_at=None).all() 