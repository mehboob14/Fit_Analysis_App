import base64
import json
import re
import cv2
import asyncio
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os

OPENAI_MODEL = "gpt-4.1"
api_key = os.getenv("OPENAI_API_KEY")


def encode_image(image_path: str) -> str:
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_json_response(raw: str) -> Dict[str, Any]:
    try:
        match = re.search(r"\{.*?\"output\"\s*:\s*\"(yes|no)\".*?\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"output": "unknown", "summary": raw.strip()}

async def run_prompt_async(
    llm: ChatOpenAI,
    messages: List,
    tag: str,
    question: str,
    image_b64: Optional[str],
    model_measurements: str
) -> Dict[str, Any]:
    content = []
    if image_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
    content.append({
        "type": "text",
        "text": f"Model's measurements:\n{model_measurements}\n\n{question}\n\nRespond only in strict JSON format:\n{{\n  \"output\": \"yes\" or \"no\",\n  \"summary\": \"very short explanation\"\n}}"
    })
    messages.append(HumanMessage(content=content))
    response = await llm.ainvoke(messages)
    messages.append(AIMessage(content=response.content))
    parsed = extract_json_response(response.content)
    return {
        tag: parsed["output"].lower(),
        f"{tag}_summary": parsed["summary"]
    }

async def analyze_skirt_section(
    llm: ChatOpenAI,
    messages: List,
    image_b64: str,
    model_measurements: str,
    level: str,
    question: str,
    sub_tags: List[str]
) -> Dict[str, Any]:
    state = {}
    tag = f"skirt_{level}"
    main_result = await run_prompt_async(llm, messages, tag, question, image_b64, model_measurements)
    state.update(main_result)

    if main_result[tag] == "yes":
        for sub in sub_tags:
            sub_tag = f"{tag}_{sub}"
            if sub == "slits":
                sub_question = f"Does the skirt have slits or buttons in the {level.replace('_', ' ')} area?"
            else:
                sub_question = f"Is the skirt {sub.replace('_', ' ')} around the {level.replace('_', ' ')} area?"
            sub_result = await run_prompt_async(llm, messages, sub_tag, sub_question, image_b64, model_measurements)
            state.update(sub_result)
    else:
        for sub in sub_tags:
            state[f"skirt_{level}_{sub}"] = "skipped"
    return state

async def run_skirt_analysis(image_path: str, model_measurements: str) -> Dict[str, Any]:
    print("Starting skirt analysis...")
    try:
        image_b64 = encode_image(image_path)
    except Exception as e:
        return {"error": f"Image encoding error: {e}"}

    llm = ChatOpenAI(model=OPENAI_MODEL, openai_api_key=api_key, temperature=0)
    messages = []

    state = {}
    intro_result = await run_prompt_async(
        llm, messages, "skirt_ankle",
        "Does the skirt length reach the ankle?",
        image_b64, model_measurements
    )
    state.update(intro_result)

    levels = [
        ("floor", "Does the skirt length reach the floor?"),
        ("mid_calf", "By evaluating the image, does the skirt length reach or go past the mid-calf area?"),
        ("knee", "By evaluating the image, does the skirt length reach or go past the knee area?"),
        ("tea", "Does the skirt length reach the tea area?"),
        ("mid_thigh", "Does the skirt length reach or go past the mid thigh area?"),
        ("high_thigh", "Does the skirt length reach or go past the high thigh area?")
    ]
    sub_tags = ["tight", "slits", "buttons"]

    for level, question in levels:
        result = await analyze_skirt_section(llm, messages, image_b64, model_measurements, level, question, sub_tags)
        state.update(result)

    return state

def run_skirt_analysis_from_json(json_path=None) -> Dict[str, Any]:
    print("Running skirt analysis...")
    try:
        if json_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, "data", "formatted_output.json")

        with open(json_path, "r", encoding="utf-8") as f:
            dress_data = json.load(f)

        model_measurements = dress_data["Model_Measurement"]
        image_path = dress_data["images"]["model_wearning_front_image"]

        results = asyncio.run(run_skirt_analysis(image_path, model_measurements))
        if not isinstance(results, dict):
            return {"error": "run_skirt_analysis did not return a dictionary"}
        print("Skirt analysis completed")
        return results
    except Exception as e:
        return {"error": f"Unexpected error in run_skirt_analysis_from_json: {e}"}

# if __name__ == "__main__":
#     test_image_path = "../data/james_perse_dress_on_model_front.png"
#     test_model_details = """
# Model is 177cm/ 5'10"

# Bust: 79cm/ 31"
# Waist: 61cm/ 24"
# Hip: 89cm/ 35"""
#     try:
#         skirt_results = asyncio.run(run_skirt_analysis(test_image_path, test_model_details))
#         if "error" in skirt_results:
#             print(f"Error: {skirt_results['error']}")
#         else:
#             print("\nSkirt Analysis Results:")
#             for key, value in skirt_results.items():
#                 print(f"{key}: {value}")
#     except Exception as e:
#         print(f"\nUnexpected exception in __main__: {e}")
