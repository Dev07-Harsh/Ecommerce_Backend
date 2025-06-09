from flask import Blueprint, request, jsonify
from controllers.user_address_controller import UserAddressController

user_address_bp = Blueprint('user_address', __name__, url_prefix='/api/user-address')

# Handle OPTIONS requests for all routes
@user_address_bp.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({'status': 'ok'})
        return response

# Create a new address
@user_address_bp.route('', methods=['POST'])
@user_address_bp.route('/', methods=['POST'])
def create_address():
    user_id = request.json.get('user_id')
    return UserAddressController.create_address(user_id)

# Get all addresses for the current user
@user_address_bp.route('', methods=['GET'])
@user_address_bp.route('/', methods=['GET'])
def get_addresses():
    user_id = request.args.get('user_id')
    return UserAddressController.get_addresses(user_id)

# Get a specific address
@user_address_bp.route('/<int:address_id>', methods=['GET'])
def get_address(address_id):
    user_id = request.args.get('user_id')
    return UserAddressController.get_address(user_id, address_id)

# Update an address
@user_address_bp.route('/<int:address_id>', methods=['PUT'])
def update_address(address_id):
    user_id = request.json.get('user_id')
    return UserAddressController.update_address(user_id, address_id)

# Delete an address
@user_address_bp.route('/<int:address_id>', methods=['DELETE'])
def delete_address(address_id):
    user_id = request.args.get('user_id')
    return UserAddressController.delete_address(user_id, address_id)

# Set default address (shipping or billing)
@user_address_bp.route('/<int:address_id>/default/<string:address_type>', methods=['PUT'])
def set_default_address(address_id, address_type):
    if address_type not in ['shipping', 'billing']:
        return {'error': 'Invalid address type. Must be either "shipping" or "billing"'}, 400
    user_id = request.json.get('user_id')
    return UserAddressController.set_default_address(user_id, address_id, address_type) 