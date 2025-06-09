# controllers/superadmin/brand_request_controller.py
from datetime import datetime
from common.database import db
from models.brand_request import BrandRequest, BrandRequestStatus
from models.brand import Brand
from sqlalchemy.exc import IntegrityError
import re

class BrandRequestController:
    @staticmethod
    def list_pending():
        """Get all pending brand requests"""
        return BrandRequest.query.filter_by(
            status=BrandRequestStatus.PENDING,
            deleted_at=None
        ).all()

    @staticmethod
    def approve(request_id, admin_id, icon_url=None):
        """Approve a brand request and create/update the brand"""
        request = BrandRequest.query.filter_by(
            request_id=request_id,
            deleted_at=None
        ).first()
        
        if not request:
            raise FileNotFoundError(f"Brand request {request_id} not found")
        
        if request.status != BrandRequestStatus.PENDING:
            raise ValueError(f"Brand request {request_id} is not in pending status")

        # Generate slug from brand name
        base_slug = request.name.lower()
        base_slug = re.sub(r'\s+', '-', base_slug)
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
        base_slug = re.sub(r'-+', '-', base_slug).strip('-')
        
        # Ensure slug is unique
        temp_slug = base_slug
        counter = 1
        while Brand.query.filter_by(slug=temp_slug, deleted_at=None).first():
            temp_slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > 100:
                raise ValueError(f"Could not generate a unique slug for brand: {request.name}")

        # Create or update brand
        brand = Brand.query.filter_by(name=request.name, deleted_at=None).first()
        if brand:
            # Update existing brand
            brand.approved_by = admin_id
            brand.approved_at = datetime.utcnow()
            if icon_url:
                brand.icon_url = icon_url
        else:
            # Create new brand
            brand = Brand(
                name=request.name,
                slug=temp_slug,
                icon_url=icon_url,
                approved_by=admin_id,
                approved_at=datetime.utcnow()
            )
            db.session.add(brand)

        # Update request status
        request.status = BrandRequestStatus.APPROVED
        request.reviewer_id = admin_id
        request.reviewed_at = datetime.utcnow()

        try:
            db.session.commit()
            return brand
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Failed to create/update brand: {str(e)}")

    @staticmethod
    def reject(request_id, admin_id, notes):
        """Reject a brand request"""
        request = BrandRequest.query.filter_by(
            request_id=request_id,
            deleted_at=None
        ).first()
        
        if not request:
            raise FileNotFoundError(f"Brand request {request_id} not found")
        
        if request.status != BrandRequestStatus.PENDING:
            raise ValueError(f"Brand request {request_id} is not in pending status")

        request.status = BrandRequestStatus.REJECTED
        request.reviewer_id = admin_id
        request.reviewed_at = datetime.utcnow()
        request.notes = notes

        try:
            db.session.commit()
            return request
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Failed to reject brand request: {str(e)}")
