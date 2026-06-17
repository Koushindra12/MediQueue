from flask import Blueprint, render_template, request, jsonify
from services.queue_service import QueueService
from services.waittime_service import WaitTimeService
from services.clinic_service import ClinicService
from models.queue_model import QueueModel
from models.patient_model import PatientModel
from models.doctor_model import DoctorModel
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
        clinic_settings = ClinicService.get_settings()
        return render_template('receptionist.html',
                               departments=departments,
                               clinic_settings=clinic_settings)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('receptionist.html',
                               departments=QueueService.DEPARTMENTS,
                               clinic_settings={},
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

        # Only name, phone, age, gender are required — email/blood_group/medical_history/allergies are optional
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
            'email': data.get('email', ''),           # optional
            'age': data.get('age'),
            'gender': data.get('gender'),
            'blood_group': data.get('blood_group', ''),    # optional
            'address': data.get('address', ''),
            'medical_history': data.get('medical_history', ''),  # optional
            'emergency_contact': data.get('emergency_contact', ''),
            'allergies': data.get('allergies', '')         # optional
        }

        queue_data = {
            'department': data.get('department', 'General Medicine'),
            'doctor': data.get('doctor', ''),  # may be overridden by dynamic lookup
            'reason': data.get('reason', ''),
            'priority': data.get('priority', 'normal'),
            'notes': data.get('notes', '')
        }

        result = QueueService.register_and_queue(patient_data, queue_data)

        # Broadcast queue update via socket
        try:
            from socket_events.queue_events import broadcast_queue_update
            broadcast_queue_update()
        except Exception:
            pass

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
            # Socket broadcast
            try:
                from socket_events.queue_events import broadcast_queue_update, notify_patient_called
                called = result.get('patient', {})
                if called:
                    notify_patient_called(called.get('token_number', 0), called.get('patient_name', ''))
                broadcast_queue_update()
            except Exception:
                pass
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
        if result.get('success'):
            try:
                from socket_events.queue_events import broadcast_queue_update
                broadcast_queue_update()
            except Exception:
                pass
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
        if result.get('success'):
            try:
                from socket_events.queue_events import broadcast_queue_update
                broadcast_queue_update()
            except Exception:
                pass
        return api_response(result['success'], result['message'], result)
    except Exception as e:
        logger.error(f"Complete consultation error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/no-show/<queue_id>', methods=['POST'])
def mark_no_show(queue_id):
    """Mark as no-show."""
    try:
        result = QueueService.mark_no_show(queue_id)
        if result.get('success'):
            try:
                from socket_events.queue_events import broadcast_queue_update
                broadcast_queue_update()
            except Exception:
                pass
        return api_response(result['success'], result['message'])
    except Exception as e:
        logger.error(f"No-show error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/queue/cancel/<int:token_number>', methods=['POST'])
def cancel_token(token_number):
    """Cancel a token."""
    try:
        result = QueueService.cancel_queue_entry(token_number)
        if result.get('success'):
            try:
                from socket_events.queue_events import broadcast_queue_update
                broadcast_queue_update()
            except Exception:
                pass
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


@receptionist_bp.route('/api/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get patient details."""
    try:
        patient = PatientModel.find_by_id(patient_id)
        if not patient:
            return api_response(False, 'Patient not found', status_code=404)
        return api_response(True, 'Patient found', {'patient': PatientModel.serialize(patient)})
    except Exception as e:
        logger.error(f"Get patient error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/patients/<patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Update patient details."""
    try:
        data = sanitize_input(request.json or {})
        # Remove protected fields
        data.pop('_id', None)
        data.pop('created_at', None)
        data.pop('visit_count', None)
        success = PatientModel.update_patient(patient_id, data)
        if not success:
            return api_response(False, 'Patient not found or no changes made', status_code=404)
        return api_response(True, 'Patient updated successfully')
    except Exception as e:
        logger.error(f"Update patient error: {e}")
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


@receptionist_bp.route('/api/waiting-room', methods=['GET'])
def get_waiting_room():
    """Get waiting room data."""
    try:
        waiting = QueueModel.get_waiting_queue()
        current = QueueModel.get_current_serving()
        stats = WaitTimeService.get_queue_statistics()
        serialized_waiting = [QueueModel.serialize(e) for e in waiting]
        return api_response(True, 'Waiting room data retrieved', {
            'waiting': serialized_waiting,
            'current_serving': QueueModel.serialize(current) if current else None,
            'stats': stats,
            'total_waiting': len(waiting)
        })
    except Exception as e:
        logger.error(f"Waiting room error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get comprehensive statistics."""
    try:
        queue_stats = WaitTimeService.get_queue_statistics()
        patient_stats = PatientModel.get_statistics()
        consultation_stats = ConsultationModel.get_statistics()
        doctor_stats = DoctorModel.get_statistics()

        return api_response(True, 'Statistics retrieved', {
            'queue': queue_stats,
            'patients': patient_stats,
            'consultations': consultation_stats,
            'doctors': doctor_stats
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return api_response(False, str(e), status_code=500)


# ─────────────────────────────────────────────
# Clinic Settings API
# ─────────────────────────────────────────────

@receptionist_bp.route('/api/clinic/settings', methods=['GET'])
def get_clinic_settings():
    """Get clinic settings."""
    try:
        settings = ClinicService.get_settings()
        return api_response(True, 'Settings retrieved', {'settings': settings})
    except Exception as e:
        logger.error(f"Get settings error: {e}")
        return api_response(False, str(e), status_code=500)


@receptionist_bp.route('/api/clinic/settings', methods=['PUT'])
def update_clinic_settings():
    """Update clinic settings."""
    try:
        data = request.json or {}
        success = ClinicService.update_settings(data)
        if success:
            # Broadcast settings change
            try:
                from socket_events.queue_events import broadcast_clinic_update
                broadcast_clinic_update()
            except Exception:
                pass
            return api_response(True, 'Clinic settings updated successfully')
        return api_response(False, 'Failed to update settings', status_code=500)
    except Exception as e:
        logger.error(f"Update settings error: {e}")
        return api_response(False, str(e), status_code=500)