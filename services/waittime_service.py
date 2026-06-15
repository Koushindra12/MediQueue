from models.queue_model import QueueModel
from database.mongodb import mongo
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WaitTimeService:
    """Service for calculating and estimating wait times."""
    
    DEFAULT_CONSULTATION_TIME = 15  # minutes
    
    @staticmethod
    def calculate_wait_time(token_number: int) -> dict:
        """Calculate estimated wait time for a specific token."""
        waiting_queue = QueueModel.get_waiting_queue()
        
        # Find position of this token
        position = 0
        for i, entry in enumerate(waiting_queue):
            if entry['token_number'] == token_number:
                position = i + 1
                break
        
        if position == 0:
            return {
                'position': 0,
                'estimated_wait': 0,
                'estimated_time': 'Now',
                'patients_ahead': 0
            }
        
        # Get average consultation time
        avg_time = WaitTimeService._get_average_consultation_time()
        
        # Patients ahead (excluding current patient)
        patients_ahead = position - 1
        estimated_wait = patients_ahead * avg_time
        
        # Add buffer for current consultation if someone is being served
        current = QueueModel.get_current_serving()
        if current and current.get('consultation_start'):
            elapsed = (datetime.utcnow() - current['consultation_start']).seconds // 60
            remaining = max(0, avg_time - elapsed)
            estimated_wait += remaining
        
        return {
            'position': position,
            'estimated_wait': estimated_wait,
            'estimated_time': f"{estimated_wait} minutes" if estimated_wait > 0 else "Now",
            'patients_ahead': patients_ahead,
            'avg_consultation_time': avg_time
        }
    
    @staticmethod
    def _get_average_consultation_time() -> int:
        """Calculate average consultation time from historical data."""
        try:
            today = datetime.utcnow().date().isoformat()
            pipeline = [
                {
                    '$match': {
                        'date': today,
                        'status': 'completed',
                        'duration_minutes': {'$exists': True, '$gt': 0}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'avg': {'$avg': '$duration_minutes'}
                    }
                }
            ]
            
            result = list(mongo.db.consultations.aggregate(pipeline))
            if result:
                return max(5, int(result[0]['avg']))
            
        except Exception as e:
            logger.warning(f"Could not calculate avg consultation time: {e}")
        
        return WaitTimeService.DEFAULT_CONSULTATION_TIME
    
    @staticmethod
    def get_queue_wait_times() -> list:
        """Get wait times for all waiting patients."""
        waiting_queue = QueueModel.get_waiting_queue()
        avg_time = WaitTimeService._get_average_consultation_time()
        current = QueueModel.get_current_serving()
        
        wait_times = []
        base_wait = 0
        
        # Add remaining time of current consultation
        if current and current.get('consultation_start'):
            elapsed = (datetime.utcnow() - current['consultation_start']).seconds // 60
            base_wait = max(0, avg_time - elapsed)
        
        for i, entry in enumerate(waiting_queue):
            wait = base_wait + (i * avg_time)
            wait_times.append({
                'token_number': entry['token_number'],
                'position': i + 1,
                'estimated_wait': wait,
                'patient_name': entry['patient_name']
            })
        
        return wait_times
    
    @staticmethod
    def get_queue_statistics() -> dict:
        """Get comprehensive queue statistics."""
        stats = QueueModel.get_today_stats()
        avg_time = WaitTimeService._get_average_consultation_time()
        
        waiting_count = stats.get('waiting', 0)
        total_wait = waiting_count * avg_time
        
        return {
            **stats,
            'avg_consultation_time': avg_time,
            'estimated_total_wait': total_wait,
            'queue_health': WaitTimeService._get_queue_health(waiting_count)
        }
    
    @staticmethod
    def _get_queue_health(waiting_count: int) -> str:
        """Determine queue health status."""
        if waiting_count == 0:
            return 'empty'
        elif waiting_count <= 5:
            return 'good'
        elif waiting_count <= 15:
            return 'moderate'
        elif waiting_count <= 25:
            return 'busy'
        else:
            return 'critical'