from flask_socketio import SocketIO, emit, join_room, leave_room
from models.queue_model import QueueModel
from services.waittime_service import WaitTimeService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

socketio = SocketIO()


def init_socketio(app):
    """Initialize SocketIO with app."""
    socketio.init_app(
        app,
      cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False
    )
    register_events()
    return socketio


def register_events():
    """Register all SocketIO events."""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info(f"Client connected: {request_sid()}")
        emit('connected', {
            'status': 'connected',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Connected to Queue-Cure system'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {request_sid()}")
    
    @socketio.on('join_queue_room')
    def handle_join_queue(data):
        """Join queue monitoring room."""
        room = data.get('room', 'queue_updates')
        join_room(room)
        
        # Send current queue state
        try:
            current = QueueModel.get_current_serving()
            stats = WaitTimeService.get_queue_statistics()
            
            emit('queue_state', {
                'current_serving': QueueModel.serialize(current) if current else None,
                'stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Join queue room error: {e}")
    
    @socketio.on('join_token_room')
    def handle_join_token(data):
        """Join specific token's room for personalized updates."""
        token_number = data.get('token_number')
        if token_number:
            room = f'token_{token_number}'
            join_room(room)
            
            # Send current status
            try:
                entry = QueueModel.find_by_token(int(token_number))
                if entry:
                    wait_info = WaitTimeService.calculate_wait_time(int(token_number))
                    emit('token_status', {
                        'entry': QueueModel.serialize(entry),
                        'wait_info': wait_info,
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.error(f"Join token room error: {e}")
    
    @socketio.on('leave_room_event')
    def handle_leave_room(data):
        """Leave a room."""
        room = data.get('room')
        if room:
            leave_room(room)
    
    @socketio.on('request_queue_update')
    def handle_queue_update_request():
        """Handle request for queue update."""
        try:
            broadcast_queue_update()
        except Exception as e:
            logger.error(f"Queue update request error: {e}")
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection health check."""
        emit('pong', {'timestamp': datetime.utcnow().isoformat()})


def broadcast_queue_update():
    """Broadcast queue update to all connected clients."""
    try:
        current = QueueModel.get_current_serving()
        active_queue = QueueModel.get_active_queue()
        stats = WaitTimeService.get_queue_statistics()
        
        data = {
            'current_serving': QueueModel.serialize(current) if current else None,
            'active_queue': [QueueModel.serialize(e) for e in active_queue],
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        socketio.emit('queue_update', data, room='queue_updates')
        logger.debug("Queue update broadcasted")
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")


def notify_patient_called(token_number: int, patient_name: str):
    """Notify specific patient that they've been called."""
    try:
        room = f'token_{token_number}'
        socketio.emit('patient_called', {
            'token_number': token_number,
            'patient_name': patient_name,
            'message': f'🎉 {patient_name}, please proceed to the consultation room!',
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        # Also broadcast to queue room
        socketio.emit('patient_called_broadcast', {
            'token_display': f'TKN-{token_number:03d}',
            'message': f'Now serving Token #{token_number:03d}',
            'timestamp': datetime.utcnow().isoformat()
        }, room='queue_updates')
        
    except Exception as e:
        logger.error(f"Patient notification error: {e}")


def notify_queue_position_update():
    """Notify all waiting patients of position updates."""
    try:
        waiting = QueueModel.get_waiting_queue()
        
        for i, entry in enumerate(waiting):
            token_number = entry['token_number']
            room = f'token_{token_number}'
            wait_info = WaitTimeService.calculate_wait_time(token_number)
            
            socketio.emit('position_update', {
                'token_number': token_number,
                'position': i + 1,
                'wait_info': wait_info,
                'timestamp': datetime.utcnow().isoformat()
            }, room=room)
            
    except Exception as e:
        logger.error(f"Position update notification error: {e}")


def request_sid():
    """Get current request SID safely."""
    try:
        from flask import request
        return request.sid
    except Exception:
        return 'unknown'