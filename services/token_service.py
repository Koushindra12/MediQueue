from models.queue_model import QueueModel
from database.mongodb import mongo
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TokenService:
    """Service for generating and managing tokens."""
    
    @staticmethod
    def generate_token() -> int:
        """Generate the next sequential token number for today."""
        last_token = QueueModel.get_last_token_today()
        return last_token + 1
    
    @staticmethod
    def get_token_info(token_number: int) -> dict:
        """Get complete information about a token."""
        entry = QueueModel.find_by_token(token_number)
        if not entry:
            return None
        
        return QueueModel.serialize(entry)
    
    @staticmethod
    def validate_token(token_number: int) -> tuple[bool, str]:
        """Validate if a token is valid and active."""
        entry = QueueModel.find_by_token(token_number)
        
        if not entry:
            return False, "Token not found for today"
        
        if entry['status'] == QueueModel.STATUS_CANCELLED:
            return False, "This token has been cancelled"
        
        if entry['status'] == QueueModel.STATUS_COMPLETED:
            return False, "This consultation has been completed"
        
        if entry['status'] == QueueModel.STATUS_NO_SHOW:
            return False, "Marked as no-show"
        
        return True, "Valid token"
    
    @staticmethod
    def get_token_display(token_number: int) -> str:
        """Get formatted token display string."""
        return f"TKN-{token_number:03d}"
    
    @staticmethod
    def reset_daily_tokens():
        """Reset token counter (called at start of new day)."""
        # Tokens are date-based, so no reset needed
        # This method can be used for cleanup tasks
        logger.info(f"Daily token reset initiated for {datetime.utcnow().date()}")
        return True