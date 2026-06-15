from datetime import datetime
from bson import ObjectId
from database.mongodb import mongo
import logging

logger = logging.getLogger(__name__)


class ConsultationModel:
    """Consultation records model."""
    
    COLLECTION = 'consultations'
    
    @staticmethod
    def create_consultation(data: dict) -> dict:
        """Create a new consultation record."""
        consultation = {
            'patient_id': data.get('patient_id'),
            'queue_id': data.get('queue_id'),
            'patient_name': data.get('patient_name'),
            'token_number': data.get('token_number'),
            'doctor': data.get('doctor', 'Dr. General Physician'),
            'department': data.get('department', 'General'),
            'diagnosis': data.get('diagnosis', '').strip(),
            'prescription': data.get('prescription', '').strip(),
            'notes': data.get('notes', '').strip(),
            'follow_up_date': data.get('follow_up_date'),
            'status': 'active',
            'date': datetime.utcnow().date().isoformat(),
            'start_time': datetime.utcnow(),
            'end_time': None,
            'duration_minutes': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = mongo.db.consultations.insert_one(consultation)
        consultation['_id'] = result.inserted_id
        return consultation
    
    @staticmethod
    def complete_consultation(consultation_id: str, data: dict) -> bool:
        """Complete a consultation."""
        end_time = datetime.utcnow()
        
        update_data = {
            'status': 'completed',
            'end_time': end_time,
            'diagnosis': data.get('diagnosis', ''),
            'prescription': data.get('prescription', ''),
            'notes': data.get('notes', ''),
            'follow_up_date': data.get('follow_up_date'),
            'updated_at': end_time
        }
        
        consultation = mongo.db.consultations.find_one({'_id': ObjectId(consultation_id)})
        if consultation and consultation.get('start_time'):
            duration = (end_time - consultation['start_time']).seconds // 60
            update_data['duration_minutes'] = duration
        
        result = mongo.db.consultations.update_one(
            {'_id': ObjectId(consultation_id)},
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def get_patient_history(patient_id: str) -> list:
        """Get consultation history for a patient."""
        return list(
            mongo.db.consultations.find({'patient_id': patient_id})
            .sort('date', -1)
            .limit(20)
        )
    
    @staticmethod
    def get_today_consultations() -> list:
        """Get today's consultations."""
        today = datetime.utcnow().date().isoformat()
        return list(
            mongo.db.consultations.find({'date': today})
            .sort('start_time', -1)
        )
    
    @staticmethod
    def get_statistics() -> dict:
        """Get consultation statistics."""
        today = datetime.utcnow().date().isoformat()
        
        total_today = mongo.db.consultations.count_documents({'date': today})
        completed_today = mongo.db.consultations.count_documents({
            'date': today,
            'status': 'completed'
        })
        
        # Average duration
        pipeline = [
            {'$match': {'date': today, 'status': 'completed', 'duration_minutes': {'$exists': True}}},
            {'$group': {'_id': None, 'avg_duration': {'$avg': '$duration_minutes'}}}
        ]
        
        avg_result = list(mongo.db.consultations.aggregate(pipeline))
        avg_duration = round(avg_result[0]['avg_duration'], 1) if avg_result else 15
        
        return {
            'total_today': total_today,
            'completed_today': completed_today,
            'avg_duration': avg_duration
        }
    
    @staticmethod
    def serialize(consultation: dict) -> dict:
        """Convert MongoDB document to JSON-serializable dict."""
        if consultation:
            consultation['_id'] = str(consultation['_id'])
            for field in ['start_time', 'end_time', 'created_at', 'updated_at']:
                if consultation.get(field):
                    consultation[field] = consultation[field].isoformat()
        return consultation