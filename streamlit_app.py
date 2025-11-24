# streamlit_app.py
"""
Career Future Self - Single-file Streamlit app (frontend + Mongo + OpenAI + Google Drive)

Features:
- Option C UI (gradient hero + steps)
- Session-based storage of user data & images
- MongoDB: save name, mobile (unique), dream, timestamp; admin number upsert logic
- AI generation via OpenAI gpt-image-1 (image input + prompt)
- Google Drive upload (service account) as backup; public download link saved in DB & session
- Download button + Share via WhatsApp (wa.me link). Optional pywhatkit send if enabled locally.
- Uses provided asset image paths (local). Replace with your own images if needed.

Required environment (.env):
MONGO_URI=
DB_NAME=career_future_self
OPENAI_API_KEY=
AI_MODEL=gpt-image-1
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id_here
ADMIN_NUMBER=9999912345   # 10-digit admin/test number
USE_PYWHATKIT=false       # 'true' if you plan to run pywhatkit locally (optional)
API_MODE=streamlit_only   # informational only

Dependencies (requirements.txt):
streamlit
pymongo
python-dotenv
openai
google-api-python-client
google-auth
google-auth-httplib2
google-auth-oauthlib
pillow
requests
pywhatkit (optional, only if USE_PYWHATKIT=true and running locally)
"""

import os
import re
import io
import base64
from datetime import datetime
from typing import Optional

import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# DB & OpenAI & Google Drive imports
from pymongo import MongoClient, errors
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import certifi
CA = certifi.where()
# OpenAI new official client (the "OpenAI" wrapper)
try:
    from openai import OpenAI
except Exception:
    # fallback to 'openai' package - adapt if needed
    import openai as _openai
    OpenAI = None

import requests

# Optional pywhatkit (only if you plan to run locally with GUI)
try:
    import pywhatkit
except Exception:
    pywhatkit = None

load_dotenv()

# -----------------------------
# Config from environment
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI", "").strip()
DB_NAME = os.getenv("DB_NAME", "career_future_self").strip()
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "Master").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "dall-e-3").strip()
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json").strip()
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "7981856940").strip()  # 10-digit admin/test number
USE_PYWHATKIT = os.getenv("USE_PYWHATKIT", "false").lower() == "true"

# Assets (using the local paths you provided earlier)
HERO_IMAGE = "/mnt/data/c2892358-61a1-46b7-83cf-0d1da964c83f.png"
FORM_MOCKUP = "/mnt/data/bf99c585-61c4-4ced-9329-b29718fec640.png"
RESULT_MOCKUP = "/mnt/data/e592523b-9207-488e-8c60-30402ee1da7c.png"

# UI style constants
PRIMARY_GRADIENT = "linear-gradient(90deg, #2D9CDB 0%, #9B51E0 50%, #F2994A 100%)"
CARD_BG = "#ffffff"
ACCENT = "#2D9CDB"

# Validate OpenAI client
openai_client = None
if OPENAI_API_KEY:
    try:
        if OpenAI is not None:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            # older openai library fallback
            _openai.api_key = OPENAI_API_KEY
            openai_client = _openai
    except Exception:
        openai_client = None

# Mongo client
mongo_client = None
collection = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(
            MONGO_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
        )
        db = mongo_client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # ensure unique index on mobile
        try:
            collection.create_index("mobile", unique=True)
        except Exception:
            pass

    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
        collection = None

# Google Drive service
drive_service = None
if os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE) and GOOGLE_DRIVE_FOLDER_ID:
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        drive_service = build("drive", "v3", credentials=creds)
    except Exception as e:
        drive_service = None

# Mobile validation: Indian 10-digit beginning 6-9
MOBILE_RE = re.compile(r'^(?:\+91[\-\s]?|0?)?([6-9]\d{9})$')

# Streamlit page config
st.set_page_config(page_title="Career Future Self", layout="wide", page_icon="🎯")

# Session defaults
if "page" not in st.session_state:
    st.session_state.page = "home"
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "original_image" not in st.session_state:
    st.session_state.original_image = None  # bytes
if "generated_image" not in st.session_state:
    st.session_state.generated_image = None  # bytes
if "drive_file_id" not in st.session_state:
    st.session_state.drive_file_id = None
if "drive_url" not in st.session_state:
    st.session_state.drive_url = None
