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

def run_neckline_analysis_from_json(json_path=None) -> Dict[str, Any]:
    print("Running Neckline analysis...")
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

        results = run_neckline_analysis(image_path)
        if not isinstance(results, dict):
            return {"error": "run_neckline_analysis did not return a dictionary"}
        return results
    except Exception as e:
        return {"error": f"Unexpected error in run_neckline_analysis_from_json: {e}"}

def encode_image(image_path: str) -> str:
    """Encode an image as base64 string."""
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def extract_json_response(raw: str) -> Dict[str, Any]:
    """Extracts a JSON-like structure with 'output' and 'summary' from LLM raw response."""
    try:
        
        data = json.loads(raw)
        if "output" in data and "summary" in data:
            return data
    except json.JSONDecodeError:
        
        try:
            match = re.search(r'\{\s*"output"\s*:\s*"(.*?)"\s*,\s*"summary"\s*:\s*"(.*?)"\s*\}', raw, re.DOTALL)
            if match:
                return {"output": match.group(1), "summary": match.group(2)}
        except Exception as e:
            return {"output": "error", "summary": f"Regex extraction error: {e}"}

    
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
return only in strict JSON format:
{{
    "output": "single word answer",
    "summary": "short explanation"
}}

"""
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

def run_neckline_analysis(image_path: str) -> Dict[str, Any]:
    try:
        image_b64 = encode_image(image_path)
        if api_key is None:
            return {"error": "OPENAI_API_KEY missing"}
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
                "text": """Is the neckline of this dress positioned high, mid, or low on the chest?

return only in strict JSON format:
{
    "output": "single word answer",
    "summary": "short explanation"
}          
"""
            }
        ]

        messages.append(HumanMessage(content=intro_message))
        response = llm.invoke(messages)
        messages.append(AIMessage(content=response.content))

        state = {}
        parsed = extract_json_response(response.content)
        state["high-mid-low"] = parsed["output"].lower()
        state["high-mid-low_summary"] = parsed["summary"]

        waist_prompts = [
            ("Neckline Type", "Based on the visual and structural design of the dress, how would you categorize its neckline? Please choose the most appropriate option from the following list: Button-up Crew, V-neck with Collar, Zipper with Collar, Collar, Asymmetric, V-neck, Turtleneck, Mock Neck, Crew, Button-up with Collar, Halter, Boat, or Cowl", False),

        ]

        for tag, question, use_image in waist_prompts:
            result = run_prompt(llm, messages, tag, question, image_b64 if use_image else None)
            state.update(result)
        print("Neckline Analysis completed..")
        return state
    except Exception as e:
        return {"error": f"Error in run_Neckline_analysis: {e}"}
    
if __name__ == "__main__":
    image_path = r"C:\Users\Administrator\Desktop\Learning\Scraping\dress_scraper_app\dress_images\Moncler_dress_image.png"  
    results = run_neckline_analysis(image_path)
    print(results)
