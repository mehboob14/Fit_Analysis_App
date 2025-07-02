import base64
import json
import re
import cv2
import os
from typing import Dict, Any, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4.1"

def run_waist_analysis_from_json(json_path=None) -> Dict[str, Any]:
    print("Running waist analysis...")
    try:
        if json_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(base_dir, "data", "formatted_output.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dress_data = json.load(f)
        except Exception as e:
            return {"error": f"Error loading scraped data: {e}"}

        try:
            image_path = dress_data["images"]["fabric_dress_image"]
        except Exception as e:
            return {"error": f"Error extracting image path: {e}"}

        results = run_waist_analysis(image_path)
        if not isinstance(results, dict):
            return {"error": "run_waist_analysis did not return a dictionary"}
        return results
    except Exception as e:
        return {"error": f"Unexpected error in run_waist_analysis_from_json: {e}"}

def encode_image(image_path: str) -> str:
    """Encode an image as base64 string."""
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_json_response(raw: str) -> Dict[str, Any]:
    """Extract JSON object from LLM text output."""
    try:
        match = re.search(r'\{.*"output"\s*:\s*".*?".*?\}', raw, re.DOTALL)
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
    try:
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
  "output": "yes" or "no",
  "summary": "very short explanation"
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
    except Exception as e:
        return {
            tag: "error",
            f"{tag}_summary": f"Error in run_prompt: {e}"
        }

def run_waist_analysis(image_path: str) -> Dict[str, Any]:
    try:
        image_b64 = encode_image(image_path)
        if api_key is None:
            return {"error": "OPENAI_API_KEY environment variable not set"}
        llm = ChatOpenAI(model=OPENAI_MODEL, openai_api_key=api_key, temperature=0)
        messages = []

        
        intro_message = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
            },
            {
                "type": "text",
                "text": """Now I'll be asking you a couple of questions regarding the waist of this dress.
By evaluating the image, would you say that the waist of this dress is tight? 
No other factors to be considered except for tight.

Respond only in JSON format:
{
  "output": "yes" or "no",
  "summary": "short explanation"
}"""
            }
        ]

        messages.append(HumanMessage(content=intro_message))
        response = llm.invoke(messages)
        messages.append(AIMessage(content=response.content))

        state = {}
        parsed = extract_json_response(response.content)
        state["waist_tight"] = parsed["output"].lower()
        state["waist_tight_summary"] = parsed["summary"]

        waist_prompts = [
            ("waist_fitted", "Is the waist of this dress fitted?", False),
            ("waist_flare", "Is there any flare at the waist?", False),
            ("waist_loose", "Is the waist of this dress loose?", False),
        ]

        for tag, question, use_image in waist_prompts:
            result = run_prompt(llm, messages, tag, question, image_b64 if use_image else None)
            state.update(result)
        print("Waist analysis completed..")
        return state
    except Exception as e:
        return {"error": f"Error in run_waist_analysis: {e}"}
