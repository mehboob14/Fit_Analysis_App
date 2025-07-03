import base64
import cv2 as cv
import os
import json

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage

OPENAI_MODEL = "gpt-4.1"
api_key = os.getenv("OPENAI_API_KEY")
def encode_image(image_path):
    image = cv.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image at path: {image_path}")
    _, buffer = cv.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")


def run_fit_analysis(front_image_path, side_image_path, tags_json_path):
    print(" Fit analysis started")
    print(" Using tags JSON path:", tags_json_path)

  
    front_b64 = encode_image(front_image_path)
    side_b64 = encode_image(side_image_path)


    with open(tags_json_path, "r", encoding="utf-8") as f:
        tags_data = json.load(f)


    base_dir = os.path.dirname(os.path.abspath(__file__))
    dresses_json_path = os.path.join(base_dir, "data", "formatted_output.json")
    print("dresses_path", dresses_json_path)
    try:
        with open(dresses_json_path, "r", encoding="utf-8") as f:
            dress_data = json.load(f)
    except Exception as e:
        return {"error": f"Error loading scraped data: {e}"}

    try:
        dress1 = encode_image(dress_data["images"]["fabric_dress_image"])
        dress2 = encode_image(dress_data["images"]["model_wearning_back_image"])
        dress3 = encode_image(dress_data["images"]["model_wearning_front_image"])

    except Exception as e:
            return {"error": f"Error extracting image path: {e}"}

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
            "prompt": f"""
                Tags: {json.dumps(tags_data)}
                These are the output tags of the dresses and below are the conditions. 

Fabric
If fabric is shiny → Calls attention to body
If fabric is light-colored or patterned → May show undergarments or highlight features
If fabric is stretchy → Increases comfort
If fabric is see-through/sheer → Not modest, requires layering
If fabric retains odor → Less desirable, harder to maintain
If fabric is not machine washable → High maintenance

Waist
If dress is tight at the waist → Accentuates waist, flatters hourglass shapes
If waist is elasticized or cinched → Adds comfort, defines shape
If there’s no defined waist → Can create a boxy silhouette

Flare
If skirt is flared → Generally flatters most body types
If skirt is not flared (straight or tight) → May restrict movement, highlights hip/leg area

Hips
If skirt is tight at the hips → Accentuates hips
If skirt has darts/panels at hips → Adds structure, draws attention

Skirt Length
If skirt reaches high thigh → Not work appropriate, Reveals legs
If skirt reaches mid thigh → Accentuates legs, still not formal
If skirt reaches knee or below → Work appropriate, modest
If skirt is tight around thighs → May ride up, accentuates body lines
If skirt has slits/buttons at thigh → Reveals more leg, not modest

Hemline
If hemline is asymmetric/high-low → Draws attention to legs, adds movement
If hemline is straight → Balanced, formal
If hemline is too short → Not work appropriate

Neckline
If neckline is low → Not modest, draws attention to chest
If neckline is high → Brings attention to the face, modest
If neckline is plunging/sweetheart → May accentuate bust
If neckline is off-shoulder → Accentuates shoulders, not conservative

One Shoulder
If one-shoulder and tight → Accentuates larger upper body, not modest
If one-shoulder and draped → Adds elegance, softens sharp body lines

Sleeves
If sleeves are short or sleeveless → Shows arms, may not be modest
If sleeves are puffy or ruffled → Adds volume, may hide arms
If armholes are high-set → Makes frame look slimmer
If sleeves are tight → Accentuates arm shape, not suitable for all body types

Back
If back is low or open → Not work appropriate, Risk of undergarments showing
If back is covered or high → Modest and structured
If back has cutouts → Trendy but less conservative

Bodice
If bodice has boning/corset → Accentuates waist, flatters bust
If bodice has built-in support → Good for larger bust
If bodice is loose/unstructured → May create a boxy or shapeless look

                You’re a fashion designer and fit expert. Based on the dress images, 
                fabric details, the client’s body proportions provided earlier, write a one-paragraph narrative-style evaluation.

                Assess how the dress fits and interacts with the client’s
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

    for step in prompts:
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

        tags_data['Conclusion'] = final_response

        with open(tags_json_path, "w", encoding="utf-8") as f:
            json.dump(tags_data, f, indent=2)


    return final_response
