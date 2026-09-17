import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def test_qwen_vision():
    api_key = os.getenv("GROQ_API_KEY")
    from groq import Groq
    client = Groq(api_key=api_key)
    
    # Download a sample jpeg image
    img_data = requests.get("https://picsum.photos/200/300.jpg").content
    base64_image = base64.b64encode(img_data).decode('utf-8')
    
    prompt = "Describe this image."
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1
        )
        print("Response:", response.choices[0].message.content.strip())
    except Exception as e:
        print("Error:", type(e).__name__, e)
        if hasattr(e, 'response'):
            print(e.response.json())

test_qwen_vision()
