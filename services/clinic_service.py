from database.mongodb import mongo
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    'clinic_name': 'Queue-Cure Medical Center',
    'clinic_tagline': 'Your Health, Our Priority',
    'clinic_address': '123 Health Street, Medical District',
    'clinic_phone': '+1-800-QUEUECURE',
    'clinic_email': 'info@queuecure.com',
    'clinic_website': '',
    'open_time': '09:00',
    'close_time': '17:00',
    'working_days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    'max_queue_size': 100,
    'avg_consultation_time': 15,
    'auto_refresh_interval': 30,
    'enable_qr_codes': True,
    'enable_email_notifications': False,
    'enable_sms_notifications': False,
    'currency': 'USD',
    'timezone': 'UTC',
    'updated_at': None
}


class ClinicService:
    """Service for managing clinic settings stored in MongoDB."""

    COLLECTION = 'clinic_settings'
    SINGLETON_KEY = 'main'

    @staticmethod
    def get_settings() -> dict:
        """Get clinic settings, returning defaults if not set."""
        try:
            settings = mongo.db.clinic_settings.find_one({'_key': ClinicService.SINGLETON_KEY})
            if not settings:
                # Auto-initialize with defaults
                ClinicService._initialize_defaults()
                settings = mongo.db.clinic_settings.find_one({'_key': ClinicService.SINGLETON_KEY})

            if settings:
                settings['_id'] = str(settings['_id'])
                if settings.get('updated_at'):
                    settings['updated_at'] = settings['updated_at'].isoformat()
            return settings or DEFAULT_SETTINGS.copy()
        except Exception as e:
            logger.error(f"Error getting clinic settings: {e}")
            return DEFAULT_SETTINGS.copy()

    @staticmethod
    def update_settings(data: dict) -> bool:
        """Update clinic settings."""
        try:
            allowed_fields = list(DEFAULT_SETTINGS.keys())
            update_data = {k: v for k, v in data.items() if k in allowed_fields}
            update_data['updated_at'] = datetime.utcnow()

            result = mongo.db.clinic_settings.update_one(
                {'_key': ClinicService.SINGLETON_KEY},
                {'$set': update_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating clinic settings: {e}")
            return False

    @staticmethod
    def _initialize_defaults():
        """Insert default settings if not present."""
        try:
            defaults = DEFAULT_SETTINGS.copy()
            defaults['_key'] = ClinicService.SINGLETON_KEY
            defaults['updated_at'] = datetime.utcnow()
            mongo.db.clinic_settings.insert_one(defaults)
        except Exception as e:
            logger.error(f"Error initializing clinic defaults: {e}")

    @staticmethod
    def get_setting(key: str, default=None):
        """Get a single setting value."""
        settings = ClinicService.get_settings()
        return settings.get(key, default or DEFAULT_SETTINGS.get(key))
