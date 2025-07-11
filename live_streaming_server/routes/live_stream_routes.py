from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the parent directory to the path to import from main backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.database import db
from common.response import success_response, error_response
from common.decorators import merchant_required
from models.live_stream import LiveStream, LiveStreamComment, LiveStreamViewer, StreamStatus
from models.product import Product
from auth.models.models import MerchantProfile, User
from live_streaming_server.services.youtube_live_service import YouTubeLiveService

live_stream_bp = Blueprint('live_streams', __name__)

@live_stream_bp.route('/', methods=['POST'])
@jwt_required()
@merchant_required
def create_live_stream():
    """Create a new live stream."""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Get merchant profile
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
        if not merchant:
            return error_response('Merchant profile not found', 404)
        
        # Validate required fields
        required_fields = ['title', 'product_id', 'description', 'scheduled_time']
        for field in required_fields:
            if field not in data:
                return error_response(f'Missing required field: {field}', 400)
        
        # Validate product exists and belongs to merchant
        product = Product.query.filter_by(
            product_id=data['product_id'],
            merchant_id=merchant.id
        ).first()
        if not product:
            return error_response('Product not found or not owned by merchant', 404)
        
        # Parse scheduled time
        try:
            scheduled_time = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
        except ValueError:
            return error_response('Invalid scheduled_time format. Use ISO format.', 400)
        
        # Check if slot is available
        if not LiveStream.is_slot_available(data['product_id'], scheduled_time):
            return error_response('Time slot is not available for this product', 409)
        
        # Generate unique stream key
        stream_key = str(uuid.uuid4())
        
        # Create live stream
        live_stream = LiveStream(
            merchant_id=merchant.id,
            product_id=data['product_id'],
            title=data['title'],
            description=data['description'],
            scheduled_time=scheduled_time,
            stream_key=stream_key,
            status=StreamStatus.SCHEDULED
        )
        
        db.session.add(live_stream)
        db.session.flush()  # Get the stream ID before committing
        
        # Try to create YouTube Live event
        youtube_event_data = None
        try:
            youtube_service = YouTubeLiveService()
            youtube_event_data = youtube_service.create_youtube_live_event(
                title=data['title'],
                description=data['description'],
                scheduled_time=scheduled_time
            )
            
            if youtube_event_data:
                live_stream.youtube_event_id = youtube_event_data['broadcast_id']
                live_stream.youtube_broadcast_url = youtube_event_data['watch_url']
                live_stream.youtube_stream_url = youtube_event_data['embed_url']
                
        except Exception as e:
            # Log the error but don't fail the stream creation
            print(f"Warning: Failed to create YouTube event: {str(e)}")
        
        db.session.commit()
        
        response_data = live_stream.serialize()
        if youtube_event_data:
            response_data['youtube_integration'] = {
                'status': 'success',
                'broadcast_id': youtube_event_data['broadcast_id'],
                'watch_url': youtube_event_data['watch_url'],
                'embed_url': youtube_event_data['embed_url']
            }
        else:
            response_data['youtube_integration'] = {
                'status': 'failed',
                'message': 'Stream created successfully but YouTube integration failed'
            }
        
        return success_response('Live stream created successfully', response_data, 201)
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error creating live stream: {str(e)}', 500)

