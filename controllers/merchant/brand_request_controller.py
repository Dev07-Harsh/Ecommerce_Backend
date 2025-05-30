# controllers/merchant/brand_request_controller.py

from flask_jwt_extended import get_jwt_identity
from flask import abort
from common.database import db
from models.brand_request import BrandRequest, BrandRequestStatus
from auth.models.models import MerchantProfile 

class MerchantBrandRequestController:
    @staticmethod
    def list_all():
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, description="Merchant profile not found")
        return BrandRequest.query.filter_by(merchant_id=merchant.id).all()

    @staticmethod
    def create(data):
        user_id = get_jwt_identity()
        merchant = MerchantProfile.get_by_user_id(user_id)
        if not merchant:
            abort(404, description="Merchant profile not found")

        br = BrandRequest(
            merchant_id=merchant.id,
            name=data['brand_name'],
            status=BrandRequestStatus.PENDING
        )
        br.save()
        return br
