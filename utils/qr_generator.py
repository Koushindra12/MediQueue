import qrcode
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)


class QRGenerator:
    """QR Code generation utility."""
    
    QR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'qrcodes')
    
    @staticmethod
    def ensure_directory():
        """Ensure QR code directory exists."""
        os.makedirs(QRGenerator.QR_DIR, exist_ok=True)
    
    @staticmethod
    def generate_queue_qr(token_number: int, data: dict) -> str:
        """Generate QR code for queue token."""
        try:
            QRGenerator.ensure_directory()
            
            today = datetime.utcnow().date().isoformat()
            filename = f"token_{token_number}_{today}.png"
            filepath = os.path.join(QRGenerator.QR_DIR, filename)
            
            # QR data
            qr_content = json.dumps({
                'token': token_number,
                'patient': data.get('patient', ''),
                'date': today,
                'system': 'Queue-Cure',
                'check_url': f'/patient/status/{token_number}'
            })
            
            # Generate QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            # Create image with colors
            qr_image = qr.make_image(
                fill_color='#1a56db',
                back_color='white'
            )
            
            # Save QR code
            qr_image.save(filepath)
            
            # Return relative path for URL usage
            return f'/static/qrcodes/{filename}'
            
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            return ''
    
    @staticmethod
    def generate_patient_card_qr(patient_id: str, patient_name: str) -> str:
        """Generate QR code for patient card."""
        try:
            QRGenerator.ensure_directory()
            
            filename = f"patient_{patient_id}.png"
            filepath = os.path.join(QRGenerator.QR_DIR, filename)
            
            qr_content = json.dumps({
                'patient_id': patient_id,
                'patient': patient_name,
                'system': 'Queue-Cure'
            })
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=4
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            qr_image = qr.make_image(
                fill_color='#059669',
                back_color='white'
            )
            qr_image.save(filepath)
            
            return f'/static/qrcodes/{filename}'
            
        except Exception as e:
            logger.error(f"Patient QR generation error: {e}")
            return ''
    
    @staticmethod
    def cleanup_old_qr_codes(days: int = 7):
        """Clean up QR codes older than specified days."""
        try:
            import time
            cutoff = time.time() - (days * 86400)
            
            for filename in os.listdir(QRGenerator.QR_DIR):
                filepath = os.path.join(QRGenerator.QR_DIR, filename)
                if os.path.isfile(filepath):
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        logger.info(f"Removed old QR code: {filename}")
                        
        except Exception as e:
            logger.warning(f"QR cleanup error: {e}")