if "request_saved" not in st.session_state:
    st.session_state.request_saved = False
if "mongo_id" not in st.session_state:
    st.session_state.mongo_id = None

# -----------------------------
# Helper functions
# -----------------------------
def normalize_mobile(raw: str) -> Optional[str]:
    if not raw:
        return None
    m = MOBILE_RE.match(raw.strip())
    if not m:
        return None
    return m.group(1)

def image_bytes_to_b64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode("utf-8")

def b64_to_image_bytes(b64_str: str) -> bytes:
    return base64.b64decode(b64_str)

def pil_image_to_bytes(img: Image.Image, fmt="JPEG", quality=90) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()

# DB helpers
def save_to_mongo(name: str, mobile: str, dream: str, timestamp: datetime, admin_number: str = ADMIN_NUMBER):
    """
    Save submission to MongoDB.
    - mobile is unique
    - if mobile == ADMIN_NUMBER -> upsert (update timestamp)
    Returns: (ok: bool, result: inserted_id or error message)
    """
    if collection is None:
        return False, "MongoDB not configured."

    doc = {
        "name": name,
        "mobile": mobile,
        "dream": dream,
        "timestamp": timestamp,
    }
    try:
        if admin_number and mobile == admin_number:
            # Upsert (update timestamp)
            res = collection.find_one_and_update(
                {"mobile": mobile},
                {"$set": doc},
                upsert=True,
                return_document=True
            )
            return True, str(res.get("_id"))
        else:
            res = collection.insert_one(doc)
            return True, str(res.inserted_id)
    except errors.DuplicateKeyError:
        return False, "Mobile number already exists."
    except Exception as e:
        return False, str(e)

def update_mongo_with_drive(mongo_id: str, drive_url: str, drive_file_id: str):
    if collection is None or not mongo_id:
        return False, "MongoDB not configured or no id"
    try:
        from bson import ObjectId
        collection.update_one({"_id": ObjectId(mongo_id)}, {"$set": {"drive_url": drive_url, "drive_file_id": drive_file_id}})
        return True, None
    except Exception as e:
        return False, str(e)

# OpenAI image generation
def generate_future_career_image(image_bytes: bytes, career: str, name: str) -> bytes:
    """
    If OpenAI API key missing → return original image (fallback mode)
    If OpenAI fails → return original image
    """

    # Fallback: No OpenAI key
    if not OPENAI_API_KEY or openai_client is None:
        return image_bytes  # return same image

    # base64 input
    b64_in = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        f"Take the provided user's face image and generate a realistic portrait of the same person "
        f"as a 25–30-year-old {career} in an Indian context. Keep the same facial features and skin tone, "
        f"slightly matured appearance, confident and professional expression. Dress them in a profession-appropriate outfit "
        f"(no real badges, insignia, logos, or government IDs). Use a clean, simple career-related background. "
        f"Output photo-realistic, well-lit image. No graphic, sexual, political, or hateful content."
    )

    try:
        if OpenAI is not None and isinstance(openai_client, OpenAI):
            response = openai_client.images.generate(
                model=AI_MODEL,
                prompt=prompt,
                image=[{"image": b64_in}],
                size="1024x1024"
            )
            b64_out = response.data[0].b64_json
            return base64.b64decode(b64_out)

        else:
            resp = openai_client.Image.create(
                model=AI_MODEL,
                prompt=prompt,
                image=[{"image": b64_in}],
                size="1024x1024"
            )
            return base64.b64decode(resp['data'][0]['b64_json'])

    except Exception:
        # AI model failed → fallback image
        return image_bytes

# Google Drive upload
def upload_to_drive(file_bytes: bytes, filename: str):
    """
    Uploads bytes to Google Drive folder (GOOGLE_DRIVE_FOLDER_ID) using service account.
    Makes the file publicly readable and returns (file_id, public_download_url).
    """
    if drive_service is None:
        raise RuntimeError("Google Drive service not configured or service account file missing.")

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype="image/jpeg", resumable=False)
    file_metadata = {"name": filename, "parents": [GOOGLE_DRIVE_FOLDER_ID]}

    created = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    file_id = created.get("id")

    # Make public
    drive_service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()

    public_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    return file_id, public_url

# WhatsApp share helper
def create_wa_link(message: str):
    quoted = requests.utils.quote(message)
    return f"https://wa.me/?text={quoted}"

