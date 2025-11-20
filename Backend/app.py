import os
import io
import base64
import cv2
import numpy as np
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()

# -----------------------
# Config & paths
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
RESULT_DIR = os.path.join(STATIC_DIR, "results")
PDF_DIR = os.path.join(STATIC_DIR, "pdfs")

# create directories if someone still wants to save outputs locally
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Model path (adjust if you store model elsewhere)
MODEL_PATH = os.path.join(BASE_DIR, "..", "Model", "Yolov8-fintuned-on-potholes.pt")

# Control whether app writes files to disk. Default: no (safe for ephemeral hosts).
SAVE_OUTPUTS = os.getenv("SAVE_OUTPUTS", "false").lower() in ("1", "true", "yes")

# -----------------------
# FastAPI setup
# -----------------------
app = FastAPI(title="Pothole Detection Full App")

# Allow CORS so your HTML frontend (hosted elsewhere) can call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for production, lock this down to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static only so legacy disk-based URLs continue to work if SAVE_OUTPUTS is true.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


# Serve index.html at root (simple static hosting)
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# -----------------------
# Load YOLO model
# -----------------------
# We load the model once at startup. If your model is large, consider downloading it
# from remote storage during deployment instead of committing it to the repo.
model = YOLO(MODEL_PATH)
print("[INFO] Loaded model:", getattr(model, "names", "unknown"))


# -----------------------
# Helper utilities
# -----------------------
def numpy_from_bytes(image_bytes: bytes):
    """Convert raw image bytes to a BGR numpy array (cv2 compatible)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_np is None:
        # fallback: use PIL if cv2 can't decode directly
        try:
            from PIL import Image
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:
            raise RuntimeError("Could not decode uploaded image")
    return img_np


def encode_image_to_data_uri(img_np, ext=".jpg"):
    """Encode a BGR numpy image to a data URI (base64)."""
    success, encoded = cv2.imencode(ext, img_np)
    if not success:
        raise RuntimeError("Image encoding failed")
    img_bytes = encoded.tobytes()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    mime = "image/jpeg" if ext.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{b64}", img_bytes


# -----------------------
# PREDICTION ENDPOINT (in-memory by default)
# -----------------------
@app.post("/api/predict")
async def predict(images: list[UploadFile] = File(...)):
    """
    Accept multiple uploaded images, run YOLO, and return:
      - original_filename
      - result_image_data_uri  (base64 data URI for immediate display in browser)
      - optional result_image_url (only present if SAVE_OUTPUTS is true)
      - count (number of boxes)
    By default we do not write results/uploads to disk. Set SAVE_OUTPUTS=true to enable legacy file-saving.
    """
    results_list = []

    for upload in images:
        filename = upload.filename.replace("/", "_")
        contents = await upload.read()  # raw bytes

        # Convert to numpy array for model
        try:
            img_np = numpy_from_bytes(contents)
        except Exception as e:
            return JSONResponse({"error": f"Failed to decode {filename}: {str(e)}"}, status_code=400)

        # Optionally save the raw upload (legacy mode)
        upload_path = None
        if SAVE_OUTPUTS:
            upload_path = os.path.join(UPLOAD_DIR, filename)
            try:
                with open(upload_path, "wb") as f:
                    f.write(contents)
            except Exception as e:
                # don't break the whole loop on save errors; just warn
                print(f"[WARN] Failed to save upload {upload_path}: {e}")
                upload_path = None

        # Run YOLO on the in-memory numpy image
        # Note: ultralytics accepts numpy arrays as input
        results = model.predict(img_np, conf=0.05, save=False)
        result = results[0]

        # result.plot() returns an image (BGR numpy array)
        plotted = result.plot()

        # Encode plotted image to base64 data URI for frontend
        try:
            data_uri, img_bytes = encode_image_to_data_uri(plotted, ext=".jpg")
        except Exception as e:
            return JSONResponse({"error": f"Failed to encode result image: {e}"}, status_code=500)

        # Optionally write the result image to disk (legacy)
        result_url = None
        if SAVE_OUTPUTS:
            try:
                output_filename = "result_" + filename
                output_path = os.path.join(RESULT_DIR, output_filename)
                cv2.imwrite(output_path, plotted)
                result_url = f"/static/results/{output_filename}"
            except Exception as e:
                print(f"[WARN] Failed to save result {output_path}: {e}")
                result_url = None

        results_list.append({
            "original_filename": filename,
            "result_image_data_uri": data_uri,
            "result_image_url": result_url,
            "count": len(result.boxes),
            "detections": []  # keep this for compatibility with your frontend
        })

    return {"results": results_list}


# -----------------------
# COMPLAINT GENERATOR
# -----------------------
class ComplaintRequest(BaseModel):
    pothole_count: int
    road_name: str | None = ""
    area: str | None = ""
    city: str | None = ""
    user_name: str | None = "Concerned Citizen"
    authority_name: str | None = "Municipal Commissioner"
    extra_details: str | None = ""


@app.post("/api/generate_complaint")
async def gen_complaint(req: ComplaintRequest):
    # Build a polite, short complaint letter — simple templating
    text = f"""
