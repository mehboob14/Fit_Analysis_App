
import base64
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage
import cv2 as cv
import os
import json

OPENAI_MODEL = "gpt-4.1"
api_key = os.getenv("OPENAI_API_KEY")

def encode_image(image_path):
    image = cv.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image at path: {image_path}")
    _, buffer = cv.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def run_fit_analysis(front_image_path, side_image_path, json_path=None):
    print("fit analysis started")
    front_b64 = encode_image(front_image_path)
    side_b64 = encode_image(side_image_path)

    if json_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "scraper", "data", "formatted_output.json")

    with open(json_path, "r", encoding="utf-8") as f:
        dress_data = json.load(f)

    images = dress_data["images"]
    dress1 = encode_image(images["model_wearning_front_image"])
    dress2 = encode_image(images["model_wearning_back_image"])
    dress3 = encode_image(images["fabric_dress_image"])

    prompts = [
        {
            "prompt": """
                You’re a fashion designer and fit expert. I’m uploading the client’s images.
                Evaluate their body proportions silently in the background.
                Do not generate any output yet. You will use this to inform the dress evaluations that follow.
            """,
            "image_b64": [front_b64, side_b64]
        },
        {
            "prompt": """
You’re a fashion designer and fit expert. Based on the dress image, 
fabric details, and the client’s body proportions provided earlier,
write a one-paragraph narrative-style evaluation. Assess how the dress fits and interacts with the client’s
body across the waist, bodice, hips, skirt, neckline, flare, fabric, and sleeves.
Be objective and balanced — highlight both flattering and unflattering elements.
Give a realistic summary and final verdict: "recommended" or "not recommended".
            """,
            "image_b64": [dress1, dress2, dress3]
        }
    ]

    memory = ConversationBufferMemory(memory_key="history", return_messages=True)
    llm = ChatOpenAI(
        model=OPENAI_MODEL,
        openai_api_key=api_key,
        temperature=0.5,
        max_tokens=2000
    )

    final_response = ""

    for i, step in enumerate(prompts):
        user_msg_content = []

        for img_b64 in step["image_b64"]:
            user_msg_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}"
                }
            })

        user_msg_content.append({
            "type": "text",
            "text": step["prompt"]
        })

        full_messages = memory.load_memory_variables({})["history"] + [
            HumanMessage(content=user_msg_content)
        ]

        response = llm(full_messages)
        memory.chat_memory.add_user_message(HumanMessage(content=user_msg_content))
        memory.chat_memory.add_ai_message(AIMessage(content=response.content))

        final_response = response.content 

    return final_response
