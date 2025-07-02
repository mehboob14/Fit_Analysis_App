import base64
import json
import re
import cv2
from typing import Dict, Any, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os

api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1"

def run_fabric_analysis_from_json(json_path=None):
    print("Running Fabric analysis...")
    if json_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "data", "formatted_output.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            dress_data = json.load(f)
    except Exception as e:
        print(f"Error loading scraped data: {e}")
        return None

    fabric_characteristics = dress_data["Fabric_charactericts"]
    fabric_dress_image_path = dress_data["images"]["fabric_dress_image"]

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

    def run_prompt(
        llm: ChatOpenAI,
        messages: List,
        tag: str,
        question: str,
        image_b64: Optional[str] = None
    ) -> Dict[str, Any]:
        content = []
        if image_b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
            })
        content.append({
            "type": "text",
            "text": f"""{question}

Respond only in strict JSON format:
{{
  \"output\": \"yes\" or \"no\",
  \"summary\": \"very short explanation\"
}}"""
        })
        messages.append(HumanMessage(content=content))
        response = llm.invoke(messages)
        messages.append(AIMessage(content=response.content))
        parsed = extract_json_response(response.content)
        return {
            tag: parsed["output"].lower(),
            f"{tag}_summary": parsed["summary"]
        }

    def run_fabric_analysis(image_path: str, fabric_description: str):
        image_b64 = encode_image(image_path)
        llm = ChatOpenAI(model=OPENAI_MODEL, openai_api_key=api_key, temperature=0)
        messages = []
        state = {}

        intro_message = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            {"type": "text", "text": f"""You're a senior specialist and a fashion expert on women's dresses. Your job is to help analyze this dress.
I'm attaching an image and mentioning about the fabric of the dress. I will ask you a series of questions about this dress.

Fabric Description:
{fabric_description}

Give separate evaluations for bodice and skirt.

First question, is the dress fabric thick?

Respond only in JSON format:
{{\n  \"output\": \"yes\" or \"no\",\n  \"summary\": \"short explanation\"\n}}"""}
        ]
        messages.append(HumanMessage(content=intro_message))
        response = llm.invoke(messages)
        messages.append(AIMessage(content=response.content))
        parsed = extract_json_response(response.content)
        state["fabric_thick"] = parsed["output"].lower()
        state["fabric_thick_summary"] = parsed["summary"]

        prompts = [
            ("fabric_drape", "Does the dress have any drape effect in any part?", False),
            ("fabric_light_colored", "Is the fabric light colored/patterned?", True),
            ("fabric_shiny", "Is the dress fabric shiny?", True),
            ("fabric_draws_attention", "So you mentioned that the skirt part of this dress is shiny (made of satin). Does it draw too much attention or appear overly highlighted to customers?", False),
            ("fabric_stretchy", "Is the dress fabric stretchy?", True),
            ("fabric_ribbed", "Is the dress fabric ribbed?", True),
            ("fabric_wrinkles", "Based on the fabric characteristics, does the fabric wrinkle easily?", True),
            ("fabric_sheer", "Is the dress see through/sheer?", True),
            ("fabric_retains_odor", "Based on the fabric characteristics, does the dress fabric retain odor?", True),
            ("fabric_machine_washable", "Is the dress machine washable?", False)
        ]

        for tag, question, initial_condition in prompts:
            condition = initial_condition
            if tag == "fabric_drape" and state.get("fabric_thick") == "no":
                condition = True
            elif tag == "fabric_draws_attention" and state.get("fabric_shiny") == "yes":
                condition = True
            elif tag == "fabric_machine_washable" and state.get("fabric_retains_odor") == "yes":
                condition = True

            if not condition:
                state[tag] = "skipped"
                continue

            result = run_prompt(llm, messages, tag, question, image_b64)
            state.update(result)
        print("Fabric analysis completed.")
        return state

    fabric_description = f"""{fabric_characteristics}"""
    print("runing fabric analysis...")
    fabric_results = run_fabric_analysis(fabric_dress_image_path, fabric_description)
    return fabric_results