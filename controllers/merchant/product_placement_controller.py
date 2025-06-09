# controllers/merchant/product_placement_controller.py
from flask import current_app
from flask_jwt_extended import get_jwt_identity
from models.product_placement import ProductPlacement, PlacementTypeEnum 
from models.product import Product 
from auth.models.models import MerchantProfile 
from common.database import db
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta

class MerchantProductPlacementController:
    PLACEMENT_LIMIT_PER_TYPE = 10 

    @staticmethod
    def _get_current_merchant():
        """Helper to get current authenticated merchant's profile."""
        user_id = get_jwt_identity()
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first_or_404(
            description="Merchant profile not found for the current user."
        )
        return merchant

    @staticmethod
    def list_placements(placement_type_filter_str=None):
        """
        Lists all (active and inactive, non-hard-deleted) placements for the current merchant.
        Optionally filters by placement_type.
        """
        merchant = MerchantProductPlacementController._get_current_merchant()
        
        query = ProductPlacement.query.filter_by(merchant_id=merchant.id)
        
        if placement_type_filter_str:
            try:
                placement_type_enum = PlacementTypeEnum[placement_type_filter_str.upper()]
                query = query.filter_by(placement_type=placement_type_enum)
            except KeyError:
                raise ValueError(f"Invalid placement_type filter: {placement_type_filter_str}")
                
        return query.order_by(ProductPlacement.placement_type, ProductPlacement.sort_order, ProductPlacement.added_at.desc()).all()

    @staticmethod
    def get_placement_details(placement_id):
        """Gets details of a specific placement owned by the current merchant."""
        merchant = MerchantProductPlacementController._get_current_merchant()
        placement = ProductPlacement.query.filter_by(
            placement_id=placement_id,
            merchant_id=merchant.id
        ).first_or_404(
            description=f"Product placement with ID {placement_id} not found or not owned by you."
        )
        return placement

    @staticmethod
    def add_product_to_placement(product_id, placement_type_str, sort_order=0, promotional_price=None, special_start=None, special_end=None):
        """
        Adds a merchant's product to a specific placement type (FEATURED or PROMOTED).
        For PROMOTED placements, also updates the product's special pricing and dates.
        """
        merchant = MerchantProductPlacementController._get_current_merchant()

        if not merchant.can_place_premium:
            raise PermissionError("Your account does not have an active subscription for premium product placements.")

        try:
            placement_type_enum = PlacementTypeEnum[placement_type_str.upper()]
        except KeyError:
            allowed_types = [t.name for t in PlacementTypeEnum]
            raise ValueError(f"Invalid placement_type '{placement_type_str}'. Allowed types are: {', '.join(allowed_types)}")

        product = Product.query.filter_by(
            product_id=product_id,
            merchant_id=merchant.id,
            deleted_at=None 
        ).first_or_404(
            description=f"Product with ID {product_id} not found or does not belong to you."
        )

        # Validate promotional data for PROMOTED placements
        if placement_type_enum == PlacementTypeEnum.PROMOTED:
            if not promotional_price or not special_start or not special_end:
                raise ValueError("Promotional price, start date, and end date are required for promoted products.")
            
            try:
                promotional_price = float(promotional_price)
                if promotional_price <= 0:
                    raise ValueError("Promotional price must be greater than 0.")
            except ValueError:
                raise ValueError("Invalid promotional price format.")

            try:
                special_start_date = datetime.strptime(special_start, '%Y-%m-%d').date()
                special_end_date = datetime.strptime(special_end, '%Y-%m-%d').date()
                
                if special_start_date < datetime.now().date():
                    raise ValueError("Special start date cannot be in the past.")
                if special_end_date <= special_start_date:
                    raise ValueError("Special end date must be after start date.")
                if (special_end_date - special_start_date).days > 30:
                    raise ValueError("Promotion period cannot exceed 30 days.")
            except ValueError as e:
                raise ValueError(f"Invalid date format or {str(e)}")

        current_placements_count = ProductPlacement.count_placements_by_merchant_and_type(
            merchant.id, placement_type_enum
        )
        if current_placements_count >= MerchantProductPlacementController.PLACEMENT_LIMIT_PER_TYPE:
            raise ValueError(f"You have reached the limit of {MerchantProductPlacementController.PLACEMENT_LIMIT_PER_TYPE} products for '{placement_type_enum.value}' placements. Please remove an existing one to add a new product.")

        try:
            # Update product with promotional data if it's a PROMOTED placement
            if placement_type_enum == PlacementTypeEnum.PROMOTED:
                product.special_price = promotional_price
                product.special_start = special_start_date
                product.special_end = special_end_date
                db.session.add(product)

            # Create the placement
            new_placement = ProductPlacement(
                product_id=product.product_id,
                merchant_id=merchant.id,
                placement_type=placement_type_enum,
                sort_order=int(sort_order),
                is_active=True,
                expires_at=special_end_date if placement_type_enum == PlacementTypeEnum.PROMOTED else None,
                added_at=datetime.now(timezone.utc)
            )
            db.session.add(new_placement)
            db.session.commit()
            return new_placement
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.warning(f"IntegrityError adding product {product_id} to {placement_type_str} for merchant {merchant.id}: {e}")
            raise ValueError(f"This product is already in '{placement_type_str}' placements.") from e
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding product {product_id} to {placement_type_str} for merchant {merchant.id}: {e}")
            raise RuntimeError("An unexpected error occurred while adding product to placement.") from e

    @staticmethod
    def update_placement_sort_order(placement_id, new_sort_order):
        """Updates the sort order of a merchant's product placement."""
        merchant = MerchantProductPlacementController._get_current_merchant()
        
        placement = ProductPlacement.query.filter_by(
            placement_id=placement_id,
            merchant_id=merchant.id
        ).first_or_404(
             description=f"Product placement with ID {placement_id} not found or not owned by you."
        )

        try:
            placement.sort_order = int(new_sort_order)
            db.session.commit()
            return placement
        except ValueError:
            raise ValueError("Sort order must be an integer.")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating sort order for placement {placement_id}: {e}")
            raise RuntimeError("Could not update sort order.")

    @staticmethod
    def remove_product_from_placement(placement_id):
        """
        Hard deletes a product placement for the current merchant.
        This frees up a slot.
        """
        merchant = MerchantProductPlacementController._get_current_merchant()
        
        placement = ProductPlacement.query.filter_by(
            placement_id=placement_id,
            merchant_id=merchant.id
        ).first_or_404(
             description=f"Product placement with ID {placement_id} not found or not owned by you."
        )
        
        try:
            db.session.delete(placement)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error hard deleting placement {placement_id}: {e}")
            raise RuntimeError("Could not remove product from placement.")