import base64
import json
import os
import cv2
from typing import TypedDict, Optional, Callable, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

api_key = os.getenv("OPENAI_API_KEY")
llm_model = ChatOpenAI(api_key=api_key)

class HipState(TypedDict, total=False):
    images: List[str]
    messages: List
    high_hip_tight: Optional[str]
    high_flare_tight: Optional[str]
    high_hip_fitted: Optional[str]
    high_flare_fitted: Optional[str]
    high_hip_loose: Optional[str]
    low_hip_tight: Optional[str]
    low_flare_tight: Optional[str]
    low_hip_fitted: Optional[str]
    low_flare_fitted: Optional[str]
    low_hip_loose: Optional[str]

def encode_image(image_path: str) -> str:
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image at path: {image_path}")
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def create_prompt_node(question: str, key: str, with_image: bool = False, is_first: bool = False) -> Callable[[HipState], HipState]:
    def node(state: HipState) -> HipState:
        images = state.get("images", [])
        messages = state.get("messages", [])

        if is_first:
            messages.append(SystemMessage(content="Now, I'll be asking you a couple of questions regarding the high hip area of this dress. Respond only in JSON."))

        content = [{
            "type": "text",
            "text": f"Question:\n{question}\n\nRespond only in JSON:\n{{\"output\": \"yes\" or \"no\", \"explanation\": \"reasoning\"}}"
        }]

        if with_image and images:
            for img in images:
                content.insert(0, {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                })

        messages.append(HumanMessage(content=content))
        response = llm_model.invoke(messages)
        messages.append(AIMessage(content=response.content))
        state["messages"] = messages

        try:
            output = json.loads(response.content.strip()).get("output", "").lower()
            state[key] = output if output in ["yes", "no"] else "unknown"
        except Exception:
            lowered = response.content.lower()
            state[key] = "yes" if "yes" in lowered else "no" if "no" in lowered else "unknown"

        return state
    return node

def build_chain(label: str, tight_key: str, flare_tight_key: str, fitted_key: str, flare_fitted_key: str, loose_key: str) -> Callable[[HipState], HipState]:
    def chain(state: HipState) -> HipState:
        state = create_prompt_node(f"First question: Is the {label} area of this dress tight?", tight_key, with_image=True, is_first=True)(state)
        if state.get(tight_key) == "yes":
            state = create_prompt_node(f"The {label} area is tight. Is there a flare in this area?", flare_tight_key)(state)

        state = create_prompt_node(f"Is the {label} area of this dress fitted?", fitted_key)(state)
        if state.get(fitted_key) == "yes":
            state = create_prompt_node(f"The {label} area of this dress is fitted but is there a flare in this area? ", flare_fitted_key)(state)

        state = create_prompt_node(f"Is the {label} area of this dress loose?", loose_key)(state)
        return state
    return chain

high_hip_chain = build_chain("high hip", "high_hip_tight", "high_flare_tight", "high_hip_fitted", "high_flare_fitted", "high_hip_loose")
low_hip_chain = build_chain("low hip", "low_hip_tight", "low_flare_tight", "low_hip_fitted", "low_flare_fitted", "low_hip_loose")

def invoke(images: List[str]) -> dict:
    print("hip analysis runing..")
    state: HipState = {"images": images, "messages": []}
    high = high_hip_chain(state.copy())
    low = low_hip_chain(state.copy())
    for key in ["messages", "images"]:
        high.pop(key, None)
        low.pop(key, None)
    return {"high_hip": high, "low_hip": low}

def run_hip_analysis_from_json(json_path=None) -> dict:
    print("Running hip analysis...")
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
            dress_image_path = dress_data["images"]["fabric_dress_image"]
            model_wearing_front_image_path = dress_data["images"]["model_wearning_front_image"]
        except Exception as e:
            return {"error": f"Error extracting image path: {e}"}

        try:
            images = [encode_image(dress_image_path), encode_image(model_wearing_front_image_path)]
        except Exception as e:
            return {"error": f"Error encoding images: {e}"}

        try:
            result = invoke(images)
        except Exception as e:
            return {"error": f"Error in invoke: {e}"}

        if not isinstance(result, dict):
            return {"error": "invoke did not return a dictionary"}
        print("Hip analysis completed.")
        return result
    except Exception as e:
        return {"error": f"Unexpected error in run_hip_analysis_from_json: {e}"}
    

# if __name__ == "__main__":
#     result = run_hip_analysis_from_json()
#     if "error" in result:
#         print(f"Error: {result['error']}")
#     else:
#         print("High Hip Analysis:", result["high_hip"])
#         print("Low Hip Analysis:", result["low_hip"])