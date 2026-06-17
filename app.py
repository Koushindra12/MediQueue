import os


from flask import Flask, redirect, url_for, render_template
from config import config
from database.mongodb import init_db
from socket_events.queue_events import init_socketio
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
# Fix Windows cp1252 encoding for emoji in log messages
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp1252', 'mbcs'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Ensure static directories exist
    _create_directories(app)

    # Initialize database
    try:
        init_db(app)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # Register blueprints
    from routes.receptionist_routes import receptionist_bp
    from routes.patient_routes import patient_bp
    from routes.doctor_routes import doctor_bp

    app.register_blueprint(receptionist_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)

    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('receptionist.dashboard'))

    # Health check
    @app.route('/health')
    def health():
        from database.mongodb import check_connection
        db_status = check_connection()
        return {
            'status': 'healthy' if db_status else 'degraded',
            'database': 'connected' if db_status else 'disconnected',
            'service': 'Queue-Cure',
            'version': '2.0.0'
        }, 200 if db_status else 503

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return render_template('500.html'), 500

    logger.info(f"✅ Queue-Cure v2.0 app created successfully")
    return app


def _create_directories(app):
    """Create necessary directories."""
    dirs = [
        os.path.join(app.static_folder, 'qrcodes'),
        os.path.join(app.static_folder, 'css'),
        os.path.join(app.static_folder, 'js'),
        os.path.join(app.static_folder, 'images')
    ]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)


# Create app instance
app = create_app(os.environ.get('FLASK_ENV', 'default'))
socketio = init_socketio(app)


if __name__ == '__main__':
    logger.info("🚀 Starting Queue-Cure Server v2.0...")
    logger.info("🌐 Website: http://127.0.0.1:5000")

    socketio.run(
        app,
        host='127.0.0.1',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config.get('DEBUG', True),
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )