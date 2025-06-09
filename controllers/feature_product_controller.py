from flask import current_app
from models.product_placement import ProductPlacement, PlacementTypeEnum
from models.product import Product
from models.product_media import ProductMedia, MediaType
from common.database import db
from datetime import datetime, timezone
from sqlalchemy import desc

class FeatureProductController:
    @staticmethod
    def get_featured_products(page=1, per_page=12):
        """
        Get all featured products with pagination.
        Returns products that are currently active in featured placements.
        """
        try:
            now_utc = datetime.now(timezone.utc)
            
            # Query to get featured products with their placements
            query = Product.query.join(
                ProductPlacement,
                Product.product_id == ProductPlacement.product_id
            ).filter(
                ProductPlacement.placement_type == PlacementTypeEnum.FEATURED,
                ProductPlacement.is_active == True,
                (ProductPlacement.expires_at == None) | (ProductPlacement.expires_at > now_utc),
                Product.deleted_at == None,
                Product.active_flag == True,
                Product.approval_status == 'approved'
            ).order_by(
                ProductPlacement.sort_order.asc(),
                ProductPlacement.added_at.desc()
            )

            # Get total count for pagination
            total = query.count()

            # Apply pagination
            products = query.offset((page - 1) * per_page).limit(per_page).all()

            # Serialize products with their placement details and media
            serialized_products = []
            for product in products:
                product_data = product.serialize()
                
                # Get the placement details for this product
                placement = ProductPlacement.query.filter_by(
                    product_id=product.product_id,
                    placement_type=PlacementTypeEnum.FEATURED,
                    is_active=True
                ).first()
                
                if placement:
                    product_data['placement'] = {
                        'placement_id': placement.placement_id,
                        'sort_order': placement.sort_order,
                        'added_at': placement.added_at.isoformat() if placement.added_at else None,
                        'expires_at': placement.expires_at.isoformat() if placement.expires_at else None
                    }
                
                # Get product media
                media = ProductMedia.query.filter_by(
                    product_id=product.product_id,
                    deleted_at=None
                ).order_by(
                    ProductMedia.sort_order.asc()
                ).all()
                
                # Add media URLs to product data
                product_data['images'] = [
                    m.url for m in media 
                    if m.type == MediaType.IMAGE
                ]
                
                serialized_products.append(product_data)

            return {
                'products': serialized_products,
                'pagination': {
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                    'current_page': page,
                    'per_page': per_page
                }
            }

        except Exception as e:
            current_app.logger.error(f"Error getting featured products: {str(e)}")
            raise RuntimeError("Failed to retrieve featured products") from e

    @staticmethod
    def get_featured_product_details(product_id):
        """
        Get detailed information about a specific featured product.
        """
        try:
            now_utc = datetime.now(timezone.utc)
            
            # Query to get the product with its featured placement
            product = Product.query.join(
                ProductPlacement,
                Product.product_id == ProductPlacement.product_id
            ).filter(
                Product.product_id == product_id,
                ProductPlacement.placement_type == PlacementTypeEnum.FEATURED,
                ProductPlacement.is_active == True,
                (ProductPlacement.expires_at == None) | (ProductPlacement.expires_at > now_utc),
                Product.deleted_at == None,
                Product.active_flag == True,
                Product.approval_status == 'approved'
            ).first()

            if not product:
                raise ValueError(f"Featured product with ID {product_id} not found or not active")

            # Get the placement details
            placement = ProductPlacement.query.filter_by(
                product_id=product_id,
                placement_type=PlacementTypeEnum.FEATURED,
                is_active=True
            ).first()

            product_data = product.serialize()
            if placement:
                product_data['placement'] = {
                    'placement_id': placement.placement_id,
                    'sort_order': placement.sort_order,
                    'added_at': placement.added_at.isoformat() if placement.added_at else None,
                    'expires_at': placement.expires_at.isoformat() if placement.expires_at else None
                }

            # Get product media
            media = ProductMedia.query.filter_by(
                product_id=product_id,
                deleted_at=None
            ).order_by(
                ProductMedia.sort_order.asc()
            ).all()
            
            # Add media URLs to product data
            product_data['images'] = [
                m.url for m in media 
                if m.type == MediaType.IMAGE
            ]

            return product_data

        except ValueError as e:
            raise e
        except Exception as e:
            current_app.logger.error(f"Error getting featured product details: {str(e)}")
            raise RuntimeError("Failed to retrieve featured product details") from e 