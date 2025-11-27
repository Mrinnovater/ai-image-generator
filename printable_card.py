# printable_card.py
from PIL import Image, ImageDraw, ImageFont
import io

TEMPLATE_PATH = "assets/template.jpeg"   # update path if needed


def generate_printable_card(name, school, goal, captured_img, ai_img, logo_file=None):
    """
    Printable card with ONLY the AI-generated image at the TOP.
    No labels, no text. Simply center the AI image.
    """

    # Load template (background)
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    W, H = template.size

    card = template.copy()

    # -------------------------------
    # 1. Resize AI image to 500px width
    # -------------------------------
    target_width = 1000
    ratio = target_width / ai_img.width
    new_height = int(ai_img.height * ratio)

    ai_resized = ai_img.resize((target_width, new_height))

    # -------------------------------
    # 2. Center at the TOP
    # -------------------------------
    x = (W - target_width) // 2
    y = 150  # top padding

    card.paste(ai_resized, (x, y))

    # -------------------------------
    # 3. Export PNG
    # -------------------------------
    out = io.BytesIO()
    card.save(out, "PNG")
    out.seek(0)

    return Image.open(out)
