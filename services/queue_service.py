from models.queue_model import QueueModel
from models.patient_model import PatientModel
from models.consultation_model import ConsultationModel
from services.token_service import TokenService
from services.waittime_service import WaitTimeService
from utils.qr_generator import QRGenerator
from database.mongodb import mongo
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueueService:
    """Main queue management service."""
    
    DEPARTMENTS = [
        'General Medicine',
        'Cardiology',
        'Orthopedics',
        'Pediatrics',
        'Dermatology',
        'Neurology',
        'Gynecology',
        'Ophthalmology',
        'ENT',
        'Dental'
    ]
    
    DOCTORS = {
        'General Medicine': 'Dr. Sarah Johnson',
        'Cardiology': 'Dr. Michael Chen',
        'Orthopedics': 'Dr. Robert Williams',
        'Pediatrics': 'Dr. Emily Davis',
        'Dermatology': 'Dr. Lisa Anderson',
        'Neurology': 'Dr. James Wilson',
        'Gynecology': 'Dr. Maria Garcia',
        'Ophthalmology': 'Dr. David Lee',
        'ENT': 'Dr. Jennifer Taylor',
        'Dental': 'Dr. Christopher Brown'
    }
    
    @staticmethod
    def register_and_queue(patient_data: dict, queue_data: dict) -> dict:
        """Register patient and add to queue."""
        try:
            # Check if patient exists by phone
            existing_patient = PatientModel.find_by_phone(patient_data.get('phone'))
            
            if existing_patient:
                patient = existing_patient
                PatientModel.increment_visit_count(str(patient['_id']))
                logger.info(f"Existing patient found: {patient['name']}")
            else:
                # Create new patient
                patient = PatientModel.create_patient(patient_data)
                logger.info(f"New patient created: {patient['name']}")
            
            # Generate token
            token_number = TokenService.generate_token()
            
            # Get department and doctor
            department = queue_data.get('department', 'General Medicine')
            doctor = QueueService.DOCTORS.get(department, 'Dr. General Physician')
            
            # Calculate wait time
            waiting_count = len(QueueModel.get_waiting_queue())
            avg_time = 15  # default
            estimated_wait = waiting_count * avg_time
            
            # Generate QR code
            qr_data = {
                'token': token_number,
                'patient': patient['name'],
                'date': datetime.utcnow().date().isoformat()
            }
            qr_path = QRGenerator.generate_queue_qr(token_number, qr_data)
            
            # Add to queue
            queue_entry_data = {
                'patient_id': str(patient['_id']),
                'patient_name': patient['name'],
                'patient_phone': patient['phone'],
                'token_number': token_number,
                'department': department,
                'doctor': doctor,
                'reason': queue_data.get('reason', ''),
                'priority': queue_data.get('priority', QueueModel.PRIORITY_NORMAL),
                'estimated_wait': estimated_wait,
                'position': waiting_count + 1,
                'qr_code_path': qr_path,
                'notes': queue_data.get('notes', '')
            }
            
            queue_entry = QueueModel.add_to_queue(queue_entry_data)
            
            # Recalculate wait time
            wait_info = WaitTimeService.calculate_wait_time(token_number)
            
            return {
                'success': True,
                'patient': PatientModel.serialize(patient),
                'queue_entry': QueueModel.serialize(queue_entry),
                'wait_info': wait_info,
                'token_number': token_number,
                'token_display': TokenService.get_token_display(token_number),
                'qr_code': qr_path
            }
            
        except Exception as e:
            logger.error(f"Error in register_and_queue: {e}")
            raise
    
    @staticmethod
    def call_next_patient() -> dict | None:
        """Call the next patient in queue."""
        try:
            # Check if someone is already being served
            current = QueueModel.get_current_serving()
            if current and current['status'] == QueueModel.STATUS_IN_CONSULTATION:
                return {
                    'success': False,
                    'message': 'Complete current consultation first',
                    'current_patient': QueueModel.serialize(current)
                }
            
            # Get next waiting patient
            waiting = QueueModel.get_waiting_queue()
            if not waiting:
                return {
                    'success': False,
                    'message': 'No patients in queue'
                }
            
            next_patient = waiting[0]
            queue_id = str(next_patient['_id'])
            
            # Update status to called
            QueueModel.update_status(queue_id, QueueModel.STATUS_CALLED)
            
            # Get updated entry
            updated_entry = QueueModel.find_by_id(queue_id)
            
            logger.info(f"Called patient: {next_patient['patient_name']} - Token: {next_patient['token_number']}")
            
            return {
                'success': True,
                'patient': QueueModel.serialize(updated_entry),
                'message': f"Called {next_patient['patient_name']} - Token #{next_patient['token_number']}"
            }
            
        except Exception as e:
            logger.error(f"Error calling next patient: {e}")
            raise
    
    @staticmethod
    def start_consultation(queue_id: str) -> dict:
        """Start consultation for called patient."""
        try:
            queue_entry = QueueModel.find_by_id(queue_id)
            if not queue_entry:
                return {'success': False, 'message': 'Queue entry not found'}
            
            QueueModel.update_status(queue_id, QueueModel.STATUS_IN_CONSULTATION)
            
            # Create consultation record
            consultation = ConsultationModel.create_consultation({
                'patient_id': queue_entry['patient_id'],
                'queue_id': queue_id,
                'patient_name': queue_entry['patient_name'],
                'token_number': queue_entry['token_number'],
                'doctor': queue_entry['doctor'],
                'department': queue_entry['department']
            })
            
            return {
                'success': True,
                'consultation_id': str(consultation['_id']),
                'message': 'Consultation started'
            }
            
        except Exception as e:
            logger.error(f"Error starting consultation: {e}")
            raise
    
    @staticmethod
    def complete_consultation(queue_id: str, consultation_data: dict) -> dict:
        """Complete consultation and update records."""
        try:
            queue_entry = QueueModel.find_by_id(queue_id)
            if not queue_entry:
                return {'success': False, 'message': 'Queue entry not found'}
            
            # Update queue status
            QueueModel.update_status(queue_id, QueueModel.STATUS_COMPLETED)
            
            # Find and complete consultation record
            today = datetime.utcnow().date().isoformat()
            consultation = mongo.db.consultations.find_one({
                'queue_id': queue_id,
                'date': today
            })
            
            if consultation:
                ConsultationModel.complete_consultation(
                    str(consultation['_id']),
                    consultation_data
                )
            
            # Update patient visit count
            if queue_entry.get('patient_id'):
                PatientModel.increment_visit_count(queue_entry['patient_id'])
            
            logger.info(f"Consultation completed for Token: {queue_entry['token_number']}")
            
            return {
                'success': True,
                'message': 'Consultation completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error completing consultation: {e}")
            raise
    
    @staticmethod
    def get_dashboard_data() -> dict:
        """Get comprehensive dashboard data."""
        try:
            queue_stats = WaitTimeService.get_queue_statistics()
            patient_stats = PatientModel.get_statistics()
            active_queue = QueueModel.get_active_queue()
            current = QueueModel.get_current_serving()
            
            serialized_queue = [QueueModel.serialize(e) for e in active_queue]
            
            return {
                'queue_stats': queue_stats,
                'patient_stats': patient_stats,
                'active_queue': serialized_queue,
                'current_serving': QueueModel.serialize(current) if current else None,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            raise
    
    @staticmethod
    def get_departments() -> list:
        """Get list of departments."""
        return QueueService.DEPARTMENTS
    
    @staticmethod
    def mark_no_show(queue_id: str) -> dict:
        """Mark patient as no-show."""
        QueueModel.update_status(queue_id, QueueModel.STATUS_NO_SHOW)
        return {'success': True, 'message': 'Marked as no-show'}
    
    @staticmethod
    def cancel_queue_entry(token_number: int) -> dict:
        """Cancel a queue entry."""
        success = QueueModel.cancel_token(token_number)
        if success:
            return {'success': True, 'message': f'Token #{token_number} cancelled'}
        return {'success': False, 'message': 'Could not cancel token'}