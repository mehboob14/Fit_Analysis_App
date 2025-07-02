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

def run_Back_analysis_from_json(json_path=None) -> Dict[str, Any]:
    print("Running Back analysis...")
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
            image_path = dress_data["images"]["model_wearning_back_image"]
        except Exception as e:
            return {"error": f"Error extracting image path: {e}"}

        results = run_full_analysis(image_path)
        if not isinstance(results, dict):
            return {"error": "run_full_analysis did not return a dictionary"}
        return results
    except Exception as e:
        return {"error": f"Unexpected error in One_Shoulder_analysis_from_json: {e}"}

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
    """ return {tag: yes|no, tag_summary: ...}"""
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
  "output": "pick from prompt if not mentioned, then must be yes or no",
  "summary": " short explanation"
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

def run_full_analysis(image_path: str) -> Dict[str, Any]:
    try:
        image_b64 = encode_image(image_path)
        if api_key is None:
            return {"error": "OPENAI_API_KEY missing"}
        llm = ChatOpenAI(model=OPENAI_MODEL, openai_api_key=api_key, temperature=0)
        messages = []
        
        state: Dict[str, Any] = {}
        prompts: List[Tuple[str, str, bool]] = [
            ("Back Type", "Based on the structure and design of the dress, how would you categorize the back style? Please choose one of the following: Open, Cutout, Closed, or Racerback.", True),
            ("Buttons", "Does the back of the dress have any buttons", False),
            ("Zippers", "Does the back of the dress have any Zippers?", False),
        ]


        for tag, question, use_image in prompts:
            image = image_b64 if use_image else None
            result = run_prompt(llm, messages, tag, question, image_b64=image)
            state.update(result)
        print("back analysis stuff completed")
        return state
    except Exception as e:
        return {"error": f"Error in run_full_analysis: {e}"}
    
# if __name__ == "__main__":
#     image_path = r"C:\Users\Administrator\Desktop\Learning\Scraping\dress_scraper_app\dress_images\max_mara_back_image.png"
#     result  = run_full_analysis(image_path)
#     print(json.dumps(result, indent=2, ensure_ascii=False))