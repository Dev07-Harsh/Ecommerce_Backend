# controllers/superadmin/brand_request_controller.py
from models.brand_request import BrandRequest, BrandRequestStatus
from common.database import db
from datetime import datetime, timezone

class BrandRequestController:
    @staticmethod
    def list_pending():
        return BrandRequest.query.filter_by(
            status=BrandRequestStatus.PENDING,
            deleted_at=None
        ).all()

    @staticmethod
    def approve(request_id_from_route, reviewer_id, icon_url=None):
        br = BrandRequest.query.filter_by(
            request_id=request_id_from_route,
            status=BrandRequestStatus.PENDING,
            deleted_at=None
        ).first_or_404(
            description=f"Brand request ID {request_id_from_route} not found or not pending."
        )

        # Only flip the status and set reviewer info
        br.status = BrandRequestStatus.APPROVED
        br.reviewer_id = reviewer_id
        br.reviewed_at = datetime.now(timezone.utc)
        db.session.add(br)

        db.session.commit()
        return br

    @staticmethod
    def reject(request_id_from_route, reviewer_id, notes=None):
        br = BrandRequest.query.filter_by(
            request_id=request_id_from_route,
            status=BrandRequestStatus.PENDING,
            deleted_at=None
        ).first_or_404(
            description=f"Brand request ID {request_id_from_route} not found or not pending."
        )

        br.status = BrandRequestStatus.REJECTED
        br.reviewer_id = reviewer_id
        br.reviewed_at = datetime.now(timezone.utc)
        br.verification_notes = notes
        db.session.add(br)
        db.session.commit()
        return br