@live_stream_bp.route('/', methods=['GET'])
@jwt_required()
def get_live_streams():
    """Get all live streams with optional filtering."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        # Query parameters
        status = request.args.get('status')
        merchant_id = request.args.get('merchant_id')
        product_id = request.args.get('product_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Build query
        query = LiveStream.query.filter_by(deleted_at=None)
        
        if status:
            query = query.filter_by(status=StreamStatus(status))
        
        if merchant_id:
            query = query.filter_by(merchant_id=merchant_id)
        
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        # If user is merchant, show only their streams
        if user.role.value == 'merchant':
            merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
            if merchant:
                query = query.filter_by(merchant_id=merchant.id)
        
        # Order by scheduled time
        query = query.order_by(LiveStream.scheduled_time.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        streams = [stream.serialize() for stream in pagination.items]
        
        return success_response('Live streams retrieved successfully', {
            'streams': streams,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return error_response(f'Error retrieving live streams: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>', methods=['GET'])
@jwt_required()
def get_live_stream(stream_id):
    """Get a specific live stream by ID."""
    try:
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        return success_response('Live stream retrieved successfully', live_stream.serialize())
        
    except Exception as e:
        return error_response(f'Error retrieving live stream: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>', methods=['PUT'])
@jwt_required()
@merchant_required
def update_live_stream(stream_id):
    """Update a live stream."""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Get merchant profile
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
        if not merchant:
            return error_response('Merchant profile not found', 404)
        
        # Get live stream
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        # Check ownership
        if live_stream.merchant_id != merchant.id:
            return error_response('Unauthorized to update this stream', 403)
        
        # Update fields
        if 'title' in data:
            live_stream.title = data['title']
        if 'description' in data:
            live_stream.description = data['description']
        if 'scheduled_time' in data:
            try:
                scheduled_time = datetime.fromisoformat(data['scheduled_time'].replace('Z', '+00:00'))
                # Check if slot is available (excluding current stream)
                if not LiveStream.is_slot_available(live_stream.product_id, scheduled_time):
                    return error_response('Time slot is not available', 409)
                live_stream.scheduled_time = scheduled_time
            except ValueError:
                return error_response('Invalid scheduled_time format', 400)
        
        db.session.commit()
        
        return success_response('Live stream updated successfully', live_stream.serialize())
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error updating live stream: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>', methods=['DELETE'])
@jwt_required()
@merchant_required
def delete_live_stream(stream_id):
    """Delete a live stream."""
    try:
        user_id = get_jwt_identity()
        
        # Get merchant profile
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
        if not merchant:
            return error_response('Merchant profile not found', 404)
        
        # Get live stream
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        # Check ownership
        if live_stream.merchant_id != merchant.id:
            return error_response('Unauthorized to delete this stream', 403)
        
        # Soft delete
        live_stream.deleted_at = datetime.utcnow()
        live_stream.status = StreamStatus.CANCELLED
        
        db.session.commit()
        
        return success_response('Live stream deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error deleting live stream: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>/start', methods=['POST'])
@jwt_required()
@merchant_required
def start_live_stream(stream_id):
    """Start a live stream."""
    try:
        user_id = get_jwt_identity()
        
        # Get merchant profile
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
        if not merchant:
            return error_response('Merchant profile not found', 404)
        
        # Get live stream
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        # Check ownership
        if live_stream.merchant_id != merchant.id:
            return error_response('Unauthorized to start this stream', 403)
        
        # Check if stream can be started
        if live_stream.status != StreamStatus.SCHEDULED:
            return error_response('Stream cannot be started. Invalid status.', 400)
        
        # Start stream
        live_stream.status = StreamStatus.LIVE
        live_stream.is_live = True
        live_stream.start_time = datetime.utcnow()
        
        db.session.commit()
        
        return success_response('Live stream started successfully', live_stream.serialize())
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error starting live stream: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>/end', methods=['POST'])
@jwt_required()
@merchant_required
def end_live_stream(stream_id):
    """End a live stream."""
    try:
        user_id = get_jwt_identity()
        
        # Get merchant profile
        merchant = MerchantProfile.query.filter_by(user_id=user_id).first()
        if not merchant:
            return error_response('Merchant profile not found', 404)
        
        # Get live stream
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        # Check ownership
        if live_stream.merchant_id != merchant.id:
            return error_response('Unauthorized to end this stream', 403)
        
        # End stream
        live_stream.status = StreamStatus.ENDED
        live_stream.is_live = False
        live_stream.end_time = datetime.utcnow()
        
        # Update viewer records
        active_viewers = LiveStreamViewer.get_active_viewers(stream_id)
        for viewer in active_viewers:
            viewer.left_at = datetime.utcnow()
        
        db.session.commit()
        
        return success_response('Live stream ended successfully', live_stream.serialize())
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error ending live stream: {str(e)}', 500)

@live_stream_bp.route('/available-slots', methods=['GET'])
@jwt_required()
def get_available_slots():
    """Get available time slots for a product on a specific date."""
    try:
        product_id = request.args.get('product_id')
        date_str = request.args.get('date')
        
        if not product_id or not date_str:
            return error_response('product_id and date are required', 400)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return error_response('Invalid date format. Use YYYY-MM-DD', 400)
        
        # Generate available slots (12 AM to 12 PM, hourly slots)
        available_slots = []
        for hour in range(0, 12):  # 12 AM to 11 AM (ending at 12 PM)
            slot_time = datetime.combine(date, datetime.min.time().replace(hour=hour))
            available = LiveStream.is_slot_available(int(product_id), slot_time)
            print(f"Checking slot {slot_time}: available={available}")
            if available:
                available_slots.append(f"{hour:02d}:00")
        
        response_data = {
            'available_slots': available_slots
        }
        print(f"Response data: {response_data}")
        
        response = success_response('Available slots retrieved successfully', response_data)
        print(f"Success response: {response}")
        return response
        
    except Exception as e:
        print(f"Error in /available-slots: {e}")
        return error_response(f'Error retrieving available slots: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>/join', methods=['POST'])
@jwt_required()
def join_stream(stream_id):
    """Join a live stream as a viewer."""
    try:
        user_id = get_jwt_identity()
        
        # Get live stream
        live_stream = LiveStream.get_by_id(stream_id)
        if not live_stream:
            return error_response('Live stream not found', 404)
        
        # Check if stream is live
        if not live_stream.is_live:
            return error_response('Stream is not live', 400)
        
        # Check if user is already viewing
        existing_viewer = LiveStreamViewer.query.filter_by(
            stream_id=stream_id,
            user_id=user_id,
            left_at=None
        ).first()
        
        if existing_viewer:
            return success_response('Already viewing stream')
        
        # Create viewer record
        viewer = LiveStreamViewer(
            stream_id=stream_id,
            user_id=user_id
        )
        
        # Update viewer count
        live_stream.viewers_count += 1
        
        db.session.add(viewer)
        db.session.commit()
        
        return success_response('Joined stream successfully')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error joining stream: {str(e)}', 500)

@live_stream_bp.route('/<int:stream_id>/leave', methods=['POST'])
@jwt_required()
def leave_stream(stream_id):
    """Leave a live stream."""
    try:
        user_id = get_jwt_identity()
        
        # Get viewer record
        viewer = LiveStreamViewer.query.filter_by(
            stream_id=stream_id,
            user_id=user_id,
            left_at=None
        ).first()
        
        if not viewer:
            return error_response('Not currently viewing this stream', 400)
        
        # Update viewer record
        viewer.left_at = datetime.utcnow()
        
        # Update viewer count
        live_stream = LiveStream.get_by_id(stream_id)
        if live_stream and live_stream.viewers_count > 0:
            live_stream.viewers_count -= 1
        
        db.session.commit()
        
        return success_response('Left stream successfully')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error leaving stream: {str(e)}', 500) 