from flask import Blueprint, render_template, request, jsonify
from models.queue_model import QueueModel
from models.patient_model import PatientModel
from services.waittime_service import WaitTimeService
from utils.helpers import api_response
import logging

logger = logging.getLogger(__name__)

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


@patient_bp.route('/', methods=['GET'])
def waiting_room():
    """Patient waiting room view."""
    return render_template('waiting_room.html')


@patient_bp.route('/status/<int:token_number>', methods=['GET'])
def token_status(token_number):
    """Get token status page."""
    entry = QueueModel.find_by_token(token_number)
    if entry:
        wait_info = WaitTimeService.calculate_wait_time(token_number)
        return render_template('waiting_room.html', 
                             token=token_number,
                             entry=QueueModel.serialize(entry),
                             wait_info=wait_info)
    return render_template('waiting_room.html', 
                         error=f'Token #{token_number} not found')


@patient_bp.route('/api/status/<int:token_number>', methods=['GET'])
def api_token_status(token_number):
    """API: Get token status."""
    try:
        entry = QueueModel.find_by_token(token_number)
        if not entry:
            return api_response(False, f'Token #{token_number} not found today', 
                              status_code=404)
        
        wait_info = WaitTimeService.calculate_wait_time(token_number)
        
        return api_response(True, 'Token status retrieved', {
            'entry': QueueModel.serialize(entry),
            'wait_info': wait_info
        })
    except Exception as e:
        logger.error(f"Token status error: {e}")
        return api_response(False, str(e), status_code=500)


@patient_bp.route('/api/queue-display', methods=['GET'])
def queue_display():
    """Get queue display data for waiting room screen."""
    try:
        current = QueueModel.get_current_serving()
        waiting = QueueModel.get_waiting_queue()
        stats = WaitTimeService.get_queue_statistics()
        
        # Get next 5 in queue
        next_in_queue = []
        for i, entry in enumerate(waiting[:5]):
            next_in_queue.append({
                'position': i + 1,
                'token_display': entry['token_display'],
                'patient_name': entry['patient_name'][:1] + '***',  # Privacy
                'department': entry['department'],
                'estimated_wait': (i + 1) * stats.get('avg_consultation_time', 15)
            })
        
        return api_response(True, 'Queue display data', {
            'current_serving': QueueModel.serialize(current) if current else None,
            'next_in_queue': next_in_queue,
            'stats': stats,
            'total_waiting': len(waiting)
        })
    except Exception as e:
        logger.error(f"Queue display error: {e}")
        return api_response(False, str(e), status_code=500)


@patient_bp.route('/api/check-token', methods=['POST'])
def check_token():
    """Check token by number."""
    try:
        data = request.json or {}
        token_number = data.get('token_number')
        
        if not token_number:
            return api_response(False, 'Token number required', status_code=400)
        
        try:
            token_number = int(token_number)
        except ValueError:
            return api_response(False, 'Invalid token number', status_code=400)
        
        entry = QueueModel.find_by_token(token_number)
        if not entry:
            return api_response(False, f'Token #{token_number} not found', 
                              status_code=404)
        
        wait_info = WaitTimeService.calculate_wait_time(token_number)
        
        return api_response(True, 'Token found', {
            'entry': QueueModel.serialize(entry),
            'wait_info': wait_info
        })
        
    except Exception as e:
        logger.error(f"Check token error: {e}")
        return api_response(False, str(e), status_code=500)