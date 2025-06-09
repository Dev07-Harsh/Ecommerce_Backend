from models.carousel import Carousel
from common.database import db
import cloudinary.uploader
from datetime import datetime

class CarouselController:
    @staticmethod
    def list_all():
        """
        Get all active carousel items.
        Returns:
            List[Carousel]: List of all active carousel items
        """
        return Carousel.query.filter_by(deleted_at=None).order_by(Carousel.display_order).all()

    @staticmethod
    def create(data, image_file=None):
        """
        Create a new carousel item. Handles Cloudinary upload if image_file is provided.
        Args:
            data (dict): Carousel item data (type, target_id, display_order, is_active, shareable_link)
            image_file (FileStorage): Image file to upload (optional)
        Returns:
            Carousel: Created carousel item
        """
        image_url = data.get('image_url')
        if image_file:
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="carousel_images",
                resource_type="image"
            )
            image_url = upload_result.get('secure_url')
        carousel = Carousel(
            type=data['type'],
            image_url=image_url,
            target_id=data['target_id'],
            display_order=data.get('display_order', 0),
            is_active=data.get('is_active', True),
            shareable_link=data.get('shareable_link')
        )
        db.session.add(carousel)
        db.session.commit()
        return carousel

    @staticmethod
    def delete(carousel_id):
        """
        Soft delete a carousel item.
        Args:
            carousel_id (int): ID of the carousel item to delete
        Returns:
            Carousel: Deleted carousel item
        """
        carousel = Carousel.query.get_or_404(carousel_id)
        carousel.deleted_at = datetime.utcnow()
        db.session.commit()
        return carousel

    @staticmethod
    def update_display_orders(order_list):
        """
        Update display_order for multiple carousel items.
        Args:
            order_list (list of dict): [{'id': 1, 'display_order': 0}, ...]
        Returns:
            int: Number of updated items
        """
        updated = 0
        for item in order_list:
            carousel = Carousel.query.get(item['id'])
            if carousel and carousel.deleted_at is None:
                carousel.display_order = item['display_order']
                updated += 1
        db.session.commit()
        return updated 