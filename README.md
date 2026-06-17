# Queue-Cure - Smart Clinic Queue Management System

**A modern, real-time digital queue management system for hospitals and clinics.**

Queue-Cure transforms traditional manual queues into a smart, efficient, and patient-friendly digital experience with live updates, QR codes, and intelligent wait time estimation.

##  Features

### Core Features
- **Token-based Queue System** with automatic token generation
- **Real-time Updates** using Flask-SocketIO (Live queue, notifications)
- **Patient Registration** with medical history & emergency details
- **Priority Management** (Normal, Urgent, Emergency)
- **Dynamic Doctor Assignment** by department
- **QR Code Generation** for tokens and patient cards
- **Live Waiting Room Display** for patients
- **Smart Wait Time Estimation** based on historical consultation data
- **Full Consultation Workflow** (Start → Diagnosis → Prescription → Complete)
- **Doctor Management** (Add, Update, Deactivate)
- **Clinic Settings** (Name, hours, contact info, etc.)

### Analytics & Dashboard
- Live queue statistics
- Queue health indicator
- Patient search & history
- Doctor directory with stats
- Daily summary reports

---

## Tech Stack

- **Backend**: Flask (Python 3.11)
- **Database**: MongoDB (PyMongo)
- **Real-time Communication**: Flask-SocketIO + Eventlet
- **Frontend**: HTML5, CSS3, JavaScript (Modern & Responsive)
- **QR Codes**: qrcode + Pillow
- **Environment Management**: python-dotenv
- **Deployment Ready**: Render.com, Railway, Heroku

---

##  Project Structure

```bash
Queue-Cure/
├── app.py                          # Main application
├── config.py                       # Configuration
├── requirements.txt
├── .env.example
├── runtime.txt
│
├── database/
│   └── mongodb.py
│
├── models/
│   ├── patient_model.py
│   ├── queue_model.py
│   ├── doctor_model.py
│   └── consultation_model.py
│
├── services/
│   ├── queue_service.py            # Core business logic
│   ├── waittime_service.py
│   ├── token_service.py
│   └── clinic_service.py
│
├── routes/
│   ├── receptionist_routes.py
│   ├── patient_routes.py
│   └── doctor_routes.py
│
├── socket_events/
│   └── queue_events.py             # Real-time events
│
├── utils/
│   ├── helpers.py
│   └── qr_generator.py
│
├── templates/                      # Jinja2 Templates
├── static/
│   ├── qrcodes/                    # Generated QR codes
│   └── (css, js, images)
│
└── README.md
