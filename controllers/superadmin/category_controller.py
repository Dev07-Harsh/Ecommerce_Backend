from models.category import Category
from common.database import db
from sqlalchemy.exc import IntegrityError

class CategoryController:
    @staticmethod
    def list_all():
        return Category.query.all()

    @staticmethod
    def get(category_id):
        return Category.query.get_or_404(category_id)

    @staticmethod
    def get_main_categories():
        """
        Retrieve only the main categories (categories without a parent_id)
        """
        return Category.query.filter(Category.parent_id.is_(None)).all()

    @staticmethod
    def create(data):
        cat = Category(
            name=data['name'],
            slug=data['slug'],
            parent_id=data.get('parent_id'),
            icon_url=data.get('icon_url')  
        )
        cat.save()
        return cat

    @staticmethod
    def update(category_id, data):
        cat = Category.query.get_or_404(category_id)
        cat.name = data.get('name', cat.name)
        cat.slug = data.get('slug', cat.slug)
        cat.parent_id = data.get('parent_id', cat.parent_id)
        cat.icon_url = data.get('icon_url', cat.icon_url)  
        db.session.commit()
        return cat

    @staticmethod
    def delete(category_id):
        cat = Category.query.get_or_404(category_id)
        db.session.delete(cat)
        db.session.commit()
        return cat
