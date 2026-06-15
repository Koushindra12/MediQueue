from datetime import datetime
from bson import ObjectId
from database.mongodb import mongo
import re
import logging

logger = logging.getLogger(__name__)


class PatientModel:
    """Patient data model with CRUD operations."""
    
    COLLECTION = 'patients'
    
    @staticmethod
    def create_patient(data: dict) -> dict:
        """Create a new patient record."""
        patient = {
            'name': data.get('name', '').strip().title(),
            'phone': data.get('phone', '').strip(),
            'email': data.get('email', '').strip().lower(),
            'age': int(data.get('age', 0)),
            'gender': data.get('gender', 'other'),
            'blood_group': data.get('blood_group', ''),
            'address': data.get('address', '').strip(),
            'medical_history': data.get('medical_history', '').strip(),
            'emergency_contact': data.get('emergency_contact', '').strip(),
            'allergies': data.get('allergies', '').strip(),
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'visit_count': 0,
            'last_visit': None
        }
        
        result = mongo.db.patients.insert_one(patient)
        patient['_id'] = result.inserted_id
        return patient
    
    @staticmethod
    def find_by_phone(phone: str) -> dict | None:
        """Find patient by phone number."""
        return mongo.db.patients.find_one({'phone': phone})
    
    @staticmethod
    def find_by_id(patient_id: str) -> dict | None:
        """Find patient by ID."""
        try:
            return mongo.db.patients.find_one({'_id': ObjectId(patient_id)})
        except Exception:
            return None
    
    @staticmethod
    def find_all(limit: int = 50, skip: int = 0) -> list:
        """Get all patients with pagination."""
        return list(
            mongo.db.patients.find({'is_active': True})
            .sort('name', 1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def search_patients(query: str) -> list:
        """Search patients by name or phone."""
        search_filter = {
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'phone': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}}
            ],
            'is_active': True
        }
        return list(mongo.db.patients.find(search_filter).limit(20))
    
    @staticmethod
    def update_patient(patient_id: str, data: dict) -> bool:
        """Update patient information."""
        data['updated_at'] = datetime.utcnow()
        result = mongo.db.patients.update_one(
            {'_id': ObjectId(patient_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def increment_visit_count(patient_id: str):
        """Increment patient visit count."""
        mongo.db.patients.update_one(
            {'_id': ObjectId(patient_id)},
            {
                '$inc': {'visit_count': 1},
                '$set': {'last_visit': datetime.utcnow()}
            }
        )
    
    @staticmethod
    def get_statistics() -> dict:
        """Get patient statistics."""
        total = mongo.db.patients.count_documents({'is_active': True})
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_today = mongo.db.patients.count_documents({
            'created_at': {'$gte': today},
            'is_active': True
        })
        
        return {
            'total_patients': total,
            'new_today': new_today
        }
    
    @staticmethod
    def serialize(patient: dict) -> dict:
        """Convert MongoDB document to JSON-serializable dict."""
        if patient:
            patient['_id'] = str(patient['_id'])
            if patient.get('created_at'):
                patient['created_at'] = patient['created_at'].isoformat()
            if patient.get('updated_at'):
                patient['updated_at'] = patient['updated_at'].isoformat()
            if patient.get('last_visit'):
                patient['last_visit'] = patient['last_visit'].isoformat()
        return patient