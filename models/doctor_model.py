from datetime import datetime
from bson import ObjectId
from database.mongodb import mongo
import logging

logger = logging.getLogger(__name__)


class DoctorModel:
    """Doctor data model with CRUD operations."""

    COLLECTION = 'doctors'

    @staticmethod
    def create_doctor(data: dict) -> dict:
        """Create a new doctor record."""
        doctor = {
            'name': data.get('name', '').strip().title(),
            'specialization': data.get('specialization', '').strip(),
            'department': data.get('department', 'General Medicine').strip(),
            'phone': data.get('phone', '').strip(),
            'email': data.get('email', '').strip().lower(),
            'qualification': data.get('qualification', '').strip(),
            'experience_years': int(data.get('experience_years', 0)),
            'availability': data.get('availability', 'active'),  # 'active' | 'inactive' | 'on_leave'
            'schedule_notes': data.get('schedule_notes', '').strip(),
            'consultation_fee': float(data.get('consultation_fee', 0)),
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }

        result = mongo.db.doctors.insert_one(doctor)
        doctor['_id'] = result.inserted_id
        return doctor

    @staticmethod
    def find_by_id(doctor_id: str) -> dict | None:
        """Find doctor by ID."""
        try:
            return mongo.db.doctors.find_one({'_id': ObjectId(doctor_id)})
        except Exception:
            return None

    @staticmethod
    def find_by_department(department: str) -> list:
        """Find active doctors by department."""
        return list(mongo.db.doctors.find({
            'department': department,
            'is_active': True,
            'availability': 'active'
        }))

    @staticmethod
    def find_all(include_inactive: bool = False) -> list:
        """Get all doctors."""
        query = {} if include_inactive else {'is_active': True}
        return list(
            mongo.db.doctors.find(query)
            .sort([('department', 1), ('name', 1)])
        )

    @staticmethod
    def update_doctor(doctor_id: str, data: dict) -> bool:
        """Update doctor information."""
        allowed_fields = [
            'name', 'specialization', 'department', 'phone', 'email',
            'qualification', 'experience_years', 'availability',
            'schedule_notes', 'consultation_fee'
        ]
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        if not update_data:
            return False

        # Type coercions
        if 'name' in update_data:
            update_data['name'] = update_data['name'].strip().title()
        if 'email' in update_data:
            update_data['email'] = update_data['email'].strip().lower()
        if 'experience_years' in update_data:
            update_data['experience_years'] = int(update_data['experience_years'])
        if 'consultation_fee' in update_data:
            update_data['consultation_fee'] = float(update_data['consultation_fee'])

        update_data['updated_at'] = datetime.utcnow()

        result = mongo.db.doctors.update_one(
            {'_id': ObjectId(doctor_id)},
            {'$set': update_data}
        )
        return result.modified_count > 0

    @staticmethod
    def deactivate_doctor(doctor_id: str) -> bool:
        """Soft-delete a doctor (mark as inactive)."""
        result = mongo.db.doctors.update_one(
            {'_id': ObjectId(doctor_id)},
            {'$set': {'is_active': False, 'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    def reactivate_doctor(doctor_id: str) -> bool:
        """Reactivate a deactivated doctor."""
        result = mongo.db.doctors.update_one(
            {'_id': ObjectId(doctor_id)},
            {'$set': {'is_active': True, 'availability': 'active', 'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    def get_department_doctor_map() -> dict:
        """Get a mapping of department -> primary doctor name for queue assignment."""
        doctors = DoctorModel.find_all(include_inactive=False)
        dept_map = {}
        for doc in doctors:
            dept = doc.get('department', '')
            if dept and dept not in dept_map:
                dept_map[dept] = doc.get('name', 'Dr. General Physician')
        return dept_map

    @staticmethod
    def get_statistics() -> dict:
        """Get doctor statistics."""
        total = mongo.db.doctors.count_documents({'is_active': True})
        active = mongo.db.doctors.count_documents({'is_active': True, 'availability': 'active'})
        on_leave = mongo.db.doctors.count_documents({'is_active': True, 'availability': 'on_leave'})
        return {
            'total': total,
            'active': active,
            'on_leave': on_leave,
            'inactive': total - active - on_leave
        }

    @staticmethod
    def serialize(doctor: dict) -> dict:
        """Convert MongoDB document to JSON-serializable dict."""
        if doctor:
            doctor['_id'] = str(doctor['_id'])
            if doctor.get('created_at'):
                doctor['created_at'] = doctor['created_at'].isoformat()
            if doctor.get('updated_at'):
                doctor['updated_at'] = doctor['updated_at'].isoformat()
        return doctor
