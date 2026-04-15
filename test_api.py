import os
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

try:
    response = model.generate_content("hello")
    print("SUCCESS")
    print(response.text)
except Exception as e:
    print("ERROR:")
    print(type(e).__name__)
    print(e)