def try_send_whatsapp_with_pywhatkit(phone_no: str, message: str):
    """
    Attempt to send via pywhatkit if enabled and available. This requires a running desktop/browser
    environment and logged-in WhatsApp Web. Not available on Streamlit Cloud usually.
    """
    if not pywhatkit:
        raise RuntimeError("pywhatkit not installed.")
    # pywhatkit expects phone in format '+91xxxxxxxxxx'
    try:
        pywhatkit.sendwhatmsg_instantly(phone_no, message, wait_time=15)
        return True, None
    except Exception as e:
        return False, str(e)

# -----------------------------
# CSS + small scripts
# -----------------------------
st.markdown(
    f"""
    <style>
    :root{{ --accent: {ACCENT}; }}
    .hero-bg {{
        background: {PRIMARY_GRADIENT};
        padding: 60px 40px;
        border-radius: 18px;
        color: white;
        box-shadow: 0 8px 40px rgba(35, 48, 77, 0.08);
        margin-bottom: 20px;
    }}
    .hero-title {{
        font-size: 44px;
        font-weight: 800;
        line-height: 1.02;
        margin-bottom: 12px;
    }}
    .hero-sub {{
        font-size: 18px;
        opacity: 0.95;
        margin-bottom: 22px;
    }}
    .cta-btn {{
        background: white;
        color: #123;
        padding: 12px 26px;
        border-radius: 999px;
        font-weight: 600;
        text-decoration: none;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    }}
    .card {{
        background: {CARD_BG};
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 12px 40px rgba(16,24,40,0.06);
    }}
    .spinner {{
      width:56px;height:56px;border-radius:50%;
      background: conic-gradient(from 0deg, rgba(255,255,255,0.12), rgba(255,255,255,0.9));
      animation: spin 1s linear infinite;
      box-shadow: 0 8px 30px rgba(0,0,0,0.12) inset;
      display:inline-block;
    }}
    @keyframes spin {{ to{{ transform: rotate(360deg); }} }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Page navigation helpers
# -----------------------------
def go_home():
    st.session_state.page = "home"

def go_create():
    st.session_state.page = "create"

def go_result():
    st.session_state.page = "result"

# -----------------------------
# Pages
# -----------------------------
def page_home():
    st.markdown('<div class="hero-bg">', unsafe_allow_html=True)
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown('<div class="hero-title">See Your <span style="background:linear-gradient(90deg,#6FC3F7,#7C65F2);-webkit-background-clip:text;color:transparent">Future Career Self</span>!</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-sub">Upload or take a live photo and watch yourself aged 25–30 in the career you dream of — professional, inspiring, and photo-realistic.</div>', unsafe_allow_html=True)
        if st.button("Start Now — Create My Future Self"):
            go_create()
        st.write("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown("<small>Made for students and young people (13+). Privacy-first — consent required.</small>", unsafe_allow_html=True)

        st.write("<div style='height:18px'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="card" style="display:flex;gap:14px;align-items:center;">
                <div style="flex:1;text-align:center;">
                    <div style="width:80px;height:80px;border-radius:16px;background:rgba(255,255,255,0.12);display:inline-flex;align-items:center;justify-content:center;font-size:28px">📷</div>
                    <div style="margin-top:12px;font-weight:600">Click / Upload</div>
                </div>
                <div style="width:40px;text-align:center;font-size:28px;color:#fff">→</div>
                <div style="flex:1;text-align:center;">
                    <div style="width:80px;height:80px;border-radius:16px;background:rgba(255,255,255,0.12);display:inline-flex;align-items:center;justify-content:center;font-size:28px">🎓</div>
                    <div style="margin-top:12px;font-weight:600">Choose Career</div>
                </div>
                <div style="width:40px;text-align:center;font-size:28px;color:#fff">→</div>
                <div style="flex:1;text-align:center;">
                    <div style="width:80px;height:80px;border-radius:16px;background:rgba(255,255,255,0.12);display:inline-flex;align-items:center;justify-content:center;font-size:28px">✨</div>
                    <div style="margin-top:12px;font-weight:600">See Future You</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        # hero image from provided path
        if os.path.exists(HERO_IMAGE):
            try:
                hero_img = Image.open(HERO_IMAGE)
                st.image(hero_img, use_container_width=True)
            except Exception:
                st.info("Hero image not found or invalid.")
        else:
            st.info("Hero image not found; replace HERO_IMAGE path in code.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><h4>Safe & Private</h4><p>We only use your photo to create the image. Consent is required and data is handled carefully.</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><h4>Photo-Realistic</h4><p>Outputs are realistic portraits aged 25–30 in career-appropriate attire (no real badges).</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><h4>Share & Download</h4><p>Download your image or share it with friends when ready. Drive backup is optional.</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Footer • About • Privacy • Contact: hello@example.com")

def page_create():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Create your Future Career Self")
    st.caption("Step 1: Fill your details. Step 2: Capture / Upload a clear face photo. Step 3: Generate.")
    with st.form("form", clear_on_submit=False):
        name = st.text_input("Your Name *", value=st.session_state.form_data.get("name", ""))
        age = st.number_input("Your Age", min_value=13, max_value=100, value=st.session_state.form_data.get("age", 18))
        gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"], index=0)
        status = st.selectbox("Current Status", ["Student", "Working", "Preparing (exams)", "Other"], index=0)
        mobile_raw = st.text_input("Mobile Number *", value=st.session_state.form_data.get("mobile",""), placeholder="10-digit Indian number")
        mobile = normalize_mobile(mobile_raw)
        if mobile_raw and not mobile:
            st.warning("Enter a valid 10-digit Indian mobile number (start 6-9).")

        dream = st.selectbox("Your Dream Career *", [
            "Doctor",
            "Indian Police Officer",
            "Software Engineer",
            "Teacher",
            "Scientist",
            "Businessperson / Entrepreneur",
            "Army Officer",
            "Lawyer",
            "Artist / Musician",
            "Other"
        ])
        other = ""
        if dream == "Other":
            other = st.text_input("Please specify your dream career")

        st.markdown("### Step 2: Capture a photo (face clearly visible)")
        col_cam, col_upload = st.columns(2)
        with col_cam:
            camera_image = st.camera_input("Click Live Photo")
        with col_upload:
            upload_image = st.file_uploader("Or upload from gallery", type=["jpg","jpeg","png"])

        chosen_image = None
        if camera_image:
            chosen_image = camera_image
        elif upload_image:
            chosen_image = upload_image

        if chosen_image:
            try:
                img = Image.open(chosen_image)
                st.image(img, caption="Selected image preview", use_container_width=False)
            except Exception as e:
                st.error("Unable to read image: " + str(e))

        consent = st.checkbox("I agree to the use of my photo for generating my future career image. My data will not be misused or publicly shared without my permission.")
        submitted = st.form_submit_button("Generate My Future Career Photo")

    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        # Validations
        if not name.strip():
            st.error("Please enter your name.")
            return
        if not mobile:
            st.error("Please enter a valid mobile number.")
            return
        if dream == "Other" and not other.strip():
            st.error("Please specify your dream career.")
            return
        if not chosen_image:
            st.error("Please capture or upload a clear face photo.")
            return
        if not consent:
            st.error("Consent is required.")
            return

        # Save to session
        st.session_state.form_data = {
            "name": name.strip(),
            "age": age,
            "gender": gender,
            "status": status,
            "mobile": mobile,
            "dream": other.strip() if dream == "Other" else dream
        }

        # Save original image bytes
        try:
            st.session_state.original_image = chosen_image.getvalue()
        except Exception as e:
            st.error("Could not read image bytes: " + str(e))
            return

        # Save to MongoDB (unique mobile)
        now = datetime.utcnow()
        ok, res = save_to_mongo(
            name=st.session_state.form_data["name"],
            mobile=st.session_state.form_data["mobile"],
            dream=st.session_state.form_data["dream"],
            timestamp=now
        )
        if not ok:
            st.error(f"{res}")
            return
        st.session_state.request_saved = True
        st.session_state.mongo_id = res

        # Proceed to generation / result page
        go_result()

def page_result():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header(f"Here is your Future Career Self, {st.session_state.form_data.get('name','Friend')}!")
    st.caption(f"You as a {st.session_state.form_data.get('dream','Career')} at age 25–30.")
    st.write("")

    # If already generated, show it
    if st.session_state.generated_image:
        st.image(st.session_state.generated_image, use_container_width=True)
    else:
        # Show loader block
        st.markdown(
            """
            <div style="display:flex;gap:18px;align-items:center;padding:16px;border-radius:12px;background:linear-gradient(90deg, rgba(45,156,219,0.06), rgba(155,81,224,0.04));">
                <div class="spinner"></div>
                <div>
                    <div style="font-weight:700">Generating your Future Career Self...</div>
                    <div style="opacity:0.85">This may take 20–60 seconds. We will only use your photo for this generation and will not publish it without your permission.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Kick off generation
        try:
            # Generate image using OpenAI
            with st.spinner("Contacting AI model..."):
                generated_bytes = generate_future_career_image(
                    image_bytes=st.session_state.original_image,
                    career=st.session_state.form_data.get("dream"),
                    name=st.session_state.form_data.get("name")
                )
            st.session_state.generated_image = generated_bytes
        except Exception as e:
            st.error(f"Image generation failed: {e}")
            return

        # Upload to Google Drive as backup (if configured)
        # Drive backup only if all 3 conditions satisfied:
        # 1. service is ready
        # 2. folder ID exists
        # 3. OPENAI key exists (optional, but keeps logic clean)
        if drive_service is not None and GOOGLE_DRIVE_FOLDER_ID:
            try:
                fname = f"{st.session_state.form_data.get('name')}-{st.session_state.form_data.get('dream')}-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
                file_id, public_url = upload_to_drive(st.session_state.generated_image, fname)
                st.session_state.drive_file_id = file_id
                st.session_state.drive_url = public_url

                if st.session_state.mongo_id:
                    update_mongo_with_drive(st.session_state.mongo_id, public_url, file_id)

                st.success("Image generated & backed up to Google Drive.")
            except Exception as e:
                st.warning(f"Drive upload failed: {e}")
        else:
            st.info("Drive backup skipped (no credentials or folder ID).")


    # Display the generated image
        try:
            st.image(st.session_state.generated_image, use_container_width=True)
        except Exception:
            st.warning("Could not load generated image preview.")

    st.write("")  # spacing

    # Action buttons
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.session_state.generated_image:
            # streamlit download button needs bytes or file-like
            if st.button("Download Image"):
                try:
                    st.download_button(
                        label="Click to save image",
                        data=st.session_state.generated_image,
                        file_name=f"{st.session_state.form_data.get('name','user')}_{st.session_state.form_data.get('dream','career')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg",
                        mime="image/jpeg"
                    )
                except Exception as e:
                    st.error("Download failed: " + str(e))
    with c2:
        if st.button("Share on WhatsApp"):
            message = (
                f"🔥 {st.session_state.form_data.get('name')}'s Future Career Self! 🔥\n\n"
                f"Looking great as a {st.session_state.form_data.get('dream')} — age 25–30.\n"
            )

            # Include Drive link only if available
            if st.session_state.drive_url:
                message += f"\nDownload image: {st.session_state.drive_url}\n"
            else:
                message += "\nDownload is available inside the app.\n"

            # pywhatkit only works locally, not on Streamlit Cloud
            if USE_PYWHATKIT and pywhatkit:
                try:
                    phone_full = "+91" + st.session_state.form_data.get("mobile")
                    ok, err = try_send_whatsapp_with_pywhatkit(phone_full, message)
                    if ok:
                        st.success("Message sent via pywhatkit (check WhatsApp Web)")
                    else:
                        st.error(f"pywhatkit failed: {err}")
                except Exception as e:
                    st.error(f"pywhatkit error: {e}")

            else:
                wa_link = create_wa_link(message)
                st.markdown(f"[Open WhatsApp →]({wa_link})", unsafe_allow_html=True)

    with c3:
        if st.button("Try Another Career"):
            # preserve name/mobile to ease re-use
            preserve = {
                "name": st.session_state.form_data.get("name", ""),
                "mobile": st.session_state.form_data.get("mobile", "")
            }
            st.session_state.form_data = preserve
            st.session_state.original_image = None
            st.session_state.generated_image = None
            st.session_state.drive_file_id = None
            st.session_state.drive_url = None
            st.session_state.request_saved = False
            st.session_state.mongo_id = None
            go_create()

    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# Router
# -----------------------------
if st.session_state.page == "home":
    page_home()
elif st.session_state.page == "create":
    page_create()
elif st.session_state.page == "result":
    page_result()
else:
    page_home()

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center;color:#7F8FA4;'>© Career Future Self — Privacy first. Contact: hello@example.com</div>", unsafe_allow_html=True)
