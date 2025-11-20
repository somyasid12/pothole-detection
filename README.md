📸 Pothole Detection & Reporting System
AI-powered road monitoring • YOLOv8 Model • Automated Complaint Filing • PDF + Email Generator
This project is a complete AI-based pothole detection and reporting system, built to help automate road safety monitoring. It uses a custom-trained YOLOv8 model to detect potholes from images, generates visual reports, auto-creates complaint letters, exports PDF reports, and can send them via email with attachments.

The project includes a FastAPI backend and a modern HTML/CSS/JS dashboard frontend.

🚀 Features

🔍 1. AI Pothole Detection (YOLOv8)
Upload multiple road images at once
YOLOv8 model detects potholes with bounding boxes
Processed images are returned instantly
Pothole count + breakdown per image

📝 2. Auto Complaint Generator
Auto-fills a full complaint letter based on:
Pothole count
Road name
Area / locality
City
Optional extra details

📄 3. PDF Report Exporter
Generates a formatted PDF complaint
Ready to share with government authorities

✉️ 4. Email Sender
Sends email directly from the dashboard
Automatically attaches detected pothole images
Supports SMTP (Brevo / Gmail / any provider)

🖥 5. Modern Dashboard UI
Clean TailwindCSS-based interface
Drag & drop uploader
Live image carousel
Dark mode toggle
Full desktop-ready design

🗂 Project Structure

Potehole_project/
│
├── Backend/
│   ├── app.py                  # FastAPI backend
│   ├── requirements.txt        # Backend dependencies
│   ├── frontend/               # HTML/CSS/JS dashboard
│   │   ├── index.html
│   │   ├── asset/
│   │   │   ├── style.css
│   │   │   └── js/script.js
│   ├── static/                 # (Optional) saved outputs
│   │   ├── uploads/
│   │   ├── results/
│   │   └── pdfs/
│
├── Model/
│   └── Yolov8-fintuned-on-potholes.pt
│
└── README.md

🧠 Tech Stack

YOLOv8 (Ultralytics) for pothole detection
FastAPI for backend APIs
Pillow / NumPy for image handling
ReportLab for PDF generation
SMTP for email automation
HTML + Tailwind CSS + JavaScript frontend

⚙️ Setup & Installation

1️⃣ Clone the repository
git clone https://github.com/your-username/pothole-detection.git
cd pothole-detection

2️⃣ Create virtual environment
python3 -m venv venv
source venv/bin/activate

3️⃣ Install backend dependencies
pip install -r Backend/requirements.txt

4️⃣ Add your .env file inside Backend/
Create a file:
Backend/.env
With:
OPENROUTER_API_KEY=...
SMTP_HOST=...
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
FROM_EMAIL=...
SAVE_OUTPUTS=false

5️⃣ Run the FastAPI backend
cd Backend
python -m uvicorn app:app --reload
Backend starts at:
http://127.0.0.1:8000
Open your browser → Dashboard loads automatically.

📡 API Endpoints (Main)

🚀 Detect potholes
POST /api/predict
Accepts multiple images and returns detection results.

📝 Generate complaint text
POST /api/generate_complaint

📄 Generate complaint PDF
POST /api/generate_pdf

✉️ Send email
POST /api/send_email

🙌 Author
Somya Siddarth
AI Engineer 
Passionate about real-world AI applications & automation.
⭐ Contribute
PRs, suggestions, and improvements are welcome!
Make sure to open an issue before submitting a pull request.
📜 License
MIT License — feel free to modify and use with attribution.
