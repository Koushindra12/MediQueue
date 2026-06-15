from flask_pymongo import PyMongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging

logger = logging.getLogger(__name__)

# Global PyMongo instance
mongo = PyMongo()


def init_db(app):
    """Initialize MongoDB connection and create indexes."""
    try:
        mongo.init_app(app)
        
        with app.app_context():
            _create_indexes()
            logger.info("✅ MongoDB connected successfully")
            return mongo
            
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


def _create_indexes():
    """Create database indexes for optimal performance."""
    try:
        # Patients collection indexes
        mongo.db.patients.create_index([('phone', ASCENDING)], unique=True)
        mongo.db.patients.create_index([('email', ASCENDING)])
        mongo.db.patients.create_index([('created_at', DESCENDING)])
        
        # Queue collection indexes
        mongo.db.queue.create_index([('token_number', ASCENDING)])
        mongo.db.queue.create_index([('status', ASCENDING)])
        mongo.db.queue.create_index([('created_at', DESCENDING)])
        mongo.db.queue.create_index([('date', ASCENDING), ('status', ASCENDING)])
        
        # Consultations collection indexes
        mongo.db.consultations.create_index([('patient_id', ASCENDING)])
        mongo.db.consultations.create_index([('token_number', ASCENDING)])
        mongo.db.consultations.create_index([('date', DESCENDING)])
        mongo.db.consultations.create_index([('status', ASCENDING)])
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ Index creation warning: {e}")


def get_db():
    """Get database instance."""
    return mongo.db


def check_connection():
    """Check if MongoDB connection is alive."""
    try:
        mongo.db.command('ping')
        return True
    except Exception:
        return False