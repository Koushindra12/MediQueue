from datetime import datetime, timedelta
from functools import wraps
from flask import jsonify, request
import re
import logging

logger = logging.getLogger(__name__)


def validate_phone(phone: str) -> bool:
    """Validate phone number format — accepts international and local formats."""
    if not phone:
        return False
    # Strip all non-digit characters (except leading +) for length check
    digits_only = re.sub(r'[^\d]', '', phone.strip())
    # Accept 7-15 digit phone numbers (international range)
    return 7 <= len(digits_only) <= 15


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return True  # Email is optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def format_time(minutes: int) -> str:
    """Format minutes to human-readable time."""
    if minutes <= 0:
        return "Now"
    elif minutes < 60:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"


def get_time_greeting() -> str:
    """Get time-based greeting."""
    hour = datetime.utcnow().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"


def api_response(success: bool, message: str = '', data: dict = None, 
                 status_code: int = 200) -> tuple:
    """Standard API response format."""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    if data:
        response['data'] = data
    
    return jsonify(response), status_code


def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, str]:
    """Validate required fields in request data."""
    missing = []
    for field in required_fields:
        if not data.get(field, '').strip() if isinstance(data.get(field), str) else not data.get(field):
            missing.append(field)
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, ""


def sanitize_input(data: dict) -> dict:
    """Sanitize input data."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = value.strip()
        else:
            sanitized[key] = value
    return sanitized


def get_priority_label(priority: str) -> dict:
    """Get priority label and color."""
    priorities = {
        'normal': {'label': 'Normal', 'color': '#059669', 'icon': '🟢'},
        'urgent': {'label': 'Urgent', 'color': '#d97706', 'icon': '🟡'},
        'emergency': {'label': 'Emergency', 'color': '#dc2626', 'icon': '🔴'}
    }
    return priorities.get(priority, priorities['normal'])


def get_status_label(status: str) -> dict:
    """Get status label and color."""
    statuses = {
        'waiting': {'label': 'Waiting', 'color': '#1a56db', 'icon': '⏳'},
        'called': {'label': 'Called', 'color': '#d97706', 'icon': '📢'},
        'in_consultation': {'label': 'In Consultation', 'color': '#059669', 'icon': '🩺'},
        'completed': {'label': 'Completed', 'color': '#6b7280', 'icon': '✅'},
        'cancelled': {'label': 'Cancelled', 'color': '#dc2626', 'icon': '❌'},
        'no_show': {'label': 'No Show', 'color': '#9333ea', 'icon': '👻'}
    }
    return statuses.get(status, {'label': status.title(), 'color': '#6b7280', 'icon': '❓'})