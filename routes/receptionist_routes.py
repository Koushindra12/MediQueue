from flask import Blueprint, render_template, request, jsonify
from services.queue_service import QueueService
from services.waittime_service import WaitTimeService
from models.queue_model import QueueModel
from models.patient_model import PatientModel
from models.consultation_model import ConsultationModel
from utils.helpers import (
    api_response, validate_required_fields, 
    sanitize_input, validate_phone
)
import logging

logger = logging.getLogger(__name__)

receptionist_bp = Blueprint('receptionist', __name__, url_prefix='/receptionist')


@receptionist_bp.route('/', methods=['GET'])
def dashboard():
    """Receptionist dashboard."""
    try:
        departments = QueueService.get_departments()
        return render_template('receptionist.html', 
                             departments=departments)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('receptionist.html', 
                             departments=QueueService.DEPARTMENTS,
                             error=str(e))


@receptionist_bp.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get dashboard data via API."""
    try:
        data = QueueService.get_dashboard_data()
        return api_response(True, 'Dashboard data retrieved', data)
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/register', methods=['POST'])
def register_patient():
    """Register new patient and add to queue."""
    try:
        data = sanitize_input(request.json or {})
        
        # Validate required fields
        patient_fields = ['name', 'phone', 'age', 'gender']
        valid, message = validate_required_fields(data, patient_fields)
        if not valid:
            return api_response(False, message, status_code=400)
        
        # Validate phone
        if not validate_phone(data.get('phone', '')):
            return api_response(False, 'Invalid phone number format', status_code=400)
        
        # Separate patient and queue data
        patient_data = {
            'name': data.get('name'),
            'phone': data.get('phone'),
            'email': data.get('email', ''),
            'age': data.get('age'),
            'gender': data.get('gender'),
            'blood_group': data.get('blood_group', ''),
            'address': data.get('address', ''),
            'medical_history': data.get('medical_history', ''),
            'emergency_contact': data.get('emergency_contact', ''),
            'allergies': data.get('allergies', '')
        }
        
        queue_data = {
            'department': data.get('department', 'General Medicine'),
            'reason': data.get('reason', ''),
            'priority': data.get('priority', 'normal'),
            'notes': data.get('notes', '')
        }
        
        result = QueueService.register_and_queue(patient_data, queue_data)
        
        return api_response(
            True, 
            f"Patient registered successfully. Token: {result['token_display']}",
            result
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return api_response(False, f'Registration failed: {str(e)}', status_code=500)


@receptionist_bp.route('/api/queue/call-next', methods=['POST'])
def call_next():
    """Call next patient."""
    try:
        result = QueueService.call_next_patient()
        if result and result.get('success'):
            return api_response(True, result.get('message', 'Next patient called'), result)
        else:
            return api_response(False, result.get('message', 'No patients in queue'), 
                              result, status_code=400)
    except Exception as e:
        logger.error(f"Call next error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/start-consultation/<queue_id>', methods=['POST'])
def start_consultation(queue_id):
    """Start consultation."""
    try:
        result = QueueService.start_consultation(queue_id)
        return api_response(result['success'], result['message'], result)
    except Exception as e:
        logger.error(f"Start consultation error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/complete/<queue_id>', methods=['POST'])
def complete_consultation(queue_id):
    """Complete consultation."""
    try:
        data = request.json or {}
        result = QueueService.complete_consultation(queue_id, data)
        return api_response(result['success'], result['message'], result)
    except Exception as e:
        logger.error(f"Complete consultation error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/no-show/<queue_id>', methods=['POST'])
def mark_no_show(queue_id):
    """Mark as no-show."""
    try:
        result = QueueService.mark_no_show(queue_id)
        return api_response(result['success'], result['message'])
    except Exception as e:
        logger.error(f"No-show error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/cancel/<int:token_number>', methods=['POST'])
def cancel_token(token_number):
    """Cancel a token."""
    try:
        result = QueueService.cancel_queue_entry(token_number)
        return api_response(result['success'], result['message'])
    except Exception as e:
        logger.error(f"Cancel token error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/patients/search', methods=['GET'])
def search_patients():
    """Search patients."""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return api_response(False, 'Search query too short', status_code=400)
        
        patients = PatientModel.search_patients(query)
        serialized = [PatientModel.serialize(p) for p in patients]
        return api_response(True, f'Found {len(patients)} patients', {'patients': serialized})
    except Exception as e:
        logger.error(f"Search error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/today', methods=['GET'])
def get_today_queue():
    """Get today's full queue."""
    try:
        queue = QueueModel.get_today_queue()
        serialized = [QueueModel.serialize(e) for e in queue]
        stats = WaitTimeService.get_queue_statistics()
        return api_response(True, 'Queue retrieved', {
            'queue': serialized, 
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Queue fetch error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get comprehensive statistics."""
    try:
        queue_stats = WaitTimeService.get_queue_statistics()
        patient_stats = PatientModel.get_statistics()
        consultation_stats = ConsultationModel.get_statistics()
        
        return api_response(True, 'Statistics retrieved', {
            'queue': queue_stats,
            'patients': patient_stats,
            'consultations': consultation_stats
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return api_response(False, str(e), status_code=500)