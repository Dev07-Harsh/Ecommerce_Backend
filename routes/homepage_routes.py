from flask import Blueprint
from controllers.homepage_controller import HomepageController
from flask_cors import cross_origin

homepage_bp = Blueprint('homepage', __name__)

@homepage_bp.route('/products', methods=['GET', 'OPTIONS'])
@homepage_bp.route('/products/', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_homepage_products():
    """Get products from categories selected for homepage display"""
    return HomepageController.get_homepage_products() 
    