import os
import json
import base64
from openai import OpenAI

def run_structure():
    print("structing started")
    BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Scripts")
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    IMAGES_DIR = os.path.join(DATA_DIR, 'images', 'downloaded')
    DETAILS_PATH = os.path.join(DATA_DIR, 'dress_details.txt')
    SIZE_GUIDE_PATH = os.path.join(DATA_DIR, 'Size_guide.json')
    OUTPUT_PATH = os.path.join(DATA_DIR, 'formatted_output.json')

    client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

    def load_text(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def load_json(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def encode_image(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    image_files = sorted([
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith(".jpeg") or f.lower().endswith(".jpg")
    ])

    image_id_map = {}
    base64_images = []

    for idx, filename in enumerate(image_files):
        image_id = f"img_{idx+1:03}"
        full_path = os.path.join(IMAGES_DIR, filename)
        image_id_map[image_id] = full_path
        b64_data = encode_image(full_path)

        base64_images.append({
            "role": "user",
            "content": [
                {"type": "text", "text": f"This is image {image_id}."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_data}",
                        "detail": "auto"
                    }
                }
            ]
        })

    details_text = load_text(DETAILS_PATH)
    size_guide_json = load_json(SIZE_GUIDE_PATH)

    text_prompt = f"""
You will be shown a list of images with IDs (e.g. img_001, img_002).
Your job is to visually inspect each and classify them into:

- fabric_close_image
- fabric_dress_image
- model_wearning_front_image
- model_wearning_back_image

Use the following JSON format:

{{
  "Fabric_charactericts": "...",
  "Model_Measurement": "...",
  "images": {{
    "fabric_close_image": "img_003",
    "model_wearning_front_image": "img_001",
    ...
  }},
  "sizing_guide": {{}}
}}

Dress description:
{details_text}

Sizing guide:
{json.dumps(size_guide_json, indent=2)}

Return only the JSON. Do not invent IDs. Do not add markdown.
"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant that structures product data into labeled JSON."},
        {"role": "user", "content": text_prompt},
        *base64_images
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0].strip()

    structured = json.loads(content)

    if "images" in structured:
        for key, image_id in structured["images"].items():
            path = image_id_map.get(image_id)
            if path:
                structured["images"][key] = path
            else:
                print(f" Warning: ID {image_id} not found!")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=2)

    print(f"\nJSON saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_structure()
