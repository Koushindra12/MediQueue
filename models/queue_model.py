from datetime import datetime, date
from bson import ObjectId
from database.mongodb import mongo
import logging

logger = logging.getLogger(__name__)


class QueueModel:
    """Queue management model."""
    
    COLLECTION = 'queue'
    
    # Queue Status Constants
    STATUS_WAITING = 'waiting'
    STATUS_CALLED = 'called'
    STATUS_IN_CONSULTATION = 'in_consultation'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'
    
    # Priority Constants
    PRIORITY_NORMAL = 'normal'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_EMERGENCY = 'emergency'
    
    @staticmethod
    def add_to_queue(data: dict) -> dict:
        """Add patient to queue."""
        today = datetime.utcnow().date().isoformat()
        
        queue_entry = {
            'patient_id': data.get('patient_id'),
            'patient_name': data.get('patient_name'),
            'patient_phone': data.get('patient_phone'),
            'token_number': data.get('token_number'),
            'token_display': f"TKN-{data.get('token_number', 0):03d}",
            'department': data.get('department', 'General'),
            'doctor': data.get('doctor', 'Dr. General Physician'),
            'reason': data.get('reason', '').strip(),
            'priority': data.get('priority', QueueModel.PRIORITY_NORMAL),
            'status': QueueModel.STATUS_WAITING,
            'date': today,
            'estimated_wait': data.get('estimated_wait', 15),
            'position': data.get('position', 1),
            'qr_code_path': data.get('qr_code_path', ''),
            'notes': data.get('notes', '').strip(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'called_at': None,
            'consultation_start': None,
            'consultation_end': None,
            'actual_wait_time': None,
            'actual_consultation_time': None
        }
        
        result = mongo.db.queue.insert_one(queue_entry)
        queue_entry['_id'] = result.inserted_id
        return queue_entry
    
    @staticmethod
    def get_today_queue() -> list:
        """Get today's complete queue."""
        today = datetime.utcnow().date().isoformat()
        pipeline = [
            {'$match': {'date': today}},
            {'$addFields': {'priority_order': {
                '$switch': {'branches': [
                    {'case': {'$eq': ['$priority', 'emergency']}, 'then': 3},
                    {'case': {'$eq': ['$priority', 'urgent']}, 'then': 2}
                ], 'default': 1}
            }}},
            {'$sort': {'priority_order': -1, 'token_number': 1}}
        ]
        return list(mongo.db.queue.aggregate(pipeline))
    
    @staticmethod
    def get_active_queue() -> list:
        """Get active (waiting + called) queue for today."""
        today = datetime.utcnow().date().isoformat()
        pipeline = [
            {'$match': {'date': today, 'status': {'$in': [
                QueueModel.STATUS_WAITING,
                QueueModel.STATUS_CALLED,
                QueueModel.STATUS_IN_CONSULTATION
            ]}}},
            {'$addFields': {'priority_order': {
                '$switch': {'branches': [
                    {'case': {'$eq': ['$priority', 'emergency']}, 'then': 3},
                    {'case': {'$eq': ['$priority', 'urgent']}, 'then': 2}
                ], 'default': 1}
            }}},
            {'$sort': {'priority_order': -1, 'token_number': 1}}
        ]
        return list(mongo.db.queue.aggregate(pipeline))
    
    @staticmethod
    def get_waiting_queue() -> list:
        """Get only waiting patients."""
        today = datetime.utcnow().date().isoformat()
        pipeline = [
            {'$match': {'date': today, 'status': QueueModel.STATUS_WAITING}},
            {'$addFields': {'priority_order': {
                '$switch': {'branches': [
                    {'case': {'$eq': ['$priority', 'emergency']}, 'then': 3},
                    {'case': {'$eq': ['$priority', 'urgent']}, 'then': 2}
                ], 'default': 1}
            }}},
            {'$sort': {'priority_order': -1, 'token_number': 1}}
        ]
        return list(mongo.db.queue.aggregate(pipeline))
    
    @staticmethod
    def find_by_token(token_number: int) -> dict | None:
        """Find queue entry by token number for today."""
        today = datetime.utcnow().date().isoformat()
        return mongo.db.queue.find_one({
            'token_number': token_number,
            'date': today
        })
    
    @staticmethod
    def find_by_id(queue_id: str) -> dict | None:
        """Find queue entry by ID."""
        try:
            return mongo.db.queue.find_one({'_id': ObjectId(queue_id)})
        except Exception:
            return None
    
    @staticmethod
    def update_status(queue_id: str, status: str, extra_data: dict = None) -> bool:
        """Update queue entry status."""
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        if extra_data:
            update_data.update(extra_data)
        
        if status == QueueModel.STATUS_CALLED:
            update_data['called_at'] = datetime.utcnow()
        elif status == QueueModel.STATUS_IN_CONSULTATION:
            update_data['consultation_start'] = datetime.utcnow()
        elif status in [QueueModel.STATUS_COMPLETED, QueueModel.STATUS_NO_SHOW]:
            update_data['consultation_end'] = datetime.utcnow()
        
        result = mongo.db.queue.update_one(
            {'_id': ObjectId(queue_id)},
            {'$set': update_data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def get_current_serving() -> dict | None:
        """Get currently serving patient."""
        today = datetime.utcnow().date().isoformat()
        return mongo.db.queue.find_one({
            'date': today,
            'status': {'$in': [
                QueueModel.STATUS_CALLED,
                QueueModel.STATUS_IN_CONSULTATION
            ]}
        })
    
    @staticmethod
    def get_queue_position(token_number: int) -> int:
        """Get patient's current position in queue."""
        today = datetime.utcnow().date().isoformat()
        count = mongo.db.queue.count_documents({
            'date': today,
            'status': QueueModel.STATUS_WAITING,
            'token_number': {'$lte': token_number}
        })
        return count
    
    @staticmethod
    def get_today_stats() -> dict:
        """Get today's queue statistics."""
        today = datetime.utcnow().date().isoformat()
        
        pipeline = [
            {'$match': {'date': today}},
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(mongo.db.queue.aggregate(pipeline))
        stats = {
            'waiting': 0,
            'called': 0,
            'in_consultation': 0,
            'completed': 0,
            'cancelled': 0,
            'no_show': 0,
            'total': 0
        }
        
        for r in results:
            status = r['_id']
            if status in stats:
                stats[status] = r['count']
            stats['total'] += r['count']
        
        return stats
    
    @staticmethod
    def get_last_token_today() -> int:
        """Get the last token number issued today."""
        today = datetime.utcnow().date().isoformat()
        last = mongo.db.queue.find_one(
            {'date': today},
            sort=[('token_number', -1)]
        )
        return last['token_number'] if last else 0
    
    @staticmethod
    def cancel_token(token_number: int) -> bool:
        """Cancel a token."""
        today = datetime.utcnow().date().isoformat()
        result = mongo.db.queue.update_one(
            {
                'token_number': token_number,
                'date': today,
                'status': QueueModel.STATUS_WAITING
            },
            {
                '$set': {
                    'status': QueueModel.STATUS_CANCELLED,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def serialize(entry: dict) -> dict:
        """Convert MongoDB document to JSON-serializable dict."""
        if entry:
            entry['_id'] = str(entry['_id'])
            for field in ['created_at', 'updated_at', 'called_at', 
                         'consultation_start', 'consultation_end']:
                if entry.get(field):
                    entry[field] = entry[field].isoformat()
        return entry