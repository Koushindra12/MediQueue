from flask import Blueprint, request, jsonify
from models.doctor_model import DoctorModel
from utils.helpers import api_response, validate_required_fields, sanitize_input
import logging

logger = logging.getLogger(__name__)

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')


@doctor_bp.route('/api/list', methods=['GET'])
def list_doctors():
    """List all doctors."""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        doctors = DoctorModel.find_all(include_inactive=include_inactive)
        serialized = [DoctorModel.serialize(d) for d in doctors]
        return api_response(True, f'{len(serialized)} doctors found', {
            'doctors': serialized,
            'stats': DoctorModel.get_statistics()
        })
    except Exception as e:
        logger.error(f"List doctors error: {e}")
        return api_response(False, str(e), status_code=500)


@doctor_bp.route('/api/add', methods=['POST'])
def add_doctor():
    """Add a new doctor."""
    try:
        data = sanitize_input(request.json or {})

        required = ['name', 'department']
        valid, message = validate_required_fields(data, required)
        if not valid:
            return api_response(False, message, status_code=400)

        doctor = DoctorModel.create_doctor(data)
        serialized = DoctorModel.serialize(doctor)

        # Broadcast via socket
        try:
            from socket_events.queue_events import broadcast_doctors_update
            broadcast_doctors_update()
        except Exception:
            pass

        return api_response(True, f"Dr. {doctor['name']} added successfully", {
            'doctor': serialized
        })

    except Exception as e:
        logger.error(f"Add doctor error: {e}")
        return api_response(False, f'Failed to add doctor: {str(e)}', status_code=500)


@doctor_bp.route('/api/<doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    """Get a specific doctor."""
    try:
        doctor = DoctorModel.find_by_id(doctor_id)
        if not doctor:
            return api_response(False, 'Doctor not found', status_code=404)
        return api_response(True, 'Doctor found', {'doctor': DoctorModel.serialize(doctor)})
    except Exception as e:
        logger.error(f"Get doctor error: {e}")
        return api_response(False, str(e), status_code=500)


@doctor_bp.route('/api/<doctor_id>', methods=['PUT'])
def update_doctor(doctor_id):
    """Update doctor details."""
    try:
        data = sanitize_input(request.json or {})
        success = DoctorModel.update_doctor(doctor_id, data)

        if not success:
            return api_response(False, 'Doctor not found or no changes made', status_code=404)

        # Broadcast update
        try:
            from socket_events.queue_events import broadcast_doctors_update
            broadcast_doctors_update()
        except Exception:
            pass

        return api_response(True, 'Doctor updated successfully')

    except Exception as e:
        logger.error(f"Update doctor error: {e}")
        return api_response(False, str(e), status_code=500)


@doctor_bp.route('/api/<doctor_id>/deactivate', methods=['POST'])
def deactivate_doctor(doctor_id):
    """Deactivate a doctor."""
    try:
        success = DoctorModel.deactivate_doctor(doctor_id)
        if not success:
            return api_response(False, 'Doctor not found', status_code=404)

        try:
            from socket_events.queue_events import broadcast_doctors_update
            broadcast_doctors_update()
        except Exception:
            pass

        return api_response(True, 'Doctor deactivated successfully')
    except Exception as e:
        logger.error(f"Deactivate doctor error: {e}")
        return api_response(False, str(e), status_code=500)


@doctor_bp.route('/api/<doctor_id>/reactivate', methods=['POST'])
def reactivate_doctor(doctor_id):
    """Reactivate a doctor."""
    try:
        success = DoctorModel.reactivate_doctor(doctor_id)
        if not success:
            return api_response(False, 'Doctor not found', status_code=404)

        try:
            from socket_events.queue_events import broadcast_doctors_update
            broadcast_doctors_update()
        except Exception:
            pass

        return api_response(True, 'Doctor reactivated successfully')
    except Exception as e:
        logger.error(f"Reactivate doctor error: {e}")
        return api_response(False, str(e), status_code=500)


@doctor_bp.route('/api/by-department/<department>', methods=['GET'])
def doctors_by_department(department):
    """Get doctors for a specific department."""
    try:
        doctors = DoctorModel.find_by_department(department)
        serialized = [DoctorModel.serialize(d) for d in doctors]
        return api_response(True, f'{len(serialized)} doctors found', {'doctors': serialized})
    except Exception as e:
        logger.error(f"Doctors by dept error: {e}")
        return api_response(False, str(e), status_code=500)
