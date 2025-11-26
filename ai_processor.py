# ai_processor.py
import base64
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_profession_image(image_stream, goal):
    """
    100% Working (2025 API):
    1. Feed the student's image to GPT-4o using image_url → data URI base64
    2. GPT-4o generates a detailed DALL·E prompt preserving the face
    3. GPT-Image-1 generates the final image
    """

    # Convert webcam image to base64 data URI
    img_bytes = image_stream.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_uri = f"data:image/png;base64,{img_b64}"

    # --- STEP 1: GPT-4o Vision builds a precise DALL·E prompt ---
    prompt_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate extremely detailed photorealistic portrait prompts "
                    "for DALL·E while preserving the person's identity."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Study this student's face and generate a perfect DALL·E prompt to recreate "
                            f"the SAME person as a future {goal}. "
                            "Preserve face structure, skin tone, eyes, hair, and expression. "
                            "Add realistic {goal} uniform and workplace background. "
                            "Output ONLY the final prompt."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_uri
                        }
                    }
                ]
            }
        ]
    )

    dalle_prompt = prompt_response.choices[0].message.content


    # --- STEP 2: Generate the future-goal image ---
    img_result = client.images.generate(
        model="gpt-image-1",
        prompt=dalle_prompt,
        size="1024x1024"
    )

    out_b64 = img_result.data[0].b64_json
    return base64.b64decode(out_b64)