Subject: Request for urgent pothole repair at {req.road_name}, {req.area}, {req.city}

Respected {req.authority_name},

I would like to bring to your attention that a total of {req.pothole_count} potholes 
have been detected on the road at {req.road_name}, {req.area}, {req.city}. These potholes 
pose a serious risk to commuters, especially at night.

{req.extra_details}

I request you to kindly take immediate action and repair the road at the earliest.

Thank you,
{req.user_name}
    """
    return {"complaint_text": text}


# -----------------------
# PDF GENERATOR (in-memory by default)
# -----------------------
class PDFRequest(BaseModel):
    complaint_text: str


@app.post("/api/generate_pdf")
async def generate_pdf(req: PDFRequest):
    """
    Generate a PDF from complaint text. Returns:
      - pdf_data_uri (base64 data URI for immediate download)
      - pdf_url (only if SAVE_OUTPUTS is true and file was written to disk)
    """
    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    text_obj = c.beginText(40, 800)
    text_obj.setFont("Helvetica", 12)

    for line in req.complaint_text.split("\n"):
        text_obj.textLine(line.rstrip())

    c.drawText(text_obj)
    c.showPage()
    c.save()
    buffer.seek(0)
    pdf_bytes = buffer.read()

    # Optionally write to disk (legacy)
    pdf_url = None
    if SAVE_OUTPUTS:
        try:
            filename = "complaint.pdf"
            filepath = os.path.join(PDF_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(pdf_bytes)
            pdf_url = f"/static/pdfs/{filename}"
        except Exception as e:
            print(f"[WARN] Failed to save PDF {filepath}: {e}")
            pdf_url = None

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_data_uri = f"data:application/pdf;base64,{pdf_b64}"

    return {"pdf_url": pdf_url, "pdf_data_uri": pdf_data_uri}


# -----------------------
# EMAIL SENDER (in-memory attachments preferred)
# -----------------------
class EmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    image_urls: list[str] = []         # legacy: /static/... paths
    image_data_b64: list[str] = []     # preferred: data URIs from /api/predict


@app.post("/api/send_email")
async def send_email(req: EmailRequest):
    """
    Send an email and attach images. Preferred approach: pass base64 data URIs
    in `image_data_b64`. If you pass `image_urls` and SAVE_OUTPUTS is true and the files
    exist, they will be attached from disk (legacy support).
    """
    try:
        SMTP_HOST = os.getenv("SMTP_HOST")
        SMTP_PORT = int(os.getenv("SMTP_PORT") or 587)
        SMTP_USERNAME = os.getenv("SMTP_USERNAME")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        FROM_EMAIL = os.getenv("FROM_EMAIL")

        # Basic debug prints (safe-ish). Remove in production if sensitive.
        print("SMTP_HOST:", SMTP_HOST)
        print("SMTP_USERNAME:", SMTP_USERNAME)
        if SMTP_PASSWORD:
            print("SMTP_PASSWORD: [REDACTED]")

        # Build message
        msg = EmailMessage()
        msg["From"] = FROM_EMAIL or SMTP_USERNAME or "no-reply@example.com"
        msg["To"] = req.to_email
        msg["Subject"] = req.subject
        msg.set_content(req.body)

        # Attach in-memory base64 images (preferred)
        for idx, data_uri in enumerate(req.image_data_b64 or []):
            if not data_uri:
                continue
            # expected form: data:image/jpeg;base64,AAAA...
            if data_uri.startswith("data:"):
                header, b64data = data_uri.split(",", 1)
                subtype = "jpeg"
                if "png" in header:
                    subtype = "png"
                filename = f"attachment_{idx}.{subtype}"
                try:
                    img_bytes = base64.b64decode(b64data)
                    msg.add_attachment(img_bytes, maintype="image", subtype=subtype, filename=filename)
                except Exception as e:
                    print(f"[WARN] Failed to decode/attach image_data_b64 idx={idx}: {e}")

        # Legacy: attach disk-based images referenced by /static/... if they exist and SAVE_OUTPUTS is true
        for url in req.image_urls or []:
            if url.startswith("/static") and SAVE_OUTPUTS:
                filepath = url.replace("/static", STATIC_DIR)
                try:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            data = f.read()
                        ext = os.path.splitext(filepath)[1].lower().lstrip(".")
                        subtype = "jpeg" if ext in ("jpg", "jpeg") else (ext or "octet-stream")
                        msg.add_attachment(data, maintype="image", subtype=subtype, filename=os.path.basename(filepath))
                except Exception as e:
                    print(f"[WARN] Failed to attach disk file {filepath}: {e}")

        # Send email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return {"status": "sent"}
    except Exception as e:
        # return error text (useful for debugging). In prod, sanitize this.
        return {"status": "error", "error": str(e)}

