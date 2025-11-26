# printable_card.py
from PIL import Image, ImageDraw, ImageFont
import io

A4_WIDTH_PX = 2480   # A4 @ 300 DPI
A4_HEIGHT_PX = 3508  # A4 @ 300 DPI


def generate_printable_card(name, school, goal, captured_img, ai_img, logo_file=None):
    """
    A4 Printable card
    Layout:
    - Title + student details
    - Captured photo (top)
    - AI-generated future photo (below)
    - Footer: Powered by Robokalam
    """

    # ---------------------------------------------
    # 1. Create white A4 canvas
    # ---------------------------------------------
    card = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), "white")
    draw = ImageDraw.Draw(card)

    # ---------------------------------------------
    # 2. Load fonts
    # ---------------------------------------------
    try:
        font_title = ImageFont.truetype("arial.ttf", 90)
        font_sub = ImageFont.truetype("arial.ttf", 60)
        font_body = ImageFont.truetype("arial.ttf", 70)
        font_footer = ImageFont.truetype("arial.ttf", 50)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_footer = ImageFont.load_default()

    # ---------------------------------------------
    # 3. Title
    # ---------------------------------------------
    title_text = "Future Goal Profile"
    draw.text(
        ((A4_WIDTH_PX - draw.textlength(title_text, font=font_title)) // 2, 100),
        title_text,
        fill="black",
        font=font_title
    )

    # ---------------------------------------------
    # 4. Student Info
    # ---------------------------------------------
    info_y = 300

    draw.text((200, info_y), f"Name: {name}", fill="black", font=font_body)
    draw.text((200, info_y + 120), f"School: {school}", fill="black", font=font_body)
    draw.text((200, info_y + 240), f"Future Goal: {goal}", fill="black", font=font_body)

    # ---------------------------------------------
    # 5. Images stacked vertically (centered)
    # ---------------------------------------------
    display_width = 1600  # wide for A4 layout

    # --- Captured image ---
    ratio1 = display_width / captured_img.width
    cap_resized = captured_img.resize(
        (display_width, int(captured_img.height * ratio1))
    )

    cap_x = (A4_WIDTH_PX - display_width) // 2
    cap_y = info_y + 450

    card.paste(cap_resized, (cap_x, cap_y))

    draw.text(
        ((A4_WIDTH_PX - draw.textlength("Captured Photo", font=font_sub)) // 2,
         cap_y + cap_resized.height + 20),
        "Captured Photo",
        fill="black",
        font=font_sub
    )

    # --- AI Image ---
    ratio2 = display_width / ai_img.width
    ai_resized = ai_img.resize(
        (display_width, int(ai_img.height * ratio2))
    )

    ai_x = (A4_WIDTH_PX - display_width) // 2
    ai_y = cap_y + cap_resized.height + 200

    card.paste(ai_resized, (ai_x, ai_y))

    draw.text(
        ((A4_WIDTH_PX - draw.textlength(f"Future {goal}", font=font_sub)) // 2,
         ai_y + ai_resized.height + 20),
        f"Future {goal}",
        fill="black",
        font=font_sub
    )

    # ---------------------------------------------
    # 6. Footer (centered)
    # ---------------------------------------------
    footer_text = "Powered by Robokalam"
    draw.text(
        ((A4_WIDTH_PX - draw.textlength(footer_text, font=font_footer)) // 2,
         A4_HEIGHT_PX - 200),
        footer_text,
        fill="gray",
        font=font_footer
    )

    # ---------------------------------------------
    # 7. Save to BytesIO (PNG)
    # ---------------------------------------------
    output = io.BytesIO()
    card.save(output, format="PNG", dpi=(300, 300))
    output.seek(0)

    return Image.open(output)
