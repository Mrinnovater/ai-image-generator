# app.py
import streamlit as st
from PIL import Image
import io
from datetime import datetime

from ai_processor import generate_profession_image
from printable_card import generate_printable_card
from storage_mongo import save_file_to_db
from database_history import save_history

st.set_page_config(page_title="Future Goal AI – Printable", layout="wide")
st.title("📸 AI Future Goal – Printable & Saved to MongoDB")

# Inputs
name = st.text_input("Student Name")
school = st.text_input("School Name")
goal = st.selectbox("Future Goal",
                    ["Doctor", "IAS Officer", "Pilot", "Engineer", "Scientist", "Lawyer", "Army Officer"])
logo = st.file_uploader("Upload School Logo (optional)", type=["png", "jpg", "jpeg"])

st.subheader("📷 Capture Student Photo")
captured_image = st.camera_input("Take Photo")


if captured_image and st.button("Generate AI Future Image"):

    # Convert captured pic to bytes
    captured_img = Image.open(captured_image)
    stream = io.BytesIO()
    captured_img.save(stream, format="PNG")

    # Generate AI image
    st.info("⏳ Generating realistic AI portrait…")
    ai_bytes = generate_profession_image(stream, goal)
    ai_img = Image.open(io.BytesIO(ai_bytes))

    # Show results
    col1, col2 = st.columns(2)
    with col1: st.image(captured_img, caption="Captured Photo", width=300)
    with col2: st.image(ai_img, caption=f"Future {goal}", width=300)

    # Build printable card
    printable = generate_printable_card(
        name=name, school=school, goal=goal,
        captured_img=captured_img, ai_img=ai_img, logo_file=logo
    )

    # Final card → bytes
    card_buffer = io.BytesIO()
    printable.save(card_buffer, format="PNG")
    card_bytes = card_buffer.getvalue()

    # Save to MongoDB GridFS
    captured_id = save_file_to_db(stream.getvalue(), f"{name}_captured.png", "image/png")
    ai_id = save_file_to_db(ai_bytes, f"{name}_ai.png", "image/png")
    card_id = save_file_to_db(card_bytes, f"{name}_card.png", "image/png")

    save_history(name, school, goal, captured_id, ai_id, card_id)

    st.success("📦 Saved to MongoDB Successfully!")

    # Printable preview
    st.subheader("🖨️ Printable A4 Card")
    st.markdown('<div id="print-area">', unsafe_allow_html=True)
    st.image(printable, width=600)
    st.markdown('</div>', unsafe_allow_html=True)

    # Print button
    print_js = """
    <script>
        function printDiv() {
            var content = document.getElementById('print-area').innerHTML;
            var printWindow = window.open('', '', 'height=800,width=600');
            printWindow.document.write('<html><head><title>Print</title>');
            printWindow.document.write('</head><body>');
            printWindow.document.write(content);
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.print();
        }
    </script>

    <button onclick="printDiv()" style="
        background-color:#4CAF50; color:white;
        padding:12px 24px; border:none;
        border-radius:8px; cursor:pointer;
        font-size:18px; margin-top:20px;
    ">🖨️ Print</button>
    """

    st.markdown(print_js, unsafe_allow_html=True)

    # Download button
    st.download_button(
        "⬇️ Download Printable PNG",
        card_bytes,
        file_name=f"{name}_{goal}.png",
        mime="image/png"
    )
