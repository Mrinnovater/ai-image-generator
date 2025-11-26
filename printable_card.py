# printable_card.py
from PIL import Image, ImageDraw, ImageFont
import io

A4_WIDTH_PX = 2480   # A4 @ 300 DPI
A4_HEIGHT_PX = 3508  # A4 @ 300 DPI


def generate_printable_card(name, school, goal, captured_img, ai_img, logo_file=None):
    """
    Build a high-quality A4 printable card.
    NOTE: logo_file is ignored (no logo required)
    """

    # ---------------------------------------------
    # 1. Create A4 white canvas
    # ---------------------------------------------
    card = Image.new("RGB", (A4_WIDTH_PX, A4_HEIGHT_PX), "white")
    draw = ImageDraw.Draw(card)

    # ---------------------------------------------
    # 2. Fonts
    # ---------------------------------------------
    try:
        font_title = ImageFont.truetype("arial.ttf", 90)
        font_sub = ImageFont.truetype("arial.ttf", 60)
        font_body = ImageFont.truetype("arial.ttf", 70)
    except:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # ---------------------------------------------
    # 3. Title
    # ---------------------------------------------
    title_text = "Future Goal Profile"
    title_y = 120

    draw.text(
        ((A4_WIDTH_PX - draw.textlength(title_text, font=font_title)) // 2,
         title_y),
        title_text,
        fill="black",
        font=font_title
    )

    # ---------------------------------------------
    # 4. Student Details
    # ---------------------------------------------
    info_y = 350

    draw.text((200, info_y),       f"Name: {name}", fill="black", font=font_body)
    draw.text((200, info_y + 120), f"School: {school}", fill="black", font=font_body)
    draw.text((200, info_y + 240), f"Future Goal: {goal}", fill="black", font=font_body)


    # ---------------------------------------------
    # 5. Resize and place images
    # ---------------------------------------------
    img_width = 900

    # Captured image
    ratio1 = img_width / captured_img.width
    cap_img = captured_img.resize((img_width, int(captured_img.height * ratio1)))

    # AI-generated image
    ratio2 = img_width / ai_img.width
    ai_img_resized = ai_img.resize((img_width, int(ai_img.height * ratio2)))

    # Positions
    cap_x, cap_y = 200, info_y + 450
    ai_x, ai_y = A4_WIDTH_PX - img_width - 200, info_y + 450

    card.paste(cap_img, (cap_x, cap_y))
    card.paste(ai_img_resized, (ai_x, ai_y))

    # Labels
    draw.text((cap_x, cap_y + cap_img.height + 20), "Captured Photo", fill="black", font=font_sub)
    draw.text((ai_x, ai_y + ai_img_resized.height + 20), f"Future {goal}", fill="black", font=font_sub)

    # ---------------------------------------------
    # 6. Output to BytesIO
    # ---------------------------------------------
    out = io.BytesIO()
    card.save(out, "PNG", dpi=(300, 300))
    out.seek(0)

    return Image.open(out)